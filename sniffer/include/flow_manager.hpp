// sniffer/include/flow_manager.hpp
// Define FlowStatistics: lo que el sniffer acumula por flujo para extraer rasgos. La tabla que lo guarda
// es flow/sharded_flow_manager.hpp; FlowKey esta en flow_tracker.hpp. [DAY307] la clase FlowManager que
// vivia aqui no la usaba nadie y se borro (la historia de git la conserva). [D308-PASO1] estadisticos
// incrementales de tamano fijo en lugar de un vector por paquete.
#pragma once

#include "main.h"
#include "flow_tracker.hpp"
#include <unordered_map>
#include <vector>
#include <map>  // [DDOS-SNAP-D290]
#include <mutex>
#include <memory>
#include <chrono>
#include <functional>

namespace sniffer {

// [D308-PASO1] Estadisticos incrementales de tamano fijo: el estado de un flujo ya no crece con sus paquetes.
// Las sumas son enteras y exactas; las varianzas se evaluan al leer (ml_defender_features.cpp).
// Cotas (sin desbordamiento posible dentro de las hipotesis que el codigo ya hacia):
//   longitudes: packet_len es uint32_t -> x^2 < 2^64 -> sum_sq < 2^128 con menos de 2^64 paquetes.
//   IAT: la suma de pares validos cabe en uint64_t (como antes); como todo iat >= 0,
//        sum_sq <= (sum)^2 < 2^128.
__extension__ using u128 = unsigned __int128;  // __extension__: -Wpedantic no admite __int128 sin el

// Longitudes de una serie (todas, ida, vuelta). La suma vive fuera: sbytes, dbytes y sbytes + dbytes.
struct LenAcc {
    uint32_t min = UINT32_MAX;
    uint32_t max = 0;
    u128 sum_sq = 0;

    void add(uint32_t x) {
        if (x < min) min = x;
        if (x > max) max = x;
        sum_sq += static_cast<u128>(x) * x;
    }
};

// Tiempos entre llegadas de una serie de marcas en orden de llegada. Par valido: la marca nueva es >= la
// anterior EN LLEGADA (no la maxima); la anterior se actualiza siempre, sea el par valido o no. Es la regla
// del recorrido timestamps[i] >= timestamps[i-1] que hacia ml_defender_features.cpp sobre los vectores.
// El numero de marcas de la serie no se guarda: es spkts + dpkts, spkts o dpkts.
struct IatAcc {
    uint64_t last_ts = 0;
    uint64_t pairs = 0;        // pares validos
    uint64_t sum = 0;          // suma de los iat de los pares validos
    uint64_t min = UINT64_MAX;
    uint64_t max = 0;
    u128 sum_sq = 0;

    // marcas_previas: cuantas marcas tenia ya la serie antes de esta
    void add(uint64_t ts, uint64_t marcas_previas) {
        if (marcas_previas > 0 && ts >= last_ts) {
            const uint64_t iat = ts - last_ts;
            ++pairs;
            sum += iat;
            if (iat < min) min = iat;
            if (iat > max) max = iat;
            sum_sq += static_cast<u128>(iat) * iat;
        }
        last_ts = ts;
    }
};

// Nucleo del flujo: todo lo que leen los rasgos, de tamano fijo y copiable de una vez (la copia por evento
// de ShardedFlowManager::get_flow_stats_copy es O(1) y no se pierde ningun campo al anadir uno nuevo).
struct FlowStatsCore {
    // ============ TIMING ============
    uint64_t flow_start_ns = 0;
    uint64_t flow_last_seen_ns = 0;

    // ============ PACKET COUNTERS ============
    uint64_t spkts = 0;  // Forward packets (source -> destination)
    uint64_t dpkts = 0;  // Backward packets (destination -> source)

    // ============ BYTE COUNTERS ============
    uint64_t sbytes = 0;  // Forward bytes (= suma de longitudes de ida)
    uint64_t dbytes = 0;  // Backward bytes (= suma de longitudes de vuelta)

    // ============ PACKET LENGTHS ============
    LenAcc len_all;
    LenAcc len_fwd;
    LenAcc len_bwd;

    // ============ INTER-ARRIVAL TIMES ============
    IatAcc iat_all;
    IatAcc iat_fwd;
    IatAcc iat_bwd;

