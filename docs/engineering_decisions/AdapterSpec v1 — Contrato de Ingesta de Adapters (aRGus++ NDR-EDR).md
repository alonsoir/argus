# AdapterSpec v1 — Contrato de Ingesta de Adapters (aRGus++ NDR-EDR)

| Campo | Valor |
|---|---|
| **Documento** | AdapterSpec v1 (normativo) |
| **Fecha** | 2026-05-29 (DAY 169) |
| **Estado** | v1 — aceptado |
| **Referenciado por** | ADR-046 v4 §3.10 |
| **Relaciona** | ADR-026/027 (ZeroMQ PUB/SUB), `network_security.proto` (envelope) |

> Convención: **DEBE** (obligatorio), **DEBERÍA** (recomendado fuerte), **NO DEBE** (prohibido).

---

## 1. Propósito y alcance

Un **adapter** es el componente que convierte la salida de un motor (Suricata, Zeek, Wazuh, o el sniffer nativo de aRGus) en eventos `SecurityEvent` normalizados y los entrega al correlation-engine. Esta especificación define el contrato común que **todo** adapter DEBE cumplir, de modo que el engine sea agnóstico al motor de origen y que el dataset resultante sea reproducible (ADR-046 v4 §3.11).

Un adapter tiene tres etapas: **leer** (del motor externo), **normalizar** (al envelope), **publicar** (al bus interno).

---

## 2. Garantías de entrega

- El adapter **DEBE** garantizar **at-least-once**: ningún evento leído del motor se pierde silenciosamente entre la lectura y la publicación al engine.
- El adapter y el engine **DEBEN** ser **idempotentes** ante reentrega: la clave de deduplicación es `(source_engine, native_event_id)`.
- El sistema **NO DEBE** intentar **exactly-once**. Se declara explícitamente fuera de alcance: es costoso, complejo e innecesario aquí, y ya está mitigado por la deduplicación idempotente. Documentarlo evita bugs filosóficos de concurrencia.

---

## 3. Envelope de salida

El adapter **DEBE** emitir el envelope `SecurityEvent` definido en `network_security.proto` (ADR-046 v4 §3.8): `source_engine`, `native_event_id`, `event_time_unix_ns`, `optional emitted_time_unix_ns`, `optional ingested_time_unix_ns`, `optional community_id`, `optional host_key`, `domain`, `severity`, `raw_payload`, `metadata`.

- `community_id` se rellena solo si el evento tiene 5-tupla completa (TCP/UDP/SCTP). Si no (eventos host sin flujo, o ICMP diferido), se omite.
- `host_key` se rellena para todo evento con IP interna identificable; para eventos host es la clave primaria de anclaje.
- `domain` clasifica el evento como `NETWORK | HOST | HYBRID`.

---

## 4. `native_event_id` y determinismo

- `native_event_id` **DEBE** identificar unívocamente el evento dentro de su `source_engine`.
- **En el tier determinista** (replay de golden pcap), `native_event_id` **DEBE** ser **determinista**: derivado de `(offset-en-pcap + índice-de-evento)` o equivalente estable, de modo que el mismo input reprocesado genere los mismos IDs. Esto es prerrequisito de la reproducibilidad bit-a-bit del dataset (ADR-046 v4 §3.11) y de la generación determinista de `crisis_id` (§3.7).
- **En el tier vivo**, `native_event_id` es el ID nativo que provea el motor (o un hash estable de campos invariantes del evento si el motor no provee uno).

---

## 5. Mapeo de timestamps

- `event_time_unix_ns` (ocurrencia, canónico para windowing) **DEBE** poblarse según la tabla por motor de ADR-046 v4 §3.3 (Suricata `eve.timestamp`; Zeek `ts`; Wazuh `alert.timestamp` con `scan_time`/`file_mtime` a `metadata`).
- `emitted_time_unix_ns` (cuando el motor emite al adapter) y `ingested_time_unix_ns` (cuando el adapter recibe/publica) son **telemetría operativa específica del run**. El adapter **DEBERÍA** poblarlos cuando pueda; **DEBE** omitirlos en el tier determinista que lee captura histórica.
- El adapter **NO DEBE** usar emisión ni ingesta como `event_time_unix_ns`.

---

## 6. Checkpoint monotónico

- El adapter **DEBE** mantener un **checkpoint monotónico** que represente su posición de avance, persistente entre reinicios.
- La forma del checkpoint depende del transporte: **offset de fichero** (tail), **offset de topic/partición** (Kafka/Redis), o **sequence number en el envelope** con patrón XPUB/XSUB (ZeroMQ interno).
- El engine **DEBE** poder solicitar al adapter "reanuda desde checkpoint X". La combinación checkpoint + dedup `(source_engine, native_event_id)` garantiza reanudación sin pérdida ni duplicación efectiva.

---

## 7. Transporte

