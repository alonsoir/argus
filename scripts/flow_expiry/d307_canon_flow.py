#!/usr/bin/env python3
# DAY307 opcion A — ShardedFlowManager: solo codigo de produccion.
#  1. sharded_flow_manager.cpp incluye la cabecera canonica (flow/sharded_flow_manager.hpp) en vez de _fix3.hpp.
#  2. Borra los 9 residuos de la clase (no los compila nadie; inventario DAY307).
# Valida TODO antes de escribir NADA: sha256 de cada fichero, ancla unica, cabecera _fix3 identica a la canonica.
# Estado "ya aplicado" reconocido (no hace nada y lo dice).
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d307_canon_flow.py --check | --apply
import hashlib, os, sys

CPP = "sniffer/src/flow/sharded_flow_manager.cpp"
CANON = "sniffer/include/flow/sharded_flow_manager.hpp"
CPP_ANTES = "1436a75d2e57128046b1008ade61b89417c9019c4cccf13d0abe1d64686d4360"
CPP_DESPUES = "6259cf99ca06c225d41eb2094fb0e31c2e6fc9ab8b1d4378d6beace69084e6fb"
CANON_SHA = "11763d01e9540cd65331e6f34f71fdb3fd8dcb21ee9de8888a481d7fd156f9e7"
VIEJA = '#include "flow/sharded_flow_manager_fix3.hpp"\n'
NUEVA = '#include "flow/sharded_flow_manager.hpp"\n'
RESIDUOS = {
    "sniffer/include/flow/sharded_flow_manager_fix3.hpp": CANON_SHA,
    "sniffer/include/flow/sharded_flow_manager_fix1.hpp": "b4de2c5f15e5dccf5a6a0ebcdfcf8e94e2075d38f2188cced690dbc3e7cd250b",
    "sniffer/include/flow/sharded_flow_manager_fix2.hpp": "c632c46811d16c13e3297b40b1586d2411248827824fdaf718e7b6d3c8839f3c",
    "sniffer/include/flow/sharded_flow_manager.hpp.original": "035c3cc715bb0556938af3d53d1c304cf88aa3a331f5730ab6a18da20b8135bd",
    "sniffer/src/flow/sharded_flow_manager_fix1.cpp": "cf7a7f0578facc7117400016187131e5daf15bb8c61ed273d935b882c4f1a05a",
    "sniffer/src/flow/sharded_flow_manager_fix2.cpp": "0f644be73eaaf0b99627c27dcdaecbdc504b487a67535fb2b463abd441126f0f",
    "sniffer/src/flow/sharded_flow_manager_fix3.cpp": "507a8a100277193aee1e49f0eae7bcf88e1a75e309db4a886d260ca4551404f7",
    "sniffer/src/flow/sharded_flow_manager_original.cpp": "9517d8232016020e1fe3752499adbae255d55b66fbd0a073a4a1534c4f7b89b3",
    "sniffer/src/flow/sharded_flow_manager.cpp.original": "9517d8232016020e1fe3752499adbae255d55b66fbd0a073a4a1534c4f7b89b3",
}

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
APPLY = sys.argv[1] == "--apply"
if not (os.path.isfile("Makefile") and os.path.isdir("sniffer/src/flow")):
    die("no estoy en la raiz del repo")

# cabecera canonica intacta (es la que queda)
if sha(CANON) != CANON_SHA:
    die(f"{CANON} no es la esperada: {sha(CANON)}")

# estado del .cpp
s = sha(CPP)
presentes = [p for p in RESIDUOS if os.path.exists(p)]
if s == CPP_DESPUES and not presentes:
    print("[YA APLICADO] include canonico y los 9 residuos borrados. Nada que hacer.")
    sys.exit(0)
if s != CPP_ANTES:
    die(f"{CPP} sha256 {s} no es el de partida ni el de llegada")
t = open(CPP, encoding="utf-8").read()
if t.count(VIEJA) != 1:
    die(f"ancla del include _fix3 aparece {t.count(VIEJA)} veces (esperado 1)")
if t.count(NUEVA) != 0:
    die("el .cpp ya incluye la cabecera canonica (estado mixto)")
nuevo = t.replace(VIEJA, NUEVA)
if hashlib.sha256(nuevo.encode("utf-8")).hexdigest() != CPP_DESPUES:
    die("el resultado no tendria el sha256 esperado")

# residuos: todos presentes y exactos
if len(presentes) != len(RESIDUOS):
    die(f"faltan residuos (estado mixto): {sorted(set(RESIDUOS) - set(presentes))}")
for p, h in RESIDUOS.items():
    if sha(p) != h:
        die(f"{p} sha256 {sha(p)} no es el esperado")

print(f"[OK] {CPP}: include _fix3 -> canonico (1 linea)")
for p in sorted(RESIDUOS):
    print(f"[OK] borrar {p}")
if not APPLY:
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)

tmp = CPP + ".d307tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(nuevo)
os.replace(tmp, CPP)
for p in RESIDUOS:
    os.remove(p)
if sha(CPP) != CPP_DESPUES or any(os.path.exists(p) for p in RESIDUOS):
    die("verificacion posterior fallida")
print("[APLICADO] include canonico; 9 residuos borrados del disco (falta git rm al commitear).")
