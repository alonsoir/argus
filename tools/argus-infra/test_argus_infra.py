#!/usr/bin/python3 -I
# test_argus_infra.py — [PROTEGIDOS-MANIFIESTO-D319] ADR-060 8e.3d. Tests de argus-infra con la biblioteca estándar
# (unittest), sin red ni Vault: el validador portado de libs/protegidos (mismos casos que
# libs/protegidos/tests/test_protegidos_manifiesto.cpp, mismo motivo de rechazo), la configuración, la plantilla del
# repo, la construcción de la carga, el diff y la política. La firma Ed25519 la verifica Vault (prueba de punta a punta
# en el banco y en el lab); aquí se simula con verificar_firma.
#   python3 -I tools/argus-infra/test_argus_infra.py       (make test-argus-infra, en la VM etcd)
import base64
import datetime
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True  # se ejecuta desde /vagrant: sin __pycache__ en el repo
AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("argus_infra", os.path.join(AQUI, "argus-infra.py"))
ai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ai)

LIM = '{"infraestructura":32,"intranet":24,"dmz":24,"externos_criticos":32}'
FIRMA = "vault:v1:" + base64.b64encode(bytes(range(64))).decode()


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def entrada(cat, cidr, iface="eth2", mac="", motivo="prueba"):
    return json.dumps({"categoria": cat, "cidr": cidr, "interfaz": iface, "mac": mac, "motivo": motivo},
                      separators=(",", ":"))


KLAB = entrada("infraestructura", "192.168.100.20/32") + "," + entrada("intranet", "192.168.100.61/32")


def carga(version, planta_lab, comun="", limites=LIM, hospital="hospital-lab", extra="", otras=""):
    # La misma forma que prueba::carga de libs/protegidos/tests/ayuda_firma.hpp
    return ('{"esquema":1,"hospital_id":"' + hospital + '","version":' + str(version) +
            ',"emitido_utc":"2026-11-05T08:00:00Z","firmante":"argus-infra","motivo":"alta del lab",'
            '"hash_anterior":"","limites":' + limites + ',"comun":[' + comun + '],"plantas":{"lab-vagrant":[' +
            planta_lab + ']' + otras + '}' + extra + '}').encode()


def sobre(c, firma=FIRMA, extra=""):
    return ('{"formato":"argus-protegidos/v1","carga_b64":"' + base64.b64encode(c).decode() + '","firma":"' + firma +
            '"' + extra + '}').encode()


def V(s, planta="lab-vagrant", aplicada=0, hospital="hospital-lab", firma_ok=True):
    return ai.validar_sobre(s, hospital, planta, aplicada, lambda c, f: firma_ok)


