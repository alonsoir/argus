## Prompt de continuidad DAY 156

```markdown
# aRGus NDR — PROMPT DE CONTINUIDAD DAY 156
*Fecha: 2026-05-18 | Branch: main @ v0.9.0-day155*

---

## ESTADO ACTUAL

**Tag activo:** `v0.9.0-day155`
**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d827d1d6d4c938b720e34331f8a73f478ee85daa`

### EMECAS DAY 155 — VERDE ✅
- bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅
- 49/49 firewall tests | 4/4 test_autonomy_publisher | 6/6 test_autonomy_subscriber

---

## COMPLETADO DAY 155

### P0 — DEBT-FIREWALL-DENY-SELECTIVE-001 CERRADA (Consejo 8/8 unánime DAY 154)
- Cadena dedicada `argus-autonomy`: N → lo ACCEPT → ESTABLISHED ACCEPT → CIDRs ACCEPT → DROP → I INPUT 1
- `whitelist_cidrs` obligatorio desde `firewall.json["autonomy"]["whitelist_cidrs"]` — sin defaults
- `AutonomyConfig` + `parse_autonomy()` en `ConfigLoader` con fail-fast explícito
- Constructor lanza `std::invalid_argument` si whitelist vacía
- test_auto_isolate: T1-T6 actualizados + T7-T12 nuevos (12/12 PASSED)
- `test-components` integra firewall (49/49 verde)

### P1 — DEBT-AUTONOMY-ZMQ-EVENTS-001 CERRADA
- `AutonomyPublisher` (`common/`): ZMQ PUB, topic `argus.crypto.autonomy`
  `make_callback()` integra con `CryptoAutonomyStateMachine::TransitionCallback`
- `AutonomySubscriber` (`firewall-acl-agent/`): ZMQ SUB event-driven + polling reconciliador 90s
- Transport: `ipc:///run/argus/autonomy.sock` (procesos separados — firewall no linkea common/)
- RECONCILING → NORMAL. test_autonomy_publisher 4/4. test_autonomy_subscriber 6/6.
- `DEBT-AUTONOMY-CRYPTO-INTEGRATION-001` registrada en `docs/debt/`

### P2 — BACKLOG-ZMQ-TUNING-001 CERRADA
- `zmq_subscriber`: `rcvhwm` desde `firewall.json["zmq"]["high_water_mark"]` + `reconnect_ivl`
- `autonomy_subscriber`: `rcvhwm=1000`, `reconnect_ivl=100ms`, `max=5000ms`
- `autonomy_publisher`: `sndhwm=1000`, `reconnect_ivl=100ms`, `max=5000ms`
- ml-detector y sniffer ya tenían HWM desde config — sin cambios

### Archivo nuevo: `test_firewall_stubs.hpp`
- `StubExecutor` extraído como helper compartido entre tests del firewall

---

## DECISIONES DEL CONSEJO — DAY 155 (8/8)

### Q1 — Proceso propietario de CryptoAutonomyStateMachine (6/8)
**`etcd-server`** instancia `CryptoAutonomyStateMachine` + `AutonomyPublisher` para FEDER.
Ya es trust anchor operacional (STEP 0), ya conoce estado de Vault, ya tiene health-check loop.
Un solo publisher = coherencia garantizada, sin split-brain.
Migración post-FEDER a `argus-crypto-daemon` documentada (DeepSeek + Grok disidentes).

### Q2 — Endpoint pub/sub (8/8 unánime)
`ipc://` correcto y suficiente para edge nodes co-locados.
Endpoint configurable desde `firewall.json["autonomy"]["zmq_endpoint"]` (default: `ipc:///run/argus/autonomy.sock`).
El autonomy plane debe ser local, determinista, fail-contained.

### Q3 — Reconciliador (8/8 unánime)
`reconcile_interval_sec` configurable desde `firewall.json["autonomy"]["reconcile_interval_sec"]`.
Re-aplica último estado conocido — NO consulta Vault/etcd.
Desired state reconciliation, no distributed state recomputation.

