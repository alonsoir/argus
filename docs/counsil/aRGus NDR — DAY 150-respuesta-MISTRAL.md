**Dictamen del Consejo de Sabios — DAY 150 (aRGus NDR)**
*13 de mayo de 2026 | Respuesta unificada y priorizada*

---

---

## **📜 Resumen Ejecutivo**
**El progreso de DAY 150 es excepcional:**
✅ **EMECAS verde completo** (4 PRs mergeados, 0 fallos).
✅ **ADR-044 implementado** (`provision_crypto.sh`, `vault_client`, Jenkinsfile).
✅ **Modelo open-core claro** (community vs. enterprise).

**Respuestas clave a las preguntas:**
1. **Compilación condicional (`#ifdef`)** es **preferible** a dos binarios (Q1).
2. **Orden de migración** es correcto, pero **`sniffer` debe ir antes que `ml-detector`** (Q2).
3. **`etcd-server` debe escribir su estado en un fichero local** (`/run/argus/etcd-crypto-status.json`) (Q3).
4. **Cache persistente en `/etc/ml-defender/` para producción** (Q4).
5. **`ARGUS_VAULT_ENABLED` es suficiente para open-core**, pero **Falco/OpenCanary/Neo4j podrían ser flags adicionales** (Q5).

---
**Prioridad para DAY 151:**
1. **Integración `etcd-server` con `VaultClient`** (P0).
2. **DEBT-CRYPTO-HEARTBEAT-001** (P1).
3. **Ansible Jinja2** (P1).

---

---

---

## **🔍 Respuestas Detalladas a Q1-Q5**

---

---

### **Q1 — Compilación Condicional vs. Dos Binarios**
**✅ **`#ifdef ARGUS_VAULT_ENABLED` es la opción correcta.**

#### **Análisis:**
| Opción | Ventajas | Desventajas | Recomendación |
|--------|----------|-------------|---------------|
| **`#ifdef`** | **Mantenimiento unificado** (mismo código, misma lógica). | Riesgo de **divergencia silenciosa** si no se testea bien. | ✅ **Recomendado** |
| **Dos binarios** | **Aislamiento total** (community vs. enterprise). | **Duplicación de código**, mantenimiento complejo. | ❌ No recomendado |

#### **Argumentos a favor de `#ifdef`:**
1. **Mantenimiento unificado:**
    - **Mismo código base** para ambos modos (community/enterprise).
    - **Menos divergencia** (los cambios en la lógica común se aplican a ambos).
2. **Testing simplificado:**
    - **Mismos tests** para ambos modos (solo cambiar el flag).
    - **EMECAS** puede validar ambos caminos con `ARGUS_VAULT_ENABLED=ON/OFF`.
3. **Flexibilidad:**
    - **Fácil de activar/desactivar** en tiempo de compilación.
    - **No requiere cambios en el despliegue** (mismo binario, diferente configuración).

#### **Mitigación del riesgo de divergencia:**
1. **Tests obligatorios para ambos modos:**
    - **CI/CD debe ejecutar tests con `ARGUS_VAULT_ENABLED=ON` y `OFF`.**
    - **Ejemplo en Jenkinsfile:**
      ```groovy
      stages {
          stage('Test Community') {
              steps { sh 'make test ARGUS_VAULT_ENABLED=OFF' }
          }
          stage('Test Enterprise') {
              steps { sh 'make test ARGUS_VAULT_ENABLED=ON' }
          }
      }
      ```
2. **Documentación clara:**
    - **Añadir un `ADR-045: Open-Core Separation Strategy`** que documente:
        - **Qué está detrás de `ARGUS_VAULT_ENABLED`** (solo governance criptográfico).
        - **Qué NO está detrás** (ej: lógica de detección, ML, etc.).
3. **Auditoría de código:**
    - **Herramientas como `cppcheck` o `clang-tidy`** para detectar código muerto (`#ifdef` no utilizado).

#### **Veredicto:**
**✅ Mantener `#ifdef ARGUS_VAULT_ENABLED`**, pero:
- **Asegurar que todos los tests pasan en ambos modos.**
- **Documentar claramente la separación open-core en un ADR dedicado.**

---

---

### **Q2 — Orden de Migración de Componentes**
**✅ Orden propuesto es correcto, pero ajustar prioridad de `sniffer`.**

