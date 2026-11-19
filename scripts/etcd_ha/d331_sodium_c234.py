#!/usr/bin/env python3
"""d331_sodium_c234.py — [TERCEROS-SODIUM-D331] parcheador de los commits 2-4 del PR de libsodium:
  Vagrantfile         el bloque que bajaba libsodium con curl de GitHub sin comprobar -> scripts/terceros/libsodium_instalar.sh
  tools/provision.sh  install_libsodium_1019 -> el mismo instalador; SODIUM_REQUIRED de provisioning/libsodium/VERSION;
                      fuera SODIUM_URL, SODIUM_SHA256 y el enlace del FIX DAY107 (ahora en el instalador)
  Makefile            check-system-deps lee la versión de provisioning/libsodium/VERSION y la compara exacta
Uso: python3 d331_sodium_c234.py --check <raíz> | --apply <raíz>. Todo o nada: sha256 de partida de los tres; cada
marcador (línea comparada sin la sangría inicial) exactamente una vez; si algo falla no escribe nada. Imprime el
sha256 final de cada fichero. Idempotente: si ya está aplicado (marca TERCEROS-SODIUM-D331 presente), no hace nada."""
import hashlib, os, sys
MARCA = "[TERCEROS-SODIUM-D331]"
SHA = {"Vagrantfile": "a70018d23ab62919d7644c5f23a924342c2eb8e0f00269a07768a809430b365f",
       "tools/provision.sh": "485be8f2b7e276660845fe766d29d65771a7597d521e8282a5592aaa5028fe08",
       "Makefile": "11352bd8e17b60872e1dc62f7970a99305af3c3c59ad21c8060d31bee1881718"}

# (fichero, línea inicial, línea final, líneas extra tras la final (contenido esperado, sin sangría), nuevo texto
#  sin sangría; cada línea nueva lleva la sangría de la línea inicial, salvo las vacías)
CAMBIOS = [
 ("Vagrantfile",
  "# libsodium 1.0.19 (requerido por crypto-transport HKDF-SHA256 — ADR-013)",
  'echo "✅ libsodium 1.0.19 already installed"', ["fi"],
  ["# [TERCEROS-SODIUM-D331] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: libsodium (crypto-transport necesita",
   "# HKDF-SHA256 desde la 1.0.19, ADR-013; bookworm trae la 1.0.18) de download.libsodium.org, en la versión de",
   "# provisioning/libsodium/VERSION, comprobada con la firma minisign del mantenedor y el SHA256 fijado. Medido DAY331:",
   "# antes se bajaba con curl de GitHub sin comprobar nada (y tools/provision.sh, que sí comprobaba, no llegaba a",
   "# instalarla). Si falla, para aquí.",
   'bash /vagrant/scripts/terceros/libsodium_instalar.sh || { echo "❌ libsodium"; exit 1; }']),
 ("tools/provision.sh",
  "# LIBSODIUM 1.0.19 — Compilación desde fuente",
  'log_item "HKDF:    crypto_kdf_hkdf_sha256_extract/expand disponibles ✅"', ["}"],
  ["# LIBSODIUM — [TERCEROS-SODIUM-D331] un solo instalador: scripts/terceros/libsodium_instalar.sh",
   "# (download.libsodium.org, firma minisign del mantenedor y SHA256 fijado; versión, clave y SHA256 en",
   "# provisioning/libsodium/). Hasta DAY331 aquí había otra copia, con solo el SHA256, que en un lab desde cero no",
   "# llegaba a instalar nada: el Vagrantfile la instalaba antes, sin comprobar.",
   "# " + "=" * 77,
   "",
   'ARGUS_RAIZ_SODIUM=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)',
   "SODIUM_REQUIRED=$( { tr -d '[:space:]' < \"${ARGUS_RAIZ_SODIUM}/provisioning/libsodium/VERSION\"; } 2>/dev/null || echo \"?\")",
   "readonly ARGUS_RAIZ_SODIUM SODIUM_REQUIRED",
   "",
   "install_libsodium_1019() {",
   '    log_section "libsodium ${SODIUM_REQUIRED}"',
   '    SODIUM_SRC="${ARGUS_RAIZ_SODIUM}/provisioning/libsodium" \\',
   '        bash "${ARGUS_RAIZ_SODIUM}/scripts/terceros/libsodium_instalar.sh" \\',
   '        || { log_error "libsodium: falló scripts/terceros/libsodium_instalar.sh"; exit 1; }',
   "}"]),
 ("tools/provision.sh",
  "# ── FIX DAY 107: libsodium.so.23 → libsodium.so.26 + ldconfig ────────────",
  'log_warn "libsodium.so.26 no encontrada — instalar primero con install_libsodium_1019"', ["fi"],
  ["# FIX DAY 107 (libsodium.so.23 -> la 1.0.19): lo hace scripts/terceros/libsodium_instalar.sh [TERCEROS-SODIUM-D331]"]),
 ("tools/provision.sh",
  'echo "    SHA-256:           ${SODIUM_SHA256}"', None, [],
  ['echo "    Verificación:      firma minisign + SHA256 (provisioning/libsodium/)"']),
 ("Makefile",
  "check-system-deps:", None, [],
  ["# [TERCEROS-SODIUM-D331] versión de libsodium: la de provisioning/libsodium/VERSION (un único lugar)",
   "SODIUM_VERSION := $(shell tr -d '[:space:]' < provisioning/libsodium/VERSION)",
   "",
   "check-system-deps:"]),
 ("Makefile",
  "@vagrant ssh -c \"pkg-config --modversion libsodium 2>/dev/null | grep -q '1.0.19' || { echo '❌ libsodium 1.0.19 missing'; exit 1; }\"",
  None, [],
  ["@vagrant ssh -c \"pkg-config --modversion libsodium 2>/dev/null | grep -qxF '$(SODIUM_VERSION)' || { echo '❌ libsodium $(SODIUM_VERSION) missing (provisioning/libsodium/VERSION)'; exit 1; }\""]),
]

