### **Respuestas del Consejo de Sabios para DAY 164**

---

---

## **📌 Q1 — HttpEtcdRegistrar: etcd-cpp-apiv3 vs HTTP directo (cpp-httplib)**

**🔹 Recomendación unánime: `etcd-cpp-apiv3`**

### Razonamiento:
1. **Dependencia ya resuelta**: `etcd-cpp-apiv3 v0.15.3` **ya está instalado** en `provision.sh`. No añade complejidad de *deploy* ni riesgo de *drift* de versiones.
2. **Fiabilidad en watches**: El **watch nativo** de etcd-cpp-apiv3 (via gRPC) es *battle-tested* para conexiones persistentes. `cpp-httplib` requeriría implementar lógicas de *reconexión*, *timeout*, y *heartbeat* manualmente, lo que introduce **puntos de fallo** en un sistema crítico.
3. **Keepalive nativo**: El *lease TTL* + *refresh thread* está **integrado** en la librería. Reimplementarlo con HTTP directo sería **error-prone** (ej.: manejo de *lease IDs*, *renewal race conditions*).
4. **Consistencia con el stack**: `etcd-cpp-apiv3` usa **gRPC**, que ya es parte del ecosistema de etcd. HTTP directo añadiría un *protocolo alternativo* sin beneficio claro.
5. **Mantenimiento**: Menos código propio = menos superficie de *bugs*. La librería ya maneja *backoff*, *retry*, y *error handling* de forma robusta.

**⚠️ Mitigación del riesgo de threading**:
El modelo de threading de gRPC (usado por etcd-cpp-apiv3) **no debe bloquear** el hilo principal. Solución:
- Usar el *event loop* de etcd-cpp-apiv3 en un **hilo dedicado** (1 por `HttpEtcdRegistrar`).
- Aislar el *watch callback* en una cola *lock-free* (ej.: `moodstool::ConcurrentQueue`) para evitar bloqueos en el *health-check loop*.

---
---

## **📌 Q2 — Watch de etcd: polling vs long-poll vs gRPC watch**

**🔹 Recomendación unánime: `gRPC watch` (nativo en etcd-cpp-apiv3)**

### Razonamiento:
| Opción               | Latencia  | Overhead | Complejidad | Fiabilidad (fallos de red) | Recomendación |
|----------------------|-----------|----------|-------------|-----------------------------|----------------|
| **Polling (1s)**    | 0–1s      | Alto     | Baja        | ❌ (Falsos negativos)       | ❌             |
| **HTTP long-poll**  | 0–1s      | Medio    | Media       | ⚠️ (Timeouts, reconexión)   | ⚠️             |
| **gRPC watch**       | **~0ms**  | **Bajo** | **Media**   | ✅ (Reconexión automática)  | **✅**         |

1. **Grace period de 10s**: Un *polling cada 1s* **no garantiza** detección inmediata (ej.: cambio en `t=0.5s` → detectado en `t=1s`). **gRPC watch** notifica en **~millisegundos**.
2. **Eficiencia**: gRPC usa **conexión persistente** (HTTP/2), evitando el *overhead* de abrir/cerrar conexiones en cada *poll*.
3. **Reconexión automática**: etcd-cpp-apiv3 **reintenta** automáticamente si la conexión cae (configurable con *retry policies*).
4. **Consistencia**: etcd **garantiza** que los *watches* reciban todos los eventos *después del punto de registro* (no así el polling, que puede perder eventos entre *polls*).

**⚠️ Consideración operacional**:
- **Monitorear el estado del watch**: Si el *gRPC stream* falla, el `CryptoEpochCoordinator` debe **escalar a polling de respaldo** (ej.: cada 500ms) hasta que el *watch* se restablezca.
- **Timeouts**: Configurar *watch timeout* = `grace_period / 2` (5s) para evitar *stale watches*.

---
---

