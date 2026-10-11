// sniffer/tests/test_ddos_flow_snap.cpp
// [DDOS-SNAP-D290] La foto incremental de los rasgos DDoS v2 (ddos_v2_flow_snapshot, la que toma
// el hilo del anillo) tiene que dar EXACTAMENTE (bit a bit) lo mismo que la extraccion de lote de
// produccion (extract_ddos_features sobre la copia del flujo). Sin agregador: source_ip_dispersion
// sale como centinela y no interviene en lo que se compara.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "ml_defender_features.hpp"
#include "network_security.pb.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <random>

using namespace sniffer;
using namespace sniffer::flow;

namespace {

int g_fallos = 0;
int g_comparaciones = 0;

bool mismos_bits(float a, float b) { return std::memcmp(&a, &b, sizeof(float)) == 0; }

void comparar(const char* caso, const char* rasgo, float foto, float lote) {
    ++g_comparaciones;
    if (!mismos_bits(foto, lote)) {
        ++g_fallos;
        std::printf("FALLO %s / %s: foto=%a (%.9g) lote=%a (%.9g)\n", caso, rasgo,
                    static_cast<double>(foto), static_cast<double>(foto),
                    static_cast<double>(lote), static_cast<double>(lote));
    }
}

SimpleEvent paquete(const FlowKey& k, bool directo, uint32_t len, uint8_t flags, uint64_t ts) {
    SimpleEvent p{};
    p.src_ip = directo ? k.src_ip : k.dst_ip;
    p.dst_ip = directo ? k.dst_ip : k.src_ip;
    p.src_port = directo ? k.src_port : k.dst_port;
    p.dst_port = directo ? k.dst_port : k.src_port;
    p.protocol = k.protocol;
    p.tcp_flags = flags;
    p.packet_len = len;
    p.ip_header_len = 20;
    p.l4_header_len = (k.protocol == 6) ? 20 : 8;
    p.timestamp = ts;
    return p;
}

void verificar(const char* caso, const FlowKey& k) {
    auto& mgr = ShardedFlowManager::instance();
    MLDefenderExtractor ext;

    DdosFlowSnap foto{};
    mgr.with_flow_stats(k, [&](const auto& fs) { foto = ext.ddos_v2_flow_snapshot(fs); });

    auto copia = mgr.get_flow_stats_copy(k);
    ++g_comparaciones;
    if (!foto.valid || !copia.has_value()) {
        ++g_fallos;
        std::printf("FALLO %s: flujo ausente (foto.valid=%d copia=%d)\n", caso,
                    foto.valid ? 1 : 0, copia.has_value() ? 1 : 0);
        return;
    }
    const auto& f = copia.value();

    // Coherencia de los estadisticos incrementales con all_lengths (y de que la copia los arrastra)
    uint64_t suma = 0;
    std::map<uint32_t, uint32_t> hist;
    for (uint32_t v : f.all_lengths) { suma += v; ++hist[v]; }
    ++g_comparaciones;
    if (suma != f.sum_all_lengths || hist != f.len_hist ||
        static_cast<uint64_t>(f.all_lengths.size()) != f.get_total_packets()) {
        ++g_fallos;
        std::printf("FALLO %s: estadisticos incrementales incoherentes (suma %llu/%llu, hist %s, n %llu/%llu)\n",
                    caso, static_cast<unsigned long long>(suma),
                    static_cast<unsigned long long>(f.sum_all_lengths),
                    (hist == f.len_hist) ? "igual" : "DISTINTO",
                    static_cast<unsigned long long>(f.all_lengths.size()),
                    static_cast<unsigned long long>(f.get_total_packets()));
    }

    ::protobuf::DDoSFeatures lote;
    ext.extract_ddos_features(f, &lote);

    comparar(caso, "syn_ack_ratio", foto.syn_ack_ratio, lote.syn_ack_ratio());
    comparar(caso, "flow_completion_rate", foto.flow_completion_rate, lote.flow_completion_rate());
    comparar(caso, "flow_packet_count", foto.flow_packet_count, lote.flow_packet_count());
    comparar(caso, "mean_packet_size", foto.mean_packet_size, lote.mean_packet_size());
    comparar(caso, "packet_size_entropy", foto.packet_size_entropy, lote.packet_size_entropy());
}

}  // namespace