#### **Análisis de dependencias:**
| Componente | Dependencias | Riesgo si falla | Prioridad |
|------------|---------------|------------------|-----------|
| **`etcd-server`** | Ninguna (bootstrap). | **Bloquea todo el sistema.** | 1 |
| **`sniffer`** | `etcd-server` (para registrar estado). | **Pérdida de telemetría.** | **2** |
| **`ml-detector`** | `etcd-server`, `sniffer` (datos de entrada). | **Pérdida de detección ML.** | 3 |
| **`firewall-acl-agent`** | `etcd-server`, `ml-detector` (alertas). | **Pérdida de bloqueo automático.** | 4 |
| **`rag-ingester`** | `etcd-server`. | **Pérdida de logs RAG.** | 5 |
| **`rag-security`** | `etcd-server`, `rag-ingester`. | **Pérdida de análisis RAG.** | 6 |

#### **Recomendación:**
**✅ Orden ajustado:**
1. **`etcd-server`** (bootstrap, sin dependencias).
2. **`sniffer`** (captura de tráfico, dependencia crítica para `ml-detector`).
3. **`ml-detector`** (necesita datos de `sniffer`).
4. **`firewall-acl-agent`** (necesita alertas de `ml-detector`).
5. **`rag-ingester`** (independiente, pero depende de `etcd-server`).
6. **`rag-security`** (depende de `rag-ingester`).

#### **Justificación:**
- **`sniffer` debe ir antes que `ml-detector`** porque este último **depende de los datos de tráfico** que genera `sniffer`.
- **`firewall-acl-agent` depende de `ml-detector`** (para bloquear basándose en alertas ML).
- **`rag-ingester` y `rag-security`** son **independientes del pipeline de detección**, pero aún necesitan `etcd-server`.

---
---

### **Q3 — `register_etcd_status` sin etcd disponible en bootstrap**
**✅ `etcd-server` debe escribir su estado en un fichero local (`/run/argus/etcd-crypto-status.json`).**

#### **Análisis:**
- **Problema:**
    - `etcd-server` **no puede registrarse en etcd antes de arrancar** (no hay etcd disponible).
    - Los demás componentes **esperan a que `etcd-server` esté listo** (via `/health/crypto_ready`).
- **Soluciones posibles:**
  | Opción | Ventajas | Desventajas |
  |--------|----------|-------------|
  | **Fichero local** (`/run/argus/etcd-crypto-status.json`) | Simple, no depende de etcd. | **No es distribuido** (solo visible en el nodo local). |
  | **Endpoint HTTP** (`/health/crypto_ready`) | **Distribuido** (cualquier nodo puede consultarlo). | Requiere que `etcd-server` exponga un endpoint HTTP. |
  | **etcd auto-registro** (escribir en sí mismo) | **Consistente con el resto del sistema.** | **Complejidad** (etcd-server debe arrancar con etcd disponible). |

#### **Recomendación:**
**✅ Usar fichero local + endpoint HTTP (solución híbrida).**
1. **`etcd-server` escribe su estado en `/run/argus/etcd-crypto-status.json`:**
   ```json
   {
     "component": "etcd-server",
     "crypto_ready": true,
     "timestamp": "2026-05-13T12:00:00Z",
     "public_key_fingerprint": "sha256:..."
   }
   ```
2. **`etcd-server` expone un endpoint HTTP `/health/crypto_ready`** que devuelve el contenido del fichero.
3. **Los demás componentes:**
    - **Primero consultan `/health/crypto_ready` de `etcd-server`** (via HTTP).
    - **Si falla, leen el fichero local** (fallback para single-node).

#### **Implementación:**
- **En `etcd-server`:**
  ```cpp
  // Tras derivar el keypair:
  std::ofstream status_file("/run/argus/etcd-crypto-status.json");
  status_file << R"({
      "component": "etcd-server",
      "crypto_ready": true,
      "timestamp": ")" << current_utc_time() << R"(",
      "public_key_fingerprint": ")" << fingerprint << "\""
  })";

  // Iniciar servidor HTTP (ej: con libmicrohttpd)
  start_http_server(8080, [](const char* path) {
      if (std::string(path) == "/health/crypto_ready") {
          return read_file("/run/argus/etcd-crypto-status.json");
      }
      return "404 Not Found";
  });
  ```
- **En otros componentes:**
  ```cpp
  bool wait_for_etcd_crypto_ready() {
      // 1. Intentar HTTP (preferido)
      if (auto response = http_get("http://etcd-server:8080/health/crypto_ready")) {
          if (response.status == 200) return true;
      }
      // 2. Fallback: leer fichero local (single-node)
      if (std::ifstream file("/run/argus/etcd-crypto-status.json")) {
          return parse_json(file).crypto_ready;
      }
      return false;
  }
  ```

