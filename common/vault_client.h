#pragma once
// ============================================================================
// vault_client.h — ADR-044/045 Vault Crypto Client
// ============================================================================
#include "vault_types.h"
#include "vault_transport.h"
#include "cache_manager.h"
#include "crypto_deriver.h"
#include "etcd_registrar.h"
#include <memory>
namespace ml_defender {
    class VaultClient {
    public:
        explicit VaultClient(const VaultClientConfig& config);
        VaultClient(const VaultClientConfig& config,
                    std::unique_ptr<IVaultTransport> transport,
                    std::unique_ptr<ICacheManager>   cache);
        VaultClient(const VaultClientConfig& config,
                    std::unique_ptr<IVaultTransport>  transport,
                    std::unique_ptr<ICacheManager>    cache,
                    std::unique_ptr<ICryptoDeriver>   deriver,
                    std::unique_ptr<IEtcdRegistrar>   registrar = nullptr);
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
        std::unique_ptr<ICryptoDeriver>  deriver_;
        std::unique_ptr<IEtcdRegistrar>  registrar_;
        void try_mlock(void* ptr, size_t len);
    };
} // namespace ml_defender
