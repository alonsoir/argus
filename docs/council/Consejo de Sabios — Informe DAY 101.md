# Consejo de Sabios — Informe DAY 101
## 29 marzo 2026

**De:** Alonso Isidoro Roman
**Para:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai
**Tests:** 24/24 ✅ · Branch: feature/bare-metal-arxiv

---

## Resumen ejecutivo

DAY 101 fue un día de corrección técnica y expansión sistemática.
Descubrimos y corregimos un bug en el parser del PluginLoader,
validamos ADR-012 PHASE 1b en sniffer, lo expandimos a ml-detector,
y enviamos el email al tercer candidato a endorser arXiv.

---

## Bug corregido: extract_enabled_list → extract_enabled_objects

**Síntoma:** el smoke test del sniffer producía WARNINGs:
```
[plugin-loader] WARNING: plugin 'name' not found at /usr/lib/.../libplugin_name.so
[plugin-loader] WARNING: plugin 'path' not found at /usr/lib/.../libplugin_path.so
[plugin-loader] WARNING: plugin 'active' not found ...
[plugin-loader] WARNING: plugin 'comment' not found ...
```

**Causa raíz:** `extract_enabled_list()` fue escrita para arrays de strings `["a","b"]`
pero el JSON usa array de objetos `[{name, path, active, comment}]`.
El parser extraía todas las strings con comillas — incluyendo las claves.

**Fix:** `extract_enabled_objects()` — itera objetos `{}` dentro del array,
filtra `active:false`, lee `name` y `path` explícitos del descriptor.

**Resultado post-fix:**
```
[plugin:hello] init OK — name=hello config={}
[plugin-loader] INFO: loaded plugin 'hello' v0.1.0
✅ [plugin-loader] Plugins loaded (ADR-012 PHASE 1b)
[plugin:hello] shutdown OK — invocations=0 overruns=0 errors=0
```
Cero WARNINGs. Init → run → shutdown limpio.

---

## ADR-012 PHASE 1b — ml-detector validado

Mismo patrón que sniffer aplicado a ml-detector:
- `CMakeLists.txt`: find_library + target_link + `PLUGIN_LOADER_ENABLED`
- `main.cpp`: `#ifdef` guard + PluginLoader instanciado + load + shutdown
- `ml_detector_config.json`: sección `plugins` con hello plugin

Smoke test idéntico al sniffer: init OK → shutdown OK, invocations=0, overruns=0, errors=0.

**Patrón canónico establecido:**
- Plugins individuales → `/usr/lib/ml-defender/plugins/`
- Librería del loader → `/usr/local/lib/libplugin_loader.so`

---

## Endorser arXiv — tercer contacto

Email enviado a **Prof. Andrés Caro Lindo** (`andresc@unex.es`),
Director de la Cátedra INCIBE-UEx-EPCC, Universidad de Extremadura.
Fue profesor de Laboratorio de Programación 2 del autor.
PDF v6 adjunto. Esperando respuesta.

Estado del panel de endorsers:
- Sebastian Garcia (CTU Prague): ✅ respondió
- Yisroel Mirsky (BGU): ⏳ sin respuesta
- Andrés Caro Lindo (UEx): ⏳ enviado hoy

---

## Preguntas para el Consejo

**Q1 — Orden de integración plugin-loader:**
El Consejo DAY 100 estableció: sniffer ✅ → ml-detector ✅ → **firewall** → rag-ingester.
¿Confirmáis que firewall-acl-agent es el siguiente antes que rag-ingester?
¿Hay alguna razón técnica para cambiar el orden?

**Q2 — PAPER-ADR022:**
La subsección "HKDF Context Symmetry" debe documentar el bug de asimetría
como caso pedagógico del TDH. ¿Sugerís ubicarla en §5.5 (Cryptographic Transport)
o como subsección independiente en §6 (Consejo de Sabios / TDH)?

**Q3 — Plugin invocations=0:**
El hello plugin arranca y hace shutdown pero `invocations=0` porque no hay
paquetes reales en el smoke test. ¿Debería haber un test unitario específico
que invoque `invoke_all()` con un PacketContext sintético para validar
el path completo? ¿O es suficiente con el smoke test E2E de DAY 101?

---

*DAY 101 — 29 marzo 2026*
*Tests: 24/24 ✅*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*