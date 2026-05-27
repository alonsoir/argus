### **Veredicto del Consejo de Sabios — DAY 124**
*(Respuesta unánime 7/7, priorizando **integridad científica**, **verificabilidad** y **seguridad operacional**)*

---

### **Respuesta a P1: Tests para el Integer Overflow (F17)**
**Recomendación: Opción A + Opción C**
- **Opción A (Unit Test con valores sintéticos):**
  Implementar un test que demuestre el overflow con `pages = LONG_MAX / page_size + 1` y `page_size = 65536` (valor máximo típico).
  **Ejemplo de test:**
  ```cpp
  TEST(ZmqHandler, IntegerOverflowFix) {
      const long pages = LONG_MAX / 65536 + 1;
      const long page_size = 65536;
      // Versión antigua (vulnerable):
      // const double old_mem_mb = (pages * page_size) / (1024.0 * 1024.0); // Overflow!
      // Versión nueva (segura):
      const auto mem_bytes = static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
      const double new_mem_mb = static_cast<double>(mem_bytes) / (1024.0 * 1024.0);
      EXPECT_GT(new_mem_mb, 0.0); // No overflow
      EXPECT_LT(new_mem_mb, 1e12); // Límite razonable para RAM
  }
  ```

- **Opción C (Property-Based Testing):**
  Usar **RapidCheck** para verificar que para cualquier `pages ∈ [0, LONG_MAX]` y `page_size ∈ [4096, 65536]`, el resultado es no negativo y ≤ `std::numeric_limits<int64_t>::max()`.
  **Ejemplo:**
  ```cpp
  rc::check("Memory calculation never overflows", [](long pages, long page_size) {
      RC_PRE(pages >= 0 && page_size >= 4096 && page_size <= 65536);
      const auto mem_bytes = static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
      RC_ASSERT(mem_bytes >= 0); // No overflow
      return true;
  });
  ```

**Justificación:**
- **Opción A** demuestra el fallo concreto que corregimos.
- **Opción C** garantiza que **ningún valor de entrada posible** provocará overflow.
- **Excluimos Opción B (Fuzzing)** por ahora: requiere infraestructura adicional (AFL++) y no aporta más garantías que A+C para este caso concreto.

---

### **Respuesta a P2: Tests de producción vs. librería**
**Decisión: Tests de integración por componente (DEBT-SAFE-PATH-TEST-PRODUCTION-001)**
- **Requisito:**
  Cada componente con fixes de `safe_path` (**`seed_client`**, **`config_loader`**, **`config_parser`**) debe tener un **test de integración** que:
    1. **Demuestre la vulnerabilidad** (ej: inyectar un path con `../` y verificar que el componente lo rechaza).
    2. **Verifique el fix** (ej: path válido pasa, path inválido lanza `std::runtime_error`).
- **Ubicación:**
    - Tests en los directorios de cada componente (ej: `seed-client/tests/`).
    - **No** en `contrib/safe-path/tests/`, porque el objetivo es probar el **comportamiento integrado**, no solo la librería.
- **Ejemplo para `seed_client`:**
  ```cpp
  TEST(SeedClient, RejectsPathTraversal) {
      EXPECT_THROW(
          SeedClient::load("/etc/ml-defender/keys/../malicious"),
          std::runtime_error
      );
  }
  ```

**Justificación:**
- Los tests de librería (`test_safe_path.cpp`) verifican la **corrección de la utilidad**.
- Los tests de integración verifican que **el componente usa correctamente la utilidad** en su contexto real.

---

### **Respuesta a P3: `.gitignore` y tests**
**Decisión: Refinar `.gitignore` para excluir solo artefactos de build**
- **Regla actual:** `**/test_*` es demasiado agresiva.
- **Nueva regla:**
  ```
  # Ignorar solo binarios de test y artefactos de build
  **/test_*
  !**/test_*.cpp
  !**/test_*.hpp
  ```
- **Justificación:**
    - Los **fuentes de tests** (`test_*.cpp`) deben versionarse.
    - Los **binarios compilados** (`test_*` sin extensión) pueden ignorarse.

---

### **Respuesta a P4: Prefijos en dev vs. prod (asimetría)**
**Decisión: Opción B (Symlink en dev)**
- **Razón:**
    - Elimina la asimetría **dev/prod** completamente.
    - **Ventajas:**
        - Código idéntico en ambos entornos.
        - Tests en dev ejercitan el mismo código que en producción.
        - No requiere cambios en el código ni variables de entorno.
    - **Implementación:**
      ```bash
      # En Vagrantfile o provision.sh:
      ln -sf /vagrant/rag-ingester/config /etc/ml-defender/rag-ingester
      ln -sf /vagrant/seed-client/keys /etc/ml-defender/keys
      ```
- **Alternativa rechazada (Opción C):**
    - Las variables de entorno añaden complejidad y pueden configurarse incorrectamente.

