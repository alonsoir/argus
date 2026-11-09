#!/usr/bin/env python3
# [ARGUS-GATE-PERF-D321] DAY321: make test-firewall excluye e2e|root|perf (como test-components). Medido en el
# banco (ctest -N): con -LE "e2e" entraban 97 tests y los dos IPSetWrapperPerfTest salían Skipped por falta de root; con
# -LE "e2e|root|perf" entran 95 y salen exactamente esos dos, que siguen en make test-firewall-perf (root, su puerta).
# Solo Makefile.
# Uso (raíz del repo): python3 -I d321_test_firewall_perf.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'Makefile', 'antes': 'cc6e01b9487387712d54590392c96fd4a2a77725cdfa2035269f38ab1d5fa9de', 'despues': 'a8f9c495eb3860f3463d31a5fa3b002d285008972f258b30e550e1009a534e11', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('# No-root: tests puros del firewall (validacion/parsing). Entra en make test-all.\n# Los tests que tocan ipset real hacen GTEST_SKIP sin root -> \'Skipped\', no \'Failed\'.\ntest-firewall:\n\t@echo "🧪 firewall tests (perfil=$(PROFILE), sin root)"\n\t@vagrant ssh -c \'cd $(FIREWALL_BUILD_DIR) && \\\n\t\tLD_LIBRARY_PATH=/usr/local/lib \\\n\t\tctest -LE "e2e" --output-on-failure\'\n\n# e2e/root: integracion contra ipset real (canario de inyeccion H-2). Solo VM, con sudo.\n',
             '# No-root: tests puros del firewall (validacion/parsing). Entra en make test-all.\n# Los tests que tocan ipset real hacen GTEST_SKIP sin root -> \'Skipped\', no \'Failed\'.\n# [ARGUS-GATE-PERF-D321] sin root: fuera e2e, root y perf, como test-components (medido DAY321: con -LE "e2e" los dos\n# IPSetWrapperPerfTest salían Skipped por falta de root). Los perf corren en test-firewall-perf, con root y su puerta.\ntest-firewall:\n\t@echo "🧪 firewall tests (perfil=$(PROFILE), sin root; e2e/root en test-firewall-e2e, perf en test-firewall-perf)"\n\t@vagrant ssh -c \'cd $(FIREWALL_BUILD_DIR) && \\\n\t\tLD_LIBRARY_PATH=/usr/local/lib \\\n\t\tctest -LE "e2e|root|perf" --output-on-failure\'\n\n# e2e/root: integracion contra ipset real (canario de inyeccion H-2). Solo VM, con sudo.\n'),
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
