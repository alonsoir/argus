# ADR-007: Consenso vs Máximo en la Decisión de Bloqueo del Firewall

**Fecha:** 2026-03-11 (DAY 82 — descubierto durante análisis post-replay)
**Estado:** ACEPTADO — implementación diferida a PHASE2
**Autores:** Alonso Isidoro Román + Claude (Anthropic)
**Relacionado con:** ADR-002 (Multi-Engine Provenance), ADR-006 (Fast Detector thresholds)
**Formalizado:** DAY 90 — 18 marzo 2026
**Path:** `docs/adr/ADR-007-and-consensus-firewall.md`

---

## Contexto

Durante la validación con datasets balanceados (DAY 82), el análisis del comportamiento
del pipeline bajo volúmenes de tráfico variables reveló una vulnerabilidad teórica
en la lógica de scoring actual.

El sistema implementa una arquitectura dual-score (ADR-002): cada evento recibe
un `fast_score` (Fast Detector, heurísticas de red) y un `ml_score` (RandomForest,
features extraídas del flujo). La decisión final se calcula como:

```cpp
// Implementación actual (zmq_handler.cpp)
double final_score = std::max(fast_score, ml_score);
bool should_block = final_score >= config_.scoring.malicious_threshold;
```

Esta lógica es correcta en el caso nominal, pero presenta una vulnerabilidad
bajo adversario sofisticado que comprenda la arquitectura del pipeline.

---

## Problema: Envenenamiento del contexto temporal

Se identificaron dos vectores de manipulación basados en la observación de que
el `ml_score` correlaciona con el volumen y diversidad de tráfico en la ventana
temporal de inferencia (DAY 82: 0.38 → 0.66 → 0.69 con 1K/19K/40K flows):

### Vector A — Inflación (ML score envenenado hacia arriba)

Un adversario inunda la red con tráfico que activa el RandomForest hacia scores
altos (tráfico con características de ataque pero sin comportamiento malicioso
real detectable por heurísticas de red).

Resultado con lógica `max()`:

```
fast_score = 0.20  (Fast Detector: benigno)
ml_score   = 0.95  (ML: inflado por envenenamiento)
final      = 0.95  → BLOQUEO
```

El firewall bloquea tráfico legítimo. El Fast Detector, que es más difícil de
engañar (heurísticas de red independientes del historial), dice benigno — pero
es ignorado por `max()`.

### Vector B — Dilución (ML score envenenado hacia abajo)

Un adversario precede el ataque real con un flood de tráfico benigno sintético,
diluyendo el espacio de features hacia scores bajos.

Resultado con lógica `max()`:

```
fast_score = 0.90  (Fast Detector: ataque real detectado)
ml_score   = 0.10  (ML: diluido por flood benigno previo)
final      = 0.90  → BLOQUEO ✅
```

En este caso `max()` es correcto — el Fast Detector salva la situación.
El Vector B es menos peligroso que el Vector A con la arquitectura actual.

### Tabla de escenarios completa

| fast_score | ml_score | max() | AND lógico | Escenario |
|---|---|---|---|---|
| 0.90 | 0.90 | 0.90 BLOCK | BLOCK ✅ | Ataque real, consenso |
| 0.90 | 0.10 | 0.90 BLOCK | ALERT only ⚠️ | Fast solo — ML diluido |
| 0.20 | 0.95 | 0.95 BLOCK ❌ | ALERT only ✅ | Vector A — ML inflado |
| 0.20 | 0.20 | 0.20 ALLOW | ALLOW ✅ | Benigno, consenso |

El único escenario donde `max()` y `AND lógico` difieren es exactamente
el Vector A: ML envenenado arrastra bloqueos que Fast Detector nunca autorizaría.

---

## Decisión

Separar la semántica de **alerta** y **bloqueo** mediante criterios distintos:

