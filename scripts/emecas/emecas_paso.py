#!/usr/bin/env python3
# scripts/emecas/emecas_paso.py — [EMECAS-PROGRESO-D322] avance de EMECAS (petición de Alonso DAY322): cada paso de las
# recetas emecas, emecas++ y emecas+++ va envuelto por este ayudante, que lo ejecuta tal cual (misma salida, mismo
# código de salida: si un paso falla, EMECAS para igual que antes) y apunta cuándo empieza y cuándo acaba.
# Corre en el Mac (donde corre make), solo biblioteca estándar. Ficheros, en logs/lab/ del repo:
#   emecas_progreso.txt          la corrida en curso: META, INICIO y FIN de cada paso (una línea por suceso)
#   emecas_tiempos_<meta>.tsv    lo que tardó cada paso en la última corrida de <meta> que terminó bien
#   emecas/<fecha>_<meta>/       [EMECAS-RESUMEN-D322] una carpeta por corrida (se guardan todas: decisión de Alonso):
#       NN_<paso>.log            la salida completa de cada paso (también sale por la salida de siempre, sin cambios)
#       resumen.md               al final, y también si un paso falla: meta, rama, commit, cambios sin commit, horas,
#                                tabla de pasos (duración, resultado, diferencia con la última corrida buena), las líneas
#                                de veredicto de cada paso y, si falló, las últimas líneas del paso que falló
# El porcentaje y la hora de fin salen de esos tiempos MEDIDOS, no de contar pasos (lab-e2e dura más de una hora y
# emecas-frescura segundos). La primera corrida de una meta no tiene tiempos: solo pasos hechos y tiempo transcurrido.
#   emecas_paso.py inicio META                   empieza una corrida (vacía emecas_progreso.txt)
#   emecas_paso.py paso META NOMBRE -- ORDEN...  ejecuta ORDEN como el paso NOMBRE
#   emecas_paso.py fin META RECETA               si RECETA es la META, la corrida terminó bien: guarda sus tiempos
#   emecas_paso.py ver                           la barra (make emecas-progreso, desde otra terminal)
# Coste: lineal en el número de pasos (una lectura de dos ficheros pequeños por paso).
import os
import re
import subprocess
import sys
import time

DIR = os.environ.get("EMECAS_PROGRESO_DIR", "logs/lab")
PROGRESO = os.path.join(DIR, "emecas_progreso.txt")
METAS = ("emecas", "emecas++", "emecas+++")
ANCHO = 30
COLA = 40           # líneas finales del paso que falló, en el resumen
MAX_VEREDICTO = 60  # líneas de veredicto por paso, en el resumen (el resto, contado)
VEREDICTO = re.compile(r"(\bPASA\b|\bFALLA\b|RESULTADO|PASSED|FAILED|❌|NO PASA)")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def tiempos_de(meta):
    """{nombre: segundos} y orden de la última corrida buena de meta; ({}, []) si no hay."""
    t, orden = {}, []
    try:
        with open(os.path.join(DIR, "emecas_tiempos_%s.tsv" % meta), encoding="utf-8") as f:
            for ln in f:
                p = ln.rstrip("\n").split("\t")
                if len(p) == 2 and p[1].isdigit() and not ln.startswith("#"):
                    t[p[0]] = int(p[1]); orden.append(p[0])
    except OSError:
        pass
    return t, orden


