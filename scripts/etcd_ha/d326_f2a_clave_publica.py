#!/usr/bin/env python3
# d326_f2a_clave_publica.py — DAY326, F2a de DEBT-FALCO-RUIDO-ADMIN-001 [CLAVE-PUBLICA-D326] (PR2b de
# DEBT-ETCD-HA-TLS-RAFT-001). Regenerado DAY326 sobre 627885d5e: el d325_f2a_clave_publica.py de DAY325 no llegó al Mac.
# La clave pública del manifiesto la lee argus-infra con su propio cliente de Vault (orden nueva clave-publica), no
# protegidos_pubkey_vm.sh con curl (decisión de Alonso DAY325). Toca:
#   - tools/argus-infra/argus-infra.py: Vault.clave_publica() y la orden clave-publica (solo Ed25519 de 32 bytes).
#   - tools/argus-infra/test_argus_infra.py: 3 tests nuevos (25 en total), sin red.
#   - scripts/etcd_ha/protegidos_pubkey.sh: llama a sudo /usr/local/sbin/argus-infra clave-publica; si el instalado es
#     anterior a la orden, lo dice y da el comando.
# scripts/etcd_ha/protegidos_pubkey_vm.sh (el del curl) se borra aparte con git rm.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d326_f2a_clave_publica.py --check | --apply
# Todo o nada: sha256 de partida, cada ancla exactamente una vez y sha256 del resultado antes de escribir. Idempotente.
import hashlib
import os
import sys