class Validador(unittest.TestCase):
    def rech(self, motivo, s, **kw):
        with self.assertRaises(ai.Rechazo) as cm:
            V(s, **kw)
        self.assertEqual(cm.exception.motivo, motivo, cm.exception.detalle)

    def test_01_valido(self):
        c = carga(1, KLAB)
        m = V(sobre(c))
        self.assertEqual(m["version"], 1)
        self.assertEqual(len(m["entradas"]), 2)
        self.assertEqual(m["entradas"][0]["interfaz"], "eth2")
        self.assertEqual(m["sha256"], hashlib.sha256(c).hexdigest())
        self.assertEqual(m["sobre"], sobre(c))

    def test_03_firma(self):
        c = carga(1, KLAB)
        self.rech("firma", sobre(c), firma_ok=False)
        corta = "vault:v1:" + base64.b64encode(bytes(63)).decode()
        self.rech("formato", sobre(c, corta))
        for f in ("v1:abc", "vault:v0:" + FIRMA[9:], "vault:vx:" + FIRMA[9:], "", "vault:v01:" + FIRMA[9:],
                  "vault:v12345678901:" + FIRMA[9:], "vault:v1:" + FIRMA[9:-2]):
            self.rech("formato", sobre(c, f))

    def test_04_version(self):
        s = sobre(carga(5, KLAB))
        self.rech("version", s, aplicada=5)
        self.rech("version", s, aplicada=7)
        self.assertEqual(V(s, aplicada=4)["version"], 5)

    def test_05_hospital_y_planta(self):
        self.rech("hospital", sobre(carga(1, KLAB, hospital="hospital-otro")))
        c2 = carga(1, KLAB, entrada("externos_criticos", "203.0.113.10/32", "eth1"), otras=',"planta-2":[' +
                   entrada("dmz", "10.2.0.0/24") + ']')
        self.rech("planta", sobre(c2), planta="planta-3")
        m = V(sobre(c2))
        self.assertEqual(len(m["entradas"]), 3)
        self.assertTrue(m["entradas"][0]["comun"] and not m["entradas"][1]["comun"])
        self.assertEqual(len(V(sobre(c2), planta="planta-2")["entradas"]), 2)

    def test_06_limites(self):
        self.rech("limite", sobre(carga(1, entrada("infraestructura", "192.168.100.20/31"))))
        self.rech("limite", sobre(carga(1, entrada("intranet", "192.168.100.0/23"))))
        V(sobre(carga(1, entrada("intranet", "192.168.100.0/24"))))
        V(sobre(carga(1, entrada("infraestructura", "fd00::20/128"))))
        self.rech("limite", sobre(carga(1, entrada("intranet", "fd00::/64"))))
        for l in ('{"infraestructura":31,"intranet":24,"dmz":24,"externos_criticos":32}',
                  '{"infraestructura":32,"intranet":4,"dmz":24,"externos_criticos":32}',
                  '{"infraestructura":32,"intranet":33,"dmz":24,"externos_criticos":32}'):
            self.rech("limite", sobre(carga(1, KLAB, limites=l)))
        self.rech("formato", sobre(carga(1, KLAB, limites='{"infraestructura":32,"intranet":24,"dmz":24}')))
        self.rech("formato", sobre(carga(1, KLAB, limites='{"infraestructura":32,"intranet":24.0,"dmz":24,'
                                                          '"externos_criticos":32}')))

    def test_07_entradas_mal_formadas(self):
        sin_iface = '{"categoria":"intranet","cidr":"192.168.100.61/32","mac":"","motivo":"x"}'
        for e in (sin_iface, entrada("intranet", "192.168.100.61/32", ""),
                  entrada("intranet", "192.168.100.61/32", "eth2;rm"),
                  entrada("intranet", "192.168.100.61/32", "interfaz-demasiado-larga"),
                  entrada("intranet", "192.168.100.61/32", "eth2", "AA:BB:CC:DD:EE:FF"),
                  entrada("intranet", "192.168.100.61/32", "eth2", "aa:bb:cc:dd:ee"),
                  entrada("lan", "192.168.100.61/32"), entrada("intranet", "192.168.100.300/32"),
                  entrada("intranet", "192.168.100.61/24"), entrada("intranet", "192.168.100.61"),
                  entrada("intranet", "192.168.100.61/32", "eth2", "", ""),
                  entrada("intranet", "192.168.100.61/32", "eth2", "", "a\u0001b"),
                  entrada("intranet", "192.168.100.61/32", "eth2", "", "x" * 201),
                  entrada("intranet", "192.168.100.61/32") + "," + entrada("intranet", "192.168.100.61/32"),
                  entrada("intranet", "192.168.100.61/32") + "," + entrada("dmz", "192.168.100.61/32", "eth1"),
                  entrada("intranet", " 192.168.100.61/32"), entrada("intranet", "192.168.100.61/32/32"),
                  entrada("intranet", "192.168.100.61/0032")):
            with self.subTest(e=e):
                self.rech("formato", sobre(carga(1, e)))
        V(sobre(carga(1, entrada("intranet", "192.168.100.61/32") + "," +
                      entrada("intranet", "192.168.100.61/32", "eth1", "08:00:27:aa:bb:cc"))))
        self.rech("limite", sobre(carga(1, KLAB, otras=',"planta-2":[' + entrada("dmz", "10.0.0.0/8") + ']')))

    def test_07b_cidr_como_el_validador_de_c(self):
        # Lo que is_valid_ip_cidr + inet_pton aceptan: prefijo con cero a la izquierda (3 cifras), IPv6 en mayúsculas
        V(sobre(carga(1, entrada("intranet", "192.168.100.61/032"))))
        V(sobre(carga(1, entrada("infraestructura", "FD00::20/128"))))
        self.rech("formato", sobre(carga(1, entrada("intranet", "192.168.100.061/32"))))   # inet_pton: sin octales

    def test_08_sobre_y_carga(self):
        c = carga(1, KLAB)
        self.rech("formato", sobre(c, extra=',"ranura_clave":"actual"'))
        self.rech("formato", ('{"formato":"argus-protegidos/v1","formato":"x","carga_b64":"' +
                              base64.b64encode(c).decode() + '","firma":"' + FIRMA + '"}').encode())
        self.rech("formato", sobre(c).replace(b"/v1", b"/v2"))
        self.rech("formato", b"no es json")
        self.rech("formato", b"[]")
        self.rech("formato", sobre(carga(1, KLAB, extra=',"extra":1')))
        self.rech("formato", sobre(c.replace(b'"esquema":1', b'"esquema":2')))
        self.rech("formato", sobre(c.replace(b'"esquema":1', b'"esquema":true')))
        self.rech("formato", sobre(c.replace(b'"version":1', b'"version":1.0')))
        self.rech("formato", sobre(c.replace(b'"version":1', b'"version":-1')))
        self.rech("formato", sobre(c.replace(b'"version":1', b'"version":18446744073709551616')))
        V(sobre(c.replace(b'"version":1', b'"version":18446744073709551615')))
        self.rech("formato", sobre(c.replace(b"2026-11-05T08:00:00Z", b"2026-11-05 08:00:00")))
        self.rech("formato", sobre(b'{"no":"es la carga"'))
        V(sobre(c) + b" ")
        self.rech("formato", sobre(c) + b"{}")
        self.rech("formato", sobre(c, extra=',"x":NaN'))
        self.rech("formato", sobre(c.replace(b'"motivo":"alta del lab"', b'"motivo":"\xff"')))
        self.rech("formato", sobre(c.replace(b'"hash_anterior":""', b'"hash_anterior":"' + b"A" * 64 + b'"')))
        self.rech("formato", b" " * (ai.MAX_SOBRE + 1))
        self.rech("formato", ('{"formato":"argus-protegidos/v1","carga_b64":"' + base64.b64encode(c).decode()[:-1] +
                              '","firma":"' + FIRMA + '"}').encode())
        # Medido DAY319 con libs/protegidos: fuera del alfabeto base64 (salto de línea, espacio) y una clave duplicada
        # aunque repita el mismo valor, rechazo motivo=formato
        b = base64.b64encode(c).decode()
        for sucio in (b[:40] + "\\n" + b[40:], b[:40] + " " + b[40:], b[:40] + "!" + b[41:]):
            self.rech("formato", ('{"formato":"argus-protegidos/v1","carga_b64":"' + sucio + '","firma":"' + FIRMA +
                                  '"}').encode())
        self.rech("formato", sobre(c).replace(b'{"formato":"argus-protegidos/v1",',
                                              b'{"formato":"argus-protegidos/v1","formato":"argus-protegidos/v1",', 1))
        self.rech("formato", sobre(c.replace(b'"esquema":1', b'"esquema":1,"esquema":1', 1)))

    def test_10c_documento(self):
        otra = ',"planta-2":[' + entrada("intranet", "10.1.0.0/24", "eth1") + ']'
        c1 = carga(3, KLAB, otras=otra)
        m = V(sobre(c1), planta=None, aplicada=2)
        self.assertEqual((m["version"], len(m["entradas"])), (3, 3))
        self.rech("version", sobre(c1), planta=None, aplicada=3)
        self.rech("hospital", sobre(c1), planta=None, hospital="otro-hospital")
        self.rech("firma", sobre(c1), planta=None, firma_ok=False)
        comun = entrada("intranet", "10.9.0.0/24", "eth1")
        c2 = carga(4, KLAB, comun, otras=',"planta-2":[' + comun + ']')
        V(sobre(c2))                                     # el firewall de lab-vagrant lo aceptaría
        self.rech("formato", sobre(c2), planta=None)     # el documento entero no
        c3 = carga(5, KLAB).replace(b'"plantas":{"lab-vagrant":[' + KLAB.encode() + b']}', b'"plantas":{}')
        self.rech("planta", sobre(c3), planta=None)