---
---

### **Q4 — Cache tmpfs y `vagrant destroy`**
**✅ Cache persistente en `/etc/ml-defender/{component}/crypto-cache/` para producción.**

#### **Análisis:**
| Entorno | Cache Location | TTL | Permisos | Justificación |
|---------|----------------|-----|----------|---------------|
| **Dev (Vagrant)** | `/run/argus/crypto-cache/` (tmpfs) | 1h | 0700 | **EMECAS requiere limpieza total** en cada ciclo. |
| **Prod (Edge)** | `/etc/ml-defender/{component}/crypto-cache/` | 72h | 0600 | **Supervive reboots**, pero no es permanente. |

#### **Recomendación:**
1. **Dev (Vagrant):**
    - **Mantener tmpfs** (`/run/argus/crypto-cache/`).
    - **TTL corto** (1h) para forzar renovación frecuente.
2. **Prod (Edge):**
    - **Cache persistente en `/etc/ml-defender/{component}/crypto-cache/`**.
    - **TTL largo** (72h) para **sobrevivir reboots**.
    - **Permisos estrictos** (`0600`, usuario `argus`).
    - **Cifrado adicional** (opcional): Usar `fscrypt` para cifrar el directorio.

#### **Implementación:**
- **En `vault_client.cpp`:**
  ```cpp
  #ifdef ARGUS_VAULT_ENABLED
      std::string get_cache_path() {
          #ifdef PRODUCTION
              return "/etc/ml-defender/" + component_name + "/crypto-cache/";
          #else
              return "/run/argus/crypto-cache/";
          #endif
      }
  #endif
  ```
- **En `provision_crypto.sh` (prod):**
  ```bash
  # Crear directorio de cache con permisos seguros
  mkdir -p /etc/ml-defender/{component}/crypto-cache
  chown argus:argus /etc/ml-defender/{component}/crypto-cache
  chmod 0600 /etc/ml-defender/{component}/crypto-cache
  ```

---
---

### **Q5 — Open-Core: `ARGUS_VAULT_ENABLED` como único separador**
**✅ `ARGUS_VAULT_ENABLED` es suficiente para el MVP, pero considerar flags adicionales para funcionalidades avanzadas.**

#### **Análisis:**
| Funcionalidad | ¿Detrás de `ARGUS_VAULT_ENABLED`? | ¿Nuevo flag? | Recomendación |
|---------------|------------------------------------|--------------|---------------|
| **Governance criptográfico** | ✅ Sí | ❌ No | Mantener actual. |
| **Falco actuation** | ❌ No | ✅ `ARGUS_FALCO_ENABLED` | **Nuevo flag** (depende de kernel eBPF). |
| **Neo4j graph** | ❌ No | ✅ `ARGUS_NEO4J_ENABLED` | **Nuevo flag** (depende de librerías externas). |
| **OpenCanary honeypot** | ❌ No | ✅ `ARGUS_HONEYPOT_ENABLED` | **Nuevo flag** (módulo opcional). |
| **RAG (Retrieval-Augmented Generation)** | ❌ No | ⚠ `ARGUS_RAG_ENABLED` | **Opcional** (depende de Python/ML). |

#### **Recomendación:**
1. **Mantener `ARGUS_VAULT_ENABLED` como flag principal** (governance criptográfico).
2. **Añadir flags adicionales para funcionalidades opcionales:**
    - **`ARGUS_FALCO_ENABLED`**: Actuación en tiempo real (eBPF).
    - **`ARGUS_NEO4J_ENABLED`**: Integración con grafo de memoria histórica.
    - **`ARGUS_HONEYPOT_ENABLED`**: OpenCanary (honeypot).
3. **Documentar en `ADR-045: Open-Core Feature Flags`**:
   | Flag | Descripción | Dependencias | Estado |
   |------|-------------|---------------|--------|
   | `ARGUS_VAULT_ENABLED` | Governance criptográfico (Vault). | libvault_client, Vault server. | ✅ Estable |
   | `ARGUS_FALCO_ENABLED` | Actuación en kernel (eBPF). | libfalco, kernel headers. | 🟡 Experimental |
   | `ARGUS_NEO4J_ENABLED` | Memoria histórica (Neo4j). | libneo4j-cpp, Neo4j server. | 🟡 Experimental |
   | `ARGUS_HONEYPOT_ENABLED` | Honeypot (OpenCanary). | Python 3.10+, OpenCanary. | 🟡 Experimental |

