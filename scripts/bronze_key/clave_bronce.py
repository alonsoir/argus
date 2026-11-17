#!/usr/bin/python3 -I
# clave_bronce.py — [CLAVE-BRONCE-D326] DAY326, F2d de DEBT-FALCO-RUIDO-ADMIN-001 (PR2b de DEBT-ETCD-HA-TLS-RAFT-001).
# Se ejecuta EN EL DEFENDER con sudo (la clave TLS del conversor es 0600 root). Imprime en stdout la clave HMAC ACTIVA
# (64 hex) de un componente, la que mitre/ctu/custom-start pasan al bronze-to-gold-converter y la que comparan las
# huellas de d317_reinicio_defender.sh. La pide por mTLS con la identidad del conversor (OU=CN=bronze-to-gold-converter;
# la regla de /secrets/valid/{c} del etcd-server le deja leerla) a la primera dirección del bloque etcd del JSON del
# ml-detector: así el conversor y el ml-detector hablan con el mismo etcd-server y no pueden quedar con claves distintas.
# Sustituye a clave_bronce_ml_detector.sh y al curl de d317_reinicio_defender.sh (decisión de Alonso DAY326: sin curl;
# Falco conoce a esta orden, no a un curl). Python estándar, sin dependencias.
#   sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py [--json RUTA] [--pki DIR] COMPONENTE
# Del JSON (el JSON es la ley): etcd.endpoints[0] (https://host:puerto, sin defecto), etcd.ca_file (ruta absoluta, sin
# defecto) y etcd.connection_timeout_ms ([100, 60000], defecto 5000 con aviso: los mismos que etcd_client). Cada valor
# efectivo, y de dónde sale, a stderr; por stdout solo la clave.
# Salida: 0 bien; 1 error (red, TLS, HTTP, respuesta); 2 uso o configuración. Errores a stderr.
import argparse
import http.client
import json
import re
import ssl
import sys
import urllib.parse

TAG = "[CLAVE-BRONCE]"
JSON_DEFECTO = "/etc/ml-defender/ml-detector/ml_detector_config.json"
PKI_DEFECTO = "/etc/argus-pki"
ID = "bronze-to-gold-converter"
# Los de etcd_client::leer_bloque_etcd() (el _doc del bloque etcd de ml_detector_config.json)
TIMEOUT_DEFECTO_MS, TIMEOUT_MIN_MS, TIMEOUT_MAX_MS = 5000, 100, 60000
MAX_RESPUESTA = 1 << 20
SALIDA_OK, SALIDA_ERROR, SALIDA_USO = 0, 1, 2


class Fallo(Exception):
    def __init__(self, mensaje, codigo=SALIDA_ERROR):
        super().__init__(mensaje)
        self.codigo = codigo


def leer_bloque(ruta):
    """(host, puerto, ca_file, timeout_ms, líneas de log) del bloque etcd de un JSON de componente."""
    try:
        with open(ruta, encoding="utf-8") as f:
            j = json.load(f)
    except (OSError, ValueError) as e:
        raise Fallo(f"{TAG} no se puede leer {ruta}: {e}", SALIDA_USO) from None
    e = j.get("etcd") if isinstance(j, dict) else None
    if not isinstance(e, dict):
        raise Fallo(f"{TAG} {ruta} sin bloque etcd", SALIDA_USO)
    eps = e.get("endpoints")
    ep = eps[0] if isinstance(eps, list) and eps else None
    if not isinstance(ep, str):
        raise Fallo(f"{TAG} {ruta}: etcd.endpoints[0] ausente o mal formado (https://host:puerto)", SALIDA_USO)
    u = urllib.parse.urlsplit(ep)
    try:
        puerto = u.port
    except ValueError:
        puerto = None
    if u.scheme != "https" or not u.hostname or puerto is None or u.path not in ("", "/") or u.query or u.fragment:
        raise Fallo(f"{TAG} {ruta}: etcd.endpoints[0]='{ep[:80]}' no es https://host:puerto", SALIDA_USO)
    ca = e.get("ca_file")
    if not isinstance(ca, str) or not ca.startswith("/"):
        raise Fallo(f"{TAG} {ruta}: etcd.ca_file ausente o mal formado (ruta absoluta)", SALIDA_USO)
    log = [f"[CONFIG] etcd.endpoints[0]={ep} (JSON)", f"[CONFIG] etcd.ca_file={ca} (JSON)"]
    t = e.get("connection_timeout_ms")
    if type(t) is int and TIMEOUT_MIN_MS <= t <= TIMEOUT_MAX_MS:
        log.append(f"[CONFIG] etcd.connection_timeout_ms={t} (JSON)")
    else:
        porque = "ausente" if t is None else "mal formado"
        log.append(f"[CONFIG-DEFAULT] etcd.connection_timeout_ms={TIMEOUT_DEFECTO_MS} (DEFECTO: {porque}; entero en "
                   f"[{TIMEOUT_MIN_MS}, {TIMEOUT_MAX_MS}] ms)")
        t = TIMEOUT_DEFECTO_MS
    return u.hostname, puerto, ca, t, log


