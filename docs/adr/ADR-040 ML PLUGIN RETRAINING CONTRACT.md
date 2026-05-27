# ADR-040 — ML Plugin Retraining Contract (v2)

| Campo        | Valor                                                                 |
|--------------|-----------------------------------------------------------------------|
| **Estado**   | PROPUESTO v2 — post-Consejo de Sabios 2026-04-28                     |
| **Fecha**    | 2026-04-28                                                            |
| **Autor**    | Alonso Isidoro Román                                                  |
| **Versión anterior** | v1 — propuesto 2026-04-28, previo a Consejo                  |
| **Prioridad** | BACKLOG — implementación post-FEDER, pre-ADR-026 Año 1              |
| **Consejo de Sabios** | Consultado 2026-04-28, 8/8 modelos (Claude, ChatGPT-5, DeepSeek, Gemini, Grok, Mistral, Qwen, Kimi). Veredicto: APROBADO con 17 enmiendas. |
| **Referencias** | ADR-025 (Plugin Integrity Verification), ADR-026 (P2P Fleet Federated), ADR-041 (Hardware Acceptance Metrics), BACKLOG-FEDER-001 |
| **Referencia externa** | Mercadona Tech Search Engine Playbook — José Ramón Pérez Agüera (gemba.es, abril 2026) |

---

## Contexto

aRGus NDR incluye un plugin de clasificación de tráfico de red basado en RandomForest (F1=0.9985, CTU-13 Neris). En el Año 1 post-FEDER (ADR-026), está prevista la evolución hacia plugins XGBoost con capacidad de reentrenamiento periódico.

El reentrenamiento continuo introduce tres riesgos sistémicos:

1. **Catastrophic forgetting**: el modelo olvida ataques clásicos al aprender variantes nuevas.
2. **Feedback loop**: el modelo aprende que "lo que ya detectó es ataque" y se vuelve ciego a variantes no vistas.
3. **Regresión silenciosa**: una nueva versión del plugin pasa a producción con peor rendimiento sin que nadie lo detecte.

Este ADR formaliza el contrato que cualquier proceso de reentrenamiento debe cumplir antes de que un plugin nuevo sea firmado con Ed25519 (ADR-025) y desplegado.

---

## Arquitectura del pipeline de evaluación

**Decisión (consenso 6/7 del Consejo): enfoque híbrido.**

El núcleo de evaluación vive en el repositorio como scripts versionados. La orquestación puede ejecutarse localmente (Vagrant/Makefile) o en CI (GitHub Actions). Son el mismo código con dos puntos de entrada — no dos sistemas paralelos.

```
eval-pipeline/                    ← versionado en repo
├── walk_forward_split.py
├── evaluate_against_golden.py
├── check_guardrails.py
├── compute_ipw_weights.py
├── detect_concept_drift.py
└── run_algorithm_competition.py
        ↓
Ejecución local:   make retrain-eval PLUGIN=candidate_v3.ubj
Ejecución CI:      GitHub Actions workflow (llama a los mismos scripts)
Gate de firma:     make prod-sign invoca check_guardrails.py — si exit ≠ 0, no firma
```

**Justificación:**
- Scripts en repo → reproducibilidad local, trazabilidad entre modelo y criterio de evaluación, sin dependencia de infraestructura externa.
- CI → histórico auditable de cada decisión PROMOTE/HOLD/REJECT, bloqueo de merge automático, imposibilidad de bypass manual en entornos distribuidos.
- Datos sensibles (pcaps, modelos) no suben a GitHub — CI accede a ellos via secrets o volúmenes montados.

**Makefile targets requeridos:**
```bash
make retrain-eval PLUGIN=candidate.ubj   # walk-forward + golden set + guardrail → PROMOTE/HOLD/REJECT
make golden-set-eval ARCH=$(uname -m)    # solo golden set, para test de hardware (ADR-041)
make algo-competition                    # competición algoritmos (una sola vez pre-FEDER)
```

---

## Regla 1 — Walk-forward obligatorio (nunca random k-fold)

### Especificación

Walk-forward es una **serie de splits deslizantes**, no un único corte temporal. El protocolo correcto para aRGus:

```
Entrenamiento 1: escenarios CTU-13 1-6  →  Validación: escenario 7
Entrenamiento 2: escenarios CTU-13 1-7  →  Validación: escenario 8
Entrenamiento 3: escenarios CTU-13 1-8  →  Validación: escenario 9
...
```

