#pragma once
// ============================================================================
// seed_file_provider.h — SeedFileProvider (community, ARGUS_VAULT_ENABLED=OFF)
// ============================================================================
// Implementación de ICryptoProvider que lee material criptográfico desde el
// sistema de ficheros local (/etc/ml-defender/<component>/) via seed-client.
//
// Derivación (idéntica a VaultProvider, Kimi D12):
//   seed.bin (32B) → crypto_sign_seed_keypair() → (pk, sk)
//   fingerprint     = sha256(pk)
//
// El resultado es determinista: mismo seed.bin → mismo keypair siempre.
// Esto garantiza compatibilidad de canal ZeroMQ entre arranques.
//
// Uso:
//   Solo instanciar via CryptoProvider::create() — no directamente.
//
// Referencia: ADR-013, ADR-025, ADR-044
// ============================================================================

#include "crypto_provider.h"
#include <optional>

namespace ml_defender {

class SeedFileProvider final : public ICryptoProvider {
public:
    // Construye el provider pero NO carga aún el material.
    // La carga ocurre en la primera llamada a get_material() o refresh().
    explicit SeedFileProvider(const CryptoProviderConfig& config);

    ~SeedFileProvider() override = default;

    // No copiable — contiene material criptográfico sensible.
    SeedFileProvider(const SeedFileProvider&)            = delete;
    SeedFileProvider& operator=(const SeedFileProvider&) = delete;

    // ICryptoProvider ─────────────────────────────────────────────────────────

    // Lee seed.bin via SeedClient y deriva el keypair Ed25519.
    // Si el material ya está en cache, lo devuelve directamente.
    // Lanza std::runtime_error si seed.bin no existe o la derivación falla.
    CryptoMaterial get_material() override;

    // Recarga seed.bin desde disco y rederiva el keypair.
    // Útil si provision.sh rotó las claves.
    // Retorna false si seed.bin no es legible (no lanza).
    bool refresh() override;

    // true si el seed fue cargado correctamente y la cache es válida.
    bool is_healthy() const override;

    std::string component_name() const override;

private:
    CryptoProviderConfig         config_;
    std::optional<CryptoMaterial> cached_material_;

    // Construye el path al JSON del componente:
    //   config_.component_config_path + config_.component_name + ".json"
    // Ejemplo: /etc/ml-defender/etcd-server/etcd-server.json
    std::string json_path() const;

    // Carga seed via SeedClient y deriva CryptoMaterial.
    // Lanza std::runtime_error si algo falla.
    CryptoMaterial load_and_derive();

    // Derivación: seed (32B) → crypto_sign_seed_keypair → pk + sk + fingerprint.
    // Misma lógica que VaultClient::derive_material() (Kimi D12).
    static CryptoMaterial derive_from_seed(
        const std::array<uint8_t, 32>& seed,
        const std::string& family,
        uint32_t key_version);
};

} // namespace ml_defender