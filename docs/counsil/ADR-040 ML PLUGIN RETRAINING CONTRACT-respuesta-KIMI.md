## Kimi — Respuesta al Consejo de Sabios — ADR-040

*Evaluación bajo criterios de reproducibilidad científica, seguridad operacional y viabilidad institucional para hospitales y municipios.*

---

### Evaluación de las 5 Reglas

**Veredicto general: Las 5 reglas son arquitectónicamente correctas y científicamente fundadas. Apruebo el ADR con modificaciones en la Regla 3 (guardrail) y una decisión arquitectónica sobre el pipeline de evaluación.**

---

#### Regla 1 — Walk-forward obligatorio

**Hipótesis:** El eje temporal en datos de red no es ignorable. La correlación intra-sesión viola la independencia que asume k-fold.

**Veredicto: APROBADA sin modificaciones.**

**Justificación científica:** En CTU-13, un flujo de Neris puede generar 10.000 paquetes en una ventana de 30 minutos. Si k-fold mezcla paquetes de la misma sesión entre train y test, el modelo "ve" patrones de comportamiento futuro durante el entrenamiento. Esto es **data leakage temporal**, no un error de implementación.

**Test de cumplimiento reproducible:**

```python
# test_walk_forward.py — gate CI obligatorio
import pandas as pd
import hashlib

def validate_walk_forward(df: pd.DataFrame, split_date_col: str) -> bool:
    """
    Falla explícitamente si detecta mezcla temporal.
    """
    if split_date_col not in df.columns:
        raise ValueError(f"Columna temporal '{split_date_col}' no encontrada. "
                        f"Split aleatorio está PROHIBIDO por ADR-040 Regla 1.")
    
    # Verificar que no hay overlap temporal entre folds
    folds = df.groupby('fold_id')[split_date_col]
    for i, (fold_id, dates) in enumerate(folds):
        max_prev = df[df['fold_id'] < fold_id][split_date_col].max()
        if dates.min() < max_prev:
            raise ValueError(f"Fold {fold_id} contiene datos anteriores a fold {fold_id-1}. "
                           f"Walk-forward violado.")
    
    return True
```

**Nota:** El parámetro `--split-date` debe ser **obligatorio posicional**, no opcional. Un script que no recibe fecha de split debe fallar con exit code 2 (uso incorrecto), no ejecutar un default aleatorio.

---

#### Regla 2 — Golden Set inmutable, versionado

**Hipótesis:** Un golden set creado *después* de ver los resultados del modelo es un test set contaminado.

**Veredicto: APROBADA con condición de creación inmediata.**

**Justificación científica:** Esto es equivalente al principio de **preregistro** en ciencia experimental. El golden set debe existir antes de que el primer experimento de reentrenamiento se ejecute. Si no, existe la tentación (incluso inconsciente) de seleccionar ejemplos que "el modelo ya detecta bien".

**Condición:** El golden set debe crearse **ahora**, durante el DAY actual, no post-FEDER. Usad el CTU-13 Neris actual como semilla. Congelad 10.000 flows representativos con sus etiquetas, calculad el SHA-256, y commitead el hash en `docs/adr/ADR-040-GOLDEN-SET.md`.

**Estructura propuesta:**

```
data/golden/
  v1.0.0/
    golden_set.parquet          # datos
    golden_set.sha256           # hash
    manifest.json               # metadatos: fuente, fecha congelación, ataques cubiertos
    README.md                   # instrucciones de uso
```

**Manifest obligatorio:**
```json
{
  "version": "1.0.0",
  "frozen_at": "2026-04-28T00:00:00Z",
  "sha256": "a3f5...",
  "source": "CTU-13 Scenario 1 (Neris)",
  "flows_total": 10000,
  "attacks_covered": ["Neris", "Rbot", "Murbo"],
  "created_by": "Consejo de Sabios DAY 133",
  "next_review": "2027-04-28"
}
```

---

#### Regla 3 — Guardrail del −2%

**Hipótesis:** Un guardrail fijo del −2% es mejor que la ausencia de guardrail, pero puede ser demasiado laxo para Recall y demasiado estricto para FPR.

