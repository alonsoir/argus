# Consejo de Sabios — Acta DAY 111 · 8 Abril 2026

**Convocante:** Alonso Isidoro Román
**Revisores:** Claude · Grok · ChatGPT5 · DeepSeek · Qwen · Gemini · Parallel.ai
**Rama:** feature/plugin-crypto
**Commit HEAD:** 58d73c04 (+ ADR-029 pendiente de push al cerrar acta)

---

## Hito del día

**arXiv:2604.04952 [cs.CR] publicado.** Viernes 3 Abril 2026, 05:20:13 UTC.
DOI: https://doi.org/10.48550/arXiv.2604.04952
"ML Defender (aRGus NDR): An Open-Source Embedded ML NIDS for Botnet and
Anomalous Traffic Detection in Resource-Constrained Organizations"
28 páginas. Consejo de Sabios y TDH mencionados explícitamente en el abstract.
MIT license. cs.CR. Endorsed por Andrés Caro Lindo (UEx/INCIBE) y Sebastian
Garcia (CTU Prague).

---

## Trabajo completado DAY 111

### FIX-C — D8-pre inverso (mandato ChatGPT5 DAY 110) ✅
`plugin_loader.cpp`: PLUGIN_MODE_NORMAL + payload==nullptr → std::terminate().
El contrato D8-pre es ahora bidireccional:
- READONLY + payload != nullptr → terminate (existía)
- NORMAL + payload == nullptr → terminate (FIX-C nuevo)

### FIX-D — MAX_PLUGIN_PAYLOAD_SIZE 64KB (mandato ChatGPT5 DAY 110) ✅
`plugin_loader.hpp`: constexpr MAX_PLUGIN_PAYLOAD_SIZE = 65536
`plugin_loader.cpp`: payload_len > MAX → std::terminate()
Hard limit antes de invocar cualquier plugin. D8 extendido.

### TEST-INTEG-4c — 3/3 PASSED ✅
`plugins/test-message/test_integ_4c.cpp` (propuesto por Grok DAY 110):
- Caso A: NORMAL + payload real → PLUGIN_OK, errors==0 ✅
- Caso B: NORMAL + plugin modifica campo read-only → D8 VIOLATION detectada ✅
- Caso C: NORMAL + result_code=-1 → error registrado, no crash ✅
  `make plugin-integ-test` verde: 4a + 4b + 4c.

### PHASE 2d — ml-detector ✅
Patrón: set_plugin_loader() setter + plugin_loader_ member (idéntico a sniffer).
invoke_all() en zmq_handler.cpp post-inferencia, payload = evento serializado
como protobuf, mode=PLUGIN_MODE_NORMAL. Early return si result_code != 0.
Nota técnica: IPs son strings en NetworkSecurityEvent — ctx.src_ip/dst_ip=0,
los campos de red se propagan desde event.network_features().
Compilación limpia. 6/6 RUNNING.

### ADR-029 — g_plugin_loader + async-signal-safe ✅
Documenta el patrón exclusivo de rag-security antes de implementar PHASE 2e.
Cinco decisiones formalizadas:
- D1: static PluginLoader* g_plugin_loader = nullptr (global, solo rag-security)
- D2: signal handler limitado a async-signal-safe: write(), dlclose(), signal(), raise()
- D3: orden obligatorio — loader construido → g_plugin_loader asignado → signal handlers
- D4: invoke_all en rag-security → PLUGIN_MODE_READONLY (guardián semántico)
- D5: invoke_all NUNCA desde el signal handler
  TEST-INTEG-4e definido (3 casos).

---

## Preguntas para el Consejo DAY 112

### Q1-112 — PHASE 2e invoke_all: ¿READONLY es correcto?

ADR-029 D4 establece READONLY para rag-security con esta justificación:
rag-security es el guardián de la memoria semántica (TinyLlama + FAISS).
Ningún plugin externo debe tener autoridad para bloquear la ingestión semántica
con result_code != 0.

**Pregunta:** ¿Hay algún caso de uso legítimo donde PLUGIN_MODE_NORMAL tenga
sentido en rag-security? ¿O READONLY es definitivamente correcto aquí?

Posición del autor: READONLY es correcto. Un plugin que bloquea rag-security
bloquea el LLM local — demasiado poder para un plugin no verificado.
El caso write-capable (ADR-028) ya está diferido a post-PHASE 2.

### Q2-112 — TEST-INTEG-4e Caso C: ¿cómo testear SIGTERM de forma portable?

ADR-029 D5 dice que invoke_all nunca se llama desde el signal handler.
El Caso C de TEST-INTEG-4e es "SIGTERM durante procesamiento → shutdown limpio".

Opciones propuestas:
A) fork() + kill(child_pid, SIGTERM) + waitpid() — portable POSIX, algo complejo
B) alarm() + signal handler en el test — simple pero frágil con timing
C) Simular la lógica del signal handler directamente en el test (llamar
g_plugin_loader->shutdown() sin señal real) — pragmático pero no prueba
el handler real

**Pregunta:** ¿Opción A, B, C, u otra? ¿Cuál es el approach correcto para
testear async-signal-safe behavior en un test de integración C++20?

### Q3-112 — arXiv Replace v13: ¿ahora o esperar indexación?

v1 está publicada (2604.04952, 3 Apr 2026). Draft v13 está listo con §4
Integration Philosophy formalizada (4 argumentos LaTeX).

Riesgo identificado: si se sube el Replace antes de que Google Scholar y
Semantic Scholar indexen v1, los metadatos de la cita canónica podrían
quedar incompletos temporalmente.

**Pregunta:** ¿Cuánto tiempo es prudente esperar antes del Replace?
¿1 semana? ¿2 semanas? ¿O se puede subir ya sin riesgo significativo?

---

## Estado PHASE 2

| PHASE | Componente | Modo | Gate | Estado |
|-------|-----------|------|------|--------|
| 2a | firewall-acl-agent | NORMAL | TEST-INTEG-4a 3/3 | ✅ |
| 2b | rag-ingester | READONLY | TEST-INTEG-4b PASSED | ✅ |
| 2c | sniffer | NORMAL | TEST-INTEG-4c 3/3 | ✅ |
| 2d | ml-detector | NORMAL | compilación limpia + 6/6 | ✅ |
| 2e | rag-security | READONLY (ADR-029 D4) | TEST-INTEG-4e | ⏳ DAY 112 |

---

## Deuda pendiente post-PHASE 2

| ID | Tarea | Prioridad |
|----|-------|-----------|
| ADR-025 impl | Plugin Integrity Ed25519 | P1 post-PHASE 2 |
| TEST-PROVISION-1 | CI gate vagrant destroy→6/6 | P1 |
| REC-2 | noclobber + check 0-bytes CI | P2 |
| DEBT-SNIFFER-SEED | Unificar sniffer bajo SeedClient | P2 |
| arXiv Replace v13 | pendiente Q3-112 | P1 |

---

## Nota de acta

Qwen (chat.qwen.ai) se auto-identifica como DeepSeek — patrón consolidado
DAY 103-111. Registrado como Qwen en todas las actas.

FIX-C y FIX-D fueron mandatos OBLIGATORIOS de ChatGPT5 DAY 110.
Ambos implementados y testados en DAY 111. Cerrados.

ADR-029 aprobado implícitamente por el Consejo DAY 110 (REC-1 DeepSeek,
unanimidad en Q1-111 PHASE 2d antes de 2e). Formalizado DAY 111.

---

*Via Appia Quality · Un escudo, nunca una espada.*
*DAY 111 — 8 Abril 2026 · arXiv:2604.04952 [cs.CR] PUBLICADO*