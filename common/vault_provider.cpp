// ============================================================================
// vault_provider.cpp — VaultProvider implementation (ADR-044 DAY 152)
// ============================================================================
#include "vault_provider.h"
#include <stdexcept>
#include <iostream>

namespace ml_defender {

VaultProvider::VaultProvider(const CryptoProviderConfig& config)
    : config_(config)
    , vault_client_(std::make_unique<VaultClient>(config.vault_config))
    , autonomy_(config.component_name)   // ← DAY 152: inicializar con nombre
{
    if (config_.component_name.empty()) {
        throw std::runtime_error("VaultProvider: component_name vacío");
    }
    std::cout << "[VaultProvider] 🔐 Arrancando modo enterprise — componente: "
              << config_.component_name << std::endl;
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
            autonomy_.on_vault_unreachable();   // ← DAY 152
            throw std::runtime_error(
                "VaultProvider: Vault KO y sin cache — " + result.error_message);

        case VaultClientStatus::ERROR_DERIVE:
            healthy_ = false;
            autonomy_.on_tamper_detected();     // ← DAY 152: derivación fallida = tampering
            throw std::runtime_error(
                "VaultProvider: derivación fallida — " + result.error_message);

        case VaultClientStatus::ERROR_CACHE_WRITE:
            // No fatal: material válido pero no se pudo cachear.
            cached_material_ = result.material.value();
            healthy_         = true;
            vault_client_->start_etcd_keepalive();
            return cached_material_.value();
    }
    throw std::runtime_error("VaultProvider: status desconocido");
}

bool VaultProvider::refresh() {
    const auto mode_before = autonomy_.current_mode();
    auto result = vault_client_->fetch_crypto_material();

    switch (result.status) {
        case VaultClientStatus::OK:
        case VaultClientStatus::OK_FROM_CACHE:
        case VaultClientStatus::ERROR_CACHE_WRITE:
            cached_material_ = result.material.value();
            healthy_         = true;
            // ── DAY 152: transiciones de recuperación ──────────────────────
            if (mode_before == OperationalMode::AUTONOMOUS) {
                autonomy_.on_vault_restored();      // AUTONOMOUS → RECONCILING
                autonomy_.on_reconciliation_ok();   // RECONCILING → NORMAL
            } else if (mode_before == OperationalMode::RECONCILING) {
                autonomy_.on_reconciliation_ok();   // RECONCILING → NORMAL
            }
            // NORMAL → no-op (refresh periódico sin outage previo)
            return true;

        case VaultClientStatus::ERROR_VAULT_DOWN:
            healthy_ = false;
            autonomy_.on_vault_unreachable();       // ← DAY 152
            return false;

        case VaultClientStatus::ERROR_DERIVE:
            healthy_ = false;
            autonomy_.on_tamper_detected();         // ← DAY 152
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

// ── DAY 152: get_operational_mode ─────────────────────────────────────────────

OperationalMode VaultProvider::get_operational_mode() const noexcept {
    return autonomy_.current_mode();
}

} // namespace ml_defender