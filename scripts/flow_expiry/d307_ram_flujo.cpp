// DAY307 — medida de RAM de la tabla de flujos del sniffer (DEBT-SNIFFER-FLOW-EXPIRY-001 /
// DEBT-SNIFFER-FLOWSTATS-UNBOUNDED-001). SOLO MEDIDA: no toca el repo, enlaza el ShardedFlowManager real.
//
// Fase A (coste fijo por flujo): CAP_TOTAL*2 flujos distintos de 1 paquete UDP; VmRSS cada PASO flujos.
//   Pendiente hasta CAP_TOTAL = bytes por flujo; despues de CAP_TOTAL la LRU desaloja y el RSS debe aplanarse.
// Fase B (coste por paquete de un flujo largo): 1 flujo, N paquetes; VmRSS y tiempo de get_flow_stats_copy
//   (la copia que ring_consumer.cpp:929 hace en CADA evento) cada PASO paquetes.
//
// Uso:
//   d307_ram_flujo A SHARDS MAX_POR_SHARD PASO
//   d307_ram_flujo B N_PAQUETES PASO
// Los tamanos de la tabla se pasan por argumento (en el sniffer vivo: 16 y 10000, ring_consumer.cpp:131-132).
// Salida: TSV por stdout, una cabecera "# ..." con los parametros efectivos.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "main.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

using namespace sniffer;
using namespace sniffer::flow;

static long vmrss_kb() {
    std::ifstream f("/proc/self/status");
    std::string k;
    long v = -1;
    while (f >> k) {
        if (k == "VmRSS:") { f >> v; return v; }
        std::string resto;
        std::getline(f, resto);
    }
    return v;
}

static uint64_t entero(const char* s, const char* nombre, uint64_t min, uint64_t max) {
    char* fin = nullptr;
    unsigned long long v = std::strtoull(s, &fin, 10);
    if (!s[0] || *fin || v < min || v > max) {
        std::fprintf(stderr, "ABORTA: %s='%s' fuera de [%llu, %llu] o no entero\n", nombre, s,
                     (unsigned long long)min, (unsigned long long)max);
        std::exit(2);
    }
    return v;
}

static SimpleEvent paquete(uint32_t src, uint32_t dst, uint16_t sp, uint16_t dp, uint64_t ts) {
    SimpleEvent e{};
    e.src_ip = src;
    e.dst_ip = dst;
    e.src_port = sp;
    e.dst_port = dp;
    e.protocol = 17;
    e.packet_len = 90;
    e.ip_header_len = 20;
    e.l4_header_len = 8;
    e.timestamp = ts;
    return e;
}

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "uso: A SHARDS MAX_POR_SHARD PASO | B N_PAQUETES PASO\n"); return 2; }
    std::string fase = argv[1];
    auto& mgr = ShardedFlowManager::instance();

    if (fase == "A" && argc == 5) {
        uint64_t shards = entero(argv[2], "SHARDS", 1, 1024);
        uint64_t max_ps = entero(argv[3], "MAX_POR_SHARD", 1, 10000000);
        uint64_t paso = entero(argv[4], "PASO", 1, 100000000);
        mgr.initialize(ShardedFlowManager::Config{.shard_count = shards, .max_flows_per_shard = max_ps,
                                                  .idle_timeout_ns = 120'000'000'000ULL});
        const uint64_t cap = shards * max_ps;
        const uint64_t total = cap * 2;
        long rss0 = vmrss_kb();
        std::printf("# fase=A shards=%llu max_por_shard=%llu cap=%llu total=%llu paso=%llu rss0_kb=%ld\n",
                    (unsigned long long)shards, (unsigned long long)max_ps, (unsigned long long)cap,
                    (unsigned long long)total, (unsigned long long)paso, rss0);
        std::printf("flujos\tvmrss_kb\tdelta_kb\tbytes_por_flujo\n");
        uint64_t ts = 1'000'000'000ULL;
        for (uint64_t i = 1; i <= total; ++i) {
            // tupla unica: src 10.x.y.z, sport y dport derivados de i (sin repetir hasta 2^40)
            uint32_t src = 0x0A000000u | static_cast<uint32_t>(i & 0x00FFFFFFu);
            uint16_t sp = static_cast<uint16_t>(1024 + ((i >> 24) & 0x3FFF));
            FlowKey k{.src_ip = src, .dst_ip = 0xC0A86401u, .src_port = sp, .dst_port = 53, .protocol = 17};
            mgr.add_packet(k, paquete(src, 0xC0A86401u, sp, 53, ts));
            ts += 1000;
            if (i % paso == 0 || i == total) {
                long r = vmrss_kb();
                uint64_t vivos = i < cap ? i : cap;
                std::printf("%llu\t%ld\t%ld\t%.1f\n", (unsigned long long)i, r, r - rss0,
                            (double)(r - rss0) * 1024.0 / (double)vivos);
                std::fflush(stdout);
            }
        }
        return 0;
    }

    if (fase == "B" && argc == 4) {
        uint64_t n = entero(argv[2], "N_PAQUETES", 1, 1'000'000'000ULL);
        uint64_t paso = entero(argv[3], "PASO", 1, 1'000'000'000ULL);
        mgr.initialize(ShardedFlowManager::Config{.shard_count = 16, .max_flows_per_shard = 10000,
                                                  .idle_timeout_ns = 120'000'000'000ULL});
        long rss0 = vmrss_kb();
        std::printf("# fase=B n=%llu paso=%llu rss0_kb=%ld (1 flujo UDP, 90 B, 1 paquete cada 10 ms)\n",
                    (unsigned long long)n, (unsigned long long)paso, rss0);
        std::printf("paquetes\tvmrss_kb\tdelta_kb\tbytes_por_paquete\tcopia_us\n");
        FlowKey k{.src_ip = 0xC0A86433u, .dst_ip = 0xC0A86401u, .src_port = 123, .dst_port = 123, .protocol = 17};
        uint64_t ts = 1'000'000'000ULL;
        for (uint64_t i = 1; i <= n; ++i) {
            mgr.add_packet(k, paquete(k.src_ip, k.dst_ip, 123, 123, ts));
            ts += 10'000'000ULL;
            if (i % paso == 0 || i == n) {
                long r = vmrss_kb();
                auto t0 = std::chrono::steady_clock::now();
                auto c = mgr.get_flow_stats_copy(k);
                auto t1 = std::chrono::steady_clock::now();
                if (!c || c->get_total_packets() != i) {
                    std::fprintf(stderr, "ABORTA: la copia no tiene %llu paquetes\n", (unsigned long long)i);
                    return 3;
                }
                double us = std::chrono::duration<double, std::micro>(t1 - t0).count();
                std::printf("%llu\t%ld\t%ld\t%.1f\t%.1f\n", (unsigned long long)i, r, r - rss0,
                            (double)(r - rss0) * 1024.0 / (double)i, us);
                std::fflush(stdout);
            }
        }
        return 0;
    }

    std::fprintf(stderr, "uso: A SHARDS MAX_POR_SHARD PASO | B N_PAQUETES PASO\n");
    return 2;
}
