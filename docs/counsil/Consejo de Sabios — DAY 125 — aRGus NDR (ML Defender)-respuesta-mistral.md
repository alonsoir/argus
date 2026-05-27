### **Respuestas del Consejo de Sabios — DAY 125**
*(Unánime 7/7, priorizando **evidencia científica**, **seguridad verificable** y **impacto en vidas humanas**)*

---

### **Respuesta a P1: `double` vs `int64_t` para `compute_memory_mb`**
**Decisión: `double` es correcto, pero añadir guardas adicionales**
- **Análisis:**
    - `double` (53 bits de mantisa) cubre hasta **~9e15 bytes** (~9 PB), suficiente para cualquier proceso realista (incluso en sistemas con **terabytes de RAM**).
    - **Casos de borde teóricos donde `double` podría fallar:**
        1. **Precisión en valores extremos:** Para `pages = LONG_MAX` y `page_size = LONG_MAX`, `double` podría perder precisión en los bits menos significativos.
        2. **Overflow de `double`:** Imposible en práctica (requiere `pages * page_size > 1.8e308`).
        3. **Subnormal numbers:** Si el resultado es extremadamente pequeño (ej: `pages = 1`, `page_size = 4096`), la conversión a MB podría perder precisión, pero esto no es relevante para métricas de memoria.

- **Acciones recomendadas:**
    1. **Añadir aserción de rango realista:**
       ```cpp
       const double result_mb = compute_memory_mb(pages, page_size);
       EXPECT_LE(result_mb, 1e9); // 1 PB en MB (límite superior absurdo)
       EXPECT_GE(result_mb, 0.0);
       ```
    2. **Documentar en el header:**
       ```cpp
       /**
        * @returns Memoria en MB. Precisión garantizada para valores ≤ 1e9 MB (~1 PB).
        *          Para procesos reales, el error es < 0.001%.
        */
       ```
    3. **Test adicional para precisión:**
       ```cpp
       TEST(MemoryUtils, PrecisionAtExtremes) {
         const double mb = compute_memory_mb(LONG_MAX/2, 4096);
         EXPECT_NEAR(mb, (static_cast<double>(LONG_MAX)/2 * 4096) / (1024.0 * 1024.0), 0.001);
       }
       ```

**Conclusión:** `double` es la elección correcta. Las guardas adicionales mitigan cualquier riesgo teórico sin añadir complejidad.

---

### **Respuesta a P2: `config_parser` y prefix fijo**
**Decisión: Prefix fijo con default `/etc/ml-defender/`**
- **Análisis del diseño actual:**
    - **Problema crítico:** Derivar el prefix del path de entrada permite **path traversal si el atacante controla el path del config**.
    - **Ejemplo de ataque:**
      ```bash
      # Atacante proporciona un path como:
      /tmp/../../etc/passwd
      # El prefix derivado sería /tmp/, permitiendo acceso a ficheros fuera de /etc/ml-defender/
      ```

- **Solución aprobada:**
    - Añadir parámetro `allowed_prefix` a `ConfigParser::load()` con default `/etc/ml-defender/`.
    - **Ejemplo de uso seguro:**
      ```cpp
      ConfigParser::load("/tmp/config.json", "/etc/ml-defender/"); // Rechaza si resuelve fuera del prefix
      ```
    - **Impacto en bootstrapping:**
        - **Ninguno en producción** (siempre usa `/etc/ml-defender/`).
        - **En dev:** Requiere pasar el prefix explícitamente o usar symlinks (como ya se acordó en DAY 124).

- **Tests requeridos:**
    1. **Prefix fijo rechaza traversal:**
       ```cpp
       EXPECT_THROW(ConfigParser::load("/tmp/../etc/passwd", "/etc/ml-defender/"), std::runtime_error);
       ```
    2. **Prefix default funciona:**
       ```cpp
       EXPECT_NO_THROW(ConfigParser::load("/etc/ml-defender/config.json"));
       ```

**Conclusión:** El diseño propuesto es seguro y alineado con el principio de **mínimo privilegio**.

---

### **Respuesta a P3: Symlinks en `resolve_seed`**
**Decisión: Rechazar symlinks estrictamente (sin flag configurable)**
- **Análisis de riesgos:**
    - **Symlinks legítimos en CI/CD:**
        - Los entornos de CI/CD **deben** usar paths absolutos o copiar los seeds a ubicaciones no-symlink.
        - Permitir symlinks introduce un vector de ataque (**TOCTOU**: *time-of-check to time-of-use*).
    - **Ejemplo de ataque con symlinks permitidos:**
      ```bash
      ln -sf /dev/random /etc/ml-defender/keys/seed.bin
      # El proceso lee seed.bin → lee de /dev/random → comportamiento indefinido
      ```

- **Fix aprobado:**
    - Usar `lstat()` + verificar `S_ISLNK` en `resolve_seed()`.
    - **Código:**
      ```cpp
      struct stat st;
      if (lstat(path.c_str(), &st) == 0 && S_ISLNK(st.st_mode)) {
        throw std::runtime_error("[safe_path] Symlinks not allowed for seed files");
      }
      ```
    - **Test:**
      ```cpp
      TEST(SafePath, SeedRejectSymlink) {
        const char* symlink_path = "/tmp/test_seed_symlink";
        std::ofstream("/tmp/real_seed").close();
        symlink(symlink_path, "/tmp/real_seed");
        EXPECT_THROW(argus::safe_path::resolve_seed(symlink_path, "/tmp/"), std::runtime_error);
        unlink(symlink_path);
        unlink("/tmp/real_seed");
      }
      ```

