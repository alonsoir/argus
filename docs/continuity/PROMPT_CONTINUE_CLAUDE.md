python3 << 'PYEOF'
prompt = """# Prompt de Continuidad — aRGus NDR — DAY 165
**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Rama activa:** `feature/day161-enterprise-crypto-integration`
**Entorno:** macOS M2 Pro host · Vagrant/VirtualBox · Debian Bookworm
**Metodología:** TDH (RED→GREEN obligatorio) · EMECAS · KISS · Via Appia Quality

---

## Estado al inicio de DAY 165

### Cerrado DAY 164 (5 commits)

| Commit | Qué |
|--------|-----|
| `426c0340` | fix: vault-enterprise-bootstrap token via @file (not shell expansion) |
| `b48c86ec` | feat: DEBT-ETCD-REGISTRAR-REAL-001 — HttpEtcdRegistrar REST 5/5 tests |
| `36d05cef` | feat: BACKLOG-CRYPTO-EPOCH-001 — CryptoEpochCoordinator + /v1/epoch 5/5 tests |
| `475589fb` | feat: PASO 4 — CryptoEpochCoordinator integrado en etcd-server |
| `db63c44f` | fix: httplib ODR + heartbeat timestamp + etcd-server arranca limpio |

**DEBT-ETCD-REGISTRAR-REAL-001 CERRADA (FASE 2a)**
- `common/http_etcd_registrar.h/.cpp`: IEtcdRegistrar real con httplib
  · register_status → POST /register
  · start_keepalive → hilo POST /v1/heartbeat/{component} con timestamp Unix
  · watch_epoch → polling GET /v1/epoch cada 2s, baseline silencioso en primer poll
  · last_seen_revision: no dispara callback en primer poll
  · WatchState: CONNECTED → DEGRADED tras N fallos consecutivos
- 5/5 tests RED→GREEN con FakeEtcdServer httplib inline
- fix: test_autonomy_publisher ZMQ PUB/SUB invertido (bug DAY 155)

**BACKLOG-CRYPTO-EPOCH-001 CERRADA (FASE 2b)**
- `common/crypto_epoch_coordinator.h/.cpp`: coordina rotación de época
  · watch /v1/epoch via HttpEtcdRegistrar
  · on_epoch_change callback → caller hace handle.reload()
  · ACK timestamp monotónico en ns
  · current_epoch() / current_not_before() / watch_state()
  · stop() idempotente
- 5/5 tests RED→GREEN
- etcd-server: GET/PUT /v1/epoch + EpochInfo thread-safe (mutex)

**PASO 4 completado — etcd-server integrado**
- `etcd-server/src/main.cpp`: HttpEtcdRegistrar + CryptoEpochCoordinator arrancados
- etcd-server arranca limpio: register OK, heartbeat 200, /v1/epoch responde
- `/components` → `["etcd-server"]` registrado
- fix: CPPHTTPLIB_OPENSSL_SUPPORT via CMake en todos los targets (evita ODR)
- fix: alert_client.hpp #ifndef guard

**Suite:** 12/12 common verde

---

## Constantes permanentes

- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **EMECAS++:** añadir `&& make test-e2e-synthetic`
- **EMECAS se ejecuta justo antes de mergear a main** — no en cada sesión
- **Edición ficheros:** siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- **Vagrant:** siempre `vagrant ssh -c '...'` desde host macOS
- **ARGUS_ENTERPRISE_PUBKEY_HEX:** efímero por diseño (Modelo B) — se obtiene de Vault en cada vagrant up
- **Token enterprise:** `/vagrant/enterprise/enterprise.token` (regenerado cada vagrant up)
- **vendor.key:** solo en Vault dev `secret/argus/enterprise/vendor-key`. Nunca en disco.
- **CPPHTTPLIB_OPENSSL_SUPPORT:** definido via CMake en crypto_provider y etcd-server — NUNCA inline en .cpp/.hpp

---

## Lo que existe en common/ (confirmado DAY 164)
common/crypto_provider_handle.hpp    ✅ RCU header-only, std::atomic<shared_ptr>, C++20
common/crypto_provider.h/.cpp        ✅ ICryptoProvider, CryptoProvider::create(), factoría
common/vault_provider.h/.cpp         ✅ VaultProvider, ICryptoProvider enterprise
common/seed_file_provider.h/.cpp     ✅ SeedFileProvider, ICryptoProvider community
common/etcd_registrar.h/.cpp         ✅ IEtcdRegistrar + StubEtcdRegistrar
common/http_etcd_registrar.h/.cpp    ✅ HttpEtcdRegistrar REST, 5/5 tests (DAY 164)
common/crypto_epoch_coordinator.h/.cpp ✅ CryptoEpochCoordinator, 5/5 tests (DAY 164)
common/tests/test_http_etcd_registrar.cpp     ✅ 5/5
common/tests/test_crypto_epoch_coordinator.cpp ✅ 5/5
common/tests/test_crypto_provider_handle.cpp  ✅ 9/9
---

## Objetivo DAY 165 — FASE 3: Wire header epoch_id

### Descripción (ADR-045 v2)
Wire header actual:   `[uint32_t size][LZ4 payload]`
Wire header nuevo:    `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4 payload]`

El epoch_id viaja en cada mensaje ZMQ para coordinar la ventana dual-key durante rotaciones.

### Ficheros a tocar
1. `crypto-transport/include/crypto_transport/transport.hpp` — añadir epoch_id al header
2. `crypto-transport/src/transport.cpp` — serializar/deserializar epoch_id
3. `crypto-transport/tests/` — actualizar tests existentes + nuevos para epoch_id
4. `ml-detector/` — serializador: escribe epoch_id en header
5. `firewall-acl-agent/src/api/zmq_subscriber.cpp` — deserializador: lee epoch_id
6. `test-e2e-synthetic` — validar pipeline completo post-cambio

### Antes de empezar FASE 3
```bash
# Ver wire protocol actual
vagrant ssh -c "cat /vagrant/crypto-transport/include/crypto_transport/transport.hpp"
vagrant ssh -c "grep -n 'header\\|size\\|uint32\\|LZ4' /vagrant/crypto-transport/src/transport.cpp | head -20"
```

---

## Roadmap ciclo de vida criptográfico enterprise

| Fase | ID | Descripción | Estado |
|------|----|-------------|--------|
| 0 | BACKLOG-CRYPTO-VENDOR-KEY-001 | vendor.key → Vault + Modelo B | ✅ DAY 163 |
| 1 | BACKLOG-CRYPTO-HOT-RELOAD-001 | CryptoProviderHandle RCU | ✅ DAY 163 |
| 2a | DEBT-ETCD-REGISTRAR-REAL-001 | HttpEtcdRegistrar real | ✅ DAY 164 |
| 2b | BACKLOG-CRYPTO-EPOCH-001 | CryptoEpochCoordinator + ADR-045 v2 | ✅ DAY 164 |
| 3 | BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 | Wire header epoch_id + ventana dual-key | ⏳ DAY 165 |
| 4 | BACKLOG-CRYPTO-E2E-ROTATION-001 | test-e2e-rotation Vault HA | ⏳ DAY 166 |
| 5 | BACKLOG-CRYPTO-OPERABILITY-001 | Runbook + métricas + circuit breaker | ⏳ DAY 167 |
| 6 | BACKLOG-CRYPTO-JENKINS-AUTOMATION-001 | Jenkins pipeline rotación | ⏳ DAY 168+ |

**Veto Consejo:** NO mergear enterprise a main hasta Fases 0-4 verdes con EMECAS.

---

## Notas técnicas permanentes

### ZMQ slow joiner (DAY 156 + confirmado DAY 162)
Publisher SIEMPRE hace `bind()` antes de que cualquier subscriber haga `connect()`.
En tests E2E: PUB arranca con ≥3s de antelación antes del SUB.

### CryptoProviderHandle — uso correcto
```cpp
CryptoProviderHandle handle(CryptoProvider::create(cfg));
auto p = handle.get();          // reader thread-safe, nunca null
auto mat = p->get_material();
handle.reload(CryptoProvider::create(new_cfg)); // rotación de época
```

### HttpEtcdRegistrar — uso correcto
```cpp
HttpEtcdRegistrar reg("http://127.0.0.1:2379", "component-name",
                      /*keepalive_ms=*/30000, /*poll_ms=*/2000);
reg.register_status(material, "component-name");
reg.start_keepalive();
// watch_epoch() establece baseline silencioso en primer poll
reg.watch_epoch([](uint16_t eid, const std::string& nb) {
    // handle.reload(CryptoProvider::create(new_cfg));
});
```

### CryptoEpochCoordinator — uso correcto
```cpp
CryptoEpochCoordinator coord(registrar, "component-name");
coord.start([&](uint16_t eid, const std::string& nb) {
    handle.reload(CryptoProvider::create(new_cfg));
});
// coord.stop() en destructor automáticamente
```

### CPPHTTPLIB_OPENSSL_SUPPORT — regla permanente (DAY 164)
Debe definirse via CMake (`target_compile_definitions`) en TODOS los targets
que incluyan httplib.h — nunca como `#define` inline en ficheros .cpp/.hpp.
Targets afectados: `crypto_provider`, `etcd-server`.

### Pendiente en docs/BACKLOG.md
BACKLOG-RESEARCH-KALMAN-001.md está en docs/experiments/ — añadir entrada en docs/BACKLOG.md.
