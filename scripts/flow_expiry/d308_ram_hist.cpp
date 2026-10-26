// DAY308 — RAM del histograma de longitudes por flujo (len_hist, [DDOS-SNAP-D290]). SOLO MEDIDA: enlaza el
// ShardedFlowManager real. Complementa a d307_ram_flujo (fase A: flujos de 1 paquete; fase B: 1 flujo con una sola
// longitud), que no ejercitan el crecimiento del histograma: len_hist crece con las longitudes DISTINTAS del flujo.
//
// Fase C (flujos "anchos"): F flujos distintos, cada uno con un paquete de cada longitud de [LMIN, LMAX];
//   VmRSS cada PASO flujos -> bytes por flujo en el peor caso (lo que un atacante puede forzar variando la
//   longitud de sus paquetes). Con LMIN = LMAX - 1 da la base (2 longitudes) para restar.
//   Un solo flujo no sirve: el RSS crece a saltos de pagina y de arena de malloc; hacen falta muchos flujos.
//   La medida es la PENDIENTE entre filas (bytes_por_flujo_tramo): la media desde el arranque arrastra un coste fijo
//   (arena, paginas) que en flujos pequenos domina y baja fila a fila sin converger (medido DAY308).
//
// Uso:
//   d308_ram_hist C SHARDS MAX_POR_SHARD F LMIN LMAX PASO
// Salida: TSV por stdout, con una cabecera "# ..." con los parametros efectivos.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "main.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

using namespace sniffer;
using namespace sniffer::flow;

static long vmrss_kb() {
    std::ifstream f("/proc/self/status");
    std::string l;
    while (std::getline(f, l))
        if (l.rfind("VmRSS:", 0) == 0) return std::strtol(l.c_str() + 6, nullptr, 10);
    return -1;
}

static bool entero(const char* s, unsigned long long lo, unsigned long long hi, unsigned long long& v) {
    char* fin = nullptr;
    v = std::strtoull(s, &fin, 10);
    return s[0] && !*fin && v >= lo && v <= hi;
}

static SimpleEvent paquete(const FlowKey& k, uint32_t len, uint64_t ts) {
    SimpleEvent e{};
    e.src_ip = k.src_ip;
    e.dst_ip = k.dst_ip;
    e.src_port = k.src_port;
    e.dst_port = k.dst_port;
    e.protocol = k.protocol;
    e.packet_len = len;
    e.ip_header_len = 20;
    e.l4_header_len = 8;
    e.timestamp = ts;
    return e;
}

int main(int argc, char** argv) {
    const std::string fase = argc > 1 ? argv[1] : "";
    auto& mgr = ShardedFlowManager::instance();
    unsigned long long a, b, c, d, e2, f, g;  // argumentos validados uno a uno
    if (fase == "C" && argc == 8 && entero(argv[2], 1, 1024, a) && entero(argv[3], 1, 10'000'000, b) &&
        entero(argv[4], 1, 100'000'000, c) && entero(argv[5], 1, 65535, d) && entero(argv[6], 1, 65535, e2) &&
        d <= e2 && entero(argv[7], 1, 100'000'000, g)) {
        mgr.initialize(ShardedFlowManager::Config{.shard_count = (size_t)a, .max_flows_per_shard = (size_t)b,
                                                  .idle_timeout_ns = 120'000'000'000ULL});
        const long rss0 = vmrss_kb();
        std::printf("# fase=C shards=%llu max_por_shard=%llu cap=%llu flujos=%llu lmin=%llu lmax=%llu "
                    "longitudes_por_flujo=%llu paso=%llu rss0_kb=%ld\n",
                    a, b, a * b, c, d, e2, e2 - d + 1, g, rss0);
        std::printf("flujos\tvmrss_kb\tdelta_kb\tbytes_por_flujo_media\tbytes_por_flujo_tramo\n");
        long r_prev = rss0;
        unsigned long long f_prev = 0;
        uint64_t ts = 1'000'000'000ULL;
        for (f = 1; f <= c; ++f) {
            const FlowKey k{.src_ip = 0x0A000000u | (uint32_t)(f & 0xFFFFFF), .dst_ip = 0x0A800001,
                            .src_port = (uint16_t)(1024 + (f >> 24)), .dst_port = 53, .protocol = 17};
            for (unsigned long long len = d; len <= e2; ++len)
                mgr.add_packet(k, paquete(k, (uint32_t)len, ts += 1'000ULL));
            if (f % g == 0 || f == c) {
                const long r = vmrss_kb();
                // pendiente desde la fila anterior; la primera fila no tiene anterior: su tramo arrastra el coste fijo
                std::printf("%llu\t%ld\t%ld\t%.1f\t%.1f\n", f, r, r - rss0, 1024.0 * (double)(r - rss0) / (double)f,
                            1024.0 * (double)(r - r_prev) / (double)(f - f_prev));
                r_prev = r;
                f_prev = f;
            }
        }
        return 0;
    }
    std::fprintf(stderr, "uso: d308_ram_hist C SHARDS MAX_POR_SHARD F LMIN LMAX PASO\n");
    return 2;
}
