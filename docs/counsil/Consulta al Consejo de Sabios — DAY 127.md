## Consulta al Consejo de Sabios — DAY 127

---

**Para:** Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral  
**De:** Alonso Isidoro Román — aRGus NDR (ML Defender)  
**Fecha:** DAY 127 — Jueves 23 de abril de 2026  
**Repositorio:** https://github.com/alonsoir/argus | arXiv:2604.04952

---

### Contexto del proyecto

aRGus NDR es un sistema C++20 de Network Detection and Response open-source para infraestructura crítica (hospitales, escuelas, municipios), desarrollado en solitario con el Consejo de Sabios como framework de revisión arquitectónica. Metodología: Test-Driven Hardening (TDH). Tag activo: `v0.5.2-hardened` + merge DAY 127.

---

### Trabajo completado DAY 125–127

**DAY 125 (ayer):** 5 deudas cerradas con RED→GREEN:
- `DEBT-INTEGER-OVERFLOW-TEST-001` — `memory_utils.hpp` + 4 tests. Property test `PropertyNeverNegative` encontró bug latente en el propio fix F17 (`int64_t` desborda para `LONG_MAX/4096 * 8192`). Fix correcto: aritmética `double` directa.
- `DEBT-SAFE-PATH-TEST-RELATIVE-001` — Test 10 en `safe_path`
- `DEBT-SAFE-PATH-TEST-PRODUCTION-001` — `test_config_parser_traversal` en rag-ingester
- `DEBT-CRYPTO-TRANSPORT-CTEST-001` — permisos `0400` en test fixtures
- `DEBT-GITIGNORE-TEST-SOURCES-001` — 47 fuentes de test versionadas

**DAY 126 (hoy temprano):** 4 deudas críticas cerradas:
- `DEBT-SAFE-PATH-SEED-SYMLINK-001` — `lstat` ANTES de `resolve()`. Hallazgo clave: `fs::is_symlink(resolved)` llega tarde porque `weakly_canonical()` ya resolvió el symlink. La única defensa correcta es `lstat()` sobre el path original. 11/11 tests PASSED.
- `DEBT-CONFIG-PARSER-FIXED-PREFIX-001` — `allowed_prefix` explícito en `rag-ingester` y `firewall-acl-agent`. El prefix nunca se deriva del input. 4/4 + 3/3 tests PASSED.
- `DEBT-PRODUCTION-TESTS-REMAINING-001` — traversal tests RED→GREEN en seed-client (3/3) y firewall-acl-agent (3/3).
- `DEBT-MEMORY-UTILS-BOUNDS-001` — `MAX_REALISTIC_MEMORY_MB` + `RealisticBounds` test. 5/5 PASSED.
- Tag: `v0.5.2-hardened` mergeado a main.

**DAY 127 (hoy):** 1 deuda arquitectónica cerrada:
- `DEBT-DEV-PROD-SYMLINK-001` — Nueva primitiva `resolve_config()` en `safe_path.hpp`. Usa `lexically_normal()` para verificar el prefix ANTES de seguir symlinks. Permite `/etc/ml-defender/*.json → /vagrant/*.json` en dev via `provision.sh`. Corrección de hardcodes en Makefile. 5/5 tests PASSED. 6/6 RUNNING. Mergeado a main.

---

### Hallazgos técnicos destacados DAY 125–127

1. **`fs::is_symlink(resolved)` es inútil post-`weakly_canonical()`** — el symlink ya fue resuelto. `lstat()` sobre el path original es la única defensa correcta para material criptográfico.

2. **`lexically_normal()` vs `weakly_canonical()`** — para configs con symlinks legítimos, la verificación de prefix debe hacerse sobre el path lexical (antes de resolver), no sobre el canónico. Dos primitivas distintas para dos casos de seguridad distintos.

3. **Property testing encontró un bug en el propio fix** — `PropertyNeverNegative` demostró que el fix F17 con `int64_t` también desbordaba para valores extremos. Solo la aritmética `double` es correcta. Esto valida la adopción sistémica de property testing.

---

### Deudas pendientes al inicio de DAY 128

```
🟡 DEBT-PROPERTY-TESTING-PATTERN-001  — formalizar patrón property testing, docs + 3 tests
🟢 DEBT-PROVISION-PORTABILITY-001     — provision.sh portable para hardened-x86/ARM64
🟡 DEBT-SNYK-WEB-VERIFICATION-001     — verificación panel Snyk (informe pendiente de análisis)
⏳ DEBT-PENTESTER-LOOP-001            — ACRL, post todas las deudas anteriores
```

---

### Preguntas al Consejo

**P1 — Arquitectura `safe_path`:**
Tenemos ahora tres primitivas: `resolve()` (general), `resolve_seed()` (sin symlinks, `lstat`), `resolve_config()` (symlinks permitidos, `lexically_normal`). ¿Es esta taxonomía suficiente o anticipáis un cuarto caso de uso que requeriría una primitiva adicional?

**P2 — Property testing sistémico:**
El hallazgo F17 valida el property testing como "net de seguridad bajo los tests unitarios". La propuesta es formalizar el patrón en `docs/testing/PROPERTY-TESTING.md` y aplicarlo sistemáticamente a las superficies críticas (`resolve_seed`, `resolve_config`, `config_parser`). ¿Cuál es la relación correcta entre property tests, fuzzing (`libFuzzer`) y mutation testing para un proyecto como aRGus? ¿En qué orden los introduciríais?

**P3 — DEBT-SNYK-WEB-VERIFICATION-001:**
El panel Snyk muestra resultados que requieren análisis. Dado que el código de producción propio ya tiene los fixes aplicados (ADR-037), ¿cuál es el criterio correcto para distinguir entre vulnerabilidades que requieren fix inmediato vs. las que se aceptan con justificación documentada? ¿Debe el Consejo revisar el informe Snyk antes del merge de cualquier nueva feature?

**P4 — Roadmap hacia FEDER:**
`BACKLOG-FEDER-001` tiene deadline septiembre 2026. Requisitos: ADR-026 mergeado + ADR-029 Variants A/B estables + demo Vagrant pcap reproducible. Dado el ritmo actual (~1 deuda/día), ¿veis el deadline alcanzable? ¿Qué riesgos técnicos principales identificáis para la demo FEDER?

**P5 — Paper arXiv:2604.04952 Draft v17:**
Pendiente: §5.3 "Property Testing as a Security Fix Validator", §5.4 "Dev/Prod Parity via Symlinks", §5.5 "RED→GREEN as Non-Negotiable Merge Gate". ¿Consideráis que los hallazgos DAY 125–127 son suficientemente novedosos para justificar una contribución científica en §5? ¿Qué trabajo relacionado deberíamos citar?

---

*"Via Appia Quality — Un escudo que aprende de su propia sombra."*  
*arXiv:2604.04952 — DAY 127 — 23 de abril de 2026*

---

Copia esta consulta y pásala a cada modelo del Consejo. Cuando tengas el feedback, lo sintetizamos y actualizamos `BACKLOG.md`, `README.md`, el prompt de continuidad y el post de LinkedIn.