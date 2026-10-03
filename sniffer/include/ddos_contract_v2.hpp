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
// Medida offline DAY286 (v4, opcion B) sobre ddos_windows.csv: dos alfas para que un
// ataque no envenene la linea base sin dejar falsos positivos permanentes.
inline constexpr double kVictimEwmaAlpha = 0.1;                      // por ventana
inline constexpr double kVictimEwmaAlphaAnom = kVictimEwmaAlpha / 60.0;  // clave caliente y anomala
inline constexpr double kVictimRatioHot = 5.0;                       // K
inline constexpr uint64_t kVictimWarmWindows = 30;                   // W: ventanas vistas
inline constexpr double kVictimPpsFloor = 10.0;                      // suelo, pps
inline constexpr uint64_t kVictimEvictWindows = 3600;                // 1 h sin aparecer -> se olvida

struct VictimEwmaState {
    double ewma = 0.0;
    uint64_t last_seq = 0;
    uint64_t seen = 0;  // ventanas en que la victima aparecio (delta > 0)
};

// Un paso por ventana en que la victima aparece. Las ventanas sin trafico entre medias
// cuentan como 0 (decaen con alpha). Devuelve el ratio de ESTA ventana contra la EWMA previa.
inline double victim_ewma_step(VictimEwmaState& s, uint64_t seq, double pps) noexcept {
    double prior = 0.0;
    if (s.seen > 0) {
        const uint64_t gap = (seq > s.last_seq) ? (seq - s.last_seq) : 1;
        if (gap <= kVictimEvictWindows) {
            prior = s.ewma;
            for (uint64_t i = 1; i < gap; ++i) prior *= (1.0 - kVictimEwmaAlpha);
        }
    }
    const double ratio = pps / (prior > kVictimPpsFloor ? prior : kVictimPpsFloor);
    const bool hot = s.seen >= kVictimWarmWindows && ratio >= kVictimRatioHot;
    const double a = hot ? kVictimEwmaAlphaAnom : kVictimEwmaAlpha;
    s.ewma = (1.0 - a) * prior + a * pps;
    s.last_seq = seq;
    s.seen += 1;
    return ratio;
}

}  // namespace argus::ddos
