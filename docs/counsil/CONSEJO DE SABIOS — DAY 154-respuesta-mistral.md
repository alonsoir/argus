**Dictamen del Consejo de Sabios — DAY 154 (aRGus NDR)**
*16 de mayo de 2026 | Respuesta unificada y priorizada*

---

---

## **📜 Resumen Ejecutivo**
**Prioridad para DAY 155: Opción B (Eventos ZMQ) para P1 + Granularidad selectiva para P2 + ZMQ Tuning (HWM primero) para P3 + Posponer P4.**
El progreso de DAY 153-154 es **excelente** (ADR-045 implementado, `FirewallAutonomyReactor` funcional, EMECAS verde). Las decisiones de hoy **consolidan la arquitectura** y preparan el terreno para benchmarks y producción.

---

---

---

## **🔍 Respuestas Detalladas**

---

### **P1 — Señal de autonomía: Polling vs. Eventos ZMQ**
**✅ Opción B (Eventos ZMQ) es la recomendación del Consejo para DAY 155.**

#### **Análisis Comparativo:**
| Criterio               | Polling (etcd)                          | Eventos ZMQ (Pub/Sub)                  |
|------------------------|-----------------------------------------|----------------------------------------|
| **Latencia**           | ~30s (intervalo de polling)             | **~1ms** (tiempo real)                 |
| **Complejidad**        | Baja (reutiliza health-check loop)      | Media (nuevo canal ZMQ)               |
| **Acoplamiento**       | Alto (firewall depende de etcd)         | **Bajo** (solo depende de ZMQ)         |
| **Escalabilidad**      | Media (polling a etcd en todos los nodos)| **Alta** (ZMQ es ligero y eficiente)   |
| **Robustez**           | Media (fallo en etcd = no detección)   | **Alta** (ZMQ tiene reconexión automática) |
| **Consistencia**       | Alta (etcd es fuente de verdad)         | Alta (si se configura correctamente)   |
| **Esfuerzo DAY 155**   | Bajo (1-2h)                             | **Medio (3-4h)**                       |

#### **Razones para elegir ZMQ:**
1. **Latencia crítica:**
    - En un ataque de ransomware, **cada segundo cuenta**. Polling cada 30s **deja una ventana de vulnerabilidad inaceptable**.
    - ZMQ permite **reacción inmediata** (ej: `AUTONOMOUS → DEGRADED` en milisegundos).

2. **Desacoplamiento:**
    - **`CryptoAutonomyStateMachine` (productor)** y **`FirewallAutonomyReactor` (consumidor)** no necesitan conocerse.
    - **ZMQ actúa como bus de eventos interno**, permitiendo que otros componentes (ej: `rag-security`) también reaccionen sin acoplamiento directo.

3. **Alta disponibilidad:**
    - ZMQ **reintenta automáticamente** la conexión si el broker falla (configurable con `ZMQ_RECONNECT_IVL`).
    - **No depende de etcd** (que podría estar comprometido o sobrecargado).

4. **Alineación con la arquitectura existente:**
    - aRGus **ya usa ZMQ** para comunicación entre componentes (`sniffer` ↔ `ml-detector`).
    - **No introduce nuevas dependencias**.

#### **Implementación Recomendada para DAY 155:**
1. **Topic para eventos de autonomía:**
    - Usar **`argus.crypto.autonomy`** (string constante en `constants.hpp`).
2. **Mensaje ZMQ:**
    - **Formato JSON** (fácil de parsear y extensible):
      ```json
      {
        "component": "vault_client",
        "state": "EXTENDED_AUTONOMY",
        "timestamp": "2026-05-16T12:00:00Z",
        "ttl_remaining_seconds": 2592000  // 30 días
      }
      ```
3. **Integración en `CryptoAutonomyStateMachine`:**
    - **Publicar evento al cambiar de estado:**
      ```cpp
      void CryptoAutonomyStateMachine::transition_to(State new_state) {
          // ... lógica existente ...
          if (m_zmq_publisher) {
              m_zmq_publisher->publish("argus.crypto.autonomy", state_to_json(new_state));
          }
      }
      ```
