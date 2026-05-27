# aRGus NDR — Deuda Técnica DAY 125
## Documentación formal para Test-Driven Hardening (TDH)

**Proyecto:** aRGus NDR (ML Defender)  
**Repositorio:** https://github.com/alonsoir/argus  
**Tag activo:** `v0.5.1-hardened`  
**Fecha:** DAY 125 (2026-04-22)  
**Autor:** Alonso Isidoro Román  
**Metodología:** Test-Driven Hardening (TDH)

> **Regla de oro TDH (Consejo 7/7, DAY 124):**  
> *"Un fix sin test de demostración es una promesa sin firma."* — Qwen  
> *"Un escudo sin tests es un escudo de papel."* — Kimi

---

## Índice

1. [DEBT-INTEGER-OVERFLOW-TEST-001](#debt-integer-overflow-test-001) 🔴 Bloqueante
2. [DEBT-SAFE-PATH-TEST-RELATIVE-001](#debt-safe-path-test-relative-001) 🔴 Bloqueante
3. [DEBT-SAFE-PATH-TEST-PRODUCTION-001](#debt-safe-path-test-production-001) 🔴 Bloqueante
4. [DEBT-SNYK-WEB-VERIFICATION-001](#debt-snyk-web-verification-001) 🟡 Bloqueante
5. [DEBT-CRYPTO-TRANSPORT-CTEST-001](#debt-crypto-transport-ctest-001) 🟡 Bloqueante
6. [DEBT-DEV-PROD-SYMLINK-001](#debt-dev-prod-symlink-001) 🟢 No bloqueante
7. [DEBT-PROVISION-PORTABILITY-001](#debt-provision-portability-001) 🟢 No bloqueante
8. [DEBT-PENTESTER-LOOP-001](#debt-pentester-loop-001) ⏳ Post-deuda

---

## DEBT-INTEGER-OVERFLOW-TEST-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-INTEGER-OVERFLOW-TEST-001 |
| **Severidad** | 🔴 Alta — Bloqueante |
| **Origen** | DAY 124 — ADR-037 (Snyk hardening, fix F17) |
| **Componente** | `ml-detector/src/zmq_handler.cpp` |
| **Estado** | Fix existe. Test de demostración: NO existe. |
| **Target** | DAY 125 |

### Descripción del problema

Durante el análisis Snyk de DAY 124 (ADR-037), se identificó un integer overflow en el cálculo de métricas de memoria en `zmq_handler.cpp`. El cálculo original usaba un tipo entero de 32 bits (`int`) para acumular bytes de payload. Con valores de payload superiores a `INT_MAX` (2.147.483.647 bytes), el resultado wrappea silenciosamente a negativo, produciendo comportamiento indefinido (UB en C++).

El fix consiste en un cast explícito a `int64_t` (F17). El fix **está en producción desde DAY 124**, pero no existe ningún test que:
1. Demuestre que el código antiguo falla con valores extremos (RED).
2. Demuestre que el código nuevo produce resultados correctos (GREEN).

### Por qué importa en infraestructura crítica

Un overflow silencioso en métricas de memoria puede:
- Enmascarar degradación del sistema (métricas negativas interpretadas como "todo bien").
- Producir UB en operaciones aritméticas posteriores.
- En un NDR para hospitales, métricas corruptas son una vulnerabilidad de disponibilidad encubierta.

### Cómo demostrar que el problema existe (RED)

Crear una función pura extraída del cálculo original con tipo `int`:

```cpp
// Código ANTIGUO (a recrear en test para demostración)
int compute_memory_mb_legacy(int bytes) {
    return bytes / (1024 * 1024);  // overflow si bytes > INT_MAX
}
```

Ejecutar con `bytes = 2147483648` (INT_MAX + 1):
- Resultado esperado correcto: `2048` MB
- Resultado con tipo `int`: negativo o incorrecto (UB)

### Plan TDH

**PASO 1 — Extraer función pura testeable**

En `ml-detector/src/zmq_handler.cpp`, extraer el cálculo a función libre:

```cpp
// Función pura, testeable de forma aislada
inline int64_t compute_memory_mb(int64_t bytes) {
    return bytes / (1024LL * 1024LL);
}
```

**PASO 2 — Crear test RED (tipo antiguo)**

```cpp
// test_integer_overflow.cpp
TEST(IntegerOverflow, LegacyIntOverflowsAtLargeValues) {
    int legacy_result = static_cast<int>(2147483648LL) / (1024 * 1024);
    // Con int: resultado es negativo o incorrecto
    EXPECT_LT(legacy_result, 0);  // Demuestra el problema
}
```

**PASO 3 — Crear test GREEN (fix aplicado)**

```cpp
TEST(IntegerOverflow, FixedInt64HandlesLargeValues) {
    EXPECT_EQ(compute_memory_mb(2147483648LL), 2048LL);
    EXPECT_EQ(compute_memory_mb(0LL), 0LL);
    EXPECT_EQ(compute_memory_mb(1024LL * 1024LL), 1LL);
}
```

**PASO 4 — Property test ligero**

```cpp
TEST(IntegerOverflow, NeverNegativeForPositiveInput) {
    std::vector<int64_t> values = {
        0LL, 1LL, 1024LL, 1024LL*1024LL,
        2147483648LL,           // INT_MAX + 1
        static_cast<int64_t>(LLONG_MAX / 1024)
    };
    for (auto v : values) {
        EXPECT_GE(compute_memory_mb(v), 0LL) << "Overflow for value: " << v;
    }
}
```

**Gate de cierre:** 3–5 tests PASSED · Sin dependencias nuevas · `make test-all` verde.

---

## DEBT-SAFE-PATH-TEST-RELATIVE-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-SAFE-PATH-TEST-RELATIVE-001 |
| **Severidad** | 🔴 Alta — Bloqueante |
| **Origen** | DAY 124 — ADR-037 (safe_path, 9 acceptance tests) |
| **Componente** | `contrib/safe-path/` |
| **Estado** | Librería implementada. Test explícito de ruta relativa `../`: NO existe nombrado. |
| **Target** | DAY 125 |

### Descripción del problema

En DAY 124 se creó `contrib/safe-path/`, librería header-only C++20 con 9 acceptance tests RED→GREEN. Los tests cubren symlinks y rutas fuera de prefijo absoluto. Sin embargo, **no existe un test named y explícito** que demuestre que una ruta relativa con traversal (`../`) es bloqueada antes de cualquier llamada a `open()`.

Sin ese test, no hay garantía de regresión si alguien modifica la lógica de normalización de rutas en el futuro.

### Por qué importa en infraestructura crítica

Path traversal con rutas relativas es uno de los vectores de ataque más comunes en sistemas de ficheros (CWE-22). Un atacante con control parcial sobre el argumento de configuración podría intentar:

```
../../../../etc/passwd
../../../etc/shadow
../../keys/other_component.seed
```

La librería debe rechazar esto con `SECURITY VIOLATION` **antes** de abrir el fichero. Sin test, no hay contrato firmado.

### Cómo demostrar que el problema existe (RED)

Demostrar que el sistema operativo por sí solo NO protege:

```cpp
// Sin safe_path: el OS acepta rutas relativas
int fd = open("../etc/passwd", O_RDONLY);
EXPECT_GE(fd, 0);  // El OS lo abre sin problema — esto es el peligro
if (fd >= 0) close(fd);
```

Esto es el RED: demuestra que sin la librería, el ataque funciona.

### Plan TDH

**PASO 1 — Crear `contrib/safe-path/tests/test_safe_path_relative.cpp`**

```cpp
#include "safe_path.hpp"
#include <gtest/gtest.h>
#include <stdexcept>
#include <fcntl.h>
#include <unistd.h>

// RED: Sin safe_path, el OS acepta rutas relativas con traversal
TEST(SafePathRelative, OsAllowsTraversalWithoutProtection) {
    int fd = open("../etc/passwd", O_RDONLY);
    // Si existe el fichero, fd >= 0 — el OS no protege
    // Este test documenta el peligro, no lo consideramos fallo del test
    if (fd >= 0) {
        close(fd);
        SUCCEED() << "OS allows traversal — safe_path protection is necessary";
    } else {
        SUCCEED() << "File not accessible but OS did not throw — safe_path still needed";
    }
}

// GREEN: Con safe_path, ruta relativa con traversal lanza SECURITY VIOLATION
TEST(SafePathRelative, RejectsRelativeTraversal) {
    EXPECT_THROW(
        safe_path::resolve("../etc/passwd", "/etc/argus"),
        std::runtime_error
    );
}

// GREEN: El mensaje de error contiene SECURITY VIOLATION
TEST(SafePathRelative, ErrorMessageContainsSecurityViolation) {
    try {
        safe_path::resolve("../etc/passwd", "/etc/argus");
        FAIL() << "Expected runtime_error";
    } catch (const std::runtime_error& e) {
        EXPECT_NE(std::string(e.what()).find("SECURITY VIOLATION"), std::string::npos);
    }
}

// GREEN: Ruta legítima dentro del prefijo no lanza excepción
TEST(SafePathRelative, AcceptsLegitimatePathUnderPrefix) {
    EXPECT_NO_THROW(
        safe_path::resolve("/etc/argus/config.json", "/etc/argus")
    );
}

// GREEN: Variantes de traversal también bloqueadas
TEST(SafePathRelative, RejectsMultipleTraversalLevels) {
    EXPECT_THROW(safe_path::resolve("../../etc/shadow", "/etc/argus"), std::runtime_error);
    EXPECT_THROW(safe_path::resolve("../../../root/.ssh/id_rsa", "/etc/argus"), std::runtime_error);
}
```

**PASO 2 — Registrar en CMakeLists.txt de safe-path**

```cmake
add_executable(test_safe_path_relative tests/test_safe_path_relative.cpp)
target_link_libraries(test_safe_path_relative PRIVATE safe_path GTest::gtest_main)
add_test(NAME test_safe_path_relative COMMAND test_safe_path_relative)
```

**Gate de cierre:** 5 tests PASSED · Registrados en CTest · `make test-all` verde.

---

## DEBT-SAFE-PATH-TEST-PRODUCTION-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-SAFE-PATH-TEST-PRODUCTION-001 |
| **Severidad** | 🔴 Alta — Bloqueante |
| **Origen** | DAY 124 — ADR-037 (integración safe_path en 3 componentes) |
| **Componentes** | `libs/seed-client/`, `firewall-acl-agent/`, `rag-ingester/` |
| **Estado** | Integración en producción. Tests de integración por componente: NO existen. |
| **Target** | DAY 125 |

### Descripción del problema

ADR-037 integró `safe_path` en tres componentes de producción: `seed-client`, `firewall-acl-agent` y `rag-ingester`. El merge pasó `make test-all` en verde. Sin embargo, **ningún test existente ejerce el path traversal en el contexto real de cada componente**.

La diferencia crítica:
- Los tests de `contrib/safe-path/` validan la **librería en aislamiento**.
- Los tests de producción deben validar que la **integración concreta** (prefijo correcto, función llamada en el sitio correcto, path canonicalizado antes de pasarlo) también funciona.

La librería puede ser correcta y la integración puede estar rota. Sin test por componente, el fix es una promesa, no una garantía.

### Por qué importa en infraestructura crítica

Cada componente tiene su propio prefijo de rutas legítimas:
- `seed-client`: `keys_dir_` (dinámico, configurado en runtime)
- `firewall-acl-agent`: prefijo de configuración canonicalizado
- `rag-ingester`: directorio de configuración del componente

Un error de integración (prefijo hardcodeado incorrecto, función llamada con los argumentos invertidos, path no canonicalizado antes de pasar a `resolve()`) no sería detectado por los tests de la librería.

### Cómo demostrar que el problema existe

Para cada componente: escribir el test que llama a la función de carga real con un path malicioso. **Si el test ya pasa verde**, la integración está correcta y el test queda como documentación de regresión. **Si el test falla en rojo**, encontramos un gap real — esto es el hallazgo valioso.

### Plan TDH — 3 sub-tests, uno por componente

---

#### Sub-test A: seed-client

**Archivo:** `libs/seed-client/tests/test_seed_client_traversal.cpp`

```cpp
#include "seed_client.hpp"
#include <gtest/gtest.h>

TEST(SeedClientSecurity, RejectsTraversalOutsideKeysDir) {
    // keys_dir_ apunta a /tmp/test_keys en el test
    SeedClient client("/tmp/test_keys");
    
    // RED: path con traversal fuera de keys_dir
    EXPECT_THROW(
        client.load_seed("../../../etc/shadow"),
        std::runtime_error
    ) << "seed-client debe rechazar traversal fuera de keys_dir_";
}

TEST(SeedClientSecurity, AcceptsLegitimatePathInsideKeysDir) {
    // GREEN: path legítimo dentro de keys_dir
    // (El fichero puede no existir, pero no debe lanzar SECURITY VIOLATION)
    SeedClient client("/tmp/test_keys");
    
    EXPECT_NO_THROW(
        // Debe lanzar file_not_found, NO security_violation
        [&]() {
            try {
                client.load_seed("/tmp/test_keys/component.seed");
            } catch (const std::runtime_error& e) {
                std::string msg(e.what());
                EXPECT_EQ(msg.find("SECURITY VIOLATION"), std::string::npos)
                    << "No debe lanzar SECURITY VIOLATION para ruta legítima";
            }
        }()
    );
}
```

---

#### Sub-test B: firewall-acl-agent

**Archivo:** `firewall-acl-agent/tests/test_config_traversal.cpp`

```cpp
#include "config_loader.hpp"
#include <gtest/gtest.h>

TEST(FirewallConfigSecurity, RejectsTraversalInConfigPath) {
    ConfigLoader loader("/etc/argus/firewall");
    
    EXPECT_THROW(
        loader.load("../../../etc/passwd"),
        std::runtime_error
    ) << "config_loader debe rechazar traversal fuera del prefijo";
}

TEST(FirewallConfigSecurity, AcceptsLegitimateConfigPath) {
    ConfigLoader loader("/etc/argus/firewall");
    
    // Debe fallar por fichero no encontrado, NO por SECURITY VIOLATION
    try {
        loader.load("/etc/argus/firewall/rules.json");
    } catch (const std::runtime_error& e) {
        EXPECT_EQ(std::string(e.what()).find("SECURITY VIOLATION"), std::string::npos)
            << "No debe lanzar SECURITY VIOLATION para ruta dentro del prefijo";
    }
}
```

---

#### Sub-test C: rag-ingester

**Archivo:** Añadir casos a `rag-ingester/tests/test_config_parser.cpp`

```cpp
// Añadir al test suite existente:

TEST(RagIngesterConfigSecurity, RejectsTraversalInConfigPath) {
    ConfigParser parser("/etc/argus/rag-ingester");
    
    EXPECT_THROW(
        parser.parse("../etc/passwd"),
        std::runtime_error
    ) << "config_parser debe rechazar traversal";
}

TEST(RagIngesterConfigSecurity, AcceptsLegitimateConfigPath) {
    ConfigParser parser("/etc/argus/rag-ingester");
    
    try {
        parser.parse("/etc/argus/rag-ingester/config.json");
    } catch (const std::runtime_error& e) {
        EXPECT_EQ(std::string(e.what()).find("SECURITY VIOLATION"), std::string::npos);
    }
}
```

**Gate de cierre:** 6 tests PASSED (2 por componente) · `make test-all` verde.

---

## DEBT-SNYK-WEB-VERIFICATION-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-SNYK-WEB-VERIFICATION-001 |
| **Severidad** | 🟡 Media — Bloqueante |
| **Origen** | DAY 118 — análisis Snyk C++, 23 vulnerabilidades medium |
| **Componente** | Global (todos los componentes C++) |
| **Estado** | Fixes implementados en ADR-037. Verificación en panel Snyk: NO realizada. |
| **Target** | DAY 126 |

### Descripción del problema

Snyk identificó 23 vulnerabilidades de severidad media en el codebase C++ de aRGus en DAY 118. ADR-037 (DAY 124) implementó los fixes: `safe_path` para path traversal, `validate_chain_name()` para command injection, y `int64_t` cast para integer overflow.

Sin embargo, **no se ha verificado en el panel web de Snyk** que las 23 vulnerabilidades aparezcan como cerradas. Es posible que:
- Algunas vulnerabilidades requieran un re-scan explícito.
- Algún fix no haya sido reconocido por Snyk (firma de código diferente a la esperada).
- Haya vulnerabilidades residuales no cubiertas por ADR-037.

### Cómo demostrar que el problema existe

Acceder al panel Snyk del repositorio `alonsoir/argus`. Si el contador de vulnerabilidades medium sigue en >0, el problema existe y requiere análisis adicional.

### Plan TDH

1. Acceder a https://app.snyk.io → proyecto `alonsoir/argus`
2. Forzar re-scan si necesario
3. Verificar contador de vulnerabilidades medium
4. Para cada vulnerabilidad residual: documentar en `docs/KNOWN-ISSUES.md` o crear DEBT nueva
5. **Gate de cierre:** Panel Snyk muestra 0 vulnerabilidades medium abiertas, O cada residual documentada con justificación de aceptación de riesgo firmada por el Consejo.

---

## DEBT-CRYPTO-TRANSPORT-CTEST-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-CRYPTO-TRANSPORT-CTEST-001 |
| **Severidad** | 🟡 Media — Bloqueante |
| **Origen** | DAY 97 — creación de `crypto-transport`. Tests existen pero no integrados en CTest. |
| **Componente** | `crypto-transport/` |
| **Estado** | Tests existen. Integración en `make test-all`: ROTA o incompleta. |
| **Target** | DAY 126–127 |

### Descripción del problema

`crypto-transport` es la librería criptográfica central del proyecto (HKDF-SHA256 + ChaCha20-Poly1305 + nonces monotónicos). Tiene tests unitarios, pero están **fuera del flujo CTest** que alimenta `make test-all`. Esto significa que cambios que rompan la criptografía pueden pasar desapercibidos en el ciclo normal de desarrollo.

### Cómo demostrar que el problema existe

```bash
vagrant ssh defender -c "cd /vagrant/crypto-transport/build && ctest -V 2>&1 | tail -50"
```

Si el output muestra errores de linking, crashes, o el Makefile usa `|| echo` para suprimir fallos, el problema existe.

### Plan TDH

1. **Diagnóstico:** ejecutar CTest con `-V` y clasificar el fallo (linking / runtime / aserción lógica)
2. **Fix según causa:**
    - Linking → revisar `target_link_libraries` en `CMakeLists.txt`
    - Runtime → analizar test específico fallido
    - `|| echo` en Makefile → eliminar el supresor, hacer que el fallo sea visible
3. **Gate de cierre:** `test_crypto_transport` PASSED · `test_integ_contexts` PASSED · Sin `|| echo` en Makefile.

---

## DEBT-DEV-PROD-SYMLINK-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-DEV-PROD-SYMLINK-001 |
| **Severidad** | 🟢 Baja — No bloqueante |
| **Origen** | DAY 124 — rag-ingester falló en build de producción, no en dev |
| **Componente** | Global (asimetría dev/prod) |
| **Estado** | Causa raíz documentada. Fix estructural: pendiente. |
| **Target** | DAY 127 |

### Descripción del problema

En DAY 124, `rag-ingester` con `safe_path` integrado falló en el build de producción pero no en dev. La causa raíz fue una asimetría en symlinks entre los dos entornos. Este tipo de divergencia entre dev y prod es una fuente sistémica de bugs silenciosos.

### Lección TDH aprendida

> Cualquier componente que pase en dev y falle en prod tiene una divergencia de entorno no documentada. Esa divergencia es deuda técnica, independientemente de que el fix puntual funcione.

### Plan TDH

1. Auditar diferencias de symlinks entre `vagrant/dev/` y `vagrant/hardened-x86/`
2. Documentar en `docs/ENVIRONMENT.md` las diferencias aceptadas y las que deben eliminarse
3. Añadir check en `make bootstrap` que detecte asimetrías críticas
4. **Gate de cierre:** `make bootstrap` en entorno de producción produce el mismo resultado que en dev para los 6 componentes.

---

## DEBT-PROVISION-PORTABILITY-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-PROVISION-PORTABILITY-001 |
| **Severidad** | 🟢 Baja — No bloqueante |
| **Origen** | Acumulado desde DAY 95 — `provision.sh` escrito para un único entorno |
| **Componente** | `tools/provision.sh` |
| **Estado** | Funciona en entorno actual. Portabilidad a hardened-x86/ARM64: no verificada. |
| **Target** | DAY 128 |

### Descripción del problema

`provision.sh` contiene rutas hardcodeadas que asumen el entorno de desarrollo específico de Extremadura. Cuando se inicien las variantes de producción (`aRGus-production`) y las imágenes hardened (ADR-029), el script fallará silenciosamente o con errores crípticos.

### Plan TDH

1. Identificar todas las rutas hardcodeadas en `provision.sh`
2. Parametrizar vía variables de entorno con defaults seguros
3. Añadir validación al inicio del script: si variable crítica no definida, error explícito
4. Probar en entorno limpio (`vagrant destroy && vagrant up`)
5. **Gate de cierre:** `TEST-PROVISION-1` verde en entorno hardened-x86.

---

## DEBT-PENTESTER-LOOP-001

| Campo | Valor |
|-------|-------|
| **ID** | DEBT-PENTESTER-LOOP-001 |
| **Severidad** | ⏳ Post-deuda — No bloqueante hoy |
| **Origen** | Visión ADR-026 + Consejo DAY 122 |
| **Componente** | Pipeline completo + XGBoost + Ed25519 |
| **Estado** | Diseño completo. Implementación: NO iniciada. |
| **Condición de inicio:** | Las 7 deudas anteriores cerradas. |

### Descripción del problema

ACRL (Adversarial Continuous Retraining Loop): un loop automatizado donde un pentester simulado (Caldera) genera ataques reales, eBPF captura el tráfico, XGBoost detecta o falla, y el resultado alimenta reentrenamiento, firma Ed25519, y hot-swap del modelo en producción — sin reiniciar el pipeline.

Este es el componente que convierte aRGus de un detector estático a un **escudo que aprende de su propia sombra**.

### Condición de cierre (cuando llegue el momento)

- Caldera genera ataque → XGBoost produce score ATTACK > 0.5
- Modelo reentrenado con nuevos datos → F1 ≥ 0.9985 en holdout CIC-IDS-2017
- Modelo firmado con Ed25519 activo
- Hot-swap sin downtime del pipeline
- `make test-all` verde tras el swap

---

## Resumen ejecutivo DAY 125

| ID | Severidad | Componente | Tests a crear | Target |
|----|-----------|-----------|--------------|--------|
| DEBT-INTEGER-OVERFLOW-TEST-001 | 🔴 | ml-detector | 3–5 (unit + property) | DAY 125 |
| DEBT-SAFE-PATH-TEST-RELATIVE-001 | 🔴 | contrib/safe-path | 5 | DAY 125 |
| DEBT-SAFE-PATH-TEST-PRODUCTION-001 | 🔴 | seed-client, firewall, rag | 6 (2×3) | DAY 125 |
| DEBT-SNYK-WEB-VERIFICATION-001 | 🟡 | global | 0 (verificación) | DAY 126 |
| DEBT-CRYPTO-TRANSPORT-CTEST-001 | 🟡 | crypto-transport | diagnóstico → fix | DAY 126–127 |
| DEBT-DEV-PROD-SYMLINK-001 | 🟢 | global | check en bootstrap | DAY 127 |
| DEBT-PROVISION-PORTABILITY-001 | 🟢 | provision.sh | TEST-PROVISION-1 | DAY 128 |
| DEBT-PENTESTER-LOOP-001 | ⏳ | pipeline completo | ACRL completo | post-deuda |

**Tests nuevos en DAY 125: ~14 tests**  
**Condición de merge a producción:** deudas 🔴 y 🟡 cerradas + DEBT-PENTESTER-LOOP-001 completo.

---

*"Via Appia Quality — Un escudo que aprende de su propia sombra."*  
*aRGus NDR — DAY 125 — 2026-04-22*