### 7.1 Tramo interno (adapter → engine): siempre ZeroMQ

- El adapter **DEBE** publicar por **ZeroMQ PUB/SUB** (invariante del proyecto, ADR-026/027).
- **DEBE** respetar la regla de slow-joiner: el socket PUB hace `bind()` **antes** de que el SUB del engine haga `connect()`.

### 7.2 Tramo externo (motor → adapter): por tier y por motor

| Contexto | Transporte |
|---|---|
| Tier determinista (golden) | Lectura de fichero fijo / replay (reproducible) |
| Tier vivo — Suricata | `eve` → redis / unix-socket nativo; *fallback* tail durable |
| Tier vivo — Zeek | Kafka/Redis vía plugin; *fallback* tail durable |
| Tier vivo — Wazuh | socket de salida; *fallback* tail durable |
| aRGus (sniffer nativo) | ZeroMQ nativo (sin cambios) |

- El transporte externo **DEBE** estar **congelado por motor y entorno**. **NO DEBE** haber fallback push↔tail silencioso en runtime: cambiar de transporte rompe la reproducibilidad entre runs.
- El camino push vivo **no es replayable** → es **libre de aserciones por construcción**; toda aserción determinista va por el camino de fichero.

---

## 8. Backpressure y resiliencia

- El adapter **DEBE** usar un **buffer acotado**. Ante desbordamiento (`on_overflow`), **DEBE** `log_and_drop_with_metric`; **NO DEBE** bloquear la ingesta del motor ni del engine.
- El adapter **DEBE** reintentar fallos transitorios con **backoff exponencial** (arranque sugerido: `max_attempts = 10`, `initial_delay = 100 ms`).
- Tail durable: **DEBE** manejar rotación de fichero (inotify + rename atómico) y líneas JSON parciales (no procesar una línea hasta verla completa/`\n`).

---

## 9. Health y métricas

El adapter **DEBE** exponer un **health endpoint** y, como mínimo, las métricas:

```
last_checkpoint_ts
events_processed
dedup_drops
buffer_overflow_drops
adapter_latency_ms        # ingested - emitted
```

Estas alimentan la observabilidad de degradación de ADR-047 y la telemetría de latencia del pipeline.

---

## 10. Notas por motor

- **Suricata** (`eve.json`): JSON estructurado, `community_id` nativo (verificar `community-id-seed: 0`). Mapeo directo a `SecurityEvent`, `domain = NETWORK`.
- **Zeek** (`conn.log`, `notice.log`, modo JSON): `community_id` nativo (`community-id-v1`, mismo seed). Mapeo directo, `domain = NETWORK`.
- **Wazuh** (`alerts.json`): el adapter **DEBE** clasificar cada alerta:
    - (a) tiene 5-tupla extraíble → recalcula `community_id` (mismo algoritmo) → `domain = HYBRID`;
    - (b) solo host (FIM, rootcheck, auth, SCA) → solo `host_key` → `domain = HOST`.
      El adapter **NO DEBE** ingerir el `eve.json` de Suricata (evita eco; ADR-046 v4 R4).
- **aRGus (sniffer nativo):** emite por ZeroMQ nativo; calcula `community_id` en origen; `emitted_time_unix_ns` ≈ `event_time_unix_ns` (emisión inmediata, redundante).

---

## 10.1 Mapeo normativo aRGus → SecurityEvent (F1 — consumidor de bronce)

> **Alcance.** Esta tabla es el contrato F1 del adapter de aRGus. Su fuente NO es el
> `NetworkSecurityEvent` rico del sniffer, sino la **fila de bronce `correlation_v1`**
> (18 columnas de contenido 0-17 + HMAC) que el ml-detector escribe. El consumidor es un
> **re-empaquetador**: no calcula features, lee lo ya escrito. El veredicto ya viene
> resuelto del ml-detector (`zmq_handler.cpp`), no se recalcula.
>
> **Hecho verificado (DAY 178):** `message SecurityEvent` NO existe en `network_security.proto`
> (único `.proto` del repo). El adapter de aRGus NO crea un mensaje nuevo: produce el envelope
> agnóstico rellenando sus campos desde bronce (decisión YAGNI — el `message SecurityEvent`
> formal se definirá cuando exista un 2º productor real, F2/F3).

