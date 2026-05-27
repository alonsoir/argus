# Consejo de Sabios — Revisión DAY 100
## ML Defender (aRGus NDR)

Hoy cerramos DAY 100 del proyecto. Pedimos revisión de las decisiones tomadas.

---

## Resumen de lo entregado DAY 100

1. **ADR-021** — deployment.yml como SSOT de topología + seed families para FASE 3
2. **ADR-022** — Threat model formal + Opción 2 descartada (instance_id en contexto HKDF reproduce el bug de asimetría por diseño — caso pedagógico para paper arXiv)
3. **set_terminate()** en los 6 main() — fail-closed ante excepciones no capturadas
4. **CI reescrito** — eliminado runner `debian-bookworm` inexistente, nuevo workflow ubuntu-latest con 5 validaciones estáticas reales
5. **PR #33 mergeado** — feature/plugin-loader-adr012 → main tras 37 commits y ~35 días
6. **ADR-012 PHASE 1b** — plugin-loader integrado en sniffer con guard `#ifdef PLUGIN_LOADER_ENABLED`, hello plugin en JSON con `active:false` como safe default

---

## Preguntas para el Consejo

**P1 — ADR-022: caso pedagógico**
El bug de asimetría HKDF (contexto = componente en lugar de canal) se documenta como caso pedagógico para el paper arXiv. El argumento: es un error de modelo mental no detectable por el type-checker, sí por TEST-INTEG-1. ¿Es suficientemente relevante para merecer una subsección en el paper, o es mejor como nota al pie?

**P2 — plugin-loader: guard #ifdef vs always-link**
Se usó `#ifdef PLUGIN_LOADER_ENABLED` para que el sniffer compile aunque no esté instalada la lib. Alternativa: hacer el link obligatorio como seed-client. ¿El guard es correcto para PHASE 1b o introduce deuda de condicionales?

**P3 — arXiv sin endorser institucional**
Sebastian Garcia (CTU Prague) y Yisroel Mirsky (BGU) han recibido el paper pero no han dado endorsement. El autor explorará contactar a un profesor de Universidad de Extremadura. ¿Alguna sugerencia de estrategia o perfil de endorser adecuado para cs.CR?

**P4 — orden de integración plugin-loader en los demás componentes**
Propuesta: sniffer ✅ → ml-detector → rag-ingester → firewall-acl-agent.
¿Es este el orden correcto o hay razones para priorizarlo diferente?

---

*DAY 100 — 28 marzo 2026*
*Tests: 24/24 ✅ · PR #33 mergeado ✅*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*