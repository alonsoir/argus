// sniffer/include/ddos_kernel_agg.hpp
// DAY273 -- lector userspace del agregador DDoS en-kernel (mapa BPF `ddos_victims`).
//
// Contrato (decisiones (a)/(b)/(c) de DAY273, no re-litigar):
//   - El kernel cuenta MONOTONO por victima (dst_ip + proto): paquetes y bytes.
//   - Userspace lee cada T segundos; el DELTA entre dos lecturas = ventana tumbling.
//   - Cero logica de ventana / reset / float / division en el kernel.
//
// Header-only a proposito: no obliga a tocar CMakeLists. Necesita libbpf (ya enlazado).
//
// Byte order: `dst_ip` es el valor NUMERICO a<<24|b<<16|c<<8|d (identico a
// simple_event::dst_ip). ip_to_string() lo pinta con shifts, independiente del
// endianness del host: 0xC0A86401 -> "192.168.100.1".
//
// Requiere kernel >= 5.6 (bpf_map_lookup_batch sobre LRU_HASH). Defender = 6.1: ok.
#pragma once

#include <bpf/bpf.h>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace sniffer {

// Layout IDENTICO a `struct ddos_key` / `struct ddos_val` de sniffer.bpf.c.
struct DdosVictimKey {
    uint32_t dst_ip;
    uint32_t proto;
};
struct DdosVictimVal {
    uint64_t pkts;
    uint64_t bytes;
};
static_assert(sizeof(DdosVictimKey) == 8, "ddos_key debe medir 8 B (sin padding)");
static_assert(sizeof(DdosVictimVal) == 16, "ddos_val debe medir 16 B");

struct DdosVictimDelta {
    uint32_t dst_ip;
    uint32_t proto;
    uint64_t d_pkts;
    uint64_t d_bytes;
};

struct DdosWindow {
    uint64_t t_start_ns = 0;  // CLOCK_MONOTONIC de la lectura anterior (0 en la primera)
    uint64_t t_end_ns = 0;    // CLOCK_MONOTONIC de esta lectura
    std::vector<DdosVictimDelta> victims;  // solo delta > 0; d_pkts desc, luego dst_ip
    uint32_t counter_resets = 0;  // contador que RETROCEDIO: evict LRU + reinsercion
    uint32_t evicted = 0;         // estaban en la lectura anterior y ya no estan
};

class DdosKernelAggregator {
public:
    using Snapshot = std::unordered_map<uint64_t, DdosVictimVal>;

    // map_fd: fd del mapa `ddos_victims`. max_entries: el del mapa en el .bpf.c (65536);
    // el buffer de lectura se dimensiona con el, asi una sola llamada batch cubre todo.
    explicit DdosKernelAggregator(int map_fd, uint32_t max_entries = 65536)
        : fd_(map_fd), cap_(max_entries) {}

    static uint64_t pack(uint32_t dst_ip, uint32_t proto) {
        return (static_cast<uint64_t>(dst_ip) << 32) | proto;
    }

    static std::string ip_to_string(uint32_t v) {
        char buf[16];
        std::snprintf(buf, sizeof(buf), "%u.%u.%u.%u", (v >> 24) & 0xFF, (v >> 16) & 0xFF,
                      (v >> 8) & 0xFF, v & 0xFF);
        return buf;
    }

    // Delta respecto a la lectura anterior. La PRIMERA llamada devuelve todo lo contado
    // desde que se cargo el programa (baseline vacio): es lo correcto, no se pierde nada.
    // Si la lectura falla devuelve nullopt y NO avanza el baseline: el siguiente poll()
    // acumula el intervalo perdido en vez de descartarlo.
    std::optional<DdosWindow> poll() {
        auto snap = read_snapshot();
        if (!snap) return std::nullopt;
        DdosWindow w = compute_delta(prev_, *snap);
        const uint64_t now = now_ns();
        w.t_start_ns = last_ns_;
        w.t_end_ns = now;
        prev_ = std::move(*snap);
        last_ns_ = now;
        return w;
    }

    // Funcion PURA (testeable sin kernel).
    static DdosWindow compute_delta(const Snapshot& prev, const Snapshot& cur) {
        DdosWindow w;
        w.victims.reserve(cur.size());
        for (const auto& [k, c] : cur) {
            uint64_t dp = c.pkts, db = c.bytes;  // victima nueva: todo es delta
            auto it = prev.find(k);
            if (it != prev.end()) {
                if (c.pkts < it->second.pkts || c.bytes < it->second.bytes) {
                    // Evicted por LRU y reinsertada: el contador arranco de cero. Lo
                    // contado antes del desalojo y no leido es irrecuperable; el delta
                    // es lo acumulado desde la reinsercion.
                    ++w.counter_resets;
                } else {
                    dp = c.pkts - it->second.pkts;
                    db = c.bytes - it->second.bytes;
                }
            }
            if (dp != 0 || db != 0) {
                w.victims.push_back({static_cast<uint32_t>(k >> 32),
                                     static_cast<uint32_t>(k & 0xFFFFFFFFu), dp, db});
            }
        }
        for (const auto& [k, p] : prev) {
            (void)p;
            if (cur.find(k) == cur.end()) ++w.evicted;
        }
        std::sort(w.victims.begin(), w.victims.end(),
                  [](const DdosVictimDelta& a, const DdosVictimDelta& b) {
                      if (a.d_pkts != b.d_pkts) return a.d_pkts > b.d_pkts;
                      if (a.dst_ip != b.dst_ip) return a.dst_ip < b.dst_ip;
                      return a.proto < b.proto;
                  });
        return w;
    }

    // Snapshot completo del mapa con bpf_map_lookup_batch. Devuelve nullopt si falla.
    std::optional<Snapshot> read_snapshot() {
        if (fd_ < 0 || cap_ == 0) return std::nullopt;
        keys_.resize(cap_);
        vals_.resize(cap_);
        Snapshot snap;
        snap.reserve(1024);
        uint32_t in_batch = 0, out_batch = 0;  // token opaco; en hash maps es u32
        bool first = true;
        for (;;) {
            uint32_t count = cap_;
            int err = bpf_map_lookup_batch(fd_, first ? nullptr : &in_batch, &out_batch,
                                           keys_.data(), vals_.data(), &count, nullptr);
            for (uint32_t i = 0; i < count; ++i) {
                snap[pack(keys_[i].dst_ip, keys_[i].proto)] = vals_[i];
            }
            if (err == -ENOENT) break;  // recorrido completo (count = lo leido en esta pasada)
            if (err != 0) {
                last_errno_ = err < 0 ? -err : errno;
                return std::nullopt;
            }
            in_batch = out_batch;
            first = false;
        }
        return snap;
    }

    int last_errno() const { return last_errno_; }

private:
    static uint64_t now_ns() {
        timespec ts{};
        clock_gettime(CLOCK_MONOTONIC, &ts);
        return static_cast<uint64_t>(ts.tv_sec) * 1000000000ull + static_cast<uint64_t>(ts.tv_nsec);
    }

    int fd_;
    uint32_t cap_;
    int last_errno_ = 0;
    uint64_t last_ns_ = 0;
    Snapshot prev_;
    std::vector<DdosVictimKey> keys_;
    std::vector<DdosVictimVal> vals_;
};

}  // namespace sniffer