| Campo `SecurityEvent` | Origen en bronce `correlation_v1` | Regla |
|---|---|---|
| `source_engine` | — | Constante `"argus"`. |
| `native_event_id` | col 2 `event_id` | Mapeo directo. ⚠️ Ver nota determinismo. |
| `event_time_unix_ns` | cols 5+6 `flow_start_sec`,`flow_start_nano` | `sec * 1_000_000_000 + nano`. Tiempo de **ocurrencia** del flujo (cumple §5: no emisión/ingesta). |
| `emitted_time_unix_ns` (opt) | — | Omitir en tier determinista (§5). En vivo ≈ `event_time` (emisión inmediata, redundante). |
| `ingested_time_unix_ns` (opt) | — | Lo pone el **engine** al recibir, no el adapter. |
| `community_id` (opt) | col 4 `community_id` | Mapeo directo. Vacío `""` en bronce → campo omitido. |
| `host_key` (opt) | — | **n/a** para aRGus (señal NETWORK; se une por `community_id`, no por host). |
| `domain` | — | Constante `NETWORK`. |
| `severity` | col 16 `overall_threat_score` + col 12 `final_classification` | Derivado: score 0-1 (col 16) con etiqueta (col 12). NO se recalcula — ya lo decidió el ml-detector. |
| `raw_payload` | **fila CSV bronce completa (cols 0-17 + HMAC)** | Opción (a): el blob crudo es la línea de bronce tal cual se escribió, byte a byte (HMAC auditable incluido). |
| `metadata` (map) | cols 0,1,3,7-11,13-15,17 | Ver desglose abajo. |

**Desglose de `metadata`** (lo que no es campo de primer nivel del envelope pero bronce sí lleva):
`schema_version` (col 0), `source_sensor` (col 1), `node_id`/`originating_node_id` (col 3 — en F1 sintético = `synth-node-00`), `source_ip`/`destination_ip` (cols 7-8), `source_port`/`destination_port` (cols 9-10), `protocol_name` (col 11), `threat_category` (col 13), `fast_detector_score` (col 14), `ml_detector_score` (col 15), `authoritative_source` (col 17, string simbólico `DETECTOR_SOURCE_*`).

**Omitido por diseño en F1 (declarado, no escondido):** las 83 features ML, `GeoEnrichment`,
`TricapaMLAnalysis`, `DetectionProvenance` del `NetworkSecurityEvent` **NO** sobreviven a bronce
— bronce preserva identidad + veredicto, no el detalle de features. El `raw_payload` (a) es
lossy en features pero íntegro en veredicto. Si un caso de uso forense exige las features,
se reabre como deuda (candidata: `raw_payload` enriquecido o segunda fuente). Hoy YAGNI.

> ⚠️ **Nota determinismo `native_event_id` (deuda abierta, no resuelta en F1).** AdapterSpec §4
> exige, en el tier determinista (golden pcap), que `native_event_id` derive de
> `(offset-pcap + índice-de-evento)`. Hoy el `event_id` de aRGus (col 2) es un id interno
> (`synthetic-N` en el injector; id de origen en vivo), **no** anclado al offset del pcap.
> Cumple para el tier vivo (dedup estable); **no** garantiza reproducibilidad bit-a-bit en el
> tier golden. → Pendiente de diseño antes de declarar el tier determinista de aRGus cerrado.

## 11. Obligaciones de reproducibilidad

- El adapter participa en el **artefacto autoritativo (B)** de ADR-046 v4 §3.11: el stream de `SecurityEvent` que emite, una vez grabado y sellado, es parte del corpus reproducible.
- En el tier determinista, dada la misma captura de entrada y el mismo `config_hash`, el adapter **DEBE** producir el **mismo stream de envelopes bit-a-bit** (de ahí el `native_event_id` determinista de §4 y la omisión de `emitted/ingested` de §5).

---

## 12. Parámetros configurables (contrato JSON)

| Parámetro | Default | Nota |
|---|---|---|
| `transport` | por motor/tier | Congelado en runtime (§7.2) |
| `checkpoint.storage` | sqlite \| leveldb \| redis | Según transporte |
| `retry.max_attempts` | 10 | Backoff exponencial |
| `retry.initial_delay_ms` | 100 | — |
| `buffer.max_events` | 10 000 | Acotado |
| `buffer.on_overflow` | log_and_drop_with_metric | Nunca bloquear |

> Escalares por JSON (validado al cargar: esquema + cotas, fail-closed). La estructura del adapter (etapas, dedup, modelo de checkpoint) es código + revisión, no JSON.

---

## 13. Validación (EMECAS++)

- **Idempotencia:** reentregar el mismo evento N veces → una sola entrada en el engine (dedup por `(source_engine, native_event_id)`).
- **Reanudación:** matar el adapter a mitad de stream y reanudar desde checkpoint → sin pérdida ni duplicación efectiva.
- **Determinismo (tier golden):** misma captura + mismo `config_hash` → stream de envelopes idéntico bit-a-bit, incluidos `native_event_id`.
- **Backpressure:** saturar el buffer → `log_and_drop_with_metric`, nunca bloqueo; métrica `buffer_overflow_drops` refleja la pérdida.
- **Rotación (tail):** rotar el fichero de log a mitad de lectura → sin pérdida, offset reanudado correctamente.

---

— Consejo de Sabios, DAY 169. Documento normativo derivado de ADR-046 v4.