### Q4 — Estructura enterprise (6/8)
`enterprise/` en raíz del proyecto, paralelo a `common/`.
`CMakeLists.txt` raíz: `add_subdirectory(enterprise)` condicional.
Documentar en `docs/OPEN_CORE.md`. Migración física post-FEDER.
Disidentes ChatGPT + Kimi: `plugins/enterprise/` (argumentan plugin system existente).

### Q5 — Benchmarks sintéticos VirtualBox (6/8)
Ejecutar con disclaimer: "VirtualBox Synthetic Baseline — lower bound only".
Valor: detección de regresiones, calibración HWM, validación metodológica.
NO publicar como throughput de producción.
Claude + Kimi disidentes (datos ya en paper DAY 145; usar solo internamente).

---

## PRIORIDADES DAY 156

### P0 — DEBT-AUTONOMY-CRYPTO-INTEGRATION-001

Integrar `CryptoAutonomyStateMachine` + `AutonomyPublisher` en `etcd-server/main.cpp`.

```cpp
// etcd-server/main.cpp — añadir
#include "autonomy_publisher.h"      // desde /usr/local/include/vault_client/
#include "crypto_autonomy.h"

// En main():
ml_defender::common::AutonomyPublisher pub(
    config.autonomy.zmq_endpoint,  // "ipc:///run/argus/autonomy.sock"
    "etcd-server",
    0  // linger_ms
);
ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

// Conectar al health-check loop existente:
// on_vault_unreachable() → sm.on_vault_unreachable()
// on_vault_restored()    → sm.on_vault_restored()
// on_revocation()        → sm.on_revocation()
```

También en `firewall-acl-agent/src/main.cpp`:
```cpp
// Añadir AutonomySubscriber con reconcile_interval desde config
auto autonomy_sub = std::make_unique<AutonomySubscriber>(
    reactor,
    poll_callback,   // consulta etcd para reconciliar
    config.autonomy.zmq_endpoint,
    config.autonomy.reconcile_interval_sec  // desde firewall.json
);
autonomy_sub->start();
```

Añadir a `firewall.json["autonomy"]`:
```json
"zmq_endpoint": "ipc:///run/argus/autonomy.sock"
```

Tests de cierre E2E:
- Vault KO simulado → etcd-server publica AUTONOMOUS → firewall aplica deny selectivo
- Vault recuperado → etcd-server publica RECONCILING → firewall levanta deny

### P1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001

Estado firmado Ed25519 en `/run/argus/crypto-autonomy-state.json` (tmpfs):
```json
{
  "state": "AUTONOMOUS",
  "timestamp_utc_ns": 1747442880000000000,
  "component": "etcd-server",
  "fingerprint": "b5b6cbdf...",
  "signature": "<ed25519-sig-base64>"
}
```
Verificar firma antes de reconciliar en el subscriber.

### P1 — DEBT-BOOTSTRAP-STATUS-SIGNATURE-001

Firmar `/run/argus/etcd-bootstrap-status.json` con `crypto_material.sk` en STEP 0.
Verificar firma antes de consumir en cualquier componente.

### P2 — DEBT-CRYPTO-AUTONOMY-001

Máquina de estados EXTENDED_AUTONOMY completa en `etcd-server`:
- `on_vault_unreachable()` → AUTONOMOUS
- `on_vault_restored()` → RECONCILING
- `on_reconciliation_ok()` → NORMAL
- `on_revocation()` → DEGRADED (terminal)
- Circuit breaker configurable (default 30 días)

---

## DEUDAS ACTIVAS

| Deuda | Prioridad | DAY |
|---|---|---|
| DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 | **P0 DAY 156** | Integrar SM en etcd-server + firewall main.cpp |
| DEBT-AUTONOMY-STATE-PERSISTENCE-001 | P1 DAY 156 | Estado firmado en tmpfs |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 | P1 pre-FEDER | Bootstrap sin firma |
| DEBT-CRYPTO-AUTONOMY-001 | P2 DAY 156 | SM EXTENDED_AUTONOMY completa |
| DEBT-CRYPTO-RECONCILIATION-001 | P1 pre-FEDER | Handshake validación post-Vault |
| DEBT-ALERTING-EDGE-SOS-001 | P1 pre-FEDER | SOS webhook edge |
| BACKLOG-BENCHMARK-CAPACITY-001 | P1 FEDER | 4 configs BM-A/B/C/D |
| DEBT-CAPTURE-BACKEND-ISP-001 | P2 post-benchmark | ISP CaptureBackend |
| DEBT-ENTERPRISE-LAYOUT-001 | P3 post-FEDER | Mover vault_client a enterprise/ |

