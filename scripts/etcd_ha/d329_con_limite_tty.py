#!/usr/bin/env python3
"""DAY329 [CON-LIMITE-TTY-D329] con_limite.pl: si la entrada estándar es un terminal, la orden la recibe de /dev/null
(en su propio grupo, al leer el terminal la detenía SIGTTIN hasta el límite: falso "no contesta" de vagrant ssh -c
lanzado a mano). Test con un pseudoterminal de verdad (scripts/emecas/test_con_limite.py), en test-kernel-homogeneo.
Va DESPUÉS del commit de d329_c7_limite.py (parte del Makefile que deja ese parcheador).

Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d329_con_limite_tty.py [--apply]
Sin --apply solo comprueba. Con --apply escribe, y solo si TODO cuadra: sha256 de partida de cada fichero que modifica,
cada ancla exactamente las veces esperadas y ningún fichero nuevo ya existente. Si algo falla no escribe nada.
"""
import hashlib, os, sys

NUEVOS = {'scripts/emecas/test_con_limite.py': ('#!/usr/bin/env python3\n"""[CON-LIMITE-TTY-D329] tests de scripts/emecas/con_limite.pl (Mac, raíz del repo; biblioteca estándar).\n\nCon un pseudoterminal de verdad como entrada: una orden que lee la entrada no se queda detenida hasta el límite (el\nfalso "no contesta" de SIGTTIN). Además: la entrada de un fichero llega intacta, un cuelgue se corta en el límite sin\ndejar hijos ni nietos vivos, y el código de salida de la orden se respeta.\n"""\nimport os, pty, subprocess, sys, tempfile, time\n\nP = "scripts/emecas/con_limite.pl"\nfallos = 0\ncasos = 0\n\n\ndef caso(nombre, ok, detalle=""):\n    global fallos, casos\n    casos += 1\n    if not ok:\n        fallos += 1\n    print(("✅ " if ok else "❌ ") + nombre + ("" if ok else "  (" + detalle + ")"))\n\n\ndef lanza(lim, orden, stdin):\n    t0 = time.time()\n    r = subprocess.run(["perl", P, str(lim)] + orden, stdin=stdin, capture_output=True, text=True)\n    return r.returncode, r.stdout, time.time() - t0\n\n\nif not os.path.isfile(P):\n    sys.exit("❌ ejecutar desde la raíz del repo")\n\nmaestro, esclavo = pty.openpty()\nrc, out, dt = lanza(5, ["sh", "-c", "read x; echo leido=$x"], esclavo)\ncaso("entrada de un terminal: la orden que lee no se detiene (lee fin de fichero)", rc == 0 and "leido=" in out and dt < 4,\n     "rc=%d, %.1f s, salida %r" % (rc, dt, out))\nrc, out, dt = lanza(5, ["sh", "-c", "test -t 0 && echo TERMINAL || echo SIN_TERMINAL"], esclavo)\ncaso("entrada de un terminal: la orden no la recibe", rc == 0 and "SIN_TERMINAL" in out, "rc=%d, salida %r" % (rc, out))\nos.close(esclavo)\nos.close(maestro)\n\nwith tempfile.TemporaryFile() as f:\n    f.write(b"linea uno\\nlinea dos\\n")\n    f.seek(0)\n    rc, out, dt = lanza(5, ["cat"], f)\ncaso("entrada de un fichero: llega intacta", rc == 0 and out == "linea uno\\nlinea dos\\n", "rc=%d, salida %r" % (rc, out))\n\nmarca = "31.%d" % os.getpid()  # una duración única para encontrar el nieto si sobreviviera\nrc, out, dt = lanza(2, ["sh", "-c", "sleep %s & sleep %s; echo no-debe-salir" % (marca, marca)], subprocess.DEVNULL)\nvivos = subprocess.run(["pgrep", "-f", "sleep " + marca], capture_output=True, text=True).stdout.split()\ncaso("cuelgue: 142 en el límite (2 s + 2 s de gracia)", rc == 142 and dt < 6 and "no-debe-salir" not in out,\n     "rc=%d, %.1f s" % (rc, dt))\ncaso("cuelgue: no quedan hijos ni nietos vivos", not vivos, "vivos: %s" % vivos)\nfor p in vivos:\n    os.kill(int(p), 9)\n\nrc, out, dt = lanza(5, ["sh", "-c", "exit 7"], subprocess.DEVNULL)\ncaso("código de salida de la orden: se respeta", rc == 7, "rc=%d" % rc)\nrc, out, dt = lanza(5, ["/no/existe/orden"], subprocess.DEVNULL)\ncaso("orden inexistente: 127", rc == 127, "rc=%d" % rc)\n\nprint("%d/%d casos" % (casos - fallos, casos))\nsys.exit(1 if fallos else 0)\n', 493)}

