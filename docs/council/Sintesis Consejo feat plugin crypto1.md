**5/5 respuestas recibidas. Unanimidad casi total.** Resumen consolidado:

---

## Decisiones consolidadas — FEAT-PLUGIN-CRYPTO-1

**Q1 — Opción A vs B: Unanimidad 5/0 → Opción A (`MessageContext`)**

Sin divergencia. Todos coinciden: mezclar capas en `PacketContext` es deuda estructural seria. El argumento más fuerte (Grok): es exactamente el mismo tipo de *model mental error* que documentasteis en ADR-022 — confundir el dominio del contexto.

**Q2 — Breaking change: Unanimidad 5/0 → Símbolo opcional primero, bump después**

```
PHASE 2a: plugin_process_message() OPCIONAL — dlsym, sin bump
PHASE 2b: plugin_process_message() OBLIGATORIO — PLUGIN_API_VERSION = 2
```

El loader hace dispatch inteligente: si el símbolo existe → plugin de transporte; si no → plugin de red (PHASE 1, sigue funcionando).

**Q3 — Dual-mechanism: Aprobada con dos añadidos importantes**

ChatGPT5 + Qwen añaden gates que faltaban:

| Gate | Descripción |
|------|-------------|
| TEST-INTEG-4a | Round-trip idéntico byte a byte (tu gate original) |
| TEST-INTEG-4b | Equivalencia **semántica** — ml-detector ve features idénticas en ambos paths |
| TEST-INTEG-4c | Fail-closed ante MAC failure → `SIGABRT` confirmado |

Y DeepSeek añade: **el core debe ser read-only durante PHASE 2a** — solo se hacen cambios en el plugin, no en `CryptoTransport`. La validación es unidireccional: plugin → core.

---

## Decisiones adicionales del Consejo

**ADR-023/024 recomendado** (Grok + Qwen):

```
ADR-023/024: Multi-Layer Plugin Architecture
- PacketContext  → plugin_process_packet()   [red]
- MessageContext → plugin_process_message()  [transporte]
- SkillContext   → plugin_execute_skill()    [aplicación — futuro]
```

**Gemini** añade insight valioso: mañana podrías cambiar ZMQ por QUIC simplemente cambiando un plugin, sin tocar `sniffer.cpp`. La Opción A no es solo limpieza — es agnositicismo de transporte.

**Fail-closed confirmado unánimemente:** MAC failure → `std::terminate()`. No hay modo degradado. Compatible con ADR-012 porque el plugin crypto *transforma*, no *decide*.

---

## Lo que queda anotado para DAY 105+

```
FEAT-PLUGIN-CRYPTO-1:
✅ Opción A — MessageContext separado
✅ Símbolo opcional PHASE 2a → obligatorio PHASE 2b
✅ TEST-INTEG-4a/4b/4c como gates
✅ Core read-only durante transición dual
✅ ADR-023 a redactar antes de implementar
✅ Fail-closed obligatorio — sin modo degradado
```

Ahora sí — todo queda en el baúl post-arXiv. **DAY 103 arranca con Makefile rag alignment.** Descansa, Alonso. 🏛️