```cpp
// ADR-007: Consenso para bloqueo, OR para alerta
bool should_alert =
    fast_score >= config_.scoring.alert_threshold ||
    ml_score   >= config_.scoring.alert_threshold;

bool should_block =
    fast_score >= config_.scoring.malicious_threshold &&
    ml_score   >= config_.scoring.malicious_threshold;
```

**El Fast Detector actúa como ancla de bloqueo.** Sin su confirmación,
ningún score ML por sí solo puede forzar un bloqueo en el firewall.

---

## Propiedades de la nueva arquitectura

### Resistencia al Vector A (ML inflado)
- ML envenenado ↑ solo → `should_alert=true`, `should_block=false`
- El firewall no bloquea sin consenso
- El operador recibe alerta y puede investigar

### Resistencia al Vector B (ML diluido)
- Fast Detector detecta ataque real → `should_alert=true`
- Sin confirmación ML → `should_block=false` (más conservador que antes)
- **Trade-off explícito:** se pierde capacidad de bloqueo autónomo cuando
  ML está bajo envenenamiento de dilución. Aceptable: preferimos fallar
  abiertos (no bloquear) antes que fallar cerrados (bloquear legítimo)
  en hospitales y escuelas.

### Comportamiento ante adversario con acceso completo al pipeline
Si el adversario puede manipular simultáneamente el Fast Detector y el ML,
ninguna arquitectura de scoring resuelve el problema solo con umbrales.
Este escenario requiere integridad del pipeline (HMAC, ADR-001) y
detección de anomalías en el propio sistema de scoring — fuera del
alcance de este ADR.

### Inclusión del comportamiento anterior
La lógica `max()` actual es un caso especial donde `alert_threshold == malicious_threshold`.
La nueva arquitectura es estrictamente más expresiva — no rompe nada, extiende.

---

## Threat model formal

- **Adversario A1:** conoce el threshold de bloqueo, puede generar tráfico
  con features ML altas pero sin patrones de red detectables por heurísticas.
  → Mitigado por ADR-007 (AND para bloqueo).

- **Adversario A2:** puede generar flood benigno previo para diluir contexto ML.
  → Parcialmente mitigado: Fast Detector es independiente del historial ML.
  → Limitación documentada: ventana temporal del Fast Detector también es
  manipulable si el adversario conoce `WINDOW_NS`. Fix: DEBT-FD-001 (ADR-006).

- **Adversario A3:** acceso completo al pipeline, puede manipular ambos detectores.
  → Fuera del alcance de scoring. Requiere integridad de pipeline (ADR-001 HMAC)
  y auditoría continua. Documentado como limitación conocida.

---

## Implicaciones para el paper

### Sección propuesta: "Adversarial Robustness of Dual-Score Architectures"

La observación experimental de que `ml_score` correlaciona con el volumen
de tráfico en la ventana temporal abre un vector de ataque teórico documentado
aquí para arquitecturas EDR de doble motor.

**Contribución científica:**

> *La lógica `max(fast, ml)` es segura en el caso nominal pero vulnerable
> bajo adversario con conocimiento del pipeline. La separación semántica
> alerta/bloqueo mediante OR/AND lógico elimina el vector de inflación
> sin sacrificar la sensibilidad del sistema de alertas.*

---

## Relación con el microscopio

Cuando un ataque supere ambas capas (Fast Detector + ML en consenso), el evento
quedará registrado con scores completos, trace_id, provenance ADR-002, y features
de 40 dimensiones. El RAG-security actúa como microscopio forense post-hoc:
el sistema no previene ese ataque en tiempo real, pero lo documenta con
resolución suficiente para entender el vector y reentrenar.

Esta es la filosofía correcta: **no fingir omnisciencia, sino construir
capacidad de aprendizaje continuo ante ataques desconocidos.**

---

## Alternativas consideradas y descartadas

### Alternativa 1: Score ponderado (weighted average)
`final = α·fast_score + (1-α)·ml_score`

