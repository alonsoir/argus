// test_protegidos_vigia.cpp -- [PROTEGIDOS-VIGIA-D320] ADR-060 D8, 8e.4a: la parte pura del vigía (sin kernel ni
// root): forma canónica de las entradas, comparación del set con el manifiesto (de más, de menos, opciones como
// nomatch, otra interfaz, duplicados, /32 implícito, red con bits de host) y comprobación de la cadena de aRGus.
#include "firewall/protegidos_vigia.hpp"

#include <algorithm>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

using namespace mldefender::firewall;
using Esp = std::vector<std::pair<std::string, std::string>>;
using Ker = std::vector<std::string>;

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

static bool contiene(const std::vector<std::string>& v, const std::string& x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}

// Wrappers falsos para el paso del vigía: lo que el kernel "tiene" y si sus operaciones dicen la verdad.
struct IpsFalso {
    bool existe = true;
    std::string tipo = "hash:net,iface";
    std::vector<std::string> entradas;
    bool mentirosa = false;  // replace_net_iface devuelve éxito sin cambiar nada
    int sustituciones = 0, creados = 0;
    std::optional<std::string> set_type(const std::string&) const {
        return existe ? std::optional<std::string>(tipo) : std::nullopt;
    }
    bool create_set(const IPSetConfig&) {
        ++creados;
        existe = true;
        tipo = "hash:net,iface";
        entradas.clear();
        return true;
    }
    std::vector<std::string> list_entries_opciones(const std::string&) const { return entradas; }
    IPSetResult<void> replace_net_iface(const std::string&, const std::vector<std::pair<std::string, std::string>>& e,
                                        uint32_t) {
        ++sustituciones;
        if (!mentirosa) {
            entradas.clear();
            for (const auto& [cidr, iface] : e) entradas.push_back(cidr + "," + iface);
        }
        return IPSetResult<void>();
    }
};
struct IptFalso {
    std::vector<std::string> input, cadena, arreglo;
    bool mentirosa = false;  // setup_base_rules devuelve éxito sin cambiar nada
    int rehechas = 0;
    std::string ultimo_prot = "(sin llamar)";
    std::vector<std::string> list_rules(const std::string& ch) const { return ch == "INPUT" ? input : cadena; }
    IPTablesResult<void> setup_base_rules(const FirewallConfig& c) {
        ++rehechas;
        ultimo_prot = c.protegidos_ipset;
        if (!mentirosa) cadena = arreglo;
        return IPTablesResult<void>();
    }
};

