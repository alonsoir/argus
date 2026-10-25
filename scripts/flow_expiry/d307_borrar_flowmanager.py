#!/usr/bin/env python3
# DAY307 — borrar la clase FlowManager del sniffer (codigo muerto: no la instancia ni la llama nadie).
#  1. flow_manager.hpp: fuera el alias FlowExportCallback y la clase FlowManager (lineas 185-260, bloque con sha256
#     verificado). FlowStatistics se queda donde esta. Comentario de cabecera que dice que contiene el fichero.
#     Los #include no se tocan (otros ficheros pueden depender de ellos de forma transitiva).
#  2. sniffer/CMakeLists.txt: fuera las 5 lineas "src/userspace/flow_manager.cpp" (sniffer + 4 tests).
#  3. Borra sniffer/src/userspace/flow_manager.cpp (solo metodos de FlowManager).
#  4. Borra sniffer/scripts/verify_integration.sh (verificacion de Day 3 de la integracion de FlowManager; no lo
#     llama nadie). Si Alonso no lo quiere borrar: --sin-verify.
# Valida TODO antes de escribir NADA. Reconoce el estado "ya aplicado".
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d307_borrar_flowmanager.py --check|--apply [--sin-verify]
import hashlib, os, sys

HPP = "sniffer/include/flow_manager.hpp"
CMK = "sniffer/CMakeLists.txt"
CPP = "sniffer/src/userspace/flow_manager.cpp"
VER = "sniffer/scripts/verify_integration.sh"
HPP_ANTES = "8c8f0849a04d5d2de30099194c0f2592f6dc51a49191ec8fc536263d3e2c633d"
HPP_DESPUES = "eaa205cf2a371685afefbef4d481285ed1b066eabf2eb2457a0d2289cc9a5024"
BLOQUE_SHA = "fbdb850c120dedff5a9a6dee64161e32c6c3e0846fe717a5b54185eab1f41aea"
CMK_ANTES = "18acd0727e784ffda0bb98919007097290c87e9ae6be58aef61b403bc9a91b8c"
CMK_DESPUES = "8aa489c1d8101150e5007175fc063be0e91aed872dbf461d722b05b184144cca"
CPP_SHA = "a7bf2b5cee1d8d630e7bed03e170e8d1f7eee7440084b20bdeba30622b5483f9"
VER_SHA = "73901f7551580f91cd9d3eedb101fe2d215fd67e92f9549c75225fa0361c2289"
INI = "// Callback for when a flow expires and needs to be processed\n"
FIN = "    bool should_auto_export(const FlowStatistics& stats) const;\n};\n\n"
CAB_VIEJA = "// sniffer/include/flow_manager.hpp\n"
CAB_NUEVA = CAB_VIEJA + (
    "// Define FlowStatistics: lo que el sniffer acumula por flujo para extraer rasgos. La tabla que lo guarda\n"
    "// es flow/sharded_flow_manager.hpp; FlowKey esta en flow_tracker.hpp. [DAY307] la clase FlowManager que\n"
    "// vivia aqui no la usaba nadie y se borro (la historia de git la conserva).\n")
LINEA_CMK = "        src/userspace/flow_manager.cpp\n"

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha_b(b):
    return hashlib.sha256(b).hexdigest()

def sha(p):
    return sha_b(open(p, "rb").read())

args = sys.argv[1:]
if not args or args[0] not in ("--check", "--apply") or any(a not in ("--check", "--apply", "--sin-verify") for a in args):
    die("uso: --check|--apply [--sin-verify]")
APPLY = args[0] == "--apply"
CON_VER = "--sin-verify" not in args
if not (os.path.isfile("Makefile") and os.path.isdir("sniffer/src/userspace")):
    die("no estoy en la raiz del repo")

hs, cs = sha(HPP), sha(CMK)
hecho = (hs == HPP_DESPUES and cs == CMK_DESPUES and not os.path.exists(CPP)
         and (not CON_VER or not os.path.exists(VER)))
if hecho:
    print("[YA APLICADO] FlowManager borrada. Nada que hacer.")
    sys.exit(0)

# cabecera
if hs != HPP_ANTES:
    die(f"{HPP} sha256 {hs} no es el de partida ni el de llegada")
t = open(HPP, encoding="utf-8").read()
if t.count(INI) != 1 or t.count(FIN) != 1:
    die(f"anclas del bloque: inicio x{t.count(INI)}, fin x{t.count(FIN)} (esperado 1 y 1)")
i = t.index(INI)
j = t.index(FIN) + len(FIN)
if j <= i:
    die("el fin del bloque esta antes del inicio")
if sha_b(t[i:j].encode("utf-8")) != BLOQUE_SHA:
    die("el bloque a borrar no es el esperado")
if not t.startswith(CAB_VIEJA) or t.count(CAB_VIEJA) != 1:
    die("la primera linea de la cabecera no es la esperada")
nuevo_h = (t[:i] + t[j:]).replace(CAB_VIEJA, CAB_NUEVA, 1)
if sha_b(nuevo_h.encode("utf-8")) != HPP_DESPUES:
    die("la cabecera resultante no tendria el sha256 esperado")
if "FlowManager" in nuevo_h.replace("ShardedFlowManager", "").replace("la clase FlowManager que", ""):
    die("quedaria alguna mencion a FlowManager en la cabecera")

# CMakeLists
if cs != CMK_ANTES:
    die(f"{CMK} sha256 {cs} no es el de partida")
c = open(CMK, encoding="utf-8").read()
if c.count(LINEA_CMK) != 5:
    die(f"'{LINEA_CMK.strip()}' aparece {c.count(LINEA_CMK)} veces (esperado 5)")
nuevo_c = c.replace(LINEA_CMK, "")
if sha_b(nuevo_c.encode("utf-8")) != CMK_DESPUES:
    die("el CMakeLists resultante no tendria el sha256 esperado")

# ficheros a borrar
if not os.path.exists(CPP) or sha(CPP) != CPP_SHA:
    die(f"{CPP} falta o no es el esperado")
if CON_VER and (not os.path.exists(VER) or sha(VER) != VER_SHA):
    die(f"{VER} falta o no es el esperado")

print(f"[OK] {HPP}: fuera FlowExportCallback y la clase FlowManager ({t[i:j].count(chr(10))} lineas); comentario de cabecera")
print(f"[OK] {CMK}: fuera 5 lineas '{LINEA_CMK.strip()}'")
print(f"[OK] borrar {CPP}")
print(f"[OK] borrar {VER}" if CON_VER else f"[--] {VER} se queda (--sin-verify)")
if not APPLY:
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)

for p, contenido in ((HPP, nuevo_h), (CMK, nuevo_c)):
    tmp = p + ".d307tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(contenido)
    os.replace(tmp, p)
os.remove(CPP)
if CON_VER:
    os.remove(VER)
if sha(HPP) != HPP_DESPUES or sha(CMK) != CMK_DESPUES or os.path.exists(CPP):
    die("verificacion posterior fallida")
print("[APLICADO] FlowManager borrada (falta git rm de los ficheros borrados al commitear).")
