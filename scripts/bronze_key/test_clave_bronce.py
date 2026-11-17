#!/usr/bin/python3 -I
# test_clave_bronce.py — [CLAVE-BRONCE-D326] tests de clave_bronce.py con la biblioteca estándar (unittest), sin red: la
# lectura del bloque etcd (el JSON es la ley), la respuesta de /secrets/valid/{c} y la orden entera con la petición
# HTTPS simulada. La petición real la prueban mitre-start y lab-e2e-reinicio-etcd.
#   python3 -I scripts/bronze_key/test_clave_bronce.py      (make test-clave-bronce, en el defender)
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True  # se ejecuta desde /vagrant: sin __pycache__ en el repo
AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("clave_bronce", os.path.join(AQUI, "clave_bronce.py"))
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

K1 = "a" * 64
K2 = "0123456789abcdef" * 4


def bloque(**kw):
    e = {"endpoints": ["https://192.168.100.20:2379"], "ca_file": "/etc/argus-pki/ca.crt",
         "connection_timeout_ms": 5000}
    e.update(kw)
    return e


def json_tmp(obj):
    d = tempfile.mkdtemp()
    r = os.path.join(d, "c.json")
    with open(r, "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj))
    return r


def resp(*claves):
    return json.dumps({"keys": [{"key": k, "is_active": a} for k, a in claves]}).encode()


class Bloque(unittest.TestCase):
    def test_lee_lo_del_json_y_lo_dice(self):
        h, p, ca, t, log = cb.leer_bloque(json_tmp({"etcd": bloque(connection_timeout_ms=2500)}))
        self.assertEqual((h, p, ca, t), ("192.168.100.20", 2379, "/etc/argus-pki/ca.crt", 2500))
        self.assertIn("[CONFIG] etcd.connection_timeout_ms=2500 (JSON)", log)
        self.assertIn("[CONFIG] etcd.endpoints[0]=https://192.168.100.20:2379 (JSON)", log)

    def test_timeout_ausente_o_fuera_de_rango_va_al_defecto_con_aviso(self):
        for v, porque in ((None, "ausente"), (99, "mal formado"), (60001, "mal formado"), ("5000", "mal formado"),
                          (True, "mal formado")):
            e = bloque()
            if v is None:
                del e["connection_timeout_ms"]
            else:
                e["connection_timeout_ms"] = v
            *_, t, log = cb.leer_bloque(json_tmp({"etcd": e}))
            self.assertEqual(t, 5000, v)
            self.assertIn(f"[CONFIG-DEFAULT] etcd.connection_timeout_ms=5000 (DEFECTO: {porque}; entero en "
                          "[100, 60000] ms)", log, v)

    def test_endpoint_y_ca_sin_defecto(self):
        malos = [{"etcd": bloque(endpoints=[])}, {"etcd": bloque(endpoints="https://x:1")},
                 {"etcd": bloque(endpoints=["http://192.168.100.20:2379"])},
                 {"etcd": bloque(endpoints=["https://192.168.100.20"])},
                 {"etcd": bloque(endpoints=["https://192.168.100.20:99999"])},
                 {"etcd": bloque(endpoints=["https://192.168.100.20:2379/otra"])},
                 {"etcd": bloque(ca_file="relativa.crt")}, {"etcd": bloque(ca_file=None)}, {"otro": 1}, [1], "{"]
        for m in malos:
            with self.assertRaises(cb.Fallo, msg=m) as c:
                cb.leer_bloque(json_tmp(m))
            self.assertEqual(c.exception.codigo, cb.SALIDA_USO, m)


class Respuesta(unittest.TestCase):
    def test_una_sola_activa(self):
        self.assertEqual(cb.clave_activa(resp((K1, False), (K2, True))), K2)

    def test_rechaza(self):
        for datos, texto in ((resp((K1, True), (K2, True)), "hay 2"), (resp((K1, False)), "hay 0"),
                             (resp(("A" * 64, True)), "64 hex"), (resp(("a" * 63, True)), "64 hex"),
                             (json.dumps({"keys": [{"key": K1, "is_active": "true"}]}).encode(), "hay 0"),
                             (b"no es json", "no es JSON"), (b'{"otra": 1}', "lista keys")):
            with self.assertRaises(cb.Fallo, msg=datos) as c:
                cb.clave_activa(datos)
            self.assertIn(texto, str(c.exception))


class Orden(unittest.TestCase):
    def correr(self, argv, status=200, cuerpo=None):
        self.pedidos = []

        def falsa(host, puerto, ca, cert, key, timeout_s, ruta):
            self.pedidos.append((host, puerto, ca, cert, key, timeout_s, ruta))
            return status, cuerpo if cuerpo is not None else resp((K2, True))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cb.main(argv, pedir=falsa)
        return rc, out.getvalue(), err.getvalue()

    def test_imprime_solo_la_clave_y_pide_con_la_identidad_del_conversor(self):
        j = json_tmp({"etcd": bloque()})
        rc, out, err = self.correr(["--json", j, "--pki", "/pki", "firewall-acl-agent"])
        self.assertEqual((rc, out), (0, K2 + "\n"))
        self.assertEqual(self.pedidos, [("192.168.100.20", 2379, "/etc/argus-pki/ca.crt",
                                         "/pki/bronze-to-gold-converter.crt", "/pki/bronze-to-gold-converter.key",
                                         5.0, "/secrets/valid/firewall-acl-agent")])
        self.assertIn("[CLAVE-BRONCE] [CONFIG] etcd.connection_timeout_ms=5000 (JSON)", err)

    def test_errores_sin_clave_por_stdout(self):
        j = json_tmp({"etcd": bloque()})
        for argv, kw, rc_esperado in ((["--json", j, "ml-detector"], {"status": 403}, 1),
                                      (["--json", j, "ml-detector"], {"cuerpo": b"x" * (cb.MAX_RESPUESTA + 1)}, 1),
                                      (["--json", j, "ml-detector"], {"cuerpo": resp((K1, False))}, 1),
                                      (["--json", j, "../etc"], {}, 2),
                                      (["--json", json_tmp("{"), "ml-detector"], {}, 2)):
            rc, out, err = self.correr(argv, **kw)
            self.assertEqual((rc, out), (rc_esperado, ""), (argv, kw))
            self.assertIn("[CLAVE-BRONCE]", err)

    def test_pedir_real_sin_certificado_es_un_fallo_claro(self):
        with self.assertRaises(cb.Fallo) as c:
            cb.pedir("127.0.0.1", 9, "/no/existe/ca.crt", "/no/c.crt", "/no/c.key", 1.0, "/secrets/valid/x")
        self.assertIn("GET https://127.0.0.1:9/secrets/valid/x", str(c.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
