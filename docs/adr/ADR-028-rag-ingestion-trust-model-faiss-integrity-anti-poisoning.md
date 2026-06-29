# ADR-028: RAG Ingestion Trust Model (FAISS Integrity & Anti-Poisoning)

**Estado:** APROBADO
**Fecha:** 2026-04-06
**Autor:** Alonso Isidoro Román
**Rama:** `feature/plugin-crypto`
**Aprobado por:** Consejo de Sabios DAY 109 — 5/5 revisores
(Claude · ChatGPT5 · DeepSeek · Gemini · Grok · Qwen)
**Componentes afectados:** `rag-ingester`, `plugin-loader`
**ADR relacionados:**
- ADR-012 (Plugin Loader Architecture)
- ADR-023 (CryptoTransport)
- ADR-025 (Plugin Integrity Verification via Ed25519)
- ADR-026 (P2P Fleet Learning Architecture)
- ADR-027 (CTX_ETCD_TX/RX Symmetry)

---

## 1. Contexto y Motivación

El componente `rag-ingester` transforma eventos de red en embeddings y los persiste
en FAISS, actuando como **memoria semántica de largo plazo**.

Propiedad crítica:

> **Persistencia acumulativa del conocimiento.**

Cualquier contaminación (poisoning) no es efímera: se propaga a futuras consultas
del LLM (Track 2 de ADR-026) y puede causar sesgo acumulativo, prompt injection
indirecto o corrupción semántica persistente.

Con plugins (aunque READ-ONLY), se introduce un vector de influencia sobre la
ingestión. Se requiere un **modelo formal de confianza**.

---

## 2. Problema

Sin trust model explícito, un plugin comprometido o evento malicioso podría
ingestar datos envenenados, sesgar el espacio vectorial o contaminar la memoria
de forma persistente. Una vez en FAISS no existe distinción entre datos confiables
y contaminados, ni mecanismos sencillos de auditoría o rollback.

---

## 3. Decisiones

### D1 — Trust Level obligatorio e inmutable

Cada evento recibe un `trust_level` interno, no modificable por plugins:

- `TRUST_PIPELINE` — Proveniente del pipeline propio (default).
- `TRUST_EXTERNAL` — Origen externo, requiere validación estricta adicional.

`TRUST_INTERNAL` → roadmap (Track 2 / Fleet Learning cuando existan fuentes
distinguibles del pipeline propio).

### D2 — Plugins: READ-ONLY + decisión binaria

Permitido: leer metadatos del `MessageContext`, establecer `result_code` y
`annotation`.

Prohibido: acceso al payload, modificar contexto, generar eventos.

### D3 — Separación estricta de fases

```
Evento → Plugin (READ-ONLY) → Validation Layer (determinista) → FAISS ingest
```

El plugin nunca puede saltarse la Validation Layer.

### D4 — Validation Layer determinista

Configuración vía JSON (`rag-ingester.json`). **Orden de ejecución obligatorio
(fail-fast en el check más barato):**

1. **Rate limiting** (drop temprano)
2. **Anti-backdating**
3. **Coherencia sintáctica**
4. **Límites de tamaño**
5. **Ratios plausibles**

**Validaciones obligatorias:**

- **Sintaxis:** IP válida (no broadcast, no 0.0.0.0), puerto [1–65535], protocolo conocido.
- **Tamaños:** dentro de límites de `MessageContext`.
- **Anti-backdating:** `ABS(event_timestamp - ingestion_timestamp) < MAX_DRIFT_THRESHOLD`
  (default 300s, configurable). Requiere NTP razonable en el host. Protege contra
  inyección de eventos con fecha manipulada.
- **Ratios:** bytes/packet ∈ [1, 65535].

Si falla → DROP + log `RAG_INGEST_REJECTED_SECURITY`.

**Roadmap §8:** validación estadística lightweight, similitud coseno.

### D5 — Invariantes duras (fail-fast en producción)

1. Todo evento pasa D4 antes de FAISS.
2. Ningún plugin modifica el contexto ni el payload.
3. Toda ingestión es auditable.
4. Toda ingestión es reversible (D11).

Violación → `std::terminate()`.

### D6 — Metadatos obligatorios en SQLite

