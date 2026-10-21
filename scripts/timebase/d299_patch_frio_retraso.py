#!/usr/bin/env python3
"""DAY299: lab_frio.sh acepta RETRASO_S (entero, segundos): el trafico del client empieza RETRASO_S s
despues del paso 6 para que solape con el arranque del sniffer (un pcap disjunto de un solo origen
dura como mucho ~210 s a 300 pps: ~64k puertos de destino por clase). Sin RETRASO_S, igual que DAY298.
Uso: --check | --apply (desde la raiz del repo)."""
import os
import sys

P = "scripts/timebase/lab_frio.sh"
M = "[DAY299-RETRASO]"
OLD = r"""  vagrant ssh client -c "setsid nohup bash -c '$CLI' > /tmp/$N.client.txt 2>&1 < /dev/null & sleep 2; pgrep -af '^(sudo )?tcpreplay'" || falla "el trafico del client no esta en marcha (no hay tcpreplay vivo)"
"""
NEW = r"""  # [DAY299-RETRASO] RETRASO_S opcional: sleep antes del trafico; la comprobacion acepta ese sleep vivo
  CLI_EF="$CLI"; PAT='^(sudo )?tcpreplay'
  if [ -n "${RETRASO_S:-}" ]; then
    case "$RETRASO_S" in ''|*[!0-9]*) falla "RETRASO_S debe ser un entero de segundos (es '$RETRASO_S')";; esac
    CLI_EF="sleep $RETRASO_S; $CLI"; PAT="^(sudo )?tcpreplay|^sleep $RETRASO_S\$"
    echo "RETRASO_S=$RETRASO_S: el trafico del client empieza $RETRASO_S s despues de este paso"
  fi
  vagrant ssh client -c "setsid nohup bash -c '$CLI_EF' > /tmp/$N.client.txt 2>&1 < /dev/null & sleep 2; pgrep -af '$PAT'" || falla "el trafico del client no esta en marcha (no hay tcpreplay ni sleep de RETRASO_S vivo)"
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    t = open(P, encoding="utf-8").read()
    if M in t:
        print("[YA-APLICADO]")
        return 0
    n = t.count(OLD)
    if n != 1:
        print(f"[ABORTA] la linea de lanzamiento aparece {n} veces")
        return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] 1 edicion pendiente en {P}")
        return 0
    tmp = P + ".d299tmp"
    open(tmp, "w", encoding="utf-8").write(t.replace(OLD, NEW, 1))
    os.replace(tmp, P)
    print(f"[APLICADO] {M} en {P}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