Mínimo 3 ventanas de validación. Con menos, la varianza de la estimación es inaceptable — el script debe fallar con exit 1 si no hay suficientes ventanas.

El split debe hacerse sobre el campo `timestamp_first_packet` de cada flow, **ordenado explícitamente** antes de partir. Con múltiples fuentes de pcap, la concatenación sin ordenar temporal puede hacer el split no determinista.

```python
# walk_forward_split.py
flows = load_flows(dataset_path)
flows = flows.sort_values('timestamp_first_packet')  # CRÍTICO: ordenar antes
splits = generate_walk_forward_splits(flows, min_windows=3)
```

### Detección de concept drift (enmienda Qwen)

Antes de entrenar cada ventana, verificar si la distribución de features cambia significativamente entre train y validación. Indica que el concepto mismo ha cambiado (nuevas variantes de ataque, nuevos protocolos).

```python
# detect_concept_drift.py
from scipy.stats import ks_2samp

def detect_concept_drift(train_data, val_data, threshold=0.15):
    p_values = [ks_2samp(train_data[f], val_data[f]).pvalue
                for f in FEATURE_COLUMNS]
    # Corrección de Bonferroni para tests múltiples
    significant_drifts = sum(p < 0.05 / len(FEATURE_COLUMNS) for p in p_values)
    return significant_drifts / len(FEATURE_COLUMNS) > threshold
```

Si drift detectado: el resultado de la ventana se marca como `DRIFT_DETECTED`. El plugin candidato puede seguir evaluándose pero requiere revisión manual antes de promoción. No bloquea automáticamente — documenta.

### Criterio de cumplimiento

El script `walk_forward_split.py` debe recibir `--split-field timestamp_first_packet` y fallar explícitamente si se intenta usar split aleatorio o si hay menos de 3 ventanas disponibles.

---

## Regla 2 — Golden Set inmutable, versionado desde el principio

### Especificación

Antes de entrenar el primer plugin XGBoost, debe existir en el repositorio un golden set versionado:

- **Formato**: Parquet con schema versionado. Eficiente, columnar, compatible con pandas/polars, fácil de versionar con hash SHA-256.
- **Tamaño mínimo**: ≥ 50.000 flows.
- **Distribución**: 70% tráfico benigno real / 30% ataques. Refleja la distribución real en redes hospitalarias. Todas las familias CTU-13 canónicas representadas (Neris, Rbot, Murlo mínimo).
- **Inmutabilidad operativa**: ningún proceso de reentrenamiento puede modificarlo. Solo lectura.
- **Hash SHA-256 en Makefile**: verificado en cada uso antes de evaluar.
- **Hash embebido en el plugin firmado** (enmienda Gemini): el ml-detector en runtime puede verificar que el modelo que está cargando fue validado contra el golden set correcto.

```bash
# Verificación obligatoria antes de cualquier evaluación
GOLDEN_HASH=$(sha256sum golden/v1/golden_set_v1.parquet | cut -d' ' -f1)
if [ "$GOLDEN_HASH" != "$EXPECTED_HASH" ]; then
    echo "GOLDEN SET TAMPERED — ABORT"
    exit 1
fi
```

### Proceso de evolución controlada (enmienda Qwen)

La inmutabilidad es operativa, no eterna. Cuando emergen nuevos vectores de ataque o cambian los protocolos del entorno:

1. Propuesta: nuevo golden set candidato en `golden/v2-candidate/`
2. Revisión: Consejo de Sabios valida cobertura y representatividad
3. Deprecación: `golden/v1/` marcado como deprecated con fecha límite (mínimo 6 meses de solapamiento)
4. Migración: todos los plugins en producción re-evaluados contra v2
5. Activación: `golden/v2/` se convierte en activo; v1 se archiva (nunca se borra)

Registro en `docs/GOLDEN-SET-REGISTRY.md`:
```
v1: <sha256> (2026-04-28) — CTU-13 Neris/Rbot/Murlo baseline, 50K flows, 70/30
v2: <sha256> (TBD)        — +variantes ransomware +patrones DICOM
```

### Criterio de cumplimiento

El golden set debe existir **antes** de que haya nada que validar contra él. Si se crea después del primer reentrenamiento, pierde su propiedad de inmutabilidad real.

---

## Regla 3 — Guardrail automático antes de firma Ed25519

### Especificación

