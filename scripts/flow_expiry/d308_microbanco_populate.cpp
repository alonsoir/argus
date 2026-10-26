// DAY308 — microbanco de populate_ml_defender_features (codigo del paso 1), para ver que parte de populate
// cuesta en el defender (VM VirtualBox) 6-7 veces lo que en otra maquina, cuando la aritmetica, malloc y el
// protobuf aislados cuestan 1,5-2,1 veces (d308_microbanco). SOLO MEDIDA. Cuatro bucles, ns por iteracion:
//   ld_desviacion : la evaluacion de una desviacion como la de populate: u128 y uint64 -> long double,
//                   dos divisiones, resta, sqrt en long double y vuelta a float (std_dev_from_sums)
//   populate_nuevo: populate sobre un nucleo fijo y un NetworkSecurityEvent nuevo en cada iteracion (como el
//                   instrumento y ring_consumer: reserva los submensajes cada vez)
//   populate_clear: lo mismo reutilizando el evento con Clear() (los submensajes no se vuelven a reservar)
//   solo_crear    : crear y destruir el evento con network_features y sus 3 submensajes, sin calculos
// El nucleo es un flujo de 2 000 paquetes en los dos sentidos, con IAT y longitudes variables.
// Uso: d308_microbanco_populate N
#include "flow_manager.hpp"
#include "ml_defender_features.hpp"
#include "main.h"
#include "proto/network_security.pb.h"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

using namespace sniffer;
using reloj = std::chrono::steady_clock;

static double ns_desde(reloj::time_point t0) {
    return std::chrono::duration<double, std::nano>(reloj::now() - t0).count();
}

int main(int argc, char** argv) {
    const long n = argc == 2 ? std::strtol(argv[1], nullptr, 10) : 0;
    if (n < 1 || n > 100'000'000) { std::fprintf(stderr, "uso: d308_microbanco_populate N (1..1e8)\n"); return 2; }
    std::string carga;
    { std::ifstream f("/proc/loadavg"); std::getline(f, carga); }
    std::printf("# n=%ld loadavg=%s\n", n, carga.c_str());

    // nucleo de flujo fijo: 2 000 paquetes, 2/3 de ida
    const FlowKey k{.src_ip = 0x0A000001, .dst_ip = 0x0A000002, .src_port = 40000, .dst_port = 443, .protocol = 6};
    FlowStatsCore core;
    uint64_t ts = 1'000'000'000ULL;
    for (uint32_t i = 0; i < 2000; ++i) {
        SimpleEvent e{};
        const bool ida = (i % 3) != 0;
        e.src_ip = ida ? k.src_ip : k.dst_ip;
        e.dst_ip = ida ? k.dst_ip : k.src_ip;
        e.src_port = ida ? k.src_port : k.dst_port;
        e.dst_port = ida ? k.dst_port : k.src_port;
        e.protocol = 6;
        e.packet_len = 60 + (i * 37u) % 1400u;
        e.ip_header_len = 20;
        e.l4_header_len = 20;
        e.tcp_flags = (i % 5 == 0) ? (TCP_FLAG_PSH | TCP_FLAG_ACK) : TCP_FLAG_ACK;
        ts += 1'000 + (i * 7919u) % 3'000'000u;
        e.timestamp = ts;
        core.add_packet(e, k);
    }
    MLDefenderExtractor ext;
    const float entropia = 7.5f;

    volatile float sumidero = 0.0f;
    // 1. una desviacion como las de populate
    {
        u128 s2 = core.len_all.sum_sq;
        uint64_t s = core.get_total_bytes(), m = core.get_total_packets();
        float acc = 0.0f;
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            s2 += static_cast<unsigned>(i & 1);  // que no se pueda sacar del bucle
            const long double media = static_cast<long double>(s) / static_cast<long double>(m);
            long double var = static_cast<long double>(s2) / static_cast<long double>(m) - media * media;
            if (var < 0.0L) var = 0.0L;
            acc += static_cast<float>(std::sqrt(var));
        }
        const double ns = ns_desde(t0);
        sumidero = acc;
        std::printf("ld_desviacion_ns_por_iter=%.2f\n", ns / (double)n);
    }
    // 2. populate con evento nuevo
    {
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            protobuf::NetworkSecurityEvent ev;
            ext.populate_ml_defender_features(core, entropia, ev);
            sumidero = sumidero + ev.network_features().packet_length_std();
        }
        std::printf("populate_nuevo_ns_por_iter=%.2f\n", ns_desde(t0) / (double)n);
    }
    // 3. populate reutilizando el evento
    {
        protobuf::NetworkSecurityEvent ev;
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            ev.Clear();
            ext.populate_ml_defender_features(core, entropia, ev);
            sumidero = sumidero + ev.network_features().packet_length_std();
        }
        std::printf("populate_clear_ns_por_iter=%.2f\n", ns_desde(t0) / (double)n);
    }
    // 4. solo crear y destruir el evento con sus submensajes
    {
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            protobuf::NetworkSecurityEvent ev;
            auto* nf = ev.mutable_network_features();
            nf->mutable_ransomware_embedded();
            nf->mutable_traffic_classification();
            nf->mutable_internal_anomaly();
            sumidero = sumidero + static_cast<float>(nf->has_internal_anomaly());
        }
        std::printf("solo_crear_ns_por_iter=%.2f\n", ns_desde(t0) / (double)n);
    }
    return 0;
}
