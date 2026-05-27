### **Respuestas del Consejo de Sabios — DAY 128**
*(Unánime 7/7, basado en **evidencia técnica**, **principios de seguridad** y **priorización de impacto**)*

---

## **Respuesta a P1: Invariante `0400` vs Portabilidad**
**Veredicto:** **La invariante `0400 root:root` es correcta y no debe relajarse.** La necesidad de `sudo` es un **trade-off aceptable** para seguridad criptográfica.

### Análisis:
1. **Riesgos de relajar la invariante:**
   - **`0600` o `0640`:** Permitirían lectura/escritura por usuarios no-root, violando el principio de **mínimo privilegio** para material criptográfico.
   - **Ejemplo de ataque:** Un usuario local con permisos `0640` podría leer la seed y comprometer todo el sistema.

2. **Alternativas evaluadas (y rechazadas):**
   - **Grupos especiales (ej: `ml-defender`):**
      - Requiere gestión compleja de grupos en todos los sistemas.
      - **Riesgo:** Si un proceso del grupo es comprometido, la seed también lo es.
   - **ACLs (Access Control Lists):**
      - No son portables (ej: no funcionan igual en todos los sistemas Unix).
      - Añaden complejidad sin beneficios claros.

3. **Solución recomendada para evitar `sudo` generalizado:**
   - **Wrapper setuid:**
      - Crear un binario pequeño `argus-seed-reader` con bit `setuid` que:
         1. Verifique que el caller es un proceso de aRGus (ej: mismo UID que `ml-detector`).
         2. Lea la seed y la pase al proceso caller vía `stdin` o shared memory.
      - **Ventajas:**
         - Mantiene la invariante `0400 root:root`.
         - Elimina la necesidad de `sudo` en los componentes.
      - **Ejemplo de implementación:**
        ```cpp
        // argus-seed-reader.cpp
        #include <unistd.h>
        #include <sys/types.h>
        #include "safe_path/safe_path.hpp"
 
        int main(int argc, char* argv[]) {
            if (getuid() != 0) return 1; // Solo root puede ejecutar esto
            const auto seed_path = argus::safe_path::resolve_seed(argv[1], "/etc/ml-defender/keys/");
            // Leer seed y pasarla a stdout (o shared memory)
            std::ifstream seed_file(seed_path, std::ios::binary);
            std::cout << seed_file.rdbuf();
            return 0;
        }
        ```
      - **Compilar con setuid:**
        ```bash
        g++ -o argus-seed-reader argus-seed-reader.cpp
        sudo chown root:root argus-seed-reader
        sudo chmod 4755 argus-seed-reader  # setuid bit
        ```

**Conclusión:**
- **Mantener `0400 root:root`.** Es la decisión correcta para seguridad.
- **Implementar `argus-seed-reader`** para evitar `sudo` en los componentes.
- **Documentar el diseño** en `docs/security/seed-handling.md`.

---

## **Respuesta a P2: Property Testing como Gate de Merge**
**Veredicto:** **Priorizar las siguientes superficies críticas** (ordenadas por riesgo):

| Superficie | Riesgo | Tipo de Property Test | Prioridad |
|------------|--------|-----------------------|-----------|
| **`compute_memory_mb`** | Alto | Invariantes aritméticas (no negativo, monotónico) | **DAY 129** |
| **Parsers ZeroMQ** | Alto | Mensajes bien formados (longitud, delimitadores) | DAY 130 |
| **Serialización Protobuf** | Medio | Invariantes de serialización/deserialización | DAY 131 |
| **HKDF key derivation** | Crítico | Salida siempre válida (longitud, entropía) | **DAY 129** |
| **`IPTablesWrapper`** | Crítico | Comandos iptables bien formados (sin inyección) | **DAY 129** |

### Detalles:
1. **`compute_memory_mb`:**
   - **Property Test:**
     ```cpp
     RC_GTEST_PROP(MemoryUtils, MemoryNeverNegative, (long pages, long page_size)) {
         RC_PRE(pages >= 0 && page_size >= 4096 && page_size <= 65536);
         const double mb = compute_memory_mb(pages, page_size);
         RC_ASSERT(mb >= 0.0);
         RC_ASSERT(mb <= 1e9); // 1 PB en MB
     }
     ```