int main() {
    auto& mgr = ShardedFlowManager::instance();
    mgr.initialize(ShardedFlowManager::Config{
        .shard_count = 4,
        .max_flows_per_shard = 100000,
        .flow_timeout_ns = 120'000'000'000ULL
    });
    uint64_t ts = 1'000'000'000ULL;

    // 1. TCP, 20 paquetes de tamano variado, SYN/ACK alternos
    FlowKey k1{.src_ip = 0xC0A80101, .dst_ip = 0x08080808, .src_port = 54321, .dst_port = 80, .protocol = 6};
    for (uint32_t i = 0; i < 20; ++i)
        mgr.add_packet(k1, paquete(k1, true, 100u + 50u * i, (i % 2 == 0) ? TCP_FLAG_SYN : TCP_FLAG_ACK, ts += 10'000'000ULL));
    verificar("tcp_20_variado", k1);

    // 2. UDP de un solo paquete (flood con un flujo por paquete)
    FlowKey k2{.src_ip = 0xC0A86401, .dst_ip = 0xC0A86432, .src_port = 123, .dst_port = 40000, .protocol = 17};
    mgr.add_packet(k2, paquete(k2, true, 482, 0, ts += 1'000'000ULL));
    verificar("udp_1_paquete", k2);

    // 3. TCP bidireccional con apertura y cierre (completion 1.0)
    FlowKey k3{.src_ip = 0xC0A86432, .dst_ip = 0xC0A86401, .src_port = 50000, .dst_port = 9000, .protocol = 6};
    mgr.add_packet(k3, paquete(k3, true, 74, TCP_FLAG_SYN, ts += 1'000'000ULL));
    mgr.add_packet(k3, paquete(k3, false, 74, TCP_FLAG_SYN | TCP_FLAG_ACK, ts += 1'000'000ULL));
    mgr.add_packet(k3, paquete(k3, true, 66, TCP_FLAG_ACK, ts += 1'000'000ULL));
    for (uint32_t i = 0; i < 40; ++i)
        mgr.add_packet(k3, paquete(k3, (i % 3) != 0, 66u + (i * 37u) % 1400u, TCP_FLAG_ACK | TCP_FLAG_PSH, ts += 1'000'000ULL));
    mgr.add_packet(k3, paquete(k3, true, 66, TCP_FLAG_FIN | TCP_FLAG_ACK, ts += 1'000'000ULL));
    mgr.add_packet(k3, paquete(k3, false, 66, TCP_FLAG_FIN | TCP_FLAG_ACK, ts += 1'000'000ULL));
    verificar("tcp_bidireccional_cierre", k3);

    // 4. 5000 paquetes de tamano aleatorio 40-1514 en ambos sentidos (semilla fija)
    std::mt19937 rng(290u);
    std::uniform_int_distribution<uint32_t> tam(40u, 1514u);
    FlowKey k4{.src_ip = 0x0A000001, .dst_ip = 0x0A000002, .src_port = 1234, .dst_port = 5678, .protocol = 17};
    for (uint32_t i = 0; i < 5000; ++i)
        mgr.add_packet(k4, paquete(k4, (rng() % 4u) != 0u, tam(rng), 0, ts += 100'000ULL));
    verificar("udp_5000_aleatorio", k4);

    // 5. 200000 paquetes de 3 tamanos (acumulacion larga en float)
    FlowKey k5{.src_ip = 0x0A000003, .dst_ip = 0x0A000004, .src_port = 2222, .dst_port = 3333, .protocol = 17};
    const uint32_t tres[3] = {60u, 590u, 1442u};
    for (uint32_t i = 0; i < 200000; ++i)
        mgr.add_packet(k5, paquete(k5, true, tres[(i * 7u) % 3u], 0, ts += 10'000ULL));
    verificar("udp_200000_tres_tamanos", k5);

    // 6. Foto en cada instante: tras cada uno de los 300 paquetes de un flujo aleatorio
    FlowKey k6{.src_ip = 0x0A000005, .dst_ip = 0x0A000006, .src_port = 4444, .dst_port = 80, .protocol = 6};
    for (uint32_t i = 0; i < 300; ++i) {
        const uint8_t fl = (i == 0) ? TCP_FLAG_SYN : ((i == 299) ? (TCP_FLAG_FIN | TCP_FLAG_ACK) : TCP_FLAG_ACK);
        mgr.add_packet(k6, paquete(k6, (rng() % 2u) == 0u, tam(rng), fl, ts += 1'000'000ULL));
        verificar("foto_en_cada_paquete", k6);
    }

    std::printf("%s test_ddos_flow_snap: %d comparaciones, %d fallos\n",
                g_fallos == 0 ? "OK" : "FALLO", g_comparaciones, g_fallos);
    return g_fallos == 0 ? 0 : 1;
}
