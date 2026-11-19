#!/usr/bin/env python3
"""d331_sodium_old.py — [TERCEROS-SODIUM-D331] parcheador: libsodium_instalar.sh baja de releases/ y, si no está, de
releases/old/ (ls_bases, ls_bajar); su test lo prueba (1.0.19 de releases/, 1.0.18 de old/, una inexistente falla).
Uso: python3 d331_sodium_old.py --check <raíz> | --apply <raíz>. Todo o nada: sha256 de partida, cada ancla una vez,
sha256 final; si algo falla no escribe nada. Idempotente: con los ficheros ya en el sha256 final, no hace nada."""
import hashlib, os, sys
SHA = {
 "scripts/terceros/libsodium_instalar.sh": [
  "efb8e19d28c79e29ee0b4cda8d59ee6203d2c1f42c493e637ca9a4786e4dc809",
  "6366519d7673c066b5c091425953f99c4287077aa90fde7dd8f8cc688beaeb5f"
 ],
 "scripts/terceros/test_libsodium_instalar.sh": [
  "35917936d544f74295081efe795bfca79e9ba6895bd47c92d820ad9b90aa47b7",
  "b4a8db8ae0ce82638b0f373ae2099f26d827ab0566986fa86e779ac21c74c3db"
 ]
}
PARCHES = {
 "scripts/terceros/libsodium_instalar.sh": [
  [
   "# tarball firmado de otra versión, renombrado, no pasa.\n# Idempotente: si la marca /usr/local/lib/argus-libsodium.verificado dice esta versión y este SHA256, pkg-config da la\n",
   "# tarball firmado de otra versión, renombrado, no pasa.\n# Dónde (medido DAY331): libsodium pasa las versiones antiguas a releases/old/ (la 1.0.18 ya solo está allí); se prueba\n# releases/ y, si no tiene el tarball y su firma, releases/old/. Lo que se baje pasa igual por firma, nombre y SHA256.\n# Idempotente: si la marca /usr/local/lib/argus-libsodium.verificado dice esta versión y este SHA256, pkg-config da la\n"
  ],
  [
   "\n# ls_verificar TARBALL MINISIG CLAVE NOMBRE SHA256 -> rc 0 si la firma es válida con CLAVE, el comentario de confianza\n",
   "\n# ls_bases -> las carpetas donde libsodium publica sus versiones, en el orden en que se prueban\nls_bases() {\n  printf '%s\\n' https://download.libsodium.org/libsodium/releases https://download.libsodium.org/libsodium/releases/old\n}\n\n# ls_bajar NOMBRE DIR -> baja NOMBRE y NOMBRE.minisig a DIR desde la primera carpeta de ls_bases que tenga los dos y\n# escribe la URL usada; rc 1 si ninguna los tiene. No comprueba nada: eso es ls_verificar.\nls_bajar() {\n  local b\n  for b in $(ls_bases); do\n    if wget -q --https-only -T 60 -t 3 -O \"$2/$1\" \"$b/$1\" \\\n       && wget -q --https-only -T 60 -t 3 -O \"$2/$1.minisig\" \"$b/$1.minisig\"; then\n      printf '%s\\n' \"$b/$1\"; return 0\n    fi\n  done\n  rm -f \"$2/$1\" \"$2/$1.minisig\"; return 1\n}\n\n# ls_verificar TARBALL MINISIG CLAVE NOMBRE SHA256 -> rc 0 si la firma es válida con CLAVE, el comentario de confianza\n"
  ],
  [
   "    fi\n    url=\"https://download.libsodium.org/libsodium/releases/$nombre\"\n    tmp=$(mktemp -d)\n",
   "    fi\n    tmp=$(mktemp -d)\n"
  ],
  [
   "    tmp=$(mktemp -d)\n    wget -q --https-only -T 60 -t 3 -O \"$tmp/$nombre\" \"$url\" || { rm -rf \"$tmp\"; fallo \"no se pudo bajar $url\"; }\n    wget -q --https-only -T 60 -t 3 -O \"$tmp/$nombre.minisig\" \"$url.minisig\" \\\n      || { rm -rf \"$tmp\"; fallo \"no se pudo bajar $url.minisig\"; }\n    r=$(ls_verificar \"$tmp/$nombre\" \"$tmp/$nombre.minisig\" \"$k\" \"$nombre\" \"$sha\") || { rm -rf \"$tmp\"; fallo \"$r: no se instala\"; }\n",
   "    tmp=$(mktemp -d)\n    url=$(ls_bajar \"$nombre\" \"$tmp\") \\\n      || { rm -rf \"$tmp\"; fallo \"no se pudo bajar $nombre y su firma de ninguna de: $(ls_bases | tr '\\n' ' ')\"; }\n    r=$(ls_verificar \"$tmp/$nombre\" \"$tmp/$nombre.minisig\" \"$k\" \"$nombre\" \"$sha\") || { rm -rf \"$tmp\"; fallo \"$r: no se instala\"; }\n"
  ],
  [
   "    r=$(ls_verificar \"$tmp/$nombre\" \"$tmp/$nombre.minisig\" \"$k\" \"$nombre\" \"$sha\") || { rm -rf \"$tmp\"; fallo \"$r: no se instala\"; }\n    log \"tarball bajado y comprobado: $(stat -c %s \"$tmp/$nombre\") bytes, firma minisign válida, comentario de confianza file:$nombre, SHA256 igual al de $src/SHA256\"\n    d=$(tar tzf \"$tmp/$nombre\" | head -1 | cut -d/ -f1)\n",
   "    r=$(ls_verificar \"$tmp/$nombre\" \"$tmp/$nombre.minisig\" \"$k\" \"$nombre\" \"$sha\") || { rm -rf \"$tmp\"; fallo \"$r: no se instala\"; }\n    log \"tarball bajado de $url y comprobado: $(stat -c %s \"$tmp/$nombre\") bytes, firma minisign válida, comentario de confianza file:$nombre, SHA256 igual al de $src/SHA256\"\n    d=$(tar tzf \"$tmp/$nombre\" | head -1 | cut -d/ -f1)\n"
  ]
 ],
 "scripts/terceros/test_libsodium_instalar.sh": [
  [
   "#   sin argumentos: las funciones puras (en el Mac o en cualquier sitio; no baja nada ni toca el sistema)\n#   --vm:           además, la verificación de verdad con minisign y los tarballs oficiales (en el defender; baja\n#                   libsodium-<VERSION> y libsodium-1.0.18 con su firma a un directorio temporal y lo borra)\n# Sale con rc 0 solo si pasan todos; sin minisign o sin red en --vm, falla (no se salta nada).\n",
   "#   sin argumentos: las funciones puras (en el Mac o en cualquier sitio; no baja nada ni toca el sistema)\n#   --vm:           además, la descarga y la verificación de verdad con minisign y los tarballs oficiales (en el\n#                   defender; baja libsodium-<VERSION> de releases/ y libsodium-1.0.18 de releases/old/, con su firma, a\n#                   un directorio temporal y lo borra)\n# Sale con rc 0 solo si pasan todos; sin minisign o sin red en --vm, falla (no se salta nada).\n"
  ],
  [
   "\n# 4. comentario de confianza\n",
   "\n# 3b. carpetas de descarga, en orden\n[ \"$(ls_bases | grep -c .)\" = 2 ] && [ \"$(ls_bases | sed -n 1p)\" = https://download.libsodium.org/libsodium/releases ] \\\n  && [ \"$(ls_bases | sed -n 2p)\" = https://download.libsodium.org/libsodium/releases/old ] \\\n  && ok=$((ok+1)) || { mal=$((mal+1)); echo \"FALLO: ls_bases\"; }\n\n# 4. comentario de confianza\n"
  ],
  [
   "  if ! command -v minisign >/dev/null 2>&1; then mal=$((mal+1)); echo \"FALLO: --vm sin minisign\"\n  elif ! wget -q --https-only -T 60 -t 3 -P \"$t\" \"$base/$n\" \"$base/$n.minisig\" \\\n       \"$base/libsodium-1.0.18.tar.gz\" \"$base/libsodium-1.0.18.tar.gz.minisig\"; then\n    mal=$((mal+1)); echo \"FALLO: --vm no pudo bajar los tarballs y las firmas de $base\"\n  else\n",
   "  if ! command -v minisign >/dev/null 2>&1; then mal=$((mal+1)); echo \"FALLO: --vm sin minisign\"\n  elif ! u19=$(ls_bajar \"$n\" \"$t\") || ! u18=$(ls_bajar libsodium-1.0.18.tar.gz \"$t\"); then\n    mal=$((mal+1)); echo \"FALLO: --vm no pudo bajar $n o libsodium-1.0.18.tar.gz con su firma\"\n  else\n"
  ],
  [
   "  else\n    si ls_verificar \"$t/$n\" \"$t/$n.minisig\" \"$k\" \"$n\" \"$h\"\n",
   "  else\n    [ \"$u19\" = \"$base/$n\" ] && ok=$((ok+1)) || { mal=$((mal+1)); echo \"FALLO: $n debía venir de $base, vino de $u19\"; }\n    [ \"$u18\" = \"$base/old/libsodium-1.0.18.tar.gz\" ] && ok=$((ok+1)) \\\n      || { mal=$((mal+1)); echo \"FALLO: la 1.0.18 debía venir de $base/old, vino de $u18\"; }\n    no ls_bajar libsodium-0.0.0.tar.gz \"$t\"\n    si ls_verificar \"$t/$n\" \"$t/$n.minisig\" \"$k\" \"$n\" \"$h\"\n"
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
