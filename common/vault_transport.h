#pragma once
// ============================================================================
// vault_transport.h — IVaultTransport (ADR-045 DAY 153)
// ============================================================================
// Responsabilidad: comunicación HTTP con HashiCorp Vault + jitter
// anti-stampede.
//
// Implementaciones:
//   HttpVaultTransport  — curl + jitter real (producción)
//   NullVaultTransport  — siempre retorna nullopt (tests sin Vault)
//   StubVaultTransport  — retorna seed configurable (tests unitarios)
//
// Referencia: ADR-045, DEBT-CRYPTO-STAMPEDE-001
// ============================================================================

#include "vault_types.h"
#include <optional>
#include <string>

namespace ml_defender {

// ── Interfaz ──────────────────────────────────────────────────────────────────

class IVaultTransport {
public:
    virtual ~IVaultTransport() = default;

    // Obtiene el master seed desde Vault.
    // Aplica jitter anti-stampede antes de la llamada HTTP.
    // Retorna nullopt si Vault no está disponible.
    virtual std::optional<std::string> fetch_seed(
        const VaultClientConfig& config) = 0;
};

// ── HttpVaultTransport — producción ──────────────────────────────────────────

class HttpVaultTransport final : public IVaultTransport {
public:
    HttpVaultTransport() = default;
    ~HttpVaultTransport() override = default;

    std::optional<std::string> fetch_seed(
        const VaultClientConfig& config) override;

private:
    void apply_jitter(const VaultClientConfig& config);
    std::optional<std::string> vault_http_get(const VaultClientConfig& config);
    static std::optional<std::string> parse_vault_value(const std::string& json);
};

// ── NullVaultTransport — tests (Vault siempre KO) ────────────────────────────

class NullVaultTransport final : public IVaultTransport {
public:
    std::optional<std::string> fetch_seed(
        const VaultClientConfig&) override {
        return std::nullopt;
    }
};

// ── StubVaultTransport — tests (seed configurable) ───────────────────────────

class StubVaultTransport final : public IVaultTransport {
public:
    explicit StubVaultTransport(std::string seed)
        : seed_(std::move(seed)) {}

    // vault_transport.h — StubVaultTransport
    std::optional<std::string> fetch_seed(
        const VaultClientConfig&) override {
        if (unavailable_) return std::nullopt;  // ← añadir esta línea
        if (seed_.empty()) return std::nullopt;
        return seed_;
    }

    void set_seed(std::string seed) { seed_ = std::move(seed); }
    void set_unavailable() { seed_.clear(); unavailable_ = true; }

private:
    std::string seed_;
    bool        unavailable_{false};
};

} // namespace ml_defender