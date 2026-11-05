// test_argus_cadena_root.cpp -- [ARGUS-CADENA-D301] reglas base de aRGus contra el KERNEL real.
// Requiere root (make test-firewall-e2e). Sin root sale con 77 = Skipped en ctest (SKIP_RETURN_CODE), nunca un
// Passed falso. Comprueba: blacklist con timeout real, un único salto INPUT -> cadena en posición 1, dentro solo
// protegidos RETURN y blacklist DROP, sin ACCEPT ni rate limiting, idempotencia (dos llamadas) y limpieza completa.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D-A: el set de protegidos es hash:net,iface; la regla casa origen E interfaz
// de entrada (src,src); su contenido se sustituye de forma atómica (temporal + swap) y se lee el tipo del set.
#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"

#include <unistd.h>
#include <sys/wait.h>

#include <cstdio>
#include <iostream>
#include <sstream>
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

static std::vector<std::string> lineas(const std::string& s) {
    std::vector<std::string> v;
    std::istringstream is(s);
    std::string l;
    while (std::getline(is, l)) v.push_back(l);
    return v;
}

static bool tiene(const std::string& s, const std::string& sub) { return s.find(sub) != std::string::npos; }
static bool en_set(const std::string& set, const std::string& elem) {
    return sh("ipset test " + set + " " + elem + " >/dev/null 2>&1; echo $?").rfind("0", 0) == 0;
}

