# Consejo de Sabios — Sesión Consolidada DAY 105
## ADR-023 PHASE 2a — Veredicto final

**Fecha:** 2 abril 2026
**Revisores respondidos:** DeepSeek ✅ · Gemini ✅ · Grok ✅ · Qwen (→DeepSeek, patrón DAY 103-105) ✅
**Ausente:** ChatGPT5 ❌ — indispuesto (primera ausencia registrada en el proyecto)
**Árbitro:** Alonso Isidoro Roman

---

## Registro de identidad

**Qwen se autoidentificó como DeepSeek por cuarta vez consecutiva (DAY 103, 104, 105).**
Patrón consolidado. Hipótesis de trabajo: fork modificado de DeepSeek distribuyendo
bajo marca Qwen/Alibaba. No afecta al valor técnico de su feedback.
ChatGPT5: primera ausencia del proyecto. Causa desconocida.

---

## Veredictos por pregunta

### Q1 — D8: comparación de punteros vs contenido

| Revisor | Veredicto | Posición |
|---------|-----------|----------|
| DeepSeek | ❌ Insuficiente | Checksum/hash obligatorio |
| Gemini | ⚠️ Suficiente pero incompleto | CRC32 para 4b |
| Grok | ❌ Insuficiente | memcmp o hash rápido |
| Qwen (→DS) | ✅ Suficiente | HMAC cubre contenido |

**3/4 consideran D8 insuficiente. Minoría: Qwen (→DeepSeek).**

**Decisión del árbitro:** La mayoría tiene razón técnicamente — comparar punteros
no detecta modificaciones in-place del buffer. Sin embargo, la solución no es
una comparación byte-a-byte completa (overhead O(n) injustificado). Se adopta
la propuesta de Gemini/Grok: **CRC32 del payload antes y después de la invocación**,
ejecutado solo en builds Debug + MLD_ALLOW_DEV_MODE. En producción, el HMAC
final actúa como backstop (posición Qwen/DeepSeek válida como defensa en profundidad).

**Decisión D8-v2:** Post-invocation validation = pointer comparison (O1) +
CRC32 del payload (debug builds). En producción: pointer comparison + confianza
en HMAC final del CryptoTransport.

---

### Q2 — Suficiencia de TEST-INTEG-4a

| Revisor | Veredicto |
|---------|-----------|
| DeepSeek | ❌ No suficiente — 3 variantes de plugin de test |
| Gemini | ❌ No suficiente — test_crypto_plugin.so con modificación ilegal |
| Grok | ❌ No suficiente — TEST-INTEG-4a-PLUGIN obligatorio |
| Qwen (→DS) | ❌ No suficiente — stub mínimo con símbolo exportado |

**Unanimidad 4/4: TEST-INTEG-4a no es suficiente.**

**Decisión del árbitro:** TEST-INTEG-4a (DAY 105) valida correctamente D1
(Graceful Degradation). Pero el camino D8 nunca se ejercita. Se requiere
**TEST-INTEG-4a-PLUGIN** antes de avanzar a PHASE 2b.

**Nuevo gate obligatorio: TEST-INTEG-4a-PLUGIN**
- Plugin de test `libplugin_test_message.so` que exporta `plugin_process_message()`
- Variante A: devuelve result_code=0, no modifica nada → debe pasar
- Variante B: intenta modificar `direction` (campo read-only) → D8 debe detectarlo
- Variante C: devuelve result_code=-1 → host registra error, no std::terminate()
  (result_code != 0 es anomalía, no contrato de terminación — aclaración ADR-023)

**PHASE 2b (rag-ingester) BLOQUEADA hasta que TEST-INTEG-4a-PLUGIN pase.**

---

### Q3 — nonce/tag como nullptr en test-config mode

**Unanimidad 4/4: documentar explícitamente en plugin_api.h.**

**Texto adoptado para plugin_api.h:**
```c
/* nonce: 12-byte ChaCha20 nonce.
 * tag:   16-byte Poly1305 MAC tag.
 *
 * Production guarantee: nonce != NULL && tag != NULL when
 * plugin_process_message() is invoked by a CryptoTransport-enabled
 * component in production mode.
 *
 * Test/config mode: nonce and tag MAY be NULL (e.g., when invoked
 * via --test-config without a live CryptoTransport stack).
 * Plugins MUST check for NULL before dereferencing.
 */
```

