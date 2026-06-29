🏛️ **Veredicto del Consejo de Sabios**

| Pregunta | Decisión | Justificación Arquitectónica |
|----------|----------|------------------------------|
| **1. Patrón CMake** | ✅ `if(NOT TARGET <nombre>)` como invariante obligatorio | Evita contaminación de namespace, preserva semántica de tests y es idiomático en CMake moderno. Los sufijos (`_vault`) solo se recomiendan si el target enterprise tiene linkage, dependencias o comportamiento divergente. |
| **2. Scope DAY 164** | ✅ Fase 1 se cierra con lectura desde env var + validación. AppRole = Fase 2 | Fase 1 debe validar el *mecanismo de recuperación* sin exponer secretos en repos. AppRole es infraestructura/IAM y pertenece al hardening de producción. Se mantiene el veto de merge para Fases 3-4, donde AppRole será gate ineludible. |
| **3. Cobertura Acto I** | ✅ Compilación + UT + stub E2E es suficiente | Acto I debe validar el *contrato de interfaz* y la *activación condicional* (`ARGUS_VAULT_ENABLED`). Exigir `VaultProvider` real antes de cerrar `BACKLOG-CRYPTO-VENDOR-KEY-001` crea dependencia circular y frena la integración. E2E real → Acto II. |

---

🔍 **Análisis Técnico Detallado**

### 1. Patrón CMake para targets condicionales
- **Recomendación:** Adoptar `if(NOT TARGET <nombre>)` como estándar en todos los bloques condicionales (`if(ARGUS_VAULT_ENABLED)`, `if(ENABLE_ENTERPRISE)`, etc.).
- **Por qué:** CMake no lanza error por redefinición de targets idénticos, pero sí falla en `add_dependencies()` o `target_link_libraries()` cuando hay colisiones silenciosas. El guard es O(1), legible y ampliamente adoptado en proyectos enterprise (OpenSSL, LLVM, ROS2).
- **Mejora preventiva en CI:** Añadir un script de validación post-configuration:
  ```cmake
  get_cmake_property(_all_targets TARGETS)
  string(REPLACE ";" "\n" _target_list "${_all_targets}")
  # O usar un hook pre-merge que corra `cmake -DARGUS_VAULT_ENABLED=ON` y falle si hay warnings de target ya definidos.
  ```
- **Excepción:** Si el target enterprise requiere librerías adicionales o flags de compilación distintos, entonces sí usar naming explícito (`test_ntp_health_check_vault`) y alias si es necesario.

### 2. BACKLOG-CRYPTO-VENDOR-KEY-001 → Scope DAY 164
- **Fase 1 (Cierre hoy):**
    - `vendor.key` cifrado en `secret/argus/enterprise/vendor-key`
    - Pipeline lee pubkey desde `ARGUS_VENDOR_PUBKEY_HEX` (Jenkins)
    - Validación de firma/decodificación en CI sin exponer material sensible en logs/repos
- **AppRole:** Se mantiene en **Fase 2** (infraestructura + rotación automática). No bloquea el cierre de Fase 1, pero debe estar documentado como *dependency gate* para Fases 3-4. El veto de merge se aplica al pipeline completo, no a la iteración incremental.
- **Riesgo mitigado:** Evitar hardcodeo de claves en CI variables no protegidas. La lectura desde env var es transitiva y auditable.

### 3. EMECAS++ Acto I → Cobertura enterprise
- **Estrategia recomendada:** `VaultProvider` stub/mock en E2E + tests de contrato (interfaz, serialización, fallos controlados).
- **Por qué:** La integración real con Vault requiere auth, policies, y secret rotation, que dependen de `BACKLOG-CRYPTO-VENDOR-KEY-001` cerrado. Forzarlo ahora genera:
    - Flakiness en CI por dependencias externas
    - Retroceso en velocidad de iteración
    - Falsa sensación de cobertura (pasa porque el mock responde, no porque la capa enterprise esté validada)
- **Acto I debe entregar:** Compilación limpia con flag enterprise, tests unitarios de la capa de abstracción, y un E2E que valide que el stub se activa/desactiva correctamente según `ARGUS_VAULT_ENABLED`.

---

🛠️ **Acciones Inmediatas para DAY 164**
1. Aplicar `if(NOT TARGET ...)` en todos los bloques condicionales de `common/CMakeLists.txt` y `enterprise/CMakeLists.txt`.
2. Implementar lectura de `ARGUS_VENDOR_PUBKEY_HEX` en Jenkinsfile + script de validación básica (hex → bin → firma dummy).
3. Crear `mock_vault_provider.cc` que simule respuestas de `GET secret/argus/enterprise/*` con payloads deterministas.
4. Documentar explícitamente en el roadmap: `AppRole = Fase 2 | Gate de merge Fases 3-4`.

📌 **Nota del Consejo:** La regresión `DAY 167` mencionada en el resumen parece ser un typo cronológico (estamos en DAY 163). Si es una referencia a deuda futura o un ID mal transcrito, corríjalo en el commit history para mantener la trazabilidad. El resto del diagnóstico y fix es sólido y alineado con buenas prácticas de build engineering.

**¿Procedemos con la ejecución de DAY 164 bajo estos parámetros o necesitáis ajustes de scope antes de iniciar?**