#!/usr/bin/env python3
"""DAY326 — resumen de un eventos.json de Falco, en una sola pasada (lineal).

Uso:
  d326_falco_resumen.py FICHERO [--contiene TEXTO] [--ejemplos N]

- Cuenta los eventos por (prioridad, regla).
- De cada regla CRITICAL cuyo nombre empiece por 'argus' (sin distinguir
  mayúsculas) muestra los N primeros ejemplos: hora y output_fields completos.
- Con --contiene, muestra además los N últimos eventos cuya línea contenga
  TEXTO (output_fields completos): es la medida de campos que pide F2.
- Las líneas que no son JSON (p. ej. el aviso de port-check de vagrant) se
  cuentan y se saltan.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict, deque

EJEMPLOS_MIN, EJEMPLOS_MAX = 1, 50


def mostrar(ev):
    print(f"    hora={ev.get('time', '?')}")
    print(f"    salida={ev.get('output', '')}")
    campos = ev.get("output_fields", {})
    print("    output_fields=" + json.dumps(campos, ensure_ascii=False, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fichero")
    p.add_argument("--contiene")
    p.add_argument("--ejemplos", type=int, default=3)
    a = p.parse_args()
    if not EJEMPLOS_MIN <= a.ejemplos <= EJEMPLOS_MAX:
        print(f"--ejemplos fuera de rango: {a.ejemplos} "
              f"(entero, mín {EJEMPLOS_MIN}, máx {EJEMPLOS_MAX})", file=sys.stderr)
        return 2

    cuenta = Counter()
    ejemplos = defaultdict(list)
    ultimas = deque(maxlen=a.ejemplos)
    no_json = 0
    total = 0
    with open(a.fichero, encoding="utf-8", errors="replace") as f:
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
            prio = str(ev.get("priority", "?"))
            regla = str(ev.get("rule", "?"))
            cuenta[(prio, regla)] += 1
            if (prio.upper() == "CRITICAL" and regla.lower().startswith("argus")
                    and len(ejemplos[regla]) < a.ejemplos):
                ejemplos[regla].append(ev)
            if a.contiene and a.contiene in linea:
                ultimas.append(ev)

    crit_argus = sum(n for (pr, r), n in cuenta.items()
                     if pr.upper() == "CRITICAL" and r.lower().startswith("argus"))
    print(f"[FALCO-RESUMEN] {a.fichero}: eventos={total} lineas_no_json={no_json} "
          f"CRITICAL_argus={crit_argus}")
    print("  cuenta por (prioridad, regla):")
    for (pr, r), n in sorted(cuenta.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {n:6d}  {pr:<10} {r}")
    for regla, evs in sorted(ejemplos.items()):
        print(f"  ejemplos CRITICAL de «{regla}» (los {len(evs)} primeros):")
        for ev in evs:
            mostrar(ev)
    if a.contiene:
        print(f"  últimos {len(ultimas)} eventos que contienen «{a.contiene}»:")
        for ev in ultimas:
            mostrar(ev)
    return 0


if __name__ == "__main__":
    sys.exit(main())
