#pragma once
// ============================================================================
// crypto_deriver.h — ICryptoDeriver  (ADR-045, DAY 154)
// ============================================================================
// Extrae la responsabilidad de derivación criptográfica de VaultClient.
//
// Implementación canónica: HkdfCryptoDeriver
//   kdf_derive(master_seed, component_index, "family_X_seed") → component_seed
//   sign_seed_keypair(component_seed) → (pk, sk)
//   fingerprint = sha256(pk)
//
// Referencia: ADR-044, ADR-045
// ============================================================================
#include "vault_types.h"
#include <optional>
#include <string>

namespace ml_defender {

class ICryptoDeriver {
public:
    virtual ~ICryptoDeriver() = default;
    virtual std::optional<CryptoMaterial> derive(
        const std::string&     master_seed_hex,
        const VaultClientConfig& config) = 0;
};

// Implementación HKDF vía libsodium crypto_kdf_derive_from_key
class HkdfCryptoDeriver : public ICryptoDeriver {
public:
    std::optional<CryptoMaterial> derive(
        const std::string&     master_seed_hex,
        const VaultClientConfig& config) override;
};

} // namespace ml_defender
