Por supuesto. Aquí va mi respuesta formal como miembro del Consejo, en el mismo formato que usé para ADR-041.

---

## Respuesta de Claude — ADR-040 ML Plugin Retraining Contract

---

### Sobre las 5 reglas propuestas — Validación general

El contrato está bien fundamentado. Las cinco reglas son necesarias y suficientes para el Año 1 post-FEDER. No propongo eliminar ninguna. Sí tengo matices en tres de ellas.

---

### Regla 1 — Walk-forward: APROBADA con precisión adicional

**Validación**: Correcta. El split temporal es innegociable en datos de red.

**Matiz importante**: Walk-forward no es un split único — es una **serie de splits deslizantes**. El protocolo correcto para aRGus es:

```
Entrenamiento 1: escenarios CTU-13 1-6  →  Validación: escenario 7
Entrenamiento 2: escenarios CTU-13 1-7  →  Validación: escenario 8
Entrenamiento 3: escenarios CTU-13 1-8  →  Validación: escenario 9
...
```

Un único split temporal (todo anterior a T entrena, todo posterior valida) es mejor que random k-fold, pero sigue siendo una sola observación. La serie deslizante da estimaciones de varianza del modelo — crucial para el paper.

**Riesgo identificado**: Si el dataset de reentrenamiento es pequeño (pocos escenarios nuevos), el walk-forward puede tener alta varianza. Documentar el número mínimo de escenarios requeridos para que el walk-forward sea estadísticamente válido.

**Test mínimo reproducible**:
```bash
make eval-walkforward \
  --dataset ctu13-full.parquet \
  --min-train-scenarios 6 \
  --output results/walkforward-report.json
# exit 1 si menos de 3 ventanas de validación disponibles
```

---

### Regla 2 — Golden Set inmutable: APROBADA con decisión de formato urgente

**Validación**: Correcta y la más crítica de las cinco. "Si se crea después, pierde su propiedad de inmutabilidad real" es exactamente el punto.

**Decisión urgente que el ADR no resuelve**: ¿En qué formato se almacena el golden set?

- **Opción A — Parquet**: eficiente, columnar, compatible con pandas/polars. Fácil de versionar con hash SHA-256 del fichero.
- **Opción B — pcap raw + etiquetas CSV separadas**: más cercano a la fuente, permite regenerar features si cambia el extractor. Más pesado.

**Recomendación**: Parquet con schema versionado + hash SHA-256 en el Makefile. Si el extractor de features cambia, el golden set se regenera con un proceso documentado y se versiona como `golden_set_v2.parquet` — nunca sobreescribiendo el anterior.

**Riesgo identificado**: Un golden set demasiado pequeño (< 10.000 flows) puede tener alta varianza en F1 — el guardrail del -2% puede dispararse por ruido estadístico, no por regresión real. Definir tamaño mínimo: propongo **≥ 50.000 flows balanceados** (50% benigno, 50% ataque, todas las familias CTU-13 representadas).

---

### Regla 3 — Guardrail -2%: APROBADA con asimetría Recall/F1

**Validación**: Correcta. El -2% como umbral es razonable.

**Matiz crítico**: F1 y Recall no son equivalentes en ciberseguridad. Una regresión en Recall (más falsos negativos = ataques no detectados) es **cualitativamente peor** que una regresión en Precision (más falsos positivos = más alertas benignas). El guardrail debe ser **asimétrico**:

| Métrica | Umbral de regresión | Justificación |
|---|---|---|
| F1 | -2 pp absolutos | Métrica global |
| **Recall** | **-0.5 pp absolutos** | Falso negativo = ataque que pasa |
| FPR | +3 pp absolutos | Falso positivo = ruido, molesto pero no letal |

**Riesgo identificado**: Si el guardrail es simétrico en F1, un modelo que mejora Precision pero baja Recall puede pasar el gate. Eso es inaceptable en un NDR.