def _cfg():
    return {"hospital_id": "hospital-lab", "plantas": ["lab-vagrant"],
            "limites": {"infraestructura": 32, "intranet": 24, "dmz": 24, "externos_criticos": 32}}


class Construccion(unittest.TestCase):
    def test_carga_construida_valida_y_ascii(self):
        cfg = _cfg()
        p = leer_json(os.path.join(AQUI, "plantillas", "hospital-lab.json"))
        ahora = datetime.datetime(2026, 11, 6, 7, 0, 0, tzinfo=datetime.timezone.utc)
        c = ai.construir_carga(cfg, 1, "vault cert=argus-infra cn=argus-infra entidad=x", p["motivo"], "",
                               p["comun"], p["plantas"], ahora)
        c.decode("ascii")
        m = ai.validar_carga(c, "hospital-lab", "lab-vagrant", 0)
        self.assertEqual([(e["categoria"], e["cidr"], e["interfaz"]) for e in m["entradas"]],
                         [("infraestructura", "192.168.100.20/32", "eth2"), ("intranet", "192.168.100.61/32", "eth2")])
        self.assertEqual(m["carga"]["emitido_utc"], "2026-11-06T07:00:00Z")
        self.assertEqual(m["carga"]["limites"], cfg["limites"])
        s = ai.construir_sobre(c, FIRMA)
        self.assertEqual(ai.abrir_sobre(s), (c, FIRMA))
        # Motivo con tilde: escapado en ASCII, el validador lo acepta (UTF-8 al decodificar)
        c2 = ai.construir_carga(cfg, 2, "f", "versión con tilde", hashlib.sha256(c).hexdigest(), [], p["plantas"])
        c2.decode("ascii")
        self.assertEqual(ai.validar_carga(c2, "hospital-lab", None, 1)["carga"]["motivo"], "versión con tilde")

    def test_planta_ausente_de_la_plantilla_sale_vacia(self):
        cfg = _cfg()
        cfg["plantas"] = ["lab-vagrant", "planta-2"]
        c = ai.construir_carga(cfg, 1, "f", "m", "", [], {"lab-vagrant": []})
        self.assertEqual(json.loads(c)["plantas"], {"lab-vagrant": [], "planta-2": []})

    def test_diferencias(self):
        a = json.loads(carga(1, KLAB))
        b = json.loads(carga(2, entrada("infraestructura", "192.168.100.20/32") + "," +
                             entrada("intranet", "192.168.100.62/32", motivo="otra")))
        lineas, altas, bajas = ai.diferencias(a, b)
        self.assertEqual(altas, ["plantas.lab-vagrant:intranet 192.168.100.62/32 eth2"])
        self.assertEqual(bajas, ["plantas.lab-vagrant:intranet 192.168.100.61/32 eth2"])
        _, altas0, bajas0 = ai.diferencias(None, a)
        self.assertEqual(len(altas0), 2)
        self.assertEqual(bajas0, [])
        c = json.loads(carga(3, entrada("infraestructura", "192.168.100.20/32", mac="08:00:27:00:00:01") + "," +
                             entrada("intranet", "192.168.100.61/32")))
        lineas, altas, bajas = ai.diferencias(a, c)
        self.assertEqual((altas, bajas), ([], []))
        self.assertTrue(any(ln.startswith("  ~ ") for ln in lineas))
        self.assertEqual(ai.diferencias(a, a)[0], ["  (sin cambios en las entradas)"])

    def test_politica(self):
        cfg = _cfg()
        m = ai.validar_carga(carga(1, KLAB, otras=',"planta-2":[]'), "hospital-lab", None, 0)
        avisos, errores = ai.politica(cfg, m)
        self.assertEqual(len(errores), 1)        # planta-2 no está en la configuración
        m2 = ai.validar_carga(carga(1, KLAB, limites='{"infraestructura":32,"intranet":28,"dmz":24,'
                                                     '"externos_criticos":32}'), "hospital-lab", None, 0)
        avisos, errores = ai.politica(cfg, m2)
        self.assertEqual((len(avisos), errores), (1, []))

    def test_canonico(self):
        self.assertEqual(ai.canonico("192.168.100.61/32"), "192.168.100.61/32")
        self.assertEqual(ai.canonico("192.168.100.61/24"), "192.168.100.0/24")
        self.assertEqual(ai.canonico("FD00::20/128"), "fd00::20/128")