4. **Integración en `FirewallAutonomyReactor`:**
    - **Suscribirse al topic en el constructor:**
      ```cpp
      FirewallAutonomyReactor::FirewallAutonomyReactor() {
          m_zmq_subscriber = std::make_unique<ZmqSubscriber>("argus.crypto.autonomy");
          m_zmq_subscriber->on_message([this](const std::string& msg) {
              auto state = parse_state_from_json(msg);
              this->on_autonomy_state_change(state);
          });
      }
      ```
5. **Manejo de errores:**
    - Si ZMQ falla, **loguear error** pero **no bloquear el reactor** (usar cache local del último estado conocido).

#### **Mitigaciones para ZMQ:**
| Riesgo | Mitigación |
|--------|------------|
| **Pérdida de mensajes** | Usar **`ZMQ_PUB` + `ZMQ_SUB` con `ZMQ_CONFLATE=1`** (últimos mensajes se fusionan). |
| **Broker ZMQ caído** | **Reconexión automática** (`ZMQ_RECONNECT_IVL=5000` ms). |
| **Mensajes duplicados** | **Idempotencia en el reactor** (verificar estado actual antes de aplicar cambios). |
| **Latencia en la red** | **Timeout en el subscriber** (`ZMQ_RCVTIMEO=1000` ms). |

---
**Veredicto:**
**✅ Implementar Opción B (Eventos ZMQ) en DAY 155.**
**Es la opción más robusta y alineada con la arquitectura existente.**

---

---

### **P2 — Granularidad del Default-Deny**
**✅ Default-deny selectivo (preservar tráfico interno) es la recomendación del Consejo.**

#### **Análisis:**
- **Contexto:**
    - **Infraestructura crítica (hospitales)** tiene:
        - **Tráfico interno** (ej: servidores médicos, bases de datos).
        - **Tráfico externo** (ej: internet, VPNs).
    - **Objetivo del modo `AUTONOMOUS`:**
        - **Proteger contra ataques externos** (ej: ransomware desde internet).
        - **Mantener operatividad interna** (ej: acceso a historias clínicas).

- **Opciones:**
  | Opción | Ventajas | Desventajas | Recomendación |
  |--------|----------|-------------|---------------|
  | **Default-deny total** | **Máxima seguridad** (bloquea todo). | **Rompe operatividad interna** (hospital no funciona). | ❌ No recomendado |
  | **Default-deny selectivo** | **Equilibrio seguridad/operatividad**. | **Más complejo de configurar**. | ✅ **Recomendado** |
  | **Default-allow** | **Máxima operatividad**. | **Inseguro** (ataques pueden entrar). | ❌ No recomendado |

#### **Reglas Recomendadas para `AUTONOMOUS`:**
1. **Bloquear todo el tráfico entrante externo:**
   ```bash
   iptables -I INPUT 1 -m comment --comment "argus-autonomy-deny-external" -i eth0 -j DROP
   ```
    - **`eth0`**: Interfaz WAN (externa).
    - **`DROP`**: Descarta paquetes sin respuesta (evita scans).

2. **Permitir tráfico interno (LAN):**
   ```bash
   iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-lan" -i eth1 -s 192.168.0.0/16 -j ACCEPT
   ```
    - **`eth1`**: Interfaz LAN (interna).
    - **`192.168.0.0/16`**: Rango de IPs internas (ajustable).

3. **Permitir loopback (localhost):**
   ```bash
   iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-loopback" -i lo -j ACCEPT
   ```

4. **Permitir tráfico establecido (conexiones existentes):**
   ```bash
   iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-established" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
   ```

5. **Loguear tráfico bloqueado (para análisis forense):**
   ```bash
   iptables -I INPUT 1 -m comment --comment "argus-autonomy-log-drop" -j LOG --log-prefix "ARGUS-AUTONOMY-DROP: "
   ```

