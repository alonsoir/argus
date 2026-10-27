#!/usr/bin/env python3
"""DAY309: dice si hay un socket TCP en LISTEN en el puerto dado, leyendo /proc/net/tcp y tcp6 (sin pgrep -f, que se
encuentra a si mismo cuando su propia linea de comandos contiene el patron). Uso: d309_escucha.py PUERTO
Imprime ESCUCHA o NO_ESCUCHA y nada mas (rc 0). Cualquier otra salida, o ninguna, es un error: el que llama mira el
TEXTO, no el codigo de salida, porque un fallo no capturado de Python tambien sale con rc 1."""
import sys


def escucha(port):
    leido = False
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lineas = open(f).read().splitlines()[1:]
        except FileNotFoundError:
            continue
        leido = True
        for l in lineas:
            c = l.split()
            if int(c[1].rsplit(":", 1)[1], 16) == port and c[3] == "0A":
                return True
    if not leido:
        raise RuntimeError("no hay /proc/net/tcp ni /proc/net/tcp6")
    return False


if __name__ == "__main__":
    try:
        print("ESCUCHA" if escucha(int(sys.argv[1])) else "NO_ESCUCHA")
    except SystemExit:
        raise
    except BaseException as e:  # cualquier error -> 2
        print(f"d309_escucha: ERROR {e!r}", file=sys.stderr)
        sys.exit(2)
