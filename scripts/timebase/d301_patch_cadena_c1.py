#!/usr/bin/env python3
"""DAY301 -- patcher atomico [ARGUS-CADENA-D301] tanda c1: reglas base en una cadena propia de aRGus.
 src/core/iptables_wrapper.cpp  setup_base_rules reescrita: INPUT -I 1 -j <cadena> (unico salto); dentro whitelist
                                -> RETURN y blacklist -> DROP; idempotente; sin rate limiting (solo aviso); aviso de
                                reglas heredadas en INPUT; en dry_run imprime TODAS las ordenes.
 src/core/ipset_wrapper.cpp     netmask solo para hash:ip y solo si < 32 (medido: ipset 7.17 rechaza netmask en hash:net).
Uso: --check | --apply. Idempotente por la marca. No commitea. Se ejecuta en el DEFENDER."""
import sys
from pathlib import Path

MARK = "[ARGUS-CADENA-D301]"
FW = Path("/vagrant/firewall-acl-agent")
F = {
    "ipt": FW / "src/core/iptables_wrapper.cpp",
    "ips": FW / "src/core/ipset_wrapper.cpp",
}


def fail(m):
    print("ABORTA:", m)
    sys.exit(1)


def once(t, a, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))


def first_include(t, ins, n):
    L = t.splitlines(keepends=True)
    i = next((k for k, l in enumerate(L) if l.startswith("#include")), None)
    if i is None:
        fail("%s: sin #include" % n)
    return "".join(L[:i]) + ins + "".join(L[i:])


NUEVA = r"""// __MARK__ Reglas base: UNA cadena propia de aRGus con un unico salto desde INPUT (posicion 1).
//   INPUT -I 1 -j <cadena>                                  (unico salto; los anteriores se retiran)
//   <cadena> -m set --match-set <whitelist> src -j RETURN   ("protegido" = aRGus nunca lo bloquea: vuelve a INPUT y
//                                                            siguen las reglas del admin; NUNCA ACCEPT)
//   <cadena> -m set --match-set <blacklist> src -j DROP
// La cadena es config.blacklist_chain (iptables.chain_name del JSON). Idempotente: crea o vacia la cadena y deja un
// solo salto. Rate limiting: NO se crea (la version anterior aceptaba toda conexion TCP nueva y se creaba aunque
// enable_rate_limiting fuera false); con enable_rate_limiting=true solo se avisa (DEBT-FW-RATELIMIT-ACCEPT-ALL-001).
// Reglas heredadas en INPUT que usen los sets de aRGus: no se borran a ciegas; se avisa con la orden para retirarlas.
// En dry_run se imprimen TODAS las ordenes (antes salia en la primera cadena).
IPTablesResult<void> IPTablesWrapper::setup_base_rules(const FirewallConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);
    const std::string& ch = config.blacklist_chain;
    if (ch.empty() || !validate_chain_name(ch)) {
        return IPTablesResult<void>(IPTablesError{
            IPTablesErrorCode::INVALID_RULE, "Invalid aRGus chain name: '" + ch + "'"});
    }
    const std::string ipt = "/usr/sbin/iptables";
    auto orden = [&ipt](const std::vector<std::string>& a) {
        std::vector<std::string> v{ipt};
        v.insert(v.end(), a.begin(), a.end());
        return v;
    };
    auto texto = [&ipt](const std::vector<std::string>& a) {
        std::string s = ipt;
        for (const auto& x : a) {
            s += " " + x;
        }
        return s;
    };
    auto run = [&](const std::vector<std::string>& a) -> bool {
        if (m_dry_run) {
            std::cout << "[DRY-RUN] " << texto(a) << std::endl;
            return true;
        }
        auto [ret, output] = safe_exec_with_output(orden(a));
        if (ret != 0) {
            std::cerr << "[ARGUS-CADENA] ERROR rc=" << ret << " en: " << texto(a) << " :: " << output << std::endl;
            return false;
        }
        return true;
    };
    auto fallo = [&ch](const std::string& que) {
        return IPTablesResult<void>(IPTablesError{
            IPTablesErrorCode::KERNEL_ERROR, "aRGus chain " + ch + ": " + que});
    };

    // 1. cadena: crear o vaciar
    if (!m_dry_run && chain_exists_unlocked(ch, IPTablesTable::FILTER)) {
        if (!run({"-t", "filter", "-F", ch})) return fallo("flush");
    } else {
        if (!run({"-t", "filter", "-N", ch})) return fallo("create");
    }
    // 2. reglas dentro de la cadena: whitelist RETURN, blacklist DROP
    if (!config.whitelist_ipset.empty()) {
        if (!run({"-t", "filter", "-A", ch, "-m", "set", "--match-set", config.whitelist_ipset, "src",
                  "-m", "comment", "--comment", "argus-protegidos", "-j", "RETURN"})) return fallo("whitelist RETURN");
    }
    if (!config.blacklist_ipset.empty()) {
        if (!run({"-t", "filter", "-A", ch, "-m", "set", "--match-set", config.blacklist_ipset, "src",
                  "-m", "comment", "--comment", "argus-blacklist", "-j", "DROP"})) return fallo("blacklist DROP");
    }
    // 3. un unico salto desde INPUT
    int retirados = 0;
    if (m_dry_run) {
        std::cout << "[DRY-RUN] " << texto({"-t", "filter", "-D", "INPUT", "-j", ch})
                  << " (repetido hasta que no quede ninguno)" << std::endl;
    } else {
        for (int i = 0; i < 16; ++i) {
            auto [r, o] = safe_exec_with_output(orden({"-t", "filter", "-D", "INPUT", "-j", ch}));
            (void)o;
            if (r != 0) break;
            ++retirados;
        }
    }
    if (!run({"-t", "filter", "-I", "INPUT", "1", "-j", ch})) return fallo("jump from INPUT");
    // 4. reglas heredadas en INPUT que usen los sets de aRGus: aviso, no borrado a ciegas
    if (!m_dry_run) {
        auto [r, out] = safe_exec_with_output(orden({"-t", "filter", "-S", "INPUT"}));
        if (r == 0) {
            std::istringstream is(out);
            std::string l;
            while (std::getline(is, l)) {
                const bool wl = !config.whitelist_ipset.empty() &&
                                l.find("--match-set " + config.whitelist_ipset + " ") != std::string::npos;
                const bool bl = !config.blacklist_ipset.empty() &&
                                l.find("--match-set " + config.blacklist_ipset + " ") != std::string::npos;
                if (wl || bl) {
                    std::cerr << "[ARGUS-CADENA] AVISO: regla heredada en INPUT que usa un set de aRGus; retirela a mano "
                                 "(cambie -A por -D): iptables " << l << std::endl;
                }
            }
        }
    }
    // 5. rate limiting: no se crea
    if (config.enable_rate_limiting) {
        std::cerr << "[CONFIG-AVISO] iptables.enable_rate_limiting=true: NO se crea (la implementacion anterior aceptaba "
                     "toda conexion TCP nueva); DEBT-FW-RATELIMIT-ACCEPT-ALL-001" << std::endl;
    }
    std::cout << "[ARGUS-CADENA] INPUT -j " << ch << " en posicion 1 (saltos previos retirados=" << retirados
              << "); dentro: " << (config.whitelist_ipset.empty() ? "sin whitelist" : config.whitelist_ipset + " RETURN")
              << ", " << (config.blacklist_ipset.empty() ? "sin blacklist" : config.blacklist_ipset + " DROP")
              << (m_dry_run ? " (DRY-RUN: nada aplicado)" : "") << std::endl;
    return IPTablesResult<void>();
}
""".replace("__MARK__", MARK)


