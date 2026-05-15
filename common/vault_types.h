#pragma once
// ============================================================================
// vault_types.h — Tipos compartidos (ADR-045 DAY 153)
// ============================================================================
// Extraído de vault_client.h para romper el include circular:
//   vault_client.h ← vault_transport.h ← vault_client.h  ← CIRCULAR
//
// Orden correcto:
//   vault_types.h (tipos) ← vault_transport.h
//                         ← cache_manager.h
//                         ← vault_client.h
// ============================================================================

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <chrono>

namespace ml_defender {

// ── Constantes ────────────────────────────────────────────────────────────────

constexpr uint32_t VAULT_TIMEOUT_DEV_MS  = 5000;
constexpr uint32_t VAULT_TIMEOUT_PROD_MS = 15000;
constexpr uint32_t VAULT_JITTER_BASE_MS  = 500;
constexpr uint32_t VAULT_JITTER_RAND_MS  = 1000;
constexpr uint32_t ETCD_LEASE_TTL_S      = 10;
constexpr uint32_t ETCD_KEEPALIVE_S      = 5;
constexpr uint32_t CACHE_TTL_DEV_S       = 3600;
constexpr uint32_t CACHE_TTL_PROD_S      = 259200;

// ── Tipos ─────────────────────────────────────────────────────────────────────

using Ed25519PublicKey  = std::array<uint8_t, 32>;
using Ed25519SecretKey  = std::array<uint8_t, 64>;
using Sha256Fingerprint = std::array<uint8_t, 32>;

struct CryptoMaterial {
    Ed25519PublicKey  pk;
    Ed25519SecretKey  sk;
    Sha256Fingerprint fingerprint;
    std::string       family;
    uint32_t          key_version{0};
    std::string       derivation_timestamp;
    bool              from_cache{false};
};

struct VaultClientConfig {
    std::string vault_addr        {"http://127.0.0.1:8200"};
    std::string vault_token       {"root"};
    std::string env               {"dev"};
    std::string component_name;
    uint32_t    component_index   {0};
    std::string family            {"A"};
    std::string cache_dir         {"/run/argus/crypto-cache"};
    uint32_t    timeout_ms        {VAULT_TIMEOUT_DEV_MS};
    uint32_t    cache_ttl_s       {CACHE_TTL_DEV_S};
    bool        mlock_enabled     {false};
};

enum class VaultClientStatus {
    OK,
    OK_FROM_CACHE,
    ERROR_VAULT_DOWN,
    ERROR_DERIVE,
    ERROR_CACHE_WRITE,
};

struct VaultClientResult {
    VaultClientStatus             status;
    std::optional<CryptoMaterial> material;
    std::string                   error_message;
};

} // namespace ml_defender