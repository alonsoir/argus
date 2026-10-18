// test_argus_cadena_root.cpp -- [ARGUS-CADENA-D301] reglas base de aRGus contra el KERNEL real.
// Requiere root (make test-firewall-e2e). Sin root sale con 77 = Skipped en ctest (SKIP_RETURN_CODE), nunca un
// Passed falso. Comprueba: whitelist hash:net sin netmask, pertenencia por CIDR, blacklist con timeout real, un
// unico salto INPUT -> cadena en posicion 1, dentro solo whitelist RETURN y blacklist DROP, sin ACCEPT ni rate
// limiting, idempotencia (dos llamadas) y limpieza completa.
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

int main() {
    if (::geteuid() != 0) {
        std::cout << "SALTADO: requiere root (make test-firewall-e2e PROFILE=...)" << std::endl;
        return 77;
    }
    const std::string CH = "ARGUS_T301";
    const std::string WL = "d301t_wl";
    const std::string BL = "d301t_bl";
    auto limpiar = [&]() {
        for (int i = 0; i < 8; ++i) sh("iptables -t filter -D INPUT -j " + CH);
        sh("iptables -t filter -F " + CH);
        sh("iptables -t filter -X " + CH);
        sh("ipset destroy " + WL);
        sh("ipset destroy " + BL);
    };
    limpiar();

    IPSetWrapper ips;
    IPSetConfig wl;
    wl.name = WL;
    wl.type = IPSetType::HASH_NET;
    wl.family = IPSetFamily::INET;
    wl.timeout = 0;
    CHECK(static_cast<bool>(ips.create_set(wl)));  // netmask 32 por defecto: ya no se pasa a hash:net
    IPSetConfig bl;
    bl.name = BL;
    bl.type = IPSetType::HASH_IP;
    bl.family = IPSetFamily::INET;
    bl.timeout = 60;
    CHECK(static_cast<bool>(ips.create_set(bl)));

    CHECK(static_cast<bool>(ips.add_batch(WL, {IPSetEntry{"192.168.100.61/32"}, IPSetEntry{"10.0.0.0/8"}})));
    CHECK(ips.test(WL, "10.1.2.3"));
    CHECK(!ips.test(WL, "203.0.113.77"));
    IPSetEntry e{"203.0.113.77"};
    e.timeout = 30;
    CHECK(static_cast<bool>(ips.add_batch(BL, {e})));
    CHECK(ips.test(BL, "203.0.113.77"));

    FirewallConfig fc;
    fc.blacklist_chain = CH;
    fc.whitelist_ipset = WL;
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
            CHECK(tiene(reglas[0], "--match-set " + WL + " src") && tiene(reglas[0], "-j RETURN"));
            CHECK(tiene(reglas[1], "--match-set " + BL + " src") && tiene(reglas[1], "-j DROP"));
        }
        std::cout << "vuelta " << vuelta << ": saltos=" << saltos << " reglas_en_cadena=" << reglas.size() << std::endl;
    }

    const std::string lista = sh("ipset list " + BL);
    const auto pos = lista.find("203.0.113.77 timeout ");
    CHECK(pos != std::string::npos);
    if (pos != std::string::npos) {
        const long t = std::strtol(lista.c_str() + pos + std::string("203.0.113.77 timeout ").size(), nullptr, 10);
        std::cout << "timeout restante de 203.0.113.77 = " << t << " s" << std::endl;
        CHECK(t >= 1 && t <= 30);
    }

    limpiar();
    CHECK(!tiene(sh("iptables -t filter -S INPUT"), CH));
    std::cout << "test_argus_cadena_root: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
