// ============================================================================
// cache_manager.cpp — FilesystemCacheManager (ADR-045 DAY 153)
// ============================================================================
// Extraído de vault_client.cpp: write_cache(), read_cache(), cache_valid()
// ============================================================================
#include "cache_manager.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

namespace ml_defender {

namespace {

std::string hex_encode_cm(const uint8_t* data, size_t len) {
    std::ostringstream oss;
    for (size_t i = 0; i < len; ++i)
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(data[i]);
    return oss.str();
}

bool hex_decode_cm(const std::string& hex, uint8_t* out, size_t expected_len) {
    if (hex.size() != expected_len * 2) return false;
    for (size_t i = 0; i < expected_len; ++i) {
        unsigned int byte;
        if (std::sscanf(hex.c_str() + 2*i, "%02x", &byte) != 1) return false;
        out[i] = static_cast<uint8_t>(byte);
    }
    return true;
}

} // namespace anon

// ── FilesystemCacheManager ────────────────────────────────────────────────────

FilesystemCacheManager::FilesystemCacheManager(const VaultClientConfig& config)
    : config_(config) {}

std::string FilesystemCacheManager::path() const {
    return config_.cache_dir + "/" + config_.component_name
           + "_" + config_.family + ".cache";
}

bool FilesystemCacheManager::write(const CryptoMaterial& material) {
    try {
        namespace fs = std::filesystem;
        fs::create_directories(config_.cache_dir);
        fs::permissions(config_.cache_dir,
                        fs::perms::owner_all,
                        fs::perm_options::replace);

        std::ofstream f(path(), std::ios::binary | std::ios::trunc);
        if (!f) return false;

        f << material.derivation_timestamp << "\n";
        f << hex_encode_cm(material.pk.data(), material.pk.size()) << "\n";
        f << hex_encode_cm(material.sk.data(), material.sk.size()) << "\n";
        f << hex_encode_cm(material.fingerprint.data(),
                           material.fingerprint.size()) << "\n";
        f << material.family << "\n";
        f << material.key_version << "\n";
        return f.good();
    } catch (...) {
        std::cerr << "[cache_manager] WARN: no se pudo escribir cache "
                  << path() << "\n";
        return false;
    }
}

bool FilesystemCacheManager::is_valid() const {
    namespace fs = std::filesystem;
    if (!fs::exists(path())) return false;
    auto mtime = fs::last_write_time(path());
    auto age   = std::chrono::file_clock::now() - mtime;
    auto age_s = std::chrono::duration_cast<std::chrono::seconds>(age).count();
    return static_cast<uint32_t>(age_s) < config_.cache_ttl_s;
}

std::optional<CryptoMaterial> FilesystemCacheManager::read() {
    std::ifstream f(path(), std::ios::binary);
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

        if (!hex_decode_cm(pk_hex, mat.pk.data(), 32))        return std::nullopt;
        if (!hex_decode_cm(sk_hex, mat.sk.data(), 64))        return std::nullopt;
        if (!hex_decode_cm(fp_hex, mat.fingerprint.data(), 32)) return std::nullopt;

        mat.family               = family;
        mat.key_version          = static_cast<uint32_t>(std::stoul(version));
        mat.derivation_timestamp = ts;
        return mat;
    } catch (...) {
        return std::nullopt;
    }
}

} // namespace ml_defender