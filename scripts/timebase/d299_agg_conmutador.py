#!/usr/bin/env python3
"""DAY299: apaga o enciende kernel_space.ddos_kernel_agg_enabled en sniffer/config/sniffer.json para
medir que [DDOS-V2-ANOMALIA] salta con el agregador apagado. SIEMPRE dejarlo en --on al terminar.
Uso: --estado | --off | --on (desde la raiz del repo)."""
import json
import os
import sys

P = "sniffer/config/sniffer.json"
ON = '"ddos_kernel_agg_enabled": true,'
OFF = '"ddos_kernel_agg_enabled": false,'


def estado(t):
    on, off = t.count(ON), t.count(OFF)
    if on == 1 and off == 0:
        return "on"
    if off == 1 and on == 0:
        return "off"
    return f"desconocido (on={on} off={off})"


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--estado", "--off", "--on"):
        print("uso: --estado | --off | --on")
        return 2
    t = open(P, encoding="utf-8").read()
    e = estado(t)
    if sys.argv[1] == "--estado":
        print(f"[AGG] ddos_kernel_agg_enabled={e}")
        return 0 if e in ("on", "off") else 1
    quiero = sys.argv[1][2:]
    if e == quiero:
        print(f"[AGG] ya estaba {quiero}")
        return 0
    if e not in ("on", "off"):
        print(f"[ABORTA] estado {e}: revisar {P} a mano")
        return 1
    nuevo = t.replace(ON, OFF, 1) if quiero == "off" else t.replace(OFF, ON, 1)
    try:
        json.loads(nuevo)
    except ValueError as ex:
        print(f"[ABORTA] el resultado no es JSON valido: {ex}")
        return 1
    tmp = P + ".d299tmp"
    open(tmp, "w", encoding="utf-8").write(nuevo)
    os.replace(tmp, P)
    print(f"[AGG] ddos_kernel_agg_enabled: {e} -> {quiero}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
