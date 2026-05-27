#pragma once
// ============================================================================
// cache_manager.h — ICacheManager (ADR-045 DAY 153)
// ============================================================================
// Responsabilidad: persistencia de CryptoMaterial en tmpfs con TTL.
//
// Implementaciones:
//   FilesystemCacheManager  — fichero en tmpfs (producción)
//   NullCacheManager        — siempre vacía (tests sin FS)
//   InMemoryCacheManager    — mapa en memoria (tests unitarios)
//
// Referencia: ADR-045, DEBT-CRYPTO-HEARTBEAT-001
// ============================================================================

#include "vault_types.h"   // en lugar de "vault_client.h"
#include <optional>
#include <string>

namespace ml_defender {

// ── Interfaz ──────────────────────────────────────────────────────────────────

class ICacheManager {
public:
    virtual ~ICacheManager() = default;

    // Persiste material. Retorna false si falla (no fatal).
    virtual bool write(const CryptoMaterial& material) = 0;

    // Lee material persistido. Retorna nullopt si no existe o está corrupto.
    virtual std::optional<CryptoMaterial> read() = 0;

    // true si existe cache válida (no expirada).
    virtual bool is_valid() const = 0;

    // Ruta física (para logging/diagnóstico).
    virtual std::string path() const = 0;
};

// ── FilesystemCacheManager — producción ──────────────────────────────────────

class FilesystemCacheManager final : public ICacheManager {
public:
    explicit FilesystemCacheManager(const VaultClientConfig& config);
    ~FilesystemCacheManager() override = default;

    bool write(const CryptoMaterial& material) override;
    std::optional<CryptoMaterial> read() override;
    bool is_valid() const override;
    std::string path() const override;

private:
    VaultClientConfig config_;
};

// ── NullCacheManager — tests (sin cache) ─────────────────────────────────────

class NullCacheManager final : public ICacheManager {
public:
    bool write(const CryptoMaterial&) override { return true; }
    std::optional<CryptoMaterial> read() override { return std::nullopt; }
    bool is_valid() const override { return false; }
    std::string path() const override { return "/dev/null"; }
};

// ── InMemoryCacheManager — tests (cache configurable) ────────────────────────

class InMemoryCacheManager final : public ICacheManager {
public:
    bool write(const CryptoMaterial& material) override {
        cached_ = material;
        valid_  = true;
        return true;
    }

    std::optional<CryptoMaterial> read() override {
        if (!valid_ || !cached_.has_value()) return std::nullopt;
        return cached_;
    }

    bool is_valid() const override { return valid_ && cached_.has_value(); }
    std::string path() const override { return "<in-memory>"; }

    void invalidate() { valid_ = false; }
    void clear()      { cached_.reset(); valid_ = false; }

private:
    std::optional<CryptoMaterial> cached_;
    bool valid_{false};
};

} // namespace ml_defender