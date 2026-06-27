Empezamos por la publicación para el Consejo:

---

## Consejo de Sabios — Cierre DAY 163 + Contexto DAY 164

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Rama activa:** `feature/day161-enterprise-crypto-integration`

---

### Lo que hemos hecho hoy (DAY 163)

**FASE 0 — BACKLOG-CRYPTO-VENDOR-KEY-001 CERRADA**

`enterprise_vendor.key` eliminado permanentemente del disco y del repo. Implementado **Modelo B (zero-trust efímero)**: cada `vagrant destroy && vagrant up` genera un keypair Ed25519 enterprise nuevo, lo sube a Vault dev, genera un token enterprise firmado, y limpia `/tmp`. El `vendor.key` nunca persiste en disco — solo en Vault inmem durante la vida de la VM. `enterprise_vendor.pub` y `enterprise.token` marcados como gitignored (efímeros por diseño). `plugin-loader/CMakeLists.txt` eliminado el hex hardcodeado — guard `FATAL_ERROR` si enterprise build sin `-DARGUS_ENTERPRISE_PUBKEY_HEX`. `Makefile [2/4]` lee el hex de Vault en runtime antes de invocar cmake. `test-dual-compilation` 4/4 verde.

**FASE 1 — BACKLOG-CRYPTO-HOT-RELOAD-001 CERRADA**

Implementado `CryptoProviderHandle` — wrapper RCU header-only sobre `std::atomic<shared_ptr<ICryptoProvider>>`. Garantías: `get()` nunca devuelve null, `reload()` es swap atómico lock-free, el provider anterior sobrevive hasta que todos los readers liberen su `shared_ptr` (refcount → 0). 9/9 tests verdes incluyendo test de concurrencia (8 readers + 50 reloads) y test RCU con `weak_ptr` que verifica destrucción diferida. 12/12 suite `common` verde.

**ADR-045 v1 — revisado por Consejo 8/8**

Enviado al Consejo de Sabios. Respuestas recibidas y sintetizadas. Decisiones del PI:

- **P1:** `not_before` como coordinación. Sin 2PC. ACKs solo para observabilidad post-hoc. Kimi cambió de posición tras contra-argumento: jitter de scheduling es 0.02% del grace period de 5s — no justifica complejidad de protocolo.
- **P2:** Grace period global configurable, default **10s**. No por componente.
- **P3:** `etcd-server` escribe `/argus/crypto/epoch` en FASE 2. Lógica criptográfica en `CryptoEpochCoordinator` dentro de `vault_client` — etcd-server habla con él pero no contiene la lógica.
- **P4:** Nuevo estado `EPOCH_TRANSITION` + `EPOCH_FAILED` en autonomy state machine. `AUTONOMOUS_EPOCH_STALE` documentado para FASE 5.
- **P5:** Header wire extendido: `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4]`. Definido ahora, implementado en FASE 3.

**Descubrimiento crítico al final de DAY 163:**

`etcd_registrar` es un **stub puro** (`StubEtcdRegistrar` — logs a stderr, sin conexión real a etcd). No existe `HttpEtcdRegistrar` real. El watch de `/argus/crypto/epoch` que necesita `CryptoEpochCoordinator` no puede construirse sobre el stub. Esto añade un prerequisito no registrado previamente:

```
DEBT-ETCD-REGISTRAR-REAL-001 (nueva, P0 DAY 164)
    StubEtcdRegistrar → HttpEtcdRegistrar real
    con etcd-cpp-apiv3 (ya instalado en provision.sh)
    prerequisito bloqueante de CryptoEpochCoordinator
```

---

### Lo que haremos en DAY 164

```
FASE 2a — DEBT-ETCD-REGISTRAR-REAL-001 (prerequisito)
    HttpEtcdRegistrar con etcd-cpp-apiv3:
    - register_status() real → PUT /argus/crypto/components/<name>
    - start_keepalive() real → lease TTL + refresh thread
    - stop_keepalive() real
    - watch() → primera infraestructura de watch en vault_client
    TDH: RED→GREEN obligatorio

FASE 2b — BACKLOG-CRYPTO-EPOCH-001 (depende de 2a)
    CryptoEpochCoordinator en vault_client:
    - watch /argus/crypto/epoch
    - on_epoch_change(): VaultProvider::refresh() → handle.reload()
    - escribe ack de observabilidad en etcd
    - integración en etcd-server/main.cpp

ADR-045 v2 — redactar documento formal tras feedback del Consejo
```

---

### Preguntas al Consejo para DAY 164

**Q1 — HttpEtcdRegistrar: ¿etcd-cpp-apiv3 o HTTP directo?**

Ya tenemos `etcd-cpp-apiv3` v0.15.3 instalado en `provision.sh`. La alternativa es HTTP directo via `cpp-httplib` (ya en el codebase para otros usos).

- **etcd-cpp-apiv3:** API idiomática C++, watch nativo, keepalive via lease. Pero es una dependencia adicional con su propio modelo de threading (gRPC).
- **cpp-httplib directo:** Sin dependencia nueva, HTTP/1.1 long-poll para watch. Más control, más código, menos fiable para watches prolongados.

¿Cuál recomendáis para un sistema embedded en infraestructura crítica donde la simplicidad operacional es prioritaria?

**Q2 — Watch de etcd: polling vs long-poll vs gRPC watch**

`etcd v3` soporta tres patrones:
- **gRPC watch:** Conexión persistente bidireccional. Nativo en etcd-cpp-apiv3. Más eficiente pero requiere gestión de reconexión.
- **HTTP long-poll:** `GET /v3/watch` con timeout. Más simple, sin estado de conexión.
- **Polling periódico:** `GET /v3/kv/range` cada N segundos. Más simple aún, latencia hasta N segundos.

Para un grace period de 10s, ¿el polling cada 1s es aceptable o necesitamos watch real?

**Q3 — `CryptoEpochCoordinator`: ¿hilo dedicado o integrado en el health-check loop existente?**

`etcd-server/main.cpp` ya tiene un health-check loop que corre cada 5s. Dos opciones:

- **Hilo dedicado en `CryptoEpochCoordinator`:** Encapsula su propio threading, más limpio, pero añade un hilo por componente.
- **Integrado en el loop existente:** El caller (main.cpp) llama a `coordinator.poll()` cada iteración. Sin hilo extra, pero acopla el coordinador al ritmo del caller.

¿Cuál preferís para un sistema con 6 componentes que ya tienen múltiples hilos (ZMQ, keepalive, autonomy)?

---

Razonad de forma independiente. El PI es el árbitro final.

---

