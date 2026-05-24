# Prompt de Continuidad — aRGus NDR — DAY 163
**Proyecto:** aRGus NDR (arXiv:2604.04952)  
**Rama activa:** `feature/day161-enterprise-crypto-integration`  
**Entorno:** macOS M2 Pro host · Vagrant/VirtualBox · Debian Bookworm  
**Metodología:** TDH (RED→GREEN obligatorio) · EMECAS · KISS · Via Appia Quality

---

## Estado al inicio de DAY 163

### Cerrado DAY 162
- **DEBT-EMECAS-SYNTHETIC-INJECTOR-001 CERRADA** — ZMQ slow joiner: PUB bind antes que SUB connect. `synthetic_ml_output_injector` slow joiner guard 500ms→3000ms. `test-e2e-synthetic-firewall`: PUB arranca 3s antes, log truncado, snapshot post-restart, `check-firewall-abs` (valor absoluto). `check_e2e_pipeline.py`: modo `precondition` (Consejo Opción 1+3). `test-e2e-synthetic` y `test-e2e-live` desacoplados. Mergeado main vía PR `feature/day161-emecas-e2e-fix`.
- **DEBT-EMECAS-DUAL-COMPILATION-001 CERRADA** — `make test-dual-compilation`: plugin-loader community OFF ✅ · enterprise ON ✅ · common/ community ✅ · common/ enterprise ✅.
- **PASO 1 — plugin-loader validate_or_abort()** — `extract_enabled_objects` → `tuple<4>` (name, so_path, is_enterprise, token_path). Antes de `dlopen`: si `is_enterprise==true` → `argus::enterprise::TokenValidator::validate_or_abort(eff_token_path, ARGUS_ENTERPRISE_PUBKEY_HEX, {"vault_crypto"})` bajo `#ifdef ARGUS_VAULT_ENABLED`. Community build: sin cambio de comportamiento.
- **PASO 2-3** — `CryptoProvider::create()` y etcd-server ya correctos desde DAY 151.
- **PASO 4 — test-e2e-vault** — Vault dev + common/ enterprise + 6/6 vault_provider tests + smoke etcd-server enterprise ✅.
- **PASO 5 — DEBT-EMECAS-DUAL-COMPILATION-001** — cerrada (ver arriba).
- **EMECAS++ verde:** `make test-all` ✅ · `make test-e2e-synthetic-full` ✅ · `make test-e2e-synthetic-firewall` ✅.
- **Consejo de Sabios DAY 162 (8/8):** roadmap ciclo de vida criptográfico enterprise definido en 8 fases. Veto unánime: no mergear a main ni habilitar rotación automática hasta Fases 0-4 verdes. ADR-045 "Crypto Epoch Coordination" requerido antes de Fase 2.

### Constantes permanentes
- **ARGUS_ENTERPRISE_PUBKEY_HEX:** `01cd1509d3cdb6012b5d0e08c2b1a5d4164649c8cacec0f9b1bbfefc7cce0326`
- **Token enterprise:** `/vagrant/enterprise/enterprise.token` (válido hasta 2027-05-24, features=[vault_crypto])
- **enterprise_vendor.key:** NUNCA al repo, NUNCA en VM permanente → debe ir a Vault (BACKLOG-CRYPTO-VENDOR-KEY-001 P0)
- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **EMECAS++:** añadir `&& make test-e2e-synthetic`
- **Edición ficheros:** siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- **Vagrant:** siempre `vagrant ssh -c '...'` desde host macOS

---

## Lo que existe en enterprise/ (confirmado DAY 162)
enterprise/scripts/generate_token.py     ✅ firma Ed25519, genera/verifica tokens
enterprise/token/TokenValidator.hpp      ✅ header-only, libsodium, namespace argus::enterprise
enterprise/enterprise_vendor.pub         ✅ tracked (pubkey pública, safe en repo)
enterprise/enterprise_vendor.key         ✅ gitignored — MOVER A VAULT (P0 DAY 163)
enterprise/enterprise.token              ✅ emitido 365 días, features=[vault_crypto]
enterprise/plugins/vault_crypto/
vault_provider.hpp                     ✅ ICryptoProvider implementado
vault_provider.cpp                     ✅ argus_enterprise_create/destroy C ABI
CMakeLists.txt                         ✅ compila libvault_provider.so
tests/test_vault_provider.cpp          ✅ 6/6 tests verdes
---

## Roadmap ciclo de vida criptográfico enterprise (Consejo 8/8 DAY 162)

