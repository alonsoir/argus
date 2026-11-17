#!/usr/bin/env python3
# [CLAVE-PTY-D327] DAY327: mitre_start.sh y ctu_start.sh se quedan solo con la línea de 64 hex de clave_bronce.py.
# Lanzados desde una terminal, vagrant ssh abre pty y el stderr de la VM llega en el stdout (len=270 en vez de 64).
# Va sobre el mitre_start.sh de d327_correlates.py (sha256 0f6a65f6...).
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_clave_pty.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/mitre_start.sh', 'antes': '0f6a65f6cd0ad86399f0703974ce9d1c7a060625a5dba3b0ad8f748f238fc588', 'despues': 'd9c48bc40215091de7afde97d1e1d885fe073abaf653376a10beb6a282175830', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('KEY=$(vagrant ssh defender -c "sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector" 2>/dev/null | tr -d \'\\r\')\n',
             '# [CLAVE-PTY-D327] con terminal, vagrant ssh da pty y el stderr de la VM (las líneas [CONFIG] de clave_bronce.py)\n# llega mezclado en el stdout: len=270 (medido DAY327, make mitre-check en primer plano; en EMECAS, sin terminal,\n# salía bien). Se queda solo la línea de 64 hex; si hay más de una, la longitud no cuadra y para.\nKEY=$(vagrant ssh defender -c "sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector" 2>/dev/null | tr -d \'\\r\' | grep -E \'^[0-9a-f]{64}$\')\n'),
        ],
    },
    {
        'ruta': 'scripts/ctu_start.sh', 'antes': '32b5e17392db1a1c3bc73e71220bae7b4aeb195e41718a810b860ec2fea7b1bf', 'despues': '25c0e6d957bd33faf55724cd6f4bc34dcc3e808b292a704ce3df32e74bf4fe30', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('KEY=$(vagrant ssh defender -c "sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector" 2>/dev/null | tr -d \'\\r\')\n',
             '# [CLAVE-PTY-D327] con terminal, vagrant ssh da pty y el stderr de la VM (las líneas [CONFIG] de clave_bronce.py)\n# llega mezclado en el stdout: len=270 (medido DAY327, make mitre-check en primer plano; en EMECAS, sin terminal,\n# salía bien). Se queda solo la línea de 64 hex; si hay más de una, la longitud no cuadra y para.\nKEY=$(vagrant ssh defender -c "sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector" 2>/dev/null | tr -d \'\\r\' | grep -E \'^[0-9a-f]{64}$\')\n'),
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
