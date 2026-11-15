#!/usr/bin/python3 -I
# scripts/vigilancia/falco_silencio.py — [FALCO-SILENCIO-D327] DEBT-FALCO-RUIDO-ADMIN-001 (F2, último trozo): el test de
# silencio de Falco. Exige 0 eventos CRITICAL (o más graves) de reglas argus_* en cada VM con Falco, desde que se creó
# la VM: todo /var/log/falco/eventos.json y sus rotados (eventos.json.1, eventos.json.N.gz). En EMECAS va justo antes de
# lab-e2e (decisión de Alonso DAY325): lab-e2e-vigilancia provoca CRITICAL a propósito (C5) y va después.
# Solo biblioteca estándar. Dos órdenes:
#   lab [--desde T] [--espera-s N] VM...   en el Mac, raíz del repo (make falco-silencio): lanza «medir» en cada VM con
#                                          vagrant ssh y da el veredicto. rc 0 PASA, 1 FALLA, 2 uso.
#   medir [--desde T] [--espera-s N]       EN la VM, como root (sudo python3 -I /vagrant/scripts/vigilancia/falco_silencio.py
#                                          medir). rc 0 silencio, 1 ruido (hay CRITICAL), 2 no medido.
# Parámetros (los dos opcionales; EMECAS no pasa ninguno):
#   --desde T      solo eventos desde T. Formato AAAA-MM-DDTHH:MM:SSZ (UTC, como el campo time de Falco). Sin él, todo:
#                  desde la creación de la VM. Para medir a mano en VMs que ya tienen historia.
#   --espera-s N   segundos que se espera a que Falco escriba el evento de la sonda. Entero en [1, 60]; defecto 10.
# Un 0 CRITICAL solo vale si Falco estaba mirando. Por eso «medir», ANTES de contar:
#   1 exige falco-modern-bpf.service en marcha;
#   2 lanza una SONDA: nobody intenta leer una clave vigilada de la VM (la primera que exista de SONDA_GLOBS). El
#     kernel se lo niega (EACCES) y Falco tiene que escribir un WARNING de argus_lab_clave_intento_fallido con esa ruta y
#     ese usuario en menos de N s (como el caso C6 de lab-e2e-vigilancia). Prueba, en ESA VM y en ESE momento, que Falco
#     corre, que tiene cargadas las reglas de aRGus y que escribe en el fichero que se cuenta. No es CRITICAL: no rompe
#     el silencio. Deja una alerta 100552 (Warning) en el manager de Wazuh por VM y corrida.
# NO MEDIDO (y por tanto FALLA): Falco parado, sin fichero de eventos, sin clave para la sonda, nobody LEE la clave,
# la sonda no aparece, o alguna línea que no es un evento válido (no se puede clasificar: no se da por buena).
# Eventos de reglas que no son argus_* (no debería haber: argus_salida.yaml las apaga) se enseñan, no hacen fallar.
# Salida de «medir» (la lee «lab»; valores sin '|'):
#   SILENCIO|vm=..|veredicto=SILENCIO|RUIDO|NO-MEDIDO|motivo=..|falco=..|sonda=..|ficheros=N|lineas=N|anteriores=N|
#            critical=N|warning=N|notice=N|otras=N|ajenas=N|malas=N|primero=..|ultimo=..
#   SILENCIO-GRUPO|nivel=critical|warning|ajena|n=N|regla=..|proc=..|padre=..|fichero=..|usuario=..|primera=..|ultima=..
#   SILENCIO-NOTICE|n=N|regla=..
# Coste: una pasada por los ficheros de eventos, O(n) en líneas; memoria, O(grupos distintos).
import glob
import gzip
import json
import os
import re
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True  # se ejecuta desde /vagrant: sin __pycache__ en el repo