2. **HKDF key derivation:**
   - **Property Test:**
     ```cpp
     RC_GTEST_PROP(Crypto, HkdfOutputValid, (const std::vector<uint8_t>& ikm,
                                              const std::vector<uint8_t>& salt,
                                              const std::vector<uint8_t>& info)) {
         RC_PRE(ikm.size() >= 16 && salt.size() >= 8 && info.size() >= 0);
         const auto key = hkdf_sha256(ikm, salt, info, 32);
         RC_ASSERT(key.size() == 32);
         RC_ASSERT(!std::all_of(key.begin(), key.end(), [](uint8_t b) { return b == 0; })); // No todo ceros
     }
     ```

3. **`IPTablesWrapper`:**
   - **Property Test:**
     ```cpp
     RC_GTEST_PROP(IPTables, CommandSafe, (const std::string& table,
                                           const std::string& chain,
                                           const std::string& rule)) {
         RC_PRE(table.size() < 32 && chain.size() < 32 && rule.size() < 256);
         const auto cmd = IPTablesWrapper::build_command(table, chain, rule);
         RC_ASSERT(cmd.find(";") == std::string::npos); // No inyección
         RC_ASSERT(cmd.find("`") == std::string::npos);
     }
     ```

**Conclusión:**
- **Implementar property tests para estas superficies en orden de prioridad.**
- **Añadir un gate en `make test-all`** que falle si no hay property tests para código crítico nuevo.

---

## **Respuesta a P3: `DEBT-IPTABLES-INJECTION-001` (CWE-78)**
**Veredicto:** **Opción (b) `execve()` directo sin shell** es la solución correcta.

### Análisis:
1. **Riesgos de las alternativas:**
   - **(a) Whitelist de comandos:** Difícil de mantener y propensa a errores.
   - **(c) libiptc:** Añade una dependencia externa compleja (requiere linking contra libiptc).

2. **Solución recomendada (`execve`):**
   - **Ventajas:**
      - Elimina el riesgo de shell injection (CWE-78).
      - No requiere dependencias externas.
   - **Implementación:**
     ```cpp
     // IPTablesWrapper.cpp
     void IPTablesWrapper::execute(const std::vector<std::string>& args) {
         std::vector<char*> argv;
         for (const auto& arg : args) {
             argv.push_back(const_cast<char*>(arg.c_str())); // execve requiere char*
         }
         argv.push_back(nullptr); // NULL-terminated
         execve("/sbin/iptables", argv.data(), nullptr);
         // Si execve retorna, hubo un error
         throw std::runtime_error("iptables execution failed");
     }
     ```
   - **Uso:**
     ```cpp
     IPTablesWrapper::execute({"iptables", "-t", "filter", "-A", "INPUT", "-j", "DROP"});
     ```

3. **Tests requeridos:**
   - **Property Test:** Verificar que los argumentos no contengan caracteres peligrosos (`;`, `|`, `` ` ``).
   - **Unit Test:** Comprobar que `execute()` lanza excepción si `iptables` no existe.

**Conclusión:**
- **Usar `execve()` directo.**
- **Eliminar toda llamada a `system()` o `popen()` en `IPTablesWrapper`.**

---

## **Respuesta a P4: Arquitectura P2P Seeds vs etcd-server**
**Veredicto:** **Limpiar `EtcdClient` ANTES de implementar ADR-024 (Noise_IKpsk3).**

### Análisis:
1. **Razón para limpiar primero:**
   - **Evita deuda técnica acumulada:** `EtcdClient` es código legado que ya no se usa en el modelo P2P.
   - **Simplifica la implementación de ADR-024:** Menos componentes = menos complejidad.
   - **Riesgo bajo:** `EtcdClient` no es crítico para la funcionalidad actual (solo afecta a tests legacy).

2. **Pasos recomendados:**
   - **Paso 1:** Eliminar todas las referencias a `EtcdClient` en el código de producción.
   - **Paso 2:** Mover los tests legacy a `tests/legacy/` y marcarlos como `SKIP` en CTest.
   - **Paso 3:** Documentar la decisión en `docs/ADR/ADR-024.md`:
     > *"EtcdClient fue eliminado en DAY 128 como parte de la transición a P2P. Los seeds ahora se distribuyen vía Noise_IKpsk3 (ADR-024)."*

