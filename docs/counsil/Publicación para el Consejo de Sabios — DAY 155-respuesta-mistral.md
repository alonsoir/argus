**Dictamen del Consejo de Sabios — DAY 155 (aRGus NDR)**
*17 de mayo de 2026 | Respuesta unificada y estratégica*

---

---

## **📜 Resumen Ejecutivo**
**Decisiones clave para DAY 156:**
1. **Q1:** **Opción A (`etcd-server`)** como proceso propietario de `CryptoAutonomyStateMachine`.
2. **Q2:** **Mantener `ipc://` para edge nodes** (mismo host), pero **soportar `tcp://` para topologías distribuidas** (configurable).
3. **Q3:** **`reconcile_interval_sec` configurable desde `firewall.json`** (default 90s). El reconciliador **reaplica el último estado conocido** (sin consultar Vault/etcd).
4. **Q4:** **Estructura `enterprise/` en raíz** (no `common/enterprise/` ni `plugins/`). Anticipar cambios en `CMakeLists.txt` para condicionalidad.
5. **Q5:** **Hacer benchmarks sintéticos en VirtualBox** (línea base), pero **marcar claramente como "no representativos de producción"**.

---
**Prioridad DAY 156 confirmada:**
1. **P0:** Integrar `CryptoAutonomyStateMachine` en `etcd-server` (Q1).
2. **P1:** `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (estado en `/run/argus/crypto-autonomy-state.json`).
3. **P1:** `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` (firma Ed25519 en bootstrap).
4. **P2:** `DEBT-CRYPTO-AUTONOMY-001` (máquina de estados completa).

---

---

---

## **🔍 Respuestas Detalladas**

---

### **Q1 — Proceso Propietario de `CryptoAutonomyStateMachine`**
**✅ Opción A: `etcd-server` es el proceso correcto.**

#### **Análisis:**
| Opción | Ventajas | Desventajas | Veredicto |
|--------|----------|-------------|-----------|
| **A: `etcd-server`** | ✅ Ya conoce el estado de Vault (health-checks). ✅ Centralizado (un solo publisher). ✅ Arranca primero (bootstrap). | ⚠ Añade responsabilidad a `etcd-server`. | **✅ Recomendado** |
| **B: `argus-crypto-daemon`** | ✅ Separación de responsabilidades. | ❌ Nuevo proceso (complejidad adicional). | ❌ No recomendado |
| **C: `sniffer`** | ✅ Primer componente en arrancar. | ❌ `sniffer` no tiene contexto de Vault. | ❌ No recomendado |
| **D: Múltiples publishers** | ✅ Redundancia. | ❌ **Inconsistencia** (varios publishers pueden desincronizarse). | ❌ No recomendado |

#### **Razones para `etcd-server`:**
1. **Contexto de Vault:**
    - `etcd-server` **ya interactúa con Vault** (para su propia configuración).
    - **Conoce el estado de salud de Vault** (via health-checks).
2. **Centralización:**
    - **Un solo publisher** evita inconsistencias (ej: dos componentes publicando estados distintos).
3. **Orden de arranque:**
    - `etcd-server` **arranca primero** (bootstrap), por lo que puede publicar el estado inicial.
4. **Alta disponibilidad:**
    - Si `etcd-server` falla, **el cluster etcd puede elegir un nuevo líder** que asuma el rol de publisher.

#### **Implementación:**
1. **En `etcd-server/main.cpp`:**
   ```cpp
   int main() {
       // 1. Inicializar CryptoAutonomyStateMachine
       auto state_machine = std::make_shared<CryptoAutonomyStateMachine>();
       auto publisher = std::make_shared<AutonomyPublisher>("ipc:///run/argus/autonomy.sock");
       state_machine->set_transition_callback([publisher](const AutonomyState& state) {
           publisher->publish(state);
       });

       // 2. Inicializar VaultClient (si ARGUS_VAULT_ENABLED)
       #ifdef ARGUS_VAULT_ENABLED
           auto vault_client = std::make_shared<VaultClient>(...);
           state_machine->set_vault_health_check([vault_client]() {
               return vault_client->is_healthy();
           });
       #endif

       // 3. Iniciar etcd-server
       g_server->start();
   }
   ```
2. **Asegurar que `etcd-server` publique el estado inicial:**
    - Al arrancar, `state_machine->transition_to(State::NORMAL)` (si Vault está saludable).

---
**Veredicto:**
**✅ `etcd-server` como proceso propietario (Opción A).**

---

---

### **Q2 — Endpoint Pub/Sub en Producción**
**✅ Mantener `ipc://` para edge nodes, pero soportar `tcp://` para topologías distribuidas.**

