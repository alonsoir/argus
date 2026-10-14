// DAY297 D15 A5 (offline): ataque sostenido largo contra la funcion REAL del sniffer, victim_ewma_step
// (sniffer/include/ddos_contract_v2.hpp), con sus parametros por defecto (= defectos del JSON).
// Etapa 1 del ml-detector: ratio >= K (3, ddos_v2_head.hpp). Sombra: FIN = ultima ventana positiva + hold (30).
// Serie sintetica por escenario: W_BASE ventanas de base y W_ATQ de base + ataque. 1 ventana = 1 s.
// Compilar en el defender: g++ -std=c++20 -O2 -Wall -Wextra -I/vagrant/sniffer/include -o /tmp/a5 <este fichero>
#include "ddos_contract_v2.hpp"

#include <cstdint>
#include <cstdio>

int main() {
    using namespace argus::ddos;
    const VictimEwmaParams p{};
    const double K = 3.0;
    const long HOLD = 30;
    const uint64_t W_BASE = 600, W_ATQ = 7200;
    std::printf("params alpha=%g alpha_lento=%g k_in=%g k_out=%g warm=%llu floor=%g evict=%llu K_etapa1=%g hold=%ld\n",
                p.alpha, p.alpha_slow(), p.k_in, p.k_out, static_cast<unsigned long long>(p.warm_windows),
                p.floor_pps, static_cast<unsigned long long>(p.evict_windows), K, HOLD);
    std::printf("%6s %7s %8s %8s %8s %8s %8s %9s %9s %9s %9s\n", "base", "ataque", "ratio_0", "corte_s", "fin_s",
                "salida_s", "ewma_in", "ratio_5m", "ratio_10m", "ratio_20m", "ratio_30m");
    const double bases[] = {1.0, 10.0};
    const double ataques[] = {60.0, 70.0, 120.0, 600.0, 6000.0};
    for (double b : bases) {
        for (double at : ataques) {
            VictimEwmaState s{};
            uint64_t seq = 0;
            for (uint64_t i = 0; i < W_BASE; ++i) victim_ewma_step(s, ++seq, b, p);
            const double ewma_in = s.ewma;
            double r0 = 0, r5 = 0, r10 = 0, r20 = 0, r30 = 0;
            long corte = -1, salida = -1;
            bool entro = false;
            for (uint64_t t = 0; t < W_ATQ; ++t) {
                const double r = victim_ewma_step(s, ++seq, b + at, p);
                if (t == 0) r0 = r;
                if (t == 300) r5 = r;
                if (t == 600) r10 = r;
                if (t == 1200) r20 = r;
                if (t == 1800) r30 = r;
                if (corte < 0 && r < K) corte = static_cast<long>(t);
                if (s.bajo_presion) entro = true;
                if (entro && salida < 0 && !s.bajo_presion) salida = static_cast<long>(t);
            }
            const long fin = corte >= 0 ? corte - 1 + HOLD : -1;
            std::printf("%6.0f %7.0f %8.2f %8ld %8ld %8ld %8.2f %9.3f %9.3f %9.3f %9.3f\n", b, at, r0, corte, fin,
                        salida, ewma_in, r5, r10, r20, r30);
        }
    }
    return 0;
}