def leer_progreso(extra=None):
    """(meta, t0, pasos) con pasos = [[nombre, inicio, fin|None, rc|None], ...] en orden. Si extra es un dict, recibe
    las líneas CARPETA y GIT de la corrida."""
    meta, t0, pasos = None, None, []
    try:
        with open(PROGRESO, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if extra is not None and len(p) >= 2 and p[0] in ("CARPETA", "GIT"):
                    extra[p[0]] = ln.rstrip("\n").split(" ", 1)[1]
                elif len(p) >= 3 and p[0] == "META":
                    meta, t0 = p[1], int(p[2])
                elif len(p) >= 3 and p[0] == "INICIO":
                    pasos.append([p[1], int(p[2]), None, None])
                elif len(p) >= 4 and p[0] == "FIN" and pasos and pasos[-1][0] == p[1]:
                    pasos[-1][2], pasos[-1][3] = int(p[2]), int(p[3])
    except OSError:
        pass
    return meta, t0, pasos


def dur(s):
    s = max(0, int(s)); h, m = s // 3600, (s % 3600) // 60
    return "%dh%02dm" % (h, m) if h else ("%dm%02ds" % (m, s % 60) if m else "%ds" % s)


def hora(epoch):
    return time.strftime("%H:%M", time.localtime(epoch))


def estado(ahora=None):
    """Texto del avance (lo usan paso y ver)."""
    ahora = int(ahora if ahora is not None else time.time())
    meta, t0, pasos = leer_progreso()
    if meta is None:
        return "[EMECAS-PROGRESO] no hay ninguna corrida de EMECAS empezada (%s)" % PROGRESO
    prev, orden = tiempos_de(meta)
    hechos = [p for p in pasos if p[2] is not None]
    curso = pasos[-1] if pasos and pasos[-1][2] is None else None
    malo = next((p for p in hechos if p[3] != 0), None)
    n = len(hechos) + (1 if curso else 0)
    tot = ("/%d" % len(orden)) if orden else ""
    # [EMECAS-PROGRESO-D323] con un paso fallido el reloj de la cabecera se para en el fallo: antes seguía contando hasta
    # ahora («desde las 18:09 (4h09m)» horas después de parar, medido DAY322)
    if malo:
        lin = ["[EMECAS-PROGRESO] %s desde las %s hasta las %s (%s)" % (meta, hora(t0), hora(malo[2]), dur(malo[2] - t0))]
    else:
        lin = ["[EMECAS-PROGRESO] %s desde las %s (%s)" % (meta, hora(t0), dur(ahora - t0))]
    c = carpeta()
    if c:
        lin.append("  logs y resumen: %s/" % c)
    if malo:
        lin.append("  ❌ paso %s FALLÓ (rc=%d) tras %s: EMECAS parado" % (malo[0], malo[3], dur(malo[2] - malo[1])))
    elif curso:
        p = prev.get(curso[0])
        lin.append("  paso %d%s %s en curso %s%s" % (n, tot, curso[0], dur(ahora - curso[1]),
                   (" (la última vez %s)" % dur(p)) if p is not None else " (sin tiempo anterior)"))
    elif hechos:
        lin.append("  %d%s pasos hechos; el último, %s" % (len(hechos), tot, hechos[-1][0]))
    if prev and not malo:
        total = sum(prev.values())
        hecho = sum(prev.get(p[0], p[2] - p[1]) for p in hechos)
        if curso:
            hecho += min(ahora - curso[1], prev.get(curso[0], 0))
        hecho = min(hecho, total)
        quedan = sum(prev[x] for x in orden if x not in {p[0] for p in pasos})
        if curso:
            quedan += max(0, prev.get(curso[0], 0) - (ahora - curso[1]))
        pct = 100.0 * hecho / total if total else 0.0
        llenos = int(round(ANCHO * pct / 100.0))
        lin.append("  [%s%s] %3.0f %%  quedan ~%s, fin ~%s (tiempos de la última %s buena)" % (
            "█" * llenos, "░" * (ANCHO - llenos), pct, dur(quedan), hora(ahora + quedan), meta))
    elif not prev:
        lin.append("  sin tiempos de una %s anterior terminada: aún no hay porcentaje (los tendrá la próxima)" % meta)
    return "\n".join(lin)


def anotar(texto):
    with open(PROGRESO, "a", encoding="utf-8") as f:
        f.write(texto + "\n")


def git_info():
    """rama, commit y nº de ficheros con cambios sin commit del repo en el directorio actual."""
    def g(*a):
        try:
            r = subprocess.run(["git"] + list(a), capture_output=True, text=True, timeout=20)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    rama, commit, estado_git = g("rev-parse", "--abbrev-ref", "HEAD"), g("rev-parse", "--short=12", "HEAD"), g("status", "--porcelain")
    if rama is None or commit is None:
        return "git no disponible (no es un repo o no hay git)"
    n = len([x for x in (estado_git or "").splitlines() if x.strip()])
    return "rama=%s commit=%s cambios_sin_commit=%d" % (rama, commit, n)


def carpeta():
    extra = {}
    leer_progreso(extra)
    return extra.get("CARPETA")


def log_de(c, n, nombre):
    return os.path.join(c, "%02d_%s.log" % (n, re.sub(r"[^A-Za-z0-9_.+-]", "_", nombre)))


def ejecutar(orden, ruta_log):
    """Ejecuta orden: su salida (stdout y stderr juntos, como el 2>&1 de siempre) va a la salida y a ruta_log."""
    with open(ruta_log, "wb") as lg:
        p = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for linea in iter(p.stdout.readline, b""):
            sys.stdout.buffer.write(linea); sys.stdout.buffer.flush()
            lg.write(linea)
        p.stdout.close()
        return p.wait()


def escribir_resumen(final):
    """resumen.md de la corrida en curso. final: 'PASA' o 'FALLA'. Una pasada por el log de cada paso."""
    extra = {}
    meta, t0, pasos = leer_progreso(extra)
    c = extra.get("CARPETA")
    if not meta or not c or not os.path.isdir(c):
        return None
    prev, _ = tiempos_de(meta)
    ahora = int(time.time())
    fin = max([p[2] for p in pasos if p[2] is not None] or [ahora])
    L = ["# EMECAS %s — %s" % (meta, final), "",
         "- %s" % extra.get("GIT", "git: sin dato"),
         "- inicio %s, fin %s, duración %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0)),
                                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(fin)), dur(fin - t0)),
         "- tiempos de referencia: %s" % ("última %s buena (emecas_tiempos_%s.tsv)" % (meta, meta) if prev
                                          else "ninguna %s buena anterior" % meta),
         "", "| # | paso | duración | resultado | frente a la última buena |", "|---|---|---|---|---|"]
    malo = None
    for i, p in enumerate(pasos, 1):
        if p[2] is None:
            res, d = "sin terminar", "-"
        else:
            res, d = ("✅" if p[3] == 0 else "❌ rc=%d" % p[3]), dur(p[2] - p[1])
            if p[3] != 0 and malo is None:
                malo = (i, p)
        ant = prev.get(p[0])
        if ant is None or p[2] is None:
            dif = "-"
        else:
            x = (p[2] - p[1]) - ant
            dif = "%s%s (antes %s)" % ("+" if x >= 0 else "-", dur(abs(x)), dur(ant))
        L.append("| %d | %s | %s | %s | %s |" % (i, p[0], d, res, dif))
    L += ["", "## Veredictos de cada paso", ""]
    for i, p in enumerate(pasos, 1):
        ruta = log_de(c, i, p[0])
        lineas, n_ok, n_mal = [], 0, 0
        try:
            with open(ruta, "rb") as f:
                for b in f:
                    t = ANSI.sub("", b.decode("utf-8", "replace")).rstrip()
                    if "✅" in t: n_ok += 1
                    if "❌" in t or "FALLA" in t or "FAILED" in t: n_mal += 1
                    if VEREDICTO.search(t): lineas.append(t)
        except OSError:
            continue
        L.append("### %d %s (✅ %d, ❌/FALLA %d)" % (i, p[0], n_ok, n_mal))
        if lineas:
            L.append("```")
            L += lineas[:MAX_VEREDICTO]
            if len(lineas) > MAX_VEREDICTO:
                L.append("… y %d líneas de veredicto más en %s" % (len(lineas) - MAX_VEREDICTO, os.path.basename(ruta)))
            L.append("```")
        L.append("")
    if malo:
        i, p = malo
        ruta = log_de(c, i, p[0])
        try:
            with open(ruta, "rb") as f:
                cola = [ANSI.sub("", b.decode("utf-8", "replace")).rstrip() for b in f][-COLA:]
        except OSError:
            cola = ["(sin log)"]
        L += ["## Falló: paso %d %s (rc=%d), últimas %d líneas de %s" % (i, p[0], p[3], len(cola), os.path.basename(ruta)),
              "", "```"] + cola + ["```", ""]
    ruta = os.path.join(c, "resumen.md")
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    os.replace(ruta + ".tmp", ruta)
    return ruta