#### **Implementación en `FirewallAutonomyReactor`:**
```cpp
void FirewallAutonomyReactor::apply_default_deny() {
    // 1. Bloquear tráfico externo (eth0)
    executor_->execute(R"(
        iptables -I INPUT 1 -m comment --comment "argus-autonomy-deny-external" -i eth0 -j DROP
    )");

    // 2. Permitir tráfico interno (eth1, LAN)
    executor_->execute(R"(
        iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-lan" -i eth1 -s 192.168.0.0/16 -j ACCEPT
    )");

    // 3. Permitir loopback
    executor_->execute(R"(
        iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-loopback" -i lo -j ACCEPT
    )");

    // 4. Permitir tráfico establecido
    executor_->execute(R"(
        iptables -I INPUT 1 -m comment --comment "argus-autonomy-allow-established" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    )");

    // 5. Loguear drops
    executor_->execute(R"(
        iptables -I INPUT 1 -m comment --comment "argus-autonomy-log-drop" -j LOG --log-prefix "ARGUS-AUTONOMY-DROP: "
    )");

    deny_active_ = true;
}
```

#### **Configuración Dinámica:**
- **Leer interfaces y rangos de IPs desde `argus.yaml`:**
  ```yaml
  autonomy:
    external_interface: eth0
    internal_interfaces: [eth1, eth2]
    internal_networks: ["192.168.0.0/16", "10.0.0.0/8"]
  ```
- **Permitir personalización por instalación** (hospitales pueden tener redes distintas).

---
**Veredicto:**
**✅ Default-deny selectivo (bloquear externo, permitir interno).**
**Equilibra seguridad y operatividad en infraestructura crítica.**

---

---

### **P3 — `BACKLOG-ZMQ-TUNING-001`: Parámetros Críticos**
**✅ Priorizar HWM (High-Water Mark) primero, luego `ZMQ_SNDTIMEO`/`ZMQ_RCVTIMEO`.**

#### **Parámetros Críticos para Benchmarks:**
| Parámetro | Descripción | Valor Recomendado | Impacto en Benchmark |
|-----------|-------------|-------------------|----------------------|
| **`ZMQ_HWM`** | High-Water Mark (número máximo de mensajes en cola). | **1000** (ajustar según memoria). | **Evita pérdida de mensajes** por desbordamiento. |
| **`ZMQ_SNDTIMEO`** | Timeout para envío (ms). | **5000** (5s). | **Evita bloqueos** en el productor. |
| **`ZMQ_RCVTIMEO`** | Timeout para recepción (ms). | **5000** (5s). | **Evita bloqueos** en el consumidor. |
| **`ZMQ_RECONNECT_IVL`** | Intervalo de reconexión (ms). | **5000** (5s). | **Recuperación rápida** tras fallos. |
| **`ZMQ_LINGER`** | Tiempo para drenar mensajes al cerrar (ms). | **1000** (1s). | **Evita pérdida de mensajes** al cerrar sockets. |
| **`ZMQ_CONFLATE`** | Fusionar mensajes en cola (1 = último mensaje). | **1** (para topics de estado). | **Reduce latencia** en eventos de autonomía. |

#### **Orden de Prioridad para DAY 155:**
1. **`ZMQ_HWM`** (P0):
    - **Problema:** Si el HWM es demasiado bajo (ej: 10), **se pierden mensajes** en picos de tráfico.
    - **Cómo ajustar:**
        - **Fórmula:** `HWM = (memoria_disponible_MB * 0.1) / (tamaño_mensaje_promedio_KB)`.
        - **Ejemplo:** Si un mensaje promedio es 1KB y hay 8GB de RAM → `HWM = (8000 * 0.1) / 1 = 800`.
        - **Recomendación inicial:** **1000** (monitorear uso de memoria).

2. **`ZMQ_SNDTIMEO` y `ZMQ_RCVTIMEO`** (P1):
    - **Problema:** Timeouts demasiado cortos (ej: 100ms) pueden causar **falsos fallos** en redes lentas.
    - **Recomendación:** **5000ms** (5s) para empezar.

3. **`ZMQ_RECONNECT_IVL`** (P2):
    - **Recomendación:** **5000ms** (5s).

4. **`ZMQ_LINGER`** (P2):
    - **Recomendación:** **1000ms** (1s).

