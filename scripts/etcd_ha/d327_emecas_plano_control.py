#!/usr/bin/env python3
# [EMECAS-PLANO-CONTROL-D327] DAY327, DEBT-EMECAS-PLANO-CONTROL-001 (PR2b de DEBT-ETCD-HA-TLS-RAFT-001): test-etcd-cluster
# y test-etcd-reinicio entran en la receta emecas del Makefile, tras test-argus-infra (antes de falco-silencio y de
# lab-e2e). Va sobre el Makefile de F2g (sha256 8ee762a5...).
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_emecas_plano_control.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'Makefile', 'antes': '8ee762a5304988596a297d62fd93168e4f1f7642a3e50ab9ed6d69ec341b2661', 'despues': '876648f52cbdbd65869583441fdf459a691ea0f29c54c1e970331739ff2818fb', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('\t@$(EMECAS_PASO) test-argus-infra -- $(MAKE) test-argus-infra\n',
             '\t@$(EMECAS_PASO) test-argus-infra -- $(MAKE) test-argus-infra\n\t@# [EMECAS-PLANO-CONTROL-D327] DEBT-EMECAS-PLANO-CONTROL-001 (decisión de Alonso DAY326): el clúster etcd de verdad y\n\t@# su reinicio de uno en uno, en cada EMECAS. Medido DAY327: 55 s y 198 s; 0 CRITICAL de Falco; sus trazas Notice\n\t@# (495 en control-1) quedan antes de falco-silencio y fuera de la ventana de C8 de lab-e2e-vigilancia\n\t@$(EMECAS_PASO) test-etcd-cluster -- $(MAKE) test-etcd-cluster\n\t@$(EMECAS_PASO) test-etcd-reinicio -- $(MAKE) test-etcd-reinicio\n'),
            ('# durante los reinicios (quórum) y 0 CRITICAL de Falco de reglas argus_* en todos los nodos [FALCO-SILENCIO-D325]\n',
             '# durante los reinicios (quórum) y 0 CRITICAL de Falco de reglas argus_* en todos los nodos [FALCO-SILENCIO-D325].\n# Entorno: ETCD_REINICIO_HB_MS, ETCD_REINICIO_EL_MS y ETCD_REINICIO_ESCRITOR_S (pausa del escritor, [1, 10], defecto 2)\n'),
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
