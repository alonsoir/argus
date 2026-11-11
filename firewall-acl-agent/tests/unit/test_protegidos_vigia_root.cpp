// test_protegidos_vigia_root.cpp -- [PROTEGIDOS-VIGIA-D320] ADR-060 D8, 8e.4a: el vigía contra el KERNEL real.
// Requiere root (make test-firewall-e2e). Sin root sale con 77 = Skipped en ctest, nunca un Passed falso. Set y cadena
// propios del test (no toca los de aRGus) y lo limpia todo al empezar y al acabar. Cada escenario estropea el kernel
// como lo haría alguien con root y comprueba que una vuelta del vigía lo detecta, lo reconcilia y lo deja bien:
//   S1 todo cuadra: nada que hacer
//   S2 una entrada de más                    S6 el salto INPUT ya no está en la posición 1
//   S3 una entrada de menos                  S7 set destruido y cadena vaciada: se recrean los dos
//   S4 una entrada cambiada a nomatch        S9 sin manifiesto vigente: el set tiene que quedar vacío
//   S5 la regla RETURN de protegidos borrada
//   S8 set de otro tipo con el mismo nombre: alarma, no se destruye y la cadena se rehace sin RETURN (lo no firmado
//      no exime); S8b el set vuelve a estar bien: se recrea, se llena y vuelve el RETURN
#include "firewall/protegidos_vigia.hpp"

#include <unistd.h>

#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

using namespace mldefender::firewall;

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

static std::string sh(const std::string& cmd) {
    std::string out;
    FILE* p = ::popen((cmd + " 2>&1").c_str(), "r");
    if (!p) return out;
    char buf[512];
    while (std::fgets(buf, sizeof(buf), p)) out += buf;
    ::pclose(p);
    return out;
}
static bool tiene(const std::string& s, const std::string& sub) { return s.find(sub) != std::string::npos; }

static const std::string CH = "ARGUS_TVIG320";
static const std::string PROT = "tvig320_prot";
static const std::string BL = "tvig320_bl";
static const uint32_t MAXE = 4096;

static void limpiar() {
    sh("while iptables -D INPUT -j " + CH + " 2>/dev/null; do :; done");
    sh("iptables -D INPUT -m comment --comment tvig320-extra 2>/dev/null");
    sh("iptables -F " + CH + " 2>/dev/null; iptables -X " + CH + " 2>/dev/null");
    sh("ipset destroy " + PROT + " 2>/dev/null; ipset destroy " + PROT + "_n 2>/dev/null; ipset destroy " + BL + " 2>/dev/null");
}

