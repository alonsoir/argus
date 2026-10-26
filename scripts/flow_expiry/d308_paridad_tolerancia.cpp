// DAY308 — instrumento de paridad con tolerancia para el paso 1 (estadisticos incrementales en FlowStatistics).
// SOLO MEDIDA; no se sube al pipeline: enlaza el ShardedFlowManager y el MLDefenderExtractor reales.
//
// Es d307_paridad_rasgos.cpp con tres anadidos, sin tocar el generador (mismas llamadas a rnd(), en el mismo
// orden: misma semilla => mismos paquetes) ni la salida principal (mismo formato => comparable byte a byte con
// logs/lab/day307/paridad/antes.tsv):
//   1. SOMBRA: el instrumento guarda, por FlowKey, los valores exactos de cada paquete (longitudes y marcas por
//      sentido, con la misma regla de sentido que FlowStatistics::is_forward). Vive solo aqui, no en produccion.
//   2. ORACULO: por evento, calcula las desviaciones sobre la sombra en long double y en dos pasadas (media exacta),
//      y les aplica el MISMO post-proceso en float/double que ml_defender_features.cpp. Escribe un segundo fichero
//      con los 13 rasgos de las clases V y D (doc day308_paso1_diseno.md, seccion 2), el cv del oraculo y el
//      tamano del flujo en el evento.
//   3. TIEMPO DE LA FOTO: mide aparte la foto DDoS en el lock (with_flow_stats + ddos_v2_flow_snapshot), que es
//      O(k) y sigue en el camino de cada evento.
// Ademas comprueba que la tabla y la sombra cuentan los mismos paquetes por flujo (si no, ABORTA: el oraculo
// no seria del mismo flujo).
//
// Compila contra el codigo de HOY (populate sin entropia) y, con -DD308_DESPUES, contra el del paso 1
// (populate recibe la entropia de la foto, decision D1).
// La region cronometrada se reparte en tres piezas (copia del flujo, populate, rasgos DDoS) con dos lecturas de
// reloj mas (0,022 us cada una, medido en el defender, DAY308).
// Uso: d308_paridad_tolerancia N_PAQUETES SEMILLA SALIDA.tsv ORACULO.tsv
//      Con ORACULO = "-" no hay sombra ni oraculo (ni su comprobacion): solo la salida principal y los tiempos.
//      Sirve para medir la region cronometrada sin el trabajo del oraculo entre eventos, que recorre los vectores
//      sombra del flujo y puede dejar la cache y el TLB en frio (DAY308). La salida principal es la misma.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "ml_defender_features.hpp"
#include "ddos_flow_snap.hpp"
#include "main.h"
#include "proto/network_security.pb.h"

#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/reflection.h>

#include <algorithm>
#include <chrono>
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <tuple>
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

// ---------------------------------------------------------------- sombra y oraculo
struct Sombra {
    std::vector<uint32_t> len_all, len_f, len_b;
    std::vector<uint64_t> ts_all, ts_f, ts_b;
};

// Desviacion tipica poblacional de longitudes: dos pasadas en long double con la media exacta.
// Misma convencion que calculate_std_dev: 0 si hay menos de 2 valores.
static float orac_std_len(const std::vector<uint32_t>& v) {
    if (v.size() < 2) return 0.0f;
    long double s = 0;
    for (uint32_t x : v) s += (long double)x;
    const long double m = s / (long double)v.size();
    long double q = 0;
    for (uint32_t x : v) { const long double d = (long double)x - m; q += d * d; }
    return (float)std::sqrt(q / (long double)v.size());
}

// IAT de una serie de marcas en orden de llegada: pares validos = marca >= la anterior (la anterior en llegada).
struct OracIat {
    bool hay_pares = false;     // size >= 2 y al menos un par valido (condicion de populate para escribir)
    float std_f = 0.0f;         // desviacion sobre los pares validos (= calculate_iat_std_dev)
    float mean_quirk = 0.0f;    // Σ pares validos / (size - 1) (= calculate_iat_mean)
};
static OracIat orac_iat(const std::vector<uint64_t>& ts) {
    OracIat r;
    if (ts.size() < 2) return r;
    std::vector<uint64_t> iats;
    for (size_t i = 1; i < ts.size(); ++i)
        if (ts[i] >= ts[i - 1]) iats.push_back(ts[i] - ts[i - 1]);
    uint64_t sum = 0;
    for (uint64_t x : iats) sum += x;
    r.mean_quirk = static_cast<float>(sum) / static_cast<float>(ts.size() - 1);
    if (iats.empty()) return r;
    r.hay_pares = true;
    const long double m = (long double)sum / (long double)iats.size();
    long double q = 0;
    for (uint64_t x : iats) { const long double d = (long double)x - m; q += d * d; }
    r.std_f = (float)std::sqrt(q / (long double)iats.size());
    return r;
}

