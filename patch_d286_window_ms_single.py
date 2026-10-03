#!/usr/bin/env python3
"""DAY286: una sola definicion de la duracion de ventana (redondeo al ms).
Mueve ddos_window_ms() de ddos_kernel_reader.hpp a ddos_kernel_agg.hpp (junto a DdosWindow)
y hace que DdosVictimBoard la use (antes truncaba: -1 ms en ~50 % de las ventanas frente al CSV).
Atomico, idempotente (marca [DDOS-WMS-D286]). Uso: --check | --apply. No compila."""
import sys

R = "/vagrant/sniffer/include"
MARK = "[DDOS-WMS-D286]"
AGG, READER, BOARD = f"{R}/ddos_kernel_agg.hpp", f"{R}/ddos_kernel_reader.hpp", f"{R}/ddos_victim_board.hpp"

FUNC = ("// Duracion de la ventana en ms, redondeada al mas cercano. 0 = baseline (o reloj inconsistente).\n"
        "inline uint64_t ddos_window_ms(const DdosWindow& w) {\n"
        "    if (w.t_start_ns == 0 || w.t_end_ns <= w.t_start_ns) return 0;\n"
        "    return (w.t_end_ns - w.t_start_ns + 500000ull) / 1000000ull;\n"
        "}\n")
AGG_ANCHOR = "    uint32_t evicted = 0;         // estaban en la lectura anterior y ya no estan\n};\n"
BOARD_OLD = "        s->window_ms = (w.t_end_ns > w.t_start_ns) ? (w.t_end_ns - w.t_start_ns) / 1'000'000ULL : 0;\n"
BOARD_NEW = f"        s->window_ms = ddos_window_ms(w);  // {MARK} definicion unica (redondeo), la misma que el CSV\n"

SUBS = [
    (READER, FUNC, f"// {MARK} ddos_window_ms() vive en ddos_kernel_agg.hpp (definicion unica)\n"),
    (AGG, AGG_ANCHOR, AGG_ANCHOR + f"\n// {MARK} definicion unica de la duracion de ventana (lector, CSV y tablero)\n" + FUNC),
    (BOARD, BOARD_OLD, BOARD_NEW),
]

def die(m):
    print(f"ABORTO: {m}")
    sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode not in ("--check", "--apply"):
    die("uso: --check | --apply")
paths = [AGG, READER, BOARD]
txt = {p: open(p).read() for p in paths}
marked = [p for p in paths if MARK in txt[p]]
if len(marked) == len(paths):
    print("YA APLICADO. Nada que hacer.")
    sys.exit(0)
if marked:
    die(f"aplicacion parcial previa: {marked}")
for p in (AGG, READER):
    if "namespace sniffer {" not in txt[p]:
        die(f"{p} no esta en namespace sniffer: mover la funcion cambiaria su nombre cualificado")
new = dict(txt)
for p, old, rep in SUBS:
    c = new[p].count(old)
    if c != 1:
        die(f"{p}: fragmento encontrado {c} veces (esperado 1):\n{old}")
    new[p] = new[p].replace(old, rep)
if new[AGG].index("inline uint64_t ddos_window_ms") < new[AGG].index("struct DdosWindow {"):
    die("la funcion quedaria antes de DdosWindow")
print("Plan:")
for p in paths:
    print(f"  {p}: marcas {new[p].count(MARK)}, definiciones de ddos_window_ms: "
          f"{new[p].count('inline uint64_t ddos_window_ms')}")
if mode == "--check":
    print("\n--check: no se escribe nada.")
    sys.exit(0)
for p in paths:
    open(p, "w").write(new[p])
print("\nAPLICADO.")
