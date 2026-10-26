// DAY308 — coste de la limpieza por inactividad de la tabla de flujos (ShardedFlowManager::cleanup_expired_flows).
// SOLO MEDIDA: enlaza el ShardedFlowManager real. Antes del paso 2 la limpieza recorre todos los flujos y borra
// cada caducado de la LRU con list::remove (O(n) por borrado); despues, desde la cola de la LRU, O(caducados).
//
// Llena la tabla (SHARDS x MAX_POR_SHARD flujos de 1 paquete, marca base + i us) y mide tres pasadas sobre la
// MISMA tabla, con la hora elegida para caducar un numero conocido de flujos (los mas antiguos):
//   A) ninguno caducado (REPS pasadas, media por pasada)
//   B) el 10 % caducado
//   C) el resto (90 %)
// Inactividad de la tabla: 120 s (fijo en el instrumento; no es el defecto del sniffer).
// Compila contra el codigo desde el paso 2 de DAY308 (Config con idle_timeout_ns). El "antes" (limpieza O(n^2))
// se midio con la version de este instrumento anterior al paso 2 (sha256 bb71f4c8...), que elegia el API con
// -DD308_PASO2.
// Uso: d308_limpieza SHARDS MAX_POR_SHARD REPS. Salida por stdout (escribir en /tmp, nunca en /vagrant).
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "main.h"

#include <chrono>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

using namespace sniffer;
using namespace sniffer::flow;
using reloj = std::chrono::steady_clock;

static bool entero(const char* s, unsigned long long lo, unsigned long long hi, unsigned long long& v) {
    char* fin = nullptr;
    v = std::strtoull(s, &fin, 10);
    return s[0] && !*fin && v >= lo && v <= hi;
}

int main(int argc, char** argv) {
    unsigned long long shards, por_shard, reps;
    if (argc != 4 || !entero(argv[1], 1, 256, shards) || !entero(argv[2], 1, 1'000'000, por_shard) ||
        !entero(argv[3], 1, 1'000'000, reps)) {
        std::fprintf(stderr, "uso: d308_limpieza SHARDS(1..256) MAX_POR_SHARD(1..1e6) REPS(1..1e6)\n");
        return 2;
    }
    constexpr uint64_t kIdle = 120'000'000'000ULL;
    constexpr uint64_t kBase = 1'000'000'000'000ULL;
    constexpr uint64_t kPaso = 1'000ULL;  // 1 us entre flujos
    auto& mgr = ShardedFlowManager::instance();
    mgr.initialize(ShardedFlowManager::Config{.shard_count = (size_t)shards, .max_flows_per_shard = (size_t)por_shard,
                                              .idle_timeout_ns = kIdle, .active_timeout_ns = 0});
    // Se llena a la mitad de la capacidad para que la LRU no desaloje nada (un shard puede recibir mas flujos que
    // otros: el reparto lo decide el hash).
    const uint64_t n = shards * por_shard / 2;
    for (uint64_t i = 0; i < n; ++i) {
        const FlowKey k{.src_ip = 0x0A000000u | (uint32_t)(i & 0xFFFFFF), .dst_ip = 0x0A800001,
                        .src_port = (uint16_t)(1024 + (i >> 24)), .dst_port = 53, .protocol = 17};
        SimpleEvent e{};
        e.src_ip = k.src_ip;
        e.dst_ip = k.dst_ip;
        e.src_port = k.src_port;
        e.dst_port = k.dst_port;
        e.protocol = 17;
        e.packet_len = 90;
        e.ip_header_len = 20;
        e.l4_header_len = 8;
        e.timestamp = kBase + i * kPaso;
        mgr.add_packet(k, e);
    }
    std::printf("# shards=%llu max_por_shard=%llu flujos=%" PRIu64 " idle_s=120 reps_A=%llu\n", shards, por_shard, n,
                reps);
    // hora que caduca exactamente los flujos i < m: now - (kBase + i*kPaso) > kIdle  <=>  i < m
    auto hora_para = [&](uint64_t m) { return kBase + kIdle + m * kPaso; };

    // A) ninguno caducado
    {
        size_t borrados = 0;
        const auto t0 = reloj::now();
        for (unsigned long long r = 0; r < reps; ++r) borrados += mgr.cleanup_expired_flows(hora_para(0));
        const double us = std::chrono::duration<double, std::micro>(reloj::now() - t0).count();
        std::printf("A_ninguno: caducados=%zu us_por_pasada=%.2f\n", borrados, us / (double)reps);
    }
    // B) el 10 % mas antiguo
    const uint64_t m10 = n / 10;
    {
        const auto t0 = reloj::now();
        const size_t borrados = mgr.cleanup_expired_flows(hora_para(m10));
        const double ms = std::chrono::duration<double, std::milli>(reloj::now() - t0).count();
        std::printf("B_10pc: esperados=%" PRIu64 " caducados=%zu ms=%.3f\n", m10, borrados, ms);
    }
    // C) el resto
    {
        const auto t0 = reloj::now();
        const size_t borrados = mgr.cleanup_expired_flows(hora_para(n));
        const double ms = std::chrono::duration<double, std::milli>(reloj::now() - t0).count();
        std::printf("C_resto: esperados=%" PRIu64 " caducados=%zu ms=%.3f\n", n - m10, borrados, ms);
    }
    return 0;
}
