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