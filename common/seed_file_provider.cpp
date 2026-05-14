// ============================================================================
// seed_file_provider.cpp — SeedFileProvider implementation
// ============================================================================

#include "seed_file_provider.h"
#include <seed_client/seed_client.hpp>
#include <sodium.h>
#include <stdexcept>
#include <sstream>
#include <chrono>
#include <iomanip>

namespace ml_defender {

// ── Helpers ───────────────────────────────────────────────────────────────────

static std::string now_iso8601() {
    auto now = std::chrono::system_clock::now();
    auto t   = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

// ── Constructor ───────────────────────────────────────────────────────────────

SeedFileProvider::SeedFileProvider(const CryptoProviderConfig& config)
    : config_(config)
{
    if (config_.component_name.empty()) {
        throw std::runtime_error("SeedFileProvider: component_name vacío");
    }
    if (config_.component_config_path.empty()) {
        throw std::runtime_error("SeedFileProvider: component_config_path vacío");
    }
}

// ── ICryptoProvider ───────────────────────────────────────────────────────────

CryptoMaterial SeedFileProvider::get_material() {
    if (cached_material_.has_value()) {
        return cached_material_.value();
    }
    cached_material_ = load_and_derive();
    return cached_material_.value();
}

bool SeedFileProvider::refresh() {
    try {
        cached_material_ = load_and_derive();
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

bool SeedFileProvider::is_healthy() const {
    return cached_material_.has_value();
}

std::string SeedFileProvider::component_name() const {
    return config_.component_name;
}

// ── Privados ──────────────────────────────────────────────────────────────────

std::string SeedFileProvider::json_path() const {
    std::string path = config_.component_config_path;
    // Asegurar trailing slash
    if (!path.empty() && path.back() != '/') {
        path += '/';
    }
    return path + config_.component_name + ".json";
}

CryptoMaterial SeedFileProvider::load_and_derive() {
    SeedClient client(json_path());
    client.load();  // lanza std::runtime_error si falla

    const auto& raw_seed = client.seed();
    // family y key_version no aplican en SeedFileProvider —
    // el seed ya es el material final de provision.sh.
    return derive_from_seed(raw_seed, "seed-file", 0);
}

CryptoMaterial SeedFileProvider::derive_from_seed(
    const std::array<uint8_t, 32>& seed,
    const std::string& family,
    uint32_t key_version)
{
    // Derivación idéntica a VaultClient::derive_material() (Kimi D12):
    //   crypto_sign_seed_keypair(pk, sk, seed)
    CryptoMaterial mat;

    if (crypto_sign_seed_keypair(
            mat.pk.data(),
            mat.sk.data(),
            seed.data()) != 0)
    {
        throw std::runtime_error(
            "SeedFileProvider: crypto_sign_seed_keypair falló");
    }

    // Fingerprint = sha256(pk)  (Kimi D13)
    if (crypto_hash_sha256(mat.fingerprint.data(), mat.pk.data(),
                           mat.pk.size()) != 0)
    {
        throw std::runtime_error(
            "SeedFileProvider: sha256(pk) falló");
    }

    mat.family               = family;
    mat.key_version          = key_version;
    mat.derivation_timestamp = now_iso8601();
    mat.from_cache           = false;

    return mat;
}

} // namespace ml_defender