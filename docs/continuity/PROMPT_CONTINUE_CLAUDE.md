# aRGus NDR — PROMPT DE CONTINUIDAD DAY 155
*Fecha: 2026-05-17 | Branch: main @ v0.8.0-adr045*

---

## ESTADO ACTUAL

**Tag activo:** `v0.8.0-adr045`
**Paper:** arXiv:2604.04952 · Draft v18/v19 publicado
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa` (post-destroy DAY 133)

### EMECAS DAY 154 — VERDE ✅
- bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅

---

## COMPLETADO DAY 154

### ADR-045 — VaultClient decomposition completa
- `ICryptoDeriver` + `HkdfCryptoDeriver`: extrae `derive_material()`. 6 tests T1-T6.
- `IEtcdRegistrar` + `StubEtcdRegistrar`: extrae `register_etcd_status()` + keepalive. 4 tests.
- `VaultClient`: 4º ctor `(config, transport, cache, deriver, registrar=nullptr)`. 7 tests common/.
- Fix EMECAS: `crypto_deriver.h` + `etcd_registrar.h` al install target.
- Fix `-Werror` production: `test_auto_isolate` T6 sin variable no usada.

### DEBT-FIREWALL-AUTONOMY-MODE-001 — CERRADA
- `FirewallAutonomyReactor`: AUTONOMOUS/DEGRADED → `iptables -I INPUT 1 argus-autonomy-deny DROP`
- NORMAL → `iptables -D INPUT argus-autonomy-deny DROP`
- Executor inyectable (`IptablesExecutor`), dry_run, idempotencia. 6 tests. 48/48 firewall verdes.
- **ATENCIÓN:** La regla actual ES INCORRECTA para hospitales (ver DEBT-FIREWALL-DENY-SELECTIVE-001).

---

## PRIORIDADES DAY 155

### P0 — DEBT-FIREWALL-DENY-SELECTIVE-001 (Consejo 8/8 UNÁNIME)

La regla actual `-I INPUT 1 -j DROP` bloquea loopback, sesiones activas y subredes clínicas.
**Kimi:** *"Un vagrant up en un laptop no sufre. Un hospital sí."*

Regla correcta (orden crítico — el DROP debe ser ÚLTIMA):
```bash
iptables -I INPUT 1 -i lo -j ACCEPT --comment "argus-autonomy-lo"
iptables -I INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT --comment "argus-autonomy-established"
iptables -I INPUT 3 -s 10.0.0.0/8 -j ACCEPT --comment "argus-autonomy-rfc1918-a"
iptables -I INPUT 4 -s 172.16.0.0/12 -j ACCEPT --comment "argus-autonomy-rfc1918-b"
iptables -I INPUT 5 -s 192.168.0.0/16 -j ACCEPT --comment "argus-autonomy-rfc1918-c"
iptables -I INPUT 6 -j DROP --comment "argus-autonomy-deny"
```

Subnets whitelist → JSON configurable (no hardcodeadas).
Actualizar `apply_default_deny()` + `lift_default_deny()` + 6 tests existentes + nuevos tests selectivos.

### P1 — DEBT-AUTONOMY-ZMQ-EVENTS-001 (Consejo 7/8 + Founder)

**Consenso:** ZMQ pub/sub directo, sin polling como mecanismo principal.
- `TransitionCallback` ya definido en `common/crypto_autonomy.h` — solo instanciar.
- Topic: `argus.crypto.autonomy`
- Transport: `inproc://argus.autonomy` (mismo proceso) o `ipc:///run/argus/autonomy.sock`
- Payload mínimo: `{"state":"AUTONOMOUS","timestamp_utc_ns":...,"fingerprint":"..."}`
- Añadir polling reconciliador 60-120s como safety net (no como mecanismo principal).
- `FirewallAutonomyReactor` suscribe y llama `set_mode()`.

### P2 — BACKLOG-ZMQ-TUNING-001 (HWM primero)
- `ZMQ_SNDHWM` / `ZMQ_RCVHWM`: 1000-10000 mensajes (empezar conservador)
- `ZMQ_LINGER`: 0 (no bloquear en shutdown)
- `ZMQ_RECONNECT_IVL`: 100ms / `ZMQ_RECONNECT_IVL_MAX`: 5000ms
- Prerequisito de `BACKLOG-BENCHMARK-CAPACITY-001`

