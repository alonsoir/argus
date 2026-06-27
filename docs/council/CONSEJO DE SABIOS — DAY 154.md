# CONSEJO DE SABIOS — DAY 154
**Fecha:** 2026-05-16
**Rama fusionada:** `feature/adr045-vaultclient-decomposition-day154` → `main` @ `v0.8.0-adr045`
**EMECAS:** ✅ bootstrap + test-all + hardened-full + check-prod-all

---

## 1. Qué hicimos AYER (DAY 153)

- Completamos `IVaultTransport` e `ICacheManager` (ADR-044 DAY 153).
- `VaultClient` pasó a composición parcial: dos interfaces inyectables.
- 13 tests verdes en `common/`.
- EMECAS verde. Merge `feature/adr044-vault-client-day153` → `main` @ `v0.7.1-adr044`.

---

## 2. Qué hicimos HOY (DAY 154)

### ADR-045 — Descomposición completa de VaultClient

**`ICryptoDeriver` + `HkdfCryptoDeriver`**
- Extrae `derive_material()` de VaultClient.
- Contratos: determinismo, aislamiento por `family` y `component_index`, seed inválido → `nullopt`, fingerprint = sha256(pk).
- 6 tests verdes (T1–T6).

**`IEtcdRegistrar` + `StubEtcdRegistrar`**
- Extrae `register_etcd_status()`, `start_etcd_keepalive()`, `stop_etcd_keepalive()`.
- Stub loguea a stderr; implementación real pendiente (`DEBT-AUTONOMY-ZMQ-EVENTS-001`).
- 4 tests verdes.

**VaultClient por composición completa**
- Cuarto constructor: `VaultClient(config, transport, cache, deriver, registrar=nullptr)`.
- Todos los ctors anteriores delegan al canónico.
- 7 tests verdes en `common/`.

### DEBT-FIREWALL-AUTONOMY-MODE-001 — FirewallAutonomyReactor

- `FirewallAutonomyMode`: `NORMAL | AUTONOMOUS | DEGRADED`.
- `apply_default_deny()`: `iptables -I INPUT 1 --comment argus-autonomy-deny -j DROP`.
- `lift_default_deny()`: `iptables -D INPUT --comment argus-autonomy-deny -j DROP`.
- Idempotencia: AUTONOMOUS → DEGRADED no duplica la regla.
- `dry_run`: no llama al executor pero marca `deny_active_`.
- Executor inyectable (`IptablesExecutor`) → testable sin root.
- 6 tests verdes. 48/48 firewall tests verdes.

### Fixes EMECAS
- `common/CMakeLists.txt`: `crypto_deriver.h` y `etcd_registrar.h` faltaban en el bloque `install(FILES ...)` → `etcd-server` fallaba al incluir `vault_client.h`.
- `test_auto_isolate.cpp` T6: variable `cmds_after_autonomous` no usada en production build (`-Werror=unused-variable` con `-DNDEBUG`). Reescrito usando `is_deny_active()`.

### EMECAS resultado
| Fase | Resultado |
|---|---|
| `vagrant destroy -f && vagrant up` | ✅ |
| `make bootstrap` | ✅ 6/6 RUNNING |
| `make test-all` | ✅ ALL TESTS COMPLETE |
| `make hardened-full` | ✅ EMECAS HARDENED PASSED |
| `make check-prod-all` | ✅ AppArmor 6/6, BSR, caps, Falco |

---

## 3. Qué haremos MAÑANA (DAY 155)

Prioridad P1 — deudas activas:

1. **`DEBT-AUTONOMY-ZMQ-EVENTS-001`** — Conectar `FirewallAutonomyReactor` a eventos ZMQ reales desde `CryptoAutonomyStateMachine`. Hoy el reactor existe pero nadie lo llama. Mañana lo integramos en el main loop del firewall.

2. **`DEBT-AUTONOMY-STATE-PERSISTENCE-001`** — Persistencia del modo autónomo en tmpfs para sobrevivir reinicios del proceso firewall sin perder el estado.

3. **`BACKLOG-ZMQ-TUNING-001`** — Optimizar parámetros ZeroMQ actualmente arbitrarios antes de lanzar benchmarks de capacidad. Prerequisito bloqueante para `BACKLOG-BENCHMARK-CAPACITY-001`.

---

## 4. Preguntas al Consejo

### P1 — Señal de autonomía: polling vs. eventos ZMQ

El `FirewallAutonomyReactor` existe pero hoy no recibe señales. Hay dos opciones para integrarlo:

**Opción A — Polling etcd** (en el health-check loop cada 30s): el firewall consulta periódicamente si el crypto-provider está en AUTONOMOUS. Simple, sin nuevo canal ZMQ.

**Opción B — Evento ZMQ** desde `CryptoAutonomyStateMachine` (pub/sub interno): el firewall suscribe a un topic `argus.crypto.autonomy` y reacciona en tiempo real. Más complejo, más robusto.

**¿Cuál recomendáis para DAY 155? ¿Polling primero como trampolín, o directo a ZMQ?**

### P2 — Granularidad del default-deny

La regla actual es `iptables -I INPUT 1 ... -j DROP` — bloquea TODO el tráfico nuevo entrante en AUTONOMOUS.

¿Es correcto este comportamiento para hospitales en autonomía extendida (Vault caído, operando con cache)?

**¿Debería el default-deny ser más selectivo (solo tráfico externo, preservar loopback y subredes internas) o el fail-closed total es la postura correcta para infraestructura crítica?**

### P3 — `BACKLOG-ZMQ-TUNING-001` antes de benchmarks

Los parámetros ZMQ actuales son arbitrarios (HWM, linger, reconnect interval). El paper arXiv:2604.04952 menciona esta limitación explícitamente.

**¿Qué parámetros ZMQ son críticos para medir antes de `BACKLOG-BENCHMARK-CAPACITY-001`? ¿HWM primero, o send/recv timeout?**

### P4 — `DEBT-CAPTURE-BACKEND-ISP-001` (Interface Segregation)

`CaptureBackend` tiene métodos eBPF-específicos (`get_xdp_stats()`) visibles en el interfaz aunque Variant B (libpcap) nunca los use. El Consejo DAY 145 acordó moverlos a `EbpfBackend`.

**¿Es DAY 155 el momento de cerrar esta deuda, o primero consolidamos la integración ZMQ del reactor?**

---

## 5. Estado de deudas activas

| Deuda | Estado | Prioridad |
|---|---|---|
| DEBT-AUTONOMY-ZMQ-EVENTS-001 | ⏳ P1 | Conectar reactor a ZMQ |
| DEBT-AUTONOMY-STATE-PERSISTENCE-001 | ⏳ P1 | Persistencia modo autónomo |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 | ⏳ P1 | Firma de status bootstrap |
| DEBT-CAPTURE-BACKEND-ISP-001 | ⏳ P2 | ISP en CaptureBackend |
| BACKLOG-ZMQ-TUNING-001 | ⏳ P1 | Prerequisito benchmarks |
| BACKLOG-BENCHMARK-CAPACITY-001 | ⏳ P1 | 4 configuraciones BM-A/B/C/D |

---

*aRGus NDR — DAY 154 — Via Appia Quality*
