#!/usr/bin/python3 -I
# test_recursos_anfitrion.py — [RECURSOS-ANFITRION-D327] tests de recursos_anfitrion.py (unittest, sin tocar el Mac: las
# medidas entran simuladas). Lo que importa: que NO deje arrancar cuando falta un recurso (cada umbral, en su frontera)
# o cuando una medida no se puede leer, y que el JSON mande (defecto con aviso si falta o está mal; nunca se para por
# la configuración).   python3 -I scripts/emecas/test_recursos_anfitrion.py     (make test-anfitrion-recursos)
import importlib.util
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("recursos_anfitrion", os.path.join(AQUI, "recursos_anfitrion.py"))
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)

SANO_SIN_LAB = {"carga_5min": 3.33, "swap_usado_mb": 153.25, "presion_memoria": 1, "nivel_memoria": 84, "disco_libre_gb": 167.0}
SANO_CON_LAB = {"carga_5min": 8.2, "swap_usado_mb": 4051.75, "presion_memoria": 1, "nivel_memoria": 67, "disco_libre_gb": 167.0}
AHOGADO = {"carga_5min": 46.0, "swap_usado_mb": 5427.0, "presion_memoria": 2, "nivel_memoria": 30, "disco_libre_gb": 170.0}


def config(contenido):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    f.write(contenido if isinstance(contenido, str) else json.dumps(contenido))
    f.close()
    return f.name


def corre(perfil, medidas, ruta=None):
    lineas = []
    rc = ra.main([perfil, "--config", ruta or ra.CONFIG], pinta=lineas.append, medidor=lambda: dict(medidas),
                 extra=lambda p: p("GLOTONES"))
    return rc, "\n".join(lineas)


class ElJsonDelRepo(unittest.TestCase):
    def test_los_defectos_del_codigo_son_los_valores_del_json(self):
        with open(ra.CONFIG, encoding="utf-8") as f:
            j = json.load(f)
        for campo, _s, lo, hi, d_em, d_lab, _q in ra.CAMPOS:
            self.assertEqual((j["emecas"][campo], j["lab_e2e"][campo]), (d_em, d_lab), campo)
            self.assertTrue(lo <= d_em <= hi and lo <= d_lab <= hi, campo)
            self.assertIn("[%d, %d]" % (lo, hi), j["_campos"][campo], campo)
        self.assertEqual(sorted(k for k in j if not k.startswith("_")), sorted(ra.PERFILES))

    def test_cada_campo_se_escribe_con_su_origen(self):
        _, txt = corre("emecas", SANO_SIN_LAB)
        for campo, *_ in ra.CAMPOS:
            self.assertIn("emecas.%s=" % campo, txt)
        self.assertEqual(txt.count("(JSON)"), len(ra.CAMPOS))


class Veredicto(unittest.TestCase):
    def test_mac_sano_sin_lab_pasa_emecas(self):
        rc, txt = corre("emecas", SANO_SIN_LAB)
        self.assertEqual(rc, 0)
        self.assertIn("RESULTADO PASA", txt)
        self.assertNotIn("GLOTONES", txt)

    def test_lab_sano_pasa_lab_e2e_pero_no_emecas(self):
        self.assertEqual(corre("lab_e2e", SANO_CON_LAB)[0], 0)
        rc, txt = corre("emecas", SANO_CON_LAB)   # por eso emecas se comprueba tras el destroy
        self.assertEqual(rc, 1)
        self.assertIn("swap usado (MB): 4051.75 (máximo 1024)", txt)

    def test_mac_ahogado_no_arranca_en_ningun_perfil(self):
        for perfil in ra.PERFILES:
            rc, txt = corre(perfil, AHOGADO)
            self.assertEqual(rc, 1, perfil)
            self.assertIn("NO se arranca por falta de recursos disponibles en el anfitrión", txt)
            self.assertIn("carga a 5 min: 46.00", txt)
            self.assertIn("GLOTONES", txt)

    def test_cada_umbral_en_su_frontera(self):
        # (medida, valor justo en el umbral de emecas: pasa, valor un paso más allá: falla)
        for medida, justo, pasado in (("carga_5min", 8.0, 8.01), ("swap_usado_mb", 1024.0, 1024.5),
                                      ("presion_memoria", 1, 2), ("nivel_memoria", 70, 69),
                                      ("disco_libre_gb", 50.0, 49.9)):
            self.assertEqual(corre("emecas", dict(SANO_SIN_LAB, **{medida: justo}))[0], 0, medida)
            rc, txt = corre("emecas", dict(SANO_SIN_LAB, **{medida: pasado}))
            self.assertEqual(rc, 1, medida)
            self.assertEqual(txt.count("\nFALLA "), 1, medida)

    def test_una_medida_sin_leer_no_deja_arrancar(self):
        for medida in SANO_SIN_LAB:
            rc, txt = corre("emecas", dict(SANO_SIN_LAB, **{medida: None}))
            self.assertEqual(rc, 1, medida)
            self.assertIn("NO MEDIDO", txt)

    def test_uso_malo(self):
        for a in ([], ["otro"], ["emecas", "sobra"], ["emecas", "--config"]):
            self.assertEqual(ra.main(a, pinta=lambda s: None), 2, a)


