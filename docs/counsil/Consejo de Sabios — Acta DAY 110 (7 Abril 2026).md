# Consejo de Sabios — Acta DAY 110 (7 Abril 2026)

## Nota previa

DAY 110 fue de implementación pura. No se convocó Consejo formal.
Todas las decisiones del Consejo DAY 109 están implementadas y cerradas.
Este documento es un acta de cierre, no una consulta.

---

## Decisiones DAY 109 implementadas ✅

| Q | Decisión Consejo | Implementación DAY 110 |
|---|---|---|
| Q1 | Flag explícito `mode` en `MessageContext` (4/5, Grok en minoría) | ✅ `PluginMode` enum + `mode uint8_t` en `plugin_api.h`. D8-pre: `READONLY+payload!=nullptr → std::terminate()` |
| Q2 | PHASE 2c sniffer con payload real (unanimidad 5/5) | ✅ `invoke_all(ctx_msg)` en `process_raw_event()` con `mode=PLUGIN_MODE_NORMAL` y payload real. Pipeline 6/6 RUNNING |
| Q3 | §4 Integration Philosophy: expandir con 4 argumentos (unanimidad 5/5) | ✅ enumerate LaTeX con latencia, superficie de ataque, sin SPOF, footprint. Compilación limpia Overleaf |
| Q4 | ADR-028: diferir hasta primer plugin write-capable (Grok+DeepSeek 2/2) | ✅ En backlog. No bloqueante para PHASE 2c/2d |

---

## Incidente técnico DAY 110

**Ficheros vacíos en la rama:** `plugin_loader.cpp`, `rag-ingester/src/main.cpp`,
`test_integ_4b.cpp` estaban vacíos (tamaño 0) en `feature/plugin-crypto`.
Los backups `.backup` estaban intactos.

**Causa probable:** script de cierre DAY 109 ejecutó `> fichero` en lugar de escribir.

**Resolución:**
- `plugin_loader.cpp`: restaurado desde `.backup` (386 líneas, íntegro)
- `rag-ingester/src/main.cpp`: restaurado desde `.backup` (543 líneas,
  pero backup era del 30 de marzo, pre-PHASE 2b — PHASE 2b reconstruida desde cero)
- `test_integ_4b.cpp`: reconstruido desde `test_variants.cpp` como base

**Lección:** Los `.backup` son un salvavidas. La reconstrucción de PHASE 2b fue correcta
y compiló limpiamente. No se perdió trabajo lógico, solo código que había que volver
a escribir.

---

## Estado técnico al cierre DAY 110
plugin_api.h:          PluginMode enum + mode field + annotation[64] ✅
plugin_loader.cpp:     D8-pre coherence check + snap_mode ✅
rag-ingester/main.cpp: PHASE 2b reconstruida (PluginLoader + ctx_readonly) ✅
ring_consumer.hpp:     set_plugin_loader() + plugin_loader_ member ✅
ring_consumer.cpp:     invoke_all con payload real en process_raw_event() ✅
sniffer/main.cpp:      set_plugin_loader(&plugin_loader_) ✅
test_integ_4b.cpp:     TEST-INTEG-4b PASSED (Caso A + Caso B) ✅
Paper v13:             §4 con 4 argumentos, compilación limpia ✅
Pipeline:              6/6 RUNNING con binarios actualizados ✅
---

## Preguntas para DAY 111 (si el Consejo considera necesario)

No hay preguntas bloqueantes. La siguiente decisión relevante es:

**Q1-111 (opcional):** PHASE 2e (rag-security) requiere `g_plugin_loader` global
para el signal handler. ¿El Consejo recomienda resolver este patrón antes de PHASE 2d
(ml-detector, más sencillo) o después?

Recomendación del autor: PHASE 2d primero (más simple, mismo patrón que sniffer),
PHASE 2e después (patrón especial con global). No requiere validación del Consejo
a menos que algún miembro identifique un riesgo no visto.

---

## PHASE 2 — Estado

| PHASE | Componente | Estado | Gate |
|---|---|---|---|
| 2a | firewall-acl-agent | ✅ DAY 105-106 | TEST-INTEG-4a |
| 2b | rag-ingester | ✅ DAY 109-110 | TEST-INTEG-4b |
| 2c | sniffer | ✅ DAY 110 (código) | TEST-INTEG-4c ⏳ |
| 2d | ml-detector | ⏳ DAY 111 | TEST-INTEG-4d |
| 2e | rag-security | ⏳ | TEST-INTEG-4e |