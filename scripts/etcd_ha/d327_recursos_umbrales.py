#!/usr/bin/env python3
# [RECURSOS-UMBRALES-D327] DAY327: umbrales de recursos del anfitrión corregidos con lo medido al usarlos. Con los
# primeros (ec2e3f4e1) EMECAS no arrancó tras el destroy por swap 1505 MB > 1024 (resto del lab recién destruido) con
# carga 7,82 (máximo 8), y el perfil lab_e2e falló con el lab sano por swap 7207 MB > 5120. Ahora: carga a 5 min 12 en
# los dos perfiles; swap 4096 MB (emecas) y 16384 MB (lab_e2e, solo un techo: el swap no separa sano de ahogado).
# Cambian a la vez el JSON, los defectos del código (son los mismos valores) y los tests (16).
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_recursos_umbrales.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/emecas/recursos_anfitrion.py', 'antes': '39f9415614e0fbaffc2b07c5689b3d95db274169306e5973a953c07cc6f34e7b', 'despues': 'c96063d694fde42ab92f1926c53fe60f64a32ca900299190a4a1b576aff6f396', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('#            anterior arriba, el swap y la carga son los del propio lab (3-4 GB de swap con el lab sano) y un umbral de\n#            arranque no dejaría relanzar. Tras el destroy: carga 3,3, swap 0,15 GB, nivel de memoria 84.\n',
             '#            anterior arriba, el swap y la carga son los del propio lab y un umbral de arranque no dejaría relanzar.\n#            Tras el destroy, con el lab antes en reposo: carga 3,3, swap 0,15 GB, nivel 84. Tras el destroy nada\n#            más acabar una corrida: carga 7,8 (la media de 5 min aún baja), swap 1,5 GB (lo que el lab empujó de\n#            otros procesos; de 7,2 GB con el lab), nivel 81. [RECURSOS-UMBRALES-D327]\n'),
            ('#   lab_e2e  el Mac CON el lab arriba (make lab-e2e suelto). Lab sano: carga a 5 min hasta 8,2, swap hasta 4,05 GB,\n#            nivel de memoria mínimo 67, presión 1. Mac ahogado (DAY325, lab-e2e en rojo): carga 46, swap 5,3 GB.\n',
             '#   lab_e2e  el Mac CON el lab arriba (make lab-e2e suelto). Lab sano: carga a 5 min hasta 8,2, swap hasta 7,2 GB,\n#            nivel de memoria mínimo 67, presión 1. Mac ahogado (DAY325, lab-e2e en rojo): carga 46, swap 5,3 GB.\n#            El swap NO separa el Mac sano del ahogado (7,2 GB sano, 5,3 GB ahogado): su umbral es solo un techo.\n#            Separan la carga (8 frente a 46) y la presión de memoria.\n'),
            ('    ("carga_5min_max", "max", 1, 256, 8, 10, "carga a 5 min"),\n    ("swap_usado_mb_max", "max", 0, 65536, 1024, 5120, "swap usado (MB)"),\n',
             '    ("carga_5min_max", "max", 1, 256, 12, 12, "carga a 5 min"),\n    ("swap_usado_mb_max", "max", 0, 65536, 4096, 16384, "swap usado (MB)"),\n'),
        ],
    },
    {
        'ruta': 'scripts/emecas/recursos_anfitrion.json', 'antes': 'bf57cd06e7850b07a2969659f4de02b514363817aa514d691391c8ecd57fb2c1', 'despues': 'ec188979d89d4f794f1cf4a47d6fcc86823a7536b499d37a29172243e0d596b5', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('Sin lab (tras vagrant destroy): carga 3,3, swap 0,15 GB, nivel 84. Lab sano durante EMECAS: carga hasta 8,2, swap hasta 4,05 GB, nivel mínimo 67, presión 1. Mac ahogado (DAY325): carga 46, swap 5,3 GB.",\n',
             'Sin lab (tras vagrant destroy): carga 3,3, swap 0,15 GB, nivel 84; nada más acabar una corrida: carga 7,8, swap 1,5 GB, nivel 81. Lab sano: carga hasta 8,2, swap hasta 7,2 GB, nivel mínimo 67, presión 1. Mac ahogado (DAY325): carga 46, swap 5,3 GB. El swap no separa sano de ahogado: su umbral es un techo; separan la carga y la presión.",\n'),
            ('  "emecas": {\n    "carga_5min_max": 8,\n    "swap_usado_mb_max": 1024,\n',
             '  "emecas": {\n    "carga_5min_max": 12,\n    "swap_usado_mb_max": 4096,\n'),
            ('  "lab_e2e": {\n    "carga_5min_max": 10,\n    "swap_usado_mb_max": 5120,\n',
             '  "lab_e2e": {\n    "carga_5min_max": 12,\n    "swap_usado_mb_max": 16384,\n'),
        ],
    },
    {
        'ruta': 'scripts/emecas/test_recursos_anfitrion.py', 'antes': 'd1cb173caa5439e6e3def4a07d5619796b0aed030a31e0ed49b7f0b1101a9377', 'despues': '382508f3c27eb6fc3e8594f631ecf17765a20dd6c3b26d631127e760828638e6', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('SANO_CON_LAB = {"carga_5min": 8.2, "swap_usado_mb": 4051.75, "presion_memoria": 1, "nivel_memoria": 67, "disco_libre_gb": 167.0}\n',
             'TRAS_UNA_CORRIDA = {"carga_5min": 7.82, "swap_usado_mb": 1505.75, "presion_memoria": 1, "nivel_memoria": 81, "disco_libre_gb": 293.25}\nSANO_CON_LAB = {"carga_5min": 8.2, "swap_usado_mb": 7207.0, "presion_memoria": 1, "nivel_memoria": 67, "disco_libre_gb": 167.0}\n'),
            ('    def test_lab_sano_pasa_lab_e2e_pero_no_emecas(self):\n',
             '    def test_recien_acabada_una_corrida_pasa_emecas(self):\n        # medido DAY327: con los umbrales primeros (carga 8, swap 1024) EMECAS no arrancó tras el destroy\n        self.assertEqual(corre("emecas", TRAS_UNA_CORRIDA)[0], 0)\n\n    def test_lab_sano_pasa_lab_e2e_pero_no_emecas(self):\n'),
            ('        self.assertIn("swap usado (MB): 4051.75 (máximo 1024)", txt)\n',
             '        self.assertIn("swap usado (MB): 7207.00 (máximo 4096)", txt)\n'),
            ('(("carga_5min", 8.0, 8.01), ("swap_usado_mb", 1024.0, 1024.5),\n',
             '(("carga_5min", 12.0, 12.01), ("swap_usado_mb", 4096.0, 4096.5),\n'),
            ('        ruta = config({"emecas": {"carga_5min_max": 2, "swap_usado_mb_max": 1024, "presion_memoria_max": 1,\n',
             '        ruta = config({"emecas": {"carga_5min_max": 2, "swap_usado_mb_max": 4096, "presion_memoria_max": 1,\n'),
            ('        for malo, trozo in (({}, "ausente"), ({"carga_5min_max": "8"}, "\'8\' mal formado"),\n',
             '        for malo, trozo in (({}, "ausente"), ({"carga_5min_max": "12"}, "\'12\' mal formado"),\n'),
            ('            self.assertIn("emecas.carga_5min_max=8 (defecto del código: %s; entero en [1, 256])" % trozo, txt)\n',
             '            self.assertIn("emecas.carga_5min_max=12 (defecto del código: %s; entero en [1, 256])" % trozo, txt)\n'),
            ('        self.assertIn("lab_e2e.carga_5min_max=10 (defecto del código: ausente", txt)\n        self.assertIn("lab_e2e.swap_usado_mb_max=5120 (defecto del código: ausente", txt)\n',
             '        self.assertIn("lab_e2e.carga_5min_max=12 (defecto del código: ausente", txt)\n        self.assertIn("lab_e2e.swap_usado_mb_max=16384 (defecto del código: ausente", txt)\n'),
        ],
    },
]


