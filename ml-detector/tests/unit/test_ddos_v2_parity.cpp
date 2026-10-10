// DAY293 — paridad Python/C++ de la cabeza DDoS v2 factorizada. Lee el CSV de paridad del exportador
// (export_ddos_v2_fact_rf.py): 6 rasgos de flujo, victim_rate_ratio, etapa1, p0, p1, clase. Entrada como numpy:
// (float)strtod(texto). Exige igualdad EXACTA de etapa 1 y clase, y de p0/p1 (bits) cuando la etapa 1 pasa.
#include <bit>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ml_defender/ddos_v2_head.hpp"

#ifndef DDOS_V2_PARITY_CSV
#define DDOS_V2_PARITY_CSV "ddos_v2_paridad_muestra.csv"
#endif

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : DDOS_V2_PARITY_CSV;
    std::ifstream in(path);
    if (!in) {
        std::cerr << "[DDOS-V2-PARITY] no se puede abrir " << path << "\n";
        return 2;
    }
    std::string line;
    std::getline(in, line);
    long n = 0;
    long bad = 0;
    while (std::getline(in, line)) {
        std::vector<std::string> c;
        std::stringstream ss(line);
        std::string tok;
        while (std::getline(ss, tok, ',')) {
            c.push_back(tok);
        }
        if (c.size() != 11) {
            std::cerr << "[DDOS-V2-PARITY] fila mal formada " << (n + 2) << "\n";
            return 2;
        }
        auto f = [&](std::size_t i) { return static_cast<float>(std::strtod(c[i].c_str(), nullptr)); };
        const ml_defender::ddos_v2::Input x{f(0), f(1), f(2), f(3), f(4), f(5), f(6)};
        const auto r = ml_defender::ddos_v2::evaluate(x, ml_defender::ddos_v2::kTrainK);
        const bool e1 = std::atoi(c[7].c_str()) == 1;
        const double p0 = std::strtod(c[8].c_str(), nullptr);
        const double p1 = std::strtod(c[9].c_str(), nullptr);
        const int cl = std::atoi(c[10].c_str());
        bool ok = (r.stage1 == e1) && (r.clase == cl);
        if (ok && r.stage1) {
            ok = std::bit_cast<std::uint64_t>(r.p0) == std::bit_cast<std::uint64_t>(p0) &&
                 std::bit_cast<std::uint64_t>(r.p1) == std::bit_cast<std::uint64_t>(p1);
        }
        if (!ok) {
            if (bad < 10) {
                std::fprintf(stderr, "[DDOS-V2-PARITY] fila %ld: py e1=%d clase=%d p1=%.17g | cpp e1=%d clase=%d p1=%.17g\n",
                             n + 2, e1 ? 1 : 0, cl, p1, r.stage1 ? 1 : 0, r.clase, r.p1);
            }
            ++bad;
        }
        ++n;
    }
    std::printf("[DDOS-V2-PARITY] filas=%ld discrepancias=%ld\n", n, bad);
    return (bad == 0 && n > 0) ? 0 : 1;
}
