// common/crypto_autonomy.h
#pragma once
// ============================================================================
// crypto_autonomy.h — CryptoAutonomyStateMachine (ADR-044 DAY 152)
// ============================================================================
// Máquina de estados para el modo operacional del proveedor criptográfico.
//
// Estados:
//   NORMAL       → Vault accesible, material fresco
//   AUTONOMOUS   → Vault caído, operando con cache local
//   RECONCILING  → Vault recuperado, reconciliando material
//   DEGRADED     → Revocación o tampering detectado — no operar
//
// Concurrencia:
//   std::mutex              para transiciones (escritura)
//   std::atomic<Mode>       para lectura en hot path (firewall, keepalive)
//   Thread-safe desde el primer día.
//
// Clock inyectable (DEBT-AUTONOMY-CLOCK-INJECTION-001):
//   template<typename Clock = std::chrono::steady_clock>
//   ManualClock disponible para tests sin tiempo real.
//
// Regla: ningún componente instancia esta clase directamente.
//        Solo VaultProvider la posee como miembro.
//
// Referencia: ADR-044, ADR-045, DEBT-AUTONOMY-CLOCK-INJECTION-001
// ============================================================================

#include <atomic>
#include <chrono>
#include <functional>
#include <mutex>
#include <optional>
#include <string>

namespace ml_defender {

// ── Modos operacionales ───────────────────────────────────────────────────────

enum class OperationalMode : int {
    NORMAL       = 0,  // Vault OK, material fresco
    AUTONOMOUS   = 1,  // Vault KO, cache válida
    RECONCILING  = 2,  // Vault recuperado, reconciliando
    DEGRADED     = 3,  // Revocación/tampering — fail-closed
};

// Conversión a string para logging.
inline const char* operational_mode_str(OperationalMode m) noexcept {
    switch (m) {
        case OperationalMode::NORMAL:       return "NORMAL";
        case OperationalMode::AUTONOMOUS:   return "AUTONOMOUS";
        case OperationalMode::RECONCILING:  return "RECONCILING";
        case OperationalMode::DEGRADED:     return "DEGRADED";
    }
    return "UNKNOWN";
}

// ── ManualClock para tests ────────────────────────────────────────────────────

struct ManualClock {
    using duration   = std::chrono::steady_clock::duration;
    using time_point = std::chrono::steady_clock::time_point;

    static time_point now() noexcept { return current_time_; }
    static void advance(duration d) noexcept { current_time_ += d; }
    static void reset() noexcept {
        current_time_ = time_point{};
    }

private:
    inline static time_point current_time_{};
};

// ── CryptoAutonomyStateMachine ────────────────────────────────────────────────

template<typename Clock = std::chrono::steady_clock>
class CryptoAutonomyStateMachine {
public:
    using TimePoint = typename Clock::time_point;
    using Duration  = typename Clock::duration;

    // Callback opcional invocado en cada transición de estado.
    // Firma: void(OperationalMode from, OperationalMode to)
    // DEBT-AUTONOMY-ZMQ-EVENTS-001: en el futuro emitirá evento ZeroMQ.
    using TransitionCallback = std::function<void(OperationalMode, OperationalMode)>;

    // ── Constructor ──────────────────────────────────────────────────────────

    explicit CryptoAutonomyStateMachine(
        std::string component_name = "unknown",
        TransitionCallback on_transition = nullptr
    )
        : component_name_(std::move(component_name))
        , on_transition_(std::move(on_transition))
        , mode_(OperationalMode::NORMAL)
        , last_transition_(Clock::now())
    {}

    // No copiable, sí movible.
    CryptoAutonomyStateMachine(const CryptoAutonomyStateMachine&)            = delete;
    CryptoAutonomyStateMachine& operator=(const CryptoAutonomyStateMachine&) = delete;
    CryptoAutonomyStateMachine(CryptoAutonomyStateMachine&&)                 = default;
    CryptoAutonomyStateMachine& operator=(CryptoAutonomyStateMachine&&)      = default;

