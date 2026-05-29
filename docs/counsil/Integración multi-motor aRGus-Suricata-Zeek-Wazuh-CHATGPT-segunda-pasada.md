# Consejo de Sabios — Ratificación Técnica de la Pasada 2

## Evaluación de las mociones M1–M4 y consecuencias arquitectónicas

La Pasada 2 mejora significativamente el nivel de rigor respecto a la primera: ya no discute “ideas generales”, sino propiedades operacionales concretas del correlador bajo presión, skew temporal, saturación y asimetría host/red. El Consejo considera que el documento está entrando en zona de arquitectura ejecutable.

La mayoría de las reconciliaciones propuestas son sólidas y compatibles con sistemas reproducibles por terceros.

---

# M1 — Timestamp canónico

## Dictamen: RATIFICADA

La resolución propuesta es técnicamente correcta y está alineada con cómo operan sistemas de correlación temporal serios.

---

## Motivo fundamental

El correlador debe ordenar eventos según:

```text id="3fjlwm"
cuándo ocurrió el fenómeno observado
```

y no según:

```text id="y0tr6r"
cuándo el software consiguió emitirlo
```

Porque:

* la latencia de detección es variable,
* depende del motor,
* depende de carga,
* depende del pipeline interno,
* y puede fluctuar órdenes de magnitud.

---

## Caso concreto reproducible

### Suricata

La alerta suele emitirse:

* prácticamente inmediata,
* ligada al paquete.

### Wazuh

Un evento FIM puede aparecer:

* segundos después,
* tras scan periódico,
* tras pipeline decoder/rule engine,
* tras buffering.

Usar emisión para windowing produce:

```text id="1d7g6n"
false temporal distance
```

entre eventos causalmente relacionados.

---

## Recomendación adicional importante

El envelope debería conservar explícitamente:

```protobuf id="c7eq3v"
uint64 event_time_unix_ns
uint64 emitted_time_unix_ns
uint64 ingested_time_unix_ns
```

no solo vía `metadata`.

Razón:

* permite métricas binarias reproducibles,
* simplifica profiling,
* evita parsing textual,
* facilita histogramas de latencia,
* permite detectar congestión interna.

---

## Sobre la objeción de Qwen

La objeción identifica un problema real:

* incertidumbre temporal de eventos host.

Pero la solución correcta es:

* ampliar `bridge_window`,
* marcar confianza temporal,
* no degradar el timestamp canónico.

La moción responde correctamente.

---

# M2 — Política de evicción

## Dictamen: RATIFICADA FUERTEMENTE

Esta es probablemente la decisión más importante de toda la pasada.

El Consejo considera que la síntesis propuesta supera claramente tanto:

* el LRU puro,
* como la inmunidad absoluta por severidad.

---

# Hallazgo importante

La Pasada 2 identifica correctamente algo muy serio:

## “Severity pinning attack”

Es un vector completamente real.

---

## Escenario reproducible

Un atacante:

* descubre qué firmas elevan severidad,
* genera flujos distintos,
* mantiene vivas miles de crisis HIGH,
* consume el correlador,
* fuerza evicción de eventos reales.

La inmunidad absoluta convierte:

```text id="6s4k9l"
severity
```

en:

```text id="dk31cx"
memory reservation primitive
```

Eso es peligrosísimo.

---

# La arquitectura en 3 capas es correcta

## Capa 1 — Protección por recencia

Excelente decisión.

Protege:

* crisis activas,
* correlaciones en construcción,
* bursts reales,
* pipelines normales.

Y es:

* neutral,
* difícil de explotar,
* estable.

---

## Capa 2 — Severidad como orden

También correcta.

La severidad:

* influye,
* prioriza,
* pero no congela memoria.

Eso evita el pinning.

---

## Capa 3 — Cuota anti-pinning

Muy buena decisión arquitectónica.

Especialmente correcta esta asimetría:

```text id="esay3m"
host interno protegido
origen externo acotado
```

porque refleja el verdadero modelo defensivo:

* lo importante es la víctima,
* no el emisor ruidoso.

---

# Recomendación adicional importante

Añadir:

```text id="9nwl8m"
saturation mode telemetry
```

explícita:

```protobuf id="t10r7k"
enum SaturationReason {
  NONE = 0;
  MEMORY_PRESSURE = 1;
  SOURCE_QUOTA = 2;
  GLOBAL_QUOTA = 3;
}
```