int main() {
    if (::geteuid() != 0) {
        std::cout << "SALTADO: requiere root (make test-firewall-e2e PROFILE=...)" << std::endl;
        return 77;
    }
    limpiar();
    IPSetWrapper ipset;
    IPTablesWrapper ipt;
    FirewallConfig fc;
    fc.blacklist_chain = CH;
    fc.blacklist_ipset = BL;
    fc.protegidos_ipset = PROT;
    fc.enable_rate_limiting = false;
    const std::vector<std::pair<std::string, std::string>> esp{{"192.168.100.20/32", "eth2"}, {"192.168.100.61/32", "eth2"}};

    IPSetConfig bl;
    bl.name = BL;
    bl.type = IPSetType::HASH_IP;
    bl.family = IPSetFamily::INET;
    bl.timeout = 0;
    CHECK(ipset.create_set(bl));
    CHECK(ipset.create_set(config_set_protegidos(PROT, MAXE)));
    CHECK(ipset.replace_net_iface(PROT, esp, MAXE));
    CHECK(ipt.setup_base_rules(fc));
    auto paso = [&](const std::vector<std::pair<std::string, std::string>>& e) {
        return vigia_protegidos_paso(ipset, ipt, fc, PROT, true, e, MAXE);
    };
    auto set_ok_kernel = [&]() { return comparar_protegidos_kernel(esp, ipset.list_entries_opciones(PROT)).vacia(); };
    auto reglas_ok = [&]() {
        return comprobar_reglas_protegidos(ipt.list_rules("INPUT"), ipt.list_rules(CH), CH, PROT, BL).empty();
    };

    // S1
    {
        const auto r = paso(esp);
        CHECK(!r.divergente() && r.error.empty());
    }
    // S2 de más
    sh("ipset add " + PROT + " 10.66.6.6,eth2");
    {
        const auto r = paso(esp);
        CHECK(r.set_divergente && r.set_reconciliado && !r.reglas_divergentes && r.error.empty());
        CHECK(r.diferencia.sobran.size() == 1 && tiene(r.diferencia.sobran[0], "10.66.6.6"));
        CHECK(set_ok_kernel() && !tiene(sh("ipset save " + PROT), "10.66.6.6"));
    }
    // S3 de menos
    sh("ipset del " + PROT + " 192.168.100.61,eth2");
    {
        const auto r = paso(esp);
        CHECK(r.set_divergente && r.set_reconciliado && r.diferencia.faltan.size() == 1);
        CHECK(set_ok_kernel() && tiene(sh("ipset save " + PROT), "192.168.100.61,eth2"));
    }
    // S4 nomatch
    sh("ipset del " + PROT + " 192.168.100.20,eth2; ipset add " + PROT + " 192.168.100.20,eth2 nomatch");
    CHECK(tiene(sh("ipset save " + PROT), "nomatch"));
    {
        const auto r = paso(esp);
        CHECK(r.set_divergente && r.set_reconciliado);
        CHECK(set_ok_kernel() && !tiene(sh("ipset save " + PROT), "nomatch"));
    }
    // S5 RETURN borrado
    sh("iptables -D " + CH + " 1");
    CHECK(!reglas_ok());
    {
        const auto r = paso(esp);
        CHECK(r.reglas_divergentes && r.reglas_reconciliadas && !r.set_divergente && r.error.empty());
        CHECK(reglas_ok());
    }
    // S6 salto fuera de la posición 1
    sh("iptables -I INPUT 1 -m comment --comment tvig320-extra");
    CHECK(!reglas_ok());
    {
        const auto r = paso(esp);
        CHECK(r.reglas_divergentes && r.reglas_reconciliadas);
        CHECK(reglas_ok());
    }
    sh("iptables -D INPUT -m comment --comment tvig320-extra 2>/dev/null");
    // S7 set destruido y cadena vaciada
    sh("iptables -F " + CH + "; ipset destroy " + PROT);
    CHECK(!ipset.set_type(PROT).has_value());
    {
        const auto r = paso(esp);
        CHECK(r.set_divergente && r.set_reconciliado && r.reglas_divergentes && r.reglas_reconciliadas && r.error.empty());
        CHECK(ipset.set_type(PROT).value_or("") == "hash:net,iface" && set_ok_kernel() && reglas_ok());
    }
    // S9 sin vigente (antes de S8, que deja un set ajeno)
    {
        const auto r = paso({});
        CHECK(r.set_divergente && r.set_reconciliado && r.diferencia.sobran.size() == 2);
        CHECK(ipset.list_entries_opciones(PROT).empty());
        CHECK(paso(esp).set_reconciliado && set_ok_kernel());  // y vuelve a llenarse con el vigente
    }
    // S8 set ajeno: otro tipo con el mismo nombre (y la cadena intacta, con el RETURN apuntando a él)
    sh("iptables -F " + CH + "; ipset destroy " + PROT + "; ipset create " + PROT + " hash:ip; ipset add " + PROT +
       " 10.66.6.6");
    sh("iptables -A " + CH + " -m set --match-set " + PROT + " src,src -m comment --comment argus-protegidos -j RETURN");
    sh("iptables -A " + CH + " -m set --match-set " + BL + " src -m comment --comment argus-blacklist -j DROP");
    CHECK(tiene(sh("iptables -S " + CH), "--match-set " + PROT));  // medido: iptables acepta src,src sobre hash:ip
    {
        const auto r = paso(esp);
        CHECK(r.set_divergente && r.set_tipo_ajeno && !r.set_reconciliado);
        CHECK(ipset.set_type(PROT).value_or("") == "hash:ip");  // no se ha destruido
        CHECK(r.reglas_divergentes && r.reglas_reconciliadas);   // la cadena se rehace...
        CHECK(!tiene(sh("iptables -S " + CH), "--match-set " + PROT));  // ...sin el RETURN del set ajeno
        CHECK(paso(esp).reglas_divergentes == false);            // y así se queda mientras el set siga ajeno
    }
    // S8b el set vuelve a estar bien (lo quita el admin): el vigía lo recrea, lo llena y repone el RETURN
    sh("ipset destroy " + PROT);
    {
        const auto r = paso(esp);
        CHECK(r.set_reconciliado && r.reglas_reconciliadas && r.error.empty());
        CHECK(set_ok_kernel() && reglas_ok());
    }

    limpiar();
    CHECK(!tiene(sh("iptables -S"), CH) && !ipset.set_type(PROT).has_value() && !ipset.set_type(BL).has_value());
    std::cout << "test_protegidos_vigia_root: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