DIR_EVENTOS = "/var/log/falco"
BASE = "eventos.json"
UNIDAD = "falco-modern-bpf.service"
EN_VM = "/vagrant/scripts/vigilancia/falco_silencio.py"
REGLA_SONDA = "argus_lab_clave_intento_fallido"
USUARIO_SONDA = "nobody"
# Claves vigiladas por argus_lab_fichero_secreto (provisioning/falco/argus_lab.yaml); la sonda usa la primera que exista
SONDA_GLOBS = ("/etc/etcd/tls/*.key", "/etc/argus-pki/*.key", "/etc/ml-defender/*/seed.bin")
GRAVES = ("emergency", "alert", "critical")
AVISOS = ("error", "warning")
ESPERA_DEF, ESPERA_MIN, ESPERA_MAX = 10, 1, 60
PASO_SONDA_S = 0.5
LIMITE_VM_S = 180  # una VM que no contesta en este tiempo es NO MEDIDO
RE_DESDE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
RE_TIME = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
RE_VM = re.compile(r"^[a-z0-9-]{1,32}$")
USO = ("uso: falco_silencio.py lab [--desde AAAA-MM-DDTHH:MM:SSZ] [--espera-s N] VM...\n"
       "     falco_silencio.py medir [--desde AAAA-MM-DDTHH:MM:SSZ] [--espera-s N]")


def limpio(v):
    """Un valor para una línea SILENCIO: sin '|' ni saltos de línea."""
    return re.sub(r"[|\r\n]", "_", str(v))


class Resumen:
    def __init__(self):
        self.lineas = self.malas = self.anteriores = 0
        self.critical = self.warning = self.notice = self.otras = self.ajenas = 0
        self.grupos = {}   # (nivel, regla, proc, padre, fichero, usuario) -> [n, primera, última]
        self.notices = {}  # regla -> n
        self.primero = self.ultimo = None

    def _grupo(self, nivel, regla, e, t):
        of = e.get("output_fields")
        if not isinstance(of, dict):
            of = {}
        k = (nivel, regla, str(of.get("proc.exepath", "?")), str(of.get("proc.pexepath", "?")),
             str(of.get("fd.name", "-")), str(of.get("user.name", "?")))
        g = self.grupos.setdefault(k, [0, t, t])
        g[0] += 1
        g[1], g[2] = min(g[1], t), max(g[2], t)


def contar(lineas, r, desde=None):
    """Suma a r los eventos de un fichero (iterable de líneas). desde: AAAA-MM-DDTHH:MM:SSZ o None."""
    for linea in lineas:
        if not linea.strip():
            continue
        r.lineas += 1
        try:
            e = json.loads(linea)
        except ValueError:
            r.malas += 1
            continue
        if not isinstance(e, dict):
            r.malas += 1
            continue
        regla, prio, t = e.get("rule"), e.get("priority"), e.get("time")
        if not (isinstance(regla, str) and regla and isinstance(prio, str) and prio
                and isinstance(t, str) and RE_TIME.match(t)):
            r.malas += 1
            continue
        if desde and t[:19] < desde[:19]:
            r.anteriores += 1
            continue
        r.primero = t if r.primero is None else min(r.primero, t)
        r.ultimo = t if r.ultimo is None else max(r.ultimo, t)
        p = prio.lower()
        if not regla.startswith("argus_"):
            r.ajenas += 1
            r._grupo("ajena", regla, e, t)
        elif p in GRAVES:
            r.critical += 1
            r._grupo("critical", regla, e, t)
        elif p in AVISOS:
            r.warning += 1
            r._grupo("warning", regla, e, t)
        elif p == "notice":
            r.notice += 1
            r.notices[regla] = r.notices.get(regla, 0) + 1
        else:
            r.otras += 1


def ficheros_de(directorio):
    return sorted(glob.glob(os.path.join(directorio, BASE + "*")))


def abrir(ruta):
    if ruta.endswith(".gz"):
        return gzip.open(ruta, "rt", encoding="utf-8", errors="replace")
    return open(ruta, encoding="utf-8", errors="replace")