Ningún plugin puede ser firmado con la clave Ed25519 si regresiona en cualquiera de estas métricas respecto al plugin actualmente en producción:

| Métrica | Umbral máximo de regresión | Justificación |
|---|---|---|
| **Recall** | **−0.5 pp absolutos** | Crítico: falso negativo = ataque que pasa. Umbral más restrictivo. |
| F1 | −2 pp absolutos | Métrica global |
| FPR | +1 pp absolutos | Falsos positivos = alertas innecesarias en hospital |
| **Latencia inferencia p99** | **+10% relativo** | Plugin más lento degrada el pipeline aunque F1 sea perfecto |

El guardrail es **asimétrico**: Recall es el más restrictivo porque en un NDR de infraestructura crítica un falso negativo (ataque no detectado) es cualitativamente peor que un falso positivo (alerta benigna).

```python
# check_guardrails.py
def check_guardrail(current, baseline):
    violations = []
    if current['recall'] < baseline['recall'] - 0.005:
        violations.append(f"RECALL REGRESSION: {baseline['recall']:.4f} → {current['recall']:.4f}")
    if current['f1'] < baseline['f1'] - 0.02:
        violations.append(f"F1 REGRESSION: {baseline['f1']:.4f} → {current['f1']:.4f}")
    if current['fpr'] > baseline['fpr'] + 0.01:
        violations.append(f"FPR REGRESSION: {baseline['fpr']:.4f} → {current['fpr']:.4f}")
    if current['latency_p99'] > baseline['latency_p99'] * 1.10:
        violations.append(f"LATENCY REGRESSION: {baseline['latency_p99']:.1f}ms → {current['latency_p99']:.1f}ms")
    if violations:
        for v in violations:
            print(f"[BLOCK] {v}")
        sys.exit(1)  # Ed25519 sign nunca llega a ejecutarse
    return "PROMOTE"
```

El script retorna exit code ≠ 0 ante cualquier violación. El proceso de firma **debe consumir** ese exit code. No hay excepción manual.

---

## Regla 4 — IPW + exploración forzada (anti-feedback-loop)

### Prerequisito técnico (enmienda Claude — crítico)

IPW requiere conocer la **propensity score** de cada flow: P(flow marcado como ataque | features). El pipeline de inferencia debe loggear scores de confianza, no solo la clase predicha.

**Acción previa requerida**: verificar que `ml-detector` emite `confidence_score ∈ [0,1]` por flow en su salida ZeroMQ. Si no, añadirlo como prerequisito antes de implementar esta regla. Sin confidence_score, IPW no es implementable.

### Especificación IPW

```python
# compute_ipw_weights.py
def apply_ipw(flows_benign, confidence_scores):
    # Peso inverso a la probabilidad de clasificación actual
    weights = [1.0 / max(0.01, score) for score in confidence_scores]
    # Normalizar
    total = sum(weights)
    return [w / total * len(weights) for w in weights]
```

### Especificación exploración forzada

El 5% de exploración **no es aleatorio** — usar uncertainty sampling (enmienda Gemini): priorizar flows donde el modelo actual tiene P(ataque) ≈ 0.5. Es donde reside el aprendizaje más valioso.

```python
# exploration_sampler.py
def sample_for_review(flows_benign, confidence_scores, rate=0.05):
    uncertainties = [abs(s - 0.5) for s in confidence_scores]  # 0 = máxima incertidumbre
    # 50% selección por alta incertidumbre, 50% aleatoria
    n = int(rate * len(flows_benign))
    sorted_by_uncertainty = sorted(zip(uncertainties, flows_benign))
    high_uncertainty = [f for _, f in sorted_by_uncertainty[:n//2]]
    random_sample = random.sample(flows_benign, n//2)
    return high_uncertainty + random_sample
```

El ratio puede ser adaptativo [3%-10%] según drift detectado (enmienda ChatGPT-5): si drift > umbral, aumentar exploración.

### Actor responsable de revisión (enmienda DeepSeek)

Los flows de exploración no se etiquetan automáticamente — requieren revisión. El ADR debe definir quién y cómo:

- **Año 1 post-FEDER**: el administrador de seguridad del hospital, via interfaz web sencilla embebida en rag-security. Los flows se presentan con sus features más relevantes y se pregunta "¿ataque o benigno?".
- **Año 2-3**: modelo auxiliar (ensemble más lento) como oráculo semi-automático.