TAG = "[D326-F2A]"
FICHEROS = ('tools/argus-infra/argus-infra.py', 'tools/argus-infra/test_argus_infra.py', 'scripts/etcd_ha/protegidos_pubkey.sh')
INICIO = {'tools/argus-infra/argus-infra.py': '7cda47a8f1e845b92ccf22b225666a43ec85d04ece51d45b92c8e94c28575bdc', 'tools/argus-infra/test_argus_infra.py': 'b3c383d0f2d7bb69856dcd86eed9dba185bb7a60d7c5952255ecc32a006e65bc', 'scripts/etcd_ha/protegidos_pubkey.sh': 'e98e3dde6ae853d18a16bf912c7f9993d33bcf5a5254fe71703ff29f5c4e439d'}
FINAL = {'tools/argus-infra/argus-infra.py': '77ca95efc2245f785bb90dadff3aaa83d54f09e8729240c1a29ef7bcf206a7a9', 'tools/argus-infra/test_argus_infra.py': '3ba15f9d4396d50d3f3b6d1ad24a8fc52e9aa1bc723c2e9ddd3acf62e2dd107d', 'scripts/etcd_ha/protegidos_pubkey.sh': '330c5a132691801d3ae9e5141e2f8fd2075e888fd46543824c95ad794c3317b6'}
CAMBIOS = {
    'tools/argus-infra/argus-infra.py': [('#   argus-infra [-c CONFIG] verificar [--version N]\n', '#   argus-infra [-c CONFIG] verificar [--version N]\n#   argus-infra [-c CONFIG] clave-publica\n'), ('    def revocar(self):\n        if not self.token:\n', '    def clave_publica(self):\n        """(versión más reciente, 64 hex) de la clave PÚBLICA transit del manifiesto. [CLAVE-PUBLICA-D326] La pública no\n        es un secreto; la privada nunca sale de Vault (exportable=false). Solo una Ed25519 de 32 bytes."""\n        st, datos = self.h.pedir("GET", f"/v1/{self.montaje}/keys/{self.clave}", None, {"X-Vault-Token": self.token})\n        if st != 200:\n            raise self._error(f"lectura de {self.montaje}/keys/{self.clave}", st, datos)\n        j = _json_o_nada(datos)\n        d = j.get("data") if isinstance(j, dict) else None\n        if not isinstance(d, dict):\n            raise Fallo("[ARGUS-INFRA-VAULT] respuesta de la clave sin data")\n        if d.get("type") != "ed25519":\n            raise Fallo(f"[ARGUS-INFRA-VAULT] la clave {self.clave} es de tipo \'{saneado(str(d.get(\'type\')))}\': "\n                        "se exige ed25519")\n        v = d.get("latest_version")\n        try:\n            if not es_entero(v) or v < 1:\n                raise ValueError\n            pk = base64.b64decode(d["keys"][str(v)]["public_key"], validate=True)\n        except (KeyError, TypeError, ValueError, binascii.Error):\n            raise Fallo("[ARGUS-INFRA-VAULT] respuesta de la clave sin la pública de su versión más reciente") \\\n                from None\n        if len(pk) != 32:\n            raise Fallo(f"[ARGUS-INFRA-VAULT] clave pública de {len(pk)} bytes: se esperan 32 (Ed25519)")\n        return v, pk.hex()\n\n    def revocar(self):\n        if not self.token:\n'), ('def canonico(cidr):\n', 'def orden_clave_publica(ses, a):\n    """[CLAVE-PUBLICA-D326] La clave PÚBLICA del manifiesto, para compilarla en el firewall (make protegidos-pubkey).\n    Tres líneas CLAVE=valor que lee scripts/etcd_ha/protegidos_pubkey.sh. Sustituye a protegidos_pubkey_vm.sh, que\n    hacía lo mismo con curl (decisión de Alonso DAY325: sin curl; Falco conoce a argus-infra, no a un curl)."""\n    v, pk = ses.vault.clave_publica()\n    registrar(f"PROTEGIDOS_CLAVE={ses.cfg[\'vault\'][\'clave\']}")\n    registrar(f"PROTEGIDOS_VERSION={v}")\n    registrar(f"PROTEGIDOS_PUBKEY_HEX={pk}")\n    return SALIDA_OK\n\n\ndef canonico(cidr):\n'), ('    p = sub.add_parser("deshacer", help="firma como versión nueva el contenido de la versión N (D4)")\n', '    sub.add_parser("clave-publica", help="imprime la clave pública del manifiesto (la de Vault transit), en hex")\n    p = sub.add_parser("deshacer", help="firma como versión nueva el contenido de la versión N (D4)")\n'), ('           "verificar": orden_verificar, "deshacer": orden_deshacer}\n', '           "verificar": orden_verificar, "deshacer": orden_deshacer, "clave-publica": orden_clave_publica}\n')],
    'tools/argus-infra/test_argus_infra.py': [('\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n', '\n\nclass ClavePublica(unittest.TestCase):\n    """[CLAVE-PUBLICA-D326] clave-publica lee la clave transit con el cliente de Vault (sin red: se simula la respuesta\n    HTTPS) e imprime las tres líneas que lee protegidos_pubkey.sh; no acepta otra cosa que una Ed25519 de 32 bytes."""\n    PK = bytes(range(32))\n\n    def vault(self, status=200, data=None, crudo=None):\n        import types\n        v = ai.Vault.__new__(ai.Vault)\n        v.montaje, v.clave, v.token = "argus-transit", "protegidos-hospital-lab", "t"\n        self.pedidos = []\n        cuerpo = crudo if crudo is not None else json.dumps({"data": data}).encode()\n        v.h = types.SimpleNamespace(pedir=lambda m, r, c, cab: self.pedidos.append((m, r, cab)) or (status, cuerpo))\n        return v\n\n    def data(self, **kw):\n        d = {"type": "ed25519", "latest_version": 2,\n             "keys": {"1": {"public_key": base64.b64encode(b"x" * 32).decode()},\n                      "2": {"public_key": base64.b64encode(self.PK).decode()}}}\n        d.update(kw)\n        return d\n\n    def falla(self, texto, **kw):\n        with self.assertRaises(ai.Fallo) as c:\n            self.vault(**kw).clave_publica()\n        self.assertIn(texto, str(c.exception))\n\n    def test_devuelve_la_version_mas_reciente_en_hex(self):\n        v = self.vault(data=self.data())\n        self.assertEqual(v.clave_publica(), (2, self.PK.hex()))\n        self.assertEqual(self.pedidos, [("GET", "/v1/argus-transit/keys/protegidos-hospital-lab", {"X-Vault-Token": "t"})])\n\n    def test_rechaza_lo_que_no_es_una_ed25519_de_32_bytes(self):\n        self.falla("se exige ed25519", data=self.data(type="rsa-2048"))\n        self.falla("31 bytes", data=self.data(keys={"2": {"public_key": base64.b64encode(b"x" * 31).decode()}}))\n        self.falla("sin la pública", data=self.data(latest_version=3))\n        self.falla("sin la pública", data=self.data(latest_version="2"))\n        self.falla("sin la pública", data=self.data(latest_version=True))\n        self.falla("sin la pública", data=self.data(keys={"2": {"public_key": "no es base64 !"}}))\n        self.falla("sin data", crudo=b"no es json")\n        self.falla("HTTP 403", status=403, crudo=b\'{"errors":["permission denied"]}\')\n\n    def test_orden_imprime_las_tres_lineas(self):\n        import contextlib\n        import io\n        import types\n        ses = types.SimpleNamespace(cfg={"vault": {"clave": "protegidos-hospital-lab"}},\n                                    vault=self.vault(data=self.data()))\n        out = io.StringIO()\n        with contextlib.redirect_stdout(out):\n            rc = ai.orden_clave_publica(ses, None)\n        self.assertEqual(rc, ai.SALIDA_OK)\n        self.assertEqual(out.getvalue().splitlines(),\n                         ["PROTEGIDOS_CLAVE=protegidos-hospital-lab", "PROTEGIDOS_VERSION=2",\n                          "PROTEGIDOS_PUBKEY_HEX=" + self.PK.hex()])\n        self.assertEqual(ai.analizar(["clave-publica"]).orden, "clave-publica")\n        self.assertIs(ai.ORDENES["clave-publica"], ai.orden_clave_publica)\n\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n')],
    'scripts/etcd_ha/protegidos_pubkey.sh': [('CRUDO=$(vagrant ssh control-1 -c "sudo bash /vagrant/scripts/etcd_ha/protegidos_pubkey_vm.sh" 2>/tmp/argus_protegidos_pubkey_err.txt)\n', '# [CLAVE-PUBLICA-D326] la lee argus-infra (orden clave-publica, cliente de Vault en Python estándar) con su propio\n# certificado; antes era protegidos_pubkey_vm.sh con curl (CRITICAL de Falco, y curl no puede existir en producción)\nCRUDO=$(vagrant ssh control-1 -c "sudo /usr/local/sbin/argus-infra clave-publica" 2>/tmp/argus_protegidos_pubkey_err.txt)\n'), ('  cat /tmp/argus_protegidos_pubkey_err.txt >&2\n  falla "no se pudo leer la clave pública de la VM etcd (rc=$RC; arriba el error de la VM)"\n', '  cat /tmp/argus_protegidos_pubkey_err.txt >&2\n  printf \'%s\\n\' "$SAL" | grep -E \'^\\[ARGUS-INFRA|^argus-infra: |^usage: \' >&2\n  if printf \'%s\\n\' "$SAL" | grep -q "invalid choice: \'clave-publica\'" || grep -q "invalid choice: \'clave-publica\'" /tmp/argus_protegidos_pubkey_err.txt; then\n    falla "el argus-infra instalado en control-1 es anterior a la orden clave-publica: vagrant provision control-1 --provision-with argus-infra"\n  fi\n  falla "no se pudo leer la clave pública de la VM etcd (rc=$RC; arriba el error de la VM)"\n')],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(f"{TAG} uso: python3 -I scripts/etcd_ha/d326_f2a_clave_publica.py --check | --apply", file=sys.stderr)
        return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print(f"{TAG} FALLA: ejecútalo desde la raíz del repo", file=sys.stderr)
        return 1
    nuevos, ya = {}, 0
    for p in FICHEROS:
        b = open(p, "rb").read()
        h = sha(b)
        if h == FINAL[p]:
            print(f"{TAG} {p}: ya aplicado")
            ya += 1
            continue
        if h != INICIO[p]:
            print(f"{TAG} FALLA: {p} sha256 {h} no es el de partida {INICIO[p]} ni el final {FINAL[p]}; nada escrito",
                  file=sys.stderr)
            return 1
        s = b.decode("utf-8")
        for i, (a, n) in enumerate(CAMBIOS[p]):
            c = s.count(a)
            if c != 1:
                print(f"{TAG} FALLA: {p} ancla {i} aparece {c} veces (se exige 1); nada escrito", file=sys.stderr)
                return 1
            s = s.replace(a, n)
        r = s.encode("utf-8")
        if sha(r) != FINAL[p]:
            print(f"{TAG} FALLA: {p} resultado {sha(r)} no es el esperado {FINAL[p]}; nada escrito", file=sys.stderr)
            return 1
        nuevos[p] = r
        print(f"{TAG} {p}: {len(CAMBIOS[p])} anclas, una vez cada una; resultado {FINAL[p][:16]}")
    if sys.argv[1] == "--check":
        print(f"{TAG} CHECK OK: {len(nuevos)} por aplicar, {ya} ya aplicados")
        return 0
    for p, r in nuevos.items():
        modo = os.stat(p).st_mode
        tmp = p + ".d326tmp"
        with open(tmp, "wb") as f:
            f.write(r)
        os.chmod(tmp, modo)
        os.replace(tmp, p)
    print(f"{TAG} APLICADO: {len(nuevos)} escritos, {ya} ya estaban. Siguiente: git rm scripts/etcd_ha/protegidos_pubkey_vm.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
