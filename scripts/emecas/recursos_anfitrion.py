#!/usr/bin/python3 -I
# scripts/emecas/recursos_anfitrion.py — [RECURSOS-ANFITRION-D327] comprobación de los recursos del Mac anfitrión antes
# de EMECAS y de lab-e2e (decisión de Alonso DAY325: «los recursos que permiten respirar al laboratorio»; si faltan,
# avisa y NO arranca, diciendo que es por falta de recursos, para parar esos procesos o relanzar en otro momento).
# Solo biblioteca estándar; macOS (sysctl). En otro sistema las medidas no se pueden leer: NO MEDIDO y no arranca.
#   python3 -I scripts/emecas/recursos_anfitrion.py PERFIL [--config RUTA]      (make anfitrion-recursos)
# rc 0 PASA, 1 FALLA (falta un recurso o no se pudo medir), 2 uso.
# Perfiles (medido DAY327, MacBook Pro de 16 hilos y 32 GB):
#   emecas   el Mac SIN el lab: en la receta emecas va justo después de vagrant destroy. Con las VMs de la corrida
#            anterior arriba, el swap y la carga son los del propio lab y un umbral de arranque no dejaría relanzar.
#            Tras el destroy, con el lab antes en reposo: carga 3,3, swap 0,15 GB, nivel 84. Tras el destroy nada
#            más acabar una corrida: carga 7,8 (la media de 5 min aún baja), swap 1,5 GB (lo que el lab empujó de
#            otros procesos; de 7,2 GB con el lab), nivel 81. [RECURSOS-UMBRALES-D327]
#   lab_e2e  el Mac CON el lab arriba (make lab-e2e suelto). Lab sano: carga a 5 min hasta 8,2, swap hasta 7,2 GB,
#            nivel de memoria mínimo 67, presión 1. Mac ahogado (DAY325, lab-e2e en rojo): carga 46, swap 5,3 GB.
#            El swap NO separa el Mac sano del ahogado (7,2 GB sano, 5,3 GB ahogado): su umbral es solo un techo.
#            Separan la carga (8 frente a 46) y la presión de memoria.
# Qué se mide:
#   carga_5min        media de carga a 5 minutos (os.getloadavg)
#   swap_usado_mb     swap en uso, MB (sysctl vm.swapusage)
#   presion_memoria   nivel de presión de memoria de macOS: 1 normal, 2 aviso, 4 crítico (kern.memorystatus_vm_pressure_level)
#   nivel_memoria     porcentaje de memoria disponible según macOS, 0-100 (kern.memorystatus_level). Los GB «libres» de
#                     vm_stat no sirven con VMs: su memoria sale como inactiva.
#   disco_libre_gb    GB libres en el disco del repo
# El JSON es la ley (scripts/emecas/recursos_anfitrion.json): un umbral por medida y perfil. Campo ausente o mal
# formado: se aplica el defecto de aquí (los mismos valores del JSON) avisando con campo, formato y límites, y se
# sigue. Cada umbral se escribe con su valor y de dónde sale (JSON o defecto).
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recursos_anfitrion.json")
PERFILES = ("emecas", "lab_e2e")
# campo: (sentido, mínimo, máximo, defecto emecas, defecto lab_e2e, qué es)
CAMPOS = (
    ("carga_5min_max", "max", 1, 256, 12, 12, "carga a 5 min"),
    ("swap_usado_mb_max", "max", 0, 65536, 4096, 16384, "swap usado (MB)"),
    ("presion_memoria_max", "max", 1, 4, 1, 1, "presión de memoria (1 normal, 2 aviso, 4 crítico)"),
    ("nivel_memoria_min", "min", 0, 100, 70, 60, "nivel de memoria disponible (%)"),
    ("disco_libre_gb_min", "min", 1, 100000, 50, 50, "disco libre (GB)"),
)
UNIDADES = {"K": 1.0 / 1024, "M": 1.0, "G": 1024.0}


def pinta_(s):
    print("[RECURSOS] " + s)


def umbrales(perfil, ruta, pinta=pinta_):
    """{campo: valor} del perfil; lo que falte o esté mal, el defecto, avisando. El proceso sigue siempre."""
    datos, motivo = {}, None
    try:
        with open(ruta, encoding="utf-8") as f:
            j = json.load(f)
        if isinstance(j, dict) and isinstance(j.get(perfil), dict):
            datos = j[perfil]
        else:
            motivo = "sin objeto '%s'" % perfil
    except OSError as e:
        motivo = "no se puede leer (%s)" % e.__class__.__name__
    except ValueError:
        motivo = "no es JSON"
    if motivo:
        pinta("AVISO %s: %s; se aplican TODOS los defectos del código" % (ruta, motivo))
    u = {}
    for campo, _s, lo, hi, d_em, d_lab, _q in CAMPOS:
        d = d_em if perfil == "emecas" else d_lab
        v = datos.get(campo)
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            u[campo] = d
            pinta("%s.%s=%d (defecto del código: %s; entero en [%d, %d])" % (
                perfil, campo, d, "ausente" if v is None else "'%s' mal formado" % (v,), lo, hi))
        else:
            u[campo] = v
            pinta("%s.%s=%d (JSON)" % (perfil, campo, v))
    return u