def main(a):
    if len(a) >= 2 and a[0] == "inicio" and a[1] in METAS:
        t0 = int(time.time())
        c = os.path.join(DIR, "emecas", "%s_%s" % (time.strftime("%Y%m%dT%H%M%S", time.localtime(t0)), a[1]))
        os.makedirs(c, exist_ok=True)
        with open(PROGRESO, "w", encoding="utf-8") as f:
            f.write("META %s %d\nCARPETA %s\nGIT %s\n" % (a[1], t0, c, git_info()))
        print("[EMECAS-PROGRESO] %s empieza a las %s; avance desde otra terminal: make emecas-progreso; logs y resumen "
              "en %s/" % (a[1], hora(t0), c), flush=True)
        return 0
    if len(a) >= 5 and a[0] == "paso" and a[1] in METAS and a[3] == "--" and a[2].strip():
        nombre, orden = a[2], a[4:]
        _, _, pasos = leer_progreso()
        c = carpeta()
        anotar("INICIO %s %d" % (nombre, int(time.time())))
        print(estado(), flush=True)
        try:
            if c and os.path.isdir(c):
                rc = ejecutar(orden, log_de(c, len(pasos) + 1, nombre))
            else:  # corrida empezada antes de [EMECAS-RESUMEN-D322] o sin carpeta: como antes, sin log propio
                rc = subprocess.call(orden)
        except OSError as e:
            print("[EMECAS-PROGRESO] no se pudo lanzar %s: %s" % (" ".join(orden), e), flush=True)
            rc = 127
        anotar("FIN %s %d %d" % (nombre, int(time.time()), rc))
        _, _, pasos = leer_progreso()
        print("[EMECAS-PROGRESO] %s %s en %s" % ("✅" if rc == 0 else "❌", nombre,
              dur(pasos[-1][2] - pasos[-1][1]) if pasos else "?"), flush=True)
        if rc != 0:
            r = escribir_resumen("FALLA")
            if r:
                print("[EMECAS-RESUMEN] %s" % r, flush=True)
        return rc
    if len(a) >= 3 and a[0] == "fin" and a[1] in METAS and a[2] in METAS:
        if a[1] != a[2]:
            return 0  # una receta intermedia de la cadena (emecas dentro de emecas+++): la corrida sigue
        meta, t0, pasos = leer_progreso()
        if meta != a[1] or any(p[2] is None or p[3] != 0 for p in pasos):
            print("[EMECAS-PROGRESO] corrida incompleta o con fallos: no se guardan sus tiempos", flush=True)
            return 0
        ruta = os.path.join(DIR, "emecas_tiempos_%s.tsv" % meta)
        with open(ruta + ".tmp", "w", encoding="utf-8") as f:
            f.write("# [EMECAS-PROGRESO-D322] %s terminada bien el %s: segundos de cada paso\n" %
                    (meta, time.strftime("%Y-%m-%d %H:%M", time.localtime(t0))))
            for p in pasos:
                f.write("%s\t%d\n" % (p[0], p[2] - p[1]))
        r = escribir_resumen("PASA")   # antes de guardar los tiempos: compara con la corrida buena ANTERIOR
        os.replace(ruta + ".tmp", ruta)
        print("[EMECAS-PROGRESO] %s terminada en %s: tiempos guardados en %s (darán el porcentaje la próxima vez)" %
              (meta, dur(int(time.time()) - t0), ruta), flush=True)
        if r:
            print("[EMECAS-RESUMEN] %s" % r, flush=True)
        return 0
    if a == ["ver"]:
        print(estado())
        return 0
    print("uso: emecas_paso.py inicio META | paso META NOMBRE -- ORDEN... | fin META RECETA | ver  (META: %s)" %
          " ".join(METAS), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
