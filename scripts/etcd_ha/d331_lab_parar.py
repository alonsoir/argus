#!/usr/bin/env python3
"""d331_lab_parar.py — [LAB-PARAR-D331] parcheador del Makefile: `halt` pasa a ser la parada ordenada del lab
(scripts/emecas/lab_parar.sh: pipeline, client, sensores, defender y, al final, el plano de control al revés de
CONTROL_NODOS) y se añade `test-lab-parar`.
Uso: python3 d331_lab_parar.py --check <raíz> | --apply <raíz>. Todo o nada: sha256 de partida; cada marcador (línea
comparada sin la sangría inicial) exactamente una vez; si algo falla no escribe nada. Imprime el sha256 final.
Idempotente: si ya está aplicado (marca LAB-PARAR-D331 presente), no hace nada."""
import hashlib, os, sys
MARCA = "[LAB-PARAR-D331]"
SHA = {"Makefile": "203246ff9f7830e307c83751c172db7116c639fd2cc4add0f46b0eb1dff56a70"}
CAMBIOS = [
 ("Makefile", "halt:", "@vagrant halt defender client suricata zeek wazuh $(CONTROL_NODOS)", [],
  ["# [LAB-PARAR-D331] parada ordenada para cerrar el día (decisión de Alonso DAY331): scripts/emecas/lab_parar.sh para",
   "# el pipeline si el defender está en marcha y apaga de una en una client, sensores, defender y, al final, el plano de",
   "# control (al revés de CONTROL_NODOS: etcd y Vault, los últimos); cada llamada con el límite",
   "# argus_lab_llamada_vm_limite_s de all.yml y --force de reserva; falla diciendo qué VM no quedó parada.",
   "CONTROL_NODOS_INVERSO = $(shell echo '$(CONTROL_NODOS)' | awk '{ for (i = NF; i > 0; i--) printf \"%s%s\", $$i, (i > 1 ? \" \" : \"\") }')",
   "",
   "halt:",
   "\t@bash scripts/emecas/lab_parar.sh client suricata zeek wazuh defender $(CONTROL_NODOS_INVERSO)",
   "",
   "test-lab-parar:  # [LAB-PARAR-D331] (anfitrión, sin tocar el lab) tests de scripts/emecas/lab_parar.sh",
   "\t@bash scripts/emecas/test_lab_parar.sh"]),
]

def h(b): return hashlib.sha256(b).hexdigest()
def unica(lineas, texto, f):
    idx = [i for i, l in enumerate(lineas) if l.rstrip("\n").strip() == texto]
    if len(idx) != 1: raise ValueError("%s: el marcador aparece %d veces (se espera 1): %r" % (f, len(idx), texto[:90]))
    return idx[0]

def aplicar(f, s):
    lineas = s.splitlines(True)
    for (ff, ini, fin, extra, nuevo) in CAMBIOS:
        if ff != f: continue
        i = unica(lineas, ini, f)
        j = i if fin is None else unica(lineas, fin, f)
        if j < i: raise ValueError("%s: el marcador final va antes que el inicial: %r" % (f, fin))
        for k, e in enumerate(extra):
            n = j + 1 + k
            if n >= len(lineas) or lineas[n].strip() != e:
                raise ValueError("%s: tras %r se esperaba %r" % (f, fin, e))
        j += len(extra)
        l0 = lineas[i]; sangria = l0[:len(l0) - len(l0.lstrip())]
        lineas[i:j + 1] = [(sangria + x if x else "") + "\n" for x in nuevo]
    return "".join(lineas)

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__); return 2
    raiz = sys.argv[2]; nuevos = {}
    for f, ini in SHA.items():
        p = os.path.join(raiz, f)
        try: b = open(p, "rb").read()
        except OSError as e: print("FALLA: %s: %s" % (f, e)); return 1
        s = b.decode("utf-8")
        if MARCA in s and h(b) != ini: print("ya aplicado: %s (sha256 %s)" % (f, h(b))); continue
        if h(b) != ini: print("FALLA: %s tiene sha256 %s; se espera %s" % (f, h(b), ini)); return 1
        try: ns = aplicar(f, s)
        except ValueError as e: print("FALLA: %s" % e); return 1
        nuevos[p] = (f, ns.encode("utf-8"))
    if not nuevos: print("OK: nada que hacer"); return 0
    for p, (f, nb) in nuevos.items():
        if sys.argv[1] == "--check": print("se puede aplicar: %s -> sha256 %s" % (f, h(nb)))
    if sys.argv[1] == "--check": return 0
    for p, (f, nb) in nuevos.items():
        modo = os.stat(p).st_mode
        open(p, "wb").write(nb); os.chmod(p, modo); print("aplicado: %s -> sha256 %s" % (f, h(nb)))
    return 0
sys.exit(main())
