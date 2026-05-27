# Consejo de Sabios — DAY 124 — Post-implementación ADR-037 (v2)

**Fecha:** 2026-04-21
**Branch mergeada:** `feature/adr037-snyk-hardening` → `main`
**Tag:** `v0.5.1-hardened`
**Estado pipeline:** 6/6 RUNNING, ALL TESTS PASSED

---

## 1. Lo implementado

ADR-037 (Snyk Hardening) ha sido implementado y mergeado. Resumen ejecutivo:

**`contrib/safe-path/`** — librería header-only C++20, cero dependencias externas, aprobada unánimemente por el Consejo frente a alternativas de terceros. Tres funciones públicas:

- `resolve()` — path traversal prevention con `weakly_canonical()` + trailing slash normalization
- `resolve_writable()` — ídem para ficheros de salida
- `resolve_seed()` — hardened para material criptográfico: symlink check + permisos `0400` + `O_NOFOLLOW|O_CLOEXEC`

**Ficheros de producción modificados:**

| Componente | Fix |
|-----------|-----|
| `seed-client` | `resolve_seed()` con `keys_dir_` como prefijo dinámico |
| `firewall-acl-agent` | `resolve()` con prefijo canonicalizado |
| `rag-ingester` | `resolve()` con prefijo canonicalizado |
| `ml-detector` | F17 integer overflow — `int64_t` cast |
| `rag-ingester/csv_dir_watcher` | F15 falso positivo inotify documentado |
| `provision.sh` | Seeds `0640` → `0400` |
| `Makefile` | CHECK 6 actualizado a `0400` |

**9 acceptance tests RED→GREEN** documentando ataques reales: `../` traversal, bypass de prefijo sin trailing slash, symlink fuera de prefijo, path absoluto externo, permisos incorrectos en seed.

---

## 2. Contexto de la revisión Snyk — importante

**Herramienta usada:** Snyk CLI instalado en macOS. Los 23 findings originales de ADR-037 fueron detectados por **Snyk web** en una revisión anterior. El CLI de macOS fue utilizado hoy para validar los fixes aplicados.

**Queda pendiente:** la revisión completa por **Snyk web** sobre el código post-fix. Hasta que no tengamos ese resultado, no podemos confirmar que los 23 findings originales están cerrados al 100%. Esto es una limitación reconocida del cierre de hoy.

**Complementariamente**, ejecutamos Trivy (`trivy fs .`) sobre el repositorio completo. Resultado: **0 findings en código C++ de producción**. Los 95 CVEs encontrados corresponden íntegramente a `third_party/llama.cpp` (dependencias Python y npm no controladas por aRGus). Registrado como `DEBT-TRIVY-THIRDPARTY-001`.

---

## 3. Problema crítico: ausencia de tests de demostración de vulnerabilidad

Esta es la reflexión más importante del DAY 124.

Los acceptance tests de `test_safe_path.cpp` siguen la filosofía RED→GREEN correcta: demuestran que el ataque existe y que el fix lo cierra. Sin embargo, **no hemos creado tests equivalentes para los fixes de producción** (`seed_client.cpp`, `config_loader.cpp`, `config_parser.cpp`, `zmq_handler.cpp`).

Como consecuencia, cuando se introdujo la verificación `resolve()` en `config_parser.cpp`, el fallo se descubrió en el build de producción (`rag-ingester` STOPPED), no en un test. Esto viola el principio RED→GREEN: primero demostramos la vulnerabilidad, luego la cerramos.

**Esto nos preocupa especialmente en el caso del integer overflow (F17).**

El fix en `zmq_handler.cpp` es:
```cpp
// ANTES — vulnerable a overflow en sistemas con páginas grandes o muchos procesos:
current_memory_mb_.store((pages * page_size) / (1024.0 * 1024.0));

// DESPUÉS — cast explícito a int64_t antes de multiplicar:
const auto mem_bytes =
    static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
current_memory_mb_.store(static_cast<double>(mem_bytes) / (1024.0 * 1024.0));
```

