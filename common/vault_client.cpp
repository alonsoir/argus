// ============================================================================
// vault_client.cpp — ADR-044 implementación
// ============================================================================
#include "vault_client.h"

#include <sodium.h>
#include <curl/curl.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>

namespace ml_defender {

namespace {

// ── Helpers internos ─────────────────────────────────────────────────────────

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

// curl write callback
size_t curl_write_cb(char* ptr, size_t size, size_t nmemb, std::string* out) {
    out->append(ptr, size * nmemb);
    return size * nmemb;
}

// Extraer campo "value" de respuesta Vault KV v1
// {"data":{"value":"<hex>", ...}}
std::optional<std::string> parse_vault_value(const std::string& json) {
    const std::string key = "\"value\":\"";
    auto pos = json.find(key);
    if (pos == std::string::npos) return std::nullopt;
    pos += key.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) return std::nullopt;
    return json.substr(pos, end - pos);
}

} // namespace anon

// ── Constructor / Destructor ──────────────────────────────────────────────────

VaultClient::VaultClient(const VaultClientConfig& config)
    : config_(config) {
    if (sodium_init() < 0) {
        std::cerr << "[vault_client] ERROR: libsodium init failed\n";
    }
}

VaultClient::~VaultClient() {
    stop_etcd_keepalive();
}

// ── fetch_crypto_material ─────────────────────────────────────────────────────

VaultClientResult VaultClient::fetch_crypto_material() {
    // 1. Jitter anti-stampede
    apply_jitter();

    // 2. Intentar Vault
    auto seed_opt = vault_get_seed();
    if (seed_opt) {
        auto mat_opt = derive_material(*seed_opt);
        if (!mat_opt) {
            return {VaultClientStatus::ERROR_DERIVE, std::nullopt,
                    "kdf/keypair derivation failed"};
        }
        write_cache(*mat_opt);  // fallo no es fatal
        return {VaultClientStatus::OK, std::move(mat_opt), ""};
    }

    // 3. Vault KO — intentar cache
    std::cerr << "[vault_client] WARN: Vault no disponible en "
              << config_.vault_addr << "\n";

    if (cache_valid()) {
        auto cached = read_cache();
        if (cached) {
            cached->from_cache = true;
            std::cerr << "[vault_client] WARN: arrancando con cache "
                      << "(DEBT-ALERTING-EDGE-SOS-001)\n";
            return {VaultClientStatus::OK_FROM_CACHE, std::move(cached), ""};
        }
    }

    // 4. Sin Vault ni cache → exit(1)
    return {VaultClientStatus::ERROR_VAULT_DOWN, std::nullopt,
            "Vault KO y cache vacía o expirada"};
}

// ── Jitter (DEBT-CRYPTO-STAMPEDE-001) ────────────────────────────────────────

void VaultClient::apply_jitter() {
    std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist(0, VAULT_JITTER_RAND_MS);
    uint32_t delay_ms = config_.component_index * VAULT_JITTER_BASE_MS
                        + dist(rng);
    if (delay_ms > 0)
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
}

// ── Vault HTTP GET ────────────────────────────────────────────────────────────

std::optional<std::string> VaultClient::vault_get_seed() {
    // Determinar path: etcd es componente especial
    std::string path;
    if (config_.family == "etcd") {
        path = "argus/" + config_.env + "/components/etcd/seed";
    } else {
        path = "argus/" + config_.env + "/families/family_"
               + config_.family + "/seed";
    }

    std::string url = config_.vault_addr + "/v1/" + path;
    std::string response;

    CURL* curl = curl_easy_init();
    if (!curl) return std::nullopt;

    struct curl_slist* headers = nullptr;
    std::string token_header = "X-Vault-Token: " + config_.vault_token;
    headers = curl_slist_append(headers, token_header.c_str());

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS,
                     static_cast<long>(config_.timeout_ms));

    CURLcode res = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK || http_code != 200) return std::nullopt;
    return parse_vault_value(response);
}

// ── Derivación (Kimi D12/D13) ─────────────────────────────────────────────────
//
// kdf_derive(master_seed, component_index, ctx) → component_seed (32 bytes)
// sign_seed_keypair(component_seed)             → (pk 32B, sk 64B)
// fingerprint = sha256(pk)                      (Kimi D13)

std::optional<CryptoMaterial> VaultClient::derive_material(
        const std::string& master_seed_hex) {

    // Decodificar master seed
    std::array<uint8_t, 32> master_seed{};
    if (!hex_decode(master_seed_hex, master_seed.data(), 32))
        return std::nullopt;

    // kdf_derive → component_seed
    // Usamos crypto_kdf_derive_from_key (libsodium BLAKE2b-based KDF)
    // ctx: exactamente 8 bytes — rellenamos con familia
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

    // sign_seed_keypair → (pk, sk)
    CryptoMaterial mat;
    if (crypto_sign_seed_keypair(mat.pk.data(), mat.sk.data(),
                                 component_seed.data()) != 0) {
        return std::nullopt;
    }

    // fingerprint = sha256(pk) (Kimi D13)
    crypto_hash_sha256(mat.fingerprint.data(), mat.pk.data(), mat.pk.size());

    mat.family              = config_.family;
    mat.key_version         = 1;
    mat.derivation_timestamp = now_iso8601();
    mat.from_cache          = false;

    // mlock opcional
    try_mlock(mat.sk.data(), mat.sk.size());

    return mat;
}

