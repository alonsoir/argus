// sniffer/tests/test_ddos_flow_snap.cpp
// [DDOS-SNAP-D290] La foto incremental de los rasgos DDoS v2 (ddos_v2_flow_snapshot, la que toma
// el hilo del anillo) tiene que dar EXACTAMENTE (bit a bit) lo mismo que el calculo de lote sobre los
// paquetes del flujo (formulas de calculate_mean/calculate_entropy, DAY307). Sin agregador: source_ip_dispersion
// sale como centinela y no interviene en lo que se compara.
// [D308-PASO1] El flujo ya no guarda un vector por paquete: el test lleva su propia referencia con los paquetes
// que inyecta y comprueba ademas, de forma exacta (enteros), los acumuladores del flujo (LenAcc, IatAcc, sumas de
// cabeceras, histograma) y que la copia por evento los arrastra todos.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "ml_defender_features.hpp"
#include "network_security.pb.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <random>
#include <vector>
#include <algorithm>  // [D307-PASO2]
#include <cmath>      // [D307-PASO2]

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

void exacto(const char* caso, const char* que, bool ok) {
    ++g_comparaciones;
    if (!ok) {
        ++g_fallos;
        std::printf("FALLO %s: acumulador %s distinto de la referencia\n", caso, que);
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

// [D308-PASO1] Referencia del test: los valores exactos de cada paquete inyectado, por serie.
struct Serie {
    std::vector<uint32_t> len;
    std::vector<uint64_t> ts;
    uint64_t cab = 0;
};
struct Ref {
    Serie all, fwd, bwd;
};

void meter(const FlowKey& k, Ref& r, bool directo, uint32_t len, uint8_t flags, uint64_t ts) {
    const SimpleEvent p = paquete(k, directo, len, flags, ts);
    ShardedFlowManager::instance().add_packet(k, p);
    Serie& s = directo ? r.fwd : r.bwd;
    for (Serie* x : {&s, &r.all}) {
        x->len.push_back(len);
        x->ts.push_back(ts);
        x->cab += static_cast<uint64_t>(p.ip_header_len + p.l4_header_len);
    }
}

bool len_ok(const LenAcc& a, const std::vector<uint32_t>& v) {
    uint32_t mn = UINT32_MAX, mx = 0;
    u128 sq = 0;
    for (uint32_t x : v) { mn = std::min(mn, x); mx = std::max(mx, x); sq += static_cast<u128>(x) * x; }
    return a.min == mn && a.max == mx && a.sum_sq == sq;
}

// Regla de pares de antes, sobre el vector: valido si la marca es >= la anterior en llegada.
bool iat_ok(const IatAcc& a, const std::vector<uint64_t>& ts) {
    uint64_t pares = 0, suma = 0, mn = UINT64_MAX, mx = 0;
    u128 sq = 0;
    for (size_t i = 1; i < ts.size(); ++i) {
        if (ts[i] >= ts[i - 1]) {
            const uint64_t d = ts[i] - ts[i - 1];
            ++pares; suma += d; mn = std::min(mn, d); mx = std::max(mx, d); sq += static_cast<u128>(d) * d;
        }
    }
    const uint64_t ultima = ts.empty() ? 0 : ts.back();
    return a.pairs == pares && a.sum == suma && a.min == mn && a.max == mx && a.sum_sq == sq && a.last_ts == ultima;
}

uint64_t suma_len(const std::vector<uint32_t>& v) {
    uint64_t s = 0;
    for (uint32_t x : v) s += x;
    return s;
}

void verificar(const char* caso, const FlowKey& k, const Ref& r) {
    auto& mgr = ShardedFlowManager::instance();
    MLDefenderExtractor ext;

    DdosFlowSnap foto{};
    std::map<uint32_t, uint32_t> hist_tabla;
    mgr.with_flow_stats(k, [&](const auto& fs) {
        foto = ext.ddos_v2_flow_snapshot(fs);
        hist_tabla = fs.len_hist;
    });

    auto copia = mgr.get_flow_stats_copy(k);
    ++g_comparaciones;
    if (!foto.valid || !copia.has_value()) {
        ++g_fallos;
        std::printf("FALLO %s: flujo ausente (foto.valid=%d copia=%d)\n", caso,
                    foto.valid ? 1 : 0, copia.has_value() ? 1 : 0);
        return;
    }
    const auto& f = copia.value();

    // [D308-PASO1] Acumuladores exactos contra la referencia (y la copia los arrastra todos)
    std::map<uint32_t, uint32_t> hist;
    for (uint32_t v : r.all.len) ++hist[v];
    const uint64_t suma = suma_len(r.all.len);
    exacto(caso, "contadores", f.spkts == r.fwd.len.size() && f.dpkts == r.bwd.len.size() &&
                               f.sbytes == suma_len(r.fwd.len) && f.dbytes == suma_len(r.bwd.len) &&
                               f.get_total_packets() == r.all.len.size() && f.get_total_bytes() == suma);
    exacto(caso, "len_all", len_ok(f.len_all, r.all.len));
    exacto(caso, "len_fwd", len_ok(f.len_fwd, r.fwd.len));
    exacto(caso, "len_bwd", len_ok(f.len_bwd, r.bwd.len));
    exacto(caso, "iat_all", iat_ok(f.iat_all, r.all.ts));
    exacto(caso, "iat_fwd", iat_ok(f.iat_fwd, r.fwd.ts));
    exacto(caso, "iat_bwd", iat_ok(f.iat_bwd, r.bwd.ts));
    exacto(caso, "cabeceras", f.fwd_header_sum == r.fwd.cab && f.bwd_header_sum == r.bwd.cab);
    exacto(caso, "len_hist", hist_tabla == hist);

    // [D307-PASO2] Referencia de lote calculada aqui sobre los paquetes, con las mismas operaciones en float que
    // usaba extract_ddos_features (retirado): calculate_mean y calculate_entropy sobre las longitudes.
    const float n_f = static_cast<float>(r.all.len.size());
    float ent = 0.0f;
    for (const auto& [v, c] : hist) {
        (void)v;
        const float p = static_cast<float>(c) / n_f;
        if (p > 0.0f) ent -= p * std::log2(p);
    }
    const float ack1 = static_cast<float>(f.ack_count) + 1.0f;
    const float sar = std::min((ack1 != 0.0f) ? static_cast<float>(f.syn_count) / ack1 : 0.0f, 10.0f);
    const float fcr = (f.syn_count > 0 && f.ack_count > 0 && f.fin_count > 0) ? 1.0f
                    : (f.syn_count > 0 && f.ack_count > 0) ? 0.5f : 0.0f;
    const float media = r.all.len.empty() ? 0.0f : static_cast<float>(suma) / n_f;

    comparar(caso, "syn_ack_ratio", foto.syn_ack_ratio, sar);
    comparar(caso, "flow_completion_rate", foto.flow_completion_rate, fcr);
    comparar(caso, "flow_packet_count", foto.flow_packet_count, static_cast<float>(r.all.len.size()));
    comparar(caso, "mean_packet_size", foto.mean_packet_size, media);
    comparar(caso, "packet_size_entropy", foto.packet_size_entropy, ent);
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
    Ref r1;
    for (uint32_t i = 0; i < 20; ++i)
        meter(k1, r1, true, 100u + 50u * i, (i % 2 == 0) ? TCP_FLAG_SYN : TCP_FLAG_ACK, ts += 10'000'000ULL);
    verificar("tcp_20_variado", k1, r1);

    // 2. UDP de un solo paquete (flood con un flujo por paquete)
    FlowKey k2{.src_ip = 0xC0A86401, .dst_ip = 0xC0A86432, .src_port = 123, .dst_port = 40000, .protocol = 17};
    Ref r2;
    meter(k2, r2, true, 482, 0, ts += 1'000'000ULL);
    verificar("udp_1_paquete", k2, r2);

    // 3. TCP bidireccional con apertura y cierre (completion 1.0)
    FlowKey k3{.src_ip = 0xC0A86432, .dst_ip = 0xC0A86401, .src_port = 50000, .dst_port = 9000, .protocol = 6};
    Ref r3;
    meter(k3, r3, true, 74, TCP_FLAG_SYN, ts += 1'000'000ULL);
    meter(k3, r3, false, 74, TCP_FLAG_SYN | TCP_FLAG_ACK, ts += 1'000'000ULL);
    meter(k3, r3, true, 66, TCP_FLAG_ACK, ts += 1'000'000ULL);
    for (uint32_t i = 0; i < 40; ++i)
        meter(k3, r3, (i % 3) != 0, 66u + (i * 37u) % 1400u, TCP_FLAG_ACK | TCP_FLAG_PSH, ts += 1'000'000ULL);
    meter(k3, r3, true, 66, TCP_FLAG_FIN | TCP_FLAG_ACK, ts += 1'000'000ULL);
    meter(k3, r3, false, 66, TCP_FLAG_FIN | TCP_FLAG_ACK, ts += 1'000'000ULL);
    verificar("tcp_bidireccional_cierre", k3, r3);

    // 4. 5000 paquetes de tamano aleatorio 40-1514 en ambos sentidos (semilla fija)
    std::mt19937 rng(290u);
    std::uniform_int_distribution<uint32_t> tam(40u, 1514u);
    FlowKey k4{.src_ip = 0x0A000001, .dst_ip = 0x0A000002, .src_port = 1234, .dst_port = 5678, .protocol = 17};
    Ref r4;
    for (uint32_t i = 0; i < 5000; ++i) {
        const bool directo = (rng() % 4u) != 0u;
        meter(k4, r4, directo, tam(rng), 0, ts += 100'000ULL);
    }
    verificar("udp_5000_aleatorio", k4, r4);

    // 5. 200000 paquetes de 3 tamanos (acumulacion larga en float)
    FlowKey k5{.src_ip = 0x0A000003, .dst_ip = 0x0A000004, .src_port = 2222, .dst_port = 3333, .protocol = 17};
    const uint32_t tres[3] = {60u, 590u, 1442u};
    Ref r5;
    for (uint32_t i = 0; i < 200000; ++i)
        meter(k5, r5, true, tres[(i * 7u) % 3u], 0, ts += 10'000ULL);
    verificar("udp_200000_tres_tamanos", k5, r5);

    // 6. Foto en cada instante: tras cada uno de los 300 paquetes de un flujo aleatorio
    FlowKey k6{.src_ip = 0x0A000005, .dst_ip = 0x0A000006, .src_port = 4444, .dst_port = 80, .protocol = 6};
    Ref r6;
    for (uint32_t i = 0; i < 300; ++i) {
        const uint8_t fl = (i == 0) ? TCP_FLAG_SYN : ((i == 299) ? (TCP_FLAG_FIN | TCP_FLAG_ACK) : TCP_FLAG_ACK);
        const bool directo = (rng() % 2u) == 0u;
        meter(k6, r6, directo, tam(rng), fl, ts += 1'000'000ULL);
        verificar("foto_en_cada_paquete", k6, r6);
    }

    // 7. [D308-PASO1] Marcas desordenadas (1 de cada 7 anterior a la previa) y marcas repetidas, en los dos
    //    sentidos: la regla de pares validos de los acumuladores tiene que ser la del recorrido de antes
    FlowKey k7{.src_ip = 0x0A000007, .dst_ip = 0x0A000008, .src_port = 5555, .dst_port = 443, .protocol = 6};
    Ref r7;
    uint64_t t7 = ts + 10'000'000ULL;
    for (uint32_t i = 0; i < 2000; ++i) {
        const bool directo = (rng() % 3u) != 0u;
        const uint64_t marca = (i % 7u == 3u) ? t7 - 1'000'000ULL : ((i % 11u == 5u) ? t7 : (t7 += 1'000'000ULL));
        meter(k7, r7, directo, tam(rng), TCP_FLAG_ACK, marca);
        if (i % 97u == 0u) verificar("marcas_desordenadas", k7, r7);
    }
    verificar("marcas_desordenadas", k7, r7);

    std::printf("%s test_ddos_flow_snap: %d comparaciones, %d fallos\n",
                g_fallos == 0 ? "OK" : "FALLO", g_comparaciones, g_fallos);
    return g_fallos == 0 ? 0 : 1;
}
