#pragma once
// vault_provider.hpp — aRGus NDR Enterprise Vault Crypto Provider
// Implementa ICryptoProvider obteniendo el seed desde HashiCorp Vault KV v2.
// C ABI: argus_enterprise_create / argus_enterprise_destroy (enterprise ADR-025).

#include <argus/ICryptoProvider.hpp>
#include <string>

namespace argus::enterprise {

class VaultProvider final : public ICryptoProvider {
public:
    struct Config {
        std::string vault_addr;      // "http://127.0.0.1:8200"
        std::string vault_token;     // token de acceso (dev: "argus-dev-token")
        std::string secret_path;     // "secret/data/argus/crypto"
        std::string seed_field;      // "seed"
        int         timeout_seconds = 5;
    };

    explicit VaultProvider(Config cfg);
    ~VaultProvider() override = default;

    VaultProvider(const VaultProvider&)            = delete;
    VaultProvider& operator=(const VaultProvider&) = delete;
    VaultProvider(VaultProvider&&)                 = delete;
    VaultProvider& operator=(VaultProvider&&)      = delete;

    // ICryptoProvider
    [[nodiscard]] std::vector<uint8_t> get_seed()                   override;
    [[nodiscard]] std::string          provider_name() const noexcept override { return "vault_crypto"; }
    [[nodiscard]] bool                 is_healthy()    const noexcept override;

private:
    Config cfg_;

    // HTTP GET al endpoint KV v2 de Vault. Lanza en error.
    std::string fetch_from_vault() const;

    // Extrae el valor de seed_field de la respuesta JSON de Vault KV v2.
    // Formato esperado: {"data":{"data":{"seed":"..."}}}
    [[nodiscard]] static std::string extract_seed_string(
        const std::string& response_json,
        const std::string& field);

    // SHA-256 del seed string → 32 bytes deterministas.
    // Permite seeds de longitud arbitraria en Vault.
    [[nodiscard]] static std::vector<uint8_t> derive_seed_bytes(
        const std::string& seed_string);
};

}  // namespace argus::enterprise

// ── C ABI enterprise (distinto del ABI OSS plugin_api.h) ──────────────────
// El enterprise plugin loader llama a estas funciones tras TokenValidator.
// argus_enterprise_create: parsea config_json, crea VaultProvider.
//   Devuelve nullptr si config_json es inválido (no aborta — el loader decide).
// argus_enterprise_destroy: destruye el objeto y libera memoria.
extern "C" {
    __attribute__((visibility("default")))
    argus::ICryptoProvider* argus_enterprise_create(const char* config_json);
    __attribute__((visibility("default")))
    void                    argus_enterprise_destroy(argus::ICryptoProvider* provider);
}