// ── Cache tmpfs ───────────────────────────────────────────────────────────────

std::string VaultClient::cache_path() const {
    return config_.cache_dir + "/" + config_.component_name
           + "_" + config_.family + ".cache";
}

bool VaultClient::write_cache(const CryptoMaterial& material) {
    try {
        namespace fs = std::filesystem;
        fs::create_directories(config_.cache_dir);
        fs::permissions(config_.cache_dir,
                        fs::perms::owner_all,
                        fs::perm_options::replace);

        std::ofstream f(cache_path(), std::ios::binary | std::ios::trunc);
        if (!f) return false;

        // Formato: timestamp\npk_hex\nsk_hex\nfingerprint_hex\nfamily\nversion
        f << now_iso8601() << "\n";
        f << hex_encode(material.pk.data(), material.pk.size()) << "\n";
        f << hex_encode(material.sk.data(), material.sk.size()) << "\n";
        f << fingerprint_hex(material.fingerprint) << "\n";
        f << material.family << "\n";
        f << material.key_version << "\n";
        return f.good();
    } catch (...) {
        std::cerr << "[vault_client] WARN: no se pudo escribir cache "
                  << cache_path() << "\n";
        return false;
    }
}

bool VaultClient::cache_valid() const {
    namespace fs = std::filesystem;
    if (!fs::exists(cache_path())) return false;
    auto mtime = fs::last_write_time(cache_path());
    auto age   = std::chrono::file_clock::now() - mtime;
    auto age_s = std::chrono::duration_cast<std::chrono::seconds>(age).count();
    return static_cast<uint32_t>(age_s) < config_.cache_ttl_s;
}

std::optional<CryptoMaterial> VaultClient::read_cache() {
    std::ifstream f(cache_path(), std::ios::binary);
    if (!f) return std::nullopt;
    try {
        CryptoMaterial mat;
        std::string ts, pk_hex, sk_hex, fp_hex, family, version;
        std::getline(f, ts);
        std::getline(f, pk_hex);
        std::getline(f, sk_hex);
        std::getline(f, fp_hex);
        std::getline(f, family);
        std::getline(f, version);

        if (!hex_decode(pk_hex, mat.pk.data(), 32))   return std::nullopt;
        if (!hex_decode(sk_hex, mat.sk.data(), 64))   return std::nullopt;
        if (!hex_decode(fp_hex, mat.fingerprint.data(), 32)) return std::nullopt;

        mat.family               = family;
        mat.key_version          = static_cast<uint32_t>(std::stoul(version));
        mat.derivation_timestamp = ts;
        return mat;
    } catch (...) {
        return std::nullopt;
    }
}

// ── Etcd registration ─────────────────────────────────────────────────────────

bool VaultClient::register_etcd_status(const CryptoMaterial& material,
                                        bool started_with_cache) {
    // Construir JSON de registro
    std::ostringstream json;
    json << "{"
         << "\"component\":\"" << config_.component_name << "\","
         << "\"crypto_ready\":true,"
         << "\"key_version\":"  << material.key_version << ","
         << "\"family\":\""     << material.family << "\","
         << "\"fingerprint\":\"" << fingerprint_hex(material.fingerprint) << "\","
         << "\"derivation_timestamp\":\"" << material.derivation_timestamp << "\","
         << "\"started_with_cache\":" << (started_with_cache ? "true" : "false")
         << "}";

    // TODO: usar EtcdServiceRegistry para escribir la clave
    // argus/components/{component_name}/crypto_status
    // con lease TTL=10s (DEBT-CRYPTO-HEARTBEAT-001)
    // Implementación completa en siguiente iteración junto con keepalive
    std::cerr << "[vault_client] INFO: etcd crypto_status (stub): "
              << json.str() << "\n";
    return true;
}

void VaultClient::start_etcd_keepalive() {
    // TODO: DEBT-CRYPTO-HEARTBEAT-001
    // Lease TTL=10s, keepalive cada 5s en thread background
    keepalive_running_ = true;
}

void VaultClient::stop_etcd_keepalive() {
    keepalive_running_ = false;
}

// ── mlock opcional ────────────────────────────────────────────────────────────

void VaultClient::try_mlock(void* ptr, size_t len) {
    if (!config_.mlock_enabled) return;
    if (mlock(ptr, len) != 0) {
        std::cerr << "[vault_client] WARN: mlock() falló (no fatal)\n";
    }
}

// ── Utilidades ────────────────────────────────────────────────────────────────

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
