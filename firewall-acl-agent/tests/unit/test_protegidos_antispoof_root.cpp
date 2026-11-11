// test_protegidos_antispoof_root.cpp -- [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, 8e.4b: el antispoofing contra el KERNEL
// real (la medida de DAY320, scripts/etcd_ha/d320_medir_antispoof.sh, hecha test con el código del agente). Requiere
// root (make test-firewall-e2e). Sin root sale con 77 = Skipped. Sin hash:ip,mac en el kernel también sale con 77 (el
// gate de test-firewall-e2e lo cuenta como fallo); ARGUS_TEST_SIN_IPMAC=1 lo corre sin la parte de MAC (solo banco).
// Red de prueba: netns argas320 con veth as0 (raíz, 10.251.0.1/30) <-> as1 (netns, 10.251.0.2/30) y rutas /32 por as0
// para .21 y .22. Entradas: .20 por la interfaz real de su ruta; .21 por as0 con una MAC que no es la de as1; .22 por
// as0 con la MAC de as1; .23 por as0 sin ruta por as0 (H-D: fuera). Sets y cadenas propios del test; se limpia todo.
//   A1 aplicar en modo cuenta y comprobar sin cambios      A6 .23 (sin ruta): no cuenta, y aparece en sin_ruta
//   A2 no protegido: 0 spoofing                             A7 origen protegido por lo: exento
//   A3 .20 por as0: SPOOF-IF +10                            A8 modo descarta: SPOOF-IF +10 y 0 llegan a mangle
//   A4 .21 MAC distinta: SPOOF-MAC +10                      A9 alguien borra la regla de lo: divergencia y reconciliación
//   A5 .22 interfaz y MAC buenas: 0                         A10 limpieza completa
#include "firewall/protegidos_antispoof.hpp"

#include <unistd.h>

#include <cstdio>
#include <cstdlib>
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

static const std::string NS = "argas320", VA = "as0", VB = "as1";
static const std::string CH = "TAS320";
static const std::string S_RED = "tas320_red", S_IF = "tas320_if", S_IPM = "tas320_ipm", S_MAC = "tas320_mac";
static const char* MAL_MAC = "02:00:00:00:d3:20";

static void limpiar() {
    sh("while iptables -w -t raw -D PREROUTING -j " + CH + " 2>/dev/null; do :; done");
    sh("iptables -w -t mangle -D PREROUTING -i " + VA + " -s 192.168.100.20 -m comment --comment tas320-llegan 2>/dev/null");
    for (const auto& c : {CH, CH + "_IF", CH + "_MAC"}) sh("iptables -w -t raw -F " + c + " 2>/dev/null");
    for (const auto& c : {CH, CH + "_IF", CH + "_MAC"}) sh("iptables -w -t raw -X " + c + " 2>/dev/null");
    for (const auto& s : {S_RED, S_IF, S_IPM, S_MAC}) sh("ipset destroy " + s + " 2>/dev/null; ipset destroy " + s + "_n 2>/dev/null");
    sh("ip netns del " + NS + " 2>/dev/null; ip link del " + VA + " 2>/dev/null");
    sh("ip route del 192.168.100.21/32 dev " + VA + " 2>/dev/null; ip route del 192.168.100.22/32 dev " + VA + " 2>/dev/null");
}

// 10 paquetes UDP con origen 'src' hacia 10.251.0.1 desde el netns (o, con en_raiz, hacia 127.0.0.1 por lo).
static void manda(const std::string& src, bool en_raiz = false) {
    const std::string py =
        "import socket,struct,sys\n"
        "s=socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_RAW)\n"
        "c=b'argus-d320-test'\n"
        "u=struct.pack('!HHHH',40320,40321,8+len(c),0)+c\n"
        "i=struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(u),0,0,64,17,0,socket.inet_aton(sys.argv[1]),socket.inet_aton(sys.argv[2]))\n"
        "[s.sendto(i+u,(sys.argv[2],0)) for _ in range(10)]\n";
    FILE* f = std::fopen("/tmp/tas320_manda.py", "w");
    if (f) {
        std::fputs(py.c_str(), f);
        std::fclose(f);
    }
    sh(std::string(en_raiz ? "" : "ip netns exec " + NS + " ") + "python3 -I /tmp/tas320_manda.py " + src + " " +
       (en_raiz ? "127.0.0.1" : "10.251.0.1"));
    ::usleep(300000);
}