#### **Análisis:**
- **Edge Node (Hospital):**
    - **`firewall-acl-agent` y `etcd-server` corren en el mismo host.**
    - **`ipc://` es óptimo** (baja latencia, sin overhead de red).
- **Servidor Central (Cluster):**
    - **Varios componentes pueden correr en hosts distintos.**
    - **`tcp://` es necesario** (ej: `tcp://central-server:5556`).

#### **Solución:**
- **Configurable desde `firewall.json`:**
  ```json
  {
    "autonomy": {
      "zmq_endpoint": "ipc:///run/argus/autonomy.sock"  // Default para edge
    }
  }
  ```
- **En producción (cluster):**
  ```json
  {
    "autonomy": {
      "zmq_endpoint": "tcp://central-server:5556"
    }
  }
  ```
- **Lógica en `AutonomyPublisher` y `AutonomySubscriber`:**
  ```cpp
  // En AutonomyPublisher (etcd-server)
  std::string endpoint = config["autonomy"]["zmq_endpoint"];
  publisher.bind(endpoint);  // ipc:// o tcp://

  // En AutonomySubscriber (firewall-acl-agent)
  std::string endpoint = config["autonomy"]["zmq_endpoint"];
  subscriber.connect(endpoint);
  ```

#### **Seguridad:**
- **Para `tcp://`:**
    - **Cifrar el tráfico ZMQ** con `ZMQ_CURVE` (Curve25519):
      ```cpp
      // Configurar claves en publisher/subscriber
      socket.setsockopt(ZMQ_CURVE_SERVER, 1);
      socket.setsockopt(ZMQ_CURVE_SECRETKEY, secret_key.c_str());
      socket.setsockopt(ZMQ_CURVE_PUBLICKEY, public_key.c_str());
      ```
    - **Restringir acceso** a la IP del servidor central.

---
**Veredicto:**
**✅ `ipc://` para edge nodes, `tcp://` para clusters.**
**Configurable desde `firewall.json`.**

---

---

### **Q3 — `reconcile_interval_sec` en `AutonomySubscriber`**
**✅ Configurable desde `firewall.json` (default 90s). Reaplica el último estado conocido.**

#### **Análisis:**
- **Propósito del reconciliador:**
    - **Safety net** para el caso en que el evento ZMQ se pierda (ej: `firewall-acl-agent` arranca después de que `etcd-server` publique el estado).
- **¿Consultar a Vault/etcd?**
    - **No.** El reconciliador **no debe depender de servicios externos** (Vault/etcd podrían estar caídos).
    - **Reaplicar el último estado conocido** (almacenado en memoria o en `/run/argus/crypto-autonomy-state.json`).
- **Intervalo:**
    - **90s es razonable** para un hospital (equilibrio entre detección rápida y overhead).
    - **Configurable** para permitir ajustes por instalación.

#### **Implementación:**
1. **En `firewall.json`:**
   ```json
   {
     "autonomy": {
       "reconcile_interval_sec": 90
     }
   }
   ```
2. **En `AutonomySubscriber`:**
   ```cpp
   AutonomySubscriber::AutonomySubscriber(const Config& config)
       : m_reconcile_interval(std::chrono::seconds(config.autonomy.reconcile_interval_sec)) {
       // ...
   }

   void AutonomySubscriber::start_reconciliator() {
       std::thread([this]() {
           while (true) {
               std::this_thread::sleep_for(m_reconcile_interval);
               if (m_last_state) {
                   apply_state(*m_last_state);  // Reaplica último estado conocido
               }
           }
       }).detach();
   }
   ```

---
**Veredicto:**
**✅ Configurable desde `firewall.json` (default 90s).**
**Reaplica el último estado conocido (sin consultar Vault/etcd).**

---

---

### **Q4 — Estructura de Carpetas para Código Enterprise**
**✅ `enterprise/` en raíz del proyecto.**

