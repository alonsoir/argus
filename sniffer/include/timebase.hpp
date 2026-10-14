// [TIMEBASE-D295] Contrato temporal v1 (docs/timebase/contrato_temporal_day295.md).
// Logica PURA (sin protobuf ni config): ancla REALTIME-MONOTONIC, CLOCK_STEP y CLOCK_SLEW.
// Base interna unica: CLOCK_MONOTONIC (= bpf_ktime_get_ns del XDP = steady_clock).
// Medido DAY295: en reposo R-M varia < 0,00001 s en 720 s; MONOTONIC frente a RAW = -1876 ppm
// (correccion de frecuencia de base); tras suspender el Mac, chrony corrige gradualmente a
// +81300 ppm y R-M NO cambia (la correccion gradual solo se ve frente a MONOTONIC_RAW).
// Los valores vivos vienen de sniffer.json ("timebase"); estos son los DEFECTOS de laboratorio,
// que se usan con aviso [CONFIG-DEFAULT] si el JSON falta o es invalido.
#pragma once

#include <cmath>
#include <cstdint>
#include <fstream>
#include <string>
#include <time.h>

namespace argus::timebase {

inline constexpr uint32_t kContractVersion = 1;

struct TimebaseParams {
    double anchor_period_s = 1.0;        // cada cuanto se lee R-M y RAW
    double step_threshold_s = 0.05;      // cambio de R-M que cuenta como salto
    double slew_window_s = 10.0;         // ventana para medir MONOTONIC frente a RAW
    double slew_ppm_threshold = 10000.0; // |ppm| por encima = correccion gradual
    double stepped_recent_s = 60.0;      // tiempo en estado STEPPED tras un salto
};

// Rangos aceptados (inclusive). Documentados tambien en sniffer.json.
inline constexpr double kAnchorPeriodMin = 0.1, kAnchorPeriodMax = 60.0;
inline constexpr double kStepThresholdMin = 0.001, kStepThresholdMax = 10.0;
inline constexpr double kSlewWindowMin = 1.0, kSlewWindowMax = 300.0;
inline constexpr double kSlewPpmMin = 1000.0, kSlewPpmMax = 500000.0;
inline constexpr double kSteppedRecentMin = 1.0, kSteppedRecentMax = 3600.0;

inline bool in_range(double x, double lo, double hi) noexcept { return x >= lo && x <= hi; }

// Validacion completa: rangos + regla cruzada (la ventana de slew cubre al menos un periodo).
inline bool params_ok(const TimebaseParams& p) noexcept {
    return in_range(p.anchor_period_s, kAnchorPeriodMin, kAnchorPeriodMax) &&
           in_range(p.step_threshold_s, kStepThresholdMin, kStepThresholdMax) &&
           in_range(p.slew_window_s, kSlewWindowMin, kSlewWindowMax) &&
           in_range(p.slew_ppm_threshold, kSlewPpmMin, kSlewPpmMax) &&
           in_range(p.stepped_recent_s, kSteppedRecentMin, kSteppedRecentMax) &&
           p.slew_window_s >= p.anchor_period_s;
}

// Mismos valores que el enum ClockState del proto (CLOCK_STATE_OK/SLEWING/STEPPED).
enum class ClockState : uint8_t { Ok = 0, Slewing = 1, Stepped = 2 };

struct ClockReading {
    int64_t real_ns = 0;   // CLOCK_REALTIME
    uint64_t mono_ns = 0;  // CLOCK_MONOTONIC
    uint64_t raw_ns = 0;   // CLOCK_MONOTONIC_RAW
};

struct ClockEvents {
    bool stepped = false;
    double step_delta_s = 0.0;
    bool slew_measured = false;
    double slew_ppm = 0.0;
    bool slewing_changed = false;
};

inline uint64_t ts_to_ns(const timespec& t) noexcept {
    return static_cast<uint64_t>(t.tv_sec) * 1000000000ULL + static_cast<uint64_t>(t.tv_nsec);
}

inline ClockReading read_clocks() noexcept {
    timespec w{}, m{}, r{};
    clock_gettime(CLOCK_MONOTONIC_RAW, &w);
    clock_gettime(CLOCK_MONOTONIC, &m);
    clock_gettime(CLOCK_REALTIME, &r);  // justo despues de MONOTONIC: ancla con el menor jitter
    ClockReading c;
    c.real_ns = static_cast<int64_t>(r.tv_sec) * 1000000000LL + static_cast<int64_t>(r.tv_nsec);
    c.mono_ns = ts_to_ns(m);
    c.raw_ns = ts_to_ns(w);
    return c;
}

// /proc/sys/kernel/random/boot_id (36 caracteres); vacio si no se puede leer.
inline std::string read_boot_id() {
    std::ifstream f("/proc/sys/kernel/random/boot_id");
    std::string s;
    if (f) std::getline(f, s);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) s.pop_back();
    return s;
}