---

## ARQUITECTURA ACTUAL

```
common/
  autonomy_publisher.h/.cpp      ← AutonomyPublisher ZMQ PUB (DAY 155) ✅
  crypto_autonomy.h              ← CryptoAutonomyStateMachine (DAY 152)
  vault_client.h/.cpp            ← VaultClient por composición (DAY 154)
  crypto_deriver.h/.cpp          ← ICryptoDeriver + HkdfCryptoDeriver (DAY 154)
  etcd_registrar.h/.cpp          ← IEtcdRegistrar + StubEtcdRegistrar (DAY 154)
  vault_transport.h/.cpp         ← IVaultTransport + HttpVaultTransport (DAY 153)
  cache_manager.h/.cpp           ← ICacheManager + FilesystemCacheManager (DAY 153)
  crypto_provider.h/.cpp         ← ICryptoProvider + SeedFileProvider (DAY 151)

firewall-acl-agent/
  include/firewall/
    autonomy_reactor.hpp         ← FirewallAutonomyReactor cadena selectiva (DAY 155) ✅
    autonomy_subscriber.hpp      ← AutonomySubscriber ZMQ SUB (DAY 155) ✅
    config_loader.hpp            ← AutonomyConfig + parse_autonomy() (DAY 155) ✅
  src/core/
    autonomy_reactor.cpp         ← apply/lift cadena argus-autonomy (DAY 155) ✅
    autonomy_subscriber.cpp      ← SUB event-driven + reconciliador (DAY 155) ✅
  config/firewall.json           ← sección "autonomy" con whitelist_cidrs (DAY 155) ✅

etcd-server/                     ← PENDIENTE: instanciar SM + Publisher (DAY 156)
```

---

## SECUENCIA DAY 156

```bash
# 1. EMECAS apertura
vagrant destroy -f && vagrant up && make bootstrap && make test-all

# 2. Nueva rama
git checkout -b feature/day156-autonomy-integration

# 3. P0: Integrar SM en etcd-server + subscriber en firewall main.cpp
# Editar: etcd-server/src/main.cpp
# Editar: firewall-acl-agent/src/main.cpp
# Editar: firewall-acl-agent/config/firewall.json (zmq_endpoint)

# 4. P1: Estado persistido firmado
# Nuevo: common/autonomy_state_writer.h/.cpp

# 5. EMECAS post-cambios
make test-all && make hardened-full

# 6. PR → main
```

---

## REGLAS PERMANENTES

- **macOS:** nunca `sed -i` sin `-e ''` → usar Python3 inline o `vagrant ssh`
- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all` antes de merge
- **Push a main:** BLOQUEADO — siempre por PR
- **Qwen** se identifica como DeepSeek en respuestas — registrar siempre como Qwen
- **Makefile** es única fuente de verdad
- **`#ifdef ARGUS_VAULT_ENABLED`** solo en `crypto_provider.cpp`
- **`-Werror` + `PROFILE=production`** gate ODR obligatorio pre-merge
- **Canal autonomía:** `ipc://` por defecto, configurable, nunca `tcp://` sin revisión seguridad
- **Reconciliador:** re-aplica último estado conocido, NUNCA consulta Vault/etcd
- **Un solo publisher** de `CryptoAutonomyStateMachine` por nodo — sin split-brain
- **enterprise/** en raíz para código que requiere Vault — post-FEDER

---

*aRGus NDR — DAY 156 — Via Appia Quality*
*"La autonomía no se delega; se coordina. El IPC no es un detalle: es un pacto de localidad." — Qwen · DAY 155*
```