    // ============ TCP FLAGS COUNTERS ============
    uint32_t fin_count = 0;
    uint32_t syn_count = 0;
    uint32_t rst_count = 0;
    uint32_t psh_count = 0;
    uint32_t ack_count = 0;
    uint32_t urg_count = 0;
    uint32_t ece_count = 0;
    uint32_t cwr_count = 0;

    // ============ DIRECTIONAL TCP FLAGS ============
    uint32_t fwd_psh_flags = 0;
    uint32_t bwd_psh_flags = 0;
    uint32_t fwd_urg_flags = 0;
    uint32_t bwd_urg_flags = 0;

    // ============ HEADER LENGTHS ============
    uint64_t fwd_header_sum = 0;  // la cuenta es spkts
    uint64_t bwd_header_sum = 0;  // la cuenta es dpkts

    // Determines if packet is forward direction
    bool is_forward(const SimpleEvent& pkt, const FlowKey& flow_key) const {
        return pkt.src_ip == flow_key.src_ip &&
               pkt.dst_ip == flow_key.dst_ip &&
               pkt.src_port == flow_key.src_port &&
               pkt.dst_port == flow_key.dst_port;
    }

    // Add packet to flow statistics (O(1))
    void add_packet(const SimpleEvent& pkt, const FlowKey& flow_key) {
        const uint64_t previos = spkts + dpkts;
        // Initialize timestamps on first packet
        if (previos == 0) {
            flow_start_ns = pkt.timestamp;
        }
        flow_last_seen_ns = pkt.timestamp;

        const uint16_t total_header = pkt.ip_header_len + pkt.l4_header_len;

        // Direction-specific counters
        if (is_forward(pkt, flow_key)) {
            iat_fwd.add(pkt.timestamp, spkts);
            spkts++;
            sbytes += pkt.packet_len;
            len_fwd.add(pkt.packet_len);
            fwd_header_sum += total_header;

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) fwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) fwd_urg_flags++;

        } else {
            iat_bwd.add(pkt.timestamp, dpkts);
            dpkts++;
            dbytes += pkt.packet_len;
            len_bwd.add(pkt.packet_len);
            bwd_header_sum += total_header;

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) bwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) bwd_urg_flags++;
        }

        // Overall statistics
        len_all.add(pkt.packet_len);
        iat_all.add(pkt.timestamp, previos);

        // TCP flags totals
        if (pkt.protocol == 6) {  // TCP only
            if (has_tcp_flag(pkt, TCP_FLAG_FIN)) fin_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_SYN)) syn_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_RST)) rst_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) psh_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ACK)) ack_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) urg_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ECE)) ece_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_CWR)) cwr_count++;
        }
    }

    // Get flow duration in microseconds
    uint64_t get_duration_us() const {
        if (flow_last_seen_ns <= flow_start_ns) return 0;
        return (flow_last_seen_ns - flow_start_ns) / 1000ULL;
    }

    // Get total packets
    uint64_t get_total_packets() const {
        return spkts + dpkts;
    }

    // Get total bytes
    uint64_t get_total_bytes() const {
        return sbytes + dbytes;
    }

    // Check if flow should expire (inactive for timeout period)
    bool should_expire(uint64_t current_ns, uint64_t timeout_ns) const {
        return (current_ns - flow_last_seen_ns) > timeout_ns;
    }

    // Check if flow is TCP
    bool is_tcp() const {
        return fin_count > 0 || syn_count > 0 || rst_count > 0 ||
               psh_count > 0 || ack_count > 0 || urg_count > 0;
    }

    // Check if TCP connection is closed (FIN or RST seen)
    bool is_tcp_closed() const {
        return fin_count > 0 || rst_count > 0;
    }
};

// Lo que guarda la tabla por flujo: el nucleo mas el histograma de longitudes, que solo lee la foto DDoS v2
// dentro del lock (ddos_v2_flow_snapshot). El histograma NO viaja en la copia por evento [D308-PASO1, D1]:
// las dos entropias de populate reciben la de la foto, que es el mismo numero.
struct FlowStatistics : FlowStatsCore {
    // [DDOS-SNAP-D290] histograma ordenado de longitudes (entropia identica a recorrer un std::map por valor
    // ascendente). Crece con las longitudes distintas del flujo, no con sus paquetes.
    std::map<uint32_t, uint32_t> len_hist;

    void add_packet(const SimpleEvent& pkt, const FlowKey& flow_key) {
        FlowStatsCore::add_packet(pkt, flow_key);
        ++len_hist[static_cast<uint32_t>(pkt.packet_len)];
    }
};

} // namespace sniffer