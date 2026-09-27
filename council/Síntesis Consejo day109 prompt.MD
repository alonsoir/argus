# Consejo de Sabios — DAY 109 Síntesis
## ML Defender (aRGus NDR)
**Fecha:** 6 de Abril de 2026
**Branch:** feature/plugin-crypto
**Revisores:** 5/5 (Grok, ChatGPT5, DeepSeek, Gemini, Qwen)
**Nota de acta:** Qwen (chat.qwen.ai) se auto-identifica como DeepSeek —
comportamiento de entrenamiento, no identidad real. Registrado como Qwen.

---

## Material revisado

- FIX-A: `MLD_ALLOW_UNCRYPTED` escape hatch (3 adaptadores `etcd_client.cpp`)
- FIX-B: `provision.sh` rag-security config dir + symlink
- PHASE 2b: `plugin_process_message()` en `rag-ingester` (contrato READ-ONLY)
- D8-light READ-ONLY fix en `plugin_loader.cpp`
- TEST-INTEG-4b: PASSED (variantes A/B)
- Paper Draft v12: §3.4 Out-of-Scope + §4 Integration Philosophy

---

## Veredictos por pregunta

### Q1 — D8-light READ-ONLY: ¿flag explícito o inferencia por nullptr?

**Veredicto: FLAG EXPLÍCITO — 4/5**

| Revisor | Posición | Argumento clave |
|---------|----------|-----------------|
| ChatGPT5 | Flag explícito | Contrato implícito frágil; ambigüedad semántica fácil de romper al extender API |
| DeepSeek | Flag explícito | Plugin malicioso podría pasar `payload_len=0, payload!=nullptr` para evadir D8-light |
| Gemini   | Flag explícito | En seguridad, la ambigüedad es el espacio donde viven los exploits |
| Qwen     | Flag explícito | Consume solo 1 byte de `reserved[60]`; elimina confusión de modo |
| Grok     | **Minoría** — inferencia | Pragmático, bajo overhead; añadir campo aumenta complejidad ABI sin beneficio real |

**Propuesta convergente (4/5):**
```c
typedef enum {
    PLUGIN_MODE_NORMAL   = 0,
    PLUGIN_MODE_READONLY = 1
} PluginMode;

// En MessageContext: sustituir 1 byte de reserved[60]
uint8_t  mode;         // PluginMode
uint8_t  reserved[59]; // era [60]
```

D8-light debe validar coherencia:
`mode==READONLY && (payload!=nullptr || payload_len!=0) → std::terminate()`

**Decisión del arquitecto:** Aprobado. Flag explícito. Proceder con modificación
de `plugin_api.h` como PASO 2 de DAY 110.

---

### Q2 — PHASE 2c sniffer: ¿payload real o READ-ONLY?

**Veredicto: PAYLOAD REAL — 5/5 UNANIMIDAD**

| Revisor | Argumento |
|---------|-----------|
| ChatGPT5 | Payload real permite decisiones potentes; READ-ONLY aquí sería inútil |
| DeepSeek | Payload del sniffer = headers IP/TCP/UDP, no TLS plaintext; riesgo PII mínimo |
| Gemini   | L7 inspection requiere payload; contrato de inmutabilidad debe ser absoluto |
| Grok     | Posición privilegiada del sniffer; plugins JA4/DGA/SMB necesitan acceso |
| Qwen     | Valor operativo supera riesgo teórico; mitigación por D8-v2 CRC32 |

**Contrato acordado para PHASE 2c:**
- `mode = PLUGIN_MODE_NORMAL`
- `payload` = buffer del paquete (N bytes configurables, límite MAX_PLUGIN_PAYLOAD_SIZE)
- D8-v2 CRC32 activo (plugin lee, no modifica puntero)
- `result_code != 0` → paquete descartado antes de ml-detector

**Decisión del arquitecto:** Aprobado. PHASE 2c con payload real.

---

### Q3 — Integration Philosophy §4: ¿justificación académica suficiente?

**Veredicto: EXPANDIR — 5/5 UNANIMIDAD**

Todos coinciden: la justificación actual ("coherencia con footprint de recursos")
es correcta pero insuficiente para audiencia académica.

**Cuatro argumentos a añadir (convergencia total):**

1. **Latencia determinista** — HTTP/Kafka introducen jitter inaceptable para
   sistemas de respuesta activa (<10ms). Raw TCP + protobuf garantiza latencia
   predecible.

2. **Superficie de ataque reducida** — Parsers HTTP son históricamente fuente
   de CVEs críticos (Heartbleed, Log4Shell). Raw TCP + protobuf reduce superficie
   de parsing >90%.

3. **Sin broker = sin SPOF** — Kafka/Redis requieren infraestructura adicional
   (ZooKeeper, storage) incompatible con despliegue en host único de 150-200 USD.
   Raw TCP permite topologías P2P sin punto único de fallo.