Cada ciclo debe generar `exploration_log_<fecha>.csv` con flows muestreados y su etiqueta final. Sin este log, IPW no tiene datos para el siguiente ciclo.

### Métricas de diversidad obligatorias por ciclo (enmienda Qwen)

El informe de diversidad debe incluir:

| Métrica | Descripción | Umbral de alerta |
|---|---|---|
| Shannon entropy de clases | H = −Σ p(c) log p(c) | Caída >20% vs ciclo anterior |
| Coverage MITRE ATT&CK | % de técnicas representadas | < 80% → priorizar captura |
| Novelty score | % flows fuera del percentil 95 histórico | > 15% → revisar 10% en lugar del 5% |

### Memory replay como complemento (enmienda Grok)

Mantener un buffer de ejemplos históricos representativos y mezclarlo con los nuevos datos de entrenamiento. Técnica estándar en continual learning que refuerza el golden set:

```python
# memory_replay.py
REPLAY_BUFFER_SIZE = 10000  # flows históricos a mantener
def mix_with_replay(new_flows, replay_buffer):
    return pd.concat([new_flows, replay_buffer.sample(min(len(replay_buffer), REPLAY_BUFFER_SIZE))])
```

---

## Regla 5 — Competición de algoritmos antes de elegir XGBoost

### Especificación

Competición formal entre al menos:
- XGBoost
- CatBoost
- LightGBM
- RandomForest (baseline actual)

Ejecutada **una única vez** antes de lock-in de XGBoost. Resultados almacenados en `docs/ALGORITHM-SELECTION.md` con versiones exactas de cada librería. La decisión es pública y no se revisa sin justificación explícita.

### Criterio de corte multicriterio (enmienda Claude + ChatGPT-5 + Mistral + Qwen)

El ganador no es el que tiene mejor F1 aislado sino el que mejor cumple el perfil completo:

| Criterio | Peso | Umbral disqualificante |
|---|---|---|
| Recall | 40% | < 0.9985 |
| F1 | 25% | < 0.9985 |
| Latencia inferencia p99 | 20% | > 2 ms/flow |
| Tamaño modelo serializado | 10% | > 10 MB |
| Tiempo de carga inicial | 5% | > 200 ms |

Un candidato que no supera cualquier umbral disqualificante queda eliminado antes de calcular el score ponderado. Si ningún algoritmo supera al RandomForest baseline: mantener RandomForest y documentar el gap para investigación futura — sin sesgo hacia XGBoost.

---

## Regla 6 — Dataset lineage obligatorio (enmienda ChatGPT-5)

Todo modelo candidato a plugin debe registrar en sus metadatos:

```json
{
  "plugin_version": "xgboost_v1.0_20260428",
  "dataset_hash": "<sha256 del parquet de entrenamiento>",
  "golden_set_hash": "<sha256 del golden set usado>",
  "features_version": "v2.3",
  "preprocessing_commit": "<git commit hash>",
  "training_code_commit": "<git commit hash>",
  "walk_forward_windows": 5,
  "drift_detected": false,
  "algorithm": "xgboost",
  "library_versions": {
    "xgboost": "2.1.0",
    "scikit-learn": "1.5.0"
  }
}
```

Sin dataset lineage completo, no hay reproducibilidad científica real: no se puede regenerar el modelo a partir de sus inputs. El script de firma debe verificar que el fichero de metadatos existe y está completo antes de firmar.

---

## Regla 7 — Canary deployment antes de producción completa (enmienda ChatGPT-5)

Antes del despliegue completo en la flota, el plugin candidato se despliega en **5-10% del tráfico real** durante un periodo mínimo de 24 horas:

- Las decisiones del candidato se comparan contra las del modelo en producción (sin aplicar las del candidato al firewall-acl-agent).
- Si la tasa de discrepancia supera un umbral configurable (propuesta: >5% de flows con decisiones diferentes), escalar a revisión antes de ampliar el despliegue.
- Si el candidato es estable, ampliar al 100%.

Este mecanismo es post-FEDER Año 2, cuando la arquitectura federada (ADR-026) esté activa. En Año 1, el canary se implementa manualmente en la VM de desarrollo antes de desplegar en producción.

---

## Componentes afectados