static void pon_f(std::string& out, const char* nom, float v) {
    char b[64]; std::snprintf(b, sizeof b, "%s=%.9g;", nom, (double)v); out += b;
}
static void pon_d(std::string& out, const char* nom, double v) {
    char b[80]; std::snprintf(b, sizeof b, "%s=%.17g;", nom, v); out += b;
}

// Los 13 rasgos de las clases V y D con el post-proceso de ml_defender_features.cpp, mas cv_iat del oraculo.
static std::string oraculo(const Sombra& s) {
    std::string o;
    // longitudes por sentido: populate solo escribe si el vector no esta vacio; std = 0 con un solo valor
    const float sf = orac_std_len(s.len_f), sb = orac_std_len(s.len_b), sa = orac_std_len(s.len_all);
    pon_d(o, "forward_packet_length_std", (double)sf);
    pon_d(o, "backward_packet_length_std", (double)sb);
    // IAT: populate escribe min/max/mean/std solo si size >= 2 y hay pares validos; std_ns / 1000.0 en double
    const OracIat ia = orac_iat(s.ts_all), iff = orac_iat(s.ts_f), ib = orac_iat(s.ts_b);
    pon_d(o, "flow_inter_arrival_time_std", ia.hay_pares ? (double)ia.std_f / 1000.0 : 0.0);
    pon_d(o, "forward_inter_arrival_time_std", iff.hay_pares ? (double)iff.std_f / 1000.0 : 0.0);
    pon_d(o, "backward_inter_arrival_time_std", ib.hay_pares ? (double)ib.std_f / 1000.0 : 0.0);
    pon_d(o, "packet_length_std", (double)sa);
    pon_d(o, "packet_length_variance", (double)(sa * sa));  // std_dev * std_dev en float, como populate

    // cv de los IAT: calculate_iat_coefficient_of_variation (media "quirk" / std de pares validos)
    const float cv = (ia.mean_quirk == 0.0f) ? 0.0f : ia.std_f / ia.mean_quirk;

    // ransomware_embedded
    {
        const float tp = (cv < 0.5f) ? 0.8f : (cv > 1.0f) ? 0.2f : MISSING_FEATURE_SENTINEL;
        pon_f(o, "ransomware_embedded.temporal_pattern", tp);
        // behavior_consistency: iat_std / iat_mean con la misma media "quirk"
        const float bc = (ia.mean_quirk == 0.0f) ? MISSING_FEATURE_SENTINEL
                                                 : std::max(0.0f, 1.0f - ia.std_f / ia.mean_quirk);
        pon_f(o, "ransomware_embedded.behavior_consistency", bc);
    }
    // traffic_classification
    pon_f(o, "traffic_classification.temporal_consistency", std::max(0.0f, 1.0f - cv));
    // internal_anomaly
    {
        pon_f(o, "internal_anomaly.protocol_regularity", std::max(0.0f, 1.0f - cv));
        // packet_size_consistency: std_dev(all) / mean(all); mean = Σ/n en float (exacto, como calculate_mean)
        uint64_t suma = 0;
        for (uint32_t x : s.len_all) suma += x;
        const float media = s.len_all.empty() ? 0.0f
                          : static_cast<float>(suma) / static_cast<float>(s.len_all.size());
        const float psc = (media == 0.0f) ? MISSING_FEATURE_SENTINEL : std::max(0.0f, 1.0f - sa / media);
        pon_f(o, "internal_anomaly.packet_size_consistency", psc);
        const float ta = (cv < 0.2f) ? 0.8f : (cv > 2.0f) ? 0.7f : 0.3f;
        pon_f(o, "internal_anomaly.temporal_anomaly_score", ta);
    }
    pon_f(o, "cv_iat", cv);
    return o;
}

