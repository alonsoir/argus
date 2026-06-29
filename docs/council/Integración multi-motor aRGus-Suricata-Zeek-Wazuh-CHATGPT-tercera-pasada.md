# Consejo de Sabios — Ratificación Técnica de la Pasada 3

## Cierre de P3.1–P3.4 y consecuencias sobre ADR-046 v4

La Pasada 3 ya no discute arquitectura conceptual, sino propiedades de estabilidad, auditabilidad y reproducibilidad del sistema bajo replay y entrenamiento federado. El Consejo considera que el nivel de madurez alcanzado es suficiente para congelar el núcleo semántico del correlador antes de implementación pesada.

La resolución de D5 por Alonso además cambia el eje del proyecto:

```text
pipeline vivo + captura inmutable + replay determinista
```

Eso convierte:

* append-only,
* timestamps canónicos,
* replay reproducible,
* telemetría tipada,
* y estabilidad temporal,

en requisitos estructurales y no simples preferencias de implementación.

---

# P3.1 — `emitted_at` / `ingested_at`

## Dictamen: RATIFICADA

## Decisión

Campos tipados de primera clase.

---

# Motivo técnico

El sistema ya no es solo:

* un correlador en vivo,
* ni un SIEM experimental.

Ahora también es:

* generador de datasets reproducibles,
* plataforma de replay,
* pipeline de telemetría temporal,
* base de entrenamiento federado.

En ese contexto:

```protobuf
uint64 emitted_time_unix_ns
uint64 ingested_time_unix_ns
```

son semántica estructural.

No “metadata arbitraria”.

---

# Beneficios directos

## 1. Telemetría reproducible

Permite medir:

```text
detection_latency
adapter_latency
ingestion_latency
replay_skew
```

sin parsing textual.

---

## 2. Comparabilidad cross-run

Los histogramas:

* deben ser binarios,
* estables,
* agregables,
* exportables a Parquet/Arrow.

---

## 3. Detección de degradación

Permite descubrir:

* congestión,
* buffering,
* backpressure,
* stalls,
* drift operacional.

Especialmente importante bajo replay federado.

---

# Recomendación adicional

El envelope debería quedar aproximadamente así:

```protobuf
message SecurityEvent {
  string source_engine = 1;
  string native_event_id = 2;

  uint64 event_time_unix_ns = 3;
  uint64 emitted_time_unix_ns = 4;
  uint64 ingested_time_unix_ns = 5;

  optional string community_id = 6;
  optional string host_key = 7;

  EventDomain domain = 8;
  uint32 severity = 9;

  bytes raw_payload = 10;

  map<string,string> metadata = 11;
}
```

---

# P3.2 — Orden de evicción en conjunto frío

## Dictamen: RATIFICADA

## Decisión

Tiers discretos.

No score continuo.

---

# Motivo principal

La degradación bajo saturación debe ser:

```text
predecible
auditabile
demostrable
```

Los scores continuos son difíciles de:

* explicar,
* reproducir,
* probar formalmente,
* endurecer frente a ataques.

---

# El problema del score continuo

El término:

```text
severity × sources × freshness
```

parece elegante,
pero introduce comportamiento emergente.

---

## Problema crítico

El factor:

```text
sources
```

es inflable.

Un atacante puede:

* disparar correlaciones artificiales,
* aumentar fan-in,
* elevar score,
* reducir evictabilidad.

Eso reintroduce pinning indirecto.

---

# Ventajas de tiers discretos

## 1. Determinismo

El orden es explícito:

```text
LOW
→ MEDIUM
→ HIGH
→ FEDER_CRITICAL
```

---

## 2. Auditabilidad

`eviction_reason` es interpretable.

---

## 3. Testabilidad

La propiedad anti-pinning puede probarse.

---

## 4. Estabilidad operacional

No hay tuning oculto de pesos.

---

# Recomendación importante

El sistema debería exportar:

```protobuf
enum EvictionTier {
  LOW = 0;
  MEDIUM = 1;
  HIGH = 2;
  FEDER_CRITICAL = 3;
}
```

