#!/usr/bin/env python3
"""d331_sodium_sin_zmq.py — [TERCEROS-SODIUM-D331] parcheador: libsodium_instalar.sh deja de comprobar con ldd a
qué libsodium.so.23 enlazaría libzmq sola (medido DAY331: no dice qué carga un proceso); crea el enlace como provision.sh.
Uso: python3 d331_sodium_sin_zmq.py --check <raíz> | --apply <raíz>. Todo o nada: sha256 de partida, cada ancla una vez,
sha256 final; si algo falla no escribe nada. Idempotente: con los ficheros ya en el sha256 final, no hace nada."""
import hashlib, os, sys
SHA = {
 "scripts/terceros/libsodium_instalar.sh": [
  "6366519d7673c066b5c091425953f99c4287077aa90fde7dd8f8cc688beaeb5f",
  "2a95a4934c18efe6ee44e1b896d81387004fd3d100bd46dce0340b90ef062c55"
 ]
}
PARCHES = {
 "scripts/terceros/libsodium_instalar.sh": [
  [
   "# 1.0.19 (FIX DAY107, antes en tools/provision.sh); este script lo crea y comprueba que libzmq carga la de /usr/local.\n",
   "# 1.0.19 (FIX DAY107, antes en tools/provision.sh); este script lo crea, como hacía provision.sh.\n"
  ],
  [
   "  ldconfig -p | grep -qF \"$so (\" || fallo \"ldconfig no ve $so\"\n  zmq=/usr/lib/x86_64-linux-gnu/libzmq.so.5\n  if [ -e \"$zmq\" ]; then\n    ldd \"$zmq\" | grep -q 'libsodium.so.23 => /usr/local/lib/libsodium.so.23' \\\n      || fallo \"libzmq no carga /usr/local/lib/libsodium.so.23: $(ldd \"$zmq\" | grep libsodium)\"\n    log \"libzmq carga la libsodium de /usr/local (libsodium.so.23 -> $so)\"\n  else\n    log \"sin $zmq: no hay nada que comprobar del enlace libsodium.so.23\"\n  fi\n",
   "  ldconfig -p | grep -qF \"$so (\" || fallo \"ldconfig no ve $so\"\n  log \"enlace /usr/local/lib/libsodium.so.23 -> $so (FIX DAY107)\"\n"
  ]
 ]
}
def h(b): return hashlib.sha256(b).hexdigest()
def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__); return 2
    raiz = sys.argv[2]; nuevos = {}; hechos = 0
    for f, (ini, fin) in SHA.items():
        p = os.path.join(raiz, f)
        try: b = open(p, "rb").read()
        except OSError as e: print("FALLA: %s: %s" % (f, e)); return 1
        if h(b) == fin: print("ya aplicado: %s" % f); hechos += 1; continue
        if h(b) != ini: print("FALLA: %s tiene sha256 %s; se espera %s (o %s ya aplicado)" % (f, h(b), ini, fin)); return 1
        s = b.decode("utf-8")
        for viejo, nuevo in PARCHES[f]:
            n = s.count(viejo)
            if n != 1: print("FALLA: %s: un ancla aparece %d veces (se espera 1): %r" % (f, n, viejo[:80])); return 1
            s = s.replace(viejo, nuevo)
        nb = s.encode("utf-8")
        if h(nb) != fin: print("FALLA: %s quedaría con sha256 %s; se espera %s" % (f, h(nb), fin)); return 1
        nuevos[p] = nb
    if hechos == len(SHA): print("OK: nada que hacer"); return 0
    if sys.argv[1] == "--check":
        for p in nuevos: print("se puede aplicar: %s" % p)
        return 0
    for p, nb in nuevos.items():
        modo = os.stat(p).st_mode
        open(p, "wb").write(nb); os.chmod(p, modo); print("aplicado: %s -> %s" % (p, h(nb)))
    return 0
sys.exit(main())
