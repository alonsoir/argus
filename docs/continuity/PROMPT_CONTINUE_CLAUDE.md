# Prompt de Continuidad — aRGus NDR — DAY 164
**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Rama activa:** `feature/day161-enterprise-crypto-integration`
**Entorno:** macOS M2 Pro host · Vagrant/VirtualBox · Debian Bookworm
**Metodología:** TDH (RED→GREEN obligatorio) · EMECAS · KISS · Via Appia Quality

---

## Estado al inicio de DAY 164

### Cerrado DAY 163

**BACKLOG-CRYPTO-VENDOR-KEY-001 CERRADA (FASE 0)**
- Modelo B adoptado: keypair enterprise efímero por diseño
- `vault-enterprise-bootstrap` (run:always) en Vagrantfile: genera Ed25519 + token + sube a Vault + limpia `/tmp`
- vendor.key nunca persiste en disco ni en la VM — solo en Vault dev (inmem)
- `enterprise_vendor.pub` + `enterprise.token` gitignored
- `plugin-loader/CMakeLists.txt`: guard `FATAL_ERROR` si enterprise build sin `-DARGUS_ENTERPRISE_PUBKEY_HEX`
- `Makefile [2/4]` test-dual-compilation: lee hex de Vault en runtime antes de invocar cmake
- `test-dual-compilation` 4/4 verde

**BACKLOG-CRYPTO-HOT-RELOAD-001 CERRADA (FASE 1)**
- `common/crypto_provider_handle.hpp` — header-only RCU
- `std::atomic<shared_ptr<ICryptoProvider>>` — swap atómico lock-free C++20
- `get()` nunca null post-construcción. `reload()` swap atómico. Provider anterior vive hasta refcount=0
- 9/9 tests RED→GREEN (null guard, delegaciones, reload swap, 8 readers + 50 reloads concurrentes, RCU survival via weak_ptr)
- 12/12 suite common verde
- Commits: `e933e316` · `d39be6a1`

**ADR-045 v2 — Decisiones Consejo 8/8**
- P1: `not_before` como coordinador, sin 2PC. ACKs solo observabilidad post-hoc
- P2: grace period global 10s, no por componente
- P3: etcd-server escribe `/argus/crypto/epoch`. Lógica criptográfica en `CryptoEpochCoordinator` dentro de `vault_client`
- P4: estado `EPOCH_TRANSITION` + `EPOCH_FAILED`. `AUTONOMOUS_EPOCH_STALE` documentado para FASE 5
- P5: wire header `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4]`. Definido ahora, implementado FASE 3
- Nuevos del Consejo: `last_seen_revision` para reconnect seguro, `WATCH_CONNECTED/DEGRADED/STALE`, ACK timestamp monotónico en ns

**DEBT-ETCD-REGISTRAR-REAL-001 descubierta (bloqueante FASE 2)**
- `StubEtcdRegistrar` es stub puro (logs a stderr, sin etcd real)
- El watch de `/argus/crypto/epoch` no puede construirse sobre el stub
- P0 DAY 164, prerequisito de BACKLOG-CRYPTO-EPOCH-001

---

## Constantes permanentes

- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **EMECAS++:** añadir `&& make test-e2e-synthetic`
- **EMECAS se ejecuta justo antes de mergear a main** — no en cada sesión de desarrollo
- **Edición ficheros:** siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- **Vagrant:** siempre `vagrant ssh -c '...'` desde host macOS
- **ARGUS_ENTERPRISE_PUBKEY_HEX:** efímero por diseño (Modelo B) — se obtiene de Vault en cada vagrant up
- **Token enterprise:** `/vagrant/enterprise/enterprise.token` (regenerado cada vagrant up, features=[vault_crypto])
- **vendor.key:** solo en Vault dev `secret/argus/enterprise/vendor-key` (base64). Nunca en disco.

---

## Lo que existe en common/ (confirmado DAY 163)
common/crypto_provider_handle.hpp    ✅ RCU header-only, std::atomic<shared_ptr>, C++20
common/crypto_provider.h/.cpp        ✅ ICryptoProvider, CryptoProvider::create(), factoría
common/vault_provider.h/.cpp         ✅ VaultProvider, ICryptoProvider enterprise
common/seed_file_provider.h/.cpp     ✅ SeedFileProvider, ICryptoProvider community
common/etcd_registrar.h/.cpp         ✅ IEtcdRegistrar + StubEtcdRegistrar (STUB — P0 DAY 164)
common/tests/test_crypto_provider_handle.cpp ✅ 9/9 tests RCU
---

## Objetivo DAY 164 — FASE 2a: HttpEtcdRegistrar real

### Decisiones Consejo (8/8) para implementación

| Pregunta | Decisión | Ratio |
|----------|----------|-------|
| Cliente etcd | etcd-cpp-apiv3 (ya en provision.sh) | 8/8 |
| Mecanismo watch | gRPC watch nativo + fallback polling 2s si watch cae | 6/8 |
| Threading | Hilo dedicado encapsulado en CryptoEpochCoordinator | 5/8 |
| last_seen_revision | Obligatorio para reconnect seguro | ChatGPT |
| Watch states | WATCH_CONNECTED / WATCH_DEGRADED / WATCH_STALE | ChatGPT |
| ACK formato | `{epoch, component, ack_ts_monotonic_ns}` | ChatGPT |