inline uint64_t epoch_ns(uint64_t mono_ns, int64_t anchor_ns) noexcept {
    return static_cast<uint64_t>(static_cast<int64_t>(mono_ns) + anchor_ns);
}

// Un solo hilo llama a update(); los demas leen copias atomicas que publica ese hilo.
class TimebaseState {
public:
    explicit TimebaseState(const TimebaseParams& p = TimebaseParams{}) : p_(p) {}

    ClockEvents update(const ClockReading& r) noexcept {
        ClockEvents ev;
        const int64_t anchor = r.real_ns - static_cast<int64_t>(r.mono_ns);
        if (!init_) {
            anchor_ns_ = anchor;
            win_mono0_ = r.mono_ns;
            win_raw0_ = r.raw_ns;
            init_ = true;
            return ev;
        }
        const int64_t delta = anchor - anchor_ns_;
        anchor_ns_ = anchor;  // siempre: el epoch derivado sigue al reloj de pared
        if (std::fabs(static_cast<double>(delta)) > p_.step_threshold_s * 1e9) {
            ev.stepped = true;
            ev.step_delta_s = static_cast<double>(delta) / 1e9;
            last_step_mono_ns_ = r.mono_ns;
            ever_stepped_ = true;
        }
        const uint64_t draw = r.raw_ns - win_raw0_;
        if (static_cast<double>(draw) >= p_.slew_window_s * 1e9) {
            const double dm = static_cast<double>(r.mono_ns - win_mono0_);
            ev.slew_measured = true;
            ev.slew_ppm = (dm / static_cast<double>(draw) - 1.0) * 1e6;
            last_ppm_ = ev.slew_ppm;
            const bool s = std::fabs(ev.slew_ppm) > p_.slew_ppm_threshold;
            ev.slewing_changed = (s != slewing_);
            slewing_ = s;
            win_mono0_ = r.mono_ns;
            win_raw0_ = r.raw_ns;
        }
        return ev;
    }

    // Prioridad: SLEWING (afecta a las duraciones) > STEPPED (afecta al epoch) > OK.
    ClockState state_at(uint64_t mono_ns) const noexcept {
        if (slewing_) return ClockState::Slewing;
        if (ever_stepped_ && mono_ns >= last_step_mono_ns_ &&
            static_cast<double>(mono_ns - last_step_mono_ns_) < p_.stepped_recent_s * 1e9) {
            return ClockState::Stepped;
        }
        return ClockState::Ok;
    }

    int64_t anchor_ns() const noexcept { return anchor_ns_; }
    bool slewing() const noexcept { return slewing_; }
    double last_ppm() const noexcept { return last_ppm_; }
    const TimebaseParams& params() const noexcept { return p_; }

private:
    TimebaseParams p_;
    bool init_ = false;
    int64_t anchor_ns_ = 0;
    uint64_t win_mono0_ = 0;
    uint64_t win_raw0_ = 0;
    bool slewing_ = false;
    double last_ppm_ = 0.0;
    bool ever_stepped_ = false;
    uint64_t last_step_mono_ns_ = 0;
};

}  // namespace argus::timebase
