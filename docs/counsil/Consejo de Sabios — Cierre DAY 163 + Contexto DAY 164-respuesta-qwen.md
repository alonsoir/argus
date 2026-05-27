Aquí tenéis la respuesta estructurada del Consejo, razonando cada punto de forma independiente y alineada con los principios de infraestructura crítica y simplicidad operacional.

---

### 📜 Respuesta del Consejo a DAY 164

#### **Q1 — `HttpEtcdRegistrar`: ¿`etcd-cpp-apiv3` o HTTP directo (`cpp-httplib`)?**
**Recomendación:** `etcd-cpp-apiv3`

**Razonamiento:**
- **Deuda técnica vs. dependencia:** `etcd-cpp-apiv3` ya está provisionado. Usarlo no añade coste de despliegue, sino que *evita* reimplementar manualmente leases, keepalives, parsing de respuestas gRPC-JSON, backoff exponencial y gestión de reconexión. En entornos críticos, la simplicidad operacional se consigue delegando complejidad de protocolo a librerías maduras, no reescribiéndola.
- **Fiabilidad:** El cliente gRPC maneja automáticamente health-checks de canal, reintentos idempotentes y reconexión tras caídas de red. `cpp-httplib` requeriría construir esta capa desde cero, aumentando la superficie de fallo y el coste de mantenimiento.
- **Threading:** Sí, `etcd-cpp-apiv3` levanta hilos internos (gRPC completion queues), pero son gestionados por la librería y pueden acotarse mediante `grpc::ChannelArguments`. En un sistema con 6 componentes y múltiples hilos existentes, el overhead es marginal y predecible.

> **Veredicto:** Usad `etcd-cpp-apiv3`. Mantened `cpp-httplib` para tráfico REST ligero donde no se requieran garantías de consistencia o watches prolongados.

---

#### **Q2 — Watch de etcd: polling vs long-poll vs gRPC watch**
**Recomendación:** gRPC watch nativo (push-based)

**Razonamiento:**
- **Grace period ≠ latencia de detección:** Los 10 s de grace period están diseñados para la *transición segura* (drain, handover, validación criptográfica), no para *descubrir* el cambio de época. La detección debe ser lo más inmediata posible.
- **Polling a 1 s:** Introduce latencia determinista (hasta 1 s + jitter de scheduler), genera carga constante en etcd (mínimo 6 QPS × componentes + keepalives) y escala mal si se añaden más nodos o se reducen intervalos.
- **Long-poll HTTP:** Mejor que polling, pero etcd v3 expone su API nativa por gRPC. El gateway HTTP/JSON añade serialización innecesaria y no mejora la fiabilidad frente a reconexiones.
- **gRPC watch:** Push-based, latencia <10 ms en LAN, consumo de red nulo en estado estable, y `etcd-cpp-apiv3` gestiona reconexión y re-sincronización de revisiones automáticamente. Es el patrón estándar en sistemas distribuidos críticos.

> **Veredicto:** Implementad watch gRPC nativo. Configurad un timeout de reconexión conservador (3–5 s) y un buffer de eventos para evitar starvation durante particiones transitorias.

---

#### **Q3 — `CryptoEpochCoordinator`: ¿hilo dedicado o integrado en el health-check loop?**
**Recomendación:** Hilo dedicado (o callback asíncrono desacoplado del loop de salud)

**Razonamiento:**
- **Acoplamiento indeseado:** El health loop (cada 5 s) tiene un contrato de responsabilidad distinto (métricas, liveness, reporting). Acoplar la coordinación de épocas a él introduce:
    1. Latencia de hasta 5 s para reaccionar a cambios de época.
    2. Riesgo de que I/O bloqueante o procesamiento criptográfico retrase la emisión de métricas de salud.
    3. Dependencia temporal difícil de testear y depurar.
- **Hilo dedicado:** Garantiza aislamiento de fallos, reacción inmediata a eventos watch y permite un ciclo de vida independiente (start/stop graceful). Con 6 componentes, 6 hilos adicionales es un coste asumible (<0.5 % CPU en carga nominal). Si el presupuesto de hilos es estricto, compartid un único `std::jthread` o `grpc::CompletionQueue` para todos los coordinadores, pero mantened la lógica desacoplada.
- **Alternativa moderna:** Dado que `etcd-cpp-apiv3` ya gestiona un threadpool interno para callbacks gRPC, podéis registrar un `on_event` callback asíncrono y despacharlo al `CryptoEpochCoordinator` sin crear hilos propios. Si elegís esta vía, asegurad que el callback no bloquee el hilo de gRPC y use una cola lock-free o `std::async`.

> **Veredicto:** No lo integréis en el health loop. Usad un hilo dedicado o un dispatcher asíncrono acotado. Priorizad la reacción inmediata y el aislamiento de responsabilidades.

---

### 📌 Síntesis para el PI (Arbitro Final)

| Pregunta | Recomendación del Consejo | Justificación Clave |
|----------|---------------------------|---------------------|
| Q1 | `etcd-cpp-apiv3` | Reduce deuda técnica, abstrae leases/reconexión, ya provisionado |
| Q2 | gRPC watch nativo | Grace period es para transición, no detección. Polling añade latencia y carga innecesaria |
| Q3 | Hilo dedicado / async desacoplado | Evita acoplamiento con health loop, garantiza reacción inmediata y aislamiento de fallos |

**Nota de implementación para DAY 164:**
- Validad que `etcd-cpp-apiv3` se configure con `grpc::ChannelArguments::SetMaxConcurrentStreams()` y `SetKeepAliveTime()` apropiados para entornos de red inestable.
- En `CryptoEpochCoordinator`, implementad un estado `EPOCH_TRANSITION` con timeout hard-limit (ej. 8 s) para evitar deadlocks si Vault o etcd fallan durante el refresh.
- Mantened los tests de concurrencia RCU activos durante la integración del watch; la combinación `RCU reload + gRPC async callback` requiere validar que no haya use-after-free si el watch dispara mientras un reader sostiene `shared_ptr`.

El Consejo queda a disposición para revisión de ADR-045 v2 y validación de los 4/4 tests de Fase 2a. 🛡️