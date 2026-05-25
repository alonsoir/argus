## Síntesis del Consejo — DAY 164 (8/8 respuestas)

### Q1 — etcd-cpp-apiv3 vs HTTP directo

**Consenso 8/8: etcd-cpp-apiv3.**

Sin disidencias. El argumento es unánime: la dependencia ya está pagada en `provision.sh`, reimplementar watches/leases/keepalive sobre HTTP directo es crear un mini-cliente etcd propio peor que el que ya existe. ChatGPT añade un punto arquitectónico valioso: aislar el cliente en `common/etcd/` para no contaminar el árbol con includes gRPC.

**Decisión:** etcd-cpp-apiv3. Interface `IEtcdRegistrar` existente se mantiene — `HttpEtcdRegistrar` la implementa internamente sin exponer tipos gRPC al exterior.

---

### Q2 — Polling vs long-poll vs gRPC watch

**Fractura 6/8 watch vs 2/8 polling.**

- **Watch gRPC** (Claude, ChatGPT, Gemini, Grok, Mistral, Qwen): Latencia <100ms, push-based, reconexión automática. El grace period de 10s es para la transición segura, no para descubrir el cambio.
- **Polling 1s** (DeepSeek, Kimi): Argumento KISS — determinista, sin estado de conexión, 1s de latencia es solo 10% del grace period.

**El argumento de DeepSeek/Kimi es honesto** pero tiene un fallo: asume que el grace period de 10s es holgado. Gemini lo articula mejor — los 10s son para drain de buffers y validación criptográfica, no para absorber latencia de detección. Si empezamos a consumir margen desde el descubrimiento, el sistema se vuelve frágil ante cualquier carga.

**Decisión:** gRPC watch nativo. Polling cada 2s como fallback degradado si el watch cae — no como mecanismo principal. ChatGPT añade algo importante: guardar `last_seen_revision` para resume seguro tras reconexión — sin eso podemos perder eventos durante el reconnect.

---

### Q3 — Hilo dedicado vs integrado en health-check loop

**Fractura más interesante: 5/8 hilo dedicado vs 3/8 integrado.**

- **Hilo dedicado** (Claude, ChatGPT, Gemini, Mistral, Qwen): Responsabilidades distintas, latencia de hasta 5s si se integra en el loop de 5s es demasiado ajustado para grace de 10s, aislamiento de fallos.
- **Integrado en loop** (DeepSeek, Kimi, Grok): Menos hilos, 5s ≤ 10s es suficiente, embedded-friendly.

**El argumento de Kimi es el más fino de los tres:** si el watch gRPC ya corre en su propio hilo (manejado por etcd-cpp-apiv3), el `coordinator.poll()` en el health loop es simplemente drenar la cola de eventos — no bloqueante, O(1). En ese caso el "hilo dedicado" ya existe implícitamente dentro de la librería.

**Pero hay un problema con el loop integrado que nadie menciona explícitamente:** el health-check loop de `main.cpp` es específico de `etcd-server`. Los otros 5 componentes (sniffer, firewall, ml-detector...) no tienen ese loop — tendrían que crearlo. El hilo dedicado encapsulado en `CryptoEpochCoordinator` es reutilizable en todos los componentes sin requerir que cada `main.cpp` tenga su propio loop de polling.

**Decisión:** Hilo dedicado encapsulado, con el matiz de Kimi: el hilo interno es el drain de la cola de callbacks gRPC. El reload ocurre via `std::function` callback en el contexto del coordinador, no del caller. `start()/stop()` como única API de threading visible.

---

### Puntos nuevos que el Consejo añade (no estaban en la propuesta)

Tres contribuciones que merecen entrar en ADR-045 v2:

**1. `last_seen_revision` (ChatGPT):** Persistir la revision de etcd vista en el último evento para resume seguro tras reconexión. Sin esto, un reconnect puede perder eventos de época.

**2. Estados del watch (ChatGPT):** `WATCH_CONNECTED` → `WATCH_DEGRADED` → `WATCH_STALE`. Necesario para FASE 5 (`AUTONOMOUS_EPOCH_STALE`).

**3. ACK con timestamp monotónico (ChatGPT):**
```json
{
  "epoch": 42,
  "component": "etcd-server",
  "ack_ts_monotonic_ns": 1234567890
}
```
Para análisis forense y debugging distribuido — especialmente relevante en hospitales donde los incidentes requieren trazabilidad completa.

---

### Tabla de decisiones finales DAY 164

| Pregunta | Decisión | Ratio Consejo |
|----------|----------|---------------|
| Q1 Cliente etcd | etcd-cpp-apiv3 | 8/8 |
| Q2 Watch | gRPC watch + fallback polling 2s | 6/8 |
| Q3 Threading | Hilo dedicado encapsulado en CryptoEpochCoordinator | 5/8 |
| Nuevo: revision tracking | `last_seen_revision` obligatorio | ChatGPT |
| Nuevo: watch states | `WATCH_CONNECTED/DEGRADED/STALE` | ChatGPT |
| Nuevo: ACK timestamp | Monotónico en ns | ChatGPT |

---

**¿Confirmas estas decisiones como PI antes de que te pida BACKLOG.md y README.md?**
Confirmado.