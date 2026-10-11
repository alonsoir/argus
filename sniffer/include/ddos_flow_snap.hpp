// sniffer/include/ddos_flow_snap.hpp
// [DDOS-SNAP-D290] Foto de los rasgos DDoS v2 que dependen del estado del flujo, tomada en el
// hilo del anillo justo despues de add_packet (instante del paquete). La rellena
// MLDefenderExtractor::ddos_v2_flow_snapshot con las MISMAS formulas que la extraccion de lote.
// valid=false: el flujo no estaba en la tabla al tomar la foto (populate escribe centinelas).
#pragma once

namespace sniffer {

struct DdosFlowSnap {
    bool  valid = false;
    float syn_ack_ratio = 0.0f;
    float flow_completion_rate = 0.0f;
    float flow_packet_count = 0.0f;
    float mean_packet_size = 0.0f;
    float packet_size_entropy = 0.0f;
};

}  // namespace sniffer