## **📌 Q3 — `CryptoEpochCoordinator`: hilo dedicado vs integrado en health-check loop**

**🔹 Recomendación mayoritaria: `Integrado en el health-check loop existente` (5/6 votos)**
*(1 voto a favor de hilo dedicado, con justificación de aislamiento)*

### Razonamiento:
1. **Contexto del sistema**:
    - `etcd-server/main.cpp` ya tiene un *health-check loop* cada **5s**.
    - Grace period = **10s** → **2 checks por grace period** es suficiente para detectar cambios.
    - Los 6 componentes ya tienen **múltiples hilos** (ZMQ, keepalive, autonomy). Añadir 6 hilos más (1 por componente) **aumentaría la complejidad de debugging** y el *contention* de recursos.

2. **Ventajas de la integración**:
    - **Sin hilo adicional**: Menos *overhead* de scheduling y memoria.
    - **Ritmo controlado**: El *health-check loop* ya está **optimizado** para el sistema (ej.: prioridad de scheduling, *affinity*).
    - **Acoplamiento aceptable**: `coordinator.poll()` sería una **llamada no bloqueante** (ej.: *check-and-return* en O(1)).

3. **Diseño propuesto**:
   ```cpp
   // En etcd-server/main.cpp
   void health_check_loop() {
       while (running) {
           // ... (health checks existentes)
           crypto_epoch_coordinator.poll();  // ← No bloqueante
           std::this_thread::sleep_for(5s);
       }
   }
   ```
    - `poll()`:
        - Si hay un *watch activo* (gRPC), **no hace nada** (el callback ya actualizó el estado).
        - Si el *watch falló*, **fuerza un refresh** de Vault y reintenta el *watch*.
        - **Métricas**: Contador de *poll calls* y *watch failures* para observabilidad.

4. **¿Cuándo usar hilo dedicado?**
   Solo si:
    - El *grace period* se reduce a **< 2s** (requeriría polling más frecuente).
    - Se necesite **prioridad de tiempo real** (no es el caso aquí).

**⚠️ Compromiso para el voto disidente**:
Si se opta por hilo dedicado, **limitar a 1 hilo compartido** para todos los `CryptoEpochCoordinator` (usando un *thread pool* estático), no 1 por componente.

---
---
---
## **📜 Resumen de Decisiones para DAY 164**

| Pregunta | Decisión | Justificación Clave |
|----------|----------|---------------------|
| **Q1** | `etcd-cpp-apiv3` | Dependencia ya instalada + watch/keepalive nativos. |
| **Q2** | `gRPC watch` | Latencia mínima + reconexión automática. |
| **Q3** | **Integrado en health-check loop** | Evita hilos adicionales; ritmo de 5s es suficiente para grace period de 10s. |

---
**🎯 Próximos pasos para el equipo**:
1. **FASE 2a**: Implementar `HttpEtcdRegistrar` con `etcd-cpp-apiv3` + *watch gRPC* + *lease keepalive*.
2. **FASE 2b**: `CryptoEpochCoordinator::poll()` **no bloqueante**, integrado en el *health-check loop* de `main.cpp`.
3. **Métricas críticas**:
    - `argus_crypto_epoch_watch_latency_ms` (histograma).
    - `argus_crypto_epoch_poll_calls_total` (contador).
    - `argus_crypto_epoch_stale_events` (contador de fallos).

**⚠️ Advertencia del Consejo**:
El *stub* actual (`StubEtcdRegistrar`) **debe eliminarse** tras implementar `HttpEtcdRegistrar` para evitar *tech debt* oculto. Validar que **todos los tests** que usaban el *stub* ahora usen el *mock* de `HttpEtcdRegistrar`.

---
**🔒 PI como árbitro final**: Si el PI discrepa, se recomienda **documentar la decisión en ADR-045 v2** con el *trade-off* explícito (ej.: "Usamos HTTP long-poll por X, aceptando Y latencia").