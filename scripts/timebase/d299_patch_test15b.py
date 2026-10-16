#!/usr/bin/env python3
"""DAY299: el contrafactual de 15b usaba 300 pps, que reentra en presion en la misma ventana aunque el hueco
la saque (ratio 30 >= k_in). El rebase importa en la banda de histeresis: 20 pps sobre base 10,5 -> sin rebase
sale y no vuelve (ratio 2 < k_in); con rebase sigue (1,905 >= k_out). --check | --apply desde la raiz."""
import os
import sys

P = "sniffer/tests/test_ddos_victim_board.cpp"
M = "[DDOS-ESTADO-PERSIST-D299-15B]"
EDITS = [
    ("        // 15b rebase: primera ventana publicada (seq 2) con la victima presente -> sigue bajo presion,\n"
     "        // EWMA congelada; sin rebase (gap 2) el episodio terminaria\n",
     "        // 15b " + M + " rebase en la banda de histeresis (k_out <= ratio < k_in): 20 pps sobre base 10,5.\n"
     "        // Sin rebase el gap 2 la saca y no vuelve a entrar (ratio 2 < k_in); con rebase sigue bajo presion\n"
     "        // con la EWMA congelada. Con un ataque fuerte (300 pps, ratio 30) reentra solo: el rebase protege\n"
     "        // los ataques moderados.\n"),
    ("        dd::victim_ewma_step(sin_rebase, 2, 300.0, p);\n",
     "        dd::victim_ewma_step(sin_rebase, 2, 20.0, p);\n"),
    ("        const double rat = dd::victim_ewma_step(st, 2, 300.0, p);\n",
     "        const double rat = dd::victim_ewma_step(st, 2, 20.0, p);\n"),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    t = open(P, encoding="utf-8").read()
    if M in t:
        print("[YA-APLICADO]")
        return 0
    for old, _ in EDITS:
        if t.count(old) != 1:
            print(f"[ABORTA] ancla {t.count(old)} veces: {old.strip()[:80]}")
            return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones pendientes en {P}")
        return 0
    for old, new in EDITS:
        t = t.replace(old, new, 1)
    tmp = P + ".d299tmp"
    open(tmp, "w", encoding="utf-8").write(t)
    os.replace(tmp, P)
    print(f"[APLICADO] {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