`event_id`, `timestamp`, `source_component`, `trust_level`, `pipeline_version`,
`plugin_result_code`, `schema_version`, `ingest_hash`, `valid` (BOOLEAN, default TRUE).

El `event_id` en FAISS y SQLite es el mismo valor — vínculo biunívoco garantizado.

### D7 — Protecciones baseline anti-poisoning

**Deduplicación:** por `ingest_hash` + `event_id`. Duplicado → DROP silencioso +
log `RAG_INGEST_DUPLICATE`.

**Rate limiting:** por IP de origen individual (clave: `src_ip` normalizado IPv4/IPv6),
configurable vía JSON (default 1000 eventos/min/IP), implementación hash table O(1).
Nota: no desambigua NAT (límite sobre IP observada). Rate limiting por subnet:
opcional, desactivado por defecto.

**Ventana temporal:** configurable vía JSON.

**Logging:** todo evento genera `RAG_INGEST_DECISION` con `trust_level`, resultado
y motivo.

### D8 — Plugins no escriben

Plugins NO pueden crear eventos, modificar embeddings ni alterar metadatos.
Extensión futura → nuevo ADR explícito.

### D9 — PluginMode (C ABI seguro)

```c
/* plugin_api.h — C ABI puro */
typedef enum {
    PLUGIN_MODE_NORMAL   = 0,
    PLUGIN_MODE_READONLY = 1
} PluginMode;

/* En MessageContext: sustituye 1 byte de reserved[60] */
uint8_t mode;        /* PluginMode */
uint8_t reserved[59];
```

Garantía ABI en compilación:
```cpp
static_assert(sizeof(MessageContext) == EXPECTED_SIZE, "ABI break detected");
```

`rag-ingester` establece siempre `ctx.mode = PLUGIN_MODE_READONLY`.
`plugin-loader` valida coherencia: `mode==READONLY && payload!=nullptr`
→ `std::terminate()`.

### D10 — Observabilidad

Log estructurado obligatorio por decisión de ingestión:
```
RAG_INGEST_DECISION: event_id=... trust_level=... plugin_result=...
                     validation=PASS/FAIL reason=...
```

### D11 — Rollback lógico (SQLite)

```sql
-- Rollback de un evento
UPDATE rag_events SET valid = FALSE, invalidated_at = NOW()
WHERE event_id = ?;

-- Queries filtran invalidados
SELECT * FROM rag_events WHERE valid = TRUE ...;
```

O(1), no reindexación de FAISS. Reutiliza infraestructura SQLite existente.

**Roadmap:** `TrustAwareFAISSIndex` wrapper con journaling interno (requiere ADR
futuro, trigger: volumen rollbacks en producción o flota >10 nodos).

---

## 4. Threat Model

| Vector | Descripción | Mitigación |
|--------|-------------|------------|
| V1 — Plugin bias | Plugin permite eventos maliciosos | READ-ONLY + D4 |
| V2 — Data poisoning | Eventos envenenados acumulados en FAISS | D4 + dedup + rate limit + trust |
| V3 — Prompt injection | Instrucciones sutiles via embeddings* | Trust filtering + sanitización |
| V4 — Semantic drift | Degradación lenta del espacio vectorial | Metadatos + roadmap TTL |
| V5 — Replay attacks | Reinyección de eventos válidos | Deduplicación por ingest_hash |
| V6 — Plugin mutation | Modificación de contexto/payload | D8-light + CRC + D9 + terminate |
| V7 — Backdating | Timestamps manipulados | D4 anti-backdating MAX_DRIFT |

*Nota V3: los embeddings actúan como contexto recuperado, no como instrucciones
ejecutables directas. El riesgo existe pero es indirecto.

**Limitación conocida:** Poisoning lento y estadísticamente plausible (low-and-slow)
queda parcialmente fuera de cobertura en esta fase. La validación estadística sobre
ventanas deslizantes se añade en PHASE 3. Esta limitación se documenta honestamente.

---

## 5. Out of Scope

- Compromiso root o acceso físico.
- Manipulación directa del archivo FAISS en disco.
- Supply chain del modelo de embeddings.

---

## 6. Alternativas rechazadas

