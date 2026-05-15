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
#include "vault_types.h"
#include "vault_transport.h"
#include "cache_manager.h"
#include <memory>

namespace ml_defender {

    // ── API pública ───────────────────────────────────────────────────────────────

    class VaultClient {
    public:
        explicit VaultClient(const VaultClientConfig& config);

        VaultClient(const VaultClientConfig& config,
                    std::unique_ptr<IVaultTransport> transport,
                    std::unique_ptr<ICacheManager>   cache);

        ~VaultClient();

        VaultClientResult fetch_crypto_material();

        bool register_etcd_status(const CryptoMaterial& material,
                                   bool started_with_cache = false);

        void start_etcd_keepalive();
        void stop_etcd_keepalive();

        static std::string fingerprint_hex(const Sha256Fingerprint& fp);
        static std::string now_iso8601();

    private:
        VaultClientConfig                config_;
        int64_t                          etcd_lease_id_{0};
        bool                             keepalive_running_{false};

        std::unique_ptr<IVaultTransport> transport_;
        std::unique_ptr<ICacheManager>   cache_;

        std::optional<CryptoMaterial> derive_material(
            const std::string& master_seed_hex);
        void try_mlock(void* ptr, size_t len);
    };

} // namespace ml_defender