int main() {
    // ── forma canónica ──
    std::string c;
    CHECK(canon_protegido("192.168.100.20/32", "eth2", c) && c == "192.168.100.20/32,eth2");
    CHECK(canon_protegido("192.168.100.20", "eth2", c) && c == "192.168.100.20/32,eth2");
    CHECK(canon_protegido("192.168.100.77/24", "eth2", c) && c == "192.168.100.0/24,eth2");
    CHECK(canon_protegido("10.0.0.0/0", "eth0", c) && c == "0.0.0.0/0,eth0");
    CHECK(!canon_protegido("192.168.100.20/33", "eth2", c));
    CHECK(!canon_protegido("192.168.100.20/", "eth2", c));
    CHECK(!canon_protegido("192.168.100.20/2a", "eth2", c));
    CHECK(!canon_protegido("fc00::1/128", "eth2", c));
    CHECK(!canon_protegido("192.168.100.20/32", "", c));

    const Esp lab{{"192.168.100.20/32", "eth2"}, {"192.168.100.61/32", "eth2"}};

    // ── iguales (el kernel omite /32 en 'ipset save') ──
    CHECK(comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2", "192.168.100.61,eth2"}).vacia());
    CHECK(comparar_protegidos_kernel(lab, Ker{"192.168.100.61,eth2", "192.168.100.20,eth2"}).vacia());  // orden
    // red con bits de host en el manifiesto: el kernel guarda la red
    CHECK(comparar_protegidos_kernel(Esp{{"10.9.0.77/24", "eth2"}}, Ker{"10.9.0.0/24,eth2"}).vacia());

    // ── sobra una (inyectada a mano) ──
    {
        const auto d = comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2", "192.168.100.61,eth2", "10.66.6.6,eth2"});
        CHECK(d.sobran.size() == 1 && d.sobran[0] == "10.66.6.6,eth2" && d.faltan.empty());
    }
    // ── falta una (borrada a mano) ──
    {
        const auto d = comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2"});
        CHECK(d.sobran.empty() && d.faltan.size() == 1 && d.faltan[0] == "192.168.100.61/32,eth2");
    }
    // ── la misma IP por otra interfaz: sobra la ajena y falta la buena ──
    {
        const auto d = comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth0", "192.168.100.61,eth2"});
        CHECK(contiene(d.sobran, "192.168.100.20,eth0") && contiene(d.faltan, "192.168.100.20/32,eth2"));
    }
    // ── nomatch (anula la exención): divergencia aunque la entrada sea la del manifiesto ──
    {
        const auto d = comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2 nomatch", "192.168.100.61,eth2"});
        CHECK(contiene(d.sobran, "192.168.100.20,eth2 nomatch") && contiene(d.faltan, "192.168.100.20/32,eth2"));
    }
    // ── cualquier otra opción también ──
    CHECK(!comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2 timeout 60", "192.168.100.61,eth2"}).vacia());
    // ── líneas ilegibles: sobran tal cual ──
    {
        const auto d = comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2", "192.168.100.61,eth2", "basura"});
        CHECK(d.sobran.size() == 1 && d.sobran[0] == "basura");
    }
    // ── duplicado en el kernel (no debería poder darse; si se da, cuenta) ──
    CHECK(!comparar_protegidos_kernel(lab, Ker{"192.168.100.20,eth2", "192.168.100.20/32,eth2", "192.168.100.61,eth2"})
               .vacia());
    // ── sin vigente: el set tiene que estar vacío ──
    CHECK(comparar_protegidos_kernel(Esp{}, Ker{}).vacia());
    {
        const auto d = comparar_protegidos_kernel(Esp{}, Ker{"192.168.100.20,eth2"});
        CHECK(d.sobran.size() == 1 && d.faltan.empty());
    }
    // ── vigente con entradas y kernel vacío: faltan todas ──
    CHECK(comparar_protegidos_kernel(lab, Ker{}).faltan.size() == 2);
    // ── O(n): 4096 entradas, iguales en otro orden ──
    {
        Esp e;
        Ker k;
        for (int i = 0; i < 4096; ++i) {
            const std::string ip = "10." + std::to_string(i / 256) + "." + std::to_string(i % 256) + ".1";
            e.emplace_back(ip + "/32", "eth2");
            k.insert(k.begin(), ip + ",eth2");
        }
        CHECK(comparar_protegidos_kernel(e, k).vacia());
        k.pop_back();
        CHECK(comparar_protegidos_kernel(e, k).faltan.size() == 1);
    }

    // ── reglas ──
    const std::string CH = "ML_DEFENDER_BLACKLIST", P = "ml_defender_protegidos", B = "ml_defender_blacklist";
    const std::string RP = "-A " + CH + " -m set --match-set " + P + " src,src -m comment --comment argus-protegidos -j RETURN";
    const std::string RB = "-A " + CH + " -m set --match-set " + B + " src -m comment --comment argus-blacklist -j DROP";
    const std::vector<std::string> buena{"-N " + CH, RP, RB};
    const std::vector<std::string> in1{"-A INPUT -j " + CH, "-A INPUT -i lo -j ACCEPT"};
    CHECK(comprobar_reglas_protegidos(in1, buena, CH, P, B).empty());
    CHECK(!comprobar_reglas_protegidos({"-A INPUT -i lo -j ACCEPT", "-A INPUT -j " + CH}, buena, CH, P, B).empty());  // pos 2
    CHECK(!comprobar_reglas_protegidos({}, buena, CH, P, B).empty());                                                // sin salto
    CHECK(!comprobar_reglas_protegidos({"-A INPUT -j " + CH, "-A INPUT -j " + CH}, buena, CH, P, B).empty());        // dos
    CHECK(!comprobar_reglas_protegidos(in1, {"-N " + CH, RB}, CH, P, B).empty());          // falta el RETURN
    CHECK(!comprobar_reglas_protegidos(in1, {"-N " + CH, RB, RP}, CH, P, B).empty());      // orden cambiado
    CHECK(!comprobar_reglas_protegidos(in1, {"-N " + CH, RP, RB, "-A " + CH + " -s 10.0.0.1/32 -j RETURN"}, CH, P, B).empty());  // de más
    CHECK(!comprobar_reglas_protegidos(in1, {}, CH, P, B).empty());                       // la cadena no existe
    CHECK(comprobar_reglas_protegidos(in1, {"-N " + CH, RB}, CH, "", B).empty());          // set no utilizable: sin RETURN
    CHECK(!comprobar_reglas_protegidos(in1, {"-N " + CH, RP, RB}, CH, "", B).empty());     // ... y un RETURN sobra

    // ── el paso con wrappers falsos: solo cuenta como reconciliado lo que se vuelve a leer y cuadra ──
    {
        const Esp esp{{"192.168.100.20/32", "eth2"}};
        const std::vector<std::string> buenas{"-N " + CH, RP, RB};
        FirewallConfig fc;
        fc.blacklist_chain = CH;
        fc.blacklist_ipset = B;
        fc.protegidos_ipset = P;
        // a) el kernel cuadra: nada
        {
            IpsFalso ips; ips.entradas = {"192.168.100.20,eth2"};
            IptFalso ipt; ipt.input = in1; ipt.cadena = buenas;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(!r.divergente() && r.error.empty() && ips.sustituciones == 0 && ipt.rehechas == 0);
        }
        // b) sobra una y la sustitución funciona: reconciliado
        {
            IpsFalso ips; ips.entradas = {"192.168.100.20,eth2", "10.66.6.6,eth2"};
            IptFalso ipt; ipt.input = in1; ipt.cadena = buenas;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.set_divergente && r.set_reconciliado && r.error.empty() && ips.sustituciones == 1);
        }
        // c) la sustitución dice "hecho" y no hace nada: NO reconciliado y error (relectura)
        {
            IpsFalso ips; ips.entradas = {"192.168.100.20,eth2", "10.66.6.6,eth2"}; ips.mentirosa = true;
            IptFalso ipt; ipt.input = in1; ipt.cadena = buenas;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.set_divergente && !r.set_reconciliado && !r.error.empty());
        }
        // d) setup_base_rules dice "hecho" y no hace nada: NO reconciliadas y error (relectura)
        {
            IpsFalso ips; ips.entradas = {"192.168.100.20,eth2"};
            IptFalso ipt; ipt.input = in1; ipt.cadena = {"-N " + CH, RB}; ipt.mentirosa = true;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.reglas_divergentes && !r.reglas_reconciliadas && !r.error.empty() && ipt.rehechas == 1);
        }
        // e) setup_base_rules funciona: reconciliadas
        {
            IpsFalso ips; ips.entradas = {"192.168.100.20,eth2"};
            IptFalso ipt; ipt.input = in1; ipt.cadena = {"-N " + CH, RB}; ipt.arreglo = buenas;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.reglas_divergentes && r.reglas_reconciliadas && r.error.empty());
        }
        // f) set de otro tipo: no se toca y la cadena se rehace sin RETURN
        {
            IpsFalso ips; ips.tipo = "hash:ip";
            IptFalso ipt; ipt.input = in1; ipt.cadena = buenas; ipt.arreglo = {"-N " + CH, RB};
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.set_tipo_ajeno && ips.sustituciones == 0 && ips.creados == 0);
            CHECK(r.reglas_reconciliadas && ipt.ultimo_prot.empty());
        }
        // g) el set no existe: se crea y se llena
        {
            IpsFalso ips; ips.existe = false;
            IptFalso ipt; ipt.input = in1; ipt.cadena = buenas;
            const auto r = vigia_protegidos_paso(ips, ipt, fc, P, true, esp, 64);
            CHECK(r.set_divergente && ips.creados == 1 && r.set_reconciliado);
        }
    }

    std::cout << "test_protegidos_vigia: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
