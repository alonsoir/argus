#!/usr/bin/env python3
"""
join_flood_escalation.py  —  DAY272, cierra paso 1 + paso 2 de la grieta B.

El log NO trae la 5-tupla en la línea de features, así que no se puede filtrar
el flood por IP. Se ancla el flood en su firma de flujo: Feature[17] Packet
Length Mean == 482 (dominante y limpio en el histograma; el ambiente da 0.0).

Une por BLOQUE DE THREAD (no por proximidad-grep, no por event= que solo está
en DUAL-SCORE): acumula estado por thread-id y confirma un registro al ver el
veredicto `DDoS: class=`. Maneja el interleaving de threads del pipeline.

De cada registro flood saca: escalation, entropy, disp, symmetry, class,
ddos_prob. Reporta:
  - nº de registros flood vistos (el recall se lee sobre estos, no sobre 766).
  - recall DDoS sobre el flood (fracción class=1).
  - tabla escalation vs class  → ¿la rampa de ventana discrimina?
  - tabla entropy   vs class  → contraste con el discriminador de DAY272.

Uso:  python3 join_flood_escalation.py [logs/lab/detector.log]
Solo lee. No escribe nada.
"""

import re
import sys
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else "logs/lab/detector.log"
FLOOD_PLM = 482.0  # firma del flood; ver histograma Packet Length Mean

# thread-id = 4º corchete: [ts] [ml-detector] [level] [TID] msg
RE_TID   = re.compile(r"\[ml-detector\] \[\w+\] \[(\d+)\]")
RE_PLM   = re.compile(r"Feature\[17\] Packet Length Mean\s*:\s*([-0-9.]+)")
RE_EVENT = re.compile(r"\[DUAL-SCORE\] event=(\S+?),")
RE_DDOSF = re.compile(r"DDoS Features:")
RE_ESC   = re.compile(r"escalation=([-0-9.]+)")
RE_ENT   = re.compile(r"\bentropy=([-0-9.]+)")   # \b evita chocar con ransomware entropy=
RE_DISP  = re.compile(r"disp=([-0-9.]+)")
RE_SYM   = re.compile(r"symmetry=([-0-9.]+)")
RE_VERD  = re.compile(r"DDoS: class=([01]).*?ddos_prob=([-0-9.]+)")


def bucket(x, step=0.005):
    """Agrupa un float en cubos de 'step' para la tabla (0.000, 0.005, ...)."""
    return round((x // step) * step, 3)


def main():
    state = defaultdict(dict)   # tid -> campos acumulados del bloque en curso
    records = []                # registros confirmados (un veredicto DDoS)

    try:
        fh = open(LOG, "r", encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"[ABORT] no encuentro {LOG}", file=sys.stderr)
        sys.exit(2)

    with fh:
        for line in fh:
            m = RE_TID.search(line)
            if not m:
                continue
            tid = m.group(1)
            s = state[tid]

            mp = RE_PLM.search(line)
            if mp:
                s.clear()                      # nuevo bloque de features level1
                s["plm"] = float(mp.group(1))
                continue

            me = RE_EVENT.search(line)
            if me:
                s["event"] = me.group(1)
                continue

            if RE_DDOSF.search(line):
                for key, rx in (("esc", RE_ESC), ("ent", RE_ENT),
                                ("disp", RE_DISP), ("sym", RE_SYM)):
                    mm = rx.search(line)
                    if mm:
                        s[key] = float(mm.group(1))
                continue

            mv = RE_VERD.search(line)
            if mv:
                s["class"] = int(mv.group(1))
                s["ddos_prob"] = float(mv.group(2))
                records.append(dict(s))        # confirma registro
                state[tid] = {}                # resetea el thread
                continue

    # --- filtro flood ---
    flood = [r for r in records if r.get("plm") == FLOOD_PLM
             and "class" in r and "esc" in r]

    print(f"log            : {LOG}")
    print(f"registros DDoS : {len(records)} (con veredicto)")
    print(f"flood (plm=482): {len(flood)}")
    if not flood:
        print("[!] 0 registros flood — revisar firma o el join.")
        sys.exit(0)

    pos = sum(1 for r in flood if r["class"] == 1)
    print(f"recall DDoS    : {pos}/{len(flood)} = {pos/len(flood):.3f}  (class=1 sobre flood)\n")

    def tabla(campo, titulo):
        by = defaultdict(lambda: [0, 0])       # cubo -> [n_class0, n_class1]
        for r in flood:
            if campo in r:
                by[bucket(r[campo])][r["class"]] += 1
        print(f"{titulo}  (cubos de 0.005)")
        print(f"  {'valor':>8} | {'NORMAL':>6} | {'DDOS':>5} | {'%DDOS':>6}")
        for k in sorted(by):
            n0, n1 = by[k]
            tot = n0 + n1
            print(f"  {k:>8.3f} | {n0:>6} | {n1:>5} | {100*n1/tot:>5.1f}%")
        print()

    tabla("esc", "escalation vs class")
    tabla("ent", "entropy vs class")

    # ¿escalation separa NORMAL de DDOS dentro del flood?
    esc1 = [r["esc"] for r in flood if r["class"] == 1 and "esc" in r]
    esc0 = [r["esc"] for r in flood if r["class"] == 0 and "esc" in r]
    if esc0 and esc1:
        import statistics as st
        print(f"escalation media  NORMAL={st.mean(esc0):.4f}  DDOS={st.mean(esc1):.4f}")
        print(f"escalation máx    NORMAL={max(esc0):.4f}  DDOS={max(esc1):.4f}")


if __name__ == "__main__":
    main()