def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply"); return 2
    aplicar = sys.argv[1] == "--apply"
    if not os.path.isdir(".git"):
        print("[ERROR] ejecutar desde la raíz del repo (no veo .git)"); return 2
    plan, ya, errores = [], 0, 0
    for f in FICHEROS:
        r = f["ruta"]
        if os.path.exists(r):
            actual = open(r, "rb").read()
            h = sha(actual)
            if h == f["despues"]:
                print(f"[YA-APLICADO] {r} {h[:16]}"); ya += 1; continue
            if f["antes"] == "nuevo":
                print(f"[ERROR] {r} existe con otro contenido ({h[:16]}); se esperaba que no existiera"); errores += 1; continue
            if h != f["antes"]:
                print(f"[ERROR] {r} sha256 {h[:16]}, se esperaba {f['antes'][:16]} (antes) o {f['despues'][:16]} (después)"); errores += 1; continue
            t = actual.decode("utf-8")
            for i, (v, n) in enumerate(f["trozos"]):
                if t.count(v) != 1:
                    print(f"[ERROR] {r}: trozo {i + 1} aparece {t.count(v)} veces"); errores += 1; break
                t = t.replace(v, n)
            nb = t.encode("utf-8")
            modo = os.stat(r).st_mode & 0o777
        else:
            if f["antes"] != "nuevo":
                print(f"[ERROR] {r} no existe"); errores += 1; continue
            nb = f["nuevo"].encode("utf-8"); modo = int(f["modo"], 8)
        if sha(nb) != f["despues"]:
            print(f"[ERROR] {r}: el resultado no da el sha256 esperado"); errores += 1; continue
        plan.append((r, nb, modo, f))
        print(f"[APLICABLE] {r} {f['antes'][:16]} -> {f['despues'][:16]} ({len(f['trozos']) if f['nuevo'] is None else 'fichero nuevo'}{' bloques' if f['nuevo'] is None else ''})")
    if errores:
        print(f"[ERROR] {errores} problemas: no se escribe nada"); return 1
    if not plan:
        print(f"[CHECK] todo ya aplicado ({ya} ficheros)"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(plan)} ficheros, {ya} ya aplicados); nada escrito"); return 0
    for r, nb, modo, f in plan:
        d = os.path.dirname(r) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche_")
        with os.fdopen(fd, "wb") as o: o.write(nb)
        os.chmod(tmp, modo)
        os.replace(tmp, r)
        print(f"[APLICADO] {r} sha256={f['despues']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