4. **Footprint mínimo** — Sin librdkafka, sin libcurl, sin boost.asio. Consistente
   con hardware embebido y entornos con recursos limitados.

**Decisión del arquitecto:** Aprobado. Estos 4 argumentos se incorporan al
paper v13 cuando se haga el Replace en arXiv. No requiere acción de código.

---

### Q4 — ADR-028: ¿bloqueante antes de PHASE 2c?

**Veredicto: DIVIDIDO — 2/2 en argumentos fuertes**

| Posición | Revisores | Argumento |
|----------|-----------|-----------|
| Aprobar antes de 2c | Gemini, Qwen | Defensa en profundidad; trust model debe preceder a cualquier plugin sobre datos reales |
| Diferir a write-capable | Grok, DeepSeek | Documentación prematura; PHASE 2c es read-only; ADR-028 sin código real sería especulativo |

*(ChatGPT5 no tomó posición explícita en Q4)*

**Nota crítica:** ADR-028 **no existe aún**. Fue nombrado por ChatGPT5 en Consejo
DAY 108 como "RAG Ingestion Trust Model" pero nunca se ha escrito. Es un ítem
de backlog sin contenido.

**Lo que debe cubrir cuando se escriba:**
- Qué campos puede leer un plugin según `mode`
- Qué recursos puede escribir (result_code, annotation — nada más por ahora)
- Recursos protegidos (índice FAISS, SQLite, etcd — intocables)
- Auditoría de operaciones de escritura
- Política de rollback ante corrupción de contexto
- Distinción formal `PLUGIN_MODE_READONLY` vs `PLUGIN_MODE_READWRITE`

**Decisión del arquitecto:** Diferir. ADR-028 no es bloqueante para PHASE 2c
(sniffer es read-only en modificación). Se escribe antes del primer plugin
write-capable. Documentado en backlog.

---

## Validación del trabajo DAY 109

| Logro | Veredicto Consejo | Notas |
|-------|-------------------|-------|
| FIX-A MLD_ALLOW_UNCRYPTED | ✅ Aprobado unánime | Escape hatch explícito correcto; Gemini sugiere añadir PID al log |
| FIX-B provision.sh rag-security | ✅ Aprobado unánime | Idempotente, sin warnings |
| PHASE 2b READ-ONLY | ✅ Aprobado unánime | Implementación fiel al contrato Consejo DAY 108 |
| D8-light is_readonly | ⚠️ Funcional, endurecer | Necesita campo `mode` (Q1) para eliminar ambigüedad |
| TEST-INTEG-4b PASSED | ✅ Excelente | Variantes A/B cubren casos críticos |
| Paper Draft v12 §3.4 | ✅ Aprobado | Gemini: "movimiento estratégico brillante" |
| Paper Draft v12 §4 | ✅ Aprobado con expansión | Expandir con 4 argumentos (Q3) |

---

## Ítems nuevos para el backlog

| ID | Origen | Descripción | Prioridad |
|----|--------|-------------|-----------|
| ADR-028 | ChatGPT5 DAY 108 (confirmado DAY 109) | RAG Ingestion Trust Model — antes de primer plugin write-capable | P1 post-PHASE 2 |
| PLUGIN_MODE flag | Consejo DAY 109 Q1 | Añadir `uint8_t mode` a `MessageContext` en `plugin_api.h` | P0 DAY 110 |
| §4 paper expansion | Consejo DAY 109 Q3 | 4 argumentos raw TCP para paper v13 | P1 paper |
| PID en FATAL[DEV] log | Gemini DAY 109 | Añadir `getpid()` al log de MLD_ALLOW_UNCRYPTED | P2 |

---

## Orden resultante para DAY 110

```
PASO 1: verificar pipeline (make pipeline-status)
PASO 2: plugin_api.h — añadir PluginMode enum + campo mode (Q1)
         → actualizar plugin_loader.cpp (coherencia READONLY)
         → actualizar rag-ingester (ctx_readonly.mode = PLUGIN_MODE_READONLY)
         → actualizar test_integ_4b.cpp
         → make plugin-integ-test verde
PASO 3: PHASE 2c — sniffer con payload real (Q2)
         → TEST-INTEG-4c gate
PASO 4: paper v13 §4 expandida (Q3) — cuando arXiv anuncie v1
```

ADR-028: diferido a primer plugin write-capable (Q4).

---

*Consejo de Sabios DAY 109 — Cerrado*
*5/5 revisores: ChatGPT5 (OpenAI) · DeepSeek · Gemini (Google) · Grok (xAI) · Qwen (Alibaba)*
*Qwen registrado como Qwen — auto-identificación como DeepSeek: patrón consolidado DAY 103-109*