### PASO 0 — Ver estado actual de etcd_registrar y etcd-cpp-apiv3

```bash
# Confirmar que etcd-cpp-apiv3 está disponible en la VM
vagrant ssh -c "pkg-config --modversion etcd-cpp-apiv3 2>/dev/null || \
  ls /usr/local/lib/libetcd* 2>/dev/null || echo 'verificar instalación'"

# Ver qué expone la API de etcd-cpp-apiv3 para watch
vagrant ssh -c "find /usr/local/include -name '*.hpp' | xargs grep -l 'Watch\|Watcher' 2>/dev/null | head -5"
```

### PASO 1 — TDH: tests RED primero (test_etcd_registrar_real.cpp)

Tests mínimos para `HttpEtcdRegistrar`:
- `test_register_status_writes_to_etcd` — PUT real en etcd
- `test_keepalive_lease_renews` — lease TTL mantiene la entrada viva
- `test_watch_receives_epoch_change` — callback al cambiar `/argus/crypto/epoch`
- `test_reconnect_resumes_from_last_revision` — no pierde eventos tras reconexión
- `test_watch_state_transitions` — CONNECTED → DEGRADED → STALE

### PASO 2 — Implementar HttpEtcdRegistrar
common/http_etcd_registrar.h/.cpp   — NUEVO
IEtcdRegistrar implementado con etcd-cpp-apiv3
watch() con gRPC stream + last_seen_revision
Hilo dedicado encapsulado (start/stop)
Fallback polling 2s si watch cae (watchdog 30s)
Estados WATCH_CONNECTED/DEGRADED/STALE
### PASO 3 — CryptoEpochCoordinator (depende de HttpEtcdRegistrar)
common/crypto_epoch_coordinator.h/.cpp   — NUEVO
watch /argus/crypto/epoch vía HttpEtcdRegistrar
on_epoch_change(): callback → caller hace handle.reload()
escribe ACK con timestamp monotónico
Hilo dedicado (start/stop/current_epoch())
### PASO 4 — Integrar en etcd-server/main.cpp

- etcd-server instancia `CryptoEpochCoordinator`
- Cuando `not_before` llega: `coordinator` notifica → `handle.reload(new_provider)`
- etcd-server escribe `/argus/crypto/epoch` cuando Vault notifica rotación

---

## Roadmap ciclo de vida criptográfico enterprise

| Fase | ID | Descripción | Prioridad | Estado |
|------|----|-------------|-----------|--------|
| 0 | BACKLOG-CRYPTO-VENDOR-KEY-001 | vendor.key → Vault + Modelo B | P0 | ✅ DAY 163 |
| 1 | BACKLOG-CRYPTO-HOT-RELOAD-001 | CryptoProviderHandle RCU | P0 | ✅ DAY 163 |
| 2a | DEBT-ETCD-REGISTRAR-REAL-001 | HttpEtcdRegistrar real (prerequisito) | P0 | ⏳ DAY 164 |
| 2b | BACKLOG-CRYPTO-EPOCH-001 | CryptoEpochCoordinator + ADR-045 v2 | P1 | ⏳ DAY 164 |
| 3 | BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 | Wire header epoch_id + ventana dual-key | P1 | ⏳ DAY 165 |
| 4 | BACKLOG-CRYPTO-E2E-ROTATION-001 | test-e2e-rotation Vault HA | P1 | ⏳ DAY 166 |
| 5 | BACKLOG-CRYPTO-OPERABILITY-001 | Runbook + métricas + circuit breaker | P2 | ⏳ DAY 167 |
| 6 | BACKLOG-CRYPTO-JENKINS-AUTOMATION-001 | Jenkins pipeline rotación | P2 | ⏳ DAY 168+ |

**Veto Consejo:** NO mergear enterprise a main hasta Fases 0-4 verdes con EMECAS.
**Pendiente pre-merge:** EMECAS completo + DEBT-ETCD-REGISTRAR-REAL-001 + BACKLOG-CRYPTO-EPOCH-001.

---

## Notas técnicas permanentes

### ZMQ slow joiner (DAY 156 + confirmado DAY 162)
Publisher SIEMPRE hace `bind()` antes de que cualquier subscriber haga `connect()`.
En tests E2E: PUB arranca con ≥3s de antelación antes del SUB.

### Dual compilation
```bash
make test-dual-compilation   # community OFF + enterprise ON ambos verdes
```
Siempre ejecutar tras cambios en plugin-loader/ o common/ que toquen ARGUS_VAULT_ENABLED.

### CryptoProviderHandle — uso correcto
```cpp
// Construcción
CryptoProviderHandle handle(CryptoProvider::create(cfg));

// Reader (thread-safe, nunca null)
auto p = handle.get();
auto mat = p->get_material();

// Rotación de época (FASE 2b)
handle.reload(CryptoProvider::create(new_cfg));
```

### test-e2e-synthetic-firewall — secuencia correcta
injector (PUB bind :5572) → 3s → firewall start (SUB connect) →
truncate log → 35s → check-firewall-abs (eventos_procesados > 50)
### HttpEtcdRegistrar — patrón de reconnect
```cpp
// Siempre guardar last_seen_revision para no perder eventos
etcd::Watcher watcher(client, key, callback, last_seen_revision);
// Tras reconexión: reanudar desde last_seen_revision, no desde 0
```
