// sniffer/include/ddos_victim_board.hpp
// DAY279 -- tablero compartido de ventanas por victima (agregador DDoS en-kernel).
//
// El lector (DdosKernelReader) PUBLICA un snapshot por ventana; el RingBufferConsumer
// CONSULTA al construir cada NetworkSecurityEvent (campo victim_window). Lector y consumer
// no se conocen: comparten un shared_ptr<DdosVictimBoard> creado en main, asi que el orden
// de destruccion (lector antes que consumer) no deja punteros colgantes.
//
// Semantica (contrato DAY279):
//   - Sin snapshot publicado      -> lookup().have_snapshot = false (evento SIN victim_window).
//   - Snapshot y victima ausente  -> have_snapshot = true, d_pkts = d_bytes = 0.
//   - El snapshot guarda TODAS las victimas de la ventana (el tope kDdosMaxRowsPerWindow
//     es solo del CSV). La baseline (t_start_ns == 0) NO se publica: no es una tasa.
//   - Snapshot inmutable: quien tenga un shared_ptr viejo lo sigue leyendo entero.
#pragma once

#include "ddos_kernel_agg.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace sniffer {

struct DdosVictimCounts {
    uint64_t d_pkts = 0;
    uint64_t d_bytes = 0;
};

struct DdosVictimSnapshot {
    uint64_t seq = 0;           // n de ventana del lector
    uint64_t window_ms = 0;     // duracion real de la ventana
    uint64_t published_ns = 0;  // steady_clock en la publicacion
    std::unordered_map<uint64_t, DdosVictimCounts> by_key;
};

struct DdosVictimLookup {
    bool have_snapshot = false;
    uint64_t seq = 0;
    uint64_t window_ms = 0;
    uint64_t d_pkts = 0;
    uint64_t d_bytes = 0;
    uint64_t age_ms = 0;  // edad del snapshot al consultar
};

// Misma clave que el kernel: dst_ip NUMERICO (a<<24|b<<16|c<<8|d) + proto IANA.
inline uint64_t ddos_victim_key(uint32_t dst_ip, uint32_t proto) {
    return (static_cast<uint64_t>(dst_ip) << 32) | static_cast<uint64_t>(proto);
}

inline uint64_t ddos_steady_now_ns() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                     std::chrono::steady_clock::now().time_since_epoch())
                                     .count());
}

class DdosVictimBoard {
public:
    void publish(std::shared_ptr<const DdosVictimSnapshot> s) {
        std::lock_guard<std::mutex> lk(m_);
        snap_ = std::move(s);
        published_.fetch_add(1, std::memory_order_relaxed);
    }

    void publish_window(uint64_t seq, const DdosWindow& w, uint64_t now_ns = ddos_steady_now_ns()) {
        auto s = std::make_shared<DdosVictimSnapshot>();
        s->seq = seq;
        s->window_ms = (w.t_end_ns > w.t_start_ns) ? (w.t_end_ns - w.t_start_ns) / 1'000'000ULL : 0;
        s->published_ns = now_ns;
        s->by_key.reserve(w.victims.size());
        for (const auto& v : w.victims) {
            s->by_key[ddos_victim_key(v.dst_ip, v.proto)] = DdosVictimCounts{v.d_pkts, v.d_bytes};
        }
        publish(std::move(s));
    }

    std::shared_ptr<const DdosVictimSnapshot> load() const {
        std::lock_guard<std::mutex> lk(m_);
        return snap_;
    }

    DdosVictimLookup lookup(uint32_t dst_ip, uint32_t proto,
                            uint64_t now_ns = ddos_steady_now_ns()) const {
        DdosVictimLookup r;
        const std::shared_ptr<const DdosVictimSnapshot> s = load();
        if (!s) return r;
        r.have_snapshot = true;
        r.seq = s->seq;
        r.window_ms = s->window_ms;
        r.age_ms = (now_ns >= s->published_ns) ? (now_ns - s->published_ns) / 1'000'000ULL : 0;
        const auto it = s->by_key.find(ddos_victim_key(dst_ip, proto));
        if (it != s->by_key.end()) {
            r.d_pkts = it->second.d_pkts;
            r.d_bytes = it->second.d_bytes;
        }
        return r;
    }

    uint64_t published() const { return published_.load(std::memory_order_relaxed); }

private:
    mutable std::mutex m_;
    std::shared_ptr<const DdosVictimSnapshot> snap_;
    std::atomic<uint64_t> published_{0};
};

}  // namespace sniffer
