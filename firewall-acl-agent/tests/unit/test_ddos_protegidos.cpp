// test_ddos_protegidos.cpp — [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001. Standalone, CHECK propio.
#include "firewall/ddos_protegidos.hpp"
#include <iostream>
#include <sstream>

using namespace mldefender::firewall;
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

static RangosProtegidos construir(const std::vector<std::string>& dmz, const std::vector<std::string>& intranet,
                                  const std::vector<std::string>& ext, std::string& log) {
    std::ostringstream o;
    RangosProtegidos r = construir_rangos_protegidos(dmz, intranet, ext, o);
    log = o.str();
    return r;
}

int main() {
    std::string log;

    // 1. Host unico (lab: .61 simula un host interno); .50 no protegido.
    {
        auto r = construir({}, {"192.168.100.61/32"}, {}, log);
        CHECK(!r.por_defecto);
        CHECK(r.categoria_de("192.168.100.61") == C::INTRANET);
        CHECK(r.categoria_de("192.168.100.50") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.100.51") == C::NINGUNA);
        CHECK(log.find("[CONFIG] ddos_protegidos.intranet += 192.168.100.61/32 (JSON)") != std::string::npos);
    }
    // 2. Red /24 y frontera; red no normalizada en el JSON; IP sin prefijo = host.
    {
        auto r = construir({"192.168.100.77/24"}, {"10.1.2.3"}, {}, log);
        CHECK(r.categoria_de("192.168.100.1") == C::DMZ);
        CHECK(r.categoria_de("192.168.100.254") == C::DMZ);
        CHECK(r.categoria_de("192.168.101.1") == C::NINGUNA);
        CHECK(r.categoria_de("10.1.2.3") == C::INTRANET);
        CHECK(r.categoria_de("10.1.2.4") == C::NINGUNA);
    }
    // 3. Prefijo no multiplo de 8 (/12) y categoria correcta por lista.
    {
        auto r = construir({}, {}, {"172.16.0.0/12"}, log);
        CHECK(r.categoria_de("172.31.255.255") == C::EXTERNOS_CRITICOS);
        CHECK(r.categoria_de("172.32.0.1") == C::NINGUNA);
        CHECK(r.categoria_de("172.15.255.255") == C::NINGUNA);
    }
    // 4. /0 IPv4 contiene todo IPv4 y nada IPv6.
    {
        auto r = construir({"0.0.0.0/0"}, {}, {}, log);
        CHECK(r.categoria_de("8.8.8.8") == C::DMZ);
        CHECK(r.categoria_de("2001:db8::1") == C::NINGUNA);
    }
    // 5. IPv6 /64 y familias que no se mezclan.
    {
        auto r = construir({}, {"2001:db8:1:2::/64"}, {}, log);
        CHECK(r.categoria_de("2001:db8:1:2::abcd") == C::INTRANET);
        CHECK(r.categoria_de("2001:db8:1:3::1") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.1.1") == C::NINGUNA);
    }
    // 6. Entradas invalidas: se descartan con aviso y las validas siguen protegiendo; el log no se rompe.
    {
        auto r = construir({"999.1.1.1", "10.0.0.0/33"}, {"abc", "1.2.3.4;rm -rf /", "192.168.5.0/24"},
                           {"1.2.3.4\nINYECTADO"}, log);
        CHECK(!r.por_defecto);
        CHECK(r.rangos.size() == 1);
        CHECK(r.categoria_de("192.168.5.9") == C::INTRANET);
        CHECK(log.find("descartada") != std::string::npos);
        CHECK(log.find("\nINYECTADO") == std::string::npos);
    }
    // 7. Bloque ausente / listas vacias: defecto RFC 1918 + fc00::/7 como intranet.
    {
        auto r = construir({}, {}, {}, log);
        CHECK(r.por_defecto);
        CHECK(r.rangos.size() == 4);
        CHECK(r.categoria_de("10.200.3.4") == C::INTRANET);
        CHECK(r.categoria_de("172.16.5.5") == C::INTRANET);
        CHECK(r.categoria_de("172.32.0.1") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.100.50") == C::INTRANET);
        CHECK(r.categoria_de("8.8.8.8") == C::NINGUNA);
        CHECK(r.categoria_de("fd12:3456::1") == C::INTRANET);
        CHECK(r.categoria_de("2001:db8::1") == C::NINGUNA);
        CHECK(log.find("[CONFIG-DEFAULT] ddos_protegidos: ningun rango valido") != std::string::npos);
    }
    // 8. Todas las entradas invalidas: mismo defecto (el descuido grave no deja nada sin proteger).
    {
        auto r = construir({"x"}, {"300.0.0.0/8"}, {"::/129"}, log);
        CHECK(r.por_defecto);
        CHECK(r.categoria_de("192.168.1.1") == C::INTRANET);
    }
    // 9. IP de consulta invalida o vacia: NINGUNA (no protege por error ni rompe).
    {
        auto r = construir({}, {}, {}, log);
        CHECK(r.categoria_de("") == C::NINGUNA);
        CHECK(r.categoria_de("no-es-ip") == C::NINGUNA);
    }
    // 10. Primera coincidencia gana: el orden es dmz, intranet, externos_criticos.
    {
        auto r = construir({"10.0.0.0/8"}, {"10.1.0.0/16"}, {}, log);
        CHECK(r.categoria_de("10.1.2.3") == C::DMZ);
    }

    if (g_fallos != 0) {
        std::cerr << "test_ddos_protegidos: " << g_fallos << " FALLOS de " << g_checks << " comprobaciones" << std::endl;
        return 1;
    }
    std::cout << "OK test_ddos_protegidos: " << g_checks << " comprobaciones" << std::endl;
    return 0;
}
