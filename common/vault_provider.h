#pragma once
// ============================================================================
// vault_provider.h — VaultProvider (enterprise, ARGUS_VAULT_ENABLED=ON)
// ============================================================================
// Implementación de ICryptoProvider que obtiene material criptográfico desde
// HashiCorp Vault via VaultClient (ADR-044).
//
// Toda la lógica de jitter, cache tmpfs, fallback y keepalive etcd
// vive en VaultClient — VaultProvider es un adapter delgado.
//
// Uso:
//   Solo instanciar via CryptoProvider::create() — no directamente.
//
// Referencia: ADR-044, ADR-025
// ============================================================================

#include "crypto_provider.h"
#include "vault_client.h"
#include <memory>
#include <optional>

namespace ml_defender {

class VaultProvider final : public ICryptoProvider {
public:
    explicit VaultProvider(const CryptoProviderConfig& config);
    ~VaultProvider() override;

    // No copiable.
    VaultProvider(const VaultProvider&)            = delete;
    VaultProvider& operator=(const VaultProvider&) = delete;

    // ICryptoProvider ─────────────────────────────────────────────────────────

    // Obtiene material via VaultClient::fetch_crypto_material().
    // Si el material ya está en cache local, lo devuelve directamente.
    // Lanza std::runtime_error si Vault KO + cache vacía
    // (VaultClientStatus::ERROR_VAULT_DOWN).
    CryptoMaterial get_material() override;

    // Fuerza un nuevo fetch desde Vault.
    // Retorna false si Vault no está disponible (usa cache interna si existe).
    bool refresh() override;

    // true si el último fetch/refresh fue OK o OK_FROM_CACHE.
    bool is_healthy() const override;

    std::string component_name() const override;

private:
    CryptoProviderConfig          config_;
    std::unique_ptr<VaultClient>  vault_client_;
    std::optional<CryptoMaterial> cached_material_;
    bool                          healthy_{false};
};

} // namespace ml_defender