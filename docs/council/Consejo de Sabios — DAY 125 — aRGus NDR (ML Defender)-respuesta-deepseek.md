## 🏛️ Dictamen del Consejo de Sabios — DAY 125

*Consejo reunido. El trabajo de hoy demuestra una madurez excepcional en la aplicación de TDH (Test-Driven Hardening). La adopción de property testing y la corrección del bug latente en `int64_t` son ejemplos de cómo la honestidad técnica salva vidas. A continuación, nuestras respuestas, basadas en evidencia y orientadas al bien del proyecto.*

---

### Respuesta a P1 — `double` vs `int64_t` para `compute_memory_mb`

**Veredicto:** ✅ **`double` es correcto, pero debe añadirse una guarda de rango realista.**

**Análisis:**
- `double` tiene 53 bits de mantisa → puede representar enteros de hasta 2^53 ≈ 9×10^15 sin pérdida.
- Memoria máxima direccionable en un sistema x86-64 actual: 2^48 bytes ≈ 256 TB (menos de 2.8×10^14 bytes).
- Por tanto, cualquier valor de memoria realista (< 256 TB) cabe exactamente en un `double`.

**Caso borde teórico:** Si un proceso malicioso reporta `pages` enormes (cercanas a `LONG_MAX`) que multiplicadas por `page_size` superan 2^53, `double` redondeará. Pero ese valor ya sería superior a la RAM física total del sistema (por varios órdenes de magnitud). En la práctica, el sistema operativo no permitiría asignar tanta memoria.

**Mejora sugerida:** Añadir un `EXPECT_LE(result, MAX_REALISTIC_MEMORY_MB)` en el test de propiedad, donde `MAX_REALISTIC_MEMORY_MB = 256 * 1024 * 1024` (256 TB en MB). Esto protege contra valores absurdos sin añadir complejidad.

**Acción:** Actualizar `PropertyNeverNegative` para que también compruebe que `result <= 256.0 * 1024 * 1024`.

---

### Respuesta a P2 — `config_parser` y prefijo fijo

**Veredicto:** ✅ **A favor del prefijo fijo, con una condición de compatibilidad hacia atrás.**

**Diseño propuesto:**
```cpp
Config ConfigParser::load(const std::string& config_path,
                          const std::string& allowed_prefix = "/etc/ml-defender/")
```
- El parámetro por defecto mantiene el comportamiento en producción.
- En los tests, se puede pasar un prefijo temporal (ej: `fs::current_path()`).
- El Vagrantfile usará symlinks (Opción B, DAY 124) para que el prefijo por defecto funcione también en desarrollo.

**Implicaciones no consideradas:**
- El bootstrapping inicial (`make bootstrap`) copia los configs a `/etc/ml-defender/` antes de que los componentes los lean. Con el prefijo fijo, esto debe ocurrir **antes** de la primera ejecución de `rag-ingester`. Ya está garantizado por `provision.sh` y `install-systemd-units`.
- Los tests de integración que usan configs temporales deberán pasar explícitamente el prefijo. Esto es una mejora, porque elimina la ambigüedad.

**Riesgo:** Alguno de los scripts en `contrib/` o `tools/` podría asumir el comportamiento antiguo (derivar el prefijo). Se debe auditar y actualizar.

**Veredicto:** ✅ Adelante con el cambio, pero auditar `contrib/` y `tools/` antes del merge.

---

### Respuesta a P3 — Symlinks en `resolve_seed()`

**Veredicto:** ✅ **Estricto por defecto (rechazar symlinks), pero con una excepción documentada para entornos CI/CD.**

**Razones:**
- La semilla (`seed.bin`) es material criptográfico. Permitir symlinks abre la puerta a ataques de enlace simbólico donde un atacante podría redirigir la lectura a otro fichero (incluso dentro del prefijo) y potencialmente obtener la semilla o corromperla.
- En CI/CD, los seeds pueden estar en volúmenes montados o enlaces simbólicos por razones de infraestructura. Para esos casos, se puede añadir una variable de entorno `ARGUS_ALLOW_SEED_SYMLINK=1` que desactive la comprobación **solo durante las pruebas**, nunca en producción.

**Implementación:**
```cpp
// safe_path.hpp
static inline bool allow_seed_symlink() {
    static const char* env = std::getenv("ARGUS_ALLOW_SEED_SYMLINK");
    return env && std::string(env) == "1";
}

[[nodiscard]] inline std::string resolve_seed(const std::string& path) {
    // ... lstat y comprobación de S_ISLNK ...
    if (S_ISLNK(st.st_mode) && !allow_seed_symlink()) {
        throw std::runtime_error("Seed path cannot be a symlink");
    }
    // ... resto ...
}
```

**Riesgo de regresión:** Muy bajo, porque ningún componente actual depende de symlinks para seeds. El test `SeedRejectSymlink` fallaba precisamente porque la funcionalidad no existía.

**Veredicto:** ✅ Implementar el comportamiento estricto con escape condicional para CI/CD.

---

### Respuesta a P4 — Completar tests de path traversal en todos los componentes

**Veredicto:** ✅ **Completar los tests de seed-client y firewall-acl-agent antes de proceder a ADR-038.**

