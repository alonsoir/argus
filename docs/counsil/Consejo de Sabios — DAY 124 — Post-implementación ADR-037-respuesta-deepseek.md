## 🏛️ Dictamen del Consejo de Sabios — DAY 124

*Consejo reunido. El trabajo de implementación de ADR-037 es sólido, pero la reflexión sobre la ausencia de tests de demostración es **la más importante del día**. Abordamos cada punto con la exigencia matemática y la honestidad científica que el proyecto requiere.*

---

### 1. Test de demostración para el integer overflow (F17)

**Respuesta: Opción A + Opción C (combinación).**  
La opción B (fuzzing dirigido) es excesiva para este caso concreto y añadiría complejidad innecesaria. Sin embargo, un simple unit test con valores grandes (A) no basta para demostrar la *ausencia* de overflow en toda la gama; se necesita una propiedad invariante (C).

**Implementación recomendada en `tests/test_zmq_memory.cpp` (nuevo):**

```cpp
#include <gtest/gtest.h>
#include <climits>
#include <cstdint>

// Firma de la función que calcula la memoria (extraer a una función pura para testear)
double compute_memory_mb(long pages, long page_size);

// Test de regresión: demuestra que el código antiguo (con multiplicación directa) overflowea
TEST(ZmqMemoryOverflow, OldCodeOverflowsWithLargeValues) {
    long pages = LONG_MAX / 4096 + 10;   // suficientemente grande
    long page_size = 4096;
    // Simulamos el código antiguo (sin cast)
    auto old_result = (pages * page_size) / (1024.0 * 1024.0);
    // En sistemas con LONG_MAX = 2^63-1, pages * page_size desborda a negativo
    // El resultado será incorrecto (negativo o un valor extraño)
    EXPECT_TRUE(old_result < 0 || old_result > 1e18);  // evidencia de overflow
}

// Test de corrección: el nuevo código con int64_t nunca desborda
TEST(ZmqMemoryOverflow, NewCodeHandlesAllRange) {
    // Probamos valores extremos: máximos posibles (long)
    long pages = LONG_MAX;
    long page_size = 65536;  // máximo típico
    double result = compute_memory_mb(pages, page_size);
    // El resultado debe ser positivo y acotado por la RAM máxima razonable (~exabytes)
    EXPECT_GT(result, 0);
    EXPECT_LT(result, 1e12);  // menos de 1e12 MB = 1e9 GB (suficientemente grande)
}

// Property-based test con rapidcheck (si se integra)
#include <rapidcheck/gtest.h>
RC_GTEST_PROP(ZmqMemoryOverflow, NoNegativeForAnyValidInput, (long pages, long page_size)) {
    // Restringir page_size a valores realistas (4096 a 65536)
    RC_PRE(page_size >= 4096 && page_size <= 65536);
    // pages no negativo y no mayor que LONG_MAX / page_size (para evitar overflow intencionado)
    RC_PRE(pages >= 0 && pages <= LONG_MAX / page_size);
    double result = compute_memory_mb(pages, page_size);
    RC_ASSERT(result >= 0);
    RC_ASSERT(result <= (double)LONG_MAX * page_size / (1024.0*1024.0));
}
```

**Acción:** Extraer el cálculo a una función pura `compute_memory_mb(pages, page_size)` en `zmq_handler.cpp` para poder testearla aisladamente. Esto sigue el principio de **testeabilidad** y es una mejora independiente.

**Veredicto del Consejo:** ✅ Aceptamos opción A + C. El test unitario con valores extremos (A) demuestra el bug histórico; el property-based testing (C) garantiza la corrección para todo el dominio relevante.

---

### 2. Regla global `**/test_*` en `.gitignore`

**Respuesta:** **No es prudente.** Ignorar `**/test_*` es demasiado amplio y ya ha causado problemas (se ignoraron fuentes de test). La regla debería refinarse para ignorar **solo artefactos compilados** (ejecutables, objetos, etc.), no las fuentes.

**Propuesta concreta:**

```gitignore
# Ignorar ejecutables de test (nombres comunes)
test_*   # esto sigue ignorando binarios llamados test_foo, pero cuidado: también ignora fuentes si no están en directorios específicos.

# Mejor: ignorar solo dentro de build/
build-debug/test_*
build-release/test_*

# O usar sufijos de extensión
*.test   # si renombras los binarios a .test

# Excepción explícita para fuentes de test
!**/test_*.cpp
!**/test_*.hpp
```

