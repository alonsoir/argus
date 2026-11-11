// test_protegidos_antispoof.cpp -- [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, 8e.4b: la parte pura del antispoofing (sin
// kernel ni root): reparto en los sets con la comprobación de ruta (H-D), texto exacto de las reglas como lo imprime
// 'iptables -S' (medido DAY320: --limit-burst 5 se omite), texto de iptables-restore en los dos modos, comprobación de
// cadenas y sets, y el paso con wrappers falsos (solo cuenta como reconciliado lo que se vuelve a leer).
#include "firewall/protegidos_antispoof.hpp"

#include <algorithm>
#include <iostream>
#include <map>
#include <optional>
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

static bool tiene(const std::string& s, const std::string& x) { return s.find(x) != std::string::npos; }
static bool contiene(const std::vector<std::string>& v, const std::string& x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}

// Wrappers falsos: el "kernel" son mapas; restaurar_sin_vaciar deja las cadenas como se generan salvo si miente.
struct IpsFalso {
    std::map<std::string, std::string> tipo;
    std::map<std::string, std::vector<std::string>> cont;
    bool mentirosa = false;
    int reemplazos = 0;
    std::optional<std::string> set_type(const std::string& s) const {
        auto it = tipo.find(s);
        return it == tipo.end() ? std::nullopt : std::optional<std::string>(it->second);
    }
    bool create_set(const IPSetConfig& c) {
        static const char* t[] = {"hash:ip", "hash:net", "hash:ip,port", "hash:net,iface", "hash:ip,mac"};
        tipo[c.name] = t[static_cast<int>(c.type)];
        cont[c.name].clear();
        return true;
    }
    std::vector<std::string> list_entries_opciones(const std::string& s) const {
        auto it = cont.find(s);
        return it == cont.end() ? std::vector<std::string>{} : it->second;
    }
    IPSetResult<void> replace_set(const std::string& s, IPSetType, const std::vector<std::string>& e, uint32_t) {
        ++reemplazos;
        if (!mentirosa) cont[s] = e;
        return IPSetResult<void>();
    }
};
struct IptFalso {
    std::map<std::string, std::vector<std::string>> reglas;
    NombresAntispoof n;
    bool descarta_al_restaurar = false, mentirosa = false;
    int restauraciones = 0;
    std::vector<std::string> list_rules(const std::string& ch, IPTablesTable) const {
        auto it = reglas.find(ch);
        return it == reglas.end() ? std::vector<std::string>{} : it->second;
    }
    IPTablesResult<void> restaurar_sin_vaciar(const std::string& texto) {
        ++restauraciones;
        if (!mentirosa) {
            const bool d = tiene(texto, "argus-spoof-if -j DROP");
            reglas[n.cadena] = reglas_esperadas_principal(n);
            reglas[n.cadena + "_IF"] = reglas_esperadas_spoof(n, "_IF", "ARGUS-SPOOF-IF ", d);
            reglas[n.cadena + "_MAC"] = reglas_esperadas_spoof(n, "_MAC", "ARGUS-SPOOF-MAC ", d);
        }
        return IPTablesResult<void>();
    }
    IPTablesResult<void> salto_en_primera(IPTablesTable, const std::string& base, const std::string& destino) {
        if (!mentirosa) reglas[base] = {"-A " + base + " -j " + destino};
        return IPTablesResult<void>();
    }
};

