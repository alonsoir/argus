// ============================================================================
// vault_client.cpp — ADR-044/045 — coordinador tras extracción DAY 153
// ============================================================================
#include "vault_client.h"
#include "vault_transport.h"
#include "cache_manager.h"

#include <sodium.h>
#include <chrono>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <sys/mman.h>

namespace ml_defender {

// ── Constructores ─────────────────────────────────────────────────────────────

VaultClient::VaultClient(const VaultClientConfig& config)
    : VaultClient(config, nullptr, nullptr) {}

VaultClient::VaultClient(const VaultClientConfig& config,
                         std::unique_ptr<IVaultTransport> transport,
                         std::unique_ptr<ICacheManager>   cache)
    : config_(config)
    , transport_(transport
          ? std::move(transport)
          : std::make_unique<HttpVaultTransport>())
    , cache_(cache
          ? std::move(cache)
          : std::make_unique<FilesystemCacheManager>(config))
{
    if (sodium_init() < 0) {
        std::cerr << "[vault_client] ERROR: libsodium init failed\n";
    }
}

VaultClient::~VaultClient() {
    stop_etcd_keepalive();
}

// ── fetch_crypto_material ─────────────────────────────────────────────────────

VaultClientResult VaultClient::fetch_crypto_material() {
    // 1. Intentar Vault via transport_ (incluye jitter)
    auto seed_opt = transport_->fetch_seed(config_);
    if (seed_opt) {
        auto mat_opt = derive_material(*seed_opt);
        if (!mat_opt) {
            return {VaultClientStatus::ERROR_DERIVE, std::nullopt,
                    "kdf/keypair derivation failed"};
        }
        cache_->write(*mat_opt);  // fallo no es fatal
        return {VaultClientStatus::OK, std::move(mat_opt), ""};
    }

    // 2. Vault KO — intentar cache_
    std::cerr << "[vault_client] WARN: Vault no disponible en "
              << config_.vault_addr << "\n";

    if (cache_->is_valid()) {
        auto cached = cache_->read();
        if (cached) {
            cached->from_cache = true;
            std::cerr << "[vault_client] WARN: arrancando con cache\n";
            return {VaultClientStatus::OK_FROM_CACHE, std::move(cached), ""};
        }
    }

    // 3. Sin Vault ni cache
    return {VaultClientStatus::ERROR_VAULT_DOWN, std::nullopt,
            "Vault KO y cache vacía o expirada"};
}

// ── Derivación (permanece aquí hasta DAY 154 → ICryptoDeriver) ───────────────

namespace {

std::string hex_encode(const uint8_t* data, size_t len) {
    std::ostringstream oss;
    for (size_t i = 0; i < len; ++i)
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(data[i]);
    return oss.str();
}

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

std::optional<CryptoMaterial> VaultClient::derive_material(
        const std::string& master_seed_hex) {
    std::array<uint8_t, 32> master_seed{};
    if (!hex_decode(master_seed_hex, master_seed.data(), 32))
        return std::nullopt;

    std::array<uint8_t, 32> component_seed{};
    char ctx[crypto_kdf_CONTEXTBYTES] = {};
    std::string ctx_str = "family_" + config_.family;
    std::memcpy(ctx, ctx_str.c_str(),
                std::min(ctx_str.size(),
                         static_cast<size_t>(crypto_kdf_CONTEXTBYTES)));

    if (crypto_kdf_derive_from_key(
            component_seed.data(), component_seed.size(),
            static_cast<uint64_t>(config_.component_index),
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
    mat.family               = config_.family;
    mat.key_version          = 1;
    mat.derivation_timestamp = now_iso8601();
    mat.from_cache           = false;

    try_mlock(mat.sk.data(), mat.sk.size());
    return mat;
}

// ── Etcd (sin cambios) ────────────────────────────────────────────────────────

bool VaultClient::register_etcd_status(const CryptoMaterial& material,
                                        bool started_with_cache) {
    std::ostringstream json;
    json << "{"
         << "\"component\":\"" << config_.component_name << "\","
         << "\"crypto_ready\":true,"
         << "\"key_version\":"   << material.key_version << ","
         << "\"family\":\""      << material.family << "\","
         << "\"fingerprint\":\"" << fingerprint_hex(material.fingerprint) << "\","
         << "\"derivation_timestamp\":\"" << material.derivation_timestamp << "\","
         << "\"started_with_cache\":"
             << (started_with_cache ? "true" : "false")
         << "}";
    std::cerr << "[vault_client] INFO: etcd crypto_status (stub): "
              << json.str() << "\n";
    return true;
}

void VaultClient::start_etcd_keepalive()  { keepalive_running_ = true; }
void VaultClient::stop_etcd_keepalive()   { keepalive_running_ = false; }

// ── Utilidades ────────────────────────────────────────────────────────────────

void VaultClient::try_mlock(void* ptr, size_t len) {
    if (!config_.mlock_enabled) return;
    if (mlock(ptr, len) != 0)
        std::cerr << "[vault_client] WARN: mlock() falló (no fatal)\n";
}

std::string VaultClient::fingerprint_hex(const Sha256Fingerprint& fp) {
    return hex_encode(fp.data(), fp.size());
}

std::string VaultClient::now_iso8601() {
    auto now = std::chrono::system_clock::now();
    auto t   = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

} // namespace ml_defender