y exponer:

* cuántas crisis se degradaron,
* por qué,
* desde qué origen.

Eso hace auditable ADR-047.

---

# M3 — Transporte de adapters

## Dictamen: RATIFICADA

La reconciliación propuesta es correcta porque descubre que había dos debates mezclados.

---

# Hallazgo importante

El desacuerdo original era parcialmente falso.

Se estaban discutiendo:

* transporte interno,
* y adquisición externa,

como si fueran el mismo problema.

No lo son.

---

# La separación propuesta es correcta

## Interno

ZeroMQ uniforme.

Perfectamente coherente con:

* ADR-026,
* ADR-027,
* arquitectura existente.

---

## Externo

Resolver por:

* motor,
* tier,
* reproducibilidad,
* capacidades nativas.

Esto es correcto y pragmático.

---

# Recomendación importante

El `AdapterSpec v1` debería formalizar:

## Semántica mínima

### REQUIRED

```text id="n1crtm"
- at-least-once delivery
- idempotent replay
- durable checkpoint
- monotonic offsets
- bounded buffering
- health state
- replay capability
```

---

## EXPLICITLY NOT GUARANTEED

```text id="7j9h3d"
exactly-once
```

porque:

* es costoso,
* complejo,
* innecesario aquí,
* y ya mitigado por dedup.

Formalizar esto evitará bugs filosóficos futuros.

---

# M4 — Predicado de “fuente esperada”

## Dictamen: RATIFICADA

---

# M4.a — Separación de ventanas

## Correcta

Separar:

* correlación activa,
* rezagados,
* idle expiration,

es una mejora muy importante.

---

## Razón

Son tres fenómenos distintos:

| Fenómeno     | Naturaleza    |
| ------------ | ------------- |
| correlación  | lógica        |
| late arrival | transporte    |
| idle         | ciclo de vida |

Un único timeout mezclaba capas distintas.

---

# M4.b — Rechazo del acoplamiento al ruleset Wazuh

## Correcto

La objeción de Qwen detecta:

* expectativas vacías.

Pero su solución:

```text id="mjlwmv"
engine conoce el ruleset de Wazuh
```

viola separación de responsabilidades.

---

# Riesgo real de esa propuesta

El correlador pasaría a depender de:

* reglas,
* decoders,
* updates,
* configuraciones,
* coverage interno.

Eso:

* rompe encapsulación,
* dificulta reproducibilidad,
* hace el sistema frágil.

---

# La mitigación actual ya basta

Porque:

* las ventanas son acotadas,
* el timeout es finito,
* no bloquea ingestión,
* no produce hang sistémico.

La moción lo resuelve correctamente.

---

# Sobre D5 — Corpus vs pipeline

Aquí el Consejo mantiene la misma posición:

# El corpus debe ser el cimiento

No porque el pipeline vivo no importe,
sino porque:

```text id="4x2uxc"
sin corpus reproducible
no existe validación científica reproducible
```

---

# Recomendación estratégica

## FEDER debería entregar:

### 1. Corpus reproducible multi-engine

Con:

* pcaps,
* alerts,
* etiquetas,
* correlaciones esperadas,
* community_ids,
* ground truth.

### 2. Pipeline vivo demostrable

Aunque:

* sea menos determinista,
* más ligero,
* y secundario respecto al corpus.

---

# Punto muy importante

La Pasada 2 ya está describiendo implícitamente un:

# “event graph correlation runtime”

más que un SIEM clásico.

Eso cambia:

* cómo se modela el estado,
* cómo se mide saturación,
* cómo se valida,
* cómo se serializa,
* cómo se hacen replays.

El Consejo recomienda empezar a pensar explícitamente en:

* event graph lifecycle,
* graph compaction,
* temporal edge expiration,
* replay determinism,
* graph reconstruction from corpus.

Porque el diseño ya apunta naturalmente ahí.

---

# Veredicto Final de la Pasada 2

## M1 — RATIFICADA

## M2 — RATIFICADA FUERTEMENTE

## M3 — RATIFICADA

## M4 — RATIFICADA

## D5 — pendiente de decisión estratégica de Alonso

El Consejo considera que:

* el contrato wire ya tiene forma estable,
* el modelo dual está correctamente asentado,
* la política de saturación ya tiene fundamentos defensivos reales,
* y ADR-046 v4 puede empezar a escribirse sin riesgo serio de rework estructural.
CHATGPT
