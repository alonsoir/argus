## RESPUESTA DEL CONSEJO DE SABIOS — ADR-040

**Acta de deliberación y aprobación con enmiendas**  
**Fecha:** 28 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documento revisado:** ADR-040 (ML Plugin Retraining Contract)

---

### Valoración general

El Consejo considera que el ADR-040 es **necesario, sólido y metodológicamente correcto**. Aborda riesgos reales del aprendizaje continuo en ciberseguridad (catastrophic forgetting, feedback loop, regresión silenciosa) y propone contratos verificables. Se inspira en buenas prácticas del mundo de sistemas de recomendación (IPW, exploración) y las adapta al dominio NDR.

**Aprobado en su esencia**, con las siguientes enmiendas y respuestas a la pregunta abierta.

---

### Respuesta a la pregunta abierta: ¿Pipeline de evaluación interno o CI/CD externo?

**Decisión del Consejo (unánime):**  
✅ **Opción híbrida: núcleo interno reproducible + orquestación CI/CD externa.**

| Parte | Componente | Responsabilidad |
|-------|------------|------------------|
| **Interno (Vagrant/make)** | Script `evaluate_plugin.sh` que implementa walk-forward, golden set comparación, guardrail −2% | Cálculo de métricas, reproducibilidad local, misma VM que producción. |
| **Externo (GitHub Actions)** | Workflow que ejecuta el script interno en un entorno controlado (misma box Vagrant pero efímera) | Historial de decisiones, trazabilidad, impedir merges si guardrail no pasa. |

**Justificación científica (reproducibilidad + trazabilidad):**
- Si el pipeline de evaluación está solo en CI externo, se pierde la capacidad de un desarrollador de ejecutarlo localmente antes de subir un plugin candidato. Esto rompe la reproducibilidad (cada entorno CI puede tener diferencias sutiles).
- Si está solo interno, no hay un registro auditable de por qué un plugin fue rechazado; además, se podría eludir el guardrail haciendo `make bypass-validation`.
- La opción híbrida garantiza:
    1. **Reproducibilidad local** (mismo script se ejecuta en la VM dev).
    2. **Trazabilidad en GitHub** (cada PR que sube un nuevo plugin `.so` debe incluir un artefacto generado por el workflow, y el merge está bloqueado hasta que `evaluate_plugin` retorne 0).
    3. **Inmutabilidad del golden set**: el workflow CI puede verificar el SHA-256 del golden set contra un valor almacenado en secrets.

**Implementación concreta recomendada:**
```yaml
# .github/workflows/ml-plugin-validation.yml
on:
  pull_request:
    paths:
      - 'plugins/xgboost_plugin*.so'
jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Reproduce evaluation VM
        run: vagrant up --provider=virtualbox
      - name: Run internal evaluation script
        run: vagrant ssh -c '/opt/argus/bin/evaluate_plugin --golden-hash ${{ secrets.GOLDEN_HASH }}'
      - name: Check guardrail
        run: test $? -eq 0
```

**Aceptado por el Consejo con la condición de que el script interno `evaluate_plugin` sea parte del repositorio y esté documentado en `docs/ML-EVALUATION.md`.**

---

### Revisión detallada de las Reglas (con sugerencias)

#### Regla 1 — Walk-forward obligatorio
✅ **Correcta**. Añadir la especificación técnica de cómo implementar `--split-date` en presencia de múltiples pcaps.  
**Sugerencia:** usar `tcpdump -r all.pcap -G` o un índice de tiempo extraído del pcap original. Proporcionar un script de ejemplo en el ADR o en un anexo.

**Riesgo adicional identificado:** Si los datos de entrenamiento provienen de múltiples fuentes con diferentes marcas de tiempo, el split puede no ser determinista. **Solución:** antes del split, se debe ordenar cada flow por `timestamp_first_packet` y concatenar. Documentar en el ADR.

---

#### Regla 2 — Golden Set inmutable, versionado desde el principio
✅ **Correcta**. El Consejo añade una exigencia: **el golden set debe incluir también ejemplos de tráfico benigno real (no solo ataques)**.
- Proporción recomendada: 70% benigno, 30% ataques (similar a la distribución real en redes hospitalarias).
- El golden set debe estar en un formato canónico (CSV con columnas fijas) y un script de validación que verifique que no haya leaks temporales (i.e., ningún flow del golden set sea idéntico a uno del conjunto de entrenamiento).

**Tarea adicional:** crear `DEBT-GOLDEN-SET-CREATION-001` con fecha límite pre-FEDER (porque el golden set debe existir antes del primer reentrenamiento).

---

#### Regla 3 — Guardrail automático del −2% antes de firma Ed25519
✅ **Correcta**. El Consejo sugiere afinar los umbrales:

| Métrica | Umbral | Justificación adicional |
|--------|--------|--------------------------|
| F1 | −2 pp absolutos | Por ejemplo, de 0.9985 a 0.9785 es una caída enorme en la práctica. Más de 2 puntos es inaceptable. |
| Recall | −1 pp absolutos (máximo) | Es más restrictivo que F1 (prioriza no perder detección). Bien. |
| FPR | +2 pp absolutos | Por ejemplo, de 0.0002% a 2.0002% sería catastrófico. El límite es razonable. |

**Añadir una cuarta métrica:** **Latencia de inferencia p99** no debe degradarse más de un 10% (medido en el mismo hardware). Un plugin más lento puede hacer que el pipeline de detección se retrase.