def p_ipt(t):
    a = "IPTablesResult<void> IPTablesWrapper::setup_base_rules(const FirewallConfig& config) {\n"
    b = "IPTablesResult<void> IPTablesWrapper::cleanup_rules(const FirewallConfig& config) {\n"
    once(t, a, "ipt inicio setup_base_rules")
    once(t, b, "ipt inicio cleanup_rules")
    i, j = t.index(a), t.index(b)
    if j < i:
        fail("ipt: cleanup_rules antes que setup_base_rules")
    region = t[i:j]
    k = region.rfind("\n}\n")
    if k < 0:
        fail("ipt: no encuentro el cierre de setup_base_rules")
    vieja, cola = region[:k + 3], region[k + 3:]
    if vieja.count("IPTablesWrapper::") != 1 or "Setup whitelist rule" not in vieja:
        fail("ipt: la region no es exactamente la setup_base_rules esperada")
    print("ipt: setup_base_rules vieja = %d lineas; cola conservada = %d lineas" % (vieja.count("\n"), cola.count("\n")))
    t = t[:i] + NUEVA + cola + t[j:]
    return first_include(t, "#include <sstream>  // " + MARK + "\n", "ipt include")


IPS_A = """    if (config.type == IPSetType::HASH_NET) {
        args.push_back("netmask");
        args.push_back(std::to_string(config.netmask));
    }
"""
IPS_N = """    // __MARK__ medido DAY301: ipset 7.17 rechaza 'netmask' en hash:net (rc 2). Solo hash:ip, y solo si < 32.
    if (config.type == IPSetType::HASH_IP && config.netmask < 32) {
        args.push_back("netmask");
        args.push_back(std::to_string(config.netmask));
    }
""".replace("__MARK__", MARK)


def p_ips(t):
    once(t, IPS_A, "ips netmask")
    return t.replace(IPS_A, IPS_N)


PATCH = {"ipt": p_ipt, "ips": p_ips}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    txt = {k: p.read_text(encoding="utf-8") for k, p in F.items()}
    hechos = [k for k, t in txt.items() if MARK in t]
    if len(hechos) == len(F):
        print("YA APLICADO (marca presente en todos)")
        return 0
    if hechos:
        fail("marca presente solo en %s: estado mixto" % hechos)
    nuevo = {k: PATCH[k](txt[k]) for k in F}
    if sys.argv[1] == "--check":
        print("CHECK OK: anclas unicas; nada escrito")
        return 0
    for k, p in F.items():
        p.write_text(nuevo[k], encoding="utf-8")
        print("escrito", p)
    print("APPLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
