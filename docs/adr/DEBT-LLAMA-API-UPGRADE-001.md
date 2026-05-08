# DEBT-LLAMA-API-UPGRADE-001 — Migrar llama.cpp API deprecated

**Estado:** BACKLOG
**Prioridad:** P2 — post-FEDER (salvo CVE)
**Bloqueado por:** nada — decisión de timing
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

`llama_integration_real.cpp` usa `llama_new_context_with_model` que está marcada
como deprecated en llama.cpp. La nueva API es `llama_init_from_model`.

Warning suprimido temporalmente mediante `set_source_files_properties` en
`rag/CMakeLists.txt` con `-Wno-deprecated-declarations`.

## Criterio de cierre

- llama.cpp publica release estable con `llama_init_from_model` sin breaking changes
- O aparece CVE en la API deprecated (→ upgrade inmediato)
- Test de cierre: `make all 2>&1 | grep -c 'warning:'` = 0 con supresión eliminada

## Referencias

- `rag/src/llama_integration_real.cpp:29`
- `rag/CMakeLists.txt` — supresión activa
- docs/THIRDPARTY-MIGRATIONS.md — tracking
- Consejo DAY 140 (8/8): suprimir ahora, plan de migración obligatorio
