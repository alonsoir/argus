---

# Consejo de Sabios — DAY 125 — aRGus NDR (ML Defender)

## Contexto

Rama: `fix/day125-debt-closure` | Tag activo: `v0.5.1-hardened` → pendiente de tag `v0.5.2` post-merge  
Pipeline: 6/6 RUNNING tras `vagrant halt + make up + make bootstrap` desde VM fría  
Metodología: TDH (Test-Driven Hardening) — Via Appia Quality  
Regla de oro: *"Un fix sin test de demostración es una promesa sin firma."*

---

## Qué hemos hecho hoy (DAY 125)

### 1. DEBT-GITIGNORE-TEST-SOURCES-001 ✅ CERRADO
La regla `**/test_*` en `.gitignore` ignoraba todas las fuentes de test. Fix: `**/build/**/test_*` + excepciones `!test_*.cpp` / `!test_*.hpp`. Consecuencia positiva: 47 fuentes de test que llevaban tiempo sin versionar han quedado incorporadas al repositorio en un commit atómico separado.

### 2. DEBT-INTEGER-OVERFLOW-TEST-001 ✅ CERRADO
El fix F17 de DAY 124 (cast a `int64_t` en `compute_memory_mb`) tenía un bug latente: `LONG_MAX/4096 * 8192` sigue desbordando `int64_t`. El test de propiedad `PropertyNeverNegative` lo detectó en tiempo de ejecución. Fix correcto: aritmética `double` directa. Nueva función pura `compute_memory_mb()` extraída a `memory_utils.hpp` — header-only, cero dependencias, testeable de forma aislada.  
4 tests RED→GREEN: unit sintético (A), valor extremo (GREEN), property nunca negativo (C), property monotonicidad (C).  
**Lección:** el property test encontró un bug que el unit test sintético no cubría. Esto valida la Opción C del Consejo DAY 124.

### 3. DEBT-SAFE-PATH-TEST-RELATIVE-001 ✅ CERRADO
Test 10 `RelativePathResolvesBeforePrefixCheck` añadido a `contrib/safe-path/tests/test_safe_path.cpp`. Reproduce la incidencia DAY 124 (rag-ingester STOPPED por falso positivo con path relativo). PASSED.  
**Hallazgo colateral:** `SeedRejectSymlink` fallaba antes de nuestro cambio (confirmado con `git stash`). Registrado como `DEBT-SAFE-PATH-SEED-SYMLINK-001` en BACKLOG.

### 4. DEBT-SAFE-PATH-TEST-PRODUCTION-001 ✅ CERRADO (rag-ingester)
Nuevo test `test_config_parser_traversal.cpp` con 3 casos: `RejectNonExistentPath`, `RejectEmptyPath`, `ProductionConfigLoadsCorrectly` (usa config real de producción — el JSON es la ley). 3/3 PASSED. Registrado en ctest como Test #2, recogido automáticamente por `make test-all` línea 1006.  
**Hallazgo de diseño:** `config_parser` deriva el prefix de `safe_path` del parent del propio `config_path` de entrada. Esto impide rechazar traversal relativo. Registrado como `DEBT-CONFIG-PARSER-FIXED-PREFIX-001` en BACKLOG.

### 5. DEBT-CRYPTO-TRANSPORT-CTEST-001 ✅ CERRADO
Causa raíz: `test_crypto_transport.cpp` y `test_integ_contexts.cpp` creaban `seed.bin` con `owner_read | owner_write` = `0600`, pero `safe_path::resolve_seed` exige estrictamente `0400`. Fix: `perm_options::replace` con solo `owner_read` en ambos ficheros. 5/5 ctest PASSED (100%).

### Gate final
`vagrant halt → make up → make bootstrap → make test-all`: **ALL TESTS PASSED** desde VM fría.

---

## Qué haremos mañana (DAY 126)

Según el BACKLOG actualizado:

