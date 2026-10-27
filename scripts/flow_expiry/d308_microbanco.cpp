// DAY308 — microbanco para separar de donde sale el coste por evento de populate en el defender (VM VirtualBox)
// frente a una maquina sin virtualizar. SOLO MEDIDA. Tres bucles, cada uno N iteraciones, ns por iteracion:
//   aritmetica : cadena dependiente de operaciones en float/entero, sin tocar memoria nueva
//   reservas   : malloc/free de 4 bloques pequenos (tamanos del orden de los submensajes de network_features)
//   protobuf   : crear y destruir un NetworkSecurityEvent con network_features y sus 3 submensajes, escribiendo
//                un campo en cada uno (lo que reserva populate en cada evento)
// Lo que interesa no es el valor absoluto sino la proporcion entre maquinas de cada bucle.
// Uso: d308_microbanco N
#include "proto/network_security.pb.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <thread>

using reloj = std::chrono::steady_clock;

static double ns_desde(reloj::time_point t0) {
    return std::chrono::duration<double, std::nano>(reloj::now() - t0).count();
}

int main(int argc, char** argv) {
    const long n = argc == 2 ? std::strtol(argv[1], nullptr, 10) : 0;
    if (n < 1 || n > 1'000'000'000) { std::fprintf(stderr, "uso: d308_microbanco N (1..1e9)\n"); return 2; }

    std::string carga;
    { std::ifstream f("/proc/loadavg"); std::getline(f, carga); }
    std::printf("# n=%ld hilos_hw=%u loadavg=%s\n", n, std::thread::hardware_concurrency(), carga.c_str());

    // 1. aritmetica: dependencia en cadena para que el compilador no la elimine ni la paralelice
    volatile float sumidero_f = 0.0f;
    {
        float x = 1.000001f;
        uint64_t k = 12345;
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            k = k * 6364136223846793005ULL + 1442695040888963407ULL;
            x = x * 0.999999f + static_cast<float>(k >> 40) * 1e-9f;
            x = x / (1.0f + x * 1e-7f);
        }
        const double ns = ns_desde(t0);
        sumidero_f = x;
        std::printf("aritmetica_ns_por_iter=%.2f\n", ns / (double)n);
    }

    // 2. reservas: 4 bloques pequenos, liberados en orden inverso
    volatile uintptr_t sumidero_p = 0;
    {
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            void* a = std::malloc(96);
            void* b = std::malloc(64);
            void* c = std::malloc(64);
            void* d = std::malloc(192);
            sumidero_p = sumidero_p ^ reinterpret_cast<uintptr_t>(a) ^ reinterpret_cast<uintptr_t>(d);
            std::free(d); std::free(c); std::free(b); std::free(a);
        }
        const double ns = ns_desde(t0);
        std::printf("reservas_ns_por_iter=%.2f\n", ns / (double)n);
    }

    // 3. protobuf: el mensaje con los submensajes que crea populate en cada evento
    {
        const auto t0 = reloj::now();
        for (long i = 0; i < n; ++i) {
            protobuf::NetworkSecurityEvent ev;
            auto* nf = ev.mutable_network_features();
            nf->set_total_forward_packets(static_cast<uint64_t>(i));
            nf->mutable_ransomware_embedded()->set_entropy(0.5f);
            nf->mutable_traffic_classification()->set_packet_rate(0.5f);
            nf->mutable_internal_anomaly()->set_protocol_regularity(0.5f);
            sumidero_p = sumidero_p ^ static_cast<uintptr_t>(nf->total_forward_packets());
        }
        const double ns = ns_desde(t0);
        std::printf("protobuf_ns_por_iter=%.2f\n", ns / (double)n);
    }
    (void)sumidero_f;
    return 0;
}