def clave_activa(datos):
    """La única clave activa (64 hex en minúsculas) de una respuesta de /secrets/valid/{c}."""
    try:
        d = json.loads(datos.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise Fallo(f"{TAG} la respuesta no es JSON") from None
    ks = d.get("keys") if isinstance(d, dict) else None
    if not isinstance(ks, list):
        raise Fallo(f"{TAG} la respuesta no trae la lista keys")
    activas = [k.get("key") for k in ks if isinstance(k, dict) and k.get("is_active") is True]
    if len(activas) != 1:
        raise Fallo(f"{TAG} se esperaba 1 clave activa y hay {len(activas)}")
    if not isinstance(activas[0], str) or re.fullmatch(r"[0-9a-f]{64}", activas[0]) is None:
        raise Fallo(f"{TAG} la clave activa no son 64 hex")
    return activas[0]


def pedir(host, puerto, ca, cert, key, timeout_s, ruta):
    """GET por HTTPS con certificado de cliente: (status, cuerpo)."""
    c = None
    try:
        ctx = ssl.create_default_context(cafile=ca)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert, key)
        c = http.client.HTTPSConnection(host, puerto, context=ctx, timeout=timeout_s)
        c.request("GET", ruta)
        r = c.getresponse()
        return r.status, r.read(MAX_RESPUESTA + 1)
    except (OSError, http.client.HTTPException, ssl.SSLError) as e:
        raise Fallo(f"{TAG} GET https://{host}:{puerto}{ruta}: {str(e)[:200]} (¿etcd-server de control-1 arrancado?)") \
            from None
    finally:
        if c is not None:
            c.close()


def main(argv=None, pedir=pedir):
    ap = argparse.ArgumentParser(prog="clave_bronce.py", description="Clave HMAC activa de un componente (ver cabecera)")
    ap.add_argument("--json", default=JSON_DEFECTO, help=f"JSON con el bloque etcd (defecto {JSON_DEFECTO})")
    ap.add_argument("--pki", default=PKI_DEFECTO, help=f"directorio del certificado del conversor (defecto {PKI_DEFECTO})")
    ap.add_argument("componente")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if re.fullmatch(r"[a-z0-9-]{1,64}", a.componente) is None:
            raise Fallo(f"{TAG} componente '{a.componente[:64]}' mal formado ([a-z0-9-], de 1 a 64)", SALIDA_USO)
        host, puerto, ca, t, log = leer_bloque(a.json)
        for ln in log:
            print(f"{TAG} {ln}", file=sys.stderr)
        ruta = f"/secrets/valid/{a.componente}"
        st, datos = pedir(host, puerto, ca, f"{a.pki}/{ID}.crt", f"{a.pki}/{ID}.key", t / 1000, ruta)
        if st != 200:
            raise Fallo(f"{TAG} GET https://{host}:{puerto}{ruta}: HTTP {st}")
        if len(datos) > MAX_RESPUESTA:
            raise Fallo(f"{TAG} respuesta de más de {MAX_RESPUESTA} bytes")
        print(clave_activa(datos))
        return SALIDA_OK
    except Fallo as e:
        print(str(e), file=sys.stderr)
        return e.codigo


if __name__ == "__main__":
    sys.exit(main())
