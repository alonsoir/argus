Correcto — el orden lógico es: Consejo primero, feedback recogido, luego actualizamos documentación con criterio. Vamos.

---

## Publicación para el Consejo de Sabios — DAY 155

---

**aRGus NDR — DAY 155 — Informe al Consejo**
*17 Mayo 2026 · Tag: `v0.9.0-day155` · EMECAS HARDENED PASSED ✅*

---

### LO QUE SE HIZO HOY

**P0 — DEBT-FIREWALL-DENY-SELECTIVE-001 CERRADA (Consejo 8/8 unánime)**

La regla `-I INPUT 1 -j DROP` que rompía hospitales fue reemplazada por una cadena dedicada `argus-autonomy` con orden garantizado estructuralmente:

```
N argus-autonomy (cadena nueva)
A argus-autonomy -i lo             → ACCEPT  [argus-autonomy-lo]
A argus-autonomy ESTABLISHED,RELATED → ACCEPT  [argus-autonomy-established]
A argus-autonomy -s <cidr>         → ACCEPT  [argus-autonomy-permit] × N
A argus-autonomy                   → DROP    [argus-autonomy-deny]
I INPUT 1 -j argus-autonomy
```

Decisiones de diseño:
- `whitelist_cidrs` **obligatorio** desde `firewall.json["autonomy"]["whitelist_cidrs"]` — sin defaults hardcodeados, `std::invalid_argument` si vacío
- `AutonomyConfig` + `parse_autonomy()` en `ConfigLoader` con fail-fast explícito
- `lift`: orden D→F→X garantizado
- `firewall-acl-agent` integrado en `test-components` del Makefile
- **12/12 tests** (T1-T6 actualizados + T7-T12 nuevos)
- **49/49 firewall tests verdes**

**P1 — DEBT-AUTONOMY-ZMQ-EVENTS-001 CERRADA**

- `AutonomyPublisher` (`common/`) — ZMQ PUB, topic `argus.crypto.autonomy`, `make_callback()` integra con `CryptoAutonomyStateMachine::TransitionCallback`
- `AutonomySubscriber` (`firewall-acl-agent/`) — ZMQ SUB event-driven + polling reconciliador configurable (default 90s) como safety net
- Transport: `ipc:///run/argus/autonomy.sock` (procesos separados confirmado — `firewall-acl-agent` no linkea `common/`)
- `RECONCILING` mapea a `NORMAL` (Vault recuperado)
- `test_autonomy_publisher`: 4/4 PASSED
- `test_autonomy_subscriber`: 6/6 PASSED
- `DEBT-AUTONOMY-CRYPTO-INTEGRATION-001` registrada en `docs/debt/` — integración en `main.cpp` pendiente de decidir qué proceso instancia `CryptoAutonomyStateMachine`

**P2 — BACKLOG-ZMQ-TUNING-001 CERRADA**

Parámetros ZMQ aplicados en todos los sockets del proyecto:
- `zmq_subscriber` (pipeline principal): `rcvhwm` desde `firewall.json["zmq"]["high_water_mark"]`, `reconnect_ivl`/`reconnect_ivl_max` desde config
- `autonomy_subscriber`: `rcvhwm=1000`, `reconnect_ivl=100ms`, `max=5000ms`
- `autonomy_publisher`: `sndhwm=1000`, `reconnect_ivl=100ms`, `max=5000ms`
- `ml-detector` y `sniffer`: ya tenían HWM desde config — sin cambios

**EMECAS HARDENED PASSED** — `-Werror` + `-O3` + `-flto` + producción limpio. AppArmor 6/6. Falco 11 reglas. BSR verificado.

---

### DEUDA NUEVA REGISTRADA

**DEBT-AUTONOMY-CRYPTO-INTEGRATION-001** — `CryptoAutonomyStateMachine` definida en `common/` pero no instanciada en ningún componente de producción. `AutonomyPublisher` y `AutonomySubscriber` implementados y testeados pero sin integración en `main.cpp`. Transporte: `ipc:///run/argus/autonomy.sock`.

**Pregunta bloqueante:** ¿qué proceso debe instanciar `CryptoAutonomyStateMachine` + `AutonomyPublisher`?

---

### PREGUNTAS AL CONSEJO