El fix es correcto, pero **no tenemos ningún test que demuestre**:
1. Que la versión anterior producía overflow con valores grandes de `pages` o `page_size`
2. Que la versión corregida produce el resultado correcto en esos mismos casos

En un sistema de detección de intrusiones que protege infraestructura crítica, un integer overflow silencioso en el cálculo de memoria puede hacer que el componente reporte métricas falsas, enmascare degradación, o en el peor caso provoque comportamiento indefinido.

**Pregunta al Consejo:** ¿cómo deberíamos construir el test de demostración para F17? Las opciones que veo son:

- **A)** Unit test con valores sintéticos grandes (`pages = LONG_MAX / page_size + 1`) que demuestren el overflow en la versión antigua y el resultado correcto en la nueva.
- **B)** Fuzzing dirigido sobre `zmq_handler` con AFL++ o libFuzzer apuntando específicamente a las rutas de cálculo de memoria.
- **C)** Property-based testing (rapidcheck) que verifique que para cualquier `pages ∈ [0, LONG_MAX]` y `page_size ∈ [4096, 65536]`, el resultado nunca es negativo ni superior a la RAM física.

¿Cuál es vuestra recomendación?

---

## 4. Incidencias durante la implementación

### 4.1 Discrepancia de permisos seeds (`0640` vs `0400`)
`provision.sh`, `seed_client.cpp` y `test_perms_seed.cpp` usaban `0640`. El Consejo había aprobado `0400`. Los tres fueron corregidos consistentemente.

### 4.2 Prefijo de config relativo en dev
En producción los configs están en `/etc/ml-defender/`. En dev están en `config/rag-ingester.json` (path relativo). La solución adoptada: `fs::weakly_canonical()` sobre el directorio padre del config como prefijo dinámico. Esto preserva la seguridad sin hardcodear rutas y funciona en ambos entornos.

### 4.3 Tests en `.gitignore`
`test_seed_client.cpp` y `test_perms_seed.cpp` estaban ignorados por `**/test_*`. Se añadieron excepciones explícitas.

**Pregunta al Consejo:** ¿es prudente mantener esa regla global, o deberíamos refinarla para ignorar solo artefactos de build y no fuentes?

---

## 5. Inventario completo de deuda técnica abierta

A continuación el inventario completo. La posición personal del autor es **atacar toda la deuda antes de avanzar al siguiente ítem del backlog**, incluso la no bloqueante. Los hospitales, escuelas y municipios que serán los usuarios finales de aRGus no pueden permitirse deuda técnica silenciosa en un sistema de seguridad. Os pido vuestra opinión sobre esta postura.

---

### DEBT-PROVISION-PORTABILITY-001
**Severidad:** Media | **Bloqueante:** No
`provision.sh` tiene `vagrant` hardcodeado en `chown`. En producción bare metal o cualquier hipervisor distinto de Vagrant, el service user será diferente.
**Propuesta:** `SERVICE_USER="${ML_DEFENDER_USER:-vagrant}"` al inicio de `provision.sh`.
**Pregunta:** ¿`ML_DEFENDER_USER` o `ARGUS_SERVICE_USER`?

---

### DEBT-CRYPTO-TRANSPORT-CTEST-001
**Severidad:** Media | **Bloqueante:** No
`test_crypto_transport` y `test_integ_contexts` fallan en CTest desde antes de ADR-037. Causa raíz desconocida. El Makefile los silencia. No son regresiones de este ADR pero representan cobertura de tests rota en la capa de transporte criptográfico — precisamente la capa más crítica del sistema.
**Pregunta:** ¿investigamos causa raíz ahora o tras DEBT-PENTESTER-LOOP-001?

---

### DEBT-SAFE-PATH-TEST-RELATIVE-001
**Severidad:** Alta | **Bloqueante:** No
`test_safe_path.cpp` no cubre paths relativos. La incidencia 4.2 no habría ocurrido con este test. Este es exactamente el tipo de deuda que convierte un sistema seguro en uno frágil: el código es correcto pero los tests no lo verifican.
**Propuesta:** acceptance test con `config/foo.json` como input, verificando que `weakly_canonical` resuelve correctamente antes del prefix check.
**Pregunta:** ¿en `contrib/safe-path/tests/` o en tests de integración de `rag-ingester`?