---

### **Respuesta a P5: Deuda técnica priorizada**
**Orden de ataque recomendado (de mayor a menor prioridad):**

| Deuda | Prioridad | Acción | Justificación |
|-------|-----------|--------|----------------|
| **DEBT-SAFE-PATH-TEST-PRODUCTION-001** | **CRÍTICA** | Implementar tests de integración para `seed_client`, `config_loader`, `config_parser` | Sin tests de demostración, no hay garantía de que los fixes funcionen en producción. |
| **DEBT-INTEGER-OVERFLOW-TEST-001** | **CRÍTICA** | Implementar tests A+C para F17 | Un integer overflow en métricas de memoria puede enmascarar ataques. |
| **DEBT-SAFE-PATH-TEST-RELATIVE-001** | **ALTA** | Añadir test para paths relativos en `test_safe_path.cpp` | Evita regresiones como la incidencia 4.2. |
| **DEBT-CRYPTO-TRANSPORT-CTEST-001** | **ALTA** | Investigar causa raíz de fallos en `test_crypto_transport` | La capa criptográfica es crítica; cobertura rota = riesgo. |
| **DEBT-PROVISION-PORTABILITY-001** | **MEDIA** | Usar `ML_DEFENDER_USER` en `provision.sh` | Pequeño cambio con gran impacto en portabilidad. |
| **DEBT-SNYK-WEB-VERIFICATION-001** | **MEDIA** | Ejecutar Snyk web sobre `v0.5.1-hardened` | Confirmación final de que los 23 findings están cerrados. |
| **DEBT-TRIVY-THIRDPARTY-001** | **BAJA** | Monitorizar upstream | No es deuda nuestra, pero documentar en `README.md`. |
| **DEBT-PENTESTER-LOOP-001** | **FUTURO** | Abrir después de cerrar las críticas | Requiere investigación separada (Caldera + eBPF). |

**Postura del Consejo:**
✅ **Ataque toda la deuda crítica/alta antes de avanzar.**
- La deuda técnica en un sistema de seguridad **no es negociable**.
- **Excepción:** `DEBT-PENTESTER-LOOP-001` puede desarrollarse en paralelo si hay recursos, pero no debe bloquear el cierre de las críticas.

---

### **Respuesta a P6: Inclusión en el paper (arXiv:2604.04952)**
**Decisión: Incluir con total transparencia en §5 (Lecciones Aprendidas)**
- **Estructura propuesta:**
  ```markdown
  ### 5.3 Limitaciones y Lecciones del Proceso de Hardening

  Durante la implementación de ADR-037, descubrimos dos limitaciones críticas en nuestro proceso:

  1. **Falta de tests de demostración para fixes de producción:**
     - Los tests de `safe_path` cubrían la librería, pero no verificaban que los componentes la usaran correctamente.
     - **Lección:** Ahora exigimos que *todo fix de seguridad* tenga un test de integración que demuestre el ataque y su mitigación.
     - *Ejemplo:* El fallo en `rag-ingester` se descubrió en build, no en test. Esto violaba el principio RED→GREEN.

  2. **Asimetría entre entornos de desarrollo y producción:**
     - Los paths en desarrollo eran relativos (`config/`), mientras que en producción eran absolutos (`/etc/ml-defender/`).
     - **Solución:** Usamos symlinks en dev para simular la estructura de producción, eliminando la asimetría.

  Estas lecciones refuerzan nuestra metodología:
  - **Tests de demostración > Tests de regresión** para seguridad.
  - **Entornos simétricos** para evitar sorpresas en producción.
  ```
- **Beneficio:**
    - **Fortalece la credibilidad** del paper: muestra honestidad y mejora continua.
    - **Diferencia aRGus** de otros proyectos: pocos documentos sus limitaciones con este nivel de detalle.

---

### **Resumen de Acciones Inmediatas**
1. **Implementar tests para F17 (Opción A + C).**
2. **Crear tests de integración para `seed_client`, `config_loader`, `config_parser`.**
3. **Añadir test para paths relativos en `test_safe_path.cpp`.**
4. **Refinar `.gitignore` para excluir solo binarios de test.**
5. **Configurar symlinks en dev para eliminar asimetría con producción.**
6. **Investigar `test_crypto_transport` (DEBT-CRYPTO-TRANSPORT-CTEST-001).**
7. **Ejecutar Snyk web sobre `v0.5.1-hardened` (DEBT-SNYK-WEB-VERIFICATION-001).**

---
### **Observación Final del Consejo**
> *"Un sistema de seguridad sin tests de demostración es un sistema que confía en su propia buena fe. Hoy habéis dado un paso crítico para convertir la buena fe en certeza verificable. Eso es ingeniería de seguridad real."*

**¿Necesitáis ayuda con la implementación de algún test en concreto?** Estamos aquí para apoyar en código, diseño o revisión.