y separar:

* severidad original,
* tier de protección operacional.

Porque no siempre coincidirán.

---

# P3.3 — Granularidad de cuota anti-pinning

## Dictamen: RATIFICADA

## Decisión

FEDER:

* cuota por IP externa individual,
* más cap global.

---

# Motivo

Es:

* suficiente,
* simple,
* demostrable,
* y defensivamente razonable.

---

# Sobre `/24`

Correctamente descartado para FEDER.

Riesgo real:

* NAT compartidos,
* clouds,
* universidades,
* CGNAT,
* proxys,
* VPNs.

Un `/24` puede contener:

* cientos de actores legítimos.

---

# Sobre `community_id`

También correctamente descartado.

Porque:

* el objetivo es limitar origen persistente,
* no identidad de flujo.

---

# Recomendación importante

El sistema debería:

* registrar quota hits,
* exportar métricas,
* y permitir tuning futuro.

Pero no complicar FEDER prematuramente.

---

# P3.4 — Semántica del rezagado

## Dictamen: RATIFICADA FUERTEMENTE

Esta es probablemente la decisión más importante de toda la Pasada 3.

---

# Decisión

## Crisis emitidas son inmutables.

Los rezagados:

* NO mutan,
* NO reescriben,
* NO editan.

Generan:

* delta append-only enlazado.

---

# Razón fundamental

La resolución D5 hace que:

```text
captura + replay = dataset autoritativo
```

Si una crisis pudiera mutar:

* según cuándo se consulte,
* según cuándo llegue el rezagado,
* según orden de replay,

el dataset dejaría de ser determinista.

---

# Consecuencia crítica

Un dataset mutable destruye:

## 1. Walk-forward integrity

porque el “pasado” cambia.

---

## 2. Reproducibilidad

dos replays producirían datasets distintos.

---

## 3. Validez federada

los nodos no entrenarían sobre la misma historia temporal.

---

## 4. Auditabilidad científica

el ground-truth quedaría contaminado.

---

# El modelo correcto

Debe ser:

```text
CRISIS_CREATED
CRISIS_UPDATED_DELTA
CRISIS_LATE_ARRIVAL
CRISIS_CLOSED
```

todos:

* append-only,
* ordenados temporalmente,
* replayables.

---

# Recomendación importante

El log de crisis debería comportarse como:

# Event Sourcing

No como:

* fila mutable SQL,
* documento mutable,
* estado sobrescribible.

---

# Consecuencia arquitectónica importante

El Consejo considera que el sistema ya está convergiendo naturalmente hacia:

# Temporal Event Graph + Event Sourcing

Esto tiene implicaciones futuras:

| Área       | Consecuencia                  |
| ---------- | ----------------------------- |
| Replay     | determinista                  |
| Neo4j      | reconstrucción de estado      |
| ML         | datasets walk-forward válidos |
| Forense    | timeline estable              |
| Federado   | convergencia reproducible     |
| Saturación | degradación auditable         |

---

# Sobre la “Pasada 4”

El Consejo coincide plenamente:

La siguiente superficie natural es:

# contrato del dataset federado

porque ahora sí existen:

* timestamps estables,
* correlación estable,
* semántica append-only,
* replay determinista,
* envelope común,
* política de degradación.

Ya existe base suficiente para diseñar:

* Parquet/Arrow,
* etiquetas,
* particionado federado,
* ventanas walk-forward,
* leakage prevention,
* schemas de entrenamiento.

---

# Veredicto Final de la Pasada 3

## P3.1 — RATIFICADA

## P3.2 — RATIFICADA

## P3.3 — RATIFICADA

## P3.4 — RATIFICADA FUERTEMENTE

Con D5 resuelto por Alonso y P3.1–P3.4 cerradas, el Consejo considera que:

* ADR-046 v4 ya puede redactarse completamente,
* `AdapterSpec v1` tiene base estable,
* el contrato wire está esencialmente congelado,
* y la futura Pasada 4 puede centrarse exclusivamente en el contrato del dataset federado y replay determinista.
CHATGPT