def falco_estado():
    try:
        p = subprocess.run(["systemctl", "is-active", UNIDAD], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return p.stdout.decode("utf-8", "replace").strip() or "desconocido"
    except OSError:
        return "desconocido"


def elegir_sonda(globs=SONDA_GLOBS):
    for g in globs:
        c = sorted(glob.glob(g))
        if c:
            return c[0]
    return None


def lanzar_sonda(ruta):
    """nobody intenta leer la clave. True si NO pudo (lo esperado). La salida no va a ningún sitio."""
    p = subprocess.run(["/usr/sbin/runuser", "-u", USUARIO_SONDA, "--", "/usr/bin/cat", ruta],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.returncode != 0


def sonda_vista(ruta_eventos, desde_byte, clave):
    """¿Hay, después de desde_byte, un evento de la sonda (regla, fichero y usuario)? Si el fichero rotó, desde 0."""
    try:
        with open(ruta_eventos, "rb") as f:
            f.seek(desde_byte if os.path.getsize(ruta_eventos) >= desde_byte else 0)
            for b in f:
                try:
                    e = json.loads(b.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if not isinstance(e, dict) or e.get("rule") != REGLA_SONDA:
                    continue
                of = e.get("output_fields")
                if isinstance(of, dict) and of.get("fd.name") == clave and of.get("user.name") == USUARIO_SONDA:
                    return True
    except OSError:
        pass
    return False


def medir(desde=None, espera_s=ESPERA_DEF, directorio=DIR_EVENTOS, es_root=None, estado=falco_estado,
          elegir=elegir_sonda, lanzar=lanzar_sonda, dormir=time.sleep, vm=None):
    """(rc, líneas de salida). Lo de fuera (root, systemctl, sonda, espera) entra por parámetro: se prueba sin VM."""
    motivos = []
    if es_root is None:
        es_root = os.geteuid() == 0
    actual = os.path.join(directorio, BASE)
    falco = estado()
    sonda = "-"
    if not es_root:
        motivos.append("hay que ejecutarlo como root (sudo)")
    elif falco != "active":
        motivos.append("%s no está en marcha (%s)" % (UNIDAD, falco))
    elif not os.path.isfile(actual):
        motivos.append("no existe %s" % actual)
    else:
        clave = elegir()
        if clave is None:
            motivos.append("ninguna clave vigilada para la sonda (%s)" % " ".join(SONDA_GLOBS))
        else:
            sonda = clave
            byte0 = os.path.getsize(actual)
            if not lanzar(clave):
                motivos.append("%s LEYÓ %s: permisos rotos" % (USUARIO_SONDA, clave))
            else:
                vista, pasos = False, int(espera_s / PASO_SONDA_S)
                for _ in range(pasos + 1):
                    if sonda_vista(actual, byte0, clave):
                        vista = True
                        break
                    dormir(PASO_SONDA_S)
                if not vista:
                    motivos.append("Falco no escribió el evento de la sonda (%s, %s, %s) en %d s"
                                   % (REGLA_SONDA, clave, USUARIO_SONDA, espera_s))
    r = Resumen()
    fs = ficheros_de(directorio)
    for f in fs:
        try:
            with abrir(f) as fh:
                contar(fh, r, desde)
        except (OSError, EOFError) as e:
            motivos.append("no leo %s (%s)" % (f, e.__class__.__name__))
    if r.malas:
        motivos.append("%d líneas que no son un evento válido de Falco" % r.malas)
    if r.critical:
        veredicto, rc = "RUIDO", 1
    elif motivos:
        veredicto, rc = "NO-MEDIDO", 2
    else:
        veredicto, rc = "SILENCIO", 0
    campos = [("vm", vm or socket.gethostname()), ("veredicto", veredicto), ("motivo", "; ".join(motivos) or "-"),
              ("falco", falco), ("sonda", sonda), ("ficheros", len(fs)), ("lineas", r.lineas),
              ("anteriores", r.anteriores), ("critical", r.critical), ("warning", r.warning), ("notice", r.notice),
              ("otras", r.otras), ("ajenas", r.ajenas), ("malas", r.malas), ("primero", r.primero or "-"),
              ("ultimo", r.ultimo or "-")]
    sal = ["SILENCIO|" + "|".join("%s=%s" % (k, limpio(v)) for k, v in campos)]
    for (nivel, regla, proc, padre, fich, usu), (n, t1, t2) in sorted(r.grupos.items()):
        g = [("nivel", nivel), ("n", n), ("regla", regla), ("proc", proc), ("padre", padre), ("fichero", fich),
             ("usuario", usu), ("primera", t1), ("ultima", t2)]
        sal.append("SILENCIO-GRUPO|" + "|".join("%s=%s" % (k, limpio(v)) for k, v in g))
    for regla, n in sorted(r.notices.items()):
        sal.append("SILENCIO-NOTICE|n=%d|regla=%s" % (n, limpio(regla)))
    return rc, sal


# ── En el Mac ────────────────────────────────────────────────────────────────────────────────────────────────────────
def orden_vm(vm, desde, espera_s):
    o = "sudo python3 -I %s medir --espera-s %d" % (EN_VM, espera_s)
    if desde:
        o += " --desde " + desde
    return ["vagrant", "ssh", vm, "-c", o]


def correr(orden):
    """(rc, salida estándar). 124 si no contesta a tiempo, 127 si no se pudo lanzar."""
    try:
        p = subprocess.run(orden, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=LIMITE_VM_S)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""


def campos_de(linea):
    d = {}
    for trozo in linea.split("|")[1:]:
        k, sep, v = trozo.partition("=")
        if sep:
            d[k] = v
    return d


def analizar(rc, texto):
    """De lo que devolvió vagrant ssh: (veredicto, motivo, resumen{}, grupos[{}], notices[{}]). Nunca da SILENCIO si
    falta algo o algo no cuadra: vagrant ssh devuelve las líneas con \\r y avisos propios delante."""
    lineas = [l.replace("\r", "").strip() for l in texto.splitlines()]
    res = [l for l in lineas if l.startswith("SILENCIO|")]
    grupos = [campos_de(l) for l in lineas if l.startswith("SILENCIO-GRUPO|")]
    notices = [campos_de(l) for l in lineas if l.startswith("SILENCIO-NOTICE|")]
    if len(res) != 1:
        return "NO-MEDIDO", "%d líneas SILENCIO| en la salida (se exige 1; rc %d)" % (len(res), rc), {}, grupos, notices
    d = campos_de(res[0])
    v = d.get("veredicto")
    crit = d.get("critical", "")
    if v not in ("SILENCIO", "RUIDO", "NO-MEDIDO") or not crit.isdigit():
        return "NO-MEDIDO", "línea SILENCIO| mal formada (veredicto=%r critical=%r)" % (v, crit), d, grupos, notices
    coherente = rc == {"SILENCIO": 0, "RUIDO": 1, "NO-MEDIDO": 2}[v]
    if v == "SILENCIO":
        coherente = coherente and int(crit) == 0 and d.get("motivo") == "-"
    elif v == "RUIDO":
        coherente = coherente and int(crit) > 0
    if not coherente:
        return "NO-MEDIDO", "salida incoherente (veredicto=%s critical=%s motivo=%s rc=%d)" % (
            v, crit, d.get("motivo"), rc), d, grupos, notices
    return v, d.get("motivo", "-"), d, grupos, notices


def lab(vms, desde=None, espera_s=ESPERA_DEF, ejecutar=correr, pinta=print):
    """rc 0 si TODAS las VMs dan SILENCIO; 1 si alguna da RUIDO o no se pudo medir."""
    crit_total, ruidosas, sin_medir = 0, [], []
    pinta("[FALCO-SILENCIO] %d VMs (%s); eventos %s; sonda: espera de %d s" % (
        len(vms), " ".join(vms), ("desde " + desde) if desde else "desde la creación de cada VM", espera_s))
    for vm in vms:
        rc, texto = ejecutar(orden_vm(vm, desde, espera_s))
        v, motivo, d, grupos, notices = analizar(rc, texto)
        pinta("[FALCO-SILENCIO] %s: %s  critical=%s warning=%s notice=%s líneas=%s ficheros=%s falco=%s sonda=%s" % (
            vm, v, d.get("critical", "?"), d.get("warning", "?"), d.get("notice", "?"), d.get("lineas", "?"),
            d.get("ficheros", "?"), d.get("falco", "?"), d.get("sonda", "?")))
        if d:
            pinta("    primero=%s último=%s anteriores=%s otras=%s ajenas=%s malas=%s" % (
                d.get("primero", "?"), d.get("ultimo", "?"), d.get("anteriores", "?"), d.get("otras", "?"),
                d.get("ajenas", "?"), d.get("malas", "?")))
        if v != "SILENCIO" and motivo != "-":
            pinta("    motivo: %s" % motivo)
        for g in grupos:
            pinta("    %-8s %5s  %s proc=%s padre=%s fichero=%s usuario=%s (primera %s, última %s)" % (
                g.get("nivel", "?"), g.get("n", "?"), g.get("regla", "?"), g.get("proc", "?"), g.get("padre", "?"),
                g.get("fichero", "?"), g.get("usuario", "?"), g.get("primera", "?"), g.get("ultima", "?")))
        for n in notices:
            pinta("    notice   %5s  %s" % (n.get("n", "?"), n.get("regla", "?")))
        if v == "RUIDO":
            ruidosas.append(vm)
            crit_total += int(d["critical"])
        elif v != "SILENCIO":
            sin_medir.append(vm)
    if not ruidosas and not sin_medir:
        pinta("[FALCO-SILENCIO] PASA: 0 CRITICAL de reglas argus_* en las %d VMs (%s); Falco en marcha y viendo la "
              "sonda en todas" % (len(vms), " ".join(vms)))
        return 0
    partes = []
    if ruidosas:
        partes.append("%d CRITICAL de reglas argus_* (%s)" % (crit_total, " ".join(ruidosas)))
    if sin_medir:
        partes.append("sin medir: %s (un 0 sin medir no dice nada)" % " ".join(sin_medir))
    pinta("[FALCO-SILENCIO] FALLA: " + "; ".join(partes))
    return 1


def argumentos(a):
    """(desde, espera_s, resto) o lanza ValueError con campo, formato y límites."""
    desde, espera, resto, i = None, ESPERA_DEF, [], 0
    while i < len(a):
        if a[i] in ("--desde", "--espera-s"):
            if i + 1 >= len(a):
                raise ValueError("%s: falta el valor" % a[i])
            v = a[i + 1]
            if a[i] == "--desde":
                if not RE_DESDE.match(v):
                    raise ValueError("--desde='%s' mal formado: AAAA-MM-DDTHH:MM:SSZ (UTC), p. ej. 2026-11-15T05:00:00Z" % v)
                desde = v
            else:
                if not (v.isdigit() and ESPERA_MIN <= int(v) <= ESPERA_MAX):
                    raise ValueError("--espera-s='%s' mal formado: entero en [%d, %d] (defecto %d)" % (
                        v, ESPERA_MIN, ESPERA_MAX, ESPERA_DEF))
                espera = int(v)
            i += 2
        elif a[i].startswith("--"):
            raise ValueError("opción desconocida: %s" % a[i])
        else:
            resto.append(a[i])
            i += 1
    return desde, espera, resto


def main(a):
    if not a or a[0] not in ("lab", "medir"):
        print(USO)
        return 2
    try:
        desde, espera, resto = argumentos(a[1:])
        if a[0] == "medir" and resto:
            raise ValueError("medir no lleva más argumentos: %s" % " ".join(resto))
        if a[0] == "lab":
            if not resto:
                raise ValueError("lab: falta la lista de VMs")
            for vm in resto:
                if not RE_VM.match(vm):
                    raise ValueError("VM '%s' mal formada: [a-z0-9-], de 1 a 32 caracteres" % vm)
            if len(set(resto)) != len(resto):
                raise ValueError("lab: VMs repetidas: %s" % " ".join(resto))
    except ValueError as e:
        print("[FALCO-SILENCIO] %s" % e)
        print(USO)
        return 2
    if a[0] == "lab":
        return lab(resto, desde, espera)
    rc, sal = medir(desde, espera)
    print("\n".join(sal))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