#### **Análisis:**
| Opción | Ventajas | Desventajas | Veredicto |
|--------|----------|-------------|-----------|
| **`enterprise/`** | ✅ Claro y explícito. ✅ Fácil de excluir de builds community. | ⚠ Requiere ajustes en `CMakeLists.txt`. | **✅ Recomendado** |
| **`plugins/enterprise/`** | ✅ Alinea con el modelo de plugins. | ❌ `VaultClient` no es un plugin (es infraestructura). | ❌ No recomendado |
| **`common/enterprise/`** | ✅ Mantiene código relacionado. | ❌ Mezcla código core con enterprise. | ❌ No recomendado |

#### **Estructura Propuesta:**
```
argus/
├── common/               # Código core (open-source)
│   ├── crypto_autonomy.h
│   ├── autonomy_publisher.h
│   └── ...
├── enterprise/           # Código enterprise (cerrado)
│   ├── vault_client/
│   │   ├── vault_client.h
│   │   └── vault_client.cpp
│   ├── VaultProvider/
│   │   ├── vault_provider.h
│   │   └── vault_provider.cpp
│   └── CMakeLists.txt     # Build condicional (ARGUS_VAULT_ENABLED)
├── firewall-acl-agent/   # Componente (usa common/ o enterprise/)
├── etcd-server/          # Componente (usa common/ o enterprise/)
└── CMakeLists.txt        # Raíz (incluye enterprise/ si ARGUS_VAULT_ENABLED=ON)
```

#### **Cambios en `CMakeLists.txt` Raíz:**
```cmake
# Incluir enterprise/ solo si ARGUS_VAULT_ENABLED=ON
if(ARGUS_VAULT_ENABLED)
    add_subdirectory(enterprise)
endif()
```

#### **Ventajas:**
- **Separación clara** entre código open-source (`common/`) y enterprise (`enterprise/`).
- **Fácil de excluir** en builds community (solo desactivar `ARGUS_VAULT_ENABLED`).
- **No afecta** a la estructura existente de componentes (`firewall-acl-agent/`, `etcd-server/`, etc.).

---
**Veredicto:**
**✅ `enterprise/` en raíz.**
**Anticipar cambios en `CMakeLists.txt` para condicionalidad.**

---

---

### **Q5 — Benchmarks Sintéticos en VirtualBox**
**✅ Hacer benchmarks sintéticos en VirtualBox, pero marcar como "no representativos".**

#### **Análisis:**
| Opción | Ventajas | Desventajas | Veredicto |
|--------|----------|-------------|-----------|
| **Benchmarks en VirtualBox** | ✅ Rápido de ejecutar. ✅ Línea base para desarrollo. | ❌ Números **no representativos** (VirtualBox no refleja hardware real). | ✅ **Recomendado** |
| **Esperar a hardware físico** | ✅ Números precisos. | ❌ Retrasa el desarrollo. | ❌ No recomendado |

#### **Recomendaciones:**
1. **Ejecutar benchmarks sintéticos:**
    - **Herramienta:** Usar `zmq_perf` (incluida con ZeroMQ) o un script personalizado.
    - **Métricas:**
        - **Latencia** (tiempo entre `send` y `recv`).
        - **Throughput** (mensajes/segundo).
        - **Pérdida de mensajes** (con diferentes `HWM`).
    - **Configuración:**
        - **VirtualBox:** 4 vCPUs, 8GB RAM, red en modo "bridged".
        - **Carga:** Simular tráfico de `sniffer` → `ml-detector` (ej: 10K msg/s).

2. **Documentar limitaciones:**
    - **En el paper/readme:**
      > *"Los benchmarks sintéticos en VirtualBox proporcionan una línea base para desarrollo, pero **no son representativos del rendimiento en hardware físico**. Los resultados en producción pueden variar significativamente debido a factores como la latencia de red, el rendimiento del disco, y la optimización del kernel."*

3. **Ejemplo de script de benchmark:**
   ```bash
   # Benchmark de latencia (1000 mensajes de 1KB)
   zmq_perf local_lat tcp://127.0.0.1:5556 1000 1024

   # Benchmark de throughput (10K mensajes de 1KB)
   zmq_perf remote_thr tcp://127.0.0.1:5556 10000 1024
   ```