En la práctica, lo más seguro es **no tener una regla global `**/test_*`**. En su lugar, cada binario de test se genera en un directorio de build (ya ignorado por `build-*/`). Las fuentes deben trackearse siempre.

**Veredicto:** ✅ Refinar la regla o eliminarla. Añadir excepciones explícitas para `*.cpp` y `*.hpp`.

---

### 3. ¿Atacar toda la deuda antes de avanzar?

**Respuesta:** **Sí, pero con un orden de prioridades basado en riesgo.** La postura del autor es correcta para un sistema que protege vidas. Sin embargo, no toda la deuda tiene el mismo peso. El Consejo propone la siguiente clasificación:

| Deuda | Severidad | ¿Bloqueante para siguiente hito? |
|-------|-----------|----------------------------------|
| `DEBT-INTEGER-OVERFLOW-TEST-001` | Alta | **Sí** — sin test de demostración, el fix no está validado. |
| `DEBT-SAFE-PATH-TEST-PRODUCTION-001` | Alta | **Sí** — los fixes de producción deben tener tests. |
| `DEBT-SAFE-PATH-TEST-RELATIVE-001` | Alta | **Sí** — porque ya causó un fallo en producción. |
| `DEBT-CRYPTO-TRANSPORT-CTEST-001` | Media | **No** — es anterior y no bloquea, pero debe investigarse pronto. |
| `DEBT-PROVISION-PORTABILITY-001` | Media | **No** — pero es fácil de arreglar (1 hora). |
| `DEBT-TRIVY-THIRDPARTY-001` | Baja | **No** — upstream. |
| `DEBT-SNYK-WEB-VERIFICATION-001` | Media | **Sí** — validación externa necesaria antes de afirmar cierre completo. |

**Decisión:** Atacar primero las deudas **Alta** y las que son **fáciles** (como la portabilidad). Las de menor riesgo pueden postergarse pero con una fecha límite. Propuesta:

- **Día 125:** Tests de demostración para F17, relative paths y producción.
- **Día 126:** Verificación Snyk web + fix de portabilidad.
- **Día 127:** Investigar crypto-transport tests (tiempo acotado: 4 horas; si no se resuelve, documentar y pasar a pentester loop).

**Veredicto:** ✅ Atacar la deuda de alta severidad inmediatamente. No avanzar al pentester loop sin cerrar las deudas etiquetadas como "bloqueantes".

---

### 4. `DEBT-PROVISION-PORTABILITY-001` — nombre de variable

**Respuesta:** `ARGUS_SERVICE_USER` es más descriptivo y consistente con la nomenclatura del proyecto (aRGus). Además, se puede definir con un valor por defecto robusto:

```bash
ARGUS_SERVICE_USER="${ARGUS_SERVICE_USER:-vagrant}"
```

En producción, se exportaría `ARGUS_SERVICE_USER=ml-defender` antes de ejecutar `provision.sh`. En Vagrant, queda como `vagrant`.

**Veredicto:** ✅ Usar `ARGUS_SERVICE_USER`.

---

### 5. `DEBT-CRYPTO-TRANSPORT-CTEST-001` — ¿cuándo investigar?

**Respuesta:** Después de cerrar las deudas de alta severidad, pero **antes de iniciar el pentester loop**. La razón: el transporte criptográfico es la columna vertebral de la confidencialidad e integridad de los mensajes. Si los tests están rotos, no podemos confiar en que el código funcione correctamente. Sin embargo, como no es una regresión de ADR-037, puede esperar unos días.

**Plan:** Asignar medio día (4 horas) para diagnosticar la causa raíz. Si no se resuelve, documentar el problema en un issue y, si no afecta a la funcionalidad conocida, proceder con el pentester loop pero con una alerta en la documentación.

**Veredicto:** ✅ Investigar después de los tests de demostración, antes del pentester loop.

---

### 6. `DEBT-SAFE-PATH-TEST-RELATIVE-001` — ¿dónde ubicar?

