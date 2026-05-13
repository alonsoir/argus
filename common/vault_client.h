#pragma once
// ============================================================================
// vault_client.h — ADR-044 Vault Crypto Client
// ============================================================================
// Lee seeds criptográficos desde HashiCorp Vault y los deriva en keypairs
// Ed25519 usando HKDF (libsodium). Cache en tmpfs con TTL configurable.
// Registro de estado en etcd con lease TTL=10s, keepalive cada 5s.
//
// Derivación correcta (Consejo DAY 149, Kimi D12):
//   kdf_derive(master_seed, component_index, "family_X_seed") → component_seed
//   sign_seed_keypair(component_seed) → (pk, sk)
//
// Fingerprint (Kimi D13): sha256(pk), NO de seed
//
// Jitter anti-stampede (DEBT-CRYPTO-STAMPEDE-001):
//   delay = component_index * 500ms + rand(0..1000ms)
//
// Cache tmpfs (DEBT-CRYPTO-HEARTBEAT-001):
//   TTL dev=1h, prod=72h — permisos 0700, mlock() opcional
//
// Lease etcd (DEBT-CRYPTO-HEARTBEAT-001):
//   TTL=10s, keepalive cada 5s
//
// Autonomía edge: si Vault KO + cache válida → arranca + log WARN
//                 si Vault KO + cache vacía  → exit(1) + log ERROR
//
// Referencia: ADR-044, ADR-025, ADR-013
// ============================================================================
#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <chrono>

namespace ml_defender {

// ── Constantes ───────────────────────────────────────────────────────────────

constexpr uint32_t VAULT_TIMEOUT_DEV_MS  = 5000;   // 5s LAN/dev
constexpr uint32_t VAULT_TIMEOUT_PROD_MS = 15000;  // 15s WAN/prod
constexpr uint32_t VAULT_JITTER_BASE_MS  = 500;    // por component_index
constexpr uint32_t VAULT_JITTER_RAND_MS  = 1000;   // random 0..1000ms
constexpr uint32_t ETCD_LEASE_TTL_S      = 10;     // lease TTL
constexpr uint32_t ETCD_KEEPALIVE_S      = 5;      // keepalive interval
constexpr uint32_t CACHE_TTL_DEV_S       = 3600;   // 1h dev
constexpr uint32_t CACHE_TTL_PROD_S      = 259200; // 72h prod

// ── Tipos ─────────────────────────────────────────────────────────────────────

using Ed25519PublicKey  = std::array<uint8_t, 32>;
using Ed25519SecretKey  = std::array<uint8_t, 64>;
using Sha256Fingerprint = std::array<uint8_t, 32>;

struct CryptoMaterial {
    Ed25519PublicKey  pk;
    Ed25519SecretKey  sk;
    Sha256Fingerprint fingerprint;  // sha256(pk) — Kimi D13
    std::string       family;
    uint32_t          key_version{0};
    std::string       derivation_timestamp;
    bool              from_cache{false};
};

// ── Configuración ─────────────────────────────────────────────────────────────

struct VaultClientConfig {
    std::string vault_addr        {"http://127.0.0.1:8200"};
    std::string vault_token       {"root"};
    std::string env               {"dev"};       // dev | prod
    std::string component_name;                  // etcd-server, sniffer, ...
    uint32_t    component_index   {0};           // para jitter
    std::string family            {"A"};         // A | B | C | etcd
    std::string cache_dir         {"/run/argus/crypto-cache"};
    uint32_t    timeout_ms        {VAULT_TIMEOUT_DEV_MS};
    uint32_t    cache_ttl_s       {CACHE_TTL_DEV_S};
    bool        mlock_enabled     {false};       // WARNING si falla, no exit(1)
};

// ── Resultado de operación ────────────────────────────────────────────────────

enum class VaultClientStatus {
    OK,                  // Material obtenido de Vault
    OK_FROM_CACHE,       // Vault KO, cache válida — arranca con WARN
    ERROR_VAULT_DOWN,    // Vault KO + cache vacía — exit(1)
    ERROR_DERIVE,        // Fallo en derivación kdf/keypair
    ERROR_CACHE_WRITE,   // No se pudo escribir cache (no fatal)
};

struct VaultClientResult {
    VaultClientStatus status;
    std::optional<CryptoMaterial> material;
    std::string error_message;
};

// ── API pública ───────────────────────────────────────────────────────────────

class VaultClient {
public:
    explicit VaultClient(const VaultClientConfig& config);
    ~VaultClient();

    // Obtiene material criptográfico con jitter + cache + fallback
    VaultClientResult fetch_crypto_material();

    // Registra estado en etcd: {component, crypto_ready, key_version,
    // family, fingerprint, derivation_timestamp}
    // Retorna false si etcd no disponible (no fatal para edge autonomy)
    bool register_etcd_status(const CryptoMaterial& material,
                               bool started_with_cache = false);

    // Arranca keepalive de lease etcd en background (TTL=10s, cada 5s)
    void start_etcd_keepalive();
    void stop_etcd_keepalive();

    // Utilidades
    static std::string fingerprint_hex(const Sha256Fingerprint& fp);
    static std::string now_iso8601();

private:
    VaultClientConfig config_;
    int64_t           etcd_lease_id_{0};
    bool              keepalive_running_{false};

    // Jitter anti-stampede (DEBT-CRYPTO-STAMPEDE-001)
    void apply_jitter();

    // Vault HTTP GET
    std::optional<std::string> vault_get_seed();

    // Derivación (Kimi D12): kdf_derive → component_seed → sign_seed_keypair
    std::optional<CryptoMaterial> derive_material(const std::string& master_seed_hex);

    // Cache tmpfs
    std::string cache_path() const;
    bool        write_cache(const CryptoMaterial& material);
    std::optional<CryptoMaterial> read_cache();
    bool        cache_valid() const;

    // mlock opcional (WARNING si falla)
    void try_mlock(void* ptr, size_t len);
};

} // namespace ml_defender
