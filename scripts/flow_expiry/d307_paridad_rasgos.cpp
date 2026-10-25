// DAY307 — instrumento de paridad "antes/despues" de los rasgos del sniffer. SOLO MEDIDA; no se sube al
// pipeline: enlaza el ShardedFlowManager y el MLDefenderExtractor reales.
//
// Reproduce, para una secuencia de paquetes deterministas (semilla fija), el camino de cada evento en
// ring_consumer.cpp:
//   process_raw_event:     FlowKey con los campos del paquete (direccional, como :634) -> add_packet
//                          -> foto ddos_v2 dentro del lock (with_flow_stats + ddos_v2_flow_snapshot)
//   populate_protobuf_event: get_flow_stats_copy -> populate_ml_defender_features
//                          -> sobrescritura de los 5 rasgos ddos con la foto (:965-977)
// y escribe, por evento, TODOS los campos presentes de network_features (reflexion, recursivo):
//   float con %.9g y double con %.17g (ida y vuelta exacta); enteros tal cual.
// Lo que no reproduce (igual antes y despues, no afecta a la comparacion): init_embedded_sentinels, el
// agregador de ventanas (sin agregador -> los rasgos de ventana dan centinela), la victima del kernel.
//
// Tambien mide el tiempo del camino de populate por evento (medio y maximo; la escritura del fichero no cuenta).
// Uso: d307_paridad_rasgos N_PAQUETES SEMILLA SALIDA.tsv
// Comparar dos salidas: identicas byte a byte (pasos sin cambio de valores) o con tolerancia (paso 1).
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "ml_defender_features.hpp"
#include "ddos_flow_snap.hpp"
#include "main.h"
#include "proto/network_security.pb.h"

#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/reflection.h>

#include <chrono>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using namespace sniffer;
using namespace sniffer::flow;
namespace gp = google::protobuf;