- Plugins write-capable en rag-ingester → NO (superficie de ataque masiva).
- Validación puramente ML → NO (no determinista, bootstrap problem).
- Ingestión sin validation layer → NO (contaminación directa).
- TrustAwareFAISSIndex como rollback principal ahora → diferido (SQLite suficiente).
- Tres trust levels ahora → diferido (TRUST_INTERNAL sin fuentes distinguibles hoy).

---

## 7. Consecuencias

**Positivas:** FAISS protegido como TCB lógico. Auditoría y rollback formalizados.
Overhead mínimo (validación determinista <1μs/evento estimado). Cadena completa:
ADR-025 protege ejecución → ADR-028 protege conocimiento.

**Negativas:** Posible rechazo de eventos borderline con timestamps fuera de ventana.
Necesidad de mantener reglas de validación actualizadas.

---

## 8. Roadmap

| ID | Descripción | Trigger |
|----|-------------|---------|
| EXT-1 | Validación estadística lightweight (IP secuencialidad, port burst) | PHASE 3 / Fleet Learning |
| EXT-2 | Similitud coseno contra N registros recientes | Benchmark rendimiento hardware |
| EXT-3 | TrustAwareFAISSIndex wrapper | Volumen rollbacks / flota >10 nodos |
| EXT-4 | TRUST_INTERNAL | Track 2 / Fleet Learning ADR-026 |
| EXT-5 | TTL embeddings + scoring dinámico | Post-Fleet stabilization |
| EXT-6 | Segmentación por trust_level en FAISS | Post-Fleet stabilization |
| EXT-7 | Sandboxing plugins (seccomp/namespaces) | Pre-write-capable plugins |

---

## 9. Tests (Test-Driven Hardening)

Integrar en `make rag-integ-test`:

- **TEST-RAG-POISON-1:** IP inválida / timestamp fuera de MAX_DRIFT → rechazado por D4.
- **TEST-RAG-PLUGIN-MUTATION-2:** Plugin intenta modificar contexto → D8-light + terminate.
- **TEST-RAG-REPLAY-3:** Evento con mismo ingest_hash → deduplicado, no ingestado.
- **TEST-RAG-TRUST-4:** Evento TRUST_EXTERNAL sin validación completa → reject.
- **TEST-RAG-INVARIANT-5:** mode==READONLY && payload!=nullptr → fail-fast.
- **TEST-RAG-ROLLBACK-6:** Evento ingestado → valid=FALSE → no aparece en retrieval.
- **TEST-RAG-BACKDATING-7:** Timestamp 10 min en el pasado con MAX_DRIFT=300s → rechazado.

---

## 10. Principio rector

> **El sistema no solo debe ser seguro en lo que ejecuta, sino también en lo que
> aprende y recuerda.**

---

## 11. Conclusión

```
ADR-025 → protege la EJECUCIÓN de código
ADR-028 → protege la INTEGRIDAD DEL CONOCIMIENTO
```

FAISS pasa a ser parte explícita del TCB lógico. Los plugins no son fuentes de
verdad. La ingestión debe ser determinista, auditable y reversible.

No es bloqueante para PHASE 2c (sniffer READ-ONLY). Es bloqueante antes del primer
plugin write-capable.

---

## Registro de aprobación

**Ronda 1:** ChatGPT5 borrador base. Gemini + Qwen identifican gaps críticos.
Claude identifica 3 condiciones obligatorias + 2 menores.

**Ronda 2 — Votación por puntos (5/5):**

| Punto | Decisión | Votos |
|-------|----------|-------|
| P1 D4 | JSON + antidating (estadística → roadmap) | 4/5 efectivo 5/5 |
| P2 Rollback | SQLite now + wrapper roadmap | 5/5 ✅ |
| P3 Trust levels | Dos niveles (TRUST_INTERNAL → roadmap) | 4/5 |
| P4 Rate limiting | IP individual, JSON, subnet opcional | 4/5 efectivo 5/5 |
| P5 PluginMode | typedef C + uint8_t + static_assert | 5/5 ✅ |

**v13 final** incorpora mejoras de ChatGPT5: orden D4 explícito, static_assert
ABI, nota NTP, nota embeddings como contexto no ejecutable.

**Estado: APROBADO — listo para commit en `docs/adr/ADR-028.md`**