class Configuracion(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for f in ("ca.crt", "argus-infra.crt", "argus-infra.key"):
            with open(os.path.join(self.d, f), "w") as fh:
                fh.write("x")

    def escribir(self, j):
        r = os.path.join(self.d, "c.json")
        with open(r, "w") as f:
            f.write(json.dumps(j) if not isinstance(j, str) else j)
        return r

    def del_repo(self):
        j = leer_json(os.path.join(AQUI, "argus-infra.lab.json"))
        j["vault"]["ca_file"] = j["etcd_server"]["ca_file"] = os.path.join(self.d, "ca.crt")
        j["tls"]["cert_file"] = os.path.join(self.d, "argus-infra.crt")
        j["tls"]["key_file"] = os.path.join(self.d, "argus-infra.key")
        return j

    def test_la_del_repo_vale_y_registra_cada_campo(self):
        cfg, log = ai.leer_config(self.escribir(self.del_repo()))
        self.assertEqual(cfg["hospital_id"], "hospital-lab")
        self.assertEqual(cfg["plantas"], ["lab-vagrant"])
        self.assertEqual(cfg["vault"]["port"], 8200)
        self.assertEqual(cfg["etcd_server"]["host"], "127.0.0.1")
        self.assertEqual(cfg["timeout_s"], 10)
        self.assertIn("[ARGUS-INFRA-CONFIG] timeout_s=10 (JSON)", log)
        self.assertIn("[ARGUS-INFRA-CONFIG] limites.intranet=24 (JSON)", log)
        self.assertEqual(sum(1 for ln in log if ln.startswith("[ARGUS-INFRA-CONFIG] ")), 16)

    def test_timeout_defecto_avisado(self):
        for v in (None, 0, 121, "10", 10.5, True):
            j = self.del_repo()
            if v is None:
                del j["timeout_s"]
            else:
                j["timeout_s"] = v
            cfg, log = ai.leer_config(self.escribir(j))
            self.assertEqual(cfg["timeout_s"], 10, v)
            self.assertTrue(any(ln.startswith("[CONFIG-DEFAULT] timeout_s=10 (DEFECTO:") for ln in log), v)

    def test_identidad_sin_defecto(self):
        malas = [("hospital_id", "Hosp_Lab"), ("plantas", []), ("plantas", ["a", "a"]),
                 ("limites", {"infraestructura": 31, "intranet": 24, "dmz": 24, "externos_criticos": 32}),
                 ("limites", {"infraestructura": 32, "intranet": 7, "dmz": 24, "externos_criticos": 32}),
                 ("vault.url", "http://127.0.0.1:8200"), ("vault.url", "https://127.0.0.1:8200/v1"),
                 ("vault.url", "https://127.0.0.1"), ("vault.clave", "protegidos-otro"),
                 ("vault.ca_file", "/no/existe"), ("tls.key_file", "relativa.key"), ("etcd_server", None)]
        for campo, v in malas:
            with self.subTest(campo=campo, v=v):
                j = self.del_repo()
                if "." in campo:
                    a, b = campo.split(".")
                    j[a][b] = v
                elif v is None:
                    del j[campo]
                else:
                    j[campo] = v
                with self.assertRaises(ai.Fallo) as cm:
                    ai.leer_config(self.escribir(j))
                self.assertEqual(cm.exception.codigo, ai.SALIDA_USO)
                self.assertIn("sin valor sano por defecto", str(cm.exception))
        for texto in ("{no json", '{"a":1,"a":2}', "[]"):
            with self.assertRaises(ai.Fallo):
                ai.leer_config(self.escribir(texto))

    def test_desconocidos_avisan(self):
        j = self.del_repo()
        j["sobra"] = 1
        j["vault"]["sobra"] = 1
        _, log = ai.leer_config(self.escribir(j))
        self.assertIn("[CONFIG-AVISO] sobra: campo desconocido (se ignora)", log)
        self.assertIn("[CONFIG-AVISO] vault.sobra: campo desconocido (se ignora)", log)

    def test_plantilla_del_repo(self):
        cfg = _cfg()
        p = ai.leer_plantilla(os.path.join(AQUI, "plantillas", "hospital-lab.json"), cfg)
        self.assertEqual(len(p["plantas"]["lab-vagrant"]), 2)
        cfg2 = _cfg()
        cfg2["hospital_id"] = "otro"
        with self.assertRaises(ai.Fallo):
            ai.leer_plantilla(os.path.join(AQUI, "plantillas", "hospital-lab.json"), cfg2)
        cfg3 = _cfg()
        cfg3["plantas"] = ["lab-vagrant", "planta-2"]
        with self.assertRaises(ai.Fallo):
            ai.leer_plantilla(os.path.join(AQUI, "plantillas", "hospital-lab.json"), cfg3)
        j = leer_json(os.path.join(AQUI, "plantillas", "hospital-lab.json"))
        j["plantas"]["lab-vagrant"][0]["sobra"] = 1
        with self.assertRaises(ai.Fallo):
            ai.leer_plantilla(self.escribir(j), cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
