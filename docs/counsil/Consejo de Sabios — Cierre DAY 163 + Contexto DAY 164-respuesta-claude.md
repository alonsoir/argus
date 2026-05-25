## Claude — Respuestas DAY 164 preguntas al Consejo

### Q1 — HttpEtcdRegistrar: ¿etcd-cpp-apiv3 o HTTP directo?

**etcd-cpp-apiv3.**

El argumento de simplicidad operacional favorece paradójicamente la librería, no el HTTP directo. Razón concreta: el watch de etcd sobre HTTP/1.1 long-poll requiere gestionar manualmente reconexiones, timeouts, parsing de respuestas chunked y heartbeats de la conexión. Eso es más código de infraestructura frágil que el wrapper gRPC que ya tenemos instalado.

El coste real de etcd-cpp-apiv3 es el modelo de threading de gRPC — pero ese coste ya está pagado: `provision.sh` instala la librería y sus dependencias desde DAY 160. No añadimos deuda de instalación, solo de uso.

**Condición:** El hilo gRPC de etcd-cpp-apiv3 debe ser el único propietario del canal watch. `CryptoEpochCoordinator` recibe callbacks, no gestiona la conexión directamente. Esto es exactamente lo que la API de etcd-cpp-apiv3 ofrece con `etcd::Watcher`.

### Q2 — Watch de etcd: polling vs long-poll vs gRPC watch

**gRPC watch nativo**, con una matización sobre el grace period.

Para un grace period de 10s, el polling cada 1s es técnicamente suficiente — la latencia máxima de detección sería 1s sobre un grace period de 10s, un 10% de overhead. Pero el argumento en contra del polling no es de latencia sino de fiabilidad: si el proceso está bajo carga (GC, ZMQ burst), el polling puede saltarse una iteración. Con gRPC watch el evento llega por callback independientemente de la carga del caller.

La reconexión automática es el único punto de complejidad real del gRPC watch. Mitigo así: `CryptoEpochCoordinator` implementa un watchdog interno — si no recibe heartbeat del watch en 30s, reconecta. Ese código es ~20 líneas y elimina el único riesgo operacional del gRPC watch.

**Polling como fallback de emergencia:** Si el watch cae y el watchdog no reconecta en 2 intentos, `CryptoEpochCoordinator` cae a polling cada 2s hasta restablecer la conexión. Nunca queda ciego a cambios de época.

### Q3 — ¿Hilo dedicado o integrado en el health-check loop?

**Hilo dedicado en `CryptoEpochCoordinator`**, con matiz importante.

El health-check loop existente en `etcd-server/main.cpp` tiene periodo de 5s. Si el coordinador depende de ese loop, la latencia de detección de nueva época es hasta 5s sobre un grace period de 10s — demasiado ajustado. Además acopla el coordinador al ritmo del caller, lo que viola la separación de concerns que acordamos en P3.

El coste de un hilo extra es real pero aceptable. Los 6 componentes ya tienen: hilo ZMQ publisher, hilo keepalive de Vault, hilo de autonomy. Un hilo más de ~2KB de stack en espera de callbacks gRPC es ruido.

**El patrón correcto:**

```cpp
class CryptoEpochCoordinator {
    std::thread watch_thread_;   // duerme en callback gRPC
    std::atomic<bool> stop_;
    // callback → llama al caller via std::function<void(uint64_t epoch_id)>
    // el caller (main.cpp) hace handle.reload() en su propio contexto
};
```

El hilo del coordinador no hace el reload directamente — solo notifica via callback. El reload ocurre en el contexto del caller para evitar races con el material criptográfico en uso. Esta separación es crítica.

---

**Síntesis de mi posición:**

etcd-cpp-apiv3 + gRPC watch + hilo dedicado con callback. Es la combinación más limpia y más fiable. El único riesgo es la reconexión del gRPC watch — mitigado con watchdog de 30s + fallback a polling.