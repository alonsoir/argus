#!/usr/bin/env python3
"""d331_docs.py — [DOCS-D331] parcheador de documentación DAY331 (se ejecuta desde /tmp):
  docs/BACKLOG.md                            añade al final la sección DAY331 (texto en /tmp/d331_backlog.md)
  docs/continuity/PROMPT_CONTINUE_CLAUDE.md  pasa del prompt DAY331 al DAY332 (texto en /tmp/d332_prompt.md)
Uso: python3 /tmp/d331_docs.py --check <raíz> | --apply <raíz>. Todo o nada: sha256 de los dos textos nuevos; el
BACKLOG no debe tener ya [DOCS-D331]; el prompt tiene que empezar por la cabecera DAY331. Imprime el sha256 final.
Idempotente: con la sección ya puesta y el prompt ya en DAY332, no hace nada."""
import hashlib, os, sys
TEXTOS = {"/tmp/d331_backlog.md": "133d3b99eb6fb70b5a86a68f87277048bda77a83e33bdf07489048c0cb227052", "/tmp/d332_prompt.md": "e1881537cf498b7ac1a59a19bee490b89e52e14e8ff5e5c57a39779f1aa0987a"}
CAB_ANTES = "# aRGus NDR — prompt de continuidad DAY331 (sigue de DAY330)"
CAB_DESPUES = "# aRGus NDR — prompt de continuidad DAY332 (sigue de DAY331)"
MARCA = "[DOCS-D331]"
def h(b): return hashlib.sha256(b).hexdigest()
def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__); return 2
    raiz = sys.argv[2]; t = {}
    for p, sha in TEXTOS.items():
        try: b = open(p, "rb").read()
        except OSError as e: print("FALLA: %s: %s" % (p, e)); return 1
        if h(b) != sha: print("FALLA: %s tiene sha256 %s; se espera %s" % (p, h(b), sha)); return 1
        t[p] = b
    pb = os.path.join(raiz, "docs/BACKLOG.md"); pp = os.path.join(raiz, "docs/continuity/PROMPT_CONTINUE_CLAUDE.md")
    try: bl = open(pb, "rb").read(); pr = open(pp, "rb").read()
    except OSError as e: print("FALLA: %s" % e); return 1
    nuevos = {}
    if MARCA.encode() in bl: print("ya aplicado: docs/BACKLOG.md")
    else: nuevos[pb] = (bl if bl.endswith(b"\n") else bl + b"\n") + t["/tmp/d331_backlog.md"]
    primera = pr.decode("utf-8").split("\n", 1)[0]
    if pr == t["/tmp/d332_prompt.md"]: print("ya aplicado: PROMPT_CONTINUE_CLAUDE.md")
    elif primera != CAB_ANTES: print("FALLA: el prompt empieza por %r; se espera %r" % (primera, CAB_ANTES)); return 1
    else: nuevos[pp] = t["/tmp/d332_prompt.md"]
    if not nuevos: print("OK: nada que hacer"); return 0
    for p, nb in nuevos.items():
        print("%s: %s -> sha256 %s" % ("se puede aplicar" if sys.argv[1] == "--check" else "aplicado", p, h(nb)))
        if sys.argv[1] == "--apply": open(p, "wb").write(nb)
    return 0
sys.exit(main())