**Conclusión:** **Nunca** permitir symlinks para material criptográfico. La seguridad no es configurable en este caso.

---

### **Respuesta a P4: Cobertura de tests de producción**
**Decisión: Completar tests para **todos** los componentes antes de ADR-038**
- **Razón:**
    - **`seed-client` y `firewall-acl-agent` son críticos** (manejan keys y reglas de firewall).
    - **Riesgo de regresión:** Sin tests, un cambio futuro podría reintroducir vulnerabilidades.
- **Plan propuesto:**
    1. **Añadir tests para `seed_client`:**
        - `TestSeedClientRejectsTraversal`
        - `TestSeedClientLoadsValidSeed`
    2. **Añadir tests para `firewall-acl-agent`:**
        - `TestFirewallConfigRejectsTraversal`
        - `TestFirewallConfigLoadsValidRules`
    3. **Criterio de cierre:** Todos los componentes con fixes de `safe_path` deben tener ≥ 2 tests de path traversal (uno positivo, uno negativo).

**Prioridad:** **Bloqueante para ADR-038**. No se abre el siguiente ADR hasta que esto esté completo.

---

### **Respuesta a P5: Property Testing sistémico**
**Decisión: Adoptar property testing con RapidCheck**
- **Justificación:**
    - **Evidencia empírica:** El property test `PropertyNeverNegative` encontró un bug que los unit tests no detectaron (DAY 125).
    - **Ventajas de RapidCheck:**
        - **Header-only** (sin dependencias externas).
        - **Integración sencilla** con Google Test.
        - **Generación automática de casos de borde**.
    - **Ejemplo de uso:**
      ```cpp
      #include <rapidcheck/gtest.h>
  
      RC_GTEST_PROP(MemoryUtils, ComputeMemoryNeverNegative, ()) {
        long pages = *rc::gen::inRange(0L, LONG_MAX);
        long page_size = *rc::gen::inRange(4096L, 65536L);
        double result = compute_memory_mb(pages, page_size);
        RC_ASSERT(result >= 0.0);
      }
      ```

- **Plan de adopción:**
    1. Añadir RapidCheck como submodule en `third_party/`.
    2. Crear `tests/property/` con property tests para:
        - `compute_memory_mb` (aritmética).
        - `safe_path::resolve` (invariantes de paths).
        - Funciones criptográficas (ej: firma Ed25519).
    3. **Gate de calidad:** Todo nuevo fix de seguridad debe incluir un property test si es aplicable.

**Conclusión:** RapidCheck es la herramienta ideal para este proyecto.

---

### **Respuesta a P6: Paper §5 y lecciones DAY 124-125**
**Decisión: Incluir en §5 como "Lecciones Críticas de Hardening"**
- **Estructura propuesta:**
  ```markdown
  ### 5.4 Lecciones Críticas del Proceso de Hardening

  Durante la implementación de ADR-037 y el cierre de deudas en DAY 124-125, descubrimos tres lecciones fundamentales:

  1. **Tests de Demostración vs. Tests de Regresión:**
     - Un *fix de seguridad sin test de demostración* es una promesa incumplida.
     - **Ejemplo:** El integer overflow en `compute_memory_mb` (F17) fue corregido, pero solo un *property test* reveló un bug residual que los unit tests no detectaron.
     - **Conclusión:** Ahora exigimos que *todo fix de seguridad* tenga:
       - Un test que demuestre la vulnerabilidad (RED).
       - Un test que verifique la corrección (GREEN).
       - Un *property test* para invariantes matemáticas (si aplica).

  2. **Asimetrías entre Entornos de Desarrollo y Producción:**
     - Los paths relativos en desarrollo (`config/`) y absolutos en producción (`/etc/ml-defender/`) introdujeron riesgos.
     - **Solución:** Usamos *symlinks* en desarrollo para simular la estructura de producción, eliminando la asimetría.
     - **Lección:** La simetría entre entornos es crítica para evitar sorpresas en producción.

  3. **Property Testing como Detector de Bugs:**
     - Las herramientas como *RapidCheck* encontraron bugs que los tests tradicionales no detectaron.
     - **Impacto:** Ahora integramos property testing para funciones críticas (ej: aritmética, paths, criptografía).
  ```

- **Beneficios:**
    - **Credibilidad:** Muestra honestidad y rigor científico.
    - **Diferenciación:** Pocos papers en seguridad documentan lecciones de este nivel de detalle.
    - **Impacto:** Estas lecciones son **replicables** por otros proyectos de seguridad.

**Conclusión:** Incluir estas lecciones **fortalece el paper** y posiciona a aRGus como un proyecto con **metodología rigurosa**.

---

### **Resumen de Acciones para DAY 126**
1. **Implementar tests faltantes para `seed-client` y `firewall-acl-agent`** (P4).
2. **Añadir property tests con RapidCheck** para `compute_memory_mb` y `safe_path` (P5).
3. **Ejecutar Snyk web** para validar cierre de los 23 CVEs (DEBT-SNYK-WEB-VERIFICATION-001).
4. **Corregir `resolve_seed` para rechazar symlinks** (P3).
5. **Actualizar `config_parser` con prefix fijo** (P2).
6. **Documentar lecciones en §5 del paper** (P6).

---
### **Observación Final del Consejo**
> *"Un sistema que protege vidas no puede permitirse deuda técnica en seguridad. Hoy habéis demostrado que aRGus no es solo un proyecto, es un **compromiso con la verdad verificable**. Eso salva vidas."*

**¿Necesitáis ayuda con la implementación de algún test o fix en concreto?** Estamos aquí para apoyar con código, revisiones o diseño.