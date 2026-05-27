// ============================================================================
// crypto_provider.cpp — CryptoProvider::create() factory
// ============================================================================
// ÚNICO fichero del codebase donde vive #ifdef ARGUS_VAULT_ENABLED.
// Ningún componente del pipeline debe incluir vault_provider.h ni
// seed_file_provider.h directamente.
// ============================================================================

#include "crypto_provider.h"
#include <cstdlib>
#include "seed_file_provider.h"

#ifdef ARGUS_VAULT_ENABLED
#include "vault_provider.h"
#endif

#include <stdexcept>

namespace ml_defender {

    std::unique_ptr<ICryptoProvider> CryptoProvider::create(
        const CryptoProviderConfig& config)
    {
#ifdef ARGUS_VAULT_ENABLED
        // Leer credenciales Vault de env vars si están presentes (BACKLOG-CRYPTO-VENDOR-KEY-001)
        CryptoProviderConfig vault_config = config;
        const char* env_addr  = std::getenv("VAULT_ADDR");
        const char* env_token = std::getenv("VAULT_TOKEN");
        if (env_addr)  vault_config.vault_config.vault_addr  = env_addr;
        if (env_token) vault_config.vault_config.vault_token = env_token;
        return std::make_unique<VaultProvider>(vault_config);
#else
        return std::make_unique<SeedFileProvider>(config);
#endif
    }

} // namespace ml_defender