#!/usr/bin/python3 -I
# test_falco_silencio.py — [FALCO-SILENCIO-D327] tests de falco_silencio.py con la biblioteca estándar (unittest), sin
# VMs ni Falco: la cuenta de eventos, «medir» sobre un directorio de eventos de usar y tirar (con Falco, la sonda y la
# espera simulados) y «lab» con vagrant ssh simulado. Lo que más importa: que FALLE cuando debe (una CRITICAL, también
# en un rotado o en un .gz) y que nunca dé un silencio sin medir (Falco parado, sonda que no aparece, líneas rotas, una
# VM que no contesta, salida incoherente). La medida de verdad es make falco-silencio, con las VMs arriba.
#   python3 -I scripts/vigilancia/test_falco_silencio.py      (make test-falco-silencio, en el Mac)
import gzip
import importlib.util
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("falco_silencio", os.path.join(AQUI, "falco_silencio.py"))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

CLAVE = "/etc/etcd/tls/etcd.key"


def ev(regla="argus_lab_clave_leida_admin", prio="Notice", t="2026-11-15T05:00:00.000000001Z", proc="/usr/bin/x",
       padre="/usr/bin/sudo", fichero="/etc/argus-pki/a.key", usuario="root"):
    return json.dumps({"hostname": "vm", "priority": prio, "rule": regla, "source": "syscall", "time": t,
                       "output_fields": {"proc.exepath": proc, "proc.pexepath": padre, "fd.name": fichero,
                                         "user.name": usuario}})


CRIT = ev("argus_lab_clave_leida_ajeno", "Critical", proc="/usr/bin/cat")
SONDA = ev(fs.REGLA_SONDA, "Warning", proc="/usr/bin/cat", padre="/usr/sbin/runuser", fichero=CLAVE, usuario="nobody")