int main() {
    // ── reparto (H-D) ──
    auto ruta_lab = [](const std::string& ip) { return ip.rfind("192.168.100.", 0) == 0 ? std::string("eth2") : std::string("eth0"); };
    {
        const std::vector<EntradaAntispoof> e{{"192.168.100.20/32", "eth2", "08:00:27:a2:00:20"},
                                              {"192.168.100.61/32", "eth2", ""},
                                              {"192.168.100.77/24", "eth2", "08:00:27:00:00:01"},  // MAC en una /24: no
                                              {"10.9.0.0/24", "eth2", ""}};                        // la ruta va por eth0
        const auto r = repartir_antispoof(e, ruta_lab);
        CHECK(r.redes.size() == 3 && contiene(r.redes, "192.168.100.20/32") && contiene(r.redes, "192.168.100.0/24"));
        CHECK(!contiene(r.redes, "10.9.0.0/24") && r.sin_ruta.size() == 1 && tiene(r.sin_ruta[0], "la ruta va por eth0"));
        CHECK(r.ips_mac.size() == 1 && r.ips_mac[0] == "192.168.100.20");
        CHECK(r.mac.size() == 1 && r.mac[0] == "192.168.100.20,08:00:27:a2:00:20");
    }
    {   // host con dos interfaces legítimas: con que una case con la ruta, la red entra y no hay alarma
        const std::vector<EntradaAntispoof> e{{"192.168.100.30/32", "eth2", ""}, {"192.168.100.30/32", "eth3", ""}};
        const auto r = repartir_antispoof(e, ruta_lab);
        CHECK(r.redes.size() == 1 && r.sin_ruta.empty());
    }
    {   // sin ruta conocida: fuera
        const auto r = repartir_antispoof(std::vector<EntradaAntispoof>{{"192.168.100.20/32", "eth2", ""}},
                                          [](const std::string&) { return std::string(); });
        CHECK(r.redes.empty() && r.sin_ruta.size() == 1);
    }
    CHECK(repartir_antispoof(std::vector<EntradaAntispoof>{}, ruta_lab).redes.empty());

    // ── texto de las reglas ──
    NombresAntispoof n{"ARGUS_ANTISPOOF", "ml_defender_prot_redes", "ml_defender_protegidos", "ml_defender_prot_ipmac",
                       "ml_defender_prot_mac", 5, 5, true};
    const auto p = reglas_esperadas_principal(n);
    CHECK(p.size() == 7 && p[0] == "-N ARGUS_ANTISPOOF" && p[1] == "-A ARGUS_ANTISPOOF -i lo -j RETURN");
    CHECK(p.size() == 7 && p[3] == "-A ARGUS_ANTISPOOF -m set ! --match-set ml_defender_protegidos src,src -g ARGUS_ANTISPOOF_IF");
    CHECK(p.size() == 7 && p[5] == "-A ARGUS_ANTISPOOF -m set ! --match-set ml_defender_prot_mac src,src -g ARGUS_ANTISPOOF_MAC");
    CHECK(p.size() == 7 && p[6] == "-A ARGUS_ANTISPOOF -j RETURN");
    const auto si = reglas_esperadas_spoof(n, "_IF", "ARGUS-SPOOF-IF ", false);
    CHECK(si[1] == "-A ARGUS_ANTISPOOF_IF -m limit --limit 5/min -j LOG --log-prefix \"ARGUS-SPOOF-IF \"");  // burst 5 omitido
    CHECK(si[2] == "-A ARGUS_ANTISPOOF_IF -m comment --comment argus-spoof-if");
    CHECK(reglas_esperadas_spoof(n, "_IF", "ARGUS-SPOOF-IF ", true)[2] ==
          "-A ARGUS_ANTISPOOF_IF -m comment --comment argus-spoof-if -j DROP");
    {
        NombresAntispoof n7 = n;
        n7.log_por_minuto = 7;
        n7.log_rafaga = 7;
        CHECK(tiene(reglas_esperadas_spoof(n7, "_MAC", "ARGUS-SPOOF-MAC ", false)[1], "--limit 7/min --limit-burst 7"));
        NombresAntispoof nm = n;
        nm.con_mac = false;
        CHECK(reglas_esperadas_principal(nm).size() == 5);
    }
    const std::string tc = texto_restore_antispoof(n, false), td = texto_restore_antispoof(n, true);
    CHECK(tiene(tc, "*raw\n:ARGUS_ANTISPOOF - [0:0]\n:ARGUS_ANTISPOOF_IF - [0:0]\n:ARGUS_ANTISPOOF_MAC - [0:0]\n"));
    CHECK(tiene(tc, "-g ARGUS_ANTISPOOF_IF") && tiene(tc, "-g ARGUS_ANTISPOOF_MAC") && tiene(tc, "-i lo -j RETURN"));
    CHECK(!tiene(tc, "-j DROP") && tiene(td, "argus-spoof-if -j DROP") && tiene(td, "argus-spoof-mac -j DROP"));
    CHECK(tiene(tc, "--limit-burst 5") && tc.size() > 10 && tc.substr(tc.size() - 7) == "COMMIT\n");

    // ── comprobación de las cadenas ──
    const std::vector<std::string> pre{"-A PREROUTING -j ARGUS_ANTISPOOF"};
    const auto si_c = reglas_esperadas_spoof(n, "_IF", "ARGUS-SPOOF-IF ", false);
    const auto sm_c = reglas_esperadas_spoof(n, "_MAC", "ARGUS-SPOOF-MAC ", false);
    CHECK(comprobar_reglas_antispoof(pre, p, si_c, sm_c, n, false).empty());
    CHECK(!comprobar_reglas_antispoof(pre, p, si_c, sm_c, n, true).empty());            // modo distinto
    CHECK(!comprobar_reglas_antispoof({}, p, si_c, sm_c, n, false).empty());            // sin salto
    CHECK(!comprobar_reglas_antispoof({"-A PREROUTING -j X", pre[0]}, p, si_c, sm_c, n, false).empty());  // pos 2
    {
        auto p2 = p;
        p2.erase(p2.begin() + 1);  // sin la regla de lo
        CHECK(!comprobar_reglas_antispoof(pre, p2, si_c, sm_c, n, false).empty());
        auto p3 = p;
        if (p3.size() < 4) p3.resize(4);
        p3[3] = "-A ARGUS_ANTISPOOF -m set ! --match-set ml_defender_protegidos src,src -j ARGUS_ANTISPOOF_IF";  // -j
        CHECK(!comprobar_reglas_antispoof(pre, p3, si_c, sm_c, n, false).empty());
    }

    // ── comprobación de sets ──
    CHECK(set_cuadra({"192.168.100.20", "192.168.100.0/24"}, {"192.168.100.20/32", "192.168.100.0/24"}, true));
    CHECK(!set_cuadra({"192.168.100.20", "10.6.6.6"}, {"192.168.100.20/32"}, true));
    CHECK(!set_cuadra({"192.168.100.20 nomatch"}, {"192.168.100.20/32"}, true));
    CHECK(set_cuadra({"192.168.100.20,08:00:27:A2:00:20"}, {"192.168.100.20,08:00:27:a2:00:20"}, false));  // mayúsculas
    CHECK(!set_cuadra({"192.168.100.20,08:00:27:A2:00:21"}, {"192.168.100.20,08:00:27:a2:00:20"}, false));
    CHECK(set_cuadra({}, {}, true));

    // ── el paso con wrappers falsos ──
    RepartoAntispoof rep;
    rep.redes = {"192.168.100.20/32"};
    rep.ips_mac = {"192.168.100.20"};
    rep.mac = {"192.168.100.20,08:00:27:a2:00:20"};
    {   // a) aplicar desde cero: crea los tres sets, carga cadenas y salto; reconciliado
        IpsFalso ips;
        IptFalso ipt;
        ipt.n = n;
        const auto r = antispoof_paso(ips, ipt, n, rep, false, 64, false);
        CHECK(r.reconciliado && r.error.empty() && ips.tipo["ml_defender_prot_mac"] == "hash:ip,mac" && ipt.restauraciones == 1);
        // b) vigía sin cambios: nada
        const auto r2 = antispoof_paso(ips, ipt, n, rep, false, 64, true);
        CHECK(!r2.divergente && r2.reconciliado && ipt.restauraciones == 1);
        // c) alguien borra una regla: divergencia y reconciliación
        ipt.reglas[n.cadena].erase(ipt.reglas[n.cadena].begin() + 1);
        const auto r3 = antispoof_paso(ips, ipt, n, rep, false, 64, true);
        CHECK(r3.divergente && r3.reconciliado && ipt.restauraciones == 2);
        // d) alguien mete una red en set_redes: divergencia y reconciliación
        ips.cont["ml_defender_prot_redes"].push_back("10.6.6.6");
        const auto r4 = antispoof_paso(ips, ipt, n, rep, false, 64, true);
        CHECK(r4.divergente && r4.reconciliado && ips.cont["ml_defender_prot_redes"].size() == 1);
        // e) cambio de modo (cuenta -> descarta) detectado por el vigía
        const auto r5 = antispoof_paso(ips, ipt, n, rep, true, 64, true);
        CHECK(r5.divergente && r5.reconciliado && tiene(ipt.reglas[n.cadena + "_IF"][2], "-j DROP"));
    }
    {   // f) iptables dice "hecho" y no hace nada: NO reconciliado
        IpsFalso ips;
        IptFalso ipt;
        ipt.n = n;
        ipt.mentirosa = true;
        const auto r = antispoof_paso(ips, ipt, n, rep, false, 64, false);
        CHECK(!r.reconciliado && !r.error.empty());
    }
    {   // g) ipset dice "hecho" y no hace nada: NO reconciliado
        IpsFalso ips;
        ips.mentirosa = true;
        IptFalso ipt;
        ipt.n = n;
        const auto r = antispoof_paso(ips, ipt, n, rep, false, 64, false);
        CHECK(!r.reconciliado && !r.error.empty());
    }
    {   // h) set ajeno: no se destruye ni se instala la cadena que lo usaría
        IpsFalso ips;
        ips.tipo["ml_defender_prot_redes"] = "hash:ip";
        IptFalso ipt;
        ipt.n = n;
        const auto r = antispoof_paso(ips, ipt, n, rep, false, 64, true);
        CHECK(r.divergente && !r.reconciliado && ips.tipo["ml_defender_prot_redes"] == "hash:ip" && ipt.restauraciones == 0);
    }
    {   // i) sin hash:ip,mac: no se toca set_mac ni set_ips_mac
        NombresAntispoof nm = n;
        nm.con_mac = false;
        IpsFalso ips;
        IptFalso ipt;
        ipt.n = nm;
        const auto r = antispoof_paso(ips, ipt, nm, rep, false, 64, false);
        CHECK(r.reconciliado && ips.tipo.count("ml_defender_prot_mac") == 0 && ips.tipo.count("ml_defender_prot_ipmac") == 0);
    }

    std::cout << "test_protegidos_antispoof: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
