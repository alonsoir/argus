#!/usr/bin/env python3
"""DAY301 -- patcher atomico (todo o nada) [DDOS-MITIGACION-D301] tanda 3b-a: funciones puras de la mitigacion ddos_v2.
 firewall-acl-agent/include/firewall/ddos_shadow_policy.hpp  en_episodio(dst, proto) const (solo lectura de State::blocked).
 firewall-acl-agent/CMakeLists.txt                           test_ddos_mitigacion (copia del bloque de test_ddos_protegidos).
Requiere los ficheros nuevos ddos_mitigacion.hpp y tests/unit/test_ddos_mitigacion.cpp.
Uso: --check | --apply. Idempotente por la marca. No commitea. Se ejecuta en el DEFENDER."""
import sys
from pathlib import Path

MARK = "[DDOS-MITIGACION-D301]"
FW = Path("/vagrant/firewall-acl-agent")
F = {
    "pol": FW / "include/firewall/ddos_shadow_policy.hpp",
    "cmake": FW / "CMakeLists.txt",
}
NUEVOS = [FW / "include/firewall/ddos_mitigacion.hpp", FW / "tests/unit/test_ddos_mitigacion.cpp"]


def fail(m):
    print("ABORTA:", m)
    sys.exit(1)


def after(t, a, i, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))
    return t.replace(a, a + i)


def p_pol(t):
    return after(t, "    std::size_t victims() const noexcept { return st_.size(); }\n",
                 "    // " + MARK + " solo lectura: la victima {dst, proto} esta en episodio (entre INICIO y FIN).\n"
                 "    bool en_episodio(const std::string& dst, uint32_t proto) const {\n"
                 "        const auto it = st_.find(dst + \"/\" + std::to_string(proto));\n"
                 "        return it != st_.end() && it->second.blocked;\n"
                 "    }\n", "pol en_episodio")


def bloque_protegidos(t):
    L = t.splitlines(keepends=True)
    idx = [i for i, l in enumerate(L) if "test_ddos_protegidos" in l]
    if not idx:
        fail("cmake: no aparece test_ddos_protegidos")
    a, b = idx[0], idx[-1]
    bloque = "".join(L[a:b + 1])
    if bloque.count("(") != bloque.count(")"):
        fail("cmake: bloque de test_ddos_protegidos con parentesis desbalanceados")
    if bloque.count("add_executable") != 1 or "add_executable(test_ddos_protegidos" not in bloque.replace("( ", "("):
        fail("cmake: el bloque no es un unico add_executable(test_ddos_protegidos ...)")
    return L, b, bloque


def p_cmake(t):
    L, b, bloque = bloque_protegidos(t)
    nuevo = "# " + MARK + " test de la mitigacion ddos_v2 (mismo patron que test_ddos_protegidos)\n" + \
        bloque.replace("test_ddos_protegidos", "test_ddos_mitigacion")
    return "".join(L[:b + 1]) + nuevo + "".join(L[b + 1:])


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
    nuevo = {"pol": p_pol(txt["pol"]), "cmake": p_cmake(txt["cmake"])}
    _, _, bloque = bloque_protegidos(txt["cmake"])
    print("--- bloque CMake de origen ---")
    print(bloque, end="")
    print("--- fin del bloque ---")
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
