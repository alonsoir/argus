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
    {  // 7. [SOMBRA-AISLADO-D311] DROP aislados (4 en una ventana, m=5): sin INICIO, un AISLADO con los 4
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        rafaga(p, 100, 4, "192.168.100.12", "192.168.100.11", out);
        CHECK(p.drop_pendientes_fuera() == 4 && p.drop_pendientes_episodio() == 0);
        tick(p, 105, out);
        auto a = p.take_aislados();
        CHECK(out.empty() && a.size() == 1 && p.victims() == 0);
        if (a.size() == 1) {
            CHECK(a[0].drop_events == 4 && a[0].start_s == 100 && a[0].end_s == 105 && a[0].dst_ip == "192.168.100.12");
            CHECK(!a[0].top_sources.empty() && a[0].top_sources[0].first == "192.168.100.11" &&
                  a[0].top_sources[0].second == 4);
            CHECK(mldefender::firewall::format_ddos_shadow_aislado(a[0]).rfind("AISLADO victima=192.168.100.12 ", 0) == 0);
        }
        CHECK(p.take_aislados().empty() && p.drop_pendientes_fuera() == 0);  // se entregan una sola vez
    }
    {  // 8. [SOMBRA-AISLADO-D311] el caso 2 (4 DROP/s 60 s, nunca empieza) ya no pierde nada: 240 en AISLADO
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        uint64_t aisl = 0;
        for (int64_t t = 100; t < 160; ++t) {
            rafaga(p, t, 4, "192.168.100.1", "10.0.0.1", out);
            for (auto& r : p.take_aislados()) aisl += r.drop_events;
        }
        tick(p, 300, out);
        for (auto& r : p.take_aislados()) aisl += r.drop_events;
        CHECK(out.empty() && aisl == 240 && p.drop_pendientes_fuera() == 0);
    }
    {  // 9. [SOMBRA-AISLADO-D311] un episodio no deja AISLADO; DROP sueltos tras su FIN si (3 en 300)
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        for (int64_t t = 100; t < 190; ++t) rafaga(p, t, 30, "192.168.100.1", "192.168.100.50", out);
        CHECK(p.drop_pendientes_episodio() > 0);
        tick(p, 250, out);
        CHECK(out.size() == 2 && p.take_aislados().empty());
        rafaga(p, 300, 3, "192.168.100.1", "192.168.100.50", out);
        tick(p, 302, out);
        auto a = p.take_aislados();
        CHECK(out.size() == 2 && a.size() == 1 && !a.empty() && a[0].drop_events == 3 && a[0].start_s == 300);
        if (out.size() == 2) CHECK(out[1].drop_events == 2700);
    }
    {  // 10. [SOMBRA-AISLADO-D311] identidad: todo DROP sumado acaba en un FIN o en un AISLADO (secuencia fija)
        DdosShadowPolicy p(P);
        std::vector<DdosShadowRecord> out;
        uint64_t sumados = 0, aisl = 0;
        uint32_t x = 12345u;
        const char* vict[3] = {"10.1.0.1", "10.1.0.2", "10.1.0.3"};
        for (int64_t t = 1000; t < 1600; ++t) {
            tick(p, t, out);
            for (auto& r : p.take_aislados()) aisl += r.drop_events;
            for (int v = 0; v < 3; ++v) {
                x = x * 1103515245u + 12345u;
                int n = static_cast<int>((x >> 16) % 9);  // 0-8 DROP por ventana y victima: unas veces episodio, otras no
                if (v == 2 && t > 1300) n = 0;            // una victima se calla antes del final
                for (int i = 0; i < n; ++i) {
                    p.add_drop(vict[v], 17, t, "203.0.113.7", 0.8, 5.0, "e", "m");
                    ++sumados;
                }
            }
        }
        tick(p, 100000, out);
        for (auto& r : p.take_aislados()) aisl += r.drop_events;
        uint64_t fin = 0;
        int nfin = 0;
        for (auto& r : out) {
            if (!r.inicio) { fin += r.drop_events; ++nfin; }
        }
        CHECK(nfin > 0 && aisl > 0);
        CHECK(fin + aisl == sumados);
        CHECK(p.drop_pendientes_fuera() == 0 && p.drop_pendientes_episodio() == 0 && p.victims() == 0);
    }
    std::printf("[DDOS-SHADOW-TEST] %s (%d fallos)\n", fallos ? "FALLA" : "OK", fallos);
    return fallos ? 1 : 0;
}