    // ── Eventos (tabla de transiciones explícita) ────────────────────────────

    // Vault no responde → NORMAL → AUTONOMOUS
    // Desde AUTONOMOUS o RECONCILING: no-op (ya gestionado).
    // Desde DEGRADED: no-op (fail-closed es terminal hasta reset manual).
    void on_vault_unreachable() {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto current = mode_.load(std::memory_order_relaxed);
        if (current == OperationalMode::NORMAL) {
            transition(OperationalMode::AUTONOMOUS);
        }
        // AUTONOMOUS, RECONCILING, DEGRADED: no-op
    }

    // Vault responde de nuevo → AUTONOMOUS → RECONCILING
    // Desde NORMAL: no-op (no hubo outage).
    // Desde RECONCILING: no-op (ya reconciliando).
    // Desde DEGRADED: no-op (fail-closed).
    void on_vault_restored() {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto current = mode_.load(std::memory_order_relaxed);
        if (current == OperationalMode::AUTONOMOUS) {
            transition(OperationalMode::RECONCILING);
        }
    }

    // Reconciliación completada → RECONCILING → NORMAL
    // Desde cualquier otro estado: no-op.
    void on_reconciliation_ok() {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto current = mode_.load(std::memory_order_relaxed);
        if (current == OperationalMode::RECONCILING) {
            transition(OperationalMode::NORMAL);
        }
    }

    // Revocación detectada → cualquier estado → DEGRADED (terminal)
    void on_revocation() {
        std::lock_guard<std::mutex> lock(mutex_);
        transition_to_degraded("revocation");
    }

    // Tampering detectado → cualquier estado → DEGRADED (terminal)
    void on_tamper_detected() {
        std::lock_guard<std::mutex> lock(mutex_);
        transition_to_degraded("tamper_detected");
    }

    // ── Consulta (hot path — sin lock) ───────────────────────────────────────

    // Modo actual. Lectura atómica — segura desde cualquier hilo.
    OperationalMode current_mode() const noexcept {
        return mode_.load(std::memory_order_acquire);
    }

    // true si el componente puede operar (NORMAL, AUTONOMOUS, RECONCILING).
    // false si DEGRADED.
    bool can_operate() const noexcept {
        const auto m = mode_.load(std::memory_order_acquire);
        return m != OperationalMode::DEGRADED;
    }

    // Tiempo desde la última transición de estado.
    Duration time_in_current_mode() const noexcept {
        return Clock::now() - last_transition_.load();
    }

    // Nombre del componente (para logging).
    const std::string& component_name() const noexcept {
        return component_name_;
    }

    // Razón del último DEGRADED (vacía si no hay).
    std::string degraded_reason() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return degraded_reason_;
    }

private:
    // ── Transición interna (requiere mutex tomado) ───────────────────────────

    void transition(OperationalMode to) {
        const auto from = mode_.load(std::memory_order_relaxed);
        if (from == to) return;
        mode_.store(to, std::memory_order_release);
        last_transition_.store(Clock::now());
        if (on_transition_) {
            on_transition_(from, to);
        }
    }

    void transition_to_degraded(const char* reason) {
        degraded_reason_ = reason;
        transition(OperationalMode::DEGRADED);
    }

    // ── Estado ───────────────────────────────────────────────────────────────

    std::string        component_name_;
    TransitionCallback on_transition_;

    // Escritura bajo mutex, lectura libre (atómica).
    std::atomic<OperationalMode>  mode_;
    std::atomic<TimePoint>        last_transition_;

    // Solo accesible bajo mutex.
    mutable std::mutex mutex_;
    std::string        degraded_reason_;
};

// ── Alias de conveniencia ─────────────────────────────────────────────────────

using CryptoAutonomy    = CryptoAutonomyStateMachine<std::chrono::steady_clock>;
using CryptoAutonomyMT  = CryptoAutonomyStateMachine<ManualClock>;  // para tests

} // namespace ml_defender