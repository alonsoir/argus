#!/usr/bin/env python3
"""scripts/vigilancia/argus_disco.py — [VIGILANCIA-D321] ADR-060 8e.4d: uso del disco donde Vault escribe su audit.

Si el disco del audit se llena, Vault deja de responder (un audit device que no puede escribir bloquea las peticiones):
hay que verlo venir. Cada periodo_s mide la partición de `ruta` (como df: usado / (usado + disponible para usuarios),
redondeado hacia arriba) y escribe UNA línea por stdout, que systemd lleva al journal con SyslogIdentifier=argus-disco
y el agente de Wazuh envía al manager (provisioning/wazuh/argus/shared/argus-etcd/agent.conf):

  ARGUS-DISCO ruta=<ruta> uso=<pct> umbral=<pct> estado=OK|ALTO      decoder argus-disco-campos; ALTO -> regla 100541
  ARGUS-DISCO-ERROR <qué>: <detalle>                                regla 100542 (medida o configuración imposibles)
  ARGUS-DISCO-CONFIG ruta=<v> (<origen>) umbral_pct=<v> (<origen>) periodo_s=<v> (<origen>)
      al arrancar y cada vez que cambia la configuración efectiva; origen = fichero | defecto

Configuración: un JSON (por defecto /etc/argus-vigilancia/disco.json, provisioning/vigilancia/disco.json en el repo),
releído en cada ciclo (un cambio vale sin reiniciar). Campos, todos opcionales:
  ruta        ruta absoluta, sin espacios                 defecto /var/log/vault
  umbral_pct  entero en [1, 99]: estado ALTO si uso >= él  defecto 75
  periodo_s   entero en [10, 3600]: segundos entre medidas defecto 60
Un campo fuera de rango, de otro tipo o desconocido, un JSON ilegible o un fichero ausente dan una línea
ARGUS-DISCO-ERROR (alerta en Wazuh) y ese campo toma su defecto: la vigilancia sigue, y el fallo se ve.
Coste: un statvfs y una lectura de un fichero pequeño por ciclo.

Uso: argus_disco.py [CONFIG] [--una-vez]
"""
import json
import math
import os
import sys
import time

CONFIG_DEFECTO = "/etc/argus-vigilancia/disco.json"
# campo: (defecto, mínimo, máximo); ruta no tiene rango.
CAMPOS = {
    "ruta": ("/var/log/vault", None, None),
    "umbral_pct": (75, 1, 99),
    "periodo_s": (60, 10, 3600),
}


def leer_config(ruta_config):
    """Devuelve (valores, origenes, errores). Nunca lanza: lo que no vale se queda en su defecto y se anota."""
    valores = {k: v[0] for k, v in CAMPOS.items()}
    origenes = {k: "defecto" for k in CAMPOS}
    errores = []
    try:
        with open(ruta_config, encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        return valores, origenes, [f"config={ruta_config}: no existe (se usan los defectos)"]
    except (OSError, ValueError) as e:
        return valores, origenes, [f"config={ruta_config}: ilegible ({e}); se usan los defectos"]
    if not isinstance(datos, dict):
        return valores, origenes, [f"config={ruta_config}: no es un objeto JSON; se usan los defectos"]
    for k in sorted(set(datos) - set(CAMPOS)):
        errores.append(f"config={ruta_config}: campo desconocido '{k}' (válidos: {', '.join(CAMPOS)})")
    for k, (defecto, minimo, maximo) in CAMPOS.items():
        if k not in datos:
            continue
        v = datos[k]
        if k == "ruta":
            ok = isinstance(v, str) and v.startswith("/") and v.isprintable() and not any(c.isspace() for c in v)
            regla = "ruta absoluta sin espacios"
        else:
            ok = isinstance(v, int) and not isinstance(v, bool) and minimo <= v <= maximo
            regla = f"entero en [{minimo}, {maximo}]"
        if ok:
            valores[k], origenes[k] = v, "fichero"
        else:
            errores.append(f"config={ruta_config}: {k}={v!r} no vale ({regla}); se usa el defecto {defecto}")
    return valores, origenes, errores


def uso_pct(ruta, statvfs=os.statvfs):
    """Porcentaje de uso de la partición de ruta, como df (Use%): usado / (usado + disponible), hacia arriba."""
    s = statvfs(ruta)
    usado = (s.f_blocks - s.f_bfree) * s.f_frsize
    disponible = s.f_bavail * s.f_frsize
    total = usado + disponible
    if total <= 0:
        raise OSError(f"partición sin bloques (f_blocks={s.f_blocks})")
    return math.ceil(usado * 100 / total)


def linea_config(valores, origenes):
    return "ARGUS-DISCO-CONFIG " + " ".join(f"{k}={valores[k]} ({origenes[k]})" for k in CAMPOS)


def ciclo(ruta_config, anterior, statvfs=os.statvfs):
    """Un ciclo: devuelve (líneas a escribir, periodo_s, clave de la configuración efectiva)."""
    valores, origenes, errores = leer_config(ruta_config)
    lineas = [f"ARGUS-DISCO-ERROR {e}" for e in errores]
    clave = tuple((k, valores[k], origenes[k]) for k in CAMPOS)
    if clave != anterior:
        lineas.append(linea_config(valores, origenes))
    ruta, umbral = valores["ruta"], valores["umbral_pct"]
    try:
        uso = uso_pct(ruta, statvfs)
    except OSError as e:
        lineas.append(f"ARGUS-DISCO-ERROR ruta={ruta}: {e}")
    else:
        estado = "ALTO" if uso >= umbral else "OK"
        lineas.append(f"ARGUS-DISCO ruta={ruta} uso={uso} umbral={umbral} estado={estado}")
    return lineas, valores["periodo_s"], clave


def main(argv):
    args = [a for a in argv if a != "--una-vez"]
    if len(args) > 1 or any(a.startswith("-") for a in args):
        print("uso: argus_disco.py [CONFIG] [--una-vez]", file=sys.stderr)
        return 2
    ruta_config = args[0] if args else CONFIG_DEFECTO
    anterior = None
    while True:
        lineas, periodo, anterior = ciclo(ruta_config, anterior)
        for l in lineas:
            print(l, flush=True)
        if "--una-vez" in argv:
            return 0
        time.sleep(periodo)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