**Veredicto: APROBADA con modificación de umbrales asimétricos.**

**Análisis de riesgo:**

| Métrica | Umbral propuesto | Problema | Umbral recomendado |
|---------|-----------------|----------|-------------------|
| F1 | −2 pp | Aceptable para variaciones normales | **−1.5 pp** (más estricto) |
| Recall | −1 pp | Correcto: un falso negativo es un ataque no detectado | **−0.5 pp** (más estricto) |
| FPR | +2 pp | Demasiado laxo: +2% FPR en un hospital significa miles de alertas diarias falsas | **+0.5 pp** (más estricto) |

**Justificación institucional:** En un hospital con 10.000 dispositivos IoT médicos, una FPR del 0.02% (actual) vs 2.02% (guardrail propuesto) es la diferencia entre 2 alertas diarias reales y 200 alertas diarias falsas. El equipo de seguridad del hospital desactivará el sistema antes de la segunda semana.

**Nuevo guardrail propuesto:**

| Métrica | Umbral de regresión |
|---------|---------------------|
| F1 | −1.5 pp absolutos |
| Recall | −0.5 pp absolutos |
| FPR | +0.5 pp absolutos |

**Criterio adicional:** Si Recall cae **cualquier cantidad** (incluso −0.1 pp) para una clase de ataque específica (ej. "Neris"), el guardrail debe activarse. La detección por clase no puede degradarse.

**Implementación del gate:**

```bash
#!/bin/bash
# guardrail.sh — consumido por ed25519_sign()

GOLDEN_F1=$(jq '.f1' golden_metrics.json)
GOLDEN_RECALL=$(jq '.recall' golden_metrics.json)
GOLDEN_FPR=$(jq '.fpr' golden_metrics.json)

CANDIDATE_F1=$(jq '.f1' candidate_metrics.json)
CANDIDATE_RECALL=$(jq '.recall' candidate_metrics.json)
CANDIDATE_FPR=$(jq '.fpr' candidate_metrics.json)

# Umbral asimétrico
MAX_F1_DROP=0.015
MAX_RECALL_DROP=0.005
MAX_FPR_RISE=0.005

python3 << 'PYEOF'
import sys, json

with open('golden_metrics.json') as f: g = json.load(f)
with open('candidate_metrics.json') as f: c = json.load(f)

fail = False
if c['f1'] < g['f1'] - 0.015:
    print(f"FAIL: F1 regresion {g['f1']:.4f} -> {c['f1']:.4f}", file=sys.stderr)
    fail = True
if c['recall'] < g['recall'] - 0.005:
    print(f"FAIL: Recall regresion {g['recall']:.4f} -> {c['recall']:.4f}", file=sys.stderr)
    fail = True
if c['fpr'] > g['fpr'] + 0.005:
    print(f"FAIL: FPR rise {g['fpr']:.4f} -> {c['fpr']:.4f}", file=sys.stderr)
    fail = True

# Check per-class recall
for cls in g.get('per_class_recall', {}):
    if c['per_class_recall'][cls] < g['per_class_recall'][cls] - 0.001:
        print(f"FAIL: Recall class {cls} regresion", file=sys.stderr)
        fail = True

sys.exit(1 if fail else 0)
PYEOF
```

---

#### Regla 4 — IPW + 5% exploración forzada

**Hipótesis:** El feedback loop es un riesgo real en sistemas de detección que se reentrenan con sus propias predicciones.

**Veredicto: APROBADA con condición de viabilidad operativa.**

**Justificación científica:** Esto es una instanciación del problema de **covariate shift** y **label noise**. Si el modelo actual etiqueta incorrectamente un nuevo ataque como "benigno", y ese dato entra al siguiente ciclo de entrenamiento, el modelo refuerza su error. IPW (Inverse Propensity Weighting) corrige el sesgo de selección; la exploración forzada garantiza que el modelo no se vuelve ciego a patrones no vistos.

**Condición de viabilidad:** El 5% de exploración forzada requiere un **oráculo de etiquetado**. En un hospital, esto significa que un analista de seguridad debe revisar manualmente el 5% de los flows marcados como benignos. Si el hospital no tiene analista dedicado, esta regla es **inoperable**.