def h(b): return hashlib.sha256(b).hexdigest()
def unica(lineas, texto, f):
    idx = [i for i, l in enumerate(lineas) if l.rstrip("\n").strip() == texto]
    if len(idx) != 1: raise ValueError("%s: el marcador aparece %d veces (se espera 1): %r" % (f, len(idx), texto[:90]))
    return idx[0]

def aplicar(f, s):
    lineas = s.splitlines(True)
    for (ff, ini, fin, extra, nuevo) in CAMBIOS:
        if ff != f: continue
        i = unica(lineas, ini, f)
        j = i if fin is None else unica(lineas, fin, f)
        if j < i: raise ValueError("%s: el marcador final va antes que el inicial: %r" % (f, fin))
        for k, e in enumerate(extra):
            n = j + 1 + k
            if n >= len(lineas) or lineas[n].strip() != e:
                raise ValueError("%s: tras %r se esperaba %r" % (f, fin, e))
        j += len(extra)
        l0 = lineas[i]; sangria = l0[:len(l0) - len(l0.lstrip())]
        lineas[i:j + 1] = [(sangria + x if x else "") + "\n" for x in nuevo]
    return "".join(lineas)

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__); return 2
    raiz = sys.argv[2]; nuevos = {}
    for f, ini in SHA.items():
        p = os.path.join(raiz, f)
        try: b = open(p, "rb").read()
        except OSError as e: print("FALLA: %s: %s" % (f, e)); return 1
        s = b.decode("utf-8")
        if MARCA in s and h(b) != ini: print("ya aplicado: %s (sha256 %s)" % (f, h(b))); continue
        if h(b) != ini: print("FALLA: %s tiene sha256 %s; se espera %s" % (f, h(b), ini)); return 1
        try: ns = aplicar(f, s)
        except ValueError as e: print("FALLA: %s" % e); return 1
        nuevos[p] = (f, ns.encode("utf-8"))
    if not nuevos: print("OK: nada que hacer"); return 0
    for p, (f, nb) in nuevos.items():
        if sys.argv[1] == "--check": print("se puede aplicar: %s -> sha256 %s" % (f, h(nb)))
    if sys.argv[1] == "--check": return 0
    for p, (f, nb) in nuevos.items():
        modo = os.stat(p).st_mode
        open(p, "wb").write(nb); os.chmod(p, modo); print("aplicado: %s -> sha256 %s" % (f, h(nb)))
    return 0
sys.exit(main())
