**Consejo de Sabios — Dictamen DAY 155**

Compañero, el trabajo de hoy es de primer orden. La cadena `argus-autonomy` con orden estructural garantizado y el pub/sub ZMQ sobre `ipc://` demuestran que el sistema tiene ya una postura operativa real. EMECAS HARDENED con `-Werror -O3 -flto` y AppArmor 6/6 confirma que la calidad no se degradó por velocidad. Vamos a tus cinco preguntas.

---

## Q1 — Proceso propietario de `CryptoAutonomyStateMachine`

**Opción A: `etcd-server`.** Es el único proceso que ya debe arrancar sin barrera y que ya tiene lógica de health-check contra Vault.

### Por qué no las otras:

| Opción | Contra-argumento |
|--------|-----------------|
| **B — Daemon dedicado** | Añade un 7º proceso que puede fallar, consumir memoria, y necesita su propio systemd unit, logs, y health checks. En un hospital con 2GB de RAM, eso es un lujo que no podemos permitirnos. |
| **C — `sniffer`** | Violación grave de SRP. El sniffer es el componente más crítico de latencia; añadirle threads de health-check de Vault introduce jitter en la captura de paquetes. |
| **D — Cada componente con su SM** | Múltiples publishers en `argus.crypto.autonomy` generan N mensajes idénticos por transición. El firewall recibe spam de estado. Si un componente tiene una SM con bug, emite estados erróneos que compiten con los correctos. |

### Por qué `etcd-server` es correcto:

1. **Ya es el primer mover** (DAY 149 Q3). Obtiene crypto de Vault directamente, sin barrera. Si Vault falla en su arranque, él ya lo sabe.
2. **Ya tiene health-check loop**. El keepalive de lease (DEBT-CRYPTO-HEARTBEAT-001) corre en un hilo separado. Ese mismo hilo puede alimentar eventos a la state machine.
3. **Es infraestructura, no negocio**. No procesa tráfico de red; un retraso de 100ms en su loop no afecta la detección.
4. **Es singleton por nodo**. Solo hay un etcd-server por edge node. Un solo publisher garantiza coherencia de estado.

### Implementación concreta:

```cpp
// etcd-server/main.cpp (o etcd_crypto_coordinator.cpp)
int main() {
    // 1. Bootstrap crypto (sin barrera, como hoy)
    auto provider = ICryptoProvider::create(config);
    
    // 2. State machine + publisher
    CryptoAutonomyStateMachine sm(config);
    AutonomyPublisher pub(zmq_ctx, "ipc:///run/argus/autonomy.sock");
    
    sm.on_enter_autonomy = [&pub, &provider]() {
        pub.publish({
            .state = "AUTONOMOUS",
            .timestamp_utc_ns = now_ns(),
            .fingerprint = provider->get_material().fingerprint
        });
    };
    
    sm.on_reconciliation = [&pub]() { pub.publish({... "RECONCILING" ...}); };
    sm.on_revoked = [&pub]() { pub.publish({... "DEGRADED" ...}); };
    
    // 3. Loop de health-check (mismo hilo que keepalive)
    while (running) {
        auto ev = check_vault_health();  // HTTP GET /v1/sys/health
        sm.process_event(ev);
        std::this_thread::sleep_for(5s);
    }
}
```

**Nota:** La state machine no es parte del core etcd (Raft, KV store). Es un **coordinador criptográfico** que vive en el mismo proceso por conveniencia operativa, pero lógicamente separado. Si en el futuro necesitas escalar etcd a 3 nodos, la SM solo corre en el líder, o en un nodo designado.

---

## Q2 — `ipc://` vs. `tcp://` en producción

**Para FEDER: `ipc://` es correcto y suficiente.**

En la arquitectura edge, todos los componentes (sniffer, ml-detector, firewall, etcd-server) corren en el **mismo host físico**. `ipc://` es zero-copy entre procesos, no requiere stack TCP, y no depende de la interfaz de red (que puede estar saturada por el ataque mismo).

**Cuándo cambiar a `tcp://`:** Solo si en el futuro desagregas el firewall a un host separado (ej. firewall en hardware dedicado, NDR en otro). Eso es post-FEDER.

**Documentación:** Añade un comentario en `autonomy_publisher.h`:
```cpp
// Transport: ipc:// for single-node edge deployments (FEDER).
// tcp:// with CURVE encryption required for multi-host topologies.
static constexpr const char* DEFAULT_ENDPOINT = "ipc:///run/argus/autonomy.sock";
```

---

## Q3 — `reconcile_interval_sec=90` y su propósito

**90s es arbitrario y debe ser configurable, pero el reconciliador no debe consultar a Vault.**

El reconciliador en `firewall-acl-agent` es un **safety net de coherencia**, no una fuente de verdad. Su trabajo es:

```cpp
// En el loop del subscriber
void AutonomySubscriber::reconcile() {
    if (last_event_time_ > now() - reconcile_interval_) {
        return;  // Evento ZMQ reciente, todo OK
    }
    
    // No hemos recibido evento en 90s. ¿El publisher murió o está healthy?
    // No consultamos a Vault. Re-aplicamos el último estado conocido.
    if (last_known_state_ == "AUTONOMOUS") {
        reactor_.apply_default_deny();  // re-aplicar por si iptables fue flushado
        log(LOG_WARNING, "Reconciler: re-applied autonomy deny (no ZMQ event in %ds)", interval_);
    }
}
```

