// firewall-acl-agent/tests/unit/test_protegidos_rp_filter.cpp — [PROTEGIDOS-RP-FILTER-D321] ADR-060 H-F (8e.4c,
// DEBT-FW-ANTISPOOF-RP-FILTER-001). Test de cierre: un árbol /proc falso con valores 0, 1 y 2 y lo que no se puede leer;
// se comprueba el valor efectivo (max(all, interfaz), como el kernel), la línea del log y que nunca se sale de la raíz.
// Sin root ni kernel: directorios temporales.
#include "firewall/protegidos_rp_filter.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

using namespace mldefender::firewall;
namespace fs = std::filesystem;

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

static bool tiene(const std::string& s, const std::string& x) { return s.find(x) != std::string::npos; }

static void escribe(const fs::path& d, const std::string& iface, const std::string& valor) {
    fs::create_directories(d / iface);
    std::ofstream(d / iface / "rp_filter") << valor;
}

static const RpFilterInterfaz* busca(const std::vector<RpFilterInterfaz>& v, const std::string& i) {
    for (const auto& r : v)
        if (r.interfaz == i) return &r;
    return nullptr;
}

int main() {
    const fs::path base = fs::temp_directory_path() / ("rpf_" + std::to_string(::getpid()));
    fs::remove_all(base);
    const fs::path d = base / "conf";

    // R1 all=0: el efectivo es el de la interfaz (0, 1, 2)
    escribe(d, "all", "0\n");
    escribe(d, "eth0", "0\n");
    escribe(d, "eth1", "1\n");
    escribe(d, "eth2", "2\n");
    {
        const auto v = leer_rp_filter({"eth2", "eth0", "eth1", "eth1"}, d.string());
        CHECK(v.size() == 3);  // sin repetir
        CHECK(v.size() == 3 && v[0].interfaz == "eth0" && v[1].interfaz == "eth1" && v[2].interfaz == "eth2");
        const auto* a = busca(v, "eth0");
        const auto* b = busca(v, "eth1");
        const auto* c = busca(v, "eth2");
        CHECK(a && a->todas == 0 && a->propio == 0 && a->efectivo == 0);
        CHECK(b && b->todas == 0 && b->propio == 1 && b->efectivo == 1);
        CHECK(c && c->todas == 0 && c->propio == 2 && c->efectivo == 2);
        const std::string l = linea_rp_filter(v, true);
        CHECK(tiene(l, "[PROTEGIDOS-RP-FILTER] eth0=0 (all=0 if=0, sin filtro) eth1=1 (all=0 if=1, estricto) "
                       "eth2=2 (all=0 if=2, laxo)"));
        CHECK(tiene(l, "max(all, interfaz)"));
        CHECK(tiene(l, "solo se informa, no se cambia"));
    }

    // R2 all=2 manda sobre las interfaces con 0 y 1; all=1 sobre la de 0 pero no sobre la de 2
    escribe(d, "all", "2");
    {
        const auto v = leer_rp_filter({"eth0", "eth1", "eth2"}, d.string());
        CHECK(busca(v, "eth0")->efectivo == 2);
        CHECK(busca(v, "eth1")->efectivo == 2);
        CHECK(busca(v, "eth2")->efectivo == 2);
    }
    escribe(d, "all", "1");
    {
        const auto v = leer_rp_filter({"eth0", "eth2"}, d.string());
        CHECK(busca(v, "eth0")->efectivo == 1);
        CHECK(busca(v, "eth2")->efectivo == 2);
        CHECK(tiene(linea_rp_filter(v, true), "eth0=1 (all=1 if=0, estricto)"));
    }

    // R3 lo que no se puede leer: interfaz que no existe, valor fuera de [0, 2], basura, fichero vacío
    escribe(d, "all", "0");
    escribe(d, "eth3", "7");
    escribe(d, "eth4", "x");
    escribe(d, "eth5", "");
    {
        const auto v = leer_rp_filter({"noexiste", "eth3", "eth4", "eth5"}, d.string());
        for (const auto& r : v) CHECK(r.efectivo == -1 && r.propio == -1 && r.todas == 0);
        const std::string l = linea_rp_filter(v, true);
        CHECK(tiene(l, "noexiste=? (all=0 if=?, ilegible)"));
        CHECK(tiene(l, "eth3=? (all=0 if=?, ilegible)"));
    }

    // R4 all ilegible: ninguna interfaz tiene efectivo, aunque la suya se lea
    fs::remove(d / "all" / "rp_filter");
    {
        const auto v = leer_rp_filter({"eth1"}, d.string());
        CHECK(v.size() == 1 && v[0].todas == -1 && v[0].propio == 1 && v[0].efectivo == -1);
        CHECK(tiene(linea_rp_filter(v, true), "eth1=? (all=? if=1, ilegible)"));
    }
    escribe(d, "all", "0");

    // R5 nunca fuera de la raíz: "..", "." y nombres con '/' no se leen (aunque haya un rp_filter justo encima)
    std::ofstream(base / "rp_filter") << "1";
    escribe(base / "otro", "x", "1");
    {
        const auto v = leer_rp_filter({"..", ".", "../otro/x", "a/b", "", std::string(16, 'a')}, d.string());
        CHECK(v.size() == 6);
        for (const auto& r : v) CHECK(r.efectivo == -1 && r.todas == -1 && r.propio == -1);
    }

    // R6 sin manifiesto y manifiesto sin entradas IPv4: lo dice, no queda en silencio
    CHECK(tiene(linea_rp_filter({}, false), "[PROTEGIDOS-RP-FILTER] sin manifiesto vigente"));
    CHECK(tiene(linea_rp_filter({}, true), "no trae entradas IPv4"));

    // R7 la raíz por defecto es la del kernel (en el banco y en el defender existe conf/all/rp_filter)
    CHECK(std::string(kRaizRpFilter) == "/proc/sys/net/ipv4/conf");
    {
        const auto v = leer_rp_filter({"lo"});
        CHECK(v.size() == 1 && v[0].todas >= 0 && v[0].propio >= 0 && v[0].efectivo >= 0);
    }

    fs::remove_all(base);
    std::cout << "test_protegidos_rp_filter: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
