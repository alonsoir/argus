// DAY308 — suelo de medida del reloj: cuanto cuesta un par steady_clock::now() vacio (la misma medida que
// rodea a populate y a la foto en d308_paridad_tolerancia). SOLO MEDIDA.
// Uso: d308_coste_reloj N
#include <chrono>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
    const long n = argc == 2 ? std::strtol(argv[1], nullptr, 10) : 0;
    if (n < 1 || n > 100'000'000) { std::fprintf(stderr, "uso: d308_coste_reloj N (1..1e8)\n"); return 2; }
    double total = 0, maximo = 0;
    for (long i = 0; i < n; ++i) {
        const auto t0 = std::chrono::steady_clock::now();
        const double ns = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now() - t0).count();
        total += ns;
        if (ns > maximo) maximo = ns;
    }
    std::printf("pares=%ld region_vacia_us_medio=%.3f region_vacia_us_max=%.1f\n", n, total / 1000.0 / (double)n,
                maximo / 1000.0);
    return 0;
}