**Test mínimo reproducible**:
```python
def check_guardrail(current, baseline):
    assert current['recall'] >= baseline['recall'] - 0.005, "RECALL REGRESSION — BLOCK"
    assert current['f1'] >= baseline['f1'] - 0.02, "F1 REGRESSION — BLOCK"
    assert current['fpr'] <= baseline['fpr'] + 0.03, "FPR REGRESSION — BLOCK"
    return "PROMOTE"
```

---

### Regla 4 — IPW + 5% exploración: APROBADA con advertencia de implementación

**Validación**: Correcta conceptualmente. El feedback loop es real y bien descrito.

**Advertencia práctica**: IPW requiere conocer la **propensity score** de cada flow — la probabilidad de que el modelo actual lo haya puntuado como ataque. Esto implica que el pipeline de inferencia debe **loggear los scores de confianza** de cada predicción, no solo la clase predicha. Si hoy el ml-detector solo emite 0/1, IPW no es implementable sin refactoring.

**Acción previa requerida antes de implementar ADR-040**: verificar que `ml-detector` emite `confidence_score` por flow en su salida ZeroMQ. Si no, añadirlo como prerequisito.

**Sobre el 5% de exploración**: en producción, "exploración forzada" significa revisar manualmente flows que el modelo marcó como benignos. En un hospital sin equipo de seguridad, ¿quién hace esa revisión? El ADR debe definir el **actor responsable** de la revisión de exploración — sin eso, la regla es un desideratum sin implementación real.

---

### Regla 5 — Competición de algoritmos: APROBADA con adición de criterio de corte

**Validación**: Correcta. No asumir XGBoost sin competirlo.

**Adición**: La competición necesita un **criterio de corte multicriterio**, no solo F1. Para aRGus, el perfil correcto es:

| Criterio | Peso | Justificación |
|---|---|---|
| Recall | 40% | Crítico — falsos negativos = ataques |
| F1 | 25% | Métrica global |
| Latencia de inferencia (p99) | 20% | Sin GPU, el modelo debe ser rápido |
| Tamaño del modelo serializado | 15% | 100 MB de RAM totales — el modelo debe caber |

El ganador no es el que tiene mejor F1 aislado, sino el que mejor cumple el perfil completo. Este criterio debe estar documentado **antes** de ejecutar la competición para evitar cherry-picking post-hoc.

---

### Pregunta abierta — Pipeline de evaluación: Interno vs CI/CD

**Mi posición**: **Opción A (interno, Makefile)** para la fase post-FEDER Año 1. Razones:

1. El pipeline de evaluación necesita acceso a pcaps y modelos que no deben subirse a GitHub Actions por tamaño y sensibilidad.
2. La reproducibilidad en Vagrant ya está demostrada — extender el mismo patrón es más seguro que introducir una nueva capa de infraestructura.
3. Post-FEDER Año 2, cuando el pipeline de reentrenamiento sea continuo, migrar a CI/CD tiene sentido. Pero en Año 1 es over-engineering.

`make retrain-eval` como target que orquesta walk-forward + guardrail + decisión PROMOTE/HOLD/REJECT + log firmado del resultado.

---

### Resumen ejecutivo — Veredicto Claude

| Regla | Veredicto | Cambio propuesto |
|---|---|---|
| 1 — Walk-forward | ✅ Aprobada | Aclarar que es serie deslizante, no split único |
| 2 — Golden Set | ✅ Aprobada | Definir formato (Parquet) y tamaño mínimo (≥50K flows) |
| 3 — Guardrail -2% | ✅ Aprobada con cambio | Guardrail asimétrico: Recall -0.5pp, F1 -2pp, FPR +3pp |
| 4 — IPW + exploración | ✅ Aprobada con prerequisito | Verificar que ml-detector emite confidence_score. Definir actor responsable de revisión |
| 5 — Competición | ✅ Aprobada | Añadir criterio multicriterio ponderado antes de ejecutar |
| Pipeline evaluación | Opción A | Makefile interno, migración CI/CD en Año 2 |

---

¿Lo guardo como fichero y luego me pasas el feedback del resto del Consejo?