int main() {
    if (::geteuid() != 0) {
        std::cout << "SALTADO: requiere root (make test-firewall-e2e PROFILE=...)" << std::endl;
        return 77;
    }
    const std::string CH = "ARGUS_T301";
    const std::string PR = "d318t_prot";
    const std::string MAL = "d318t_mal";
    const std::string BL = "d301t_bl";
    // hash:net,iface casa por NOMBRE de interfaz, exista o no en esta máquina (la del lab hacia la LAN es eth2).
    const std::string IF = "eth2";
    auto limpiar = [&]() {
        for (int i = 0; i < 8; ++i) sh("iptables -t filter -D INPUT -j " + CH);
        sh("iptables -t filter -F " + CH);
        sh("iptables -t filter -X " + CH);
        for (const auto& s : {PR, PR + "_n", MAL, BL}) sh("ipset destroy " + s);
    };
    limpiar();

    IPSetWrapper ips;
    IPSetConfig pr;
    pr.name = PR;
    pr.type = IPSetType::HASH_NET_IFACE;
    pr.family = IPSetFamily::INET;
    pr.timeout = 0;
    pr.maxelem = 65536;
    CHECK(static_cast<bool>(ips.create_set(pr)));
    CHECK(ips.set_type(PR).value_or("") == "hash:net,iface");
    CHECK(!ips.set_type("d318t_no_existe").has_value());
    IPSetConfig mal;
    mal.name = MAL;
    mal.type = IPSetType::HASH_NET;
    mal.family = IPSetFamily::INET;
    CHECK(static_cast<bool>(ips.create_set(mal)));
    CHECK(ips.set_type(MAL).value_or("") == "hash:net");

    // Sustitución atómica: primera carga, segunda carga (sustituye, no suma), vacía, y entradas malas (no toca nada)
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}, {"192.168.100.61/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.20," + IF));
    CHECK(!en_set(PR, "192.168.100.20,eth0"));
    CHECK(en_set(PR, "192.168.100.61," + IF));
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.20," + IF));
    CHECK(!en_set(PR, "192.168.100.61," + IF));
    CHECK(!ips.replace_net_iface(PR, {{"192.168.100.30/32", IF}, {"1.2.3.4;rm", IF}}, 65536));
    CHECK(!ips.replace_net_iface(PR, {{"192.168.100.30/32", "eth2 x"}}, 65536));
    CHECK(en_set(PR, "192.168.100.20," + IF));   // un rechazo no toca el set
    CHECK(!en_set(PR, "192.168.100.30," + IF));
    CHECK(!tiene(sh("ipset list -n"), PR + "_n"));   // el temporal no queda
    CHECK(!ips.replace_net_iface("d318t_no_existe", {{"192.168.100.20/32", IF}}, 65536));
    CHECK(!ips.replace_net_iface(MAL, {{"192.168.100.20/32", IF}}, 65536));   // swap entre tipos distintos: falla
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {}, 65536)));
    CHECK(!en_set(PR, "192.168.100.20," + IF));
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}}, 65536)));

    IPSetConfig bl;
    bl.name = BL;
    bl.type = IPSetType::HASH_IP;
    bl.family = IPSetFamily::INET;
    bl.timeout = 60;
    CHECK(static_cast<bool>(ips.create_set(bl)));
    IPSetEntry e{"203.0.113.77"};
    e.timeout = 30;
    CHECK(static_cast<bool>(ips.add_batch(BL, {e})));
    CHECK(ips.test(BL, "203.0.113.77"));

    FirewallConfig fc;
    fc.blacklist_chain = CH;
    fc.protegidos_ipset = PR;
    fc.blacklist_ipset = BL;
    fc.enable_rate_limiting = false;
    IPTablesWrapper ipt;
    for (int vuelta = 1; vuelta <= 2; ++vuelta) {
        CHECK(static_cast<bool>(ipt.setup_base_rules(fc)));
        const auto in = lineas(sh("iptables -t filter -S INPUT"));
        int saltos = 0;
        std::string primera;
        for (const auto& l : in) {
            if (l.rfind("-A INPUT", 0) == 0) {
                if (primera.empty()) primera = l;
                if (tiene(l, "-j " + CH)) ++saltos;
            }
            CHECK(!tiene(l, "RATELIMIT"));
        }
        CHECK(saltos == 1);
        CHECK(tiene(primera, "-j " + CH));
        std::vector<std::string> reglas;
        for (const auto& l : lineas(sh("iptables -t filter -S " + CH))) {
            if (l.rfind("-A " + CH, 0) == 0) reglas.push_back(l);
            CHECK(!tiene(l, "ACCEPT"));
        }
        CHECK(reglas.size() == 2);
        if (reglas.size() == 2) {
            CHECK(tiene(reglas[0], "--match-set " + PR + " src,src") && tiene(reglas[0], "-j RETURN"));
            CHECK(tiene(reglas[0], "argus-protegidos"));
            CHECK(tiene(reglas[1], "--match-set " + BL + " src") && tiene(reglas[1], "-j DROP"));
        }
        std::cout << "vuelta " << vuelta << ": saltos=" << saltos << " reglas_en_cadena=" << reglas.size()
                  << (reglas.empty() ? std::string() : " protegidos: " + reglas[0]) << std::endl;
    }
    // Con la cadena enganchada, el set sigue sustituyéndose (References > 0)
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.21/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.21," + IF) && !en_set(PR, "192.168.100.20," + IF));
    CHECK(tiene(sh("iptables -t filter -S " + CH), "--match-set " + PR + " src,src"));

    const std::string lista = sh("ipset list " + BL);
    const auto pos = lista.find("203.0.113.77 timeout ");
    CHECK(pos != std::string::npos);
    if (pos != std::string::npos) {
        const long t = std::strtol(lista.c_str() + pos + std::string("203.0.113.77 timeout ").size(), nullptr, 10);
        std::cout << "timeout restante de 203.0.113.77 = " << t << " s" << std::endl;
        CHECK(t >= 1 && t <= 30);
    }

    // Sin set de protegidos (tipo equivocado en el arranque): solo la regla del blacklist
    FirewallConfig fc2 = fc;
    fc2.protegidos_ipset = "";
    CHECK(static_cast<bool>(ipt.setup_base_rules(fc2)));
    int n = 0;
    for (const auto& l : lineas(sh("iptables -t filter -S " + CH))) {
        if (l.rfind("-A " + CH, 0) == 0) ++n;
    }
    CHECK(n == 1);

    limpiar();
    CHECK(!tiene(sh("iptables -t filter -S INPUT"), CH));
    CHECK(!tiene(sh("ipset list -n"), PR));
    std::cout << "test_argus_cadena_root: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
