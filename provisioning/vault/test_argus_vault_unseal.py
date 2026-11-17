#!/usr/bin/python3 -I
# test_argus_vault_unseal.py — [DESELLADO-PY-D326] tests del desellado del Vault del lab (provisioning/vault/
# argus-vault-unseal) con la biblioteca estándar (unittest), sin red ni Vault: las peticiones HTTPS se simulan. Prueban
# la espera a que Vault responda, Vault sin inicializar, el desellado con la clave del fichero y que la clave nunca sale
# por la salida. El desellado real lo prueban el arranque de la VM y lab-e2e-vigilancia (C7).
#   python3 -I provisioning/vault/test_argus_vault_unseal.py      (make test-vault-unseal, en control-1)
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True  # se ejecuta desde /vagrant: sin __pycache__ en el repo
AQUI = os.path.dirname(os.path.abspath(__file__))
_l = importlib.machinery.SourceFileLoader("argus_vault_unseal", os.path.join(AQUI, "argus-vault-unseal"))
_spec = importlib.util.spec_from_loader("argus_vault_unseal", _l)
du = importlib.util.module_from_spec(_spec)
_l.exec_module(du)

CLAVE = "IXyR0OJnSFobekZMMCKCoVEpT7wI6l+USMzE3IcyDyo="


class Vault:
    """Vault simulado: no responde las primeras `mudo` veces; luego contesta según su estado."""

    def __init__(self, mudo=0, inicializado=True, sellado=True, desella=True, status_unseal=200):
        self.mudo, self.inicializado, self.sellado = mudo, inicializado, sellado
        self.desella, self.status_unseal = desella, status_unseal
        self.pedidos = []

    def pedir(self, metodo, ruta, cuerpo, timeout_s):
        self.pedidos.append((metodo, ruta, cuerpo, timeout_s))
        if ruta == "/v1/sys/seal-status":
            if self.mudo > 0:
                self.mudo -= 1
                raise du.Fallo("[Errno 111] Connection refused")
            return 200, {"initialized": self.inicializado, "sealed": self.sellado}
        if ruta == "/v1/sys/unseal" and metodo == "PUT":
            if self.desella and json.loads(cuerpo) == {"key": CLAVE}:
                self.sellado = False
            return self.status_unseal, {"sealed": self.sellado}
        return 404, None


def correr(v, clave=CLAVE):
    pausas = []
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = du.main(pedir=v.pedir, dormir=pausas.append, leer_clave=lambda: clave)
    return rc, out.getvalue(), pausas


class Desellado(unittest.TestCase):
    def test_sellado_se_dessella_con_la_clave_del_fichero_en_el_cuerpo(self):
        v = Vault()
        rc, out, _ = correr(v)
        self.assertEqual((rc, out), (0, "[VAULT-UNSEAL] Vault desellado\n"))
        puts = [p for p in v.pedidos if p[0] == "PUT"]
        self.assertEqual(puts, [("PUT", "/v1/sys/unseal", json.dumps({"key": CLAVE}).encode(), du.TIMEOUT_DESELLO_S)])

    def test_ya_desellado_no_manda_la_clave(self):
        v = Vault(sellado=False)
        rc, out, _ = correr(v)
        self.assertEqual((rc, out), (0, "[VAULT-UNSEAL] Vault desellado\n"))
        self.assertFalse([p for p in v.pedidos if p[0] == "PUT"])

    def test_sin_inicializar_no_hace_nada(self):
        v = Vault(inicializado=False)
        rc, out, _ = correr(v)
        self.assertEqual(rc, 0)
        self.assertIn("Vault sin inicializar", out)
        self.assertFalse([p for p in v.pedidos if p[0] == "PUT"])

    def test_espera_a_que_vault_responda(self):
        v = Vault(mudo=5)
        rc, out, pausas = correr(v)
        self.assertEqual(rc, 0)
        self.assertEqual(pausas, [du.PAUSA_S] * 5)

    def test_vault_mudo_falla_tras_los_intentos(self):
        v = Vault(mudo=10 ** 6)
        rc, out, pausas = correr(v)
        self.assertEqual(rc, 1)
        self.assertIn("FALLA: Vault no responde en 30 s", out)
        self.assertIn("Connection refused", out)
        self.assertEqual(len(pausas), du.INTENTOS - 1)

    def test_sin_clave_falla_y_no_pide_desellar(self):
        v = Vault()
        rc, out, _ = correr(v, clave="")
        self.assertEqual(rc, 1)
        self.assertIn("FALLA: sellado y sin /etc/vault.d/unseal.key", out)
        self.assertFalse([p for p in v.pedidos if p[0] == "PUT"])

    def test_clave_mala_sigue_sellado_y_la_clave_no_sale_por_la_salida(self):
        v = Vault(desella=False, status_unseal=400)
        rc, out, _ = correr(v)
        self.assertEqual(rc, 1)
        self.assertIn("FALLA: sigue sellado", out)
        self.assertIn("AVISO: sys/unseal respondió 400", out)
        self.assertNotIn(CLAVE, out)
        self.assertNotIn(CLAVE[:12], out)

    def test_leer_clave_quita_el_salto_y_da_vacio_si_no_existe(self):
        import tempfile
        d = tempfile.mkdtemp()
        r = os.path.join(d, "unseal.key")
        with open(r, "w") as f:
            f.write(CLAVE + "\n")
        self.assertEqual(du.leer_clave(r), CLAVE)
        self.assertEqual(du.leer_clave(os.path.join(d, "no-existe")), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
