// [DDOS-SHADOW-D293] Test de la política por víctima en sombra: misma semántica que scripts/d293_politica.py.
#include <cstdio>
#include <string>
#include <vector>

#include "firewall/ddos_shadow_policy.hpp"

using mldefender::firewall::DdosShadowParams;
using mldefender::firewall::DdosShadowPolicy;
using mldefender::firewall::DdosShadowRecord;

static int fallos = 0;
#define CHECK(c)                                                         \
    do {                                                                 \
        if (!(c)) {                                                      \
            std::fprintf(stderr, "FALLO %s:%d: %s\n", __FILE__, __LINE__, #c); \
            ++fallos;                                                    \
        }                                                                \
    } while (0)

static void tick(DdosShadowPolicy& p, int64_t t, std::vector<DdosShadowRecord>& out) {
    for (auto& r : p.advance(t)) {
        out.push_back(r);
    }
}

static void rafaga(DdosShadowPolicy& p, int64_t t, int n, const std::string& dst, const std::string& src,
                   std::vector<DdosShadowRecord>& out) {
    tick(p, t, out);
    for (int i = 0; i < n; ++i) {
        p.add_drop(dst, 17, t, src, 0.99, 9.5, "ev" + std::to_string(t) + "_" + std::to_string(i), "ddos_v2_fact_rf@test");
    }
}

int main() {
    const DdosShadowParams P{true, 5, 3, 5, 30};
    {  // 1. ataque de 90 s a 30 DROP/s: INICIO en 102, FIN en 189+30 = 219
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t = 100; t < 190; ++t) rafaga(p, t, 30, "192.168.100.1", "192.168.100.50", out);
        tick(p, 250, out);
        CHECK(out.size() == 2);
        if (out.size() == 2) {
            CHECK(out[0].inicio && out[0].start_s == 102);
            CHECK(!out[1].inicio && out[1].start_s == 102 && out[1].end_s == 219);
            CHECK(out[1].drop_events == 2700 && out[1].positive_windows == 90);
            CHECK(!out[1].top_sources.empty() && out[1].top_sources[0].first == "192.168.100.50");
        }
        CHECK(p.victims() == 0);
    }
    {  // 2. por debajo de m (4 DROP/s): nunca empieza
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t = 100; t < 160; ++t) rafaga(p, t, 4, "192.168.100.1", "10.0.0.1", out);
        tick(p, 300, out);
        CHECK(out.empty());
    }
    {  // 3. k de n con huecos: positivas en 100, 102, 104 -> INICIO en 104
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t : {100, 102, 104}) rafaga(p, t, 10, "192.168.100.1", "10.0.0.2", out);
        tick(p, 105, out);
        CHECK(out.size() == 1 && out[0].inicio && out[0].start_s == 104);
    }
    {  // 4. salto largo del reloj: FIN en última positiva + hold y víctima liberada
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t = 100; t < 110; ++t) rafaga(p, t, 10, "192.168.100.1", "10.0.0.3", out);
        tick(p, 100000, out);
        CHECK(out.size() == 2 && !out.back().inicio && out.back().end_s == 109 + 30);
        CHECK(p.victims() == 0);
    }
    {  // 5. dos víctimas independientes
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t = 100; t < 110; ++t) {
            rafaga(p, t, 10, "192.168.100.1", "10.0.0.4", out);
            if (t >= 105) {
                for (int i = 0; i < 10; ++i) p.add_drop("192.168.100.2", 6, t, "10.0.0.5", 0.9, 5.0, "x", "m");
            }
        }
        tick(p, 111, out);
        int ini1 = 0, ini2 = 0;
        for (auto& r : out) {
            if (r.inicio && r.dst_ip == "192.168.100.1") { ++ini1; CHECK(r.start_s == 102); }
            if (r.inicio && r.dst_ip == "192.168.100.2") { ++ini2; CHECK(r.start_s == 107 && r.proto == 6); }
        }
        CHECK(ini1 == 1 && ini2 == 1);
    }
    {  // 6. reloj que retrocede: no cierra ventanas ni rompe nada
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        rafaga(p, 100, 10, "192.168.100.1", "10.0.0.6", out);
        tick(p, 50, out);
        CHECK(out.empty() && p.victims() == 1);
    }
    std::printf("[DDOS-SHADOW-TEST] %s (%d fallos)\n", fallos ? "FALLA" : "OK", fallos);
    return fallos ? 1 : 0;
}