static uint64_t g_rng;
static uint64_t rnd() {  // splitmix64: determinista e independiente de la libreria estandar
    uint64_t z = (g_rng += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static uint64_t rnd_in(uint64_t lo, uint64_t hi) { return lo + rnd() % (hi - lo + 1); }

static void volcar(const gp::Message& m, const std::string& pre, std::string& out) {
    const gp::Reflection* r = m.GetReflection();
    std::vector<const gp::FieldDescriptor*> campos;
    r->ListFields(m, &campos);  // solo presentes, en orden de numero de campo
    char b[64];
    for (const auto* f : campos) {
        const std::string nom = pre + f->name();
        if (f->is_repeated()) {
            std::snprintf(b, sizeof b, "%d", r->FieldSize(m, f));
            out += nom + "#=" + b + ";";
            continue;
        }
        switch (f->cpp_type()) {
            case gp::FieldDescriptor::CPPTYPE_MESSAGE: volcar(r->GetMessage(m, f), nom + ".", out); continue;
            case gp::FieldDescriptor::CPPTYPE_FLOAT:  std::snprintf(b, sizeof b, "%.9g", (double)r->GetFloat(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_DOUBLE: std::snprintf(b, sizeof b, "%.17g", r->GetDouble(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_INT32:  std::snprintf(b, sizeof b, "%" PRId32, r->GetInt32(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_INT64:  std::snprintf(b, sizeof b, "%" PRId64, r->GetInt64(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_UINT32: std::snprintf(b, sizeof b, "%" PRIu32, r->GetUInt32(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_UINT64: std::snprintf(b, sizeof b, "%" PRIu64, r->GetUInt64(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_BOOL:   std::snprintf(b, sizeof b, "%d", (int)r->GetBool(m, f)); break;
            case gp::FieldDescriptor::CPPTYPE_ENUM:   std::snprintf(b, sizeof b, "%d", r->GetEnumValue(m, f)); break;
            default: std::snprintf(b, sizeof b, "?"); break;  // string/bytes: network_features no los usa
        }
        out += nom + "=" + b + ";";
    }
}

struct Conv {  // conversacion: dos sentidos, cada uno es un flujo propio en la tabla (clave direccional)
    uint32_t a, b;
    uint16_t pa, pb;
    uint8_t proto;
    uint64_t ts;
    uint32_t restantes;
};

int main(int argc, char** argv) {
    if (argc != 4) { std::fprintf(stderr, "uso: d307_paridad_rasgos N_PAQUETES SEMILLA SALIDA.tsv\n"); return 2; }
    char* fin = nullptr;
    unsigned long long n = std::strtoull(argv[1], &fin, 10);
    if (!argv[1][0] || *fin || n < 1 || n > 50'000'000ULL) { std::fprintf(stderr, "ABORTA: N_PAQUETES en [1, 5e7]\n"); return 2; }
    unsigned long long semilla = std::strtoull(argv[2], &fin, 10);
    if (!argv[2][0] || *fin) { std::fprintf(stderr, "ABORTA: SEMILLA entera\n"); return 2; }
    g_rng = semilla;
    FILE* fo = std::fopen(argv[3], "w");
    if (!fo) { std::fprintf(stderr, "ABORTA: no puedo escribir %s\n", argv[3]); return 2; }

    auto& mgr = ShardedFlowManager::instance();
    mgr.initialize(ShardedFlowManager::Config{.shard_count = 16, .max_flows_per_shard = 10000,
                                              .flow_timeout_ns = 120'000'000'000ULL});
    MLDefenderExtractor ext;  // sin agregador, como cuando el procesador de ransomware esta apagado

    std::vector<Conv> vivas;
    uint64_t reloj = 1'000'000'000ULL;
    uint64_t desordenados = 0, eventos_sin_flujo = 0;
    double ns_total = 0, ns_max = 0;  // tiempo del camino de populate (copia + rasgos + sobrescritura)
    // reparto por tamano del flujo en el evento (paquetes ya acumulados): [1,20] [21,500] [501,inf)
    double ns_tramo[3] = {0, 0, 0};
    uint64_t ev_tramo[3] = {0, 0, 0};
    double suma_n = 0;
    std::fprintf(fo, "# n=%llu semilla=%llu\n", n, semilla);
    for (unsigned long long i = 0; i < n; ++i) {
        // mantener ~40 conversaciones vivas; longitudes de 1 a 5000 paquetes (cola larga)
        while (vivas.size() < 40) {
            Conv c;
            c.a = 0xC0A86400u | (uint32_t)rnd_in(2, 250);
            c.b = 0xC0A86400u | (uint32_t)rnd_in(2, 250);
            c.pa = (uint16_t)rnd_in(1024, 65535);
            c.pb = (uint16_t)(rnd() % 4 == 0 ? 53 : rnd_in(1, 1023));
            c.proto = (rnd() % 3 == 0) ? 17 : 6;
            c.ts = reloj;
            uint64_t r = rnd() % 100;
            c.restantes = (uint32_t)(r < 60 ? rnd_in(1, 20) : r < 95 ? rnd_in(21, 500) : rnd_in(501, 5000));
            vivas.push_back(c);
        }
        size_t k = rnd() % vivas.size();
        Conv& c = vivas[k];
        bool ida = (rnd() % 3) != 0;
        SimpleEvent e{};
        e.src_ip = ida ? c.a : c.b;
        e.dst_ip = ida ? c.b : c.a;
        e.src_port = ida ? c.pa : c.pb;
        e.dst_port = ida ? c.pb : c.pa;
        e.protocol = c.proto;
        e.packet_len = (uint32_t)(rnd() % 4 == 0 ? rnd_in(40, 1500) : (rnd() % 2 ? 60 : 1400));
        e.ip_header_len = 20;
        e.l4_header_len = (c.proto == 6) ? 20 : 8;
        if (c.proto == 6) {
            uint64_t t = rnd() % 10;
            e.tcp_flags = (uint8_t)(t == 0 ? TCP_FLAG_SYN : t == 1 ? (TCP_FLAG_SYN | TCP_FLAG_ACK)
                                  : t == 2 ? (TCP_FLAG_FIN | TCP_FLAG_ACK) : t == 3 ? TCP_FLAG_RST
                                  : t < 7 ? (TCP_FLAG_PSH | TCP_FLAG_ACK) : TCP_FLAG_ACK);
        }
        // tiempo: avance con cola larga; 1 de cada 200, marca ANTERIOR a la previa (caso de pares desordenados)
        uint64_t paso = (rnd() % 10 == 0) ? rnd_in(1'000'000, 2'000'000'000ULL) : rnd_in(1'000, 5'000'000);
        if (rnd() % 200 == 0 && c.ts > 2'000'000) { e.timestamp = c.ts - rnd_in(1, 1'000'000); ++desordenados; }
        else { c.ts += paso; e.timestamp = c.ts; }
        reloj = std::max(reloj, c.ts);

        FlowKey key{.src_ip = e.src_ip, .dst_ip = e.dst_ip, .src_port = e.src_port, .dst_port = e.dst_port,
                    .protocol = e.protocol};
        mgr.add_packet(key, e);
        DdosFlowSnap snap{};
        mgr.with_flow_stats(key, [&](const auto& fs) { snap = ext.ddos_v2_flow_snapshot(fs); });

        protobuf::NetworkSecurityEvent ev;
        auto t0 = std::chrono::steady_clock::now();
        auto copia = mgr.get_flow_stats_copy(key);
        const uint64_t n_flujo = copia ? copia->get_total_packets() : 0;
        if (copia) ext.populate_ml_defender_features(*copia, ev);
        else ++eventos_sin_flujo;
        auto* dd = ev.mutable_network_features()->mutable_ddos_embedded();
        if (snap.valid) {
            dd->set_syn_ack_ratio(snap.syn_ack_ratio);
            dd->set_flow_completion_rate(snap.flow_completion_rate);
            dd->set_flow_packet_count(snap.flow_packet_count);
            dd->set_mean_packet_size(snap.mean_packet_size);
            dd->set_packet_size_entropy(snap.packet_size_entropy);
        }
        double ns = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now() - t0).count();
        ns_total += ns;
        if (ns > ns_max) ns_max = ns;
        const int tr = n_flujo <= 20 ? 0 : n_flujo <= 500 ? 1 : 2;
        ns_tramo[tr] += ns;
        ++ev_tramo[tr];
        suma_n += (double)n_flujo;
        std::string linea;
        volcar(ev.network_features(), "", linea);
        std::fprintf(fo, "%llu\t%s\n", i, linea.c_str());

        if (--c.restantes == 0) { vivas[k] = vivas.back(); vivas.pop_back(); }
    }
    std::fclose(fo);
    std::printf("eventos=%llu desordenados=%" PRIu64 " eventos_sin_flujo=%" PRIu64 " salida=%s\n",
                n, desordenados, eventos_sin_flujo, argv[3]);
    std::printf("populate_us_medio=%.3f populate_us_max=%.1f\n", ns_total / 1000.0 / (double)n, ns_max / 1000.0);
    std::printf("paquetes_del_flujo_medio_por_evento=%.1f\n", suma_n / (double)n);
    const char* nom[3] = {"1-20", "21-500", "501+"};
    for (int j = 0; j < 3; ++j)
        std::printf("tramo=%s eventos=%" PRIu64 " (%.1f%%) us_medio=%.3f peso_en_tiempo=%.1f%%\n", nom[j], ev_tramo[j],
                    100.0 * (double)ev_tramo[j] / (double)n, ev_tramo[j] ? ns_tramo[j] / 1000.0 / (double)ev_tramo[j] : 0.0,
                    ns_total > 0 ? 100.0 * ns_tramo[j] / ns_total : 0.0);
    return eventos_sin_flujo == 0 ? 0 : 3;
}