1. **DEBT-SNYK-WEB-VERIFICATION-001** (DAY 126) — verificación web de los 23 CVEs Snyk identificados en DAY 117. Determinar cuáles son falsos positivos y cuáles requieren remediation antes de ADR-036.
2. **DEBT-SAFE-PATH-SEED-SYMLINK-001** — `resolve_seed()` no rechaza symlinks dentro del prefix. Fix: `lstat` + `O_NOFOLLOW`. Test: `SafePathTest.SeedRejectSymlink` RED→GREEN.
3. **DEBT-CONFIG-PARSER-FIXED-PREFIX-001** — `ConfigParser::load` debe aceptar `allowed_prefix` fijo en lugar de derivarlo del input. Fix de diseño con test RED→GREEN.

---

## Preguntas al Consejo

### Preguntas sobre lo realizado hoy

**P1 — double vs int64_t para compute_memory_mb:**  
Elegimos aritmética `double` directa porque `int64_t` desborda para valores extremos como `LONG_MAX/4096 * 8192`. `double` tiene 53 bits de mantisa, suficiente para cualquier valor realista de memoria de proceso. ¿Veis algún caso de borde donde `double` también podría producir un resultado incorrecto? ¿Debería añadirse un `EXPECT_LE(result, MAX_REALISTIC_MEMORY_MB)` como guard adicional?

**P2 — config_parser y prefix fijo:**  
El diseño actual de `config_parser` deriva el prefix de `safe_path` del directorio padre del propio fichero de configuración. Esto es una limitación de seguridad: si el atacante controla el path, controla el prefix. La solución es un segundo parámetro `allowed_prefix` con valor por defecto `/etc/ml-defender/`. ¿Estáis de acuerdo con este diseño? ¿Hay implicaciones en el bootstrapping o en los tests de integración que no hayamos considerado?

**P3 — DEBT-SAFE-PATH-SEED-SYMLINK-001:**  
`resolve_seed()` no rechaza symlinks dentro del prefix. El test `SeedRejectSymlink` falla. El fix obvio es `lstat()` + verificar `S_ISLNK`. Sin embargo, en algunos entornos de CI/CD los seeds pueden estar en symlinks legítimos. ¿Debería el fix ser estricto (rechazar todo symlink) o configurable (flag `allow_symlink` con default `false`)? ¿Qué riesgo de regresión veis?

### Preguntas orientadas al futuro

**P4 — Cobertura de tests de producción:**  
DAY 125 ha revelado que varios componentes (seed-client, firewall-acl-agent) aún no tienen tests de path traversal RED→GREEN propios. El Consejo DAY 124 identificó esto como la deuda más importante. ¿Recomendáis completar los tests restantes antes de abrir ADR-038, o es suficiente con rag-ingester como componente representativo y procedemos con el siguiente ADR?

**P5 — Property testing sistémico:**  
El property test `PropertyNeverNegative` encontró un bug real que el unit test sintético no detectó. ¿Recomendáis adoptar property testing de forma más sistemática en el proyecto? ¿Existe una librería de property testing para C++20 compatible con nuestro entorno Debian Bookworm que no añada dependencias problemáticas?

**P6 — Paper §5 y lecciones DAY 124-125:**  
El paper arXiv:2604.04952 (Draft v16) tiene §5 pendiente de actualización. Las lecciones de DAY 124-125 son relevantes: asimetría dev/prod, tests de demostración como requisito de merge, property testing como detector de bugs en fixes de seguridad. ¿Recomendáis incluir estos hallazgos en §5 como lecciones metodológicas formales, o reservarlos para un paper de seguimiento sobre TDH?

---

*"Via Appia Quality — Un escudo que aprende de su propia sombra."*  
*"Un fix sin test de demostración es una promesa sin firma." — Qwen, Consejo DAY 124*  
*"Un escudo sin tests es un escudo de papel." — Kimi, Consejo DAY 124*

---