| Fase | ID | Descripción | Prioridad | Target |
|------|----|-------------|-----------|--------|
| 0 | BACKLOG-CRYPTO-VENDOR-KEY-001 | vendor.key → Vault + eliminar pubkey de CMake | P0 | DAY 163 |
| 1 | BACKLOG-CRYPTO-HOT-RELOAD-001 | CryptoProvider::reload() RCU sin downtime | P0 | DAY 163-164 |
| 2 | BACKLOG-CRYPTO-EPOCH-001 | CryptoEpoch en etcd + ADR-045 aprobado | P1 | DAY 164-165 |
| 3 | BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 | Ventana dual-key ZMQ (grace period ADR-013) | P1 | DAY 165-166 |
| 4 | BACKLOG-CRYPTO-E2E-ROTATION-001 | test-e2e-rotation Vault HA (Raft 3 nodos) | P1 | DAY 166-167 |
| 5 | BACKLOG-CRYPTO-OPERABILITY-001 | Runbook manual + métricas + circuit breaker | P2 | DAY 167-168 |
| 6 | BACKLOG-CRYPTO-JENKINS-AUTOMATION-001 | Jenkins pipeline rotación (solo tras 0-5) | P2 | DAY 168+ |

**Riesgos críticos pendientes:**
- Split-brain criptográfico: si un componente rota y otro no → canal ZMQ muerto
- Bootstrap paradox: cómo se autentica Jenkins con Vault para el primer keypair
- Vault como SPOF sin caché local firmada
- Token hasta 2027 viola zero-trust (lease demasiado largo)
- Sin revocación inmediata sin recompilar

**Veto unánime Consejo:** NO se autoriza merge enterprise a main hasta Fases 0-4 verdes y con EMECAS.

---

## Objetivo DAY 163 — FASE 0: vendor.key → Vault

### PASO 0 — EMECAS limpio antes de tocar nada
```bash
cd /Users/aironman/CLionProjects/test-zeromq-docker
vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e-synthetic
```

### PASO 1 — Subir vendor.key a Vault
```bash
# Con Vault dev ya corriendo:
vagrant ssh -c "VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token \
  vault kv put secret/argus/enterprise/vendor-key \
  key=@/vagrant/enterprise/enterprise_vendor.key"
```

### PASO 2 — Modificar plugin-loader/CMakeLists.txt
Sustituir el valor hardcodeado de `ARGUS_ENTERPRISE_PUBKEY_HEX` por lectura en runtime desde Vault (o inyección desde Jenkins vía `-D`). El objetivo es que el CMakeLists NO tenga el hex hardcodeado en el repo.

### PASO 3 — test que valida que sin vendor.key en disco el sistema enterprise sigue operativo
Gate: enterprise build funciona con clave inyectada en runtime, no desde fichero en VM.

---

## Deudas técnicas abiertas relevantes

| ID | Prioridad | Estado |
|----|-----------|--------|
| BACKLOG-CRYPTO-VENDOR-KEY-001 | P0 | ⏳ DAY 163 |
| BACKLOG-CRYPTO-HOT-RELOAD-001 | P0 | ⏳ DAY 163-164 |
| BACKLOG-CRYPTO-EPOCH-001 | P1 | ⏳ DAY 164-165 (requiere ADR-045) |
| BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 | P1 | ⏳ DAY 165-166 |
| BACKLOG-CRYPTO-E2E-ROTATION-001 | P1 | ⏳ DAY 166-167 |
| DEBT-ALERTING-VAULT-001 | P2 | ⏳ post-Fase 0 |
| DEBT-CRYPTO-AUTONOMY-001 | P2 | ⏳ post-Fase 1 |
| DEBT-ARGUSPP-SURICATA-001 | P1 | ⏳ post-crypto lifecycle |
| DEBT-ARGUSPP-NTP-001 | P0 | ⏳ pre-correlación |

---

## Notas técnicas permanentes

### ZMQ slow joiner (DAY 156 + confirmado DAY 162)
Publisher SIEMPRE hace `bind()` antes de que cualquier subscriber haga `connect()`.
En tests E2E: PUB arranca con ≥3s de antelación antes del SUB.
Violación → mensajes perdidos silenciosamente → delta=0 en E2E → fallo críptico.

### Dual compilation (DAY 162)
```bash
make test-dual-compilation   # verifica community OFF y enterprise ON ambos verdes
```
Siempre ejecutar tras cambios en plugin-loader/ o common/ que toquen ARGUS_VAULT_ENABLED.

### Enterprise token validation
```cpp
// En plugin-loader, bajo #ifdef ARGUS_VAULT_ENABLED:
argus::enterprise::TokenValidator::validate_or_abort(
    token_path,
    ARGUS_ENTERPRISE_PUBKEY_HEX,   // hardcodeado en CMake (temporal — BACKLOG-CRYPTO-VENDOR-KEY-001)
    {"vault_crypto"}
);
```

### test-e2e-synthetic-firewall — secuencia correcta
injector (PUB bind :5572) → 3s → firewall start (SUB connect) →
truncate log → 35s → check-firewall-abs (eventos_procesados > 50)
