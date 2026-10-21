#!/usr/bin/env python3
"""DAY300 [PROTEGIDOS-D300] tanda 2a: registra test_ddos_protegidos en el CMakeLists del firewall
(mismo patron que test_ip_cidr_validator). --check | --apply desde la raiz del repo. Atomico."""
import os
import sys

M = "[PROTEGIDOS-D300]"
CM = "firewall-acl-agent/CMakeLists.txt"
ANCLA = "    add_test(NAME test_ip_cidr_validator COMMAND test_ip_cidr_validator)\n"
NUEVO = (ANCLA + "\n"
         "    # test_ddos_protegidos — DAY300, rangos protegidos de la cabeza DDoS (header-only, CHECK propio) " + M + "\n"
         "    add_executable(test_ddos_protegidos\n"
         "            tests/unit/test_ddos_protegidos.cpp\n"
         "    )\n"
         "    target_include_directories(test_ddos_protegidos\n"
         "            PRIVATE\n"
         "            ${CMAKE_CURRENT_SOURCE_DIR}/include\n"
         "    )\n"
         "    add_test(NAME test_ddos_protegidos COMMAND test_ddos_protegidos)\n")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_patch_protegidos_a.py --check | --apply")
        return 2
    for f in ("firewall-acl-agent/include/firewall/ddos_protegidos.hpp",
              "firewall-acl-agent/tests/unit/test_ddos_protegidos.cpp"):
        if not os.path.isfile(f):
            print("falta " + f + " (crearlo antes con su bloque cat)")
            return 1
    with open(CM, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print(CM + ": ya contiene " + M)
        return 1
    n = t.count(ANCLA)
    if n != 1:
        print("el ancla aparece %d veces (se esperaba 1); NADA aplicado" % n)
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: 1 edicion en " + CM)
        return 0
    tmp = CM + ".tmp_d300"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t.replace(ANCLA, NUEVO, 1))
    os.chmod(tmp, os.stat(CM).st_mode)
    os.replace(tmp, CM)
    print("OK --apply: test_ddos_protegidos registrado en " + CM + " con marca " + M)
    return 0


if __name__ == "__main__":
    sys.exit(main())