def sysctl(clave):
    try:
        e = dict(os.environ, LC_ALL="C")
        p = subprocess.run(["sysctl", "-n", clave], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=e, timeout=10)
        return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def swap_mb(texto):
    """'total = 1024.00M  used = 252.75M  free = ...' -> 252.75 (MB). Coma o punto. None si no se entiende."""
    m = re.search(r"used = ([0-9]+(?:[.,][0-9]+)?)([KMG])", texto or "")
    return float(m.group(1).replace(",", ".")) * UNIDADES[m.group(2)] if m else None


def entero(texto):
    return int(texto) if texto is not None and re.match(r"^[0-9]+$", texto) else None


def medir(lee=sysctl, carga=os.getloadavg, disco=shutil.disk_usage, raiz="."):
    """{medida: número o None (no medido)}."""
    m = {}
    try:
        m["carga_5min"] = float(carga()[1])
    except (OSError, AttributeError, IndexError, TypeError, ValueError):
        m["carga_5min"] = None
    m["swap_usado_mb"] = swap_mb(lee("vm.swapusage"))
    m["presion_memoria"] = entero(lee("kern.memorystatus_vm_pressure_level"))
    m["nivel_memoria"] = entero(lee("kern.memorystatus_level"))
    try:
        m["disco_libre_gb"] = disco(raiz).free / float(1024 ** 3)
    except (OSError, AttributeError):
        m["disco_libre_gb"] = None
    return m


def comprobar(u, m, pinta=pinta_):
    """Lista de faltas (vacía = PASA). Una medida sin leer es una falta: un «no lo sé» no deja arrancar."""
    faltas = []
    for campo, sentido, _lo, _hi, _de, _dl, que in CAMPOS:
        medida = campo.rsplit("_", 1)[0]
        v, lim = m.get(medida), u[campo]
        if v is None:
            faltas.append("%s: NO MEDIDO" % que)
            pinta("FALLA %s: NO MEDIDO (umbral %s %d)" % (que, "<=" if sentido == "max" else ">=", lim))
            continue
        bien = v <= lim if sentido == "max" else v >= lim
        txt = "%s: %.2f (%s %d)" % (que, v, "máximo" if sentido == "max" else "mínimo", lim)
        pinta(("PASA  " if bien else "FALLA ") + txt)
        if not bien:
            faltas.append(txt)
    return faltas


def glotones(pinta=pinta_):
    """Al fallar: los procesos que más CPU y más memoria usan, para saber qué parar. Si no se puede, nada."""
    for titulo, orden in (("más CPU", "-r"), ("más memoria", "-m")):
        try:
            p = subprocess.run(["ps", "-Ao", "pcpu,rss,comm", orden], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env=dict(os.environ, LC_ALL="C"), timeout=10)
            lineas = p.stdout.decode("utf-8", "replace").splitlines()[1:6]
        except (OSError, subprocess.TimeoutExpired):
            return
        pinta("los 5 procesos con %s (%%CPU, MB, proceso):" % titulo)
        for l in lineas:
            c = l.split(None, 2)
            if len(c) == 3 and c[1].isdigit():
                pinta("    %6s %7d  %s" % (c[0], int(c[1]) // 1024, c[2][-90:]))


def main(a, pinta=pinta_, medidor=medir, extra=glotones):
    ruta = CONFIG
    if len(a) == 3 and a[1] == "--config":
        ruta, a = a[2], a[:1]
    if len(a) != 1 or a[0] not in PERFILES:
        pinta("uso: recursos_anfitrion.py %s [--config RUTA]" % "|".join(PERFILES))
        return 2
    perfil = a[0]
    pinta("perfil=%s (%s) config=%s" % (perfil, "el Mac sin el lab" if perfil == "emecas" else "el Mac con el lab arriba", ruta))
    u = umbrales(perfil, ruta, pinta)
    faltas = comprobar(u, medidor(), pinta)
    if not faltas:
        pinta("RESULTADO PASA: el anfitrión tiene recursos para el perfil %s" % perfil)
        return 0
    pinta("RESULTADO FALLA: NO se arranca por falta de recursos disponibles en el anfitrión: " + "; ".join(faltas))
    pinta("cierra lo que esté ocupando el Mac o relanza en un momento más tranquilo")
    extra(pinta)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
