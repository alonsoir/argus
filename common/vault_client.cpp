// ============================================================================
// vault_client.cpp — ADR-044/045 — coordinador tras extracción DAY 153
// ============================================================================
#include "vault_client.h"
#include "crypto_deriver.h"
#include "etcd_registrar.h"
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
    : VaultClient(config, std::move(transport), std::move(cache), nullptr) {}

VaultClient::VaultClient(const VaultClientConfig& config,
                         std::unique_ptr<IVaultTransport>  transport,
                         std::unique_ptr<ICacheManager>    cache,
                         std::unique_ptr<ICryptoDeriver>   deriver,
                         std::unique_ptr<IEtcdRegistrar>   registrar)
    : config_(config)
    , transport_(transport
          ? std::move(transport)
          : std::make_unique<HttpVaultTransport>())
    , cache_(cache
          ? std::move(cache)
          : std::make_unique<FilesystemCacheManager>(config))
    , deriver_(deriver
          ? std::move(deriver)
          : std::make_unique<HkdfCryptoDeriver>())
    , registrar_(registrar
          ? std::move(registrar)
          : std::make_unique<StubEtcdRegistrar>())
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
        auto mat_opt = deriver_->derive(*seed_opt, config_);
        if (mat_opt) mat_opt->derivation_timestamp = now_iso8601();
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

// ── Etcd (sin cambios) ────────────────────────────────────────────────────────

bool VaultClient::register_etcd_status(const CryptoMaterial& material,
                                        bool started_with_cache) {
    return registrar_->register_status(material, config_.component_name,
                                       started_with_cache);
}
void VaultClient::start_etcd_keepalive()  { registrar_->start_keepalive(); }
void VaultClient::stop_etcd_keepalive()   { registrar_->stop_keepalive(); }

// ── Utilidades ────────────────────────────────────────────────────────────────

void VaultClient::try_mlock(void* ptr, size_t len) {
    if (!config_.mlock_enabled) return;
    if (mlock(ptr, len) != 0)
        std::cerr << "[vault_client] WARN: mlock() falló (no fatal)\n";
}

namespace {
std::string hex_encode(const uint8_t* data, size_t len) {
    std::ostringstream oss;
    for (size_t i = 0; i < len; ++i)
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(data[i]);
    return oss.str();
}
} // namespace

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