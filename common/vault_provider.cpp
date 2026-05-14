// ============================================================================
// vault_provider.cpp — VaultProvider implementation
// ============================================================================

#include "vault_provider.h"
#include <stdexcept>

namespace ml_defender {

VaultProvider::VaultProvider(const CryptoProviderConfig& config)
    : config_(config)
    , vault_client_(std::make_unique<VaultClient>(config.vault_config))
{
    if (config_.component_name.empty()) {
        throw std::runtime_error("VaultProvider: component_name vacío");
    }
}

VaultProvider::~VaultProvider() {
    if (vault_client_) {
        vault_client_->stop_etcd_keepalive();
    }
}

// ── ICryptoProvider ───────────────────────────────────────────────────────────

CryptoMaterial VaultProvider::get_material() {
    if (cached_material_.has_value()) {
        return cached_material_.value();
    }

    auto result = vault_client_->fetch_crypto_material();

    switch (result.status) {
        case VaultClientStatus::OK:
        case VaultClientStatus::OK_FROM_CACHE:
            cached_material_ = result.material.value();
            healthy_         = true;
            vault_client_->start_etcd_keepalive();
            return cached_material_.value();

        case VaultClientStatus::ERROR_VAULT_DOWN:
            healthy_ = false;
            throw std::runtime_error(
                "VaultProvider: Vault KO y sin cache — " + result.error_message);

        case VaultClientStatus::ERROR_DERIVE:
            healthy_ = false;
            throw std::runtime_error(
                "VaultProvider: derivación fallida — " + result.error_message);

        case VaultClientStatus::ERROR_CACHE_WRITE:
            // No fatal: el material es válido pero no se pudo cachear.
            cached_material_ = result.material.value();
            healthy_         = true;
            vault_client_->start_etcd_keepalive();
            return cached_material_.value();
    }

    // Inalcanzable, pero el compilador lo agradece.
    throw std::runtime_error("VaultProvider: status desconocido");
}

bool VaultProvider::refresh() {
    auto result = vault_client_->fetch_crypto_material();

    switch (result.status) {
        case VaultClientStatus::OK:
        case VaultClientStatus::OK_FROM_CACHE:
        case VaultClientStatus::ERROR_CACHE_WRITE:
            cached_material_ = result.material.value();
            healthy_         = true;
            return true;

        case VaultClientStatus::ERROR_VAULT_DOWN:
        case VaultClientStatus::ERROR_DERIVE:
            healthy_ = false;
            return false;
    }

    return false;
}

bool VaultProvider::is_healthy() const {
    return healthy_;
}

std::string VaultProvider::component_name() const {
    return config_.component_name;
}

} // namespace ml_defender