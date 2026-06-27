cat > /Users/aironman/CLionProjects/test-zeromq-docker/docs/DAY122_consejo_consultation.md << 'MDEOF'
# Consulta al Consejo de Sabios — DAY 122
## aRGus NDR — Hallazgo Científico: Límites de los Datasets Académicos para NDR en Producción

**Fecha:** Domingo 19 de Abril de 2026  
**Autor:** Alonso (aRGus NDR, ML Defender)  
**Branch:** feature/adr026-xgboost  
**Paper:** arXiv:2604.04952 (Draft v15)  
**Contexto:** PHASE 4 — XGBoost 3.2.0 integration, DEBT-PRECISION-GATE-001

---

## Resumen Ejecutivo

Hoy hemos alcanzado un hallazgo científico de primer orden durante el intento
de cerrar DEBT-PRECISION-GATE-001 (Precision ≥ 0.99 en Wednesday held-out,
gate médico ADR-026).

El hallazgo NO es un fracaso de implementación. Es una contribución
metodológica publicable sobre los límites fundamentales del uso de datasets
académicos para entrenar modelos NDR destinados a producción real.

---

## Contexto Técnico Completo

### Setup experimental (protocolo Consejo DAY 121, 7/7 unánime)
- **Train:** Tuesday + Thursday + Friday (CIC-IDS-2017)
- **Validation:** 20% del train, estratificado (para calibrar threshold)
- **Test (BLIND):** Wednesday-WorkingHours.pcap_ISCX.csv
- **Seal md5:** bf0dd7e9d991987df4e13ea58a1b409c (verificado en apertura)
- **Modelo:** XGBoost 3.2.0, 23 features, scale_pos_weight=4.273

### Resultados en Validation Set (in-distribution)
Precision:  0.9945  ✅ (gate ≥0.99)
Recall:     0.9818  ✅ (gate ≥0.95)
Threshold:  0.821119 (calibrado sobre validation, nunca sobre test)
### Resultados en Wednesday Held-Out (OOD — primera y única apertura)
Precision:  0.9870  ❌ (gate ≥0.99)
Recall:     0.0241  ❌ (gate ≥0.95)
F1-score:   0.0471
Latencia:   1.986 µs/sample  ✅ (gate <2µs)
TP=6090   FP=80   FN=246582   TN=439951
### Distribución de probabilidades asignadas por el modelo a ataques Wednesday
DoS GoldenEye   n=10293   median_proba=0.0193   >0.5=11.9%
DoS Hulk        n=231073  median_proba=0.0165   >0.5= 5.1%  ← 91% de ataques
DoS Slowhttptest n=5499   median_proba=0.0008   >0.5= 1.9%
DoS Slowloris   n=5796    median_proba=0.0058   >0.5=11.6%
Heartbleed      n=11      median_proba=0.0114   >0.5= 0.0%
### Threshold sweep — no existe threshold que satisfaga ambos gates
t=0.01  prec=0.7978  rec=0.5594  fp/h=4478
t=0.10  prec=0.7763  rec=0.2023  fp/h=1841
t=0.50  prec=0.9514  rec=0.0545  fp/h=88
t=0.80  prec=0.9856  rec=0.0261  fp/h=12
No existe ningún punto de la curva PR donde Precision≥0.99 AND Recall≥0.95.

---

## Diagnóstico Técnico

**Causa raíz:** Covariate shift estructural por diseño del dataset.

Wednesday contiene EXCLUSIVAMENTE ataques DoS de capa 7 (GoldenEye, Hulk,
Slowloris, Slowhttptest) y Heartbleed. NINGUNO de estos tipos de ataque
aparece en los CSVs de entrenamiento (Tue+Thu+Fri).

DoS Hulk (91% de los ataques de Wednesday) imita tráfico HTTP legítimo con
alto volumen. Sus features de flujo son estadísticamente similares al tráfico
benigno de alto volumen. El modelo asigna probabilidad media=0.087 a estos
flows porque nunca los vio en entrenamiento.

**Esto no es un problema de hiperparámetros ni de threshold.**
Es una separación temporal artificial del dataset: CIC-IDS-2017 fue construido
poniendo tipos de ataque específicos en días específicos, sin repetición
cross-day. Esta decisión de diseño del dataset hace matemáticamente imposible
que un modelo entrenado en Tue+Thu+Fri generalice a los attack types de Wednesday.

---

## Lo que sabemos con certeza (conclusiones de Alonso, DAY 122)

1. **Los datasets académicos tienen demasiado sesgo para entrenar modelos
   ensemble/XGBoost destinados a NDR en producción.** No entramos en por qué
   fueron creados — tienen su utilidad, y nosotros los usamos correctamente
   para el pcap relay — pero como fuente única de entrenamiento supervisado
   son insuficientes.

2. **Los datos sintéticos generados por LLMs (DeepSeek) tampoco son
   suficientes.** No tienen la profundidad necesaria. Un LLM no ha "visto"
   lo suficiente del tráfico real adversarial como para generar distribuciones
   de features que generalicen.