### P3 — DEBT-AUTONOMY-STATE-PERSISTENCE-001
- `/run/argus/crypto-autonomy-state.json` firmado Ed25519 al entrar en AUTONOMOUS.
- Verificar firma antes de reconciliar.

---

## DEUDAS ACTIVAS

| Deuda | Prioridad | DAY |
|---|---|---|
| DEBT-FIREWALL-DENY-SELECTIVE-001 | **P0 DAY 155** | Regla actual rompe hospitales |
| DEBT-AUTONOMY-ZMQ-EVENTS-001 | P1 DAY 155 | ZMQ pub/sub reactor |
| DEBT-AUTONOMY-STATE-PERSISTENCE-001 | P1 DAY 155 | Tmpfs firmado |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 | P1 pre-FEDER | Bootstrap sin firma |
| BACKLOG-ZMQ-TUNING-001 | P1 pre-FEDER | HWM primero |
| BACKLOG-BENCHMARK-CAPACITY-001 | P1 FEDER | 4 configs BM-A/B/C/D |
| DEBT-CAPTURE-BACKEND-ISP-001 | P2 post-benchmark | ISP CaptureBackend |

---

## REGLAS PERMANENTES

- **macOS:** nunca `sed -i` sin `-e ''` → usar Python3 inline o `vagrant ssh`
- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all` antes de merge
- **Push a main:** BLOQUEADO — siempre por PR
- **Qwen** se identifica como DeepSeek en respuestas — registrar siempre como Qwen
- **Makefile** es única fuente de verdad
- **`#ifdef ARGUS_VAULT_ENABLED`** solo en `crypto_provider.cpp`
- **`-Werror` + `PROFILE=production`** gate ODR obligatorio pre-merge

---

## ARQUITECTURA ACTUAL

```
common/
  vault_client.h/.cpp         ← VaultClient por composición (DAY 154)
  crypto_deriver.h/.cpp       ← ICryptoDeriver + HkdfCryptoDeriver (DAY 154) ✅
  etcd_registrar.h/.cpp       ← IEtcdRegistrar + StubEtcdRegistrar (DAY 154) ✅
  vault_transport.h/.cpp      ← IVaultTransport + HttpVaultTransport (DAY 153)
  cache_manager.h/.cpp        ← ICacheManager + FilesystemCacheManager (DAY 153)
  crypto_autonomy.h           ← CryptoAutonomyStateMachine (DAY 152)
  crypto_provider.h/.cpp      ← ICryptoProvider + SeedFileProvider (DAY 151)

firewall-acl-agent/
  include/firewall/
    autonomy_reactor.hpp      ← FirewallAutonomyReactor (DAY 154) ✅
  src/core/
    autonomy_reactor.cpp      ← apply/lift default-deny (NECESITA FIX P0) ⚠️
```

---

## SECUENCIA DAY 155

```bash
# 1. EMECAS
vagrant destroy -f && vagrant up && make bootstrap && make test-all

# 2. Nueva rama
git checkout -b feature/day155-autonomy-zmq-selective-deny

# 3. Fix P0: apply_default_deny() selectivo
# Editar: firewall-acl-agent/src/core/autonomy_reactor.cpp
# Actualizar: firewall-acl-agent/include/firewall/autonomy_reactor.hpp
# (añadir whitelist_cidrs configurable)
# Actualizar: 6 tests existentes + nuevos tests selectivos

# 4. ZMQ pub/sub
# Editar: common/crypto_autonomy.h (instanciar TransitionCallback)
# Editar: firewall-acl-agent/src/core/autonomy_reactor.cpp (suscribir)

# 5. EMECAS post-cambios
make test-all && make hardened-full

# 6. PR → main
```

---

*aRGus NDR — DAY 155 — Via Appia Quality*
*"Que el pub/sub sea inproc, que el deny sea selectivo, y que el benchmark no mida mentiras." — Kimi + Consejo DAY 154*