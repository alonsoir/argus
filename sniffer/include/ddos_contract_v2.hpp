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

}  // namespace argus::ddos
