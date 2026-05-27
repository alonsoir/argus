# RF vs XGBoost — Tabla Comparativa (DAY 121)

## Metodología

- **Evaluación:** test split 20% con `random_state=42`, `stratify=y`
- **Latencia:** µs/sample en CPU (host macOS, no VM) — referencial
- **RF level1:** pkl no localizado en producción (N/A) — pendiente auditoría
- **Nota gate ransomware:** RF F1=1.0 sobre 3000 muestras sintéticas indica overfitting (entrenado sin split). XGBoost con split honesto obtiene F1=0.9932. Gate aprobado con tolerancia ±0.01.

## Tabla

| Detector       | Model   | F1     | Precision | ROC-AUC | Latencia (µs/sample) | Dataset             |
|----------------|---------|--------|-----------|---------|----------------------|---------------------|
| level1_attack  | XGBoost | 0.9930 | 0.9875    | 1.0000  | 1.31                 | CIC-IDS-2017 real   |
| level1_attack  | RF      | N/A    | N/A       | N/A     | N/A                  | CIC-IDS-2017 real ¹ |
| ddos           | XGBoost | 1.0000 | 1.0000    | 1.0000  | 0.15                 | DeepSeek synthetic  |
| ddos           | RF      | 1.0000 | 1.0000    | N/A     | 6.12                 | DeepSeek synthetic  |
| ransomware     | XGBoost | 0.9932 | 0.9932    | ~1.000  | 2.09                 | DeepSeek synthetic  |
| ransomware     | RF      | 1.0000 | 1.0000    | N/A     | 12.93                | DeepSeek synthetic  |

¹ RF level1 pkl no encontrado en producción — pendiente auditoría backlog.

## Observaciones clave

**Latencia:** XGBoost es 4–6× más rápido que RF en inferencia (DDoS: 0.15 vs 6.12 µs/sample, Ransomware: 2.09 vs 12.93 µs/sample). Relevante para entornos de alta frecuencia de paquetes.

**Calidad en dataset real (CIC-IDS-2017):** XGBoost F1=0.9930, Precision=0.9875 — por debajo del gate médico (Precision≥0.99). Requiere revisión de features o re-entrenamiento con más epochs. Ver §4.1.

**Datasets sintéticos:** F1=1.0 en DDoS y RF Ransomware son artefactos de la baja variabilidad del dataset sintético, no indicadores de generalización real. Ver §4.2 con limitaciones explícitas.

---

## Borrador §4 paper (separación real vs sintético)

### §4.1 Evaluación sobre dataset real — CIC-IDS-2017

El detector de nivel 1 (`level1_attack_detector`) fue entrenado y evaluado sobre el dataset público CIC-IDS-2017 [ref], que contiene 2.83M flujos de red capturados en condiciones controladas de laboratorio con tráfico real de red. Se emplearon 23 features LEVEL1 (ver Tabla X) extraídas directamente de los CSVs sin transformación adicional salvo imputación de infinitos y NaN a 0.

El modelo XGBoost alcanza F1=0.9930 y Precision=0.9875 sobre el split de test (20%, 566k flujos). La detección de FTP-Patator y SSH-Patator supera el 99.9% de recall. La Precision=0.9875 queda por debajo del gate médico (≥0.99) definido en ADR-026; este gap es objeto de trabajo futuro en la rama `feature/adr026-xgboost`.

**Limitación conocida:** CIC-IDS-2017 es un dataset de laboratorio. Los patrones de tráfico real en hospitales y municipios pueden diferir significativamente. Una evaluación en entorno de producción real requiere DPIA (LOPD/GDPR) y está planificada para Q3 2026.

### §4.2 Evaluación sobre datasets sintéticos — DDoS y Ransomware

Los detectores de nivel 2 (DDoS) y nivel 3 (Ransomware) fueron entrenados sobre datasets sintéticos generados mediante LLM (DeepSeek), dada la ausencia de datasets públicos etiquetados con las features específicas requeridas por la arquitectura plugin de aRGus.

**DDoS** (50.000 flujos, 10 features): XGBoost y RF alcanzan F1=Precision=1.0000. Este resultado refleja la baja variabilidad intrínseca del dataset sintético y **no debe interpretarse como rendimiento en producción real**.

**Ransomware** (3.000 flujos combinados network+files+processes, 10 features): XGBoost F1=0.9932 con split honesto train/test. El RF obtiene F1=1.0 al ser evaluado sin split (overfitting sobre 3k muestras). XGBoost generaliza mejor.

**Limitación crítica §4.2:** Los datasets sintéticos no capturan la distribución real de tráfico DDoS ni el comportamiento real de ransomware en red hospitalaria. Los modelos de §4.2 son un punto de partida funcional. Su validación en entorno real es trabajo futuro obligatorio antes de cualquier despliegue en producción.
