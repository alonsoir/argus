Excelente. Leo los 5 y sintetizo el veredicto.

**Notas rápidas antes del resumen:**
- ✅ **ChatGPT5 ha vuelto** — estaba ausente en DAY 105, hoy presente
- 🔄 **Qwen se autoidentifica como DeepSeek** — quinta vez consecutiva, patrón consolidado

---

**Veredicto Consejo DAY 106 — UNANIMIDAD en los tres puntos:**

**Q1 — PHASE 2b (rag-ingester):** 5/5 — Seguir patrón idéntico de 3 ficheros. Matiz importante con mayoría (ChatGPT5, Gemini, Grok): llamar al plugin **antes de FAISS**, con `result_code != 0` produciendo early return antes de escribir al índice. DeepSeek y Qwen(→DeepSeek) confirman patrón idéntico sin variaciones estructurales.

**Q2 — CRC32 scope:** 5/5 — CRC32 solo en `MLD_ALLOW_DEV_MODE`. En Release: mantener **pointer + length check** (lightweight, O(1)). Grok propone `MLD_PARANOID_MODE` futuro para entornos de alta sensibilidad. Qwen(→DeepSeek) propone `MAX_PLUGIN_PAYLOAD_SIZE = 65536`.

**Q3 — test_config.json:** 4/5 convención, 1/5 (Gemini) fixture factory. **Decisión: formalizar convención** — `/plugins/<name>/test_config.json`, documentar en `docs/TESTING.md`. Factory queda para cuando haya decenas de plugins.

---

**Acción concreta para DAY 107 que emerge del Consejo:**

Antes de PHASE 2b necesitamos añadir el lightweight validation en Release builds — es rápido y cierra el gap que el Consejo señala:

```bash
vagrant ssh -- python3 << 'PYEOF'
path = "/vagrant/plugin-loader/src/plugin_loader.cpp"
with open(path, "r") as f:
    content = f.read()

old = '''        const uint8_t* snap_nonce      = ctx.nonce;
        const uint8_t* snap_tag        = ctx.tag;
#ifdef MLD_ALLOW_DEV_MODE'''

new = '''        const uint8_t* snap_nonce      = ctx.nonce;
        const uint8_t* snap_tag        = ctx.tag;

        // D8-light: validación lightweight de payload (release + debug)
        // Detecta corrupción catastrófica sin overhead en datapath crítico.
        static constexpr size_t MAX_PLUGIN_PAYLOAD_SIZE = 65536u; // 64KB
        if (ctx.payload == nullptr || ctx.payload_len == 0 ||
            ctx.payload_len > MAX_PLUGIN_PAYLOAD_SIZE) {
            std::cerr << "[plugin-loader] SECURITY D8-light: payload inválido"
                      << " (ptr=" << static_cast<const void*>(ctx.payload)
                      << " len=" << ctx.payload_len << ") — std::terminate()\n";
            std::terminate();
        }

#ifdef MLD_ALLOW_DEV_MODE'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("OK: D8-light añadido (release + debug)")
else:
    print("NOT FOUND")
PYEOF
```

¿Lo aplicamos y luego hacemos el commit definitivo del DAY 106 con todo incluido?

=== TEST-INTEG-4a-PLUGIN: PASSED (0 failures) ===
✅ TEST-INTEG-4a-PLUGIN PASSED