**Alternativa para entornos sin analista:**

```python
# Opción B: oráculo externo automatizado
# Usar un segundo modelo (diferente arquitectura) como oráculo débil
# Ejemplo: si RandomForest dice "benigno" pero un autoencoder reconstrucción-error > threshold,
# forzar etiqueta "sospechoso" y enviar a cola de revisión prioritaria

def exploration_forced(flow, primary_model, oracle_model, threshold=0.05):
    primary_label = primary_model.predict(flow)
    if primary_label == "benigno" and random.random() < threshold:
        oracle_score = oracle_model.reconstruction_error(flow)
        if oracle_score > oracle_model.threshold:
            return "sospechoso_oracle"  # enviar a revisión prioritaria
    return primary_label
```

**Recomendación:** Mantened el 5% de exploración forzada como requisito del ADR, pero permitid que el "oráculo" sea configurable: analista humano (ideal), modelo secundario (fallback), o servicio externo (API de threat intelligence).

---

#### Regla 5 — Competición de algoritmos

**Hipótesis:** Asumir XGBoost sin evidencia comparativa es sesgo de confirmación.

**Veredicto: APROBADA con condición de latencia de inferencia como métrica de decisión.**

**Justificación científica:** En benchmarks académicos (Kaggle, etc.), XGBoost, CatBoost y LightGBM tienen rendimiento similar (diferencias <1% en AUC). Sin embargo, en NDR la latencia de inferencia es crítica: un modelo que tarda 50 ms por paquete no es viable para 1 Gbps.

**Métricas de competición obligatorias:**

| Métrica | Peso en decisión | Justificación |
|---------|-----------------|---------------|
| F1 (golden set) | 30% | Precisión global |
| Recall (per-clase mínimo) | 30% | No perder ataques |
| Latencia p99 inferencia | 25% | Tiempo real en pipeline |
| Tamaño modelo (MB) | 10% | Memoria en ARM/RPi |
| Tiempo entrenamiento | 5% | Iteración rápida en desarrollo |

**Nota:** Si CatBoost supera a XGBoost en F1 pero el modelo es 10× más grande, XGBoost gana para aRGus porque debe caber en RPi4.

---

### Pregunta arquitectónica: Pipeline de evaluación interno vs CI/CD externo

**Hipótesis:** La decisión entre componente interno y CI/CD externo define la reproducibilidad, la seguridad de los datos de entrenamiento y la trazabilidad de decisiones.

**Veredicto: Opción B (CI/CD externo) como sistema de registro, Opción A (componente interno) como motor de ejecución.**

**Arquitectura híbrida propuesta:**

```
┌─────────────────────────────────────────────────────────────┐
│  CI/CD EXTERNO (GitHub Actions / GitLab CI)                 │
│  ─────────────────────────────────────────                  │
│  • Trigger: PR con nuevo plugin candidato                   │
│  • Registro: decisiones PROMOTE/HOLD/REJECT en PR comments  │
│  • Trazabilidad: histórico de métricas por commit           │
│  • Seguridad: NO tiene acceso a datos de entrenamiento      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  COMPONENTE INTERNO (Vagrant VM / entorno aislado)          │
│  ─────────────────────────────────────────────────          │
│  • Ejecución: walk-forward, golden set, competición         │
│  • Datos: acceso a CTU-13, capturas internas (NO en repo)   │
│  • Resultados: métricas JSON exportadas al CI               │
│  • Firma: ed25519_sign() solo si guardrail pasa             │
└─────────────────────────────────────────────────────────────┘
```

**Justificación:**

1. **Seguridad de datos:** Los datos de entrenamiento (capturas de red de hospitales) nunca deben estar en GitHub. El componente interno ejecuta en un entorno aislado (VM local, air-gapped).
2. **Reproducibilidad:** El componente interno usa los mismos binarios que producción (`make test-all`), garantizando que las métricas reflejan el comportamiento real.
3. **Trazabilidad:** El CI externo registra quién aprobó qué, cuándo, y por qué. Esto es auditabilidad para FEDER y para hospitales.

**Interfaz entre ambos:**

