**5/5 respondieron.** Nota habitual: Qwen se auto-identifica como DeepSeek — registrado como Qwen en actas.

## Síntesis del Consejo DAY 110

**Q1-111 (orden PHASE 2d vs 2e): UNANIMIDAD 5/5 → 2d primero**

Sin sorpresas. El argumento es consistente en todos: ml-detector sigue el patrón limpio (set_plugin_loader + member), rag-security tiene el patrón especial (g_plugin_loader global + signal handler) que merece atención dedicada después.

---

**Puntos nuevos relevantes — ChatGPT5 (los más duros, como siempre):**

Dos fixes que califica como **obligatorios antes de cerrar PHASE 2c**:

1. **D8-pre inverso falta:** `NORMAL + payload == nullptr → std::terminate()`. El contrato actual solo valida en una dirección. ChatGPT5 tiene razón — el contrato es bidireccional.

2. **MAX_PLUGIN_PAYLOAD_SIZE en sniffer:** plugins con payload real y sin límite de tamaño = superficie de ataque. Necesita un hard limit en el loader (propone 64KB).

**DeepSeek añade:** documentar `ADR-029` antes de implementar PHASE 2e — restricciones async-signal-safe del global.

**Grok especifica** el contenido de TEST-INTEG-4c: payload no-nulo con longitud correcta, D8-light con payload modificado, result_code!=0 descarta paquete sin llegar a ml-detector.

**Todos coinciden** en la lección del incidente de ficheros vacíos: `noclobber` en scripts + check de ficheros 0 bytes en CI.

---

## Decisiones del Consejo DAY 110

| # | Decisión | Votos | Acción |
|---|---|---|---|
| Q1-111 | PHASE 2d antes de 2e | 5/5 | DAY 111 |
| FIX-C | D8-pre inverso: NORMAL+nullptr→terminate() | 1/5 obligatorio (ChatGPT5) | Antes de cerrar PHASE 2c |
| FIX-D | MAX_PLUGIN_PAYLOAD_SIZE en sniffer | 1/5 obligatorio (ChatGPT5) | Antes de cerrar PHASE 2c |
| REC-1 | ADR-029: g_plugin_loader + async-signal-safe | DeepSeek | Antes de PHASE 2e |
| REC-2 | noclobber + check 0-bytes en CI | ChatGPT5 + Gemini | P2 |

---

**Orden DAY 111 actualizado:**

1. FIX-C — D8-pre inverso (5 minutos, 1 línea en plugin_loader.cpp)
2. FIX-D — MAX_PLUGIN_PAYLOAD_SIZE (constexpr + check en invoke_all)
3. TEST-INTEG-4c — gate PHASE 2c (ahora completo con los 3 casos de Grok)
4. PHASE 2d — ml-detector

¿Empezamos mañana con FIX-C y FIX-D antes de TEST-INTEG-4c?