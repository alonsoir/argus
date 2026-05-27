// ============================================================================
// crypto_provider.cpp — CryptoProvider::create() factory
// ============================================================================
// ÚNICO fichero del codebase donde vive #ifdef ARGUS_VAULT_ENABLED.
// Ningún componente del pipeline debe incluir vault_provider.h ni
// seed_file_provider.h directamente.
// ============================================================================

#include "crypto_provider.h"
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
        return std::make_unique<VaultProvider>(config);
#else
        return std::make_unique<SeedFileProvider>(config);
#endif
    }

} // namespace ml_defender