// ============================================================================
// crypto_deriver.cpp — HkdfCryptoDeriver  (ADR-045, DAY 154)
// ============================================================================
#include "crypto_deriver.h"
#include <sodium.h>
#include <array>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <cstdio>
#include <algorithm>

namespace ml_defender {

namespace {

bool hex_decode(const std::string& hex, uint8_t* out, size_t expected_len) {
    if (hex.size() != expected_len * 2) return false;
    for (size_t i = 0; i < expected_len; ++i) {
        unsigned int byte;
        if (std::sscanf(hex.c_str() + 2*i, "%02x", &byte) != 1) return false;
        out[i] = static_cast<uint8_t>(byte);
    }
    return true;
}

} // namespace anon

std::optional<CryptoMaterial> HkdfCryptoDeriver::derive(
        const std::string&      master_seed_hex,
        const VaultClientConfig& config) {

    std::array<uint8_t, 32> master_seed{};
    if (!hex_decode(master_seed_hex, master_seed.data(), 32))
        return std::nullopt;

    std::array<uint8_t, 32> component_seed{};
    char ctx[crypto_kdf_CONTEXTBYTES] = {};
    std::string ctx_str = "family_" + config.family;
    std::memcpy(ctx, ctx_str.c_str(),
                std::min(ctx_str.size(),
                         static_cast<size_t>(crypto_kdf_CONTEXTBYTES)));

    if (crypto_kdf_derive_from_key(
            component_seed.data(), component_seed.size(),
            static_cast<uint64_t>(config.component_index),
            ctx,
            master_seed.data()) != 0) {
        return std::nullopt;
    }

    CryptoMaterial mat;
    if (crypto_sign_seed_keypair(mat.pk.data(), mat.sk.data(),
                                 component_seed.data()) != 0) {
        return std::nullopt;
    }

    crypto_hash_sha256(mat.fingerprint.data(), mat.pk.data(), mat.pk.size());
    mat.family               = config.family;
    mat.key_version          = 1;
    mat.from_cache           = false;
    // derivation_timestamp lo pone VaultClient (tiene now_iso8601)
    return mat;
}

} // namespace ml_defender
