#pragma once
// ============================================================================
// crypto_provider_handle.hpp — RCU wrapper para ICryptoProvider
// BACKLOG-CRYPTO-HOT-RELOAD-001 (DAY 163)
//
// Permite swap atómico del provider sin downtime ni lock visible al caller.
//
// DISEÑO RCU (Read-Copy-Update ligero):
//   - Readers: h.get() → shared_ptr<ICryptoProvider> — atomic load, lock-free
//   - Writer:  h.reload(new_provider) → atomic store — un único writer a la vez
//   - El provider anterior sobrevive hasta que todos los readers liberen su
//     shared_ptr (refcount → 0). Cero use-after-free, cero null windows.
//
// GARANTÍAS:
//   - h.get() nunca devuelve null (invariante post-construcción)
//   - reload(nullptr) lanza std::invalid_argument; el handle queda válido
//   - Thread-safe: N readers + 1 writer concurrentes sin mutex visible
//   - No copiable — contiene material criptográfico compartido
//
// USO TÍPICO (componente):
//   CryptoProviderHandle handle(CryptoProvider::create(cfg));
//   auto p = handle.get();              // shared_ptr — reader safe
//   auto mat = p->get_material();
//   // rotación de época (FASE 2 — ADR-045):
//   handle.reload(CryptoProvider::create(new_cfg));
//
// REFERENCIAS: ADR-045 (CryptoEpoch), BACKLOG-CRYPTO-EPOCH-001
// ============================================================================

#include "crypto_provider.h"
#include <atomic>
#include <memory>
#include <stdexcept>
#include <string>

namespace ml_defender {

class CryptoProviderHandle {
public:
    // Construye el handle con el provider inicial.
    // Lanza std::invalid_argument si provider == nullptr.
    explicit CryptoProviderHandle(std::unique_ptr<ICryptoProvider> provider) {
        if (!provider) {
            throw std::invalid_argument(
                "CryptoProviderHandle: provider no puede ser null");
        }
        current_.store(
            std::shared_ptr<ICryptoProvider>(std::move(provider)),
            std::memory_order_release);
    }

    // No copiable — semántica de ownership único del provider activo.
    CryptoProviderHandle(const CryptoProviderHandle&)            = delete;
    CryptoProviderHandle& operator=(const CryptoProviderHandle&) = delete;

    // Obtiene un shared_ptr al provider activo.
    // Atomic load — lock-free en x86/ARM con std::atomic<shared_ptr>.
    // El shared_ptr mantiene vivo el provider aunque llegue un reload().
    // Nunca devuelve null.
    [[nodiscard]] std::shared_ptr<ICryptoProvider> get() const noexcept {
        return current_.load(std::memory_order_acquire);
    }

    // Swap atómico del provider.
    // El provider anterior se destruye cuando todos los readers
    // liberen sus shared_ptr (refcount → 0).
    // Lanza std::invalid_argument si new_provider == nullptr.
    // Thread-safety: un único writer a la vez (coordinación externa via
    // CryptoEpoch — ADR-045). Múltiples writers concurrentes son ABA-safe
    // gracias a shared_ptr refcount, pero el orden de épocas no estaría
    // garantizado sin coordinación externa.
    void reload(std::unique_ptr<ICryptoProvider> new_provider) {
        if (!new_provider) {
            throw std::invalid_argument(
                "CryptoProviderHandle::reload: new_provider no puede ser null");
        }
        current_.store(
            std::shared_ptr<ICryptoProvider>(std::move(new_provider)),
            std::memory_order_release);
    }

    // ── Delegaciones de conveniencia ─────────────────────────────────────────

    [[nodiscard]] bool is_healthy() const noexcept {
        auto p = get();
        return p && p->is_healthy();
    }

    [[nodiscard]] std::string component_name() const {
        return get()->component_name();
    }

    [[nodiscard]] OperationalMode get_operational_mode() const noexcept {
        auto p = get();
        return p ? p->get_operational_mode() : OperationalMode::NORMAL;
    }

private:
    // provider activo — atomic shared_ptr (C++20 std::atomic<shared_ptr>)
    mutable std::atomic<std::shared_ptr<ICryptoProvider>> current_;
};

} // namespace ml_defender
