# Consejo de Sabios — DAY 105
## Sesión de revisión: ADR-023 PHASE 2a — implementación y gate TEST-INTEG-4a

**Fecha:** 2 abril 2026
**Rama:** `feature/plugin-crypto`
**Revisor humano:** Alonso Isidoro Roman
**Co-revisores IA:** Claude (Anthropic), Grok (xAI), ChatGPT (OpenAI),
DeepSeek, Qwen (Alibaba), Gemini (Google), Parallel.ai

---

## Contexto

DAY 105 implementó ADR-023 PHASE 2a: integración de `MessageContext` y
`plugin_process_message()` en `firewall-acl-agent`. El Consejo revisó:

1. El contrato `MessageContext` tal como quedó implementado
2. La Graceful Degradation Policy D1 en producción
3. El snapshot D8 (post-invocation validation)
4. La corrección del orden de dependencias en el Makefile
5. El gate TEST-INTEG-4a y su suficiencia como gate de PHASE 2a

---

## Artefactos revisados

### `plugin_api.h` — MessageContext

```c
typedef struct MessageContext {
    // Read-only: payload post-decrypt + post-decompress (D2)
    const uint8_t* payload;
    size_t         payload_len;

    // Read-only: metadatos de flujo (D2)
    uint32_t       src_ip;
    uint32_t       dst_ip;
    uint16_t       src_port;
    uint16_t       dst_port;
    uint8_t        protocol;

    // Read-only: dirección de transporte (D3)
    uint8_t        direction;  // 0=RX, 1=TX

    // Read-only: metadatos crypto (D3)
    const uint8_t* nonce;   // 12 bytes
    const uint8_t* tag;     // 16 bytes

    // Write: salida del plugin
    int            result_code;
    char           annotation[64];

    // Reservado: forward-compatibility ADR-024 (D11)
    uint8_t        reserved[60];
} MessageContext;
```

### Gate TEST-INTEG-4a — output observado

```
[plugin:hello] init OK — name=hello config={}
[plugin-loader] INFO: plugin 'hello' no exporta plugin_process_message
  — Graceful Degradation D1 aplicada
[plugin-loader] INFO: loaded plugin 'hello' v0.1.0
[INFO] plugin-loader: 1 plugin(s) cargados
[INFO] TEST-INTEG-4a: result_code=0
[plugin:hello] shutdown OK
[plugin-loader] INFO: shutdown plugin 'hello'
  — invocations=0 overruns=0 errors=0
```

---

## Preguntas al Consejo

**Q1.** El snapshot D8 compara punteros (`ctx.payload == snap_payload`) en lugar de
contenido del buffer. ¿Es suficiente para detectar modificaciones de campos read-only,
o debería compararse el contenido byte a byte?

**Q2.** El gate TEST-INTEG-4a usa el hello plugin de PHASE 1, que no exporta
`plugin_process_message()`. Por tanto, el camino D8 (post-invocation validation)
no se ejecuta en este gate. ¿Es TEST-INTEG-4a suficiente como gate de PHASE 2a,
o se requiere un plugin de test que exporte el símbolo para validar D8?

**Q3.** `nonce` y `tag` son `nullptr` en el smoke test sintético (no hay decrypt
disponible pre-etcd en test-config mode). ¿Debe el contrato de `MessageContext`
documentar explícitamente que `nonce`/`tag` pueden ser `nullptr` en contextos
de test, o esto introduce ambigüedad en producción?

**Q4.** La Makefile fix (firewall depende de plugin-loader-build) resuelve el
problema de orden de instalación. ¿Deberían sniffer, ml-detector, rag-ingester
y rag-security tener la misma dependencia explícita, o ya la tienen implícitamente?

**Q5.** ADR-023 D11 reserva `reserved[60]` para ADR-024. ¿Es suficiente el
tamaño para los campos que ADR-024 necesitará (X25519 public key = 32 bytes,
session_id = 8 bytes, flags = 4 bytes), o conviene revisar la reserva antes
de que ADR-024 llegue a implementación?

---

## Decisiones consolidadas DAY 105 (pre-Consejo)

| ID | Decisión | Implementado |
|----|----------|-------------|
| D1 | Graceful Degradation: skip silencioso si no exporta símbolo | ✅ |
| D2 | Ownership/lifetime payload contrato | ✅ `plugin_api.h` |
| D3 | direction/nonce/tag read-only para plugin | ✅ comentarios |
| D7 | Trust model declarado en header | ✅ |
| D8 | Post-invocation snapshot (pointer comparison) | ✅ |
| D9 | TCB declaration en header | ✅ |
| D10 | MLD_DEV_MODE solo Debug + MLD_ALLOW_DEV_MODE | ✅ |
| D11 | Forward-compatibility ADR-024 — reserved[60] | ✅ |

---

## Próxima sesión Consejo

**TEST-INTEG-4b** (rag-ingester) — cuando PHASE 2b esté implementada.
Preguntas pendientes de esta sesión se incorporan al gate 4b si no se resuelven antes.

---

*DAY 105 — 2 abril 2026*
*Tests: 25/25 ✅ · Gate TEST-INTEG-4a: PASSED*