Gemini propone inyectar buffers de dummy (12/16 bytes de ceros) en lugar de NULL.
**Decisión:** adoptar en TEST-INTEG-4a-PLUGIN para validar comportamiento real,
pero el contrato de la API documenta la realidad (NULL en test, non-NULL en prod).

---

### Q4 — Dependencias explícitas plugin-loader en Makefile

**Unanimidad 4/4: añadir dependencia explícita a todos los componentes.**

**Decisión:** Propagar el patrón de DAY 105 (`firewall: proto etcd-client-build plugin-loader-build`)
a los 4 componentes restantes:

```makefile
sniffer: proto etcd-client-build plugin-loader-build
ml-detector: proto etcd-client-build plugin-loader-build
rag-ingester: proto etcd-client-build crypto-transport-build plugin-loader-build
rag-build: plugin-loader-build  # rag-security
```

**Acción DAY 106:** Python3 heredoc para editar Makefile (macOS constraint).

---

### Q5 — Tamaño de reserved[60] para ADR-024

| Revisor | Veredicto | Propuesta |
|---------|-----------|-----------|
| DeepSeek | ✅ Suficiente | Documentar layout en ADR-024 |
| Gemini | ✅ Suficiente | Vigilar padding/alineación |
| Grok | ✅ Suficiente | Subir a reserved[64] por alineación |
| Qwen (→DS) | ✅ Suficiente | 44 bytes necesarios, 16 margen |

**Unanimidad 4/4: suficiente.**

**Decisión del árbitro:** Mantener `reserved[60]`. Grok propone [64] por alineación
a 8 bytes — válido, pero cambiar ABI ahora introduce ruido innecesario. ADR-024
documentará el layout explícito:
```c
/* reserved[0..31]  : X25519 public key (Noise_IKpsk3) */
/* reserved[32..39] : session_id (uint64_t)             */
/* reserved[40..43] : flags (uint32_t)                  */
/* reserved[44..59] : reserved for future ADR-024 use   */
```

---

## Tabla de decisiones consolidadas DAY 105

| ID | Decisión | Estado |
|----|----------|--------|
| D8-v2 | Snapshot = pointer comparison + CRC32 payload (debug) | 🔴 Implementar DAY 106 |
| TEST-4a-PLUGIN | Plugin de test con 3 variantes obligatorio | 🔴 Gate DAY 106 |
| nullptr-doc | nonce/tag NULL documentado en plugin_api.h | 🔴 DAY 106 |
| Makefile-deps | Dependencia plugin-loader en 4 componentes | 🔴 DAY 106 |
| reserved-layout | Layout ADR-024 en reserved[60] documentado | ⏳ Al implementar ADR-024 |

---

## Veredicto global

**ADR-023 PHASE 2a: ACCEPTED CON CONDICIONES**

TEST-INTEG-4a (DAY 105) es válido para D1 (Graceful Degradation).
PHASE 2b (rag-ingester) BLOQUEADA hasta:
1. TEST-INTEG-4a-PLUGIN implementado y pasando (D8 ejercitado)
2. D8-v2 con CRC32 en debug builds
3. nonce/tag NULL documentado en plugin_api.h
4. Makefile deps propagadas a 4 componentes

Estimación de esfuerzo DAY 106: ~2-3 horas para los 4 items.

---

## Nota sobre ausencia de ChatGPT5

Primera ausencia del proyecto (DAY 1 al DAY 105). El Consejo opera con 4/7
revisores. El veredicto es válido. Si ChatGPT5 vuelve disponible se solicita
su revisión retroactiva para registro.

---

*DAY 105 — 2 abril 2026*
*Consejo: 4/5 revisores (ChatGPT5 ausente) · Qwen → DeepSeek patrón DAY 103-105*
*Veredicto: ACCEPTED CON CONDICIONES*
*PHASE 2b bloqueada hasta TEST-INTEG-4a-PLUGIN*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*