int main() {
    if (::geteuid() != 0) {
        std::cout << "SALTADO: requiere root (make test-firewall-e2e PROFILE=...)" << std::endl;
        return 77;
    }
    limpiar();
    const bool sin_ipmac_permitido = std::getenv("ARGUS_TEST_SIN_IPMAC") != nullptr;
    const bool con_mac = sh("ipset create " + S_MAC + " hash:ip,mac counters && echo SI").find("SI") != std::string::npos;
    if (!con_mac && !sin_ipmac_permitido) {
        std::cout << "SALTADO: el kernel no admite hash:ip,mac (el gate de test-firewall-e2e lo cuenta como fallo)" << std::endl;
        limpiar();
        return 77;
    }
    if (!con_mac) std::cout << "AVISO: sin hash:ip,mac (ARGUS_TEST_SIN_IPMAC): no se prueba la MAC" << std::endl;

    // red de prueba
    sh("ip netns add " + NS + " && ip link add " + VA + " type veth peer name " + VB + " && ip link set " + VB + " netns " + NS +
       " && ip addr add 10.251.0.1/30 dev " + VA + " && ip link set " + VA + " up && ip -n " + NS + " addr add 10.251.0.2/30 dev " +
       VB + " && ip -n " + NS + " link set " + VB + " up && ip -n " + NS + " link set lo up");
    sh("ip route add 192.168.100.21/32 dev " + VA + "; ip route add 192.168.100.22/32 dev " + VA);
    std::string macb = sh("ip netns exec " + NS + " cat /sys/class/net/" + VB + "/address");
    while (!macb.empty() && (macb.back() == '\n' || macb.back() == '\r')) macb.pop_back();
    sh("ip netns exec " + NS + " ping -c1 -W1 10.251.0.1 >/dev/null 2>&1");
    const std::string ifl = IPTablesWrapper::interfaz_de_ruta("192.168.100.20");
    CHECK(!ifl.empty() && macb.size() == 17 && IPTablesWrapper::interfaz_de_ruta("192.168.100.21") == VA);

    IPSetWrapper ipset;
    IPTablesWrapper ipt;
    CHECK(ipset.create_set(config_set_protegidos(S_IF, 4096)));
    const std::vector<EntradaAntispoof> ent{{"192.168.100.20/32", ifl, ""},
                                            {"192.168.100.21/32", VA, MAL_MAC},
                                            {"192.168.100.22/32", VA, macb},
                                            {"192.168.100.23/32", VA, ""}};
    std::vector<std::pair<std::string, std::string>> esp_if;
    for (const auto& e : ent) esp_if.emplace_back(e.cidr, e.iface);
    CHECK(ipset.replace_net_iface(S_IF, esp_if, 4096));
    const auto rep = repartir_antispoof(ent, [](const std::string& ip) { return IPTablesWrapper::interfaz_de_ruta(ip); });
    NombresAntispoof n{CH, S_RED, S_IF, S_IPM, S_MAC, 5, 5, con_mac};
    auto spoof = [&](const std::string& suf) {
        const auto v = ipt.contadores(CH + suf, IPTablesTable::RAW);
        return v.size() >= 2 ? v[1] : static_cast<uint64_t>(-1);
    };

    // A1
    {
        const auto r = antispoof_paso(ipset, ipt, n, rep, false, 4096, false);
        CHECK(r.reconciliado && r.error.empty());
        const auto r2 = antispoof_paso(ipset, ipt, n, rep, false, 4096, true);
        CHECK(!r2.divergente && r2.reconciliado);
    }
    // A6 (el reparto): .23 fuera por la ruta
    CHECK(rep.sin_ruta.size() == 1 && rep.sin_ruta[0].find("192.168.100.23/32") == 0 && rep.redes.size() == 3);
    // A2..A6
    uint64_t i0 = spoof("_IF"), m0 = spoof("_MAC");
    manda("10.251.0.2");
    CHECK(spoof("_IF") == i0 && spoof("_MAC") == m0);
    manda("192.168.100.20");
    CHECK(spoof("_IF") == i0 + 10 && spoof("_MAC") == m0);
    if (con_mac) {
        manda("192.168.100.21");
        CHECK(spoof("_MAC") == m0 + 10 && spoof("_IF") == i0 + 10);
    }
    i0 = spoof("_IF");
    m0 = spoof("_MAC");
    manda("192.168.100.22");
    manda("192.168.100.23");
    CHECK(spoof("_IF") == i0 && spoof("_MAC") == m0);
    // A7 lo
    manda("192.168.100.20", true);
    CHECK(spoof("_IF") == i0);
    // A8 modo descarta
    {
        const auto r = antispoof_paso(ipset, ipt, n, rep, true, 4096, true);
        CHECK(r.divergente && r.reconciliado);
        sh("iptables -w -t mangle -I PREROUTING 1 -i " + VA + " -s 192.168.100.20 -m comment --comment tas320-llegan");
        const uint64_t d0 = spoof("_IF");
        manda("192.168.100.20");
        const std::string ll = sh("iptables -w -t mangle -L PREROUTING -v -x -n | awk '/tas320-llegan/ {print $1}'");
        CHECK(spoof("_IF") == d0 + 10 && std::strtoull(ll.c_str(), nullptr, 10) == 0);
    }
    // A9 alguien borra la regla de lo
    sh("iptables -w -t raw -D " + CH + " 1");
    {
        const auto r = antispoof_paso(ipset, ipt, n, rep, true, 4096, true);
        CHECK(r.divergente && r.reconciliado);
        CHECK(ipt.list_rules(CH, IPTablesTable::RAW) == reglas_esperadas_principal(n));
    }
    // A10
    limpiar();
    CHECK(sh("iptables -w -t raw -S").find(CH) == std::string::npos && !ipset.set_type(S_RED).has_value() &&
          sh("ip netns list").find(NS) == std::string::npos);
    std::cout << "test_protegidos_antispoof_root: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones"
              << (con_mac ? "" : " (sin MAC)") << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