**Mecanismo de firma:** El proceso de firma (en el Makefile o en el CI) debe ejecutar `evaluate_plugin --compare-with /opt/argus/current/plugin.so`. El plugin candidato solo se firma si el guardrail pasa.

---

#### Regla 4 — IPW + 5% de exploración forzada
✅ **Correcta**. El Consejo observa que la implementación real requerirá un **oráculo externo** para las etiquetas del 5% de flows benignos (pero que el modelo duda). Propuesta:

- Inicialmente, usar un **oráculo humano** (el administrador de seguridad del hospital) mediante una interfaz web sencilla en la que se muestran los flows y se pregunta "¿ataque o benigno?".
- A medio plazo, integrar con un **modelo auxiliar** (más lento pero más preciso, por ejemplo, un ensemble) como oráculo. El 5% es pequeño, no impacta rendimiento.

**Condición de cumplimiento adicional:** Cada ciclo de reentrenamiento debe generar un fichero `exploration_log.csv` con los flows muestreados y su etiqueta final.

---

#### Regla 5 — Competición de algoritmos antes de elegir XGBoost
✅ **Correcta**. El Consejo recomienda una **competición ciega**:

- El script de competición debe ejecutarse exactamente una vez, con los resultados almacenados en `docs/ALGORITHM_SELECTION.md`.
- Incluir no solo F1/Recall/FPR, sino también **tiempo de entrenamiento** y **tiempo de inferencia por flow** (en microsegundos).
- Registrar la versión de cada biblioteca (xgboost==2.1.0, catboost==1.2.5, lightgbm==4.5.0).

**Posible sorpresa:** CatBoost o LightGBM podrían ganar. El ADR debe aceptar ese resultado sin sesgo.

---

### Preguntas adicionales que el Consejo responde (no planteadas explícitamente pero relevantes)

#### ¿Cuándo debe ejecutarse el reentrenamiento? ¿Automático o manual?
- **Post-FEDER, pre-ADR-026:** manual (un operador decide cuándo lanzar un nuevo ciclo).
- **A partir de ADR-026 (P2P federado):** automático, con periodicidad configurable (semanal/mensual) y siempre que se acumulen más de 10.000 nuevos flows etiquetados.

**Consecuencia:** El pipeline de evaluación debe ser invocable tanto manual (`make retrain-plugin`) como programáticamente desde un cron o evento.

#### ¿Cómo se versiona el plugin y su metadatos?
- Cada plugin debe incluir una sección de metadatos en el propio binario (ej. una cadena `__plugin_version = "xgboost_v2.3.1_20260428"`).
- El golden set emite un informe que referencia la versión del plugin evaluado.

---

### Enmiendas formales al ADR-040 (deben incluirse antes de aprobar)

| Enmienda | Afecta a |
|----------|-----------|
| 1. Incluir métrica de latencia p99 con umbral +10% | Regla 3 |
| 2. Especificar que el split temporal debe hacerse sobre el timestamp del primer paquete de cada flow | Regla 1 |
| 3. Exigir que el golden set contenga 70% de tráfico benigno real | Regla 2 |
| 4. Documentar el procedimiento de oráculo humano (o auxiliar) para la exploración del 5% | Regla 4 |
| 5. Establecer que la competición de algoritmos se ejecutará una única vez pre-FEDER, con resultados públicos | Regla 5 |
| 6. Aprobar la opción híbrida (evaluación interna + CI externo) como arquitectura. | Pregunta abierta |

---

### Deuda técnica generada por ADR-040 (post-FEDER)

| ID | Descripción | Target release |
|----|-------------|----------------|
| DEBT-GOLDEN-SET-001 | Creación del golden set versionado (70% benigno, 30% ataques) con script de validación | v1.0 (pre-FEDER) |
| DEBT-WALKFORWARD-SCRIPT-001 | Implementar `evaluate_plugin --split-date` y walk-forward split determinista | v1.1 |
| DEBT-IPW-PIPELINE-001 | Integrar Inverse Propensity Weighting en rag-ingester | v1.2 |
| DEBT-EXPLORATION-5PCT-001 | Interfaz de oráculo humano y logging de exploración | v1.2 |
| DEBT-ALGO-COMPETITION-001 | Ejecutar competición XGBoost vs CatBoost vs LightGBM y generar documento | v1.0 (antes de elegir) |
| DEBT-GUARDRAIL-ED25519-001 | Integrar guardrail −2% en el proceso de firma Ed25519 (ADR-025) | v1.1 |

---

### Veredicto final del Consejo

El ADR-040 **se aprueba** con las enmiendas señaladas. Se ordena al equipo:

1. Incorporar las enmiendas en el texto del ADR (nueva versión PROPUESTO-V2).
2. Crear las deudas técnicas asociadas y asignarlas al backlog post-FEDER (hitos v1.0, v1.1, v1.2).
3. Antes de cualquier reentrenamiento real (primer ciclo post-FEDER), ejecutar la competición de algoritmos y documentar los resultados.

El contrato de reentrenamiento aquí definido eleva aRGus a un nivel de rigor comparable con sistemas de ML industriales (Google TFX, Uber Michelangelo). La combinación de walk-forward, golden set inmutable, guardrail y exploración forzada es una contribución original y publicable en conferencias de ingeniería de software (ICSE, FSE) o ciberseguridad (IEEE S&P).

*Firmado por los 8 modelos, 28 abril 2026.*  
*Via Appia Quality — “Un contrato que no puede saltarse un ingeniero es un contrato que funciona.”*