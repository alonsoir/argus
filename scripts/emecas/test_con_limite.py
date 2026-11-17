#!/usr/bin/env python3
"""[CON-LIMITE-TTY-D329] tests de scripts/emecas/con_limite.pl (Mac, raíz del repo; biblioteca estándar).

Con un pseudoterminal de verdad como entrada: una orden que lee la entrada no se queda detenida hasta el límite (el
falso "no contesta" de SIGTTIN). Además: la entrada de un fichero llega intacta, un cuelgue se corta en el límite sin
dejar hijos ni nietos vivos, y el código de salida de la orden se respeta.
"""
import os, pty, subprocess, sys, tempfile, time

P = "scripts/emecas/con_limite.pl"
fallos = 0
casos = 0


def caso(nombre, ok, detalle=""):
    global fallos, casos
    casos += 1
    if not ok:
        fallos += 1
    print(("✅ " if ok else "❌ ") + nombre + ("" if ok else "  (" + detalle + ")"))


def lanza(lim, orden, stdin):
    t0 = time.time()
    r = subprocess.run(["perl", P, str(lim)] + orden, stdin=stdin, capture_output=True, text=True)
    return r.returncode, r.stdout, time.time() - t0


if not os.path.isfile(P):
    sys.exit("❌ ejecutar desde la raíz del repo")

maestro, esclavo = pty.openpty()
rc, out, dt = lanza(5, ["sh", "-c", "read x; echo leido=$x"], esclavo)
caso("entrada de un terminal: la orden que lee no se detiene (lee fin de fichero)", rc == 0 and "leido=" in out and dt < 4,
     "rc=%d, %.1f s, salida %r" % (rc, dt, out))
rc, out, dt = lanza(5, ["sh", "-c", "test -t 0 && echo TERMINAL || echo SIN_TERMINAL"], esclavo)
caso("entrada de un terminal: la orden no la recibe", rc == 0 and "SIN_TERMINAL" in out, "rc=%d, salida %r" % (rc, out))
os.close(esclavo)
os.close(maestro)

with tempfile.TemporaryFile() as f:
    f.write(b"linea uno\nlinea dos\n")
    f.seek(0)
    rc, out, dt = lanza(5, ["cat"], f)
caso("entrada de un fichero: llega intacta", rc == 0 and out == "linea uno\nlinea dos\n", "rc=%d, salida %r" % (rc, out))

marca = "31.%d" % os.getpid()  # una duración única para encontrar el nieto si sobreviviera
rc, out, dt = lanza(2, ["sh", "-c", "sleep %s & sleep %s; echo no-debe-salir" % (marca, marca)], subprocess.DEVNULL)
vivos = subprocess.run(["pgrep", "-f", "sleep " + marca], capture_output=True, text=True).stdout.split()
caso("cuelgue: 142 en el límite (2 s + 2 s de gracia)", rc == 142 and dt < 6 and "no-debe-salir" not in out,
     "rc=%d, %.1f s" % (rc, dt))
caso("cuelgue: no quedan hijos ni nietos vivos", not vivos, "vivos: %s" % vivos)
for p in vivos:
    os.kill(int(p), 9)

rc, out, dt = lanza(5, ["sh", "-c", "exit 7"], subprocess.DEVNULL)
caso("código de salida de la orden: se respeta", rc == 7, "rc=%d" % rc)
rc, out, dt = lanza(5, ["/no/existe/orden"], subprocess.DEVNULL)
caso("orden inexistente: 127", rc == 127, "rc=%d" % rc)

print("%d/%d casos" % (casos - fallos, casos))
sys.exit(1 if fallos else 0)