Descartada: la ponderación es un parámetro adicional sin criterio objetivo de
calibración, y no elimina el problema de envenenamiento — solo lo atenúa.
Introduce complejidad sin garantías formales.

### Alternativa 2: Votación por mayoría (N motores futuros)
Generalización de AND para sistemas con 3+ motores: bloqueo si mayoría supera threshold.

No descartada — es la evolución natural de ADR-007 en versión enterprise (ENT-1:
Federated Threat Intelligence). Anotada para PHASE3.

### Alternativa 3: Mantener max() con confidence intervals
Añadir incertidumbre estadística al ML score via Platt scaling o isotonic regression.
Complejidad desproporcionada para el beneficio en la fase actual. Descartada.

---

## Implementación (PHASE2)

```cpp
// En zmq_handler.cpp, reemplazar:
double final_score = std::max(fast_score, ml_score);
bool should_block = final_score >= config_.scoring.malicious_threshold;

// Por:
bool should_alert =
    fast_score >= config_.scoring.alert_threshold ||
    ml_score   >= config_.scoring.alert_threshold;

bool should_block =
    fast_score >= config_.scoring.malicious_threshold &&
    ml_score   >= config_.scoring.malicious_threshold;

double final_score = std::max(fast_score, ml_score); // para trazabilidad
```

Nuevos campos JSON necesarios en `sniffer.json`:
```json
"scoring": {
    "alert_threshold": 0.70,
    "malicious_threshold": 0.85,
    "consensus_required_for_block": true
}
```

**Sin recompilar:** los thresholds son configurables desde JSON.
**Sin cambiar el pipeline:** la lógica de routing al firewall
se actualiza solo en `zmq_handler.cpp`.

---

## Estado de implementación

| Componente | Estado actual | Acción PHASE2 |
|---|---|---|
| `zmq_handler.cpp` | `max()` → bloqueo único | Separar `should_alert` / `should_block` |
| `firewall-acl-agent` | Recibe decisión binaria | Sin cambios (recibe flag ya procesado) |
| `sniffer.json` | `malicious_threshold` único | Añadir `alert_threshold` independiente |
| DEBT-FD-001 | Fast Detector ignora JSON | **Prerequisito:** resolver antes de ADR-007 |
| Tests | No existen para esta lógica | Añadir casos: OR-only, AND-consensus, discrepancia |

> ⚠️ **DEBT-FD-001 es prerequisito de ADR-007.** Si el Fast Detector usa constantes
> hardcodeadas ignorando `sniffer.json`, el threshold de bloqueo AND no puede
> ajustarse en runtime, anulando la flexibilidad de esta arquitectura.

---

## Consecuencias

**Positivas:**
- Eliminación del Vector A (ML inflado forzando bloqueos)
- Fast Detector como ancla de bloqueo — arquitectura más honesta
- Comportamiento explícito y auditable para cada tipo de acción
- Threat model formal documentado para el paper
- Compatible con el comportamiento anterior como caso especial

**Negativas / Trade-offs:**
- Reducción de bloqueos autónomos cuando Fast Detector no confirma ML
- En entornos con Fast Detector degradado, el sistema pasa a modo alerta-only
- Requiere calibración de `alert_threshold` separada de `malicious_threshold`
- No afecta a la detección (alertas) — solo al bloqueo automático

---

## Nota de descubrimiento

Este ADR emergió de una sesión de análisis experimental (DAY 82) sin
modificar una línea de código — únicamente ejecutando PCAP replays con
el pipeline en estado actual y observando el comportamiento del scoring
bajo diferentes volúmenes de tráfico.

Es un ejemplo de cómo el pipeline como **microscopio** genera conocimiento
arquitectónico que trasciende la detección de amenazas inmediatas.

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Descubierto: DAY 82 — 11 marzo 2026*
*Formalizado: DAY 90 — 18 marzo 2026*
*Consejo de Sabios — ML Defender (aRGus EDR)*