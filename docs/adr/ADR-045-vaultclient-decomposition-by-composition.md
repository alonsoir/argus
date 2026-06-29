# ADR-045 — VaultClient Decomposition by Composition

**Status:** APROBADO — DAY 151 · Consejo 8/8 + Founder  
**Fecha:** 2026-05-14  
**Autores:** Alonso Isidoro Román, Consejo de Sabios (8 modelos)  
**Relacionado:** ADR-044 (ICryptoProvider), ADR-013 (SeedClient), ADR-035 (etcd HA)

---

## Contexto

`VaultClient` (implementado en DAY 150) acumula seis responsabilidades distintas:

1. **HTTP a Vault API** — fetch de seeds, tokens, health check
2. **Derivación criptográfica** — HKDF + `crypto_sign_seed_keypair()`
3. **Cache tmpfs** — escritura, TTL, mlock, permisos 0600
4. **Registro en etcd** — bootstrap status, keepalive
5. **Jitter anti-stampede** — `component_index * 500ms + rand(0..1000ms)`
6. **Máquina de estados de autonomía** — `NORMAL → AUTONOMOUS → RECONCILING → DEGRADED` (DAY 152)

Una clase con seis responsabilidades es un monolito. No se puede testear `ICacheManager` sin levantar Vault. No se puede testear `IEtcdRegistrar` sin un etcd real. El jitter no se puede verificar sin tiempo real. Añadir la máquina de estados como séptima responsabilidad lo convierte en inmantenible.

La motivación de fondo es de soberanía tecnológica: si `VaultClient` es monolítico, cambiar de proveedor (HashiCorp Vault → AWS KMS → HSM local → implementación propia) requiere reescribir la clase entera. Con composición, cambias `IVaultTransport`.

---

## Decisión

**VaultClient se descompone por composición.** Cada responsabilidad se convierte en una interfaz C++20 pura, inyectable en el constructor de `VaultProvider`.

```
IVaultTransport       → fetch HTTP a Vault API
ICryptoDeriver        → KDF + crypto_sign_seed_keypair
ICacheManager         → tmpfs, TTL, mlock, permisos
IEtcdRegistrar        → registro + keepalive
IJitterStrategy       → anti-stampede
CryptoAutonomyStateMachine → estados operativos (ADR-044 DAY 152)
         ↓
VaultProvider (compone todo, implementa ICryptoProvider)
         ↓
ICryptoProvider::get_operational_mode()
         ↓
firewall / alerting / etcd-server / RAG
```

`VaultClient` puede mantenerse como implementación concreta de `IVaultTransport` (cliente HTTP a Vault), sin lógica de negocio.

---

## Interfaces propuestas

### IVaultTransport
```cpp
// common/vault_transport.h
namespace ml_defender {

struct VaultResponse {
    bool ok;
    std::vector<uint8_t> data;
    std::string error;
};

class IVaultTransport {
public:
    virtual ~IVaultTransport() = default;
    virtual VaultResponse fetch_seed(const std::string& path) = 0;
    virtual bool health_check() = 0;
};

} // namespace ml_defender
```

### ICacheManager
```cpp
// common/cache_manager.h
namespace ml_defender {

class ICacheManager {
public:
    virtual ~ICacheManager() = default;
    // Escribe datos en cache segura (tmpfs, mlock, 0600)
    virtual bool store(const std::string& key,
                       const std::vector<uint8_t>& data,
                       std::chrono::seconds ttl) = 0;
    // Lee cache. Retorna vacío si expirada o inexistente.
    virtual std::optional<std::vector<uint8_t>> load(const std::string& key) = 0;
    virtual void invalidate(const std::string& key) = 0;
    virtual bool is_valid(const std::string& key) const = 0;
};

} // namespace ml_defender
```

### IEtcdRegistrar
```cpp
// common/etcd_registrar.h
namespace ml_defender {

struct CryptoBootstrapStatus {
    std::string component;
    std::string fingerprint_hex;
    uint32_t key_version;
    std::string provider;   // "SeedFileProvider" | "VaultProvider"
    bool from_cache;
    std::string timestamp;
};

class IEtcdRegistrar {
public:
    virtual ~IEtcdRegistrar() = default;
    virtual bool register_bootstrap(const CryptoBootstrapStatus& status) = 0;
    virtual bool send_keepalive(const std::string& component) = 0;
    virtual void unregister(const std::string& component) = 0;
};

} // namespace ml_defender
```

### ICryptoDeriver
```cpp
// common/crypto_deriver.h
namespace ml_defender {

class ICryptoDeriver {
public:
    virtual ~ICryptoDeriver() = default;
    // Deriva keypair Ed25519 desde seed de 32 bytes.
    // Implementación de referencia: crypto_sign_seed_keypair() (libsodium)
    virtual CryptoMaterial derive(const std::array<uint8_t, 32>& seed,
                                  const std::string& component_name,
                                  uint32_t key_version) = 0;
};

} // namespace ml_defender
```

### IJitterStrategy
```cpp
// common/jitter_strategy.h
namespace ml_defender {

class IJitterStrategy {
public:
    virtual ~IJitterStrategy() = default;
    // Tiempo de espera antes del primer fetch a Vault.
    // Implementación de referencia: component_index * 500ms + rand(0..1000ms)
    virtual std::chrono::milliseconds startup_delay(uint32_t component_index) = 0;
    // Tiempo de espera entre reintentos.
    virtual std::chrono::milliseconds retry_delay(uint32_t attempt) = 0;
};

} // namespace ml_defender
```