int main(int argc, char** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "uso: d308_paridad_tolerancia N_PAQUETES SEMILLA SALIDA.tsv ORACULO.tsv\n");
        return 2;
    }
    char* fin = nullptr;
    unsigned long long n = std::strtoull(argv[1], &fin, 10);
    if (!argv[1][0] || *fin || n < 1 || n > 50'000'000ULL) { std::fprintf(stderr, "ABORTA: N_PAQUETES en [1, 5e7]\n"); return 2; }
    unsigned long long semilla = std::strtoull(argv[2], &fin, 10);
    if (!argv[2][0] || *fin) { std::fprintf(stderr, "ABORTA: SEMILLA entera\n"); return 2; }
    g_rng = semilla;
    FILE* fo = std::fopen(argv[3], "w");
    if (!fo) { std::fprintf(stderr, "ABORTA: no puedo escribir %s\n", argv[3]); return 2; }
    const bool con_oraculo = std::string(argv[4]) != "-";
    FILE* fr = nullptr;
    if (con_oraculo) {
        fr = std::fopen(argv[4], "w");
        if (!fr) { std::fprintf(stderr, "ABORTA: no puedo escribir %s\n", argv[4]); return 2; }
    }

    auto& mgr = ShardedFlowManager::instance();
    mgr.initialize(ShardedFlowManager::Config{.shard_count = 16, .max_flows_per_shard = 10000,
                                              .flow_timeout_ns = 120'000'000'000ULL});
    MLDefenderExtractor ext;  // sin agregador, como cuando el procesador de ransomware esta apagado

    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t, uint8_t>, Sombra> sombras;

    std::vector<Conv> vivas;
    uint64_t reloj = 1'000'000'000ULL;
    uint64_t desordenados = 0, eventos_sin_flujo = 0, descuadres = 0;
    double ns_total = 0, ns_max = 0;  // tiempo del camino de populate (copia + rasgos + sobrescritura)
    double ns_foto_total = 0, ns_foto_max = 0;
    double ns_copia = 0, ns_pop = 0, ns_ddos = 0;  // [DAY308] reparto de la region cronometrada  // tiempo de la foto DDoS en el lock (aparte)
    // reparto por tamano del flujo en el evento (paquetes ya acumulados): [1,20] [21,500] [501,inf)
    double ns_tramo[3] = {0, 0, 0}, ns_foto_tramo[3] = {0, 0, 0};
    uint64_t ev_tramo[3] = {0, 0, 0};
    double suma_n = 0;
    std::fprintf(fo, "# n=%llu semilla=%llu\n", n, semilla);
    if (con_oraculo) std::fprintf(fr, "# oraculo n=%llu semilla=%llu\n", n, semilla);
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

        // sombra: misma regla de sentido que FlowStatistics::is_forward (el paquete contra la clave del flujo)
        Sombra* sh = nullptr;
        if (con_oraculo) {
            sh = &sombras[std::make_tuple(key.src_ip, key.dst_ip, key.src_port, key.dst_port, key.protocol)];
            const bool fwd = e.src_ip == key.src_ip && e.dst_ip == key.dst_ip &&
                             e.src_port == key.src_port && e.dst_port == key.dst_port;
            (fwd ? sh->len_f : sh->len_b).push_back(e.packet_len);
            (fwd ? sh->ts_f : sh->ts_b).push_back(e.timestamp);
            sh->len_all.push_back(e.packet_len);
            sh->ts_all.push_back(e.timestamp);
        }

        DdosFlowSnap snap{};
        auto tf = std::chrono::steady_clock::now();
        mgr.with_flow_stats(key, [&](const auto& fs) { snap = ext.ddos_v2_flow_snapshot(fs); });
        const double ns_foto = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now() - tf).count();

        protobuf::NetworkSecurityEvent ev;
        auto t0 = std::chrono::steady_clock::now();
        auto copia = mgr.get_flow_stats_copy(key);
        const auto t1 = std::chrono::steady_clock::now();  // [DAY308] piezas: copia | populate | rasgos DDoS
        const uint64_t n_flujo = copia ? copia->get_total_packets() : 0;
#ifdef D308_DESPUES
        if (copia) ext.populate_ml_defender_features(*copia, snap.packet_size_entropy, ev);
#else
        if (copia) ext.populate_ml_defender_features(*copia, ev);
#endif
        else ++eventos_sin_flujo;
        const auto t2 = std::chrono::steady_clock::now();
        auto* dd = ev.mutable_network_features()->mutable_ddos_embedded();
        if (snap.valid) {
            dd->set_syn_ack_ratio(snap.syn_ack_ratio);
            dd->set_flow_completion_rate(snap.flow_completion_rate);
            dd->set_flow_packet_count(snap.flow_packet_count);
            dd->set_mean_packet_size(snap.mean_packet_size);
            dd->set_packet_size_entropy(snap.packet_size_entropy);
        }
        const auto t3 = std::chrono::steady_clock::now();
        double ns = std::chrono::duration<double, std::nano>(t3 - t0).count();
        ns_copia += std::chrono::duration<double, std::nano>(t1 - t0).count();
        ns_pop += std::chrono::duration<double, std::nano>(t2 - t1).count();
        ns_ddos += std::chrono::duration<double, std::nano>(t3 - t2).count();
        ns_total += ns;
        if (ns > ns_max) ns_max = ns;
        ns_foto_total += ns_foto;
        if (ns_foto > ns_foto_max) ns_foto_max = ns_foto;
        const int tr = n_flujo <= 20 ? 0 : n_flujo <= 500 ? 1 : 2;
        ns_tramo[tr] += ns;
        ns_foto_tramo[tr] += ns_foto;
        ++ev_tramo[tr];
        suma_n += (double)n_flujo;
        std::string linea;
        volcar(ev.network_features(), "", linea);
        std::fprintf(fo, "%llu\t%s\n", i, linea.c_str());

        if (con_oraculo) {
            if (copia && n_flujo != sh->len_all.size()) ++descuadres;  // tabla y sombra deben contar lo mismo
            std::fprintf(fr, "%llu\t%" PRIu64 "\t%s\n", i, n_flujo, oraculo(*sh).c_str());
        }

        if (--c.restantes == 0) { vivas[k] = vivas.back(); vivas.pop_back(); }
    }
    std::fclose(fo);
    if (fr) std::fclose(fr);
    std::printf("eventos=%llu desordenados=%" PRIu64 " eventos_sin_flujo=%" PRIu64 " descuadres_sombra=%" PRIu64
                " flujos=%zu salida=%s oraculo=%s\n",
                n, desordenados, eventos_sin_flujo, descuadres, sombras.size(), argv[3],
                con_oraculo ? argv[4] : "(sin oraculo)");
    std::printf("populate_us_medio=%.3f populate_us_max=%.1f\n", ns_total / 1000.0 / (double)n, ns_max / 1000.0);
    std::printf("piezas_us_medio copia=%.3f populate=%.3f rasgos_ddos=%.3f\n", ns_copia / 1000.0 / (double)n,
                ns_pop / 1000.0 / (double)n, ns_ddos / 1000.0 / (double)n);
    std::printf("foto_us_medio=%.3f foto_us_max=%.1f\n", ns_foto_total / 1000.0 / (double)n, ns_foto_max / 1000.0);
    std::printf("paquetes_del_flujo_medio_por_evento=%.1f\n", suma_n / (double)n);
    const char* nom[3] = {"1-20", "21-500", "501+"};
    for (int j = 0; j < 3; ++j)
        std::printf("tramo=%s eventos=%" PRIu64 " (%.1f%%) us_medio=%.3f peso_en_tiempo=%.1f%% foto_us_medio=%.3f\n",
                    nom[j], ev_tramo[j], 100.0 * (double)ev_tramo[j] / (double)n,
                    ev_tramo[j] ? ns_tramo[j] / 1000.0 / (double)ev_tramo[j] : 0.0,
                    ns_total > 0 ? 100.0 * ns_tramo[j] / ns_total : 0.0,
                    ev_tramo[j] ? ns_foto_tramo[j] / 1000.0 / (double)ev_tramo[j] : 0.0);
    if (descuadres) std::printf("ABORTA: la sombra no cuenta lo mismo que la tabla en %" PRIu64 " eventos\n", descuadres);
    return (eventos_sin_flujo == 0 && descuadres == 0) ? 0 : 3;
}