#### **Implementación:**
- **En `CMakeLists.txt`:**
  ```cmake
  option(ARGUS_VAULT_ENABLED "Enable Vault-based crypto governance" OFF)
  option(ARGUS_FALCO_ENABLED "Enable Falco eBPF actuation" OFF)
  option(ARGUS_NEO4J_ENABLED "Enable Neo4j historical memory" OFF)
  option(ARGUS_HONEYPOT_ENABLED "Enable OpenCanary honeypot" OFF)
  ```
- **En el código:**
  ```cpp
  #ifdef ARGUS_FALCO_ENABLED
      #include <falco.h>
      // Lógica de Falco
  #endif
  ```

---
---
---
## **📌 Resumen de Decisiones para DAY 151**

| Pregunta | Decisión | Acción Concreta |
|----------|----------|-----------------|
| **Q1** | `#ifdef ARGUS_VAULT_ENABLED` | Mantener compilación condicional. Añadir tests para ambos modos. |
| **Q2** | Orden ajustado: `etcd-server` → `sniffer` → `ml-detector` → `firewall-acl-agent` → `rag-ingester` → `rag-security` | Actualizar documentación de migración. |
| **Q3** | Fichero local + endpoint HTTP | Implementar `/run/argus/etcd-crypto-status.json` + `/health/crypto_ready`. |
| **Q4** | Cache persistente en `/etc/ml-defender/` (prod) | Modificar `vault_client.cpp` para usar paths condicionales. |
| **Q5** | `ARGUS_VAULT_ENABLED` + flags adicionales (`FALCO`, `NEO4J`, `HONEYPOT`) | Añadir opciones en `CMakeLists.txt` y documentar en ADR-045. |

---
---
## **🚀 Orden de Implementación para DAY 151**
1. **P0 — Integración `etcd-server` con `VaultClient`** (Q1, Q3):
    - Compilación condicional (`#ifdef ARGUS_VAULT_ENABLED`).
    - Fichero local `/run/argus/etcd-crypto-status.json` + endpoint HTTP.
2. **P1 — DEBT-CRYPTO-HEARTBEAT-001** (Q3):
    - Implementar `register_etcd_status()` real + keepalive (TTL=10s).
3. **P1 — Ansible Jinja2** (Q2):
    - Templates para `firewall-acl-agent`, `etcd-server`, `rag-ingester`, `rag-security`.
4. **P2 — ADR-045: Open-Core Feature Flags** (Q5):
    - Documentar flags (`VAULT`, `FALCO`, `NEO4J`, `HONEYPOT`).

---
---
## **⚠ Riesgos Residuales y Mitigaciones**

| Riesgo | Mitigación |
|--------|------------|
| **Divergencia silenciosa con `#ifdef`** | Tests obligatorios para ambos modos (`ON`/`OFF`). |
| **`etcd-server` no expone `/health/crypto_ready`** | Fallback a fichero local (single-node). |
| **Cache persistente comprometida** | Permisos `0600` + `fscrypt` (opcional). |
| **Flags adicionales no documentados** | Crear `ADR-045` con tabla de flags. |

---
---
## **💡 Recomendaciones Adicionales**
1. **Testing de integración:**
    - **Probar el flujo completo** (`etcd-server` → `sniffer` → `ml-detector`) con `ARGUS_VAULT_ENABLED=ON/OFF`.
    - **Simular fallos de Vault** (¿los componentes usan cache correctamente?).
2. **Documentación:**
    - **Actualizar `README.md`** con instrucciones para compilación open-core.
    - **Añadir ejemplos de `CMakeLists.txt`** para cada flag.
3. **Seguridad:**
    - **Auditar permisos** de `/etc/ml-defender/{component}/crypto-cache/` (debe ser `0600`).
    - **Loguear accesos a Vault** (para detectar intentos no autorizados).

---
---
## **📝 Conclusión Final**
**El diseño actual es robusto y alinea con las mejores prácticas en sistemas distribuidos seguros.**
- **Prioridad DAY 151:** Integración `etcd-server` + `VaultClient` (P0).
- **Open-core:** `ARGUS_VAULT_ENABLED` es suficiente para el MVP, pero **flags adicionales** (`FALCO`, `NEO4J`, `HONEYPOT`) son recomendables para funcionalidades avanzadas.
- **Cache:** **tmpfs para dev**, **persistente para prod**.

**Para el Consejo:**
¿Estáis de acuerdo con **priorizar la integración de `etcd-server` con `VaultClient` y el fichero local de estado** para DAY 151? **Sí**, es el paso crítico para desbloquear el resto del pipeline.