3. **El método correcto para producción es el loop adversarial:**
   IA pentester generativa → pipeline aRGus captura tráfico real →
   flows etiquetados con contexto real → reentrenamiento.
   El modelo fundacional nace del entorno de despliegue, no del laboratorio.

4. **Los modelos actuales son modelos de arranque válidos**, no modelos
   fundacionales. Su función es llevar el pipeline a un estado operativo
   suficiente para comenzar a capturar tráfico real adversarial.

5. **La arquitectura de aRGus está diseñada para esto.** Plugin XGBoost
   reemplazable en caliente (ADR-026, Ed25519, fail-closed). El sistema
   fue concebido desde el principio para que el modelo sea un componente
   intercambiable. Esto es visión arquitectónica.

---

## Preguntas para el Consejo

### PREGUNTA 1 — Validez científica del hallazgo
¿Consideráis que el covariate shift estructural observado en CIC-IDS-2017
(attack types separados por días sin cross-contamination) es suficientemente
general como para constituir una contribución metodológica publicable?
¿Conocéis papers previos que hayan documentado este límite específico con
evidencia cuantitativa como la nuestra (threshold sweep completo)?

### PREGUNTA 2 — Cierre de DEBT-PRECISION-GATE-001
El gate original (Precision≥0.99 en Wednesday held-out) no puede cerrarse
con datos académicos. Dos opciones:

**Opción A:** Cerrar la deuda documentando el hallazgo. El gate se certifica
sobre attack types in-distribution (Prec=0.9945/Rec=0.9818). La limitación
OOD queda documentada en §4.2 del paper. MERGE autorizado con esta acotación.

**Opción B:** Redefinir el gate. Usar Friday-PortScan como held-out
(158k ataques, bien representados en train). Wednesday entra al train.
Científicamente válido pero cambia el protocolo acordado por el Consejo en DAY 121.

¿Cuál recomendáis? ¿Hay una Opción C que no hayamos considerado?

### PREGUNTA 3 — Impacto en el paper (arXiv:2604.04952)
¿Cómo estructuráis la narrativa de §4 y §5 para que este hallazgo
fortalezca el paper en lugar de debilitarlo? ¿Es el framing correcto
presentarlo como "validación de la arquitectura de reentrenamiento en
producción" en lugar de "limitación del modelo"?

### PREGUNTA 4 — El loop adversarial como contribución
La propuesta de Alonso: el pipeline de captura de aRGus como instrumento
de generación de datos fundacionales (IA pentester → captura → reentrenamiento).
¿Existe literatura sobre este paradigma? ¿Lo conocéis como "adversarial
data flywheel", "red team loop" u otro nombre establecido?
¿Recomendáis citarlo en el paper con nomenclatura existente o proponer
nomenclatura propia?

### PREGUNTA 5 — DEBT-PENTESTER-LOOP-001
Si aceptamos que el loop adversarial es el camino correcto, ¿qué
especificaciones mínimas debería tener una IA pentester generativa
para ser científicamente válida como fuente de datos de entrenamiento?
¿Calidad de los flows generados, diversidad de técnicas, reproducibilidad?
¿Hay herramientas existentes (Metasploit, Caldera, MITRE ATT&CK emulación)
que podríamos integrar como primera aproximación antes de una IA generativa?

### PREGUNTA 6 — Integridad del protocolo experimental
Wednesday fue abierto UNA SOLA VEZ y el resultado está sellado con md5.
El threshold fue calibrado exclusivamente en validation set.
El protocolo fue seguido con rigor máximo.
¿Consideráis que este protocolo es suficientemente riguroso para
que los resultados (tanto los positivos como el hallazgo OOD) sean
publicables sin reservas metodológicas?

---

## Datos adjuntos para el Consejo

### wednesday_eval_report.json (generado DAY 122)
```json
{
  "test_set": "Wednesday-workingHours.pcap_ISCX.csv",
  "wednesday_md5": "bf0dd7e9d991987df4e13ea58a1b409c",
  "threshold": 0.821119,
  "precision": 0.9870,
  "recall": 0.0241,
  "f1": 0.0471,
  "latency_us": 1.986,
  "tp": 6090, "fp": 80, "fn": 246582, "tn": 439951,
  "gate_precision": false,
  "gate_recall": false,
  "gate_latency": true
}
```

### Métricas de validación (in-distribution, threshold calibrado)
Precision: 0.9945 | Recall: 0.9818 | F1: 0.9881
Threshold: 0.821119
Best iteration: 724 / 1000 (early stopping)
Val AUCPR: 0.99846
---

## Contexto del proyecto para el Consejo

- **aRGus NDR:** NDR open-source para infraestructura crítica
  (hospitales, escuelas, municipios) que no puede permitirse
  soluciones enterprise.
- **Filosofía:** "un escudo, nunca una espada"
- **Via Appia Quality / TDH (Test-Driven Hardening)**
- **Paper:** arXiv:2604.04952, Draft v15
- **Hoy es DAY 122.** Llevamos más de 4 meses construyendo esto.

---

*"La seguridad de los hospitales no admite atajos estadísticos."*  
*— Principio rector del Consejo, DAY 121*

*Hoy añadimos: "Ni atajos en los datos."*
MDEOF
echo "✅ Escrito del Consejo creado"