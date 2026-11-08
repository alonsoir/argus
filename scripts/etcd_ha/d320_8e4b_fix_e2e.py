#!/usr/bin/env python3
# [PROTEGIDOS-ANTISPOOF-D320] arreglo de d320_antispoof_e2e.sh: vm() devolvía el código del filtro (grep -v de la
# línea [argus] de vagrant), no el del comando remoto; un 'grep -q' remoto que casaba sin salida daba 1 y el E2E paraba
# en el paso 1 (medido en el lab DAY320). Ahora vm() devuelve el código remoto. Solo el script del E2E.
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_8e4b_fix_e2e.py --check
#   python3 -I scripts/etcd_ha/d320_8e4b_fix_e2e.py --apply
# Todo o nada: comprueba el sha256 de cada fichero (y que los nuevos no existan) antes de escribir ninguno.
# Idempotente: si todos tienen ya el sha256 de después, no toca nada. Salidas: 0 bien, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r"""[
 {
  "ruta": "scripts/etcd_ha/d320_antispoof_e2e.sh",
  "antes": "db337c732a02b67ee64c7ca0784322af2844ee9a26353e003935afeb00b99c2e",
  "despues": "3066cc13bd9ccb330a2d9b5f2b117889ab190807ea541f101c1f830a0e45e36d",
  "bloques": [
   {
    "viejo": "pasa()  { echo \"PASA  $*\"; }\nmal()   { echo \"FALLA $*\"; FALLOS=$((FALLOS + 1)); }\nvm()    { vagrant ssh \"$1\" -c \"$2\" 2>/dev/null | tr -d '\\r' | grep -v '^\\[argus\\]'; }\ninfra() { vm etcd \"sudo /usr/local/sbin/argus-infra $1\"; }\ncuenta(){ vm defender \"sudo iptables -w -t raw -L $1 -v -x -n 2>/dev/null | awk 'NR == 4 {print \\$1}'\"; }   # regla 2 = la de cuenta\n",
    "nuevo": "pasa()  { echo \"PASA  $*\"; }\nmal()   { echo \"FALLA $*\"; FALLOS=$((FALLOS + 1)); }\n# vm VM ORDEN: salida sin la línea [argus] de vagrant y con el código de salida DEL COMANDO REMOTO (no del filtro:\n# medido DAY320, con el filtro al final un 'grep -q' remoto sin salida devolvía 1 aunque hubiera casado).\nvm()    { local out rc; out=$(vagrant ssh \"$1\" -c \"$2\" 2>/dev/null); rc=$?\n          [ -n \"$out\" ] && printf '%s\\n' \"$out\" | tr -d '\\r' | grep -v '^\\[argus\\]'; return $rc; }\ninfra() { vm etcd \"sudo /usr/local/sbin/argus-infra $1\"; }\ncuenta(){ vm defender \"sudo iptables -w -t raw -L $1 -v -x -n 2>/dev/null | awk 'NR == 4 {print \\$1}'\"; }   # regla 2 = la de cuenta\n"
   }
  ],
  "modo": null
 }
]""")

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_8e4b_fix_e2e.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    hechos, nuevos = 0, {}
    for c in CAMBIOS:
        r = c["ruta"]
        existe = os.path.isfile(r)
        b = open(r, "rb").read() if existe else None
        if existe and sha(b) == c["despues"]:
            hechos += 1; print(f"[YA APLICADO] {r}"); continue
        if c["antes"] is None:
            if existe:
                print(f"[NO APLICABLE] {r} ya existe con otro contenido (sha256={sha(b)})"); return 1
            if not os.path.isdir(os.path.dirname(r) or "."):
                print(f"[NO APLICABLE] no existe el directorio de {r} (¿estás en la raíz del repo?)"); return 1
            n = c["contenido"].encode("utf-8")
            print(f"[APLICABLE] {r} (nuevo, {len(n)} B)")
        else:
            if not existe:
                print(f"[NO APLICABLE] no existe {r} (¿estás en la raíz del repo?)"); return 1
            if sha(b) != c["antes"]:
                print(f"[NO APLICABLE] {r} sha256={sha(b)}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}"); return 1
            t = b.decode("utf-8")
            for i, bl in enumerate(c["bloques"], 1):
                if t.count(bl["viejo"]) != 1:
                    print(f"[NO APLICABLE] {r}: el bloque {i} aparece {t.count(bl['viejo'])} veces"); return 1
                t = t.replace(bl["viejo"], bl["nuevo"])
            n = t.encode("utf-8")
            print(f"[APLICABLE] {r} {c['antes'][:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques)")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {r}: el resultado no da el sha256 esperado"); return 1
        nuevos[r] = (n, c.get("modo"))
    if hechos and nuevos:
        print(f"[NO APLICABLE] estado mezclado: {hechos} ya aplicados y {len(nuevos)} no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(nuevos)} ficheros); nada escrito"); return 0
    for r, (n, modo) in nuevos.items():
        d = os.path.dirname(r) or "."
        m = (os.stat(r).st_mode & 0o7777) if os.path.exists(r) else (modo or 0o644)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, m); os.replace(tmp, r)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