5. **`ZMQ_CONFLATE`** (P2):
    - **Recomendación:** **1** (solo para topics de estado como `argus.crypto.autonomy`).

#### **Implementación en Código:**
```cpp
// Configuración ZMQ en el publisher (CryptoAutonomyStateMachine)
zmq::socket_t publisher(context, ZMQ_PUB);
publisher.setsockopt(ZMQ_HWM, 1000);          // High-Water Mark
publisher.setsockopt(ZMQ_SNDTIMEO, 5000);     // Send timeout (ms)
publisher.setsockopt(ZMQ_LINGER, 1000);        // Linger time (ms)
publisher.bind("tcp://*:5556");

// Configuración ZMQ en el subscriber (FirewallAutonomyReactor)
zmq::socket_t subscriber(context, ZMQ_SUB);
subscriber.setsockopt(ZMQ_RCVTIMEO, 5000);     // Receive timeout (ms)
subscriber.setsockopt(ZMQ_RECONNECT_IVL, 5000); // Reconnect interval (ms)
subscriber.setsockopt(ZMQ_CONFLATE, 1);        // Fusionar mensajes
subscriber.connect("tcp://localhost:5556");
subscriber.setsockopt(ZMQ_SUBSCRIBE, "argus.crypto.autonomy", 0);
```

#### **Benchmarking:**
- **Herramienta:** Usar `zmq_perf` (incluida con ZeroMQ) para medir:
    - **Latencia** (tiempo entre `send` y `recv`).
    - **Throughput** (mensajes/segundo).
    - **Pérdida de mensajes** (con `ZMQ_HWM` bajo vs. alto).
- **Comando ejemplo:**
  ```bash
  zmq_perf local_lat tcp://127.0.0.1:5556 1000 10000
  ```

---
**Veredicto:**
**✅ Priorizar `ZMQ_HWM` (1000) + `ZMQ_SNDTIMEO`/`ZMQ_RCVTIMEO` (5000ms).**
**Estos parámetros son críticos para evitar pérdida de mensajes y bloqueos.**

---

---
### **P4 — `DEBT-CAPTURE-BACKEND-ISP-001` (Interface Segregation)**
**⚠ Posponer a post-DAY 155.**
**Primero consolidar la integración ZMQ del reactor (P1-P3).**

#### **Análisis:**
- **Deuda:**
    - `CaptureBackend` tiene métodos eBPF-específicos (`get_xdp_stats()`) que **no deberían estar en el interfaz base**.
    - **Solución:** Moverlos a `EbpfBackend` (clase derivada).

- **Prioridad:**
    - **P2 (post-FEDER)** vs. **P1 (pre-FEDER)** de las otras deudas.
    - **No bloquea** el desarrollo actual (el código funciona, solo es un problema de diseño).

- **Riesgo de posponer:**
    - **Bajo:** El código actual **compila y funciona**.
    - **Alto:** Si se pospone demasiado, **la deuda técnica crece**.

#### **Recomendación:**
- **Posponer a DAY 156+** (tras completar P1-P3).
- **Crear una tarea en el backlog:**
  ```markdown
  ## DEBT-CAPTURE-BACKEND-ISP-001
  **Prioridad:** P2
  **Descripción:** Mover métodos eBPF-específicos (`get_xdp_stats()`) de `CaptureBackend` a `EbpfBackend`.
  **Impacto:** Mejora el diseño (ISP), pero no afecta funcionalidad.
  **Esfuerzo:** 2-3h.
  ```

---
**Veredicto:**
**✅ Posponer a post-DAY 155.**
**Enfocar DAY 155 en P1-P3 (integración ZMQ, granularidad firewall, tuning ZMQ).**

---

---
---
## **📌 Plan de Acción para DAY 155**

