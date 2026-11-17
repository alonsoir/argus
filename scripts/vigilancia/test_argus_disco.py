#!/usr/bin/env python3
"""scripts/vigilancia/test_argus_disco.py — [VIGILANCIA-D321] tests de argus_disco.py (unittest, biblioteca estándar).

Configuración (defectos, rangos, tipos, campos desconocidos, fichero ausente o ilegible), medida (como df, con un
statvfs falso), las líneas que leen el decoder y las reglas de Wazuh (formatos de provisioning/wazuh/argus), el aviso
de configuración solo cuando cambia, y una ejecución real de --una-vez.
[DISCO-RUTAS-D324] lista de rutas: una línea por partición (las rutas de un mismo st_dev juntas), una ruta inexistente
es ARGUS-DISCO-ERROR (estricto, decisión de Alonso DAY324) sin impedir medir las demás, y el antiguo campo "ruta" es
un campo desconocido.
Uso: python3 -I scripts/vigilancia/test_argus_disco.py   (make test-vigilancia-disco, en control-1)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import argus_disco as d  # noqa: E402

# Mismas expresiones que provisioning/wazuh/argus (decoder argus-disco-campos y regla 100542), en sintaxis de Python.
DECODER = re.compile(r"ARGUS-DISCO ruta=(\S+) uso=(\d+) umbral=(\d+) estado=(\w+)")
ERROR = "ARGUS-DISCO-ERROR"


def fs(blocks, bfree, bavail, frsize=4096):
    return lambda _ruta: SimpleNamespace(f_blocks=blocks, f_bfree=bfree, f_bavail=bavail, f_frsize=frsize)


def st(devs):
    """stat falso: devs = {ruta: st_dev}; una ruta que no está da FileNotFoundError, como os.stat."""
    def f(ruta):
        if ruta not in devs:
            raise FileNotFoundError(2, "No such file or directory", ruta)
        return SimpleNamespace(st_dev=devs[ruta])
    return f


class Config(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "disco.json")

    def tearDown(self):
        self.dir.cleanup()

    def escribir(self, texto):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(texto)

    def test_fichero_del_repo_valido_y_sin_errores(self):
        repo = os.path.join(AQUI, "..", "..", "provisioning", "vigilancia", "disco.json")
        valores, origenes, errores = d.leer_config(repo)
        self.assertEqual(errores, [])
        self.assertEqual(set(origenes.values()), {"fichero"})
        self.assertEqual(valores, {"rutas": ("/var/log/vault", "/var/lib/etcd"), "umbral_pct": 75, "periodo_s": 60})

    def test_sin_vault_del_repo_valido_y_sin_errores(self):
        # [DISCO-RUTAS-D324] el de los nodos sin Vault hasta el PR2c (el Vagrantfile lo pone en control-2 y control-3)
        repo = os.path.join(AQUI, "..", "..", "provisioning", "vigilancia", "disco-sin-vault.json")
        valores, origenes, errores = d.leer_config(repo)
        self.assertEqual(errores, [])
        self.assertEqual(set(origenes.values()), {"fichero"})
        self.assertEqual(valores, {"rutas": ("/var/lib/etcd",), "umbral_pct": 75, "periodo_s": 60})

    def test_ausente_da_defectos_y_error(self):
        valores, origenes, errores = d.leer_config(self.ruta)
        self.assertEqual(valores, {k: v[0] for k, v in d.CAMPOS.items()})
        self.assertEqual(set(origenes.values()), {"defecto"})
        self.assertEqual(len(errores), 1)
        self.assertIn("no existe", errores[0])

    def test_json_ilegible(self):
        self.escribir("{umbral_pct: 80")
        _, origenes, errores = d.leer_config(self.ruta)
        self.assertEqual(set(origenes.values()), {"defecto"})
        self.assertIn("ilegible", errores[0])

    def test_no_es_objeto(self):
        self.escribir("[1, 2]")
        self.assertIn("no es un objeto", d.leer_config(self.ruta)[2][0])

    def test_vacio_es_todo_defecto_sin_error(self):
        self.escribir("{}")
        valores, origenes, errores = d.leer_config(self.ruta)
        self.assertEqual(errores, [])
        self.assertEqual(set(origenes.values()), {"defecto"})

    def test_bordes_del_rango_valen(self):
        for umbral, periodo, rutas in ((1, 10, ["/"]), (99, 3600, ["/r%d" % i for i in range(d.MAX_RUTAS)])):
            self.escribir(json.dumps({"umbral_pct": umbral, "periodo_s": periodo, "rutas": rutas}))
            valores, origenes, errores = d.leer_config(self.ruta)
            self.assertEqual(errores, [])
            self.assertEqual((valores["umbral_pct"], valores["periodo_s"], valores["rutas"]), (umbral, periodo, tuple(rutas)))
            self.assertEqual(set(origenes.values()), {"fichero"})

    def test_fuera_de_rango_o_de_tipo_da_defecto_y_error(self):
        malos = [("umbral_pct", 0), ("umbral_pct", 100), ("umbral_pct", 75.0), ("umbral_pct", "75"),
                 ("umbral_pct", True), ("periodo_s", 9), ("periodo_s", 3601), ("periodo_s", None),
                 ("rutas", "/var/log/vault"), ("rutas", []), ("rutas", ["var/log"]), ("rutas", ["/con espacio"]),
                 ("rutas", ["/x\n"]), ("rutas", [7]), ("rutas", ["/a", "/a"]), ("rutas", ["/a,/b"]),
                 ("rutas", ["/r%d" % i for i in range(d.MAX_RUTAS + 1)]), ("rutas", None)]
        for campo, valor in malos:
            with self.subTest(campo=campo, valor=valor):
                self.escribir(json.dumps({campo: valor}))
                valores, origenes, errores = d.leer_config(self.ruta)
                self.assertEqual(valores[campo], d.CAMPOS[campo][0])
                self.assertEqual(origenes[campo], "defecto")
                self.assertEqual(len(errores), 1)
                self.assertIn(campo, errores[0])

    def test_campo_desconocido_es_error_y_los_buenos_valen(self):
        self.escribir(json.dumps({"umbral": 80, "periodo_s": 30}))
        valores, origenes, errores = d.leer_config(self.ruta)
        self.assertEqual(len(errores), 1)
        self.assertIn("'umbral'", errores[0])
        self.assertEqual((valores["periodo_s"], origenes["periodo_s"]), (30, "fichero"))
        self.assertEqual(origenes["umbral_pct"], "defecto")

    def test_el_antiguo_ruta_es_desconocido(self):
        self.escribir(json.dumps({"ruta": "/var/log/vault"}))
        valores, origenes, errores = d.leer_config(self.ruta)
        self.assertEqual(len(errores), 1)
        self.assertIn("'ruta'", errores[0])
        self.assertEqual((valores["rutas"], origenes["rutas"]), (("/var/log/vault",), "defecto"))


class Medida(unittest.TestCase):
    def test_como_df(self):
        # usado 600, disponible 300 (100 reservados a root): 600/900 = 66.7 -> 67, como el Use% de df
        self.assertEqual(d.uso_pct("/", fs(1000, 400, 300)), 67)
        self.assertEqual(d.uso_pct("/", fs(1000, 1000, 1000)), 0)
        self.assertEqual(d.uso_pct("/", fs(1000, 0, 0)), 100)
        self.assertEqual(d.uso_pct("/", fs(1000, 999, 999)), 1)  # hacia arriba: 0.1 % ya es 1

    def test_particion_sin_bloques(self):
        with self.assertRaises(OSError):
            d.uso_pct("/", fs(0, 0, 0))

    def test_real_coincide_con_df(self):
        salida = subprocess.run(["df", "--output=pcent", "/"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(d.uso_pct("/"), int(salida.split()[-1].rstrip("%")))


class Ciclo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "disco.json")
        self.config({"rutas": ["/var/log/vault", "/var/lib/etcd"], "umbral_pct": 75, "periodo_s": 60})

    def tearDown(self):
        self.dir.cleanup()

    def config(self, j):
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(j, f)

    def medidas(self, lineas):
        return [DECODER.search(l).groups() for l in lineas if DECODER.search(l)]

    def test_ok_alto_y_umbral_exacto(self):
        mismo = st({"/var/log/vault": 1, "/var/lib/etcd": 1})
        for libres, uso, estado in ((900, 10, "OK"), (260, 74, "OK"), (250, 75, "ALTO"), (100, 90, "ALTO")):
            with self.subTest(uso=uso):
                lineas, periodo, _ = d.ciclo(self.ruta, None, fs(1000, libres, libres), mismo)
                self.assertEqual(self.medidas(lineas), [("/var/log/vault,/var/lib/etcd", str(uso), "75", estado)])
                self.assertEqual(periodo, 60)

    def test_una_linea_por_particion(self):
        # misma partición: una línea con las dos rutas; distintas: una cada una (y cada una con su uso)
        lineas, _, _ = d.ciclo(self.ruta, None, fs(1000, 900, 900), st({"/var/log/vault": 1, "/var/lib/etcd": 1}))
        self.assertEqual([m[0] for m in self.medidas(lineas)], ["/var/log/vault,/var/lib/etcd"])
        usos = {"/var/log/vault": (1000, 900, 900), "/var/lib/etcd": (1000, 100, 100)}
        lineas, _, _ = d.ciclo(self.ruta, None, lambda r: fs(*usos[r])(r), st({"/var/log/vault": 1, "/var/lib/etcd": 2}))
        self.assertEqual(self.medidas(lineas), [("/var/log/vault", "10", "75", "OK"), ("/var/lib/etcd", "90", "75", "ALTO")])

    def test_ruta_inexistente_es_error_y_las_demas_se_miden(self):
        # el caso de control-2/3 antes del PR2c: sin /var/log/vault (estricto: ERROR, regla 100542)
        lineas, _, _ = d.ciclo(self.ruta, None, fs(1000, 900, 900), st({"/var/lib/etcd": 1}))
        errores = [l for l in lineas if l.startswith(ERROR + " ")]
        self.assertEqual(len(errores), 1, lineas)
        self.assertTrue(errores[0].startswith("ARGUS-DISCO-ERROR ruta=/var/log/vault: "), errores[0])
        self.assertIsNone(DECODER.search(errores[0]))
        self.assertEqual(self.medidas(lineas), [("/var/lib/etcd", "10", "75", "OK")])

    def test_config_solo_al_cambiar(self):
        mismo = st({"/var/log/vault": 1, "/var/lib/etcd": 1})
        lineas, _, clave = d.ciclo(self.ruta, None, fs(1000, 900, 900), mismo)
        self.assertEqual([l for l in lineas if l.startswith("ARGUS-DISCO-CONFIG")],
                         ["ARGUS-DISCO-CONFIG rutas=/var/log/vault,/var/lib/etcd (fichero) umbral_pct=75 (fichero) "
                          "periodo_s=60 (fichero)"])
        lineas, _, clave = d.ciclo(self.ruta, clave, fs(1000, 900, 900), mismo)
        self.assertEqual(len(lineas), 1)  # solo la medida
        self.config({"umbral_pct": 50})
        lineas, _, _ = d.ciclo(self.ruta, clave, fs(1000, 900, 900), mismo)
        self.assertTrue(any(l.startswith("ARGUS-DISCO-CONFIG") and "umbral_pct=50 (fichero)" in l
                            and "rutas=/var/log/vault (defecto)" in l for l in lineas), lineas)

    def test_lineas_que_no_son_medida_no_las_lee_el_decoder(self):
        self.config({"umbral_pct": 0})
        lineas, _, _ = d.ciclo(self.ruta, None, fs(1000, 900, 900), st({}))
        self.assertEqual(len(lineas), 3, lineas)  # error de config, CONFIG, error de medida
        for l in lineas:
            self.assertIsNone(DECODER.search(l), l)
        self.assertEqual(sum(l.startswith(ERROR + " ") for l in lineas), 2)
        self.assertTrue(lineas[-1].startswith("ARGUS-DISCO-ERROR ruta=/var/log/vault: "), lineas[-1])

    def test_statvfs_que_falla_es_error_de_la_particion(self):
        def roto(_):
            raise OSError(5, "Input/output error")
        lineas, _, _ = d.ciclo(self.ruta, None, roto, st({"/var/log/vault": 1, "/var/lib/etcd": 1}))
        self.assertEqual(self.medidas(lineas), [])
        self.assertTrue(lineas[-1].startswith("ARGUS-DISCO-ERROR ruta=/var/log/vault,/var/lib/etcd: "), lineas[-1])

    def test_una_vez_de_verdad(self):
        # "/" existe, la otra no: una medida de "/" y un error de la inexistente (estricto), rc 0
        falta = os.path.join(self.dir.name, "no-existe")
        self.config({"rutas": ["/", falta], "umbral_pct": 99, "periodo_s": 10})
        r = subprocess.run([sys.executable, "-I", os.path.join(AQUI, "argus_disco.py"), self.ruta, "--una-vez"],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        lineas = r.stdout.splitlines()
        self.assertEqual(len(lineas), 3, lineas)
        self.assertTrue(lineas[0].startswith("ARGUS-DISCO-CONFIG rutas=/,%s (fichero)" % falta), lineas[0])
        self.assertTrue(lineas[1].startswith("ARGUS-DISCO-ERROR ruta=%s: " % falta), lineas[1])
        self.assertEqual(DECODER.search(lineas[2]).group(1), "/")

    def test_argumentos_malos(self):
        r = subprocess.run([sys.executable, "-I", os.path.join(AQUI, "argus_disco.py"), "-x"],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