**Q1 — Proceso propietario de `CryptoAutonomyStateMachine` (DEBT-AUTONOMY-CRYPTO-INTEGRATION-001)**

`CryptoAutonomyStateMachine` no está instanciada en ningún componente de producción. El publisher ZMQ emite en `ipc:///run/argus/autonomy.sock`. El subscriber en `firewall-acl-agent` ya está listo para recibir.

¿Qué proceso debe ser "Proceso A"?

- **Opción A:** El `etcd-server` — ya tiene lógica de health-check y conoce el estado de Vault
- **Opción B:** Un daemon crypto dedicado (nuevo componente `argus-crypto-daemon`) — separación de responsabilidades limpia pero añade un proceso más
- **Opción C:** El `sniffer` — es el componente más cercano al hardware y primero en arrancar
- **Opción D:** Cada componente que usa `ICryptoProvider` instancia su propia SM y publica en el mismo topic — múltiples publishers, un subscriber en el firewall

**Q2 — Endpoint del pub/sub en producción**

El endpoint actual es `ipc:///run/argus/autonomy.sock`. En la arquitectura edge/servidor:

- Edge node tiene `firewall-acl-agent` y el proceso crypto en el **mismo host** → `ipc://` correcto
- Servidor central con múltiples componentes → ¿sigue siendo `ipc://` o necesitamos `tcp://`?

¿El firewall siempre correrá en el mismo host que el proceso crypto, o puede haber topologías donde estén separados?

**Q3 — `reconcile_interval_sec=90` en `AutonomySubscriber`**

El polling reconciliador es safety net, no mecanismo principal. El valor 90s viene del prompt de continuidad DAY 155. En un hospital con modo autónomo activo:

- ¿90s es el intervalo correcto, o debería ser configurable desde `firewall.json["autonomy"]["reconcile_interval_sec"]`? (ya está en el JSON, solo falta pasarlo al constructor del subscriber en `main.cpp`)
- ¿El reconciliador debe consultarle a alguien (Vault, etcd) o simplemente re-aplicar el último estado conocido?

**Q4 — Deuda enterprise: `vault_client` y `VaultProvider` fuera de `common/`**

Hoy `common/` mezcla infraestructura core (`crypto_autonomy.h`, `autonomy_publisher.h`) con código enterprise (`vault_client`, `VaultProvider`). La propuesta es mover vault_client + VaultProvider a una carpeta `enterprise/` o `plugins/enterprise/` post-FEDER.

¿Cuál es la estructura de carpetas preferida? ¿`enterprise/`, `plugins/enterprise/`, o `common/enterprise/`? ¿Hay alguna implicación en el CMakeLists raíz que debamos anticipar ahora?

**Q5 — `BACKLOG-BENCHMARK-CAPACITY-001` desbloqueado**

Con `BACKLOG-ZMQ-TUNING-001` cerrado, el prerequisito de los benchmarks de capacidad está satisfecho. Los benchmarks reales (BM-A a BM-D) requieren hardware físico (FEDER). Sin embargo, podemos hacer benchmarks sintéticos en VirtualBox para establecer una línea base.

¿Recomendáis hacer benchmarks sintéticos en VirtualBox antes de tener hardware físico, sabiendo que los números serán el suelo (no el techo), o esperamos al hardware real para no publicar números preliminares que puedan ser malinterpretados?

---

### PARA MAÑANA — DAY 156 (propuesta)

| Prioridad | Tarea |
|---|---|
| P0 | Respuesta Consejo Q1 → integrar `CryptoAutonomyStateMachine` en el proceso correcto |
| P1 | `DEBT-AUTONOMY-STATE-PERSISTENCE-001` — estado firmado en `/run/argus/crypto-autonomy-state.json` |
| P1 | `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` — firma Ed25519 en bootstrap status |
| P2 | `DEBT-CRYPTO-AUTONOMY-001` — máquina de estados EXTENDED_AUTONOMY completa |

---

*"Que el pub/sub sea ipc, que el deny sea selectivo, y que el benchmark no mida mentiras."*
*— Kimi + Consejo DAY 154, ejecutado DAY 155*

---

Pega esto en el Consejo. Cuando tengas el feedback, me lo traes y genero el script Python para actualizar `BACKLOG.md` y `README.md` sin tocar nada a mano. Luego el prompt de continuidad y el LinkedIn.