```yaml
# .github/workflows/plugin-evaluation.yml
name: Plugin Evaluation Gate

on:
  pull_request:
    paths:
      - 'plugins/**'

jobs:
  evaluate:
    runs-on: self-hosted  # runner en la VM de dev, no en GitHub cloud
    steps:
      - uses: actions/checkout@v4
      
      - name: Run evaluation pipeline
        run: |
          make evaluate-plugin PLUGIN=candidate_xgboost_v3
          # Esto ejecuta en la VM local, con acceso a datos
      
      - name: Upload metrics
        uses: actions/upload-artifact@v4
        with:
          name: evaluation-metrics
          path: dist/evaluation/metrics.json
      
      - name: Guardrail check
        run: |
          ./scripts/guardrail.sh dist/evaluation/metrics.json
          # Falla el PR si no pasa
      
      - name: Comment PR with results
        uses: actions/github-script@v7
        with:
          script: |
            const metrics = require('./dist/evaluation/metrics.json');
            const body = `## Plugin Evaluation Results\n| Metric | Golden | Candidate | Delta |\n|---|---|---|---|\n| F1 | ${metrics.golden.f1} | ${metrics.candidate.f1} | ${metrics.delta.f1} |\n| Recall | ${metrics.golden.recall} | ${metrics.candidate.recall} | ${metrics.delta.recall} |\n| FPR | ${metrics.golden.fpr} | ${metrics.candidate.fpr} | ${metrics.delta.fpr} |\n\n**Verdict:** ${metrics.verdict}`;
            github.rest.issues.createComment({...context.repo, issue_number: context.issue.number, body});
```

**Ventaja clave:** El CI externo no ejecuta el modelo; solo **orquesta** la ejecución en el entorno interno y **registra** el resultado. Los datos nunca salen de la VM.

---

### Deudas técnicas generadas por ADR-040

| ID | Descripción | Prioridad | Owner |
|----|-------------|-----------|-------|
| DEBT-GOLDEN-SET-001 | Crear golden set v1.0.0 con CTU-13, congelar, hashear | 🔴 P0 | Consejo DAY 134 |
| DEBT-WALK-FORWARD-001 | Implementar script `--split-date` con fallo explícito | 🔴 P0 | Post-FEDER |
| DEBT-GUARDRAIL-001 | Implementar guardrail asimétrico (−1.5/−0.5/+0.5) | 🔴 P0 | Post-FEDER |
| DEBT-IPW-EXPLORATION-001 | Pipeline IPW + oráculo configurable | ⏳ P1 | Año 1 |
| DEBT-ALGO-COMPETITION-001 | Competición XGBoost/CatBoost/LightGBM/RF | ⏳ P1 | Año 1 |
| DEBT-EVALUATION-ARCH-001 | Implementar arquitectura híbrida CI interno/externo | ⏳ P1 | Post-FEDER |

---

### Resumen de posiciones — Kimi

| Aspecto | Veredicto | Justificación clave |
|---------|-----------|---------------------|
| **Regla 1 (walk-forward)** | Aprobada sin modificación | Data leakage temporal es un error metodológico grave en datos de red |
| **Regla 2 (golden set)** | Aprobada, crear **ahora** | Preregistration obligatorio; post-hoc golden set es contaminado |
| **Regla 3 (guardrail)** | Aprobada con umbrales asimétricos | FPR +2% mata un sistema en hospital; Recall −1% es inaceptable |
| **Regla 4 (IPW+5%)** | Aprobada con oráculo configurable | 5% manual es inoperable en hospitales sin analista |
| **Regla 5 (competición)** | Aprobada con latencia p99 como métrica de decisión | En NDR, la latencia es tan crítica como el F1 |
| **Pipeline evaluación** | Arquitectura híbrida: CI externo orquesta, componente interno ejecuta | Seguridad de datos + reproducibilidad + trazabilidad |

**Moción:** Propongo que el Consejo ordene la creación del golden set v1.0.0 en el DAY 134 como acción inmediata, antes de cualquier otro trabajo técnico. Sin golden set congelado, ADR-040 no tiene fundamento sobre el que ejecutarse.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*