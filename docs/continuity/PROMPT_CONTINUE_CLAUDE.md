# Prompt de Continuidad — aRGus NDR — DAY 161

**Proyecto:** aRGus NDR (arXiv:2604.04952)  
**Rama activa:** `feature/day161-enterprise-crypto-integration`  
**Entorno:** macOS M2 Pro host · Vagrant/VirtualBox · Debian Bookworm  
**Metodología:** TDH (RED→GREEN obligatorio) · EMECAS · KISS · Via Appia Quality

---

## Estado al inicio de DAY 161

### Cerrado recientemente
- **DAY 159:** DEBT-FIREWALL-CRYPTO-FORMAT-001 cerrada. `zmq_subscriber.cpp` migrado a CryptoTransport + `seed.bin`. Drop rate 100% resuelto. EMECAS++ gate E2E real verde (`make test-e2e`).
- **DAY 160:** `libvault_provider.so` compilado limpio, 6/6 tests RED→GREEN. Jenkins 2.555.2 + Vault dev mode arrancando en Vagrant. `generate_token.py` + `TokenValidator.hpp` + `enterprise.token` generados.

### Lo que existe en enterprise/ (confirmado)
```
enterprise/scripts/generate_token.py   ✅ firma Ed25519, genera/verifica tokens
enterprise/token/TokenValidator.hpp    ✅ header-only, libsodium, validate_or_abort()
enterprise_vendor.pub                  ✅ tracked
enterprise_vendor.key                  ✅ gitignored (nunca al repo)
enterprise.token                       ✅ emitido 365 días, features=[vault_crypto]
enterprise/plugins/vault_crypto/
  vault_provider.hpp                   ✅ ICryptoProvider implementado
  vault_provider.cpp                   ✅ argus_enterprise_create/destroy C ABI
  CMakeLists.txt                       ✅ compila libvault_provider.so
  tests/test_vault_provider.cpp        ✅ 6 tests verdes
```

### Pendiente DAY 161 (objetivo del día)
```
❌  plugin-loader: validate_or_abort() antes de dlopen enterprise
❌  common/: CryptoProvider::create() — factoría ARGUS_VAULT_ENABLED
❌  etcd-server: integrar ICryptoProvider vía factoría (no seed-client directo)
❌  test-e2e-vault: gate E2E completo con Vault como backend
❌  DEBT-EMECAS-DUAL-COMPILATION-001: EMECAS con ON y OFF ambos verdes
```

---

## Roadmap acordado (DAY 161-166+)

| DAY | Objetivo |
|-----|----------|
| **161** | Plugin enterprise cifrado completo — enganche plugin-loader + factoría + E2E vault |
| **162** | Alerting: DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 (AlertClient → libcrypto_provider.so) + DEBT-ALERTING-VAULT-001 (credenciales Discord/Telegram a Vault) |
| **163** | Jenkins + Vault production-ready: AppRole por componente, políticas mínimas, Jenkinsfile enterprise stage |
| **164** | Script JSON contracts desde plantillas + paquetes Debian (community y enterprise) |
| **165** | Artifactory: enterprise .deb publicado desde Jenkins post-EMECAS |
| **166+** | Integración Suricata / Zeek / Wazuh (ADR-046 v3, community_id) |

---

## Secuencia de implementación DAY 161

### PASO 0 — EMECAS limpio antes de tocar nada
```bash
cd /Users/aironman/CLionProjects/test-zeromq-docker
vagrant destroy -f && vagrant up && make bootstrap && make test-all
```

### PASO 1 — Enganche plugin-loader (RED→GREEN)
En `plugin-loader/src/plugin_loader.cpp`, antes del `dlopen` de cualquier plugin enterprise:
```cpp
#include "enterprise/token/TokenValidator.hpp"
// ...
TokenValidator::validate_or_abort(
    config.enterprise_token_path,
    ARGUS_ENTERPRISE_PUBKEY_HEX,   // hardcodeado en CMakeLists.txt
    "vault_crypto"
);
```
Comportamiento fail-closed:
- Token ausente → abort con mensaje claro
- Firma inválida → abort
- Token expirado → abort con fecha
- Feature `vault_crypto` no incluida → abort

### PASO 2 — Factoría CryptoProvider::create() en common/
```cpp
// common/include/argus/crypto_provider_factory.hpp
namespace argus {
  std::unique_ptr<ICryptoProvider> create_crypto_provider(const Config& cfg);
}

// Lógica (solo en common/src/crypto_provider_factory.cpp):
// #ifdef ARGUS_VAULT_ENABLED → VaultProvider
// else                       → SeedFileProvider
// Ningún componente ve el #ifdef
```

### PASO 3 — etcd-server integra la factoría
Sustituir instanciación directa de SeedFileProvider por `create_crypto_provider(config)`.

### PASO 4 — test-e2e-vault
Variante de `make test-e2e` que:
1. Arranca Vault dev con `secret/argus/crypto` cargado
2. Compila con `ARGUS_VAULT_ENABLED=ON`
3. Ejecuta el synthetic injector
4. Verifica 0 drops + mensajes descifrados correctamente

### PASO 5 — DEBT-EMECAS-DUAL-COMPILATION-001
```bash
make ARGUS_VAULT_ENABLED=OFF test-all   # community — debe pasar
make ARGUS_VAULT_ENABLED=ON  test-all   # enterprise — debe pasar
```

---

## Decisiones arquitecturales cerradas (NO reabrir)

- **Modelo centralizado:** solo `etcd-server` habla con Vault. Distribuye semilla a componentes por canal existente. Consenso 8/8 Consejo DAY 151.
- **Factoría única:** `CryptoProvider::create()` es el único punto de decisión. Ningún componente ve `#ifdef` en lógica de negocio.
- **Migración por canal** (cuando llegue): etcd-server primero → sniffer+ml-detector simultáneo (canal A) → firewall-acl-agent (canal B) → rag-ingester+rag-security (canal C).
- **Keypair vendor distinto del keypair nodo:** generado una vez, offline, nunca en disco del nodo en producción.
- **Fail-closed absoluto:** si token inválido → abort. No hay degradación silenciosa.

---

## Constantes permanentes

- EMECAS: `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- Edición de ficheros: siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- Vagrant: siempre `vagrant ssh -c '...'` desde host macOS
- `alert_client.hpp`: NO incluir en ningún componente que linke `libetcd_client.so` hasta DAY 162
- Keypair activo (se regenera en cada destroy+up): `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`

---

## Deudas técnicas abiertas relevantes

| ID | Prioridad | DAY objetivo |
|----|-----------|--------------|
| DEBT-EMECAS-DUAL-COMPILATION-001 | P0 | 161 |
| DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 | P1 | 162 |
| DEBT-ALERTING-VAULT-001 | P2 | 162 |
| DEBT-CRYPTO-AUTONOMY-001 | P2 | post-166 |
| DEBT-ENTERPRISE-PLUGIN-001 | P0 | 161 (cierre) |

---

*Generado al cierre de DAY 160 · aRGus NDR · arXiv:2604.04952*