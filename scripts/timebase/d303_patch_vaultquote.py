#!/usr/bin/env python3
# DAY303 [ARGUS-VAULT-QUOTE-D303]: el Step 4 de test-e2e-vault (etcd-server con Vault en build-vault-$(PROFILE),
# escrito por [ARGUS-PROFILE-D303]) metia $(CMAKE_FLAGS) dentro de vagrant ssh -c "...". En production CMAKE_FLAGS
# lleva comillas DOBLES (-DCMAKE_CXX_FLAGS="-std=c++20 ... -flto ..."): cierran el -c y vagrant recibe -Wall,
# -flto... como opciones -> "An invalid option was specified" (EMECAS 15:54, acto I).
# La comprobacion de [ARGUS-PROFILE-D303] miraba la linea CMAKE_FLAGS := $(CMAKE_FLAGS_$(shell...)), sin comillas;
# las comillas estan en CMAKE_FLAGS_PRODUCTION (lineas de continuacion). Error de diseno de la comprobacion.
# Arreglo: comillas simples por fuera (como rag-build). Verificacion como la haria el shell: se expande la linea con
# los CMAKE_FLAGS_<PERFIL> reales del Makefile y shlex debe dar exactamente [vagrant, ssh, -c, <comando>].
# Se revisan ademas TODAS las lineas con vagrant ssh y $(CMAKE_FLAGS); si otra falla, se informa y no se toca nada.
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_vaultquote.py --check | --apply
import difflib
import re
import shlex
import sys
from pathlib import Path

MARCA = "[ARGUS-VAULT-QUOTE-D303]"
MK = Path("Makefile")
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_vaultquote.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []


def flags(perfil):
    m = re.search(r"^CMAKE_FLAGS_" + perfil + r"[ \t]*:=[ \t]*((?:.*\\\n)*.*)$", mk, flags=re.M)
    if not m:
        return None
    return " ".join(p.strip().rstrip("\\").strip() for p in m.group(1).split("\n")).strip()


FL = {p: flags(p) for p in ("PRODUCTION", "DEBUG", "TSAN", "ASAN")}
for p, v in FL.items():
    if v is None:
        errores.append("no encuentro CMAKE_FLAGS_" + p)


def argv(linea, perfil):
    s = linea.strip()
    if s.startswith("@"):
        s = s[1:]
    s = s.replace("$(PROFILE)", perfil.lower()).replace("$(CMAKE_FLAGS)", FL[perfil] or "").replace("$$", "$")
    try:
        return shlex.split(s)
    except ValueError as e:
        return ["<shlex: " + str(e) + ">"]


def sana(linea):
    malos = []
    for p in FL:
        a = argv(linea, p)
        if len(a) != 4 or a[:3] != ["vagrant", "ssh", "-c"]:
            malos.append(p.lower() + " -> " + str(len(a)) + " argumentos")
    return malos


lineas = mk.split("\n")
cand = [i for i, l in enumerate(lineas) if "vagrant ssh -c" in l and "$(CMAKE_FLAGS)" in l]
paso4 = [i for i in cand if "build-vault-$(PROFILE) && cd /vagrant/etcd-server/build-vault-$(PROFILE)" in lineas[i]]
if len(paso4) != 1:
    errores.append("se esperaba 1 linea del Step 4 (build-vault-$(PROFILE)), hay " + str(len(paso4)))
else:
    i = paso4[0]
    vieja = lineas[i]
    print("Step 4 ANTES (linea " + str(i + 1) + "):", "; ".join(sana(vieja)) or "sana")
    m = re.match(r'^(\t@?vagrant ssh -c )"(.*)"(\s*)$', vieja)
    if not m:
        errores.append("el Step 4 no tiene la forma vagrant ssh -c \"...\" en una sola linea")
    elif "'" in m.group(2):
        errores.append("el comando del Step 4 contiene comillas simples: no se puede envolver en simples sin mas")
    else:
        nueva = m.group(1) + "'" + m.group(2) + "'" + m.group(3)
        mal = sana(nueva)
        if mal:
            errores.append("el Step 4 corregido sigue mal: " + "; ".join(mal))
        else:
            print("Step 4 DESPUES: sana en production, debug, tsan y asan (4 argumentos: vagrant ssh -c <comando>)")
            lineas[i] = nueva
            lineas.insert(i, "\t@# " + MARCA + " comillas simples: CMAKE_FLAGS lleva comillas dobles (medido DAY303)")
otras = [(i + 1, sana(lineas[i])) for i, l in enumerate(lineas) if "vagrant ssh -c" in l and "$(CMAKE_FLAGS)" in l]
for n, mal in otras:
    if mal:
        errores.append("linea " + str(n) + " con vagrant ssh y $(CMAKE_FLAGS) tambien se rompe: " + "; ".join(mal))
print("lineas con vagrant ssh -c y $(CMAKE_FLAGS) revisadas:", len(otras))

if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
mk2 = "\n".join(lineas)
print("=== " + sys.argv[1] + ": 0 errores ===")
print("".join(difflib.unified_diff(mk.splitlines(True), mk2.splitlines(True),
                                   fromfile="a/Makefile", tofile="b/Makefile", n=1)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    print("APLICADO", MARCA)
