// sniffer/include/ddos_contract_v2.hpp
// [DDOS-V2-D286] Contrato DDoS v2: funciones puras, sin dependencias.
// Rasgos que dependen del paquete o de la ventana del kernel (no de FlowStatistics).
#pragma once
#include <cstdint>

namespace argus::ddos {

// Puertos de servicio UDP explotados en reflexion/amplificacion.
inline constexpr bool is_reflection_service_port(uint16_t p) noexcept {
    switch (p) {
        case 17: case 19: case 53: case 69: case 111: case 123: case 137: case 138:
        case 161: case 389: case 1434: case 1900: case 3702: case 5683: case 11211:
            return true;
        default:
            return false;
    }
}

// 1 si el paquete es UDP desde un puerto de servicio reflejable hacia un puerto alto.
inline constexpr float reflection_signature(uint8_t proto, uint16_t sport, uint16_t dport) noexcept {
    return (proto == 17 && is_reflection_service_port(sport) && dport >= 1024) ? 1.0f : 0.0f;
}

// Paquetes por segundo de la victima en la ventana del kernel. window_ms debe ser > 0.
inline constexpr float victim_pps(uint64_t d_pkts, uint64_t window_ms) noexcept {
    return static_cast<float>(static_cast<double>(d_pkts) * 1000.0 / static_cast<double>(window_ms));
}

// Tests en compilacion.
static_assert(reflection_signature(17, 53, 40000) == 1.0f, "DNS reflejado");
static_assert(reflection_signature(17, 123, 1024) == 1.0f, "NTP reflejado, limite 1024");
static_assert(reflection_signature(17, 40000, 53) == 0.0f, "consulta DNS legitima");
static_assert(reflection_signature(6, 53, 40000) == 0.0f, "TCP no cuenta");
static_assert(reflection_signature(17, 53, 1023) == 0.0f, "destino no alto");
static_assert(reflection_signature(17, 8080, 40000) == 0.0f, "puerto no reflejable");
static_assert(victim_pps(100, 1000) == 100.0f, "100 pkts en 1 s");
static_assert(victim_pps(50, 500) == 100.0f, "50 pkts en 0,5 s");

// [DDOS-H2-D286] H2: escalada por victima = pps_ventana / max(EWMA previa, suelo).
// [DDOS-HYST-D291] Histeresis: estado bajo_presion por victima. Entra con ratio >= k_in
// (solo clave caliente), sale con ratio < k_out; dentro, la EWMA aprende con alfa lento =
// (intervalo/1000)/tau_s (tiempo de absorcion). Medido DAY291: sin histeresis un flood de 7x
// desaparecia en ~5 s por UNA ventana de jitter (ratio 4,95 < 5). Offline (18 dias, 83
// arranques): k_in=3, k_out=1,5, tau=3600 s sostienen 30 y 60 pps los 90 s y cuestan 33
// episodios de ambiente (max 10 s). Los valores vivos vienen de sniffer.json; estos son los
// DEFECTOS validados, que se usan con aviso [CONFIG-DEFAULT] si el JSON falta o es invalido.
struct VictimEwmaParams {
    double alpha = 0.1;             // por ventana, fuera de bajo_presion
    double tau_s = 3600.0;          // tiempo de absorcion dentro de bajo_presion (s)
    double k_in = 3.0;              // entra con ratio >= k_in
    double k_out = 1.5;             // sale con ratio < k_out
    uint64_t warm_windows = 30;     // ventanas vistas para poder entrar (clave caliente)
    double floor_pps = 10.0;        // suelo del denominador
    uint64_t evict_windows = 3600;  // ventanas sin aparecer -> la clave se olvida
    double interval_ms = 1000.0;    // ventana nominal del lector (ddos_kernel_agg_interval_ms)
    double alpha_slow() const noexcept { return (interval_ms / 1000.0) / tau_s; }
};

// Rangos aceptados (inclusive). Documentados tambien en sniffer.json.
inline constexpr double kVictimEwmaAlphaMin = 0.001, kVictimEwmaAlphaMax = 1.0;
inline constexpr double kVictimEwmaTauMin = 60.0, kVictimEwmaTauMax = 86400.0;
inline constexpr double kVictimEwmaKInMin = 1.1, kVictimEwmaKInMax = 100.0;
inline constexpr double kVictimEwmaKOutMin = 1.0, kVictimEwmaKOutMax = 99.0;
inline constexpr double kVictimEwmaWarmMin = 0.0, kVictimEwmaWarmMax = 3600.0;
inline constexpr double kVictimEwmaFloorMin = 0.1, kVictimEwmaFloorMax = 1.0e6;
inline constexpr double kVictimEwmaEvictMin = 60.0, kVictimEwmaEvictMax = 86400.0;

inline bool victim_ewma_in_range(double x, double lo, double hi) noexcept { return x >= lo && x <= hi; }

// Validacion completa: rangos + reglas cruzadas (k_out < k_in; alfa lento < alfa).
inline bool victim_ewma_params_ok(const VictimEwmaParams& p) noexcept {
    return victim_ewma_in_range(p.alpha, kVictimEwmaAlphaMin, kVictimEwmaAlphaMax) &&
           victim_ewma_in_range(p.tau_s, kVictimEwmaTauMin, kVictimEwmaTauMax) &&
           victim_ewma_in_range(p.k_in, kVictimEwmaKInMin, kVictimEwmaKInMax) &&
           victim_ewma_in_range(p.k_out, kVictimEwmaKOutMin, kVictimEwmaKOutMax) &&
           victim_ewma_in_range(static_cast<double>(p.warm_windows), kVictimEwmaWarmMin, kVictimEwmaWarmMax) &&
           victim_ewma_in_range(p.floor_pps, kVictimEwmaFloorMin, kVictimEwmaFloorMax) &&
           victim_ewma_in_range(static_cast<double>(p.evict_windows), kVictimEwmaEvictMin, kVictimEwmaEvictMax) &&
           p.interval_ms > 0.0 && p.k_out < p.k_in && p.alpha_slow() < p.alpha;
}

struct VictimEwmaState {
    double ewma = 0.0;
    uint64_t last_seq = 0;
    uint64_t seen = 0;          // ventanas en que la victima aparecio (delta > 0)
    bool bajo_presion = false;  // [DDOS-HYST-D291]
};

// Un paso por ventana en que la victima aparece. Las ventanas sin trafico entre medias
// cuentan como 0 (decaen con alpha). Devuelve el ratio de ESTA ventana contra la EWMA previa.
// Si la clave reaparece tras mas de evict_windows, empieza de cero (igual que el arnes offline).
inline double victim_ewma_step(VictimEwmaState& s, uint64_t seq, double pps,
                               const VictimEwmaParams& p) noexcept {
    if (s.seen > 0 && seq > s.last_seq && seq - s.last_seq > p.evict_windows) s = VictimEwmaState{};
    double prior = 0.0;
    if (s.seen > 0) {
        const uint64_t gap = (seq > s.last_seq) ? (seq - s.last_seq) : 1;
        prior = s.ewma;
        for (uint64_t i = 1; i < gap; ++i) prior *= (1.0 - p.alpha);
    }
    const double ratio = pps / (prior > p.floor_pps ? prior : p.floor_pps);
    if (!s.bajo_presion && s.seen >= p.warm_windows && ratio >= p.k_in) s.bajo_presion = true;
    else if (s.bajo_presion && ratio < p.k_out) s.bajo_presion = false;
    const double a = s.bajo_presion ? p.alpha_slow() : p.alpha;
    s.ewma = (1.0 - a) * prior + a * pps;
    s.last_seq = seq;
    s.seen += 1;
    return ratio;
}

}  // namespace argus::ddos
