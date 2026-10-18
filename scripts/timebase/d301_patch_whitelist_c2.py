#!/usr/bin/env python3
"""DAY301 -- patcher atomico [ARGUS-WHITELIST-D301] tanda c2: whitelist = rangos protegidos + test con root.
 src/main.cpp     antes de las reglas de iptables: vacia la whitelist y la carga con los rangos protegidos IPv4
                  (IPv6 -> [CONFIG-AVISO], DEBT-FW-IPV6-SETS-001); en dry_run imprime las ordenes; si falla arranca
                  igual con ERROR visible (la barrera del suscriptor sigue protegiendo).
 CMakeLists.txt   test_argus_cadena_root (firewall_core, LABELS e2e;root, SKIP_RETURN_CODE 77).
Requiere tests/unit/test_argus_cadena_root.cpp. Uso: --check | --apply. Idempotente por la marca. Se ejecuta en el DEFENDER."""
import sys
from pathlib import Path

MARK = "[ARGUS-WHITELIST-D301]"
FW = Path("/vagrant/firewall-acl-agent")
F = {"main": FW / "src/main.cpp", "cmake": FW / "CMakeLists.txt"}
NUEVOS = [FW / "tests/unit/test_argus_cadena_root.cpp"]


def fail(m):
    print("ABORTA:", m)
    sys.exit(1)


def once(t, a, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))


MAIN_A = '        const auto& blacklist_ipset = config.ipsets.at("blacklist");\n'
MAIN_N = r"""        {   // __MARK__ la whitelist refleja EXACTAMENTE los rangos protegidos (decision de Alonso DAY300)
            if (config.ipsets.count("whitelist") > 0) {
                const std::string wl = config.ipsets.at("whitelist").set_name;
                std::vector<IPSetEntry> entradas;
                size_t v6 = 0;
                for (const auto& r : config.ddos_protegidos.rangos) {
                    if (r.texto.find(':') != std::string::npos) {
                        ++v6;
                        std::cerr << "[CONFIG-AVISO] ddos_protegidos " << r.texto << ": IPv6 no cabe en la whitelist (family "
                                     "inet; DEBT-FW-IPV6-SETS-001); la barrera del suscriptor si lo protege" << std::endl;
                        continue;
                    }
                    entradas.push_back(IPSetEntry{r.texto});
                }
                if (config.operation.dry_run) {
                    std::cout << "[DRY-RUN] ipset flush " << wl << std::endl;
                    for (const auto& en : entradas) {
                        std::cout << "[DRY-RUN] ipset add " << wl << " " << en.ip << std::endl;
                    }
                    std::cout << "[ARGUS-WHITELIST] " << wl << ": se vaciaria y cargaria con " << entradas.size()
                              << " rangos protegidos IPv4 (IPv6 omitidos=" << v6 << ") (DRY-RUN: nada aplicado)" << std::endl;
                } else {
                    const bool vaciada = static_cast<bool>(ipset.flush_set(wl));
                    const bool cargada = entradas.empty() || static_cast<bool>(ipset.add_batch(wl, entradas));
                    if (vaciada && cargada) {
                        std::cout << "[ARGUS-WHITELIST] " << wl << ": vaciada y cargada con " << entradas.size()
                                  << " rangos protegidos IPv4 (IPv6 omitidos=" << v6 << ")" << std::endl;
                    } else {
                        std::cerr << "[ARGUS-WHITELIST] ERROR " << wl << ": flush=" << (vaciada ? "ok" : "FALLO")
                                  << " carga=" << (cargada ? "ok" : "FALLO") << "; el agente sigue (la barrera del "
                                     "suscriptor protege los rangos); revise el set con: sudo ipset list " << wl << std::endl;
                    }
                }
            } else {
                std::cerr << "[CONFIG-AVISO] ipsets.whitelist ausente: los rangos protegidos no se reflejan en el kernel; "
                             "solo los protege la barrera del suscriptor" << std::endl;
            }
        }
""".replace("__MARK__", MARK)

CMAKE_A = '    set_tests_properties(test_ipset_injection_integration PROPERTIES LABELS "e2e;root")\n'
CMAKE_N = """
    # __MARK__ [ARGUS-CADENA-D301] reglas base de aRGus contra el kernel (requiere root; sin root sale 77 = Skipped)
    add_executable(test_argus_cadena_root
        tests/unit/test_argus_cadena_root.cpp
    )
    target_include_directories(test_argus_cadena_root PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/src/core
    )
    target_link_libraries(test_argus_cadena_root PRIVATE
        firewall_core
    )
    add_test(NAME test_argus_cadena_root COMMAND test_argus_cadena_root)
    set_tests_properties(test_argus_cadena_root PROPERTIES LABELS "e2e;root" SKIP_RETURN_CODE 77)
""".replace("__MARK__", MARK)


def p_main(t):
    once(t, MAIN_A, "main blacklist_ipset")
    return t.replace(MAIN_A, MAIN_N + MAIN_A)


def p_cmake(t):
    once(t, CMAKE_A, "cmake injection")
    return t.replace(CMAKE_A, CMAKE_A + CMAKE_N)


PATCH = {"main": p_main, "cmake": p_cmake}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    for n in NUEVOS:
        if not n.exists():
            fail("falta el fichero nuevo %s" % n)
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
