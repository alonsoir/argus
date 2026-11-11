#!/usr/bin/env python3
# scripts/emecas/test_emecas_paso.py — [EMECAS-PROGRESO-D322] tests de emecas_paso.py (unittest, biblioteca estándar,
# en un directorio temporal: no toca logs/lab). make test-emecas-paso (Mac).
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
H = os.path.join(AQUI, "emecas_paso.py")


class EmecasPaso(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.env = dict(os.environ, EMECAS_PROGRESO_DIR=self.d)

    def h(self, *a):
        r = subprocess.run([sys.executable, H] + list(a), env=self.env, capture_output=True, text=True, cwd=self.d)
        return r.returncode, r.stdout + r.stderr

    def corrida(self):
        c = [x for x in os.listdir(os.path.join(self.d, "emecas"))]
        self.assertEqual(len(c), 1)
        return os.path.join(self.d, "emecas", c[0])

    def modulo(self):
        os.environ["EMECAS_PROGRESO_DIR"] = self.d
        spec = importlib.util.spec_from_file_location("ep", H)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_el_codigo_de_salida_del_paso_se_devuelve(self):
        self.h("inicio", "emecas")
        self.assertEqual(self.h("paso", "emecas", "bien", "--", "true")[0], 0)
        self.assertEqual(self.h("paso", "emecas", "mal", "--", "sh", "-c", "exit 3")[0], 3)
        rc, out = self.h("paso", "emecas", "no-existe", "--", "/no/existe/orden")
        self.assertEqual(rc, 127)

    def test_la_salida_del_paso_pasa_tal_cual(self):
        self.h("inicio", "emecas")
        rc, out = self.h("paso", "emecas", "eco", "--", "echo", "hola desde el paso")
        self.assertIn("hola desde el paso", out)

    def test_primera_corrida_sin_porcentaje_y_luego_se_guardan_los_tiempos(self):
        self.h("inicio", "emecas++")
        self.h("paso", "emecas++", "a", "--", "true")
        self.assertIn("aún no hay porcentaje", self.h("ver")[1])
        self.h("fin", "emecas++", "emecas")       # receta intermedia: no guarda
        self.assertFalse(os.path.exists(os.path.join(self.d, "emecas_tiempos_emecas++.tsv")))
        rc, out = self.h("fin", "emecas++", "emecas++")
        self.assertEqual(rc, 0)
        self.assertIn("tiempos guardados", out)
        with open(os.path.join(self.d, "emecas_tiempos_emecas++.tsv"), encoding="utf-8") as f:
            self.assertEqual([ln.split("\t")[0] for ln in f if not ln.startswith("#")], ["a"])

    def test_un_paso_fallido_no_guarda_tiempos_y_se_ve_en_la_barra(self):
        self.h("inicio", "emecas")
        self.h("paso", "emecas", "x", "--", "false")
        rc, out = self.h("fin", "emecas", "emecas")
        self.assertIn("no se guardan", out)
        self.assertFalse(os.path.exists(os.path.join(self.d, "emecas_tiempos_emecas.tsv")))
        self.assertIn("FALLÓ", self.h("ver")[1])

    def test_porcentaje_y_fin_previsto_con_tiempos_medidos(self):
        with open(os.path.join(self.d, "emecas_tiempos_emecas.tsv"), "w", encoding="utf-8") as f:
            f.write("# cabecera\nuno\t100\ndos\t300\ntres\t600\n")
        with open(os.path.join(self.d, "emecas_progreso.txt"), "w", encoding="utf-8") as f:
            f.write("META emecas 1000\nINICIO uno 1000\nFIN uno 1100 0\nINICIO dos 1100\n")
        m = self.modulo()
        t = m.estado(ahora=1250)                  # dos lleva 150 de 300: hecho 100 + 150 = 250 de 1000
        self.assertIn("paso 2/3 dos en curso 2m30s (la última vez 5m00s)", t)
        self.assertIn(" 25 %", t)
        self.assertIn("quedan ~12m30s", t)        # 150 de dos + 600 de tres
        t = m.estado(ahora=1500)                  # dos se pasa de su tiempo: no cuenta más de 300
        self.assertIn(" 40 %", t)
        self.assertIn("quedan ~10m00s", t)

    def test_con_un_paso_fallido_la_cabecera_se_para_en_el_fallo(self):
        # [EMECAS-PROGRESO-D323] cuatro horas después de parar, la cabecera sigue diciendo lo que duró hasta el fallo
        with open(os.path.join(self.d, "emecas_progreso.txt"), "w", encoding="utf-8") as f:
            f.write("META emecas 1000\nINICIO uno 1000\nFIN uno 1100 0\nINICIO dos 1100\nFIN dos 1400 2\n")
        m = self.modulo()
        t = m.estado(ahora=1400 + 4 * 3600)
        cab = t.splitlines()[0]
        self.assertIn("hasta las %s (6m40s)" % m.hora(1400), cab)
        self.assertNotIn("4h", cab)
        self.assertIn("paso dos FALLÓ (rc=2) tras 5m00s", t)
        # sin fallo, la cabecera cuenta hasta ahora, como antes
        with open(os.path.join(self.d, "emecas_progreso.txt"), "w", encoding="utf-8") as f:
            f.write("META emecas 1000\nINICIO uno 1000\n")
        self.assertIn("(4m10s)", m.estado(ahora=1250).splitlines()[0])

    def test_carpeta_y_log_por_paso_con_la_salida_de_siempre(self):
        self.h("inicio", "emecas")
        rc, out = self.h("paso", "emecas", "test-all", "--", "sh", "-c", "echo por stdout; echo por stderr >&2")
        self.assertIn("por stdout", out)
        self.assertIn("por stderr", out)
        c = self.corrida()
        self.assertTrue(c.endswith("_emecas"))
        with open(os.path.join(c, "01_test-all.log"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn("por stdout", t)
        self.assertIn("por stderr", t)
        self.h("paso", "emecas", "dos", "--", "true")
        self.assertTrue(os.path.exists(os.path.join(c, "02_dos.log")))

    def test_resumen_de_una_corrida_buena_con_veredictos_y_diferencias(self):
        with open(os.path.join(self.d, "emecas_tiempos_emecas.tsv"), "w", encoding="utf-8") as f:
            f.write("prot\t100\n")
        self.h("inicio", "emecas")
        self.h("paso", "emecas", "prot", "--", "sh", "-c",
               "echo ruido; printf '\\033[32m[VEREDICTO] PASA  P1 manifiesto\\033[0m\\n'; echo '  ✅ C1 bien'; "
               "echo '[VEREDICTO] RESULTADO PASA (protegidos)'")
        rc, out = self.h("fin", "emecas", "emecas")
        self.assertIn("[EMECAS-RESUMEN]", out)
        with open(os.path.join(self.corrida(), "resumen.md"), encoding="utf-8") as f:
            r = f.read()
        self.assertIn("# EMECAS emecas — PASA", r)
        self.assertIn("git no disponible", r)                     # el directorio temporal no es un repo
        self.assertIn("| 1 | prot |", r)
        self.assertIn("(antes 1m40s)", r)                         # frente a la corrida buena anterior, no a esta
        self.assertIn("[VEREDICTO] PASA  P1 manifiesto", r)       # sin los códigos de color
        self.assertNotIn("\x1b", r)
        self.assertIn("RESULTADO PASA (protegidos)", r)
        self.assertNotIn("ruido", r)
        self.assertIn("(✅ 1, ❌/FALLA 0)", r)

    def test_resumen_al_fallar_con_la_cola_del_paso(self):
        self.h("inicio", "emecas+++")
        self.h("paso", "emecas+++", "bien", "--", "true")
        rc, out = self.h("paso", "emecas+++", "lab-e2e", "--", "sh", "-c",
                         "for i in $(seq 1 60); do echo linea $i; done; echo '[VEREDICTO] FALLA P2 episodio'; exit 2")
        self.assertEqual(rc, 2)
        self.assertIn("[EMECAS-RESUMEN]", out)
        with open(os.path.join(self.corrida(), "resumen.md"), encoding="utf-8") as f:
            r = f.read()
        self.assertIn("# EMECAS emecas+++ — FALLA", r)
        self.assertIn("| 2 | lab-e2e |", r)
        self.assertIn("❌ rc=2", r)
        self.assertIn("## Falló: paso 2 lab-e2e (rc=2)", r)
        self.assertIn("linea 60", r)
        self.assertNotIn("linea 20\n", r)                         # solo las últimas 40 líneas
        self.assertIn("FALLA P2 episodio", r)

    def test_uso(self):
        self.assertEqual(self.h("paso", "emecas", "x", "true")[0], 2)
        self.assertEqual(self.h("inicio", "otra")[0], 2)
        self.assertIn("no hay ninguna corrida", self.h("ver")[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