---

## Implementaciones de producción

| Interfaz | Implementación de producción | Implementación de test |
|---|---|---|
| `IVaultTransport` | `HttpVaultTransport` (libcurl) | `MockVaultTransport` |
| `ICacheManager` | `TmpfsCacheManager` (tmpfs + mlock) | `InMemoryCacheManager` |
| `IEtcdRegistrar` | `EtcdClientRegistrar` | `NullEtcdRegistrar` |
| `ICryptoDeriver` | `LibsodiumCryptoDeriver` | `DeterministicDeriver` (seed fija) |
| `IJitterStrategy` | `ExponentialJitter` | `ZeroJitter` (sin espera) |

---

## VaultProvider refactorizado

```cpp
// common/vault_provider.h
#ifdef ARGUS_VAULT_ENABLED

class VaultProvider : public ICryptoProvider {
public:
    struct Config {
        std::string component_name;
        uint32_t component_index = 0;
    };

    // Constructor de producción (implementaciones reales inyectadas)
    VaultProvider(Config cfg,
                  std::shared_ptr<IVaultTransport>   transport,
                  std::shared_ptr<ICacheManager>      cache,
                  std::shared_ptr<IEtcdRegistrar>     registrar,
                  std::shared_ptr<ICryptoDeriver>     deriver,
                  std::shared_ptr<IJitterStrategy>    jitter,
                  std::shared_ptr<CryptoAutonomyStateMachine> state_machine);

    // ICryptoProvider
    CryptoMaterial get_material() override;
    bool refresh() override;
    bool is_healthy() const override;
    std::string component_name() const override;
    OperationalMode get_operational_mode() const noexcept override;

private:
    Config cfg_;
    std::shared_ptr<IVaultTransport>   transport_;
    std::shared_ptr<ICacheManager>      cache_;
    std::shared_ptr<IEtcdRegistrar>     registrar_;
    std::shared_ptr<ICryptoDeriver>     deriver_;
    std::shared_ptr<IJitterStrategy>    jitter_;
    std::shared_ptr<CryptoAutonomyStateMachine> state_machine_;
    std::optional<CryptoMaterial> cached_material_;
    mutable std::mutex mutex_;
};

#endif // ARGUS_VAULT_ENABLED
```

---

## Secuencia de implementación

### DAY 152 (P0)
- `common/crypto_autonomy.h/.cpp` — `CryptoAutonomyStateMachine`
- `ICryptoProvider::get_operational_mode()` con default `NORMAL`
- `SeedFileProvider` → siempre `NORMAL`

### DAY 153 (P0)
- `common/vault_transport.h` + `HttpVaultTransport` (extrae HTTP de `VaultClient`)
- `common/cache_manager.h` + `TmpfsCacheManager` (extrae cache tmpfs)
- Tests unitarios para cada uno con mocks

### DAY 154 (P1)
- `common/etcd_registrar.h` + `EtcdClientRegistrar`
- `common/crypto_deriver.h` + `LibsodiumCryptoDeriver`
- `common/jitter_strategy.h` + `ExponentialJitter`
- `VaultProvider` refactorizado usando todas las interfaces
- `DEBT-EMECAS-DUAL-COMPILATION-001` — Jenkinsfile dual

---

## Consecuencias

**Positivas:**
- Cada responsabilidad testeable en aislamiento sin Vault, sin red, sin etcd
- Cambio de proveedor criptográfico = cambiar `IVaultTransport` y/o `ICryptoDeriver`
- Futura implementación propia del servidor de secretos es un `IVaultTransport` diferente
- Tests más rápidos y deterministas (sin red, sin tmpfs, sin esperas de jitter)
- `VaultClient` puede mantenerse como implementación HTTP legítima

**Negativas:**
- Más ficheros headers (aceptable — cada uno < 50 líneas)
- Constructor de `VaultProvider` con 6 parámetros (mitigar con builder o factory)
- La factoría `CryptoProvider::create()` inyecta implementaciones de producción

**Neutrales:**
- El `#ifdef ARGUS_VAULT_ENABLED` permanece confinado en `crypto_provider.cpp` (regla DAY 151)
- `SeedFileProvider` no se ve afectado

---

## Reglas permanentes derivadas

- **REGLA ADR-045:** Ninguna nueva responsabilidad entra en `VaultProvider` sin una interfaz nueva. Si no tiene interfaz, no tiene tests. Si no tiene tests, no entra.
- **REGLA ADR-045:** La factoría `VaultProvider::make_production()` es el único lugar donde se instancian las implementaciones concretas de producción.
- **REGLA ADR-045:** Los tests de `VaultProvider` solo usan mocks — nunca Vault real, nunca tmpfs real, nunca etcd real.

---

## Referencias

- ADR-044: ICryptoProvider abstraction
- ADR-013: SeedClient y CryptoTransport
- DEBT-CRYPTO-AUTONOMY-001: máquina de estados
- DEBT-AUTONOMY-CLOCK-INJECTION-001: clock inyectable
- Principio SRP (Consejo 8/8, DAY 151)
- Soberanía tecnológica (Founder, DAY 151)