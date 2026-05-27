#pragma once
// ============================================================================
// vault_provider.h — VaultProvider (enterprise, ARGUS_VAULT_ENABLED=ON)
// ============================================================================
#include "crypto_provider.h"
#include "crypto_autonomy.h"
#include "vault_client.h"
#include <memory>
#include <optional>

namespace ml_defender {

class VaultProvider final : public ICryptoProvider {
public:
    explicit VaultProvider(const CryptoProviderConfig& config);
    ~VaultProvider() override;

    VaultProvider(const VaultProvider&)            = delete;
    VaultProvider& operator=(const VaultProvider&) = delete;

    // ICryptoProvider ─────────────────────────────────────────────────────────

    CryptoMaterial get_material() override;
    bool refresh() override;
    bool is_healthy() const override;
    std::string component_name() const override;

    // Delega a autonomy_.current_mode()
    OperationalMode get_operational_mode() const noexcept override;

private:
    CryptoProviderConfig          config_;
    std::unique_ptr<VaultClient>  vault_client_;
    std::optional<CryptoMaterial> cached_material_;
    bool                          healthy_{false};

    // Máquina de estados de autonomía — thread-safe internamente.
    CryptoAutonomy                autonomy_;
};

} // namespace ml_defender