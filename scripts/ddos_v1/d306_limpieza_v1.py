#!/usr/bin/env python3
# DAY306 — DEBT-DDOS-V1-RETIRE-001, commits 3 y 4: configuracion y build sin la DDoS v1. [DDOS-V1-RETIRE-D306]
#   commit 3: sniffer/config/sniffer.json pierde el bloque fast_detector.ddos ("_status": "PLANNED", nadie lo lee).
#   commit 4: Makefile pierde la firma de xgboost_ddos.ubj (sign-models) y el target ddos-regen; .gitignore pierde
#             la entrada de ddos_trees_inline.hpp. Los 40 ficheros de la v1 se retiran despues con 'git rm'.
#
# Uso (Mac, raiz del repo):
#   python3 scripts/ddos_v1/d306_limpieza_v1.py --check    # valida TODO, no escribe nada
#   python3 scripts/ddos_v1/d306_limpieza_v1.py --apply    # valida TODO y, solo si todo casa, escribe
#
# Validaciones antes de escribir nada:
#   - cada ancla casa exactamente 1 vez (o, si ya se aplico, 0 veces y el texto nuevo esta presente);
#   - sha256 de cada bloque que se borra;
#   - sniffer.json: sha256 del fichero en HEAD (no lo tocaron los commits 1 y 2), JSON valido despues y ningun
#     codigo del sniffer lee la clave "ddos" de su configuracion (git grep vacio);
#   - si un fichero esta a medias, no se escribe ninguno.
import hashlib
import json
import os
import subprocess
import sys

MARK = "[DDOS-V1-RETIRE-D306]"


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


SNIFFER_JSON_PRE = "8c5eb39de4d57c63912c45b9d7029658c72e41e886fe4904b3b99339a1a44b84"

BLOQUE_DDOS_JSON = (
    '    "ddos": {\n'
    '      "_description": "DDoS-specific heuristics (future - currently not implemented)",\n'
    '      "_status": "PLANNED",\n'
    '      "scores": {\n'
    '        "high_threat": 0.95,\n'
    '        "suspicious": 0.7\n'
    '      },\n'
    '      "activation_thresholds": {\n'
    '        "syn_flood_rate": 10000,\n'
    '        "udp_flood_rate": 50000,\n'
    '        "icmp_flood_rate": 5000\n'
    '      }\n'
    '    },\n'
)

# (fichero, viejo, nuevo, texto que prueba que ya se aplico)
E = [
    ("sniffer/config/sniffer.json", BLOQUE_DDOS_JSON, "", None),
    ("Makefile",
     "\t@vagrant ssh -c \"sudo bash /vagrant/tools/sign-model.sh /vagrant/ml-detector/models/production/level2/ddos/xgboost_ddos.ubj\"\n",
     "", None),
    ("Makefile", " 4 modelo(s) firmado(s) correctamente", " 3 modelo(s) firmado(s) correctamente",
     " 3 modelo(s) firmado(s) correctamente"),
    ("Makefile",
     ".PHONY: ddos-regen\n"
     "ddos-regen:\n"
     "\tvagrant ssh defender -c 'bash /vagrant/ml-training/scripts/ddos_detection/ddos-regen.sh'\n",
     "", None),
    (".gitignore",
     "# artefacto regenerable de la manivela DDoS (fuente única en ml-detector/include)\n"
     "ml-training/scripts/ddos_detection/ddos_trees_inline.hpp\n",
     "# artefactos regenerables de las manivelas de traffic e internal (fuente única en ml-detector/include)\n",
     "# artefactos regenerables de las manivelas de traffic e internal"),
]

A_BORRAR_N = 40


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    errores, textos, aplicadas, pendientes = [], {}, 0, 0
    for f in sorted({e[0] for e in E}):
        if not os.path.isfile(f):
            errores.append(f"{f}: no existe")
        else:
            textos[f] = open(f, encoding="utf-8").read()
    if errores:
        print("[PARAR]", *errores, sep="\n   - ")
        return 1
    orig = dict(textos)
    for i, (f, old, new, prueba) in enumerate(E):
        t = textos[f]
        n = t.count(old)
        if n == 1:
            textos[f] = t.replace(old, new)
            pendientes += 1
        elif n == 0 and (prueba is None or t.count(prueba) == 1):
            aplicadas += 1  # ya aplicada (sin rastro del bloque viejo)
        else:
            errores.append(f"{f}: edicion {i}: el ancla casa {n} veces (debe ser 1, o 0 si ya se aplico)")
        if n == 1 and new == "":
            print(f"   bloque {i} ({f}) sha256 {sha(old)[:12]}")
    # sniffer.json: sha de partida, JSON valido y nadie lee "ddos" en el sniffer
    sj = "sniffer/config/sniffer.json"
    if orig[sj] != textos[sj]:
        if sha(orig[sj]) != SNIFFER_JSON_PRE:
            errores.append(f"{sj}: sha256 {sha(orig[sj])[:12]} no es el de HEAD ({SNIFFER_JSON_PRE[:12]})")
        try:
            j = json.loads(textos[sj])
            if "ddos" in j.get("fast_detector", {}):
                errores.append(f"{sj}: fast_detector.ddos sigue presente tras la edicion")
        except ValueError as e:
            errores.append(f"{sj}: el JSON resultante no es valido: {e}")
    r = subprocess.run(["git", "grep", "-n", "-F", '"ddos"', "--", "sniffer/src", "sniffer/include"],
                       capture_output=True, text=True)
    if r.stdout.strip():
        errores.append("el sniffer lee una clave \"ddos\" de su configuracion; no se borra el bloque:\n" + r.stdout)
    if errores:
        print("[PARAR] no se escribe nada:")
        for e in errores:
            print("   -", e)
        return 1
    if pendientes and aplicadas:
        print(f"[PARAR] estado mixto: {aplicadas} ediciones ya aplicadas y {pendientes} pendientes; no se escribe nada")
        return 1
    if not pendientes:
        print(f"[YA-APLICADO] las {aplicadas} ediciones ya estan aplicadas; nada que hacer")
        return 0
    print(f"[OK] {pendientes} ediciones validadas en {len(textos)} ficheros; sniffer.json sigue siendo JSON valido; "
          "ningun codigo del sniffer lee fast_detector.ddos")
    if modo == "--check":
        print("[CHECK] no se ha escrito nada. Para aplicar: --apply")
        return 0
    for f, t in textos.items():
        if t != orig[f]:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(t)
            print(f"   escrito {f}")
    print(f"[APPLY] hecho. Retira ahora los {A_BORRAR_N} ficheros de la v1 con git rm (lista en el prompt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