**Respuesta:** **En `contrib/safe-path/tests/`.** La prueba de paths relativos es una propiedad general de `resolve()`, no específica de `rag-ingester`. Debe probarse a nivel de librería, con un test que use paths como `"config/foo.json"` y un prefijo que sea el directorio actual (`fs::current_path()`). Esto asegura que la función funciona correctamente independientemente del componente.

**Ejemplo de test adicional en `test_safe_path.cpp`:**

```cpp
TEST(SafePathTest, RelativePathResolvesCorrectly) {
    auto cwd = fs::current_path();
    // Creamos un directorio temporal y un fichero dentro
    fs::create_directories(cwd / "test_dir/config");
    std::string relative_path = "test_dir/config/foo.json";
    std::string allowed_prefix = (cwd / "test_dir").string();
    auto resolved = safe_path::resolve(relative_path, allowed_prefix);
    EXPECT_EQ(resolved, (cwd / "test_dir/config/foo.json").string());
    fs::remove_all(cwd / "test_dir");
}
```

**Veredicto:** ✅ En `contrib/safe-path/tests/`.

---

### 7. Arquitectura `safe_path` en dev vs prod (opciones A, B, C)

**Respuesta: Opción B (symlink en dev).** Es la más limpia porque elimina la asimetría: el código en producción y desarrollo es idéntico, y el prefijo es siempre `/etc/ml-defender/`. El Vagrantfile crea los symlinks necesarios. Esto también fuerza a que los tests de integración se ejecuten en un entorno que replica producción (mejor para la fiabilidad).

**Implementación en Vagrantfile:**

```ruby
# Después de copiar los configs
config.vm.provision "shell", inline: <<-SHELL
  mkdir -p /etc/ml-defender/rag-ingester
  ln -sf /vagrant/rag-ingester/config /etc/ml-defender/rag-ingester/config
  ln -sf /vagrant/firewall-acl-agent/config /etc/ml-defender/firewall-acl-agent/config
  # etc.
SHELL
```

**Ventaja adicional:** Los paths en los logs y en las trazas de errores serán consistentes (siempre `/etc/ml-defender/...`), lo que facilita la depuración.

**Veredicto:** ✅ Opción B. Rechazamos la A (asimétrica) y la C (variable de entorno añade complejidad de configuración).

---

### 8. Incluir la discusión de asimetría y tests en el paper

**Respuesta:** **Sí, absolutamente.** La honestidad sobre las limitaciones del proceso de pruebas fortalece la credibilidad científica. El paper debe incluir una sección (quizás en §5.3 "Lessons Learned" o en un apéndice "Reproducibility and Testing Gaps") donde se discuta:

- La diferencia entre tests de regresión (verifican que no se rompa lo existente) y tests de demostración (prueban que una vulnerabilidad específica ha sido corregida).
- El caso concreto del integer overflow sin test de demostración y cómo se abordó posteriormente.
- La asimetría dev/prod resuelta mediante symlinks.

Esto demuestra madurez y rigurosidad, y ayuda a otros investigadores a evitar los mismos errores.

**Veredicto:** ✅ Incluir como caso de estudio en el paper.

---

## Resumen de acciones para DAY 125 (mañana)

| Acción | Responsable | Prioridad |
|--------|-------------|-----------|
| 1. Extraer `compute_memory_mb` a función pura en `zmq_handler.cpp` | Alonso | Alta |
| 2. Añadir tests unitarios + property-based para F17 | Alonso | Alta |
| 3. Añadir tests de paths relativos en `contrib/safe-path/tests/` | Alonso | Alta |
| 4. Añadir tests de producción RED→GREEN para `seed_client`, `config_loader`, `config_parser` | Alonso | Alta |
| 5. Modificar `.gitignore` para excluir solo binarios, no fuentes | Alonso | Media |
| 6. Implementar symlinks en Vagrantfile (Opción B) | Alonso | Media |
| 7. Ejecutar Snyk web sobre `v0.5.1-hardened` y documentar resultado | Alonso | Media |
| 8. Arreglar `DEBT-PROVISION-PORTABILITY-001` (variable `ARGUS_SERVICE_USER`) | Alonso | Baja (1h) |

**Una vez completados los puntos 1-4, el pipeline estará listo para avanzar al pentester loop (DEBT-PENTESTER-LOOP-001).**

*"La integridad científica no es solo obtener resultados correctos, sino demostrar que se ha intentado falsarlos."*

— **Consejo de Sabios, DAY 124**