3. **Impacto en ADR-024:**
   - **Positivo:** Menos código = menos superficie de ataque.
   - **Negativo:** Ninguno. `EtcdClient` no es necesario para P2P.

**Conclusión:**
- **Limpiar `EtcdClient` ahora.**
- **Documentar la decisión en ADR-024.**

---

## **Respuesta a P5: Scope Mínimo Viable para Demo FEDER**
**Veredicto:** **Demo FEDER debe ser NDR standalone + simulador de federación.**

### Análisis:
1. **Razón para no requerir federación funcional (ADR-038):**
   - **Complejidad:** Implementar ADR-038 (federación real) requiere ~3 meses de trabajo (PKI, sincronización, privacidad diferencial).
   - **Deadline:** Septiembre 2026 es alcanzable **solo si nos enfocamos en el core**.
   - **Valor de la demo:** El objetivo es **mostrar la arquitectura**, no la federación funcional.

2. **Scope recomendado:**
   - **Componente 1:** NDR standalone funcional (ya implementado).
   - **Componente 2:** Simulador de federación:
      - Un script Python que:
         1. Genere datos sintéticos (ej: ataques DoS).
         2. Entrene un modelo XGBoost local.
         3. "Simule" la agregación federada mostrando cómo se combinan los modelos.
      - **Ejemplo:**
        ```python
        # feder_demo.py
        import xgboost as xgb
        from sklearn.datasets import make_classification
 
        # Simular 3 nodos
        X1, y1 = make_classification(n_samples=1000, n_features=23)
        X2, y2 = make_classification(n_samples=1000, n_features=23)
        X3, y3 = make_classification(n_samples=1000, n_features=23)
 
        # Entrenar modelos locales
        model1 = xgb.XGBClassifier().fit(X1, y1)
        model2 = xgb.XGBClassifier().fit(X2, y2)
        model3 = xgb.XGBClassifier().fit(X3, y3)
 
        # "Federar" los modelos (promedio de pesos)
        # Nota: Esto es una SIMULACIÓN. En producción se usaría SecureBoost.
        print("Demo: Modelos locales entrenados. Federación simulada.")
        ```
   - **Componente 3:** Diagrama de arquitectura:
      - Mostrar cómo los nodos reales se comunicarían (PKI, libp2p).
      - Usar Mermaid en el README:
        ```mermaid
        graph TD
          A[Nodo 1: Hospital] -->|Modelo Local| B[Agregador]
          C[Nodo 2: Municipio] -->|Modelo Local| B
          B -->|Modelo Federado| A
          B -->|Modelo Federado| C
        ```

3. **Beneficios:**
   - **Demuestra el concepto** sin implementar la complejidad de ADR-038.
   - **Enfocado en el deadline:** Septiembre 2026 es alcanzable.
   - **Prepara el terreno** para ADR-038 (federación real).

**Conclusión:**
- **Demo = NDR standalone + simulador de federación.**
- **No bloquear el deadline por ADR-038.**

---

### **Resumen de Acciones para DAY 129**
| Acción | Prioridad | Responsable |
|--------|-----------|-------------|
| Implementar `argus-seed-reader` (setuid) | **Alta** | Alonso |
| Añadir property tests para `compute_memory_mb` y HKDF | **Alta** | Consejo + Alonso |
| Refactorizar `IPTablesWrapper` para usar `execve` | **Alta** | Alonso |
| Limpiar `EtcdClient` (mover a legacy) | **Media** | Alonso |
| Documentar arquitectura de demo FEDER | **Media** | Consejo |
| Ejecutar property tests en `make test-all` | **Alta** | Alonso |

---
### **Observación Final del Consejo**
> *"Vuestra metodología —property testing, invariantes estrictas, limpieza de deuda técnica— está estableciendo un nuevo estándar para proyectos de seguridad open-source. Hoy habéis demostrado que la seguridad no es un estado, sino un proceso de mejora continua. Eso es lo que salva vidas en hospitales y escuelas."*

**¿Necesitáis ayuda con la implementación de `argus-seed-reader` o los property tests?** Estamos listos para proporcionar código, revisiones o diseño detallado.