#!/usr/bin/python3 -I
# argus-infra — [PROTEGIDOS-MANIFIESTO-D319] ADR-060 paso 8e.3d (F-G, F-H; diseño fino G-A..G-G, decisiones de Alonso
# DAY319). La herramienta del administrador que firma el manifiesto de rangos protegidos de SU hospital.
#
#   argus-infra [-c CONFIG] --check-config
#   argus-infra [-c CONFIG] init --desde PLANTILLA [--si]
#   argus-infra [-c CONFIG] list [--version N]
#   argus-infra [-c CONFIG] add (--planta P | --comun) --categoria C --cidr X --interfaz I [--mac M]
#                               --motivo-entrada T --motivo T [--si]
#   argus-infra [-c CONFIG] del (--planta P | --comun) --cidr X --interfaz I --motivo T [--si]
#   argus-infra [-c CONFIG] diff [A [B]]
#   argus-infra [-c CONFIG] verificar [--version N]
#   argus-infra [-c CONFIG] deshacer N --motivo T [--si]
#
# Solo vive en la máquina del admin, nunca en un componente (D9). En el laboratorio, en la VM etcd (D11). Código
# abierto como el resto de aRGus: la seguridad sale de la clave (Vault transit, no exportable) y de la vigilancia, no
# de ocultar este fichero (Kerckhoffs).
#
# Cada cambio (init, add, del, deshacer), en este orden (G-E):
#   1. login en Vault con el certificado de argus-infra (token de 300 s atado a 127.0.0.1; G-D: el firmante sale de
#      esa identidad, "<cn> entidad=<entity_id de Vault>", <= 64 caracteres para que los logs no lo corten);
#   2. GET de la versión vigente al etcd-server: se valida con las mismas reglas que libs/protegidos y su firma con
#      Vault transit verify. Si no verifica, no se construye encima;
#   3. versión N+1 (hash_anterior = sha256 de la carga vigente), validada entera (límites de D2, que fija la
#      configuración, nunca la plantilla ni el manifiesto anterior);
#   4. diff y confirmación tecleando el número de la versión nueva (--si la salta: bootstrap de 8e.5);
#   5. firma con Vault transit sign; 6. verificación de la firma devuelta; 7. PUT al etcd-server con el mismo
#      certificado; 8. GET final: lo vigente tiene que ser, byte a byte, lo publicado; 9. el token se revoca siempre.
#
# Salida: 0 bien; 1 error (red, Vault, verificación, cancelado); 2 uso o configuración; 3 el etcd-server rechazó el PUT
# (con su motivo). Todo va a la salida estándar y las acciones también a syslog (ident argus-infra, facility auth).
#
# Configuración (G-A, el JSON es la ley): /etc/argus-infra/argus-infra.json, ver el _doc del fichero del repo
# tools/argus-infra/argus-infra.lab.json. La identidad (hospital, plantas, límites, URLs, rutas) no tiene defecto
# sano: si falta o está mal, la herramienta no firma. timeout_s sí: [1, 120], 10, con aviso.
import argparse
import base64
import binascii
import datetime
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import syslog
import urllib.parse

CONFIG_DEFECTO = "/etc/argus-infra/argus-infra.json"
FORMATO = "argus-protegidos/v1"
# Límites del formato v1 (los mismos que libs/protegidos/include/protegidos/manifiesto.hpp; no son de operación)
MAX_SOBRE = 4 * 1024 * 1024
MAX_CARGA = 2 * 1024 * 1024
MAX_ENTRADAS = 65536
LIMITE_MIN = 8
CATEGORIAS = ("infraestructura", "intranet", "dmz", "externos_criticos")
CAMPOS_ENTRADA = ("categoria", "cidr", "interfaz", "mac", "motivo")
CAMPOS_CARGA = ("esquema", "hospital_id", "version", "emitido_utc", "firmante", "motivo", "hash_anterior", "limites",
                "comun", "plantas")
MAX_U64 = 2 ** 64 - 1
TIMEOUT_DEFECTO, TIMEOUT_MIN, TIMEOUT_MAX = 10, 1, 120

SALIDA_OK, SALIDA_ERROR, SALIDA_USO, SALIDA_RECHAZO = 0, 1, 2, 3


class Fallo(Exception):
    """Error que termina la orden con un código de salida y un mensaje claro."""

    def __init__(self, mensaje, codigo=SALIDA_ERROR):
        super().__init__(mensaje)
        self.codigo = codigo


class Rechazo(Exception):
    """El manifiesto no vale. motivo: formato | firma | version | hospital | planta | limite (los de libs/protegidos)."""

    def __init__(self, motivo, detalle):
        super().__init__(f"motivo={motivo} {detalle}")
        self.motivo = motivo
        self.detalle = detalle


# ─── salida ────────────────────────────────────────────────────────────────────────────────────────────────────────

_syslog_abierto = False


def registrar(linea, a_syslog=False, prioridad=syslog.LOG_INFO):
    print(linea, flush=True)
    if a_syslog:
        global _syslog_abierto
        if not _syslog_abierto:
            syslog.openlog("argus-infra", syslog.LOG_PID, syslog.LOG_AUTH)
            _syslog_abierto = True
        syslog.syslog(prioridad, linea)


def aviso(linea):
    print(linea, file=sys.stderr, flush=True)


def saneado(s, maximo=64):
    """Para el log: sin caracteres de control (como detalle_protegidos::saneado)."""
    if not isinstance(s, str):
        s = repr(s)
    o = []
    for c in s:
        if len(o) >= maximo:
            o.append("...")
            break
        o.append(c if 0x20 <= ord(c) < 0x7F else "?")
    return "".join(o)


# ─── validador: el porte de libs/protegidos/src/manifiesto.cpp ──────────────────────────────────────────────────────
# Mismas reglas y mismos motivos. Lo único que no hace es verificar la firma Ed25519 (la biblioteca estándar no
# tiene Ed25519): eso lo hace Vault transit verify, y el etcd-server y cada firewall vuelven a verificarla con la
# clave compilada.

def json_estricto(datos):
    """JSON como jsoncpp en strictMode: UTF-8, sin claves duplicadas, sin NaN/Infinity, sin nada detrás."""
    if isinstance(datos, (bytes, bytearray)):
        try:
            texto = bytes(datos).decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"no es UTF-8 ({e.reason})") from None
    else:
        texto = datos

    def pares(ps):
        d = {}
        for k, v in ps:
            if k in d:
                raise ValueError(f"clave duplicada '{saneado(k)}'")
            d[k] = v
        return d

    def constante(c):
        raise ValueError(f"constante {c} no permitida")

    try:
        return json.loads(texto, object_pairs_hook=pares, parse_constant=constante)
    except (json.JSONDecodeError, RecursionError) as e:
        raise ValueError(f"JSON inválido: {saneado(str(e), 120)}") from None


def claves_exactas(o, claves):
    """None si o es un objeto con exactamente esas claves; si no, el error."""
    if not isinstance(o, dict):
        return "no es un objeto"
    for k in sorted(o):
        if k not in claves:
            return f"campo desconocido '{saneado(k)}'"
    for k in claves:
        if k not in o:
            return f"falta el campo '{k}'"
    return None


