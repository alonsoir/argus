// test_protegidos_rangos.cpp (antes test_ddos_protegidos.cpp del firewall) — [PROTEGIDOS-D300] rangos protegidos: análisis de CIDR y pertenencia. Standalone, CHECK propio.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen solo del manifiesto firmado (test_protegidos_manifiesto.cpp);
// fuera construir_rangos_protegidos y el defecto RFC 1918, y con ellos sus casos.
#include "protegidos/rangos.hpp"
#include <iostream>
#include <string>
#include <vector>

using namespace argus::protegidos;
using C = CategoriaProtegida;

static int g_fallos = 0;
static int g_checks = 0;
#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FALLO linea " << __LINE__ << ": " #c << std::endl;  \
            ++g_fallos;                                                       \
        }                                                                     \
    } while (0)

static RangosProtegidos rangos(const std::vector<std::pair<std::string, C>>& v) {
    RangosProtegidos r;
    for (const auto& [cidr, cat] : v) {
        RangoProtegido x;
        if (parsear_rango(cidr, cat, x)) r.rangos.push_back(x);
    }
    return r;
}

int main() {
    // 1. Host único; vecinos no protegidos.
    {
        auto r = rangos({{"192.168.100.61/32", C::INTRANET}, {"192.168.100.20/32", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("192.168.100.61") == C::INTRANET);
        CHECK(r.categoria_de("192.168.100.20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("192.168.100.50") == C::NINGUNA);
        CHECK(std::string(nombre_categoria(C::INFRAESTRUCTURA)) == "infraestructura");
        CHECK(std::string(nombre_categoria(C::NINGUNA)) == "ninguna");
    }
    // 2. Red /24 y frontera; red no normalizada; IP sin prefijo = host.
    {
        auto r = rangos({{"192.168.100.77/24", C::DMZ}, {"10.1.2.3", C::INTRANET}});
        CHECK(r.categoria_de("192.168.100.1") == C::DMZ);
        CHECK(r.categoria_de("192.168.100.254") == C::DMZ);
        CHECK(r.categoria_de("192.168.101.1") == C::NINGUNA);
        CHECK(r.categoria_de("10.1.2.3") == C::INTRANET);
        CHECK(r.categoria_de("10.1.2.4") == C::NINGUNA);
        RangoProtegido x;
        CHECK(parsear_rango("192.168.100.77/24", C::DMZ, x) && x.red[3] == 0 && x.prefijo == 24);
    }
    // 3. Prefijo no múltiplo de 8 (/12).
    {
        auto r = rangos({{"172.16.0.0/12", C::EXTERNOS_CRITICOS}});
        CHECK(r.categoria_de("172.31.255.255") == C::EXTERNOS_CRITICOS);
        CHECK(r.categoria_de("172.32.0.1") == C::NINGUNA);
        CHECK(r.categoria_de("172.15.255.255") == C::NINGUNA);
    }
    // 4. IPv6 /128 y /64; las familias no se mezclan.
    {
        auto r = rangos({{"2001:db8:1:2::/64", C::INTRANET}, {"fd00::20/128", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("2001:db8:1:2::abcd") == C::INTRANET);
        CHECK(r.categoria_de("2001:db8:1:3::1") == C::NINGUNA);
        CHECK(r.categoria_de("fd00::20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("fd00::21") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.1.1") == C::NINGUNA);
    }
    // 5. Entradas inválidas: parsear_rango las rechaza (nunca protege por error).
    {
        RangoProtegido x;
        for (const std::string& e : {std::string("999.1.1.1"), std::string("10.0.0.0/33"), std::string("abc"),
                                     std::string("1.2.3.4;rm -rf /"), std::string("1.2.3.4\nINYECTADO"),
                                     std::string("::/129"), std::string("")}) {
            CHECK(!parsear_rango(e, C::INTRANET, x));
        }
    }
    // 6. IP de consulta inválida o vacía: NINGUNA; sin rangos, nada protegido.
    {
        auto r = rangos({{"10.0.0.0/8", C::INTRANET}});
        CHECK(r.categoria_de("") == C::NINGUNA);
        CHECK(r.categoria_de("no-es-ip") == C::NINGUNA);
        RangosProtegidos vacio;
        CHECK(vacio.categoria_de("10.1.2.3") == C::NINGUNA);
    }
    // 7. Primera coincidencia gana (el manifiesto ordena: infraestructura delante, luego lo más específico).
    {
        auto r = rangos({{"10.0.0.0/8", C::DMZ}, {"10.1.0.0/16", C::INTRANET}});
        CHECK(r.categoria_de("10.1.2.3") == C::DMZ);
    }
    // 8. El log no se rompe con entradas hostiles.
    {
        const std::string s = detalle_protegidos::saneado("a\nb\x01" + std::string(100, 'x'));
        CHECK(s.find('\n') == std::string::npos && s.size() <= 67);
    }

    if (g_fallos != 0) {
        std::cerr << "test_protegidos_rangos: " << g_fallos << " FALLOS de " << g_checks << " comprobaciones" << std::endl;
        return 1;
    }
    std::cout << "OK test_protegidos_rangos: " << g_checks << " comprobaciones" << std::endl;
    return 0;
}