4. **Hardware físico (FEDER):**
    - **Priorizar** una vez disponible (para números reales).

---
**Veredicto:**
**✅ Hacer benchmarks sintéticos en VirtualBox.**
**Marcar claramente como "no representativos de producción".**

---

---
---
## **📌 Plan de Acción para DAY 156**

| Prioridad | Tarea | Detalles | Tiempo Estimado |
|-----------|-------|----------|------------------|
| **P0** | Integrar `CryptoAutonomyStateMachine` en `etcd-server` | Opción A (Q1). | 3-4h |
| **P1** | `DEBT-AUTONOMY-STATE-PERSISTENCE-001` | Estado en `/run/argus/crypto-autonomy-state.json`. | 2h |
| **P1** | `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` | Firma Ed25519 en bootstrap status. | 2h |
| **P2** | `DEBT-CRYPTO-AUTONOMY-001` | Máquina de estados completa. | 2h |
| **P2** | Benchmarks sintéticos en VirtualBox | `BACKLOG-BENCHMARK-CAPACITY-001`. | 2h |

---
**Orden recomendado:**
1. **Mañana (4h):**
    - **P0:** Integrar `CryptoAutonomyStateMachine` en `etcd-server`.
2. **Tarde (4h):**
    - **P1:** `DEBT-AUTONOMY-STATE-PERSISTENCE-001` + `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001`.
3. **Si hay tiempo:**
    - **P2:** Benchmarks sintéticos.

---

---
---
## **⚠ Riesgos y Mitigaciones**

| Riesgo | Mitigación |
|--------|------------|
| **`etcd-server` sobrecargado** | Monitorear CPU/memoria tras integración. |
| **Inconsistencia en estado de autonomía** | Usar **un solo publisher** (`etcd-server`). |
| **Benchmarks engañosos** | **Marcar como "no representativos"** en documentación. |
| **Problemas de compilación con `enterprise/`** | Probar builds con `ARGUS_VAULT_ENABLED=ON/OFF`. |

---

---
---
## **💡 Recomendaciones Adicionales**

1. **Testing de Integración:**
    - **Probar escenario de corte WAN:**
      ```bash
      # Simular corte WAN en VM
      sudo iptables -A INPUT -i eth0 -j DROP
      # Verificar que el firewall entra en AUTONOMOUS
      tail -f /var/log/argus/firewall.log
      ```
    - **Probar revocación explícita:**
      ```bash
      # Enviar evento de revocación manualmente
      echo '{"state": "REVOKED"}' | zmq_pub -b tcp://localhost:5556 argus.crypto.autonomy
      ```

2. **Documentación:**
    - **Añadir diagrama de arquitectura** en `ADR-045`:
      ```mermaid
      graph TD
          A[etcd-server] -->|pub| B[ipc:///run/argus/autonomy.sock]
          B --> C[firewall-acl-agent]
          C --> D[apply_default_deny]
      ```
    - **Actualizar `README.md`** con ejemplos de configuración ZMQ y autonomía.

3. **Seguridad:**
    - **Cifrar tráfico ZMQ en producción** (usar `ZMQ_CURVE`).
    - **Restringir permisos** en `/run/argus/autonomy.sock` (solo usuario `argus`).

4. **Benchmarking:**
    - **Comparar resultados** entre `ipc://` y `tcp://` (latencia, throughput).
    - **Documentar hardware** usado en VirtualBox (vCPUs, RAM, SO).

---
---
## **📝 Conclusión Final**
**Decisiones clave para DAY 156:**
1. **✅ `etcd-server` como proceso propietario de `CryptoAutonomyStateMachine` (Q1).**
2. **✅ `ipc://` para edge nodes, `tcp://` para clusters (Q2).**
3. **✅ `reconcile_interval_sec` configurable (default 90s), reaplica último estado conocido (Q3).**
4. **✅ Estructura `enterprise/` en raíz (Q4).**
5. **✅ Benchmarks sintéticos en VirtualBox (marcados como no representativos) (Q5).**

**Para el Consejo:**
¿Estáis de acuerdo con este plan? **Sí**, es el enfoque más robusto para **cerrar las deudas P0/P1 antes del deadline FEDER** y garantizar que el sistema **proteja infraestructuras críticas incluso sin conectividad**. **La autonomía edge es la prioridad absoluta.**