MODIFICA = {'scripts/emecas/con_limite.pl': ('0621ed971de78b2daf0d2bbaf375ec207fd67a47dba391333d88d748adef9cc0', [('#!/usr/bin/perl\n# [KERNEL-HOMOGENEO-D329] (anfitrión) con_limite.pl <segundos> <orden> [args...]: ejecuta la orden con tiempo límite.\n# La orden va en su propio grupo de procesos y, si vence el límite, se mata el GRUPO entero (TERM y, a los 2 s, KILL) y\n# sale con 142. Un alarm sobre vagrant solo no basta: su ssh hijo sigue vivo con la salida abierta y quien lee esa\n# salida se queda esperando (medido DAY329 en test_kernel_homogeneo.sh: 61 s con un límite de 10). Sin la orden: 127.\n# Si la orden muere por una señal: 128 + señal; si no, su código de salida.\nuse strict;\nuse warnings;\nmy $lim = shift @ARGV;\ndie "uso: con_limite.pl <segundos> <orden> [args...]\\n" unless defined $lim && $lim =~ /\\A[1-9][0-9]*\\z/ && @ARGV;\nmy $pid = fork();\ndie "con_limite.pl: fork: $!\\n" unless defined $pid;\nif ($pid == 0) {\n  setpgrp(0, 0);\n  exec { $ARGV[0] } @ARGV;\n  exit 127;\n}\n$SIG{ALRM} = sub {\n  kill \'TERM\', -$pid;\n  sleep 2;\n  kill \'KILL\', -$pid;\n  waitpid($pid, 0);\n  exit 142;\n};\nalarm $lim;\nwaitpid($pid, 0);\nalarm 0;\nmy $st = $?;\nexit(($st & 127) ? 128 + ($st & 127) : $st >> 8);\n', '#!/usr/bin/perl\n# [KERNEL-HOMOGENEO-D329] (anfitrión) con_limite.pl <segundos> <orden> [args...]: ejecuta la orden con tiempo límite.\n# La orden va en su propio grupo de procesos y, si vence el límite, se mata el GRUPO entero (TERM y, a los 2 s, KILL) y\n# sale con 142. Un alarm sobre vagrant solo no basta: su ssh hijo sigue vivo con la salida abierta y quien lee esa\n# salida se queda esperando (medido DAY329 en test_kernel_homogeneo.sh: 61 s con un límite de 10). Sin la orden: 127.\n# Si la orden muere por una señal: 128 + señal; si no, su código de salida.\n# [CON-LIMITE-TTY-D329] Si la entrada estándar es un terminal, la orden la recibe de /dev/null: en su propio grupo queda\n# en segundo plano respecto al terminal, y al leerlo el sistema la detendría (SIGTTIN) hasta que venciera el límite, un\n# falso "no contesta" (vagrant ssh -c lee la entrada para el ssh). Un fichero o una tubería se respetan.\nuse strict;\nuse warnings;\nmy $lim = shift @ARGV;\ndie "uso: con_limite.pl <segundos> <orden> [args...]\\n" unless defined $lim && $lim =~ /\\A[1-9][0-9]*\\z/ && @ARGV;\nmy $pid = fork();\ndie "con_limite.pl: fork: $!\\n" unless defined $pid;\nif ($pid == 0) {\n  setpgrp(0, 0);\n  if (-t STDIN) { open(STDIN, \'<\', \'/dev/null\') or exit 127; }\n  exec { $ARGV[0] } @ARGV;\n  exit 127;\n}\n$SIG{ALRM} = sub {\n  kill \'TERM\', -$pid;\n  sleep 2;\n  kill \'KILL\', -$pid;\n  waitpid($pid, 0);\n  exit 142;\n};\nalarm $lim;\nwaitpid($pid, 0);\nalarm 0;\nmy $st = $?;\nexit(($st & 127) ? 128 + ($st & 127) : $st >> 8);\n', 1)]), 'Makefile': ('a732954b30fb3ca5ef4914c0508ef3083fb2749dc9c5017e6d11c7c014b2a3bf', [('test-kernel-homogeneo:\n\t@ruby scripts/emecas/test_lab_comun.rb\n\t@bash scripts/emecas/test_kernel_homogeneo.sh\n', 'test-kernel-homogeneo:\n\t@ruby scripts/emecas/test_lab_comun.rb\n\t@python3 -I scripts/emecas/test_con_limite.py\n\t@bash scripts/emecas/test_kernel_homogeneo.sh\n', 1)])}

def main():
    aplicar = "--apply" in sys.argv[1:]
    if not os.path.isfile("Vagrantfile") or not os.path.isfile("Makefile"):
        sys.exit("❌ ejecutar desde la raíz del repo")
    errores, resultado = [], {}
    for ruta in NUEVOS:
        if os.path.exists(ruta):
            errores.append("ya existe " + ruta)
    for ruta, (sha_partida, cambios) in MODIFICA.items():
        datos = open(ruta, "rb").read()
        h = hashlib.sha256(datos).hexdigest()
        if h != sha_partida:
            errores.append("%s: sha256 de partida %s, esperado %s" % (ruta, h, sha_partida))
            continue
        texto = datos.decode("utf-8")
        for viejo, nuevo, veces in cambios:
            n = texto.count(viejo)
            if n != veces:
                errores.append("%s: ancla %d veces, esperadas %d: %r" % (ruta, n, veces, viejo[:90]))
            else:
                texto = texto.replace(viejo, nuevo)
        resultado[ruta] = texto
    if errores:
        print("❌ no se escribe nada:")
        for e in errores:
            print("   - " + e)
        sys.exit(1)
    if not aplicar:
        print("✅ todo cuadra (sin --apply no se escribe nada): %d nuevos, %d modificados" % (len(NUEVOS), len(resultado)))
        return
    for ruta, (contenido, modo) in NUEVOS.items():
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        os.chmod(ruta, modo)
        print("  + %s  sha256=%s" % (ruta, hashlib.sha256(contenido.encode()).hexdigest()))
    for ruta, texto in resultado.items():
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        print("  ~ %s  sha256=%s" % (ruta, hashlib.sha256(texto.encode()).hexdigest()))
    print("✅ aplicado")

if __name__ == "__main__":
    main()
