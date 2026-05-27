#pragma once
// ICryptoProvider.hpp — aRGus NDR Crypto Provider Interface
// ADR-044: contrato entre plugin-loader enterprise y proveedores de seed.
// Implementaciones: seed_file (OSS), vault_crypto (enterprise).

#include <cstdint>
#include <string>
#include <vector>

namespace argus {

class ICryptoProvider {
public:
    virtual ~ICryptoProvider() = default;

    // Devuelve exactamente 32 bytes de seed para HKDF key derivation.
    // Lanza std::runtime_error si el proveedor no puede obtener el seed.
    // El caller es responsable de borrar el buffer tras usarlo.
    [[nodiscard]] virtual std::vector<uint8_t> get_seed() = 0;

    // Identificador del proveedor (ej: "vault_crypto", "seed_file").
    [[nodiscard]] virtual std::string provider_name() const noexcept = 0;

    // Health check — true si el proveedor es alcanzable.
    // Nunca lanza; devuelve false en caso de error.
    [[nodiscard]] virtual bool is_healthy() const noexcept = 0;
};

}  // namespace argus
