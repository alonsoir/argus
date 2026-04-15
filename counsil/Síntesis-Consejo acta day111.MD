Perfecto. Leo las 5 respuestas y sintetizo el veredicto consolidado.

**CONSEJO DAY 111 — VEREDICTO CONSOLIDADO (5/5 respondieron)**

---

**Q1-112 — PHASE 2e READONLY: UNANIMIDAD 5/5 ✅**

READONLY es mandatorio e invariante. Argumentos convergentes: rag-security es guardián semántico (TinyLlama+FAISS), un plugin con NORMAL podría hacer "ataque de silenciamiento" (Gemini), bloquear el LLM sin fallo explícito (ChatGPT5), o degradar silenciosamente el RAG en hospitales (Qwen/DeepSeek). Recomendación adicional de ChatGPT5: hacer invariante duro en código — si component==RAG_SECURITY && mode!=READONLY → terminate(). Llevar a ADR-029 como D6.

---

**Q2-112 — TEST-INTEG-4e Caso C: Opción A fork+kill+waitpid — MAYORÍA 5/5 ✅**

Todos convergen en Opción A. Grok añade: mantener C como test "fast" y A como test "slow" en el Makefile. ChatGPT5 añade verificación de post-condición (logs, recursos liberados). Qwen/DeepSeek añade timeout guardrail de 5 segundos — si el hijo no termina, test falla explícitamente (evidencia de deadlock). Gemini pide documentar que fork() en el test no viola async-signal-safe (el test no es signal handler). Una abstención de Gemini por complejidad (registrada).

---

**Q3-112 — arXiv Replace v13: DIVIDIDO — subir pronto vs esperar 10 días**

| Revisor | Veredicto | Timing |
|---------|-----------|--------|
| ChatGPT5 | Esperar | 7–10 días |
| DeepSeek | Subir ya | 24-48h |
| Gemini | Esperar | Viernes 10 Abr |
| Grok | Subir ya | 24-48h |
| Qwen | Esperar | 10 días hábiles |

**Posición mayoritaria: esperar ~7-10 días (3/5).** Razón: Google Scholar tarda 7-14 días en indexar. Subir ya no daña el DOI pero la versión canónica en Scholar podría ser inconsistente temporalmente. Decisión prudente: **Replace el Viernes 18 Abril** (10 días desde publicación).

---

**Recomendaciones adicionales no pedidas (relevantes):**

- **ChatGPT5:** Documentar que ctx.src_ip/dst_ip=0 en ml-detector — plugins que asuman IP válida se romperán. Añadir a deuda técnica.
- **Gemini:** g_plugin_loader debería ser `std::atomic<PluginLoader*>` o con barreras de memoria para evitar que el signal handler vea puntero parcialmente construido.
- **ChatGPT5 + Grok:** Tras PHASE 2 completa → merge a main → P1: ADR-025 Ed25519 + TEST-PROVISION-1.

---

**Veredicto global: DAY 111 APROBADO SIN CONDICIONES (ChatGPT5, unanimidad implícita).**

---

**Acciones para DAY 112 derivadas del Consejo:**

1. ADR-029 añadir **D6**: invariante duro READONLY en rag-security (ChatGPT5)
2. ADR-029 evaluar **std::atomic\<PluginLoader\*\>** vs puntero raw (Gemini)
3. TEST-INTEG-4e Caso C: **fork+kill+waitpid + timeout 5s** (Qwen/DeepSeek + Grok)
4. Documentar **ctx.src_ip=0 en ml-detector** como deuda técnica (ChatGPT5)
5. **arXiv Replace v13: Viernes 18 Abril** (mayoría 3/5)

¿Arrancamos DAY 112 con PHASE 2e incorporando D6 + atomic?