| Tarea | Prioridad | Tiempo Estimado | Responsable | Dependencias |
|-------|-----------|------------------|-------------|--------------|
| **Implementar eventos ZMQ para autonomía** (P1) | P0 | 3-4h | Alonso | Ninguna |
| **Ajustar `FirewallAutonomyReactor` a default-deny selectivo** (P2) | P0 | 2h | Alonso | P1 |
| **Configurar parámetros ZMQ (`HWM`, timeouts)** (P3) | P1 | 1-2h | Alonso | Ninguna |
| **Probar integración completa** | P0 | 1h | Alonso | P1 + P2 + P3 |
| **Documentar en ADR-045** | P1 | 1h | Alonso | P1 + P2 + P3 |

---
**Orden recomendado:**
1. **Mañana (4h):**
    - Implementar eventos ZMQ (`DEBT-AUTONOMY-ZMQ-EVENTS-001`).
    - Configurar parámetros ZMQ (`BACKLOG-ZMQ-TUNING-001`).
2. **Tarde (3h):**
    - Ajustar `FirewallAutonomyReactor` a default-deny selectivo.
    - Probar integración completa (EMECAS).
3. **Última hora (1h):**
    - Documentar cambios en `ADR-045`.

---

---
---
## **⚠ Riesgos y Mitigaciones**

| Riesgo | Mitigación |
|--------|------------|
| **Eventos ZMQ perdidos** | Usar `ZMQ_CONFLATE=1` + logging de eventos. |
| **Default-deny demasiado restrictivo** | Permitir tráfico interno (LAN) y loopback. |
| **ZMQ HWM demasiado bajo** | Empezar con `HWM=1000` y ajustar según benchmarks. |
| **Falta de tiempo para P4** | Posponer `DEBT-CAPTURE-BACKEND-ISP-001` a DAY 156. |

---

---
---
## **💡 Recomendaciones Adicionales**

1. **Testing de Integración:**
    - **Probar escenario de corte WAN:**
      ```bash
      # Simular corte WAN (en VM)
      sudo iptables -A INPUT -i eth0 -j DROP
      # Verificar que el firewall entra en AUTONOMOUS
      tail -f /var/log/argus/firewall.log
      ```
    - **Probar revocación explícita:**
      ```bash
      # Enviar evento de revocación manualmente (para test)
      echo '{"state": "REVOKED"}' | zmq_pub -b tcp://localhost:5556 argus.crypto.autonomy
      ```

2. **Benchmarking ZMQ:**
    - **Herramienta:** `zmq_perf` (incluida con ZeroMQ).
    - **Métricas clave:**
        - Latencia (debe ser **<1ms** en local).
        - Throughput (debe ser **>10K msg/s** para el tráfico esperado).

3. **Documentación:**
    - **Añadir diagrama de secuencia** para el flujo de eventos ZMQ:
      ```mermaid
      sequenceDiagram
          participant StateMachine
          participant ZMQ
          participant FirewallReactor
          StateMachine->>ZMQ: Publish("argus.crypto.autonomy", {state: "AUTONOMOUS"})
          ZMQ->>FirewallReactor: Deliver message
          FirewallReactor->>FirewallReactor: apply_default_deny()
      ```
    - **Actualizar `README.md`** con ejemplos de configuración ZMQ.

4. **Seguridad:**
    - **Cifrar tráfico ZMQ** (si no está ya cifrado):
      ```cpp
      // Usar curva CurveZMQ (similar a Curve25519)
      zmq::socket_t socket(context, ZMQ_PUB);
      socket.setsockopt(ZMQ_CURVE_SERVER, 1);
      socket.setsockopt(ZMQ_CURVE_SECRETKEY, secret_key.c_str());
      ```
    - **Restringir acceso a ZMQ** (solo localhost o red interna).

---
---
## **📝 Conclusión Final**
**Prioridad para DAY 155:**
1. **✅ Eventos ZMQ para autonomía (P1).**
2. **✅ Default-deny selectivo (P2).**
3. **✅ Tuning ZMQ (HWM primero) (P3).**
4. **❌ Posponer ISP en `CaptureBackend` (P4).**

**Para el Consejo:**
¿Estáis de acuerdo con este plan? **Sí**, es el enfoque más robusto para **cerrar las deudas P1 antes del deadline FEDER** y garantizar que el sistema **proteja infraestructuras críticas incluso sin conectividad**.