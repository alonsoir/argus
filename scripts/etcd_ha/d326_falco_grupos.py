#!/usr/bin/env python3
"""DAY326 — agrupa los eventos de un eventos.json de Falco, en una pasada (lineal).

Uso:
  d326_falco_grupos.py FICHERO

Clave de grupo: (prioridad, regla, proc.exepath, proc.pexepath, fd.name,
primera palabra de proc.cmdline). De cada grupo: cuántos, primera y última
hora (UTC, como la escribe Falco). Sirve para saber qué E2E o qué proceso
produjo cada CRITICAL sin leer las líneas una a una.
Las líneas que no son JSON (p. ej. el aviso de port-check de vagrant) se
cuentan y se saltan.
"""
import json
import sys


def campo(ev, nombre):
    v = ev.get("output_fields", {}).get(nombre)
    return "-" if v is None else str(v)


def main():
    if len(sys.argv) != 2:
        print("uso: d326_falco_grupos.py FICHERO", file=sys.stderr)
        return 2
    grupos = {}
    no_json = 0
    total = 0
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                ev = json.loads(linea)
            except json.JSONDecodeError:
                no_json += 1
                continue
            if not isinstance(ev, dict):
                no_json += 1
                continue
            total += 1
            cmd = campo(ev, "proc.cmdline").split(" ", 1)[0]
            clave = (str(ev.get("priority", "?")), str(ev.get("rule", "?")),
                     campo(ev, "proc.exepath"), campo(ev, "proc.pexepath"),
                     campo(ev, "fd.name"), cmd)
            hora = str(ev.get("time", "?"))
            g = grupos.get(clave)
            if g is None:
                grupos[clave] = [1, hora, hora]
            else:
                g[0] += 1
                g[2] = hora
    print(f"[FALCO-GRUPOS] {sys.argv[1]}: eventos={total} lineas_no_json={no_json} "
          f"grupos={len(grupos)}")
    orden = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "NOTICE": 3}
    for clave, (n, ini, fin) in sorted(
            grupos.items(), key=lambda x: (orden.get(x[0][0].upper(), 9), -x[1][0])):
        prio, regla, exe, pexe, fd, cmd = clave
        print(f"  {n:5d} {prio:<9} {regla}")
        print(f"        exe={exe} padre={pexe} cmd0={cmd}")
        print(f"        fichero={fd}")
        print(f"        primera={ini[:19]}Z ultima={fin[:19]}Z")
    return 0


if __name__ == "__main__":
    sys.exit(main())