**Configuración:** Ya está en `firewall.json["autonomy"]["reconcile_interval_sec"]`. Pasa el valor al constructor en `main.cpp` del firewall.

**Por qué no consultar Vault:** El firewall no tiene credenciales de Vault. Eso es responsabilidad del proceso propietario de la SM (etcd-server). Si el firewall consultara directamente a Vault, violarías la arquitectura de ADR-044 donde solo `VaultProvider` conoce los paths.

---

## Q4 — Estructura de carpetas enterprise

**`plugins/enterprise/` es la estructura correcta.**

Razones:
1. **El sistema ya tiene un plugin system** (ADR-025, ADR-032). Vault como "plugin de gobernanza criptográfica" es coherente.
2. **Separación limpia.** `common/` debe contener solo infraestructura universal (`ICryptoProvider`, `AutonomyPublisher`, `CryptoAutonomyStateMachine`). Código que requiere HashiCorp Vault va a `plugins/enterprise/vault/`.
3. **CMake escalable.** Puedes tener:
   ```cmake
   option(ARGUS_ENTERPRISE_PLUGINS "Enable enterprise governance plugins" OFF)
   if(ARGUS_ENTERPRISE_PLUGINS)
       add_subdirectory(plugins/enterprise)
   endif()
   ```
4. **Licenciamiento.** `plugins/enterprise/` puede tener un `LICENSE.enterprise` distinto al `LICENSE` de core, facilitando el modelo open-core.

**Estructura propuesta:**
```
plugins/
├── enterprise/
│   ├── vault/
│   │   ├── vault_client.{h,cpp}
│   │   ├── vault_provider.{h,cpp}
│   │   └── CMakeLists.txt
│   └── CMakeLists.txt
└── CMakeLists.txt  # raíz: opcional, default OFF
```

**Acción post-FEDER:** Mover `vault_client.*` y `VaultProvider.*` desde `common/` a `plugins/enterprise/vault/`. El refactor es mecánico porque la interfaz `ICryptoProvider` ya está en `common/`; solo la implementación concreta se mueve.

**No hagas esto ahora.** Es un refactor de directorios que puede romper includes y tests. Espera a que la SM esté integrada y los benchmarks pasen.

---

## Q5 — Benchmarks sintéticos en VirtualBox

**Hazlos para ti, no los publiques en el paper.**

VirtualBox introduce artefactos que invalidan cualquier conclusión sobre rendimiento real:
- Virtualización del scheduler: los vCPUs no son cores físicos.
- Overhead de virtio-net: no es AF_PACKET real ni XDP real.
- Memoria compartida con el host: no hay contención de bus real.
- `tcpreplay` desde otra VM: el timing de interrupciones es artificial.

**Uso correcto de los benchmarks sintéticos:**
- Detectar **regresiones** entre versiones (¿v0.8.0 es más lento que v0.7.0?).
- Calibrar **HWM de ZMQ** (¿a qué throughput empieza a dropear?).
- Validar que el **pipeline no se bloquea** bajo carga sostenida.

**Uso incorrecto:** Publicar "aRGus procesa 1.2 Gbps en un hospital" basado en VirtualBox. Eso es una mentira que un reviewer de redes destruiría en la primera pregunta.

**Para el paper:** Escribe en §10 Future Work:
> *"Capacity benchmarks (BM-A through BM-D) are planned on physical hardware as part of the FEDER validation (§X). Synthetic benchmarks in virtualized environments establish functional correctness under load but do not represent operational throughput."*

---

## Plan de acción DAY 156

| Orden | Tarea | Tiempo | Bloquea FEDER? |
|-------|-------|--------|----------------|
| 1 | **Integrar SM en `etcd-server`** (Q1) | 2h | **Sí** — sin esto no hay señal de autonomía |
| 2 | **Pasar `reconcile_interval_sec` al constructor** (Q3) | 0.5h | No |
| 3 | **`DEBT-AUTONOMY-STATE-PERSISTENCE-001`** | 1.5h | No |
| 4 | **`DEBT-BOOTSTRAP-STATUS-SIGNATURE-001`** | 1h | No |
| 5 | **Benchmark sintético interno** (Q5) | 2h | No — solo para regresión |

**Total: ~7h.** Prioriza la integración de la SM en etcd-server; es el único bloqueante funcional que queda en el camino de un sistema autónomo operativo.

---

## Nota final sobre la deuda de integración

`DEBT-AUTONOMY-CRYPTO-INTEGRATION-001` es la última pieza del rompecabezas. Una vez que `etcd-server` publique estados y `firewall-acl-agent` reaccione, tendrás un flujo end-to-end:

```
Vault caído → etcd-server detecta → SM entra AUTONOMOUS → ZMQ pub
→ firewall sub recibe → apply_default_deny() → hospital protegido
```

Ese flujo es la demo del 22 de septiembre. El evaluador FEDER debe verlo funcionar en una VM que simula un corte de red (ej. `iptables -A OUTPUT -d vault.central.argus.es -j DROP`).

*El Consejo ha hablado. Que la state machine viva en etcd-server, que el ipc sea local, y que el benchmark no se publique.* 🛡️