def es_entero(v):
    return type(v) is int  # bool no es un entero aquí (jsoncpp tampoco lo trata como tal)


def es_id(s):
    return isinstance(s, str) and re.fullmatch(r"[a-z0-9-]{1,64}", s) is not None


def es_interfaz(s):
    return isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,15}", s) is not None


def es_mac(s):
    return isinstance(s, str) and (s == "" or re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", s) is not None)


def es_hex_min(s, n):
    return isinstance(s, str) and re.fullmatch(r"[0-9a-f]{%d}" % n, s) is not None


def es_texto(s, maximo):
    """De 1 a maximo bytes en UTF-8, sin caracteres de control (como es_texto de manifiesto.cpp)."""
    if not isinstance(s, str):
        return False
    try:
        b = s.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return 0 < len(b) <= maximo and all(x >= 0x20 and x != 0x7F for x in b)


def es_fecha_utc(s):
    return isinstance(s, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", s) is not None


def b64_a_bytes(s, maximo):
    """base64 estándar con relleno (sodium_base64_VARIANT_ORIGINAL); None si no vale o pasa de maximo bytes."""
    if not isinstance(s, str) or not s or len(s) > (maximo // 3 + 1) * 4:
        return None
    try:
        b = base64.b64decode(s.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError):
        return None
    return b if len(b) <= maximo else None


def _pton(familia, ip):
    try:
        return socket.inet_pton(familia, ip)
    except (OSError, ValueError):
        return None


def ip_cidr_valido(ip):
    """Porte de argus::is_valid_ip_cidr (common/include/argus/ip_cidr_validator.hpp)."""
    if not isinstance(ip, str) or not ip or len(ip) > 64:
        return False
    if any(c not in "0123456789abcdefABCDEF.:/" for c in ip):
        return False
    if ip.count("/") > 1:
        return False
    parte = ip.split("/", 1)[0]
    v4 = _pton(socket.AF_INET, parte) is not None
    v6 = _pton(socket.AF_INET6, parte) is not None
    if not v4 and not v6:
        return False
    if "/" in ip:
        pref = ip.split("/", 1)[1]
        if not pref or len(pref) > 3 or not all(c in "0123456789" for c in pref):
            return False
        if int(pref) > (128 if v6 else 32):
            return False
    return True


def a_bytes(ip):
    """(v6, 16 bytes) como detalle_protegidos::a_bytes: primero IPv4, si no IPv6. None si no es una IP."""
    b4 = _pton(socket.AF_INET, ip)
    if b4 is not None:
        return False, b4 + bytes(12)
    b6 = _pton(socket.AF_INET6, ip)
    if b6 is not None:
        return True, b6
    return None


def parsear_rango(cidr):
    """(v6, red normalizada de 16 bytes, prefijo) como parsear_rango de rangos.hpp; None si no vale."""
    if not ip_cidr_valido(cidr):
        return None
    ip, _, pref = cidr.partition("/")
    ab = a_bytes(ip)
    if ab is None:
        return None
    v6, red = ab
    prefijo = int(pref) if pref else (128 if v6 else 32)
    r = bytearray(red)
    for i in range(16):
        ini = i * 8
        if ini >= prefijo:
            r[i] = 0
        elif ini + 8 > prefijo:
            r[i] &= (0xFF << (8 - (prefijo - ini))) & 0xFF
    return v6, bytes(r), prefijo


def validar_entradas(lista, donde, lim, es_comun, salida, total):
    """Porte de validar_entradas. Devuelve el total acumulado; lanza Rechazo. salida: lista a la que añadir o None."""
    if not isinstance(lista, list):
        raise Rechazo("formato", f"{donde} no es una lista")
    for i, e in enumerate(lista):
        w = f"{donde}[{i}]"
        err = claves_exactas(e, CAMPOS_ENTRADA)
        if err:
            raise Rechazo("formato", f"{w}: {err}")
        for k in CAMPOS_ENTRADA:
            if not isinstance(e[k], str):
                raise Rechazo("formato", f"{w}.{k} no es una cadena")
        total += 1
        if total > MAX_ENTRADAS:
            raise Rechazo("formato", f"más de {MAX_ENTRADAS} entradas")
        cat = e["categoria"]
        if cat not in CATEGORIAS:
            raise Rechazo("formato", f"{w}.categoria '{saneado(cat)}' desconocida")
        cidr = e["cidr"]
        r = parsear_rango(cidr) if "/" in cidr else None
        if r is None:
            raise Rechazo("formato", f"{w}.cidr '{saneado(cidr)}' mal formado (IPv4 o IPv6 con prefijo explícito)")
        v6, red, prefijo = r
        if a_bytes(cidr.split("/", 1)[0])[1] != red:
            raise Rechazo("formato", f"{w}.cidr '{saneado(cidr)}' tiene bits de host (escriba la red)")
        if (prefijo != 128) if v6 else (prefijo < lim[cat]):
            tope = "IPv6: solo /128" if v6 else f"/{lim[cat]}"
            raise Rechazo("limite", f"{w}: {saneado(cidr)} más amplio que el límite de {cat} ({tope})")
        if not es_interfaz(e["interfaz"]):
            raise Rechazo("formato", f"{w}.interfaz '{saneado(e['interfaz'])}' mal formada ([A-Za-z0-9._-], de 1 a 15)")
        if not es_mac(e["mac"]):
            raise Rechazo("formato", f"{w}.mac '{saneado(e['mac'])}' mal formada (vacía o xx:xx:xx:xx:xx:xx en minúsculas)")
        if not es_texto(e["motivo"], 200):
            raise Rechazo("formato", f"{w}.motivo vacío, de más de 200 bytes o con caracteres de control")
        if salida is not None:
            salida.append({"categoria": cat, "cidr": cidr, "interfaz": e["interfaz"], "mac": e["mac"],
                           "motivo": e["motivo"], "comun": es_comun, "red": (v6, red, prefijo)})
    return total


def repetidas(entradas):
    """Porte de repetidas(): la misma red dos veces en la misma interfaz, o en dos categorías."""
    for i in range(len(entradas)):
        for j in range(i + 1, len(entradas)):
            a, b = entradas[i], entradas[j]
            if a["red"] == b["red"]:
                if a["categoria"] != b["categoria"]:
                    return f"la red {a['cidr']} aparece en dos categorías"
                if a["interfaz"] == b["interfaz"]:
                    return f"la red {a['cidr']} aparece dos veces en {a['interfaz']}"
    return None


def abrir_sobre(sobre):
    """Pasos 1 y 2 (formato) de verificar(): devuelve (bytes de la carga, firma). No verifica la firma."""
    if len(sobre) > MAX_SOBRE:
        raise Rechazo("formato", f"sobre de {len(sobre)} bytes (máximo {MAX_SOBRE})")
    try:
        s = json_estricto(sobre)
    except ValueError as e:
        raise Rechazo("formato", f"sobre: {e}") from None
    err = claves_exactas(s, ("formato", "carga_b64", "firma"))
    if err:
        raise Rechazo("formato", f"sobre: {err}")
    if not isinstance(s["formato"], str) or s["formato"] != FORMATO:
        raise Rechazo("formato", f"sobre: formato distinto de {FORMATO}")
    if not isinstance(s["carga_b64"], str) or not isinstance(s["firma"], str):
        raise Rechazo("formato", "sobre: carga_b64 y firma tienen que ser cadenas")
    carga = b64_a_bytes(s["carga_b64"], MAX_CARGA)
    if carga is None:
        raise Rechazo("formato", f"sobre: carga_b64 no es base64 válido o pasa de {MAX_CARGA} bytes")
    firma = s["firma"]
    m = re.fullmatch(r"vault:v([^:]*):(.*)", firma, re.S)
    num_ok = m is not None and 0 < len(m.group(1)) <= 10 and m.group(1)[0] != "0" and m.group(1).isascii() \
        and m.group(1).isdigit()
    fb = b64_a_bytes(m.group(2), 64) if num_ok else None
    if fb is None or len(fb) != 64:
        raise Rechazo("formato", "firma mal formada (vault:vN:<base64 de 64 bytes>)")
    return carga, firma


def validar_carga(carga, hospital_id, planta, version_aplicada):
    """Pasos 3 y 4 de verificar() (tras la firma). planta None = documento entero (como verificar_documento)."""
    try:
        c = json_estricto(carga)
    except ValueError as e:
        raise Rechazo("formato", f"carga: {e}") from None
    err = claves_exactas(c, CAMPOS_CARGA)
    if err:
        raise Rechazo("formato", f"carga: {err}")
    if not es_entero(c["esquema"]) or c["esquema"] != 1:
        raise Rechazo("formato", "carga: esquema distinto de 1")
    if not es_id(c["hospital_id"]):
        raise Rechazo("formato", "carga: hospital_id mal formado ([a-z0-9-], de 1 a 64)")
    if not es_entero(c["version"]) or not 1 <= c["version"] <= MAX_U64:
        raise Rechazo("formato", "carga: version tiene que ser un entero >= 1")
    if not es_fecha_utc(c["emitido_utc"]):
        raise Rechazo("formato", "carga: emitido_utc mal formado (AAAA-MM-DDTHH:MM:SSZ)")
    if not es_texto(c["firmante"], 128):
        raise Rechazo("formato", "carga: firmante vacío, de más de 128 bytes o con caracteres de control")
    if not es_texto(c["motivo"], 200):
        raise Rechazo("formato", "carga: motivo vacío, de más de 200 bytes o con caracteres de control")
    ha = c["hash_anterior"]
    if not isinstance(ha, str) or not (ha == "" or es_hex_min(ha, 64)):
        raise Rechazo("formato", "carga: hash_anterior tiene que ser vacío o 64 hex en minúsculas")
    lim_j = c["limites"]
    err = claves_exactas(lim_j, CATEGORIAS)
    if err:
        raise Rechazo("formato", f"carga: limites: {err}")
    lim = {}
    for k in CATEGORIAS:
        v = lim_j[k]
        if not es_entero(v) or not -2 ** 31 <= v < 2 ** 31:
            raise Rechazo("formato", f"carga: limites.{k} no es un entero")
        if (v != 32) if k == "infraestructura" else not LIMITE_MIN <= v <= 32:
            raise Rechazo("limite", f"carga: limites.{k}={v}" +
                          (" (infraestructura: solo 32)" if k == "infraestructura" else " fuera de [8, 32]"))
        lim[k] = v
    plantas = c["plantas"]
    if not isinstance(plantas, dict):
        raise Rechazo("formato", "carga: plantas no es un objeto")
    total = validar_entradas(c["comun"], "comun", lim, True, None, 0)
    for p in sorted(plantas):
        if not es_id(p):
            raise Rechazo("formato", f"carga: planta '{saneado(p)}' mal formada ([a-z0-9-], de 1 a 64)")
        total = validar_entradas(plantas[p], f"plantas.{p}", lim, False, None, total)
    if c["hospital_id"] != hospital_id:
        raise Rechazo("hospital", f"manifiesto de '{c['hospital_id']}', este es '{saneado(hospital_id)}'")
    if c["version"] <= version_aplicada:
        raise Rechazo("version", f"version {c['version']} <= la aplicada {version_aplicada}")
    entradas = []
    if planta is not None:
        if planta not in plantas:
            raise Rechazo("planta", f"el manifiesto no trae la planta '{saneado(planta)}'")
        validar_entradas(c["comun"], "comun", lim, True, entradas, 0)
        validar_entradas(plantas[planta], f"plantas.{planta}", lim, False, entradas, 0)
        r = repetidas(entradas)
        if r:
            raise Rechazo("formato", f"carga: {r}")
    else:
        if not plantas:
            raise Rechazo("planta", "el manifiesto no trae ninguna planta")
        validar_entradas(c["comun"], "comun", lim, True, entradas, 0)
        for p in sorted(plantas):
            una = []
            validar_entradas(c["comun"], "comun", lim, True, una, 0)
            validar_entradas(plantas[p], f"plantas.{p}", lim, False, una, 0)
            r = repetidas(una)
            if r:
                raise Rechazo("formato", f"carga: planta {p}: {r}")
            validar_entradas(plantas[p], f"plantas.{p}", lim, False, entradas, 0)
    return {"carga": c, "bytes": bytes(carga), "sha256": hashlib.sha256(carga).hexdigest(), "version": c["version"],
            "limites": lim, "entradas": entradas}


def validar_sobre(sobre, hospital_id, planta=None, version_aplicada=0, verificar_firma=None):
    """El verificar() completo. verificar_firma(carga, firma) -> bool (Vault transit verify)."""
    carga, firma = abrir_sobre(sobre)
    if verificar_firma is not None and not verificar_firma(carga, firma):
        raise Rechazo("firma", "Vault transit verify: la firma no verifica con la clave del hospital")
    m = validar_carga(carga, hospital_id, planta, version_aplicada)
    m["firma"] = firma
    m["sobre"] = bytes(sobre)
    return m


def construir_sobre(carga, firma):
    return json.dumps({"formato": FORMATO, "carga_b64": base64.b64encode(carga).decode("ascii"), "firma": firma},
                      separators=(",", ":")).encode("ascii")


def construir_carga(cfg, version, firmante, motivo, hash_anterior, comun, plantas, ahora=None):
    """La carga se escribe una vez, en ASCII y compacta: lo que se firma son estos bytes exactos."""
    if ahora is None:
        ahora = datetime.datetime.now(datetime.timezone.utc)
    limpia = lambda lista: [{k: e[k] for k in CAMPOS_ENTRADA} for e in lista]  # noqa: E731
    carga = {
        "esquema": 1,
        "hospital_id": cfg["hospital_id"],
        "version": version,
        "emitido_utc": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "firmante": firmante,
        "motivo": motivo,
        "hash_anterior": hash_anterior,
        "limites": {k: cfg["limites"][k] for k in CATEGORIAS},
        "comun": limpia(comun),
        "plantas": {p: limpia(plantas.get(p, [])) for p in cfg["plantas"]},
    }
    return json.dumps(carga, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def politica(cfg, m):
    """Lo que argus-infra exige además (D2/D10): límites y plantas, los de la configuración. Devuelve (avisos, errores).
    Error: una planta del manifiesto que la configuración no tiene (construir encima la perdería sin decirlo).
    Aviso: límites distintos (la versión nueva lleva los de la configuración y se valida con ellos) y plantas de la
    configuración que el manifiesto no trae (su firewall no tiene manifiesto: candado cerrado, D6)."""
    avisos, errores = [], []
    if m["limites"] != cfg["limites"]:
        avisos.append(f"los límites del manifiesto {m['limites']} no son los de la configuración {cfg['limites']}")
    plantas = m["carga"]["plantas"]
    for p in sorted(plantas):
        if p not in cfg["plantas"]:
            errores.append(f"la planta '{p}' del manifiesto no está en la configuración")
    for p in cfg["plantas"]:
        if p not in plantas:
            avisos.append(f"la planta '{p}' de la configuración no está en el manifiesto (su firewall no lo aplicará)")
    return avisos, errores


# ─── configuración (G-A) ────────────────────────────────────────────────────────────────────────────────────────────

def _url_https(v):
    if not isinstance(v, str):
        return None
    u = urllib.parse.urlsplit(v)
    try:
        puerto = u.port
    except ValueError:
        return None
    if u.scheme != "https" or not u.hostname or puerto is None or u.path not in ("", "/") or u.query or \
            u.fragment or u.username or u.password:
        return None
    return u.hostname, puerto


def _ruta(v):
    return isinstance(v, str) and v.startswith("/") and "\x00" not in v and len(v) <= 4096


def leer_config(ruta):
    """Devuelve (cfg, lineas_de_log). Fallo(SALIDA_USO) si algo de la identidad falta o está mal."""
    try:
        with open(ruta, "rb") as f:
            datos = f.read(1024 * 1024 + 1)
    except OSError as e:
        raise Fallo(f"[ARGUS-INFRA-CONFIG] no se puede leer {ruta}: {e.strerror}", SALIDA_USO) from None
    if len(datos) > 1024 * 1024:
        raise Fallo(f"[ARGUS-INFRA-CONFIG] {ruta} pasa de 1 MiB", SALIDA_USO)
    try:
        j = json_estricto(datos)
    except ValueError as e:
        raise Fallo(f"[ARGUS-INFRA-CONFIG] {ruta}: {e}", SALIDA_USO) from None
    if not isinstance(j, dict):
        raise Fallo(f"[ARGUS-INFRA-CONFIG] {ruta}: no es un objeto", SALIDA_USO)
    log, errores = [], []

    def ok(campo, valor):
        log.append(f"[ARGUS-INFRA-CONFIG] {campo}={valor} (JSON)")

    def mal(campo, que):
        errores.append(f"[ARGUS-INFRA-CONFIG] {campo}: {que}; sin valor sano por defecto: no se firma nada")

    def obj(nombre, claves):
        o = j.get(nombre)
        if not isinstance(o, dict):
            mal(nombre, "ausente o no es un objeto" if o is None else "no es un objeto")
            return {}
        for k in o:
            if k not in claves and not k.startswith("_"):
                log.append(f"[CONFIG-AVISO] {nombre}.{saneado(k)}: campo desconocido (se ignora)")
        return o

    for k in j:
        if k not in ("hospital_id", "plantas", "limites", "vault", "etcd_server", "tls", "timeout_s") and \
                not k.startswith("_"):
            log.append(f"[CONFIG-AVISO] {saneado(k)}: campo desconocido (se ignora)")
    cfg = {}
    h = j.get("hospital_id")
    if es_id(h):
        cfg["hospital_id"] = h
        ok("hospital_id", h)
    else:
        mal("hospital_id", "ausente o mal formado ([a-z0-9-], de 1 a 64)")
    p = j.get("plantas")
    if isinstance(p, list) and 1 <= len(p) <= 64 and all(es_id(x) for x in p) and len(set(p)) == len(p):
        cfg["plantas"] = list(p)
        ok("plantas", ",".join(p))
    else:
        mal("plantas", "ausente o mal formado (lista de 1 a 64 identificadores [a-z0-9-] distintos: los despliegue_id)")
    lim = obj("limites", CATEGORIAS)
    cfg["limites"] = {}
    for k in CATEGORIAS:
        v = lim.get(k)
        if k == "infraestructura":
            bueno = es_entero(v) and v == 32
            formato = "entero, exactamente 32 (ADR-060 D2: solo hosts)"
        else:
            bueno = es_entero(v) and LIMITE_MIN <= v <= 32
            formato = f"entero en [{LIMITE_MIN}, 32]"
        if bueno:
            cfg["limites"][k] = v
            ok(f"limites.{k}", v)
        elif lim:
            mal(f"limites.{k}", f"ausente o fuera de rango ({formato})")
    va = obj("vault", ("url", "ca_file", "rol_login", "montaje", "clave"))
    es = obj("etcd_server", ("url", "ca_file"))
    tl = obj("tls", ("cert_file", "key_file"))
    for nombre, o, campos in (("vault", va, ("url", "ca_file", "rol_login", "montaje", "clave")),
                              ("etcd_server", es, ("url", "ca_file")), ("tls", tl, ("cert_file", "key_file"))):
        if not o:
            continue
        sub = {}
        for k in campos:
            v = o.get(k)
            campo = f"{nombre}.{k}"
            if k == "url":
                hp = _url_https(v)
                if hp:
                    sub[k] = v
                    sub["host"], sub["port"] = hp
                    ok(campo, v)
                else:
                    mal(campo, "ausente o mal formado (https://HOST:PUERTO, sin ruta)")
            elif k.endswith("_file"):
                if _ruta(v) and os.path.isfile(v) and os.access(v, os.R_OK):
                    sub[k] = v
                    ok(campo, v)
                else:
                    mal(campo, "ausente, no es una ruta absoluta o el fichero no se puede leer")
            elif k == "clave":
                esperada = f"protegidos-{cfg.get('hospital_id', '?')}"
                if v == esperada:
                    sub[k] = v
                    ok(campo, v)
                else:
                    mal(campo, f"ausente o distinto de '{esperada}' (la clave transit de ESTE hospital, ADR-060 D3)")
            else:
                if es_id(v):
                    sub[k] = v
                    ok(campo, v)
                else:
                    mal(campo, "ausente o mal formado ([a-z0-9-], de 1 a 64)")
        cfg[nombre] = sub
    t = j.get("timeout_s")
    if es_entero(t) and TIMEOUT_MIN <= t <= TIMEOUT_MAX:
        cfg["timeout_s"] = t
        ok("timeout_s", t)
    else:
        cfg["timeout_s"] = TIMEOUT_DEFECTO
        porque = "ausente" if t is None else f"'{saneado(str(t))}' mal formado"
        log.append(f"[CONFIG-DEFAULT] timeout_s={TIMEOUT_DEFECTO} (DEFECTO: {porque}; entero en "
                   f"[{TIMEOUT_MIN}, {TIMEOUT_MAX}] segundos)")
    if errores:
        raise Fallo("\n".join(log + errores), SALIDA_USO)
    return cfg, log


# ─── HTTPS con certificado de cliente ──────────────────────────────────────────────────────────────────────────────

class Https:
    def __init__(self, host, port, ca_file, cert_file, key_file, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.ctx = ssl.create_default_context(cafile=ca_file)
        self.ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        self.ctx.load_cert_chain(cert_file, key_file)

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None):
        c = http.client.HTTPSConnection(self.host, self.port, context=self.ctx, timeout=self.timeout)
        try:
            c.request(metodo, ruta, body=cuerpo, headers=cabeceras or {})
            r = c.getresponse()
            datos = r.read(MAX_SOBRE + 65536)
            return r.status, datos
        except (OSError, http.client.HTTPException, ssl.SSLError) as e:
            raise Fallo(f"[ARGUS-INFRA] {metodo} https://{self.host}:{self.port}{ruta}: {saneado(str(e), 200)}") \
                from None
        finally:
            c.close()


def _json_o_nada(datos):
    try:
        return json.loads(datos.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


class Vault:
    """Vault transit con el certificado de argus-infra (rol argus-infra-admin: firmar, verificar y leer la pública)."""

    def __init__(self, cfg):
        v = cfg["vault"]
        self.h = Https(v["host"], v["port"], v["ca_file"], cfg["tls"]["cert_file"], cfg["tls"]["key_file"],
                       cfg["timeout_s"])
        self.montaje, self.clave, self.rol = v["montaje"], v["clave"], v["rol_login"]
        self.token = None
        self.firmante = None

    def _error(self, que, status, datos):
        j = _json_o_nada(datos)
        errs = j.get("errors") if isinstance(j, dict) else None
        det = "; ".join(saneado(str(x), 160) for x in errs) if isinstance(errs, list) else saneado(datos[:160]
                                                                                              .decode("latin-1"))
        return Fallo(f"[ARGUS-INFRA-VAULT] {que}: HTTP {status} {det}")

    def _post(self, ruta, cuerpo, que):
        cab = {"Content-Type": "application/json"}
        if self.token:
            cab["X-Vault-Token"] = self.token
        st, datos = self.h.pedir("POST", ruta, json.dumps(cuerpo).encode("ascii"), cab)
        if st not in (200, 204):
            raise self._error(que, st, datos)
        return _json_o_nada(datos) if datos else {}

    def login(self):
        j = self._post("/v1/auth/cert/login", {"name": self.rol}, "login con el certificado de argus-infra")
        try:
            a = j["auth"]
            self.token = a["client_token"]
            meta = a.get("metadata") or {}
            cn, cert = str(meta.get("common_name", "?")), str(meta.get("cert_name", "?"))
            # [PROTEGIDOS-MANIFIESTO-D319] medido en el banco: el etcd-server y el firewall registran el firmante con
            # saneado(), que corta a 64 caracteres. "<cn> entidad=<entity_id>" (56 con argus-infra) cabe entero, y el
            # entity_id es el mismo que guarda el audit de Vault de cada firma.
            firmante = f"{cn if cert == cn else cert + '/' + cn} entidad={a.get('entity_id') or '?'}"
        except (KeyError, TypeError):
            raise Fallo("[ARGUS-INFRA-VAULT] login: respuesta sin auth.client_token") from None
        if not es_texto(firmante, 64) or not firmante.isascii():
            raise Fallo(f"[ARGUS-INFRA-VAULT] login: firmante '{saneado(firmante)}' no cabe en 64 caracteres ASCII "
                        "(los logs del etcd-server y del firewall lo cortarían)")
        self.firmante = firmante
        return firmante

    def firmar(self, carga):
        j = self._post(f"/v1/{self.montaje}/sign/{self.clave}", {"input": base64.b64encode(carga).decode("ascii")},
                       f"firma con {self.montaje}/sign/{self.clave}")
        try:
            return j["data"]["signature"]
        except (KeyError, TypeError):
            raise Fallo("[ARGUS-INFRA-VAULT] firma: respuesta sin data.signature") from None

    def verificar(self, carga, firma):
        j = self._post(f"/v1/{self.montaje}/verify/{self.clave}",
                       {"input": base64.b64encode(carga).decode("ascii"), "signature": firma},
                       f"verificación con {self.montaje}/verify/{self.clave}")
        try:
            return j["data"]["valid"] is True
        except (KeyError, TypeError):
            raise Fallo("[ARGUS-INFRA-VAULT] verificación: respuesta sin data.valid") from None

    def huellas(self):
        """{versión: huella de 16 hex} de la clave transit (la misma huella que [PROTEGIDOS-CLAVE] del firewall)."""
        st, datos = self.h.pedir("GET", f"/v1/{self.montaje}/keys/{self.clave}", None, {"X-Vault-Token": self.token})
        if st != 200:
            raise self._error(f"lectura de {self.montaje}/keys/{self.clave}", st, datos)
        j = _json_o_nada(datos)
        try:
            ks = j["data"]["keys"]
            return {int(v): hashlib.sha256(base64.b64decode(k["public_key"])).hexdigest()[:16]
                    for v, k in ks.items()}
        except (KeyError, TypeError, ValueError, binascii.Error):
            raise Fallo("[ARGUS-INFRA-VAULT] respuesta de la clave sin data.keys") from None

    def revocar(self):
        if not self.token:
            return
        try:
            self._post("/v1/auth/token/revoke-self", {}, "revocar el token")
        except Fallo as e:
            aviso(f"[ARGUS-INFRA-VAULT] AVISO: no se pudo revocar el token (caduca solo en 300 s): {e}")
        finally:
            self.token = None


class EtcdServer:
    def __init__(self, cfg):
        e = cfg["etcd_server"]
        self.h = Https(e["host"], e["port"], e["ca_file"], cfg["tls"]["cert_file"], cfg["tls"]["key_file"],
                       cfg["timeout_s"])
        self.url = e["url"]

    def _motivo(self, datos):
        j = _json_o_nada(datos)
        if isinstance(j, dict):
            return f"motivo={saneado(str(j.get('motivo', '?')))} {saneado(str(j.get('message', '')), 300)}"
        return saneado(datos[:200].decode("latin-1"), 200)

    def _get(self, ruta):
        st, datos = self.h.pedir("GET", ruta)
        if st == 200:
            return datos
        if st == 404:
            return None
        raise Fallo(f"[ARGUS-INFRA-ETCD] GET {ruta}: HTTP {st} {self._motivo(datos)}")

    def vigente(self):
        return self._get("/v1/protegidos")

    def version(self, n):
        return self._get(f"/v1/protegidos/v/{n}")

    def publicar(self, sobre):
        st, datos = self.h.pedir("PUT", "/v1/protegidos", sobre, {"Content-Type": "application/json"})
        if st != 201:
            raise Fallo(f"[ARGUS-INFRA-RECHAZADO] el etcd-server rechazó el PUT: HTTP {st} {self._motivo(datos)}",
                        SALIDA_RECHAZO)
        return _json_o_nada(datos) or {}


# ─── presentación ──────────────────────────────────────────────────────────────────────────────────────────────────

def secciones(carga):
    """[(nombre de sección, lista de entradas)] en orden: comun y cada planta."""
    s = [("comun", carga["comun"])]
    s += [(f"plantas.{p}", carga["plantas"][p]) for p in sorted(carga["plantas"])]
    return s


def _clave(sec, e):
    return (sec, e["categoria"], e["cidr"], e["interfaz"])


def _texto_entrada(e):
    return f"{e['categoria']} {e['cidr']} {e['interfaz']} mac={e['mac'] or '-'} motivo=\"{saneado(e['motivo'], 200)}\""


def diferencias(anterior, nueva):
    """(lineas legibles, altas, bajas) entre dos cargas (anterior None = vacía)."""
    a = {}
    if anterior is not None:
        for sec, es in secciones(anterior):
            for e in es:
                a[_clave(sec, e)] = e
    n = {}
    for sec, es in secciones(nueva):
        for e in es:
            n[_clave(sec, e)] = e
    lineas, altas, bajas = [], [], []
    for k in sorted(set(a) | set(n)):
        sec = k[0]
        if k not in a:
            lineas.append(f"  + {sec}: {_texto_entrada(n[k])}")
            altas.append(f"{sec}:{k[1]} {k[2]} {k[3]}")
        elif k not in n:
            lineas.append(f"  - {sec}: {_texto_entrada(a[k])}")
            bajas.append(f"{sec}:{k[1]} {k[2]} {k[3]}")
        elif (a[k]["mac"], a[k]["motivo"]) != (n[k]["mac"], n[k]["motivo"]):
            lineas.append(f"  ~ {sec}: {_texto_entrada(a[k])}  ->  mac={n[k]['mac'] or '-'} "
                          f"motivo=\"{saneado(n[k]['motivo'], 200)}\"")
    if not lineas:
        lineas.append("  (sin cambios en las entradas)")
    return lineas, altas, bajas


def cabecera(m):
    c = m["carga"]
    por = {k: 0 for k in CATEGORIAS}
    for _, es in secciones(c):
        for e in es:
            por[e["categoria"]] += 1
    return (f"version={c['version']} hospital={c['hospital_id']} emitido={c['emitido_utc']} "
            f"firmante=\"{saneado(c['firmante'], 128)}\" motivo=\"{saneado(c['motivo'], 200)}\" "
            f"sha256={m['sha256'][:16]} anterior={c['hash_anterior'][:16] or '-'} firma={m['firma'].split(':')[1]} "
            f"entradas=" + " ".join(f"{k}={v}" for k, v in por.items()))


# ─── órdenes ───────────────────────────────────────────────────────────────────────────────────────────────────────

class Sesion:
    def __init__(self, cfg):
        self.cfg = cfg
        self.vault = Vault(cfg)
        self.etcd = EtcdServer(cfg)

    def leer(self, sobre, que, version_aplicada=0, esperada=None):
        """Valida un sobre del etcd-server (reglas de libs/protegidos + Vault verify + política de la configuración)."""
        try:
            m = validar_sobre(sobre, self.cfg["hospital_id"], None, version_aplicada, self.vault.verificar)
        except Rechazo as r:
            raise Fallo(f"[ARGUS-INFRA-NO-VERIFICA] {que}: {r}") from None
        if esperada is not None and m["version"] != esperada:
            raise Fallo(f"[ARGUS-INFRA-NO-VERIFICA] {que}: trae la versión {m['version']}, se pidió la {esperada}")
        return m

    def vigente(self):
        s = self.etcd.vigente()
        return None if s is None else self.leer(s, "la versión vigente")

    def version(self, n):
        s = self.etcd.version(n)
        if s is None:
            raise Fallo(f"[ARGUS-INFRA] la versión {n} no está en el histórico del etcd-server")
        return self.leer(s, f"la versión {n}", esperada=n)


def confirmar(n, si):
    if si:
        registrar(f"[ARGUS-INFRA] --si: se firma la versión {n} sin preguntar")
        return
    if not sys.stdin.isatty():
        raise Fallo("[ARGUS-INFRA] sin terminal para confirmar: lance la orden en una terminal o con --si", SALIDA_USO)
    try:
        r = input(f"Para firmar y publicar la versión {n} escriba {n}: ").strip()
    except EOFError:
        r = ""
    if r != str(n):
        raise Fallo("[ARGUS-INFRA] cancelado: no se ha firmado nada")


def cambiar(ses, anterior, comun, plantas, motivo, si, que):
    """Pasos 3 a 8 de G-E: construir N+1, validar, diff, confirmar, firmar, verificar, PUT, GET final."""
    cfg = ses.cfg
    if not es_texto(motivo, 200):
        raise Fallo("[ARGUS-INFRA] --motivo vacío, de más de 200 bytes o con caracteres de control", SALIDA_USO)
    v_ant = anterior["version"] if anterior else 0
    if v_ant >= MAX_U64:
        raise Fallo("[ARGUS-INFRA] la versión vigente es la máxima de 64 bits")
    n = v_ant + 1
    carga = construir_carga(cfg, n, ses.vault.firmante, motivo, anterior["sha256"] if anterior else "", comun, plantas)
    try:
        nueva = validar_carga(carga, cfg["hospital_id"], None, v_ant)
    except Rechazo as r:
        raise Fallo(f"[ARGUS-INFRA-INVALIDO] la versión {n} no se firma: {r}") from None
    lineas, altas, bajas = diferencias(anterior["carga"] if anterior else None, nueva["carga"])
    registrar(f"[ARGUS-INFRA] {que}: versión {v_ant or '-'} -> {n} motivo=\"{saneado(motivo, 200)}\" "
              f"firmante=\"{ses.vault.firmante}\"")
    for ln in lineas:
        registrar(ln)
    if anterior is not None and secciones(anterior["carga"]) == secciones(nueva["carga"]):
        raise Fallo("[ARGUS-INFRA] la versión nueva tendría las mismas entradas que la vigente: no se firma nada")
    confirmar(n, si)
    firma = ses.vault.firmar(carga)
    sobre = construir_sobre(carga, firma)
    m = ses.leer(sobre, f"la versión {n} recién firmada", v_ant)  # formato, Vault verify y reglas otra vez
    if m["sha256"] != nueva["sha256"]:
        raise Fallo("[ARGUS-INFRA] la carga firmada no es la construida (no se publica)")
    r = ses.etcd.publicar(sobre)
    if r.get("version") != n or r.get("sha256") != nueva["sha256"]:
        raise Fallo(f"[ARGUS-INFRA] el etcd-server respondió 201 con otra versión o sha256: {saneado(str(r), 200)}")
    final = ses.etcd.vigente()
    if final != sobre:
        raise Fallo("[ARGUS-INFRA] tras el PUT, la versión vigente del etcd-server NO es la publicada (compruebe "
                    "con 'argus-infra verificar')")
    registrar(f"[ARGUS-INFRA-PUBLICADO] version={n} anterior={v_ant} hospital={cfg['hospital_id']} "
              f"firmante=\"{ses.vault.firmante}\" firma={firma.split(':')[1]} sha256={nueva['sha256'][:16]} "
              f"altas=[{', '.join(altas)}] bajas=[{', '.join(bajas)}] motivo=\"{saneado(motivo, 200)}\"",
              a_syslog=True, prioridad=syslog.LOG_NOTICE)
    return SALIDA_OK


def leer_plantilla(ruta, cfg):
    """G-B: {_doc?, hospital_id, motivo, comun, plantas}. El hospital y las plantas, los de la configuración."""
    try:
        with open(ruta, "rb") as f:
            datos = f.read(MAX_CARGA + 1)
    except OSError as e:
        raise Fallo(f"[ARGUS-INFRA] no se puede leer la plantilla {ruta}: {e.strerror}", SALIDA_USO) from None
    if len(datos) > MAX_CARGA:
        raise Fallo(f"[ARGUS-INFRA] la plantilla {ruta} pasa de {MAX_CARGA} bytes", SALIDA_USO)
    try:
        j = json_estricto(datos)
    except ValueError as e:
        raise Fallo(f"[ARGUS-INFRA] plantilla {ruta}: {e}", SALIDA_USO) from None
    sin_doc = {k: v for k, v in j.items() if k != "_doc"} if isinstance(j, dict) else j
    err = claves_exactas(sin_doc, ("hospital_id", "motivo", "comun", "plantas"))
    if err:
        raise Fallo(f"[ARGUS-INFRA] plantilla {ruta}: {err}", SALIDA_USO)
    if sin_doc["hospital_id"] != cfg["hospital_id"]:
        raise Fallo(f"[ARGUS-INFRA] la plantilla es de '{saneado(str(sin_doc['hospital_id']))}' y este argus-infra de "
                    f"'{cfg['hospital_id']}'", SALIDA_USO)
    pl = sin_doc["plantas"]
    if not isinstance(pl, dict) or sorted(pl) != sorted(cfg["plantas"]):
        raise Fallo(f"[ARGUS-INFRA] las plantas de la plantilla ({', '.join(sorted(pl)) if isinstance(pl, dict) else '?'})"
                    f" no son las de la configuración ({', '.join(cfg['plantas'])})", SALIDA_USO)
    if not isinstance(sin_doc["comun"], list) or not all(isinstance(x, list) for x in pl.values()):
        raise Fallo(f"[ARGUS-INFRA] plantilla {ruta}: comun y cada planta tienen que ser listas", SALIDA_USO)
    for lista in [sin_doc["comun"]] + list(pl.values()):
        for e in lista:
            err = claves_exactas(e, CAMPOS_ENTRADA)
            if err:
                raise Fallo(f"[ARGUS-INFRA] plantilla {ruta}: entrada {saneado(str(e), 120)}: {err}", SALIDA_USO)
    return sin_doc


def orden_init(ses, a):
    p = leer_plantilla(a.desde, ses.cfg)
    if ses.etcd.vigente() is not None:
        raise Fallo("[ARGUS-INFRA] ya hay un manifiesto publicado: init solo firma la versión 1 (use add, del o "
                    "deshacer)")
    return cambiar(ses, None, p["comun"], p["plantas"], p["motivo"], a.si, f"init desde {a.desde}")


def _destino(a, cfg):
    if a.comun:
        return "comun"
    if a.planta not in cfg["plantas"]:
        raise Fallo(f"[ARGUS-INFRA] la planta '{saneado(a.planta)}' no está en la configuración "
                    f"({', '.join(cfg['plantas'])})", SALIDA_USO)
    return a.planta


def _copias(m, cfg):
    c = m["carga"]
    comun = [dict(e) for e in c["comun"]]
    plantas = {p: [dict(e) for e in c["plantas"].get(p, [])] for p in cfg["plantas"]}
    return comun, plantas


def _vigente_obligatorio(ses):
    m = ses.vigente()
    if m is None:
        raise Fallo("[ARGUS-INFRA] no hay manifiesto publicado: empiece con 'argus-infra init --desde PLANTILLA'")
    avisos, errores = politica(ses.cfg, m)
    for x in avisos:
        aviso(f"[ARGUS-INFRA] AVISO: {x}")
    if errores:
        raise Fallo("[ARGUS-INFRA] no se construye encima de la versión vigente: " + "; ".join(errores))
    return m


def orden_add(ses, a):
    m = _vigente_obligatorio(ses)
    dest = _destino(a, ses.cfg)
    if a.cidr != canonico(a.cidr):
        raise Fallo(f"[ARGUS-INFRA] escriba el CIDR en forma canónica: {canonico(a.cidr)}", SALIDA_USO)
    comun, plantas = _copias(m, ses.cfg)
    lista = comun if dest == "comun" else plantas[dest]
    if any(e["cidr"] == a.cidr and e["interfaz"] == a.interfaz for e in lista):
        raise Fallo(f"[ARGUS-INFRA] {a.cidr} por {a.interfaz} ya está en {dest}", SALIDA_USO)
    lista.append({"categoria": a.categoria, "cidr": a.cidr, "interfaz": a.interfaz, "mac": a.mac,
                  "motivo": a.motivo_entrada})
    return cambiar(ses, m, comun, plantas, a.motivo, a.si, f"add en {dest}")


def orden_del(ses, a):
    m = _vigente_obligatorio(ses)
    dest = _destino(a, ses.cfg)
    comun, plantas = _copias(m, ses.cfg)
    lista = comun if dest == "comun" else plantas[dest]
    quedan = [e for e in lista if not (e["cidr"] == a.cidr and e["interfaz"] == a.interfaz)]
    if len(quedan) == len(lista):
        raise Fallo(f"[ARGUS-INFRA] {a.cidr} por {a.interfaz} no está en {dest}", SALIDA_USO)
    for e in lista:
        if e not in quedan and e["categoria"] == "infraestructura":
            aviso(f"[ARGUS-INFRA] AVISO: se quita una entrada de infraestructura ({e['cidr']}): si ese host es del plano "
                  "de control, vuelve el DoS autoinfligido (ADR-060 D4)")
    lista[:] = quedan
    return cambiar(ses, m, comun, plantas, a.motivo, a.si, f"del en {dest}")


def orden_deshacer(ses, a):
    m = _vigente_obligatorio(ses)
    if a.n >= m["version"]:
        raise Fallo(f"[ARGUS-INFRA] deshacer {a.n}: tiene que ser una versión anterior a la vigente ({m['version']})",
                    SALIDA_USO)
    viejo = ses.version(a.n)
    avisos, errores = politica(ses.cfg, viejo)
    for x in avisos:
        aviso(f"[ARGUS-INFRA] AVISO: versión {a.n}: {x} (se firma con los límites de la configuración)")
    if errores:
        raise Fallo(f"[ARGUS-INFRA] deshacer {a.n}: " + "; ".join(errores))
    comun, plantas = _copias(viejo, ses.cfg)
    return cambiar(ses, m, comun, plantas, a.motivo, a.si, f"deshacer: contenido de la versión {a.n}")


def orden_list(ses, a):
    m = ses.version(a.version) if a.version else ses.vigente()
    if m is None:
        registrar("[ARGUS-INFRA] no hay manifiesto publicado (404)")
        return SALIDA_OK
    avisos, errores = politica(ses.cfg, m)
    for x in avisos + errores:
        aviso(f"[ARGUS-INFRA] AVISO: {x}")
    registrar(f"[ARGUS-INFRA] {cabecera(m)}")
    for sec, es in secciones(m["carga"]):
        registrar(f"  {sec}: {len(es)} entradas")
        for e in es:
            registrar(f"    {_texto_entrada(e)}")
    return SALIDA_OK


def orden_diff(ses, a):
    vig = ses.vigente()
    if vig is None:
        raise Fallo("[ARGUS-INFRA] no hay manifiesto publicado")
    if a.b is not None:
        va, vb = a.a, a.b
    elif a.a is not None:
        va, vb = a.a, vig["version"]
    else:
        va, vb = vig["version"] - 1, vig["version"]
    ma = None if va == 0 else (vig if va == vig["version"] else ses.version(va))
    mb = vig if vb == vig["version"] else ses.version(vb)
    registrar(f"[ARGUS-INFRA] diff versión {va or '-'} -> {vb}")
    lineas, _, _ = diferencias(ma["carga"] if ma else None, mb["carga"])
    for ln in lineas:
        registrar(ln)
    return SALIDA_OK


def orden_verificar(ses, a):
    m = ses.version(a.version) if a.version else ses.vigente()
    if m is None:
        registrar("[ARGUS-INFRA] no hay manifiesto publicado (404)")
        return SALIDA_ERROR
    avisos, errores = politica(ses.cfg, m)
    problemas = avisos + errores   # verificar es estricto: todo lo que no cuadra con la configuración es un problema
    huellas = ses.vault.huellas()
    ver_firma = int(m["firma"].split(":")[1][1:])
    registrar(f"[ARGUS-INFRA] firma con la clave transit {ses.cfg['vault']['clave']} versión {ver_firma} "
              f"huella={huellas.get(ver_firma, '?')} (compárela con [PROTEGIDOS-CLAVE] del firewall y del etcd-server)")
    v = m["version"]
    ha = m["carga"]["hash_anterior"]
    if v > 1:
        s = ses.etcd.version(v - 1)
        if s is None:
            problemas.append(f"la versión {v - 1} no está en el histórico: no se puede comprobar hash_anterior")
        else:
            ant = ses.leer(s, f"la versión {v - 1}", esperada=v - 1)
            if ant["sha256"] != ha:
                problemas.append(f"hash_anterior ({ha[:16]}) no es el sha256 de la versión {v - 1} "
                                 f"({ant['sha256'][:16]})")
    elif ha != "":
        problemas.append("la versión 1 trae hash_anterior")
    registrar(f"[ARGUS-INFRA] {cabecera(m)}")
    if problemas:
        for x in problemas:
            registrar(f"[ARGUS-INFRA-VERIFICAR] PROBLEMA: {x}")
        return SALIDA_ERROR
    registrar(f"[ARGUS-INFRA-VERIFICAR] OK versión {v}: firma (Vault transit verify), formato, límites, hospital, "
              "plantas y cadena hash_anterior")
    return SALIDA_OK


def canonico(cidr):
    """La forma canónica de un CIDR (sin ceros sobrantes ni mayúsculas): la que escribe add."""
    import ipaddress
    try:
        return str(ipaddress.ip_network(cidr, strict=False))
    except ValueError:
        return cidr


def _entero_pos(s):
    if not re.fullmatch(r"[1-9][0-9]{0,19}", s) or int(s) > MAX_U64:
        raise argparse.ArgumentTypeError(f"'{s}' no es una versión (entero >= 1)")
    return int(s)


def _diff_ver(s):
    if s == "0":
        return 0
    return _entero_pos(s)


def analizar(argv):
    ap = argparse.ArgumentParser(prog="argus-infra", description="Firma y publica el manifiesto de protegidos "
                                 "(ADR-060). Ver la cabecera del fichero.")
    ap.add_argument("-c", "--config", default=CONFIG_DEFECTO, help=f"configuración (defecto {CONFIG_DEFECTO})")
    ap.add_argument("--check-config", action="store_true", help="valida la configuración y sale")
    sub = ap.add_subparsers(dest="orden")
    p = sub.add_parser("init", help="firma la versión 1 desde una plantilla (solo si no hay ninguna)")
    p.add_argument("--desde", required=True, metavar="PLANTILLA")
    p.add_argument("--si", action="store_true", help="sin confirmación (bootstrap)")
    p = sub.add_parser("list", help="muestra la versión vigente (o la N)")
    p.add_argument("--version", type=_entero_pos)
    for nombre in ("add", "del"):
        p = sub.add_parser(nombre, help=("añade" if nombre == "add" else "quita") + " una entrada")
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--planta")
        g.add_argument("--comun", action="store_true")
        if nombre == "add":
            p.add_argument("--categoria", required=True, choices=CATEGORIAS)
        p.add_argument("--cidr", required=True)
        p.add_argument("--interfaz", required=True)
        if nombre == "add":
            p.add_argument("--mac", default="")
            p.add_argument("--motivo-entrada", required=True, help="motivo corto de ESTA entrada (va al manifiesto)")
        p.add_argument("--motivo", required=True, help="motivo del cambio (va al manifiesto y al log)")
        p.add_argument("--si", action="store_true")
    p = sub.add_parser("diff", help="diferencias: sin argumentos, vigente-1 -> vigente; A -> vigente; A -> B")
    p.add_argument("a", nargs="?", type=_diff_ver)
    p.add_argument("b", nargs="?", type=_entero_pos)
    p = sub.add_parser("verificar", help="verifica la versión vigente (o la N) y su cadena hash_anterior")
    p.add_argument("--version", type=_entero_pos)
    p = sub.add_parser("deshacer", help="firma como versión nueva el contenido de la versión N (D4)")
    p.add_argument("n", type=_entero_pos)
    p.add_argument("--motivo", required=True)
    p.add_argument("--si", action="store_true")
    a = ap.parse_args(argv)
    if not a.check_config and not a.orden:
        ap.error("falta la orden (o --check-config)")
    return a


ORDENES = {"init": orden_init, "list": orden_list, "add": orden_add, "del": orden_del, "diff": orden_diff,
           "verificar": orden_verificar, "deshacer": orden_deshacer}


def main(argv=None):
    a = analizar(sys.argv[1:] if argv is None else argv)
    if os.geteuid() != 0:
        aviso("[ARGUS-INFRA] se ejecuta como root (la clave TLS de argus-infra es de root, 0600)")
        return SALIDA_USO
    try:
        cfg, log = leer_config(a.config)
    except Fallo as e:
        aviso(str(e))
        registrar(f"[ARGUS-INFRA-CONFIG] configuración {a.config} inválida: no se firma nada", a_syslog=True,
                  prioridad=syslog.LOG_ERR)
        return e.codigo
    for ln in log:
        aviso(ln)
    if a.check_config:
        registrar(f"[ARGUS-INFRA-CONFIG] {a.config}: OK")
        return SALIDA_OK
    ses = Sesion(cfg)
    try:
        ses.vault.login()
        return ORDENES[a.orden](ses, a)
    except Fallo as e:
        registrar(str(e), a_syslog=a.orden in ("init", "add", "del", "deshacer"), prioridad=syslog.LOG_ERR)
        return e.codigo
    finally:
        ses.vault.revocar()


if __name__ == "__main__":
    sys.exit(main())