def directorio(actual, rotados=None):
    """Directorio de eventos: actual = líneas de eventos.json; rotados = {sufijo: líneas} (.gz se comprime)."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, fs.BASE), "w", encoding="utf-8") as f:
        f.write("".join(l + "\n" for l in actual))
    for suf, lineas in (rotados or {}).items():
        texto = "".join(l + "\n" for l in lineas)
        r = os.path.join(d, fs.BASE + suf)
        if suf.endswith(".gz"):
            with gzip.open(r, "wt", encoding="utf-8") as f:
                f.write(texto)
        else:
            with open(r, "w", encoding="utf-8") as f:
                f.write(texto)
    return d


def medir(d, falco_escribe=True, estado="active", clave=CLAVE, nobody_lee=False, es_root=True, **kw):
    """«medir» con lo de fuera simulado. falco_escribe: al lanzar la sonda, «Falco» añade su evento al fichero."""
    def lanzar(ruta):
        if falco_escribe:
            with open(os.path.join(d, fs.BASE), "a", encoding="utf-8") as f:
                f.write(ev(fs.REGLA_SONDA, "Warning", fichero=ruta, usuario="nobody") + "\n")
        return not nobody_lee
    rc, sal = fs.medir(directorio=d, es_root=es_root, estado=lambda: estado, elegir=lambda: clave, lanzar=lanzar,
                       dormir=lambda s: None, vm="vm-prueba", espera_s=1, **kw)
    return rc, fs.campos_de(sal[0]), sal


class Cuenta(unittest.TestCase):
    def test_clasifica_por_regla_y_prioridad(self):
        r = fs.Resumen()
        fs.contar([ev(), ev(), CRIT, SONDA, ev("argus_x", "Alert"), ev("argus_x", "Emergency"), ev("argus_x", "Error"),
                   ev("argus_x", "Informational"), ev("Read sensitive file untrusted", "Critical"), "", "  "], r)
        self.assertEqual((r.lineas, r.critical, r.warning, r.notice, r.otras, r.ajenas, r.malas),
                         (9, 3, 2, 2, 1, 1, 0))

    def test_una_critical_ajena_no_cuenta_como_argus(self):
        r = fs.Resumen()
        fs.contar([ev("Read sensitive file untrusted", "Critical")], r)
        self.assertEqual((r.critical, r.ajenas), (0, 1))

    def test_lineas_rotas_son_malas(self):
        r = fs.Resumen()
        fs.contar(["{no json", "[1, 2]", json.dumps({"rule": "argus_x"}), json.dumps({"rule": "argus_x", "priority": 3}),
                   json.dumps({"rule": "argus_x", "priority": "Critical", "time": "ayer"})], r)
        self.assertEqual((r.lineas, r.malas, r.critical), (5, 5, 0))

    def test_desde_deja_fuera_lo_anterior_y_no_lo_posterior(self):
        r = fs.Resumen()
        viejo = ev("argus_lab_clave_leida_ajeno", "Critical", t="2026-11-14T04:47:00.000000000Z")
        justo = ev("argus_lab_clave_leida_ajeno", "Critical", t="2026-11-15T05:00:00.000000000Z")
        fs.contar([viejo, justo], r, "2026-11-15T05:00:00Z")
        self.assertEqual((r.anteriores, r.critical), (1, 1))

    def test_grupos_por_proceso_padre_fichero_usuario(self):
        r = fs.Resumen()
        fs.contar([CRIT, CRIT, ev("argus_lab_clave_leida_ajeno", "Critical", proc="/usr/bin/tar")], r)
        self.assertEqual(sorted(g[0] for g in r.grupos.values()), [1, 2])


class Medir(unittest.TestCase):
    def test_silencio(self):
        rc, c, sal = medir(directorio([ev(), ev()]))
        self.assertEqual((rc, c["veredicto"], c["critical"], c["warning"], c["notice"], c["motivo"], c["sonda"]),
                         (0, "SILENCIO", "0", "1", "2", "-", CLAVE))
        self.assertTrue(any(l.startswith("SILENCIO-NOTICE|n=2|") for l in sal))

    def test_una_critical_es_ruido(self):
        rc, c, sal = medir(directorio([ev(), CRIT]))
        self.assertEqual((rc, c["veredicto"], c["critical"]), (1, "RUIDO", "1"))
        self.assertTrue(any(l.startswith("SILENCIO-GRUPO|nivel=critical|n=1|regla=argus_lab_clave_leida_ajeno|"
                                         "proc=/usr/bin/cat|") for l in sal))

    def test_critical_en_un_rotado_es_ruido(self):
        rc, c, _ = medir(directorio([ev()], {".1": [CRIT]}))
        self.assertEqual((rc, c["veredicto"], c["critical"], c["ficheros"]), (1, "RUIDO", "1", "2"))

    def test_critical_en_un_gz_es_ruido(self):
        rc, c, _ = medir(directorio([ev()], {".1": [ev()], ".2.gz": [CRIT, CRIT]}))
        self.assertEqual((rc, c["veredicto"], c["critical"], c["ficheros"]), (1, "RUIDO", "2", "3"))

    def test_gz_roto_no_medido(self):
        d = directorio([ev()])
        with open(os.path.join(d, fs.BASE + ".2.gz"), "wb") as f:
            f.write(b"esto no es gzip")
        rc, c, _ = medir(d)
        self.assertEqual((rc, c["veredicto"]), (2, "NO-MEDIDO"))

    def test_falco_parado_no_medido(self):
        rc, c, _ = medir(directorio([ev()]), estado="inactive")
        self.assertEqual((rc, c["veredicto"], c["falco"]), (2, "NO-MEDIDO", "inactive"))
        self.assertIn("no está en marcha", c["motivo"])

    def test_falco_parado_con_critical_sigue_siendo_ruido(self):
        rc, c, _ = medir(directorio([CRIT]), estado="failed")
        self.assertEqual((rc, c["veredicto"]), (1, "RUIDO"))
        self.assertIn("no está en marcha", c["motivo"])

    def test_sonda_que_no_aparece_no_medido(self):
        rc, c, _ = medir(directorio([ev()]), falco_escribe=False)
        self.assertEqual((rc, c["veredicto"]), (2, "NO-MEDIDO"))
        self.assertIn("no escribió el evento de la sonda", c["motivo"])

    def test_una_sonda_vieja_no_vale(self):
        # el evento de una sonda ANTERIOR ya está en el fichero: solo cuenta lo escrito después de lanzar esta
        rc, c, _ = medir(directorio([SONDA]), falco_escribe=False)
        self.assertEqual((rc, c["veredicto"]), (2, "NO-MEDIDO"))

    def test_sonda_de_otro_fichero_no_vale(self):
        d = directorio([ev()])

        def lanzar(ruta):
            with open(os.path.join(d, fs.BASE), "a", encoding="utf-8") as f:
                f.write(ev(fs.REGLA_SONDA, "Warning", fichero="/etc/argus-pki/otra.key", usuario="nobody") + "\n")
            return True
        rc, sal = fs.medir(directorio=d, es_root=True, estado=lambda: "active", elegir=lambda: CLAVE, lanzar=lanzar,
                           dormir=lambda s: None, vm="vm", espera_s=1)
        self.assertEqual((rc, fs.campos_de(sal[0])["veredicto"]), (2, "NO-MEDIDO"))

    def test_nobody_lee_la_clave_no_medido(self):
        rc, c, _ = medir(directorio([ev()]), nobody_lee=True)
        self.assertEqual((rc, c["veredicto"]), (2, "NO-MEDIDO"))
        self.assertIn("LEYÓ", c["motivo"])

    def test_sin_clave_para_la_sonda_no_medido(self):
        rc, c, _ = medir(directorio([ev()]), clave=None)
        self.assertEqual((rc, c["veredicto"], c["sonda"]), (2, "NO-MEDIDO", "-"))

    def test_sin_fichero_de_eventos_no_medido(self):
        rc, c, _ = medir(tempfile.mkdtemp())
        self.assertEqual((rc, c["veredicto"], c["ficheros"]), (2, "NO-MEDIDO", "0"))

    def test_sin_root_no_medido(self):
        rc, c, _ = medir(directorio([ev()]), es_root=False)
        self.assertEqual((rc, c["veredicto"]), (2, "NO-MEDIDO"))

    def test_linea_rota_no_medido(self):
        rc, c, _ = medir(directorio([ev(), "{medio evento"]))
        self.assertEqual((rc, c["veredicto"], c["malas"]), (2, "NO-MEDIDO", "1"))

    def test_desde_tapa_la_historia_pero_no_lo_nuevo(self):
        vieja = ev("argus_lab_clave_leida_ajeno", "Critical", t="2026-11-14T04:47:00.000000000Z")
        rc, c, _ = medir(directorio([vieja, ev()]), desde="2026-11-15T00:00:00Z")
        self.assertEqual((rc, c["veredicto"], c["anteriores"], c["critical"]), (0, "SILENCIO", "1", "0"))
        rc, c, _ = medir(directorio([vieja, ev()]))
        self.assertEqual((rc, c["veredicto"], c["critical"]), (1, "RUIDO", "1"))

    def test_valores_sin_barra(self):
        raro = ev("argus_lab_clave_leida_ajeno", "Critical", proc="/tmp/a|b")
        _, _, sal = medir(directorio([raro]))
        self.assertTrue(any("proc=/tmp/a_b|" in l for l in sal))


class Lab(unittest.TestCase):
    def salida(self, lineas, ruido=("[argus] aviso de vagrant",)):
        return "\r\n".join(list(ruido) + lineas) + "\r\n"

    def vm(self, **kw):
        rc, _, sal = medir(directorio(kw.pop("eventos", [ev()])), **kw)
        return rc, self.salida(sal)

    def lab(self, respuestas, vms=("defender", "control-1")):
        visto, pintado = [], []

        def ejecutar(orden):
            visto.append(orden)
            return respuestas[orden[2]]
        rc = fs.lab(list(vms), ejecutar=ejecutar, pinta=pintado.append)
        return rc, visto, "\n".join(pintado)

    def test_todas_en_silencio_pasa(self):
        rc, visto, txt = self.lab({"defender": self.vm(), "control-1": self.vm()})
        self.assertEqual(rc, 0)
        self.assertIn("PASA: 0 CRITICAL de reglas argus_* en las 2 VMs (defender control-1)", txt)
        self.assertEqual([o[:4] for o in visto], [["vagrant", "ssh", "defender", "-c"], ["vagrant", "ssh", "control-1", "-c"]])
        self.assertEqual(visto[0][4], "sudo python3 -I /vagrant/scripts/vigilancia/falco_silencio.py medir --espera-s 10")

    def test_una_vm_con_ruido_falla_y_se_miden_todas(self):
        rc, visto, txt = self.lab({"defender": self.vm(eventos=[CRIT, CRIT]), "control-1": self.vm()})
        self.assertEqual((rc, len(visto)), (1, 2))
        self.assertIn("FALLA: 2 CRITICAL de reglas argus_* (defender)", txt)
        self.assertIn("argus_lab_clave_leida_ajeno proc=/usr/bin/cat", txt)

    def test_una_vm_sin_medir_falla(self):
        rc, _, txt = self.lab({"defender": self.vm(), "control-1": self.vm(estado="inactive")})
        self.assertEqual(rc, 1)
        self.assertIn("sin medir: control-1", txt)

    def test_vm_que_no_contesta_falla(self):
        for resp in ((124, ""), (127, ""), (255, "ssh: connect to host\r\n"), (0, "")):
            rc, _, txt = self.lab({"defender": self.vm(), "control-1": resp})
            self.assertEqual(rc, 1, resp)
            self.assertIn("sin medir: control-1", txt)

    def test_salida_incoherente_falla(self):
        _, buena = self.vm()
        casos = {
            "rc 0 con RUIDO": (0, self.vm(eventos=[CRIT])[1]),
            "rc 1 con SILENCIO": (1, buena),
            "SILENCIO con critical": (0, buena.replace("|critical=0|", "|critical=3|")),
            "SILENCIO con motivo": (0, buena.replace("|motivo=-|", "|motivo=algo|")),
            "dos resúmenes": (0, buena + buena),
            "veredicto inventado": (0, buena.replace("veredicto=SILENCIO", "veredicto=VALE")),
            "critical no numérico": (0, buena.replace("|critical=0|", "|critical=cero|")),
        }
        for nombre, resp in casos.items():
            rc, _, txt = self.lab({"defender": self.vm(), "control-1": resp})
            self.assertEqual(rc, 1, nombre)
            self.assertIn("sin medir: control-1", txt, nombre)

    def test_desde_y_espera_llegan_a_la_vm(self):
        visto = []

        def ejecutar(orden):
            visto.append(orden)
            return self.vm()
        fs.lab(["defender"], "2026-11-15T05:00:00Z", 30, ejecutar=ejecutar, pinta=lambda s: None)
        self.assertTrue(visto[0][4].endswith("medir --espera-s 30 --desde 2026-11-15T05:00:00Z"))


class Argumentos(unittest.TestCase):
    def test_buenos(self):
        self.assertEqual(fs.argumentos(["--desde", "2026-11-15T05:00:00Z", "--espera-s", "60", "defender"]),
                         ("2026-11-15T05:00:00Z", 60, ["defender"]))
        self.assertEqual(fs.argumentos(["a", "b"]), (None, fs.ESPERA_DEF, ["a", "b"]))

    def test_malos_dicen_campo_formato_y_limites(self):
        for a, trozo in ((["--desde", "ayer"], "AAAA-MM-DDTHH:MM:SSZ"), (["--desde", "2026-11-15 05:00:00"], "--desde"),
                         (["--espera-s", "0"], "[1, 60]"), (["--espera-s", "61"], "[1, 60]"),
                         (["--espera-s", "x"], "[1, 60]"), (["--espera-s"], "falta el valor"),
                         (["--sin-sonda"], "desconocida")):
            with self.assertRaises(ValueError) as c:
                fs.argumentos(a)
            self.assertIn(trozo, str(c.exception), a)

    def test_main_rechaza_sin_medir(self):
        import contextlib
        import io
        for a in ([], ["otra"], ["lab"], ["lab", "Defender"], ["lab", "a", "a"], ["medir", "sobra"],
                  ["lab", "--sin-sonda", "defender"]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fs.main(a), 2, a)


if __name__ == "__main__":
    unittest.main(verbosity=2)
