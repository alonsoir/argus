// [TIMEBASE-D295:TEST] Test de la logica pura del contrato temporal (timebase.hpp).
// Lecturas sinteticas con los numeros medidos DAY295: base -1876 ppm, correccion gradual
// +81300 ppm, saltos de +-5 s; mas una comprobacion con los relojes reales (C1).
#include "timebase.hpp"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

namespace tb = argus::timebase;

namespace {

int g_fails = 0;

void check(bool ok, const std::string& msg) {
    std::cout << (ok ? "[OK]   " : "[FAIL] ") << msg << "\n";
    if (!ok) ++g_fails;
}

constexpr int64_t kAnchor0 = 1791776000000000000LL;
constexpr uint64_t kSec = 1000000000ULL;
constexpr double kBasePpm = -1876.0;

// Avanza 1 s de MONOTONIC_RAW; MONOTONIC al ritmo (1 + ppm/1e6); REALTIME = ancla + MONOTONIC.
struct Sim {
    uint64_t raw = 5000 * kSec;
    uint64_t mono = 1000 * kSec;
    int64_t anchor = kAnchor0;
    tb::ClockReading now() const {
        tb::ClockReading c;
        c.real_ns = anchor + static_cast<int64_t>(mono);
        c.mono_ns = mono;
        c.raw_ns = raw;
        return c;
    }
    tb::ClockReading step(double ppm) {
        raw += kSec;
        mono += static_cast<uint64_t>(std::llround(1e9 * (1.0 + ppm * 1e-6)));
        return now();
    }
};

void test_reposo() {
    tb::TimebaseState s;
    Sim sim;
    s.update(sim.now());
    int steps = 0, measured = 0;
    bool ppm_ok = true, slewing = false;
    for (int i = 1; i <= 30; ++i) {
        const auto ev = s.update(sim.step(kBasePpm));
        if (ev.stepped) ++steps;
        if (ev.slew_measured) {
            ++measured;
            if (std::fabs(ev.slew_ppm - kBasePpm) > 1.0) ppm_ok = false;
        }
        if (s.slewing()) slewing = true;
    }
    check(steps == 0, "reposo: 0 saltos en 30 s");
    check(measured == 3, "reposo: 3 ventanas de 10 s medidas");
    check(ppm_ok, "reposo: ppm medido = -1876 +-1");
    check(!slewing, "reposo: nunca SLEWING con la deriva de base");
    check(s.state_at(sim.mono) == tb::ClockState::Ok, "reposo: estado OK");
    check(s.anchor_ns() == kAnchor0, "reposo: ancla sin cambios");
}

void test_salto(double delta_s, const std::string& tag) {
    tb::TimebaseState s;
    Sim sim;
    s.update(sim.now());
    for (int i = 1; i < 15; ++i) s.update(sim.step(kBasePpm));
    sim.anchor += static_cast<int64_t>(std::llround(delta_s * 1e9));
    const auto ev = s.update(sim.step(kBasePpm));
    check(ev.stepped, tag + ": salto detectado");
    check(std::fabs(ev.step_delta_s - delta_s) < 1e-6, tag + ": delta medido = " + std::to_string(ev.step_delta_s));
    check(s.anchor_ns() == sim.anchor, tag + ": ancla nueva");
    const uint64_t m = sim.mono;
    check(s.state_at(m + 30 * kSec) == tb::ClockState::Stepped, tag + ": STEPPED a +30 s");
    check(s.state_at(m + 61 * kSec) == tb::ClockState::Ok, tag + ": OK a +61 s");
    int extra = 0;
    for (int i = 0; i < 10; ++i) {
        if (s.update(sim.step(kBasePpm)).stepped) ++extra;
    }
    check(extra == 0, tag + ": ningun salto mas en los 10 s siguientes");
}

void test_correccion_gradual() {
    tb::TimebaseState s;
    Sim sim;
    s.update(sim.now());
    int steps = 0;
    bool on20 = false, ch20 = false, off50 = false, ch50 = false, slewing_state20 = false;
    double ppm20 = 0.0;
    for (int i = 1; i <= 50; ++i) {
        const double ppm = (i > 10 && i <= 40) ? 81300.0 : kBasePpm;
        const auto ev = s.update(sim.step(ppm));
        if (ev.stepped) ++steps;
        if (i == 20) {
            on20 = s.slewing();
            ch20 = ev.slewing_changed;
            ppm20 = ev.slew_ppm;
            slewing_state20 = (s.state_at(sim.mono) == tb::ClockState::Slewing);
        }
        if (i == 50) {
            off50 = !s.slewing();
            ch50 = ev.slewing_changed;
        }
    }
    check(steps == 0, "gradual: R-M no cambia, 0 saltos");
    check(on20 && ch20, "gradual: SLEWING al cerrar la ventana 10-20 s");
    check(std::fabs(ppm20 - 81300.0) < 1.0, "gradual: ppm medido = " + std::to_string(ppm20));
    check(slewing_state20, "gradual: estado SLEWING");
    check(off50 && ch50, "gradual: vuelve a OK al cerrar la ventana 40-50 s");
    check(s.state_at(sim.mono) == tb::ClockState::Ok, "gradual: estado OK al final");
}

void test_jitter() {
    tb::TimebaseState s;
    Sim sim;
    s.update(sim.now());
    for (int i = 1; i < 5; ++i) s.update(sim.step(kBasePpm));
    sim.anchor += 10000000LL;  // 0,01 s < step_threshold_s 0,05
    const auto ev = s.update(sim.step(kBasePpm));
    check(!ev.stepped, "jitter 0,01 s: no es salto");
    check(s.anchor_ns() == sim.anchor, "jitter 0,01 s: el ancla lo sigue");
}

void test_params() {
    tb::TimebaseParams p;
    check(tb::params_ok(p), "params: defectos validos");
    p.anchor_period_s = 2.0;
    p.slew_window_s = 1.0;
    check(!tb::params_ok(p), "params: slew_window_s < anchor_period_s rechazado");
    tb::TimebaseParams q;
    q.step_threshold_s = 0.0;
    check(!tb::params_ok(q), "params: step_threshold_s fuera de rango rechazado");
}

void test_relojes_reales() {
    const auto c = tb::read_clocks();
    check(c.real_ns > 0 && c.mono_ns > 0 && c.raw_ns > 0, "real: lecturas > 0");
    const int64_t a = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
    timespec t{};
    clock_gettime(CLOCK_MONOTONIC, &t);
    const int64_t b = static_cast<int64_t>(t.tv_sec) * 1000000000LL + static_cast<int64_t>(t.tv_nsec);
    check(std::llabs(b - a) < 1000000LL, "C1: steady_clock = CLOCK_MONOTONIC (dif < 1 ms)");
    const std::string id = tb::read_boot_id();
    check(id.size() == 36, "real: boot_id de 36 caracteres");
    std::cout << "       boot_id=" << id << " dif_steady_mono_ns=" << (b - a) << "\n";
}

}  // namespace

int main() {
    test_reposo();
    test_salto(5.0, "salto +5 s");
    test_salto(-5.0, "salto -5 s");
    test_correccion_gradual();
    test_jitter();
    test_params();
    test_relojes_reales();
    std::cout << (g_fails == 0 ? "TODOS OK" : "HAY FALLOS: " + std::to_string(g_fails)) << std::endl;
    return g_fails == 0 ? 0 : 1;
}