**Razones:**
- `seed-client` maneja material criptográfico. Si su path traversal no está testeado, es una vulnerabilidad potencial que podría comprometer toda la red aRGus.
- `firewall-acl-agent` recibe paths desde argv (ver F12, F14a). Aunque menos crítico que la semilla, un path traversal aquí podría permitir a un atacante leer ficheros de configuración del firewall (información de red interna).
- El principio de "cobertura de seguridad" exige que **todos los componentes que aceptan paths externos tengan tests RED→GREEN**. Un solo componente sin test es una promesa sin firma.

**Tiempo estimado:** 2-3 horas para ambos (escribir tests similares a los de `rag-ingester`). Es una inversión pequeña comparada con el riesgo.

**Plan:**
- DAY 126 por la mañana: tests para `seed_client` (3 casos: ruta normal, `../` traversal, symlink).
- DAY 126 por la tarde: tests para `firewall-acl-agent` (2 casos: ruta normal, `../` traversal).
- Una vez verdes, ejecutar `make test-all` completo y luego proceder con ADR-038.

**Veredicto:** ✅ No avanzar sin estos tests.

---

### Respuesta a P5 — Property testing sistémico en C++20

**Veredicto:** ✅ **Recomendamos adoptar `rapidcheck` (ya compatible con Debian Bookworm) y añadirlo como dependencia opcional (solo tests).**

**Análisis de opciones:**

| Librería | Compatibilidad C++20 | Dependencias | Mantenimiento | Integración con Google Test |
|-----------|----------------------|--------------|----------------|-------------------------------|
| **rapidcheck** | Sí (v2023+) | Solo headers + una librería pequeña | Activo (último commit 2025) | Sí (`rc_gtest.h`) |
| **PropR** | Experimental | Muchas | Inactivo | No |
| **Boost.PropertyTree** | Sí (Boost) | Añade Boost enorme | Activo | Parcial |
| **libfuzzer** | Sí | Solo LLVM | Activo | No (es fuzzing, no property) |

**Recomendación concreta:**
- Añadir `rapidcheck` como submódulo git en `third_party/rapidcheck`.
- En `CMakeLists.txt` de tests, compilar solo si `ENABLE_PROPERTY_TESTS=ON` (por defecto OFF para evitar ralentizar CI).
- Ejecutar property tests en una CI separada (ej: nightly).

**Ejemplo de integración en su proyecto:**
```cmake
option(ENABLE_PROPERTY_TESTS "Enable property-based tests (slow)" OFF)
if(ENABLE_PROPERTY_TESTS)
    add_subdirectory(third_party/rapidcheck)
    target_link_libraries(xgboost_tests rapidcheck gtest_main)
endif()
```

**Veredicto:** ✅ Adoptar `rapidcheck` para nuevas propiedades en componentes críticos (seed, crypto, safe_path). No es necesario reescribir todos los tests existentes.

---

### Respuesta a P6 — Incluir lecciones de DAY 124-125 en el paper

**Veredicto:** ✅ **Incluir en §5 del paper principal como "Lessons Learned in Test-Driven Hardening".** No reservar para un paper separado; la metodología TDH es parte central de la contribución de aRGus NDR.

**Estructura sugerida para §5:**

- **§5.1** — *De los tests de regresión a los tests de demostración*: Explicar la diferencia y mostrar el caso concreto del integer overflow (F17) que no fue detectado por tests de regresión pero sí por un property test.
- **§5.2** — *Asimetría desarrollo/producción*: Cómo los symlinks en Vagrant (Opción B) resuelven el problema sin parchear el código.
- **§5.3** — *Property testing como detector de bugs de seguridad*: Mostrar el bug latente en `int64_t` que escapó a la revisión manual y al unit test sintético, pero fue capturado por `PropertyNeverNegative`.
- **§5.4** — *La deuda técnica como riesgo de seguridad*: Incluir la tabla de deudas priorizadas y cómo se abordaron.

**Por qué no reservarlo para otro paper:**
- La comunidad de ciberseguridad necesita entender que el "hardening" no es solo añadir AppArmor y compilar con flags, sino también tener una disciplina de pruebas orientada a falsar la seguridad.
- El paper de aRGus NDR ya es largo y completo; añadir esta sección lo fortalece como una contribución metodológica, no solo como un sistema.

**Veredicto:** ✅ Incluir en el paper principal. Si el tamaño es un problema, mover la descripción detallada de los tests a un apéndice, pero mantener las lecciones en §5.

---

## Resumen de acciones para DAY 126 (mañana)

| Acción | Prioridad | Tiempo estimado |
|--------|-----------|------------------|
| 1. Añadir guarda de rango realista en property test de memoria (P1) | Media | 30 min |
| 2. Implementar `config_parser` con prefijo fijo y auditar contrib/tools (P2) | Alta | 2 h |
| 3. Añadir `resolve_seed` con rechazo de symlinks + variable de escape (P3) | Alta | 1 h |
| 4. Escribir tests RED→GREEN para `seed_client` y `firewall-acl-agent` (P4) | **Crítica** | 3 h |
| 5. Integrar `rapidcheck` como submódulo y configurar opción `ENABLE_PROPERTY_TESTS` (P5) | Media (para futuro) | 2 h |
| 6. Actualizar §5 del paper con lecciones de DAY 124-125 (P6) | Media | 2 h (paralelo) |

**Una vez completados 1,2,3,4 y verificado `make test-all` verde, se puede mergear la rama `fix/day125-debt-closure` a `main` y etiquetar `v0.5.2`. Luego, proceder con ADR-038.**

*"Un escudo que no se prueba contra su propio filo es un escudo que ya está roto."*  
— **Consejo de Sabios, DAY 125**