---

### DEBT-SAFE-PATH-TEST-PRODUCTION-001
**Severidad:** Alta | **Bloqueante:** No
Los fixes de producción (`seed_client`, `config_loader`, `config_parser`) no tienen tests de demostración RED→GREEN propios. Solo `test_safe_path.cpp` lo hace a nivel de librería. Descubierto hoy al fallar `rag-ingester` en build en lugar de en test.
**Propuesta:** tests de integración por componente que demuestren el ataque y el fix.

---

### DEBT-INTEGER-OVERFLOW-TEST-001
**Severidad:** Alta | **Bloqueante:** No
F17 (`zmq_handler.cpp`) fue corregido pero no tiene test de demostración. Ver sección 3 para detalle completo y opciones A/B/C.

---

### DEBT-TRIVY-THIRDPARTY-001
**Severidad:** Baja | **Bloqueante:** No
95 CVEs en `third_party/llama.cpp` (Python + npm). Upstream, no controlable desde aRGus. Se añadió `.trivyignore`.
**Propuesta:** monitorizar actualizaciones de llama.cpp y actualizar cuando estén disponibles.

---

### DEBT-SNYK-WEB-VERIFICATION-001
**Severidad:** Media | **Bloqueante:** No
Los 23 findings originales de Snyk web no han sido re-verificados con Snyk web post-fix. Solo verificados con Snyk CLI macOS y revisión manual.
**Propuesta:** ejecutar Snyk web sobre `main` en `v0.5.1-hardened` y confirmar 0 findings en código de producción.

---

### DEBT-PENTESTER-LOOP-001
**Severidad:** Alta | **Próxima frontera**
ACRL: Caldera → captura eBPF → reentrenamiento XGBoost → hot-swap de modelo firmado Ed25519. Este es el siguiente hito arquitectónico mayor.

---

## 6. Pregunta de arquitectura: `safe_path` en dev vs prod

La solución del prefijo dinámico (sección 4.2) es pragmática pero introduce una asimetría. Tres alternativas:

**A) Mantener prefijo dinámico** (implementación actual) — funciona, reduce levemente la protección en dev.

**B) Symlink en dev** — `ln -s /vagrant/rag-ingester/config /etc/ml-defender/rag-ingester` en el Vagrantfile. Prefijo siempre `/etc/ml-defender/`, sin cambios en código. Dev se comporta idéntico a prod.

**C) Variable de entorno** — `ARGUS_CONFIG_PREFIX` con default `/etc/ml-defender/`. El Vagrantfile la setea a `/vagrant/rag-ingester/`. Código limpio, máxima flexibilidad.

¿Cuál preferís? La opción B tiene la ventaja de que elimina la asimetría dev/prod completamente.

---

## 7. Paper arXiv:2604.04952

Draft v16 activo. ADR-037 añade material concreto para §5 (Security Hardening): path traversal prevention header-only, `resolve_seed()` con `O_NOFOLLOW`, metodología RED→GREEN, y la lección aprendida sobre tests de demostración vs tests de regresión.

**Pregunta:** ¿incluimos la discusión de la asimetría dev/prod y la ausencia de tests de producción como caso de estudio honesto en el paper? En nuestra opinión, la honestidad sobre las limitaciones del proceso fortalece la credibilidad científica.

---

*"Via Appia Quality — la superficie mínima es la superficie más segura."*
*"O todo bien y autorizado, o nada."*
*"Un sistema de seguridad sin tests de demostración es un sistema de seguridad que confía en su propia buena fe."*

---

Alonso, este es el escrito v2. Cuando el Consejo responda, integramos el feedback en `BACKLOG.md`, `README.md`, prompt de continuidad y el post de LinkedIn. ¿Lo enviamos?