class Configuracion(unittest.TestCase):
    def test_el_json_manda(self):
        ruta = config({"emecas": {"carga_5min_max": 2, "swap_usado_mb_max": 1024, "presion_memoria_max": 1,
                                  "nivel_memoria_min": 70, "disco_libre_gb_min": 50}})
        rc, txt = corre("emecas", SANO_SIN_LAB, ruta)
        self.assertEqual(rc, 1)
        self.assertIn("emecas.carga_5min_max=2 (JSON)", txt)
        self.assertIn("carga a 5 min: 3.33 (máximo 2)", txt)

    def test_campo_ausente_o_malo_defecto_con_aviso_y_sigue(self):
        for malo, trozo in (({}, "ausente"), ({"carga_5min_max": "8"}, "'8' mal formado"),
                            ({"carga_5min_max": 0}, "'0' mal formado"), ({"carga_5min_max": 257}, "'257' mal formado"),
                            ({"carga_5min_max": 8.5}, "'8.5' mal formado"), ({"carga_5min_max": True}, "'True' mal formado")):
            rc, txt = corre("emecas", SANO_SIN_LAB, config({"emecas": malo}))
            self.assertEqual(rc, 0, malo)
            self.assertIn("emecas.carga_5min_max=8 (defecto del código: %s; entero en [1, 256])" % trozo, txt)

    def test_el_defecto_es_el_del_perfil(self):
        rc, txt = corre("lab_e2e", SANO_CON_LAB, config({"lab_e2e": {}}))
        self.assertEqual(rc, 0)
        self.assertIn("lab_e2e.carga_5min_max=10 (defecto del código: ausente", txt)
        self.assertIn("lab_e2e.swap_usado_mb_max=5120 (defecto del código: ausente", txt)
        self.assertIn("lab_e2e.nivel_memoria_min=60 (defecto del código: ausente", txt)

    def test_sin_fichero_o_roto_todos_los_defectos_y_sigue(self):
        for ruta, trozo in (("/no/existe.json", "no se puede leer"), (config("{roto"), "no es JSON"),
                            (config({"lab_e2e": {}}), "sin objeto 'emecas'"), (config([1]), "sin objeto 'emecas'")):
            rc, txt = corre("emecas", SANO_SIN_LAB, ruta)
            self.assertEqual(rc, 0, ruta)
            self.assertIn(trozo, txt)
            self.assertEqual(txt.count("(defecto del código: ausente"), len(ra.CAMPOS))


class Medidas(unittest.TestCase):
    def test_swap_con_punto_coma_y_unidades(self):
        self.assertAlmostEqual(ra.swap_mb("total = 1024.00M  used = 252.75M  free = 771.25M  (encrypted)"), 252.75)
        self.assertAlmostEqual(ra.swap_mb("total = 5120,00M  used = 3017,75M  free = 2102,25M"), 3017.75)
        self.assertAlmostEqual(ra.swap_mb("total = 6.00G  used = 5.30G  free = 0.70G"), 5427.2)
        self.assertAlmostEqual(ra.swap_mb("total = 0.00M  used = 0.00M  free = 0.00M"), 0.0)
        for malo in (None, "", "sysctl: unknown oid", "used = muchos"):
            self.assertIsNone(ra.swap_mb(malo))

    def test_medir_con_sysctl_simulado(self):
        s = {"vm.swapusage": "total = 1024.00M  used = 252.75M  free = 771.25M", "kern.memorystatus_level": "84",
             "kern.memorystatus_vm_pressure_level": "1"}
        m = ra.medir(lee=s.get, carga=lambda: (6.45, 5.76, 5.27), disco=lambda r: type("D", (), {"free": 167 * 1024 ** 3})())
        self.assertEqual(m, {"carga_5min": 5.76, "swap_usado_mb": 252.75, "presion_memoria": 1, "nivel_memoria": 84,
                             "disco_libre_gb": 167.0})

    def test_medir_cuando_nada_contesta(self):
        def sin_carga(*a):
            raise OSError
        m = ra.medir(lee=lambda k: None, carga=sin_carga, disco=sin_carga)
        self.assertEqual(set(m.values()), {None})
        self.assertEqual(len(m), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