| Componente | Rol en ADR-040 |
|---|---|
| **ml-detector** | Núcleo del reentrenamiento. Walk-forward, competición, dataset lineage. Debe emitir confidence_score. |
| **plugin-system (ADR-025)** | Gate de despliegue. Guardrail del −2% (+ latencia) es precondición de `ed25519_sign()`. Hash del golden set embebido en el plugin firmado. |
| **rag-ingester** | Proveedor de datos. IPW, uncertainty sampling, métricas de diversidad, memory replay. |
| **rag-security** | Interfaz de revisión manual del 5% exploración (Año 1). LLM explicabilidad (Año 2-3). |
| **eval-pipeline/** | Componente nuevo. Scripts versionados en repo. Ejecutable local (Vagrant) y vía CI. |

---

## Deuda técnica generada (post-FEDER)

| ID | Descripción | Target |
|---|---|---|
| DEBT-ADR040-001 | Crear golden set v1 (≥50K flows, 70/30, hash SHA-256, Parquet) | Pre-FEDER si posible, obligatorio v1.0 |
| DEBT-ADR040-002 | Verificar que ml-detector emite confidence_score en salida ZeroMQ | v1.0 |
| DEBT-ADR040-003 | Implementar walk_forward_split.py con --split-field y detección drift | v1.1 |
| DEBT-ADR040-004 | Implementar check_guardrails.py con los 4 umbrales | v1.1 |
| DEBT-ADR040-005 | Integrar guardrail en proceso de firma Ed25519 (ADR-025) | v1.1 |
| DEBT-ADR040-006 | Implementar IPW + uncertainty sampling en rag-ingester | v1.2 |
| DEBT-ADR040-007 | Interfaz web revisión exploración en rag-security | v1.2 |
| DEBT-ADR040-008 | Informe de diversidad (entropy, MITRE, novelty) por ciclo | v1.2 |
| DEBT-ADR040-009 | Ejecutar competición XGBoost vs CatBoost vs LightGBM | Pre-lock-in |
| DEBT-ADR040-010 | Implementar dataset lineage en metadatos del plugin | v1.1 |
| DEBT-ADR040-011 | Canary deployment manual en VM desarrollo | v1.2 |
| DEBT-ADR040-012 | docs/GOLDEN-SET-REGISTRY.md con hash v1 y proceso evolución | v1.0 |

---

## Consecuencias

**Positivas:**
- Cualquier plugin ML que llegue a producción habrá pasado por un contrato verificable, auditable y reproducible.
- El golden set como artefacto versionado es la base para reproducibilidad científica (publicación post-FEDER).
- Dataset lineage + walk-forward + guardrail es una contribución original publicable (ICSE, FSE, IEEE S&P).
- ADR-025 queda enriquecido: la firma Ed25519 certifica no solo integridad criptográfica sino calidad ML demostrada.

**Negativas / trade-offs:**
- El golden set debe crearse antes de necesitarlo — disciplina proactiva obligatoria.
- IPW requiere confidence_score del ml-detector — refactoring previo necesario.
- La revisión manual del 5% requiere un actor humano definido — no es automatizable en Año 1.
- La competición de algoritmos añade tiempo al ciclo de desarrollo Año 1.
- Canary deployment añade complejidad operacional que no existe hoy.

---

## Estado de implementación

| Tarea | Estado |
|---|---|
| Definición del contrato v2 (este ADR) | PROPUESTO |
| Golden set v1 | PENDIENTE — post-FEDER |
| eval-pipeline/ scripts en repo | PENDIENTE — post-FEDER |
| confidence_score en ml-detector | PENDIENTE — verificar primero |
| Integración guardrail en Ed25519 | PENDIENTE — post-FEDER |
| IPW + exploración + diversity report | PENDIENTE — post-FEDER |
| Competición algoritmos | PENDIENTE — pre-lock-in XGBoost |
| Dataset lineage | PENDIENTE — post-FEDER |
| Canary deployment | PENDIENTE — Año 2 |

---

## Referencias

- ADR-025: Plugin Integrity Verification (Ed25519, fail-closed)
- ADR-026: P2P Fleet Federated Architecture (XGBoost plugins Año 1)
- ADR-041: Hardware Acceptance Metrics for Hardened Variants (FEDER Baseline)
- BACKLOG-FEDER-001: Presentación Andrés Caro Lindo (UEx/INCIBE), deadline 22 sep 2026
- CTU-13 Dataset: Neris, Rbot, Murlo scenarios
- Mercadona Tech Search Engine Playbook — José Ramón Pérez Agüera (gemba.es, abril 2026)
- Consejo de Sabios — Acta 2026-04-28 (17 enmiendas, aprobado 8/8)