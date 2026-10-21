// test_ddos_mitigacion.cpp -- [DDOS-MITIGACION-D301] decision por origen (NADA/ESPERAR/BLOQUEAR/RENOVAR),
// un episodio = un strike, desborde sin strike, purga, escalones cortos, y coherencia de en_episodio() con los
// registros INICIO/FIN de la sombra. Sin root.
#include "firewall/ddos_mitigacion.hpp"
#include "firewall/ddos_shadow_policy.hpp"

#include <iostream>
#include <string>
#include <vector>

using namespace mldefender::firewall;
using A = AccionMitigacion;

static int g_total = 0;
static int g_fallos = 0;
#define CHECK(c)                                                            \
    do {                                                                    \
        ++g_total;                                                          \
        if (!(c)) {                                                         \
            ++g_fallos;                                                     \
            std::cerr << "FALLA linea " << __LINE__ << ": " #c << std::endl; \
        }                                                                   \
    } while (0)

static DdosMitigacionParams on(int min_drops = 1, int max_origenes = 100000) {
    DdosMitigacionParams p;
    p.habilitada = true;
    p.min_drops_origen = min_drops;
    p.max_origenes = max_origenes;
    return p;
}

int main() {
    const std::string V = "10.0.0.1";
    const std::string O = "203.0.113.5";
    {  // 1. deshabilitada (defecto): nunca actua ni sigue nada
        DdosMitigacion m{DdosMitigacionParams{}};
        CHECK(m.decidir(V, 17, O, true) == A::NADA);
        CHECK(m.origenes_seguidos() == 0);
    }
    {  // 2. fuera de episodio: un DROP aislado no bloquea
        DdosMitigacion m{on()};
        CHECK(m.decidir(V, 17, O, false) == A::NADA);
        CHECK(m.victimas_seguidas() == 0);
    }
    {  // 3. min_drops_origen = 1: bloquea al primero y luego solo renueva
        DdosMitigacion m{on()};
        CHECK(m.decidir(V, 17, O, true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, O, true) == A::RENOVAR);
        CHECK(m.decidir(V, 17, O, true) == A::RENOVAR);
        CHECK(m.origenes_seguidos() == 1);
    }
    {  // 4. min_drops_origen = 3
        DdosMitigacion m{on(3)};
        CHECK(m.decidir(V, 17, O, true) == A::ESPERAR);
        CHECK(m.decidir(V, 17, O, true) == A::ESPERAR);
        CHECK(m.decidir(V, 17, O, true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, O, true) == A::RENOVAR);
    }
    {  // 5. independencia por origen y por victima {dst, proto}
        DdosMitigacion m{on()};
        CHECK(m.decidir(V, 17, "198.51.100.1", true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, "198.51.100.2", true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, "198.51.100.1", true) == A::RENOVAR);
        CHECK(m.decidir("10.0.0.2", 17, "198.51.100.1", true) == A::BLOQUEAR);  // otra victima = otro episodio
        CHECK(m.decidir(V, 6, "198.51.100.1", true) == A::BLOQUEAR);            // otro proto = otra victima
        CHECK(m.victimas_seguidas() == 3);
        CHECK(m.origenes_seguidos() == 4);
    }
    {  // 6. episodio nuevo = strike nuevo
        DdosMitigacion m{on()};
        CHECK(m.decidir(V, 17, O, true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, O, true) == A::RENOVAR);
        CHECK(m.decidir(V, 17, O, false) == A::NADA);  // FIN: se olvida el episodio
        CHECK(m.origenes_seguidos() == 0);
        CHECK(m.decidir(V, 17, O, true) == A::BLOQUEAR);
    }
    {  // 7. desborde: por encima de max_origenes se bloquea sin strike y se cuenta
        DdosMitigacion m{on(1, 2)};
        CHECK(m.decidir(V, 17, "192.0.2.1", true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, "192.0.2.2", true) == A::BLOQUEAR);
        CHECK(m.decidir(V, 17, "192.0.2.3", true) == A::RENOVAR);
        CHECK(m.decidir(V, 17, "192.0.2.3", true) == A::RENOVAR);
        CHECK(m.desbordes() == 2);
        CHECK(m.origenes_seguidos() == 2);
        CHECK(m.decidir(V, 17, "192.0.2.1", true) == A::RENOVAR);
    }
    {  // 8. purgar olvida las victimas fuera de episodio
        DdosMitigacion m{on()};
        CHECK(m.decidir("10.0.0.1", 17, "192.0.2.1", true) == A::BLOQUEAR);
        CHECK(m.decidir("10.0.0.2", 17, "192.0.2.2", true) == A::BLOQUEAR);
        CHECK(m.decidir("10.0.0.2", 17, "192.0.2.3", true) == A::BLOQUEAR);
        const auto n = m.purgar([](const std::string& dst, uint32_t) { return dst == "10.0.0.2"; });
        CHECK(n == 1);
        CHECK(m.victimas_seguidas() == 1);
        CHECK(m.origenes_seguidos() == 2);
    }
    {  // 9. escalones cortos (solo pruebas)
        const auto c = escalones_cortos({60, 3600, 86400}, 3600);
        CHECK(c.size() == 1 && c[0] == 60);
        CHECK(escalones_cortos({3600, 86400, 604800, 2073600}, 3600).empty());
    }
    {  // 10. en_episodio() coherente con INICIO/FIN de la sombra en cada paso
        DdosShadowParams sp;
        sp.m = 1;
        sp.n = 1;
        sp.k = 1;
        sp.hold_windows = 2;
        DdosShadowPolicy pol{sp};
        bool esperado = false;
        int inicios = 0;
        int fines = 0;
        int coherentes = 0;
        int pasos = 0;
        auto paso = [&](int64_t t, bool drop) {
            for (const auto& r : pol.advance(t)) {
                if (r.inicio) {
                    esperado = true;
                    ++inicios;
                } else {
                    esperado = false;
                    ++fines;
                }
            }
            if (drop) {
                pol.add_drop("10.0.0.9", 17, t, "203.0.113.9", 0.9, 5.0, "e" + std::to_string(t), "ddos_v2@test");
            }
            ++pasos;
            if (pol.en_episodio("10.0.0.9", 17) == esperado) {
                ++coherentes;
            } else {
                std::cerr << "incoherente en t=" << t << " esperado=" << esperado << std::endl;
            }
        };
        for (int64_t t = 100; t <= 104; ++t) paso(t, true);
        for (int64_t t = 105; t <= 115; ++t) paso(t, false);
        CHECK(coherentes == pasos);
        CHECK(inicios == 1);
        CHECK(fines == 1);
        CHECK(!pol.en_episodio("10.0.0.9", 17));
        CHECK(!pol.en_episodio("10.0.0.10", 17));
    }
    std::cout << "test_ddos_mitigacion: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
