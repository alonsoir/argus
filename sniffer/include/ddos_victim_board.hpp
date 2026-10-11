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
#include "ddos_contract_v2.hpp"  // [DDOS-H2-D286]

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
    float rate_ratio = 0.0f;  // [DDOS-H2-D286] escalada; 0 si ventana degenerada
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
    float rate_ratio = 0.0f;  // [DDOS-H2-D286]
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
        s->window_ms = ddos_window_ms(w);  // [DDOS-WMS-D286] definicion unica (redondeo), la misma que el CSV
        s->published_ns = now_ns;
        s->by_key.reserve(w.victims.size());
        for (const auto& v : w.victims) {
            const uint64_t key = ddos_victim_key(v.dst_ip, v.proto);
            float ratio = 0.0f;  // [DDOS-H2-D286] solo con ventana de duracion > 0
            if (s->window_ms > 0) {
                const double pps = static_cast<double>(v.d_pkts) * 1000.0 / static_cast<double>(s->window_ms);
                ratio = static_cast<float>(::argus::ddos::victim_ewma_step(ewma_[key], seq, pps, ewma_params_));
            }
            s->by_key[key] = DdosVictimCounts{v.d_pkts, v.d_bytes, ratio};
        }
        if (seq % 60 == 0) evict_stale_ewma(seq);  // [DDOS-H2-D286] memoria acotada
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
            r.rate_ratio = it->second.rate_ratio;  // [DDOS-H2-D286]
        }
        return r;
    }

    uint64_t published() const { return published_.load(std::memory_order_relaxed); }

    // [DDOS-HYST-D291] parametros de la EWMA por victima (de sniffer.json, ya validados).
    // Llamar ANTES de arrancar el lector: publish_window (escritor unico) es quien los lee.
    void set_ewma_params(const ::argus::ddos::VictimEwmaParams& p) { ewma_params_ = p; }
    const ::argus::ddos::VictimEwmaParams& ewma_params() const { return ewma_params_; }

private:
    mutable std::mutex m_;
    std::shared_ptr<const DdosVictimSnapshot> snap_;
    std::atomic<uint64_t> published_{0};
    // [DDOS-H2-D286] estado de la EWMA por victima. SOLO lo toca el hilo que llama a
    // publish_window (el lector del kernel, escritor unico): sin cerrojo propio.
    std::unordered_map<uint64_t, ::argus::ddos::VictimEwmaState> ewma_;
    ::argus::ddos::VictimEwmaParams ewma_params_{};  // [DDOS-HYST-D291]
    void evict_stale_ewma(uint64_t seq) {
        for (auto it = ewma_.begin(); it != ewma_.end();) {
            if (seq > it->second.last_seq + ewma_params_.evict_windows) it = ewma_.erase(it);
            else ++it;
        }
    }
};

}  // namespace sniffer
