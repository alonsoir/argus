#!/usr/bin/env bash
# scripts/terceros/onnxruntime_instalar.sh — [TERCEROS-ONNX-D330] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: ONNX
# Runtime desde el paquete NuGet oficial de Microsoft (Microsoft.ML.OnnxRuntime), comprobado con el SHA512 que publica
# NuGet. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del Vagrantfile. Lee de
# provisioning/onnxruntime/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 1.17.1)
#   SHA512   SHA512 del .nupkg, en base64 (88 caracteres), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Por qué (medido DAY330): github.com/microsoft/onnxruntime devuelve 404 desde el 17-nov-2026 (repositorio, API y
# ficheros de las releases); el wget -q de antes fallaba en silencio, el aprovisionamiento seguía y el EMECAS caía 1h40m
# después al configurar ml-detector ("ONNX Runtime not found").
# Del paquete solo se sacan runtimes/linux-x64/native/libonnxruntime.so (SONAME libonnxruntime.so.X.Y.Z: se instala con
# ese nombre y libonnxruntime.so apunta a él, lo que espera tools/prod/collect-libs.sh) y build/native/include/*.h (a
# /usr/local/include, como antes). El .tgz de GitHub traía además libonnxruntime_providers_shared.so, que solo usan los
# proveedores de ejecución no CPU: aRGus usa CPU.
# Idempotente: si ya está instalado lo de este SHA512 (marca en /usr/local/lib/argus-onnxruntime.sha512), no baja nada.
# Las funciones ort_* no tocan el sistema (las prueba scripts/terceros/test_onnxruntime_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ONNX] $*"; }
fallo() { echo "[TERCEROS-ONNX] FALLA: $*"; exit 1; }

ort_version_valida() { printf '%s\n' "$1" | grep -Eqx '[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}'; }

# ort_sha_de_fichero FICHERO_SHA512 -> la única línea sin comentar, si es base64 de 88 caracteres; rc 1 si no
ort_sha_de_fichero() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \t\r' | grep -v '^$')
  [ "$(printf '%s\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$s" | grep -Eqx '[A-Za-z0-9+/]{86}==' || return 1
  printf '%s\n' "$s"
}

# ort_sha512 FICHERO -> SHA512 en base64 (portátil: openssl de Debian y LibreSSL del Mac)
ort_sha512() { openssl dgst -sha512 -binary "$1" | openssl base64 -A; }

# ort_extraer NUPKG DESTINO -> deja DESTINO/lib/libonnxruntime.so y DESTINO/include/*.h; nada más del paquete y nunca
# fuera de DESTINO. rc 1 si falta la biblioteca o alguna de las cabeceras que usa ml-detector.
ort_extraer() {
  python3 -I - "$1" "$2" <<'PY'
import os, sys, zipfile
nupkg, dest = sys.argv[1], sys.argv[2]
LIB = "runtimes/linux-x64/native/libonnxruntime.so"
INC = "build/native/include/"
NECESARIAS = {"onnxruntime_cxx_api.h", "onnxruntime_c_api.h", "onnxruntime_cxx_inline.h"}
try:
    z = zipfile.ZipFile(nupkg)
except Exception as e:
    print("no es un paquete zip: %s" % e); sys.exit(1)
os.makedirs(os.path.join(dest, "lib"), exist_ok=True)
os.makedirs(os.path.join(dest, "include"), exist_ok=True)
lib = False; cabeceras = set()
for n in z.namelist():
    if n == LIB:
        destino = os.path.join(dest, "lib", "libonnxruntime.so"); lib = True
    elif n.startswith(INC) and n.endswith(".h") and "/" not in n[len(INC):] and n[len(INC):] not in ("", ".", ".."):
        destino = os.path.join(dest, "include", n[len(INC):]); cabeceras.add(n[len(INC):])
    else:
        continue
    with z.open(n) as f, open(destino, "wb") as g:
        g.write(f.read())
falta = sorted(NECESARIAS - cabeceras)
if not lib or falta:
    print("al paquete le falta: %s" % ", ".join(([LIB] if not lib else []) + falta)); sys.exit(1)
print("%d cabeceras y la biblioteca" % len(cabeceras))
PY
}

main() {
  local src=${ONNX_SRC:-/vagrant/provisioning/onnxruntime} v sha url tmp got so marca=/usr/local/lib/argus-onnxruntime.sha512
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  ort_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z). ERROR DE FABRICANTE: avisar a aRGus"
  sha=$(ort_sha_de_fichero "$src/SHA512") || fallo "$src/SHA512: hace falta una línea sin comentar de 88 caracteres base64. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y SHA512 ${sha:0:16}... (de $src)"
  if [ -f "/usr/local/lib/libonnxruntime.so.$v" ] && [ "$(cat "$marca" 2>/dev/null)" = "$sha" ] \
     && [ -f /usr/local/include/onnxruntime_cxx_api.h ]; then
    log "ya instalado (marca $marca)"
  else
    url="https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime/$v/microsoft.ml.onnxruntime.$v.nupkg"
    tmp=$(mktemp -d)
    wget -q --https-only -T 60 -t 3 -O "$tmp/ort.nupkg" "$url" || { rm -rf "$tmp"; fallo "no se pudo bajar $url"; }
    got=$(ort_sha512 "$tmp/ort.nupkg")
    [ "$got" = "$sha" ] || { rm -rf "$tmp"; fallo "SHA512 del paquete $got, se exige $sha ($src/SHA512): no se instala"; }
    log "paquete bajado de NuGet y comprobado: $(stat -c %s "$tmp/ort.nupkg") bytes, SHA512 igual al de $src/SHA512"
    ort_extraer "$tmp/ort.nupkg" "$tmp/x" || { rm -rf "$tmp"; fallo "no se pudo sacar del paquete lo que hace falta"; }
    so=$(readelf -d "$tmp/x/lib/libonnxruntime.so" | sed -n 's/.*SONAME.*\[\(.*\)\].*/\1/p')
    [ "$so" = "libonnxruntime.so.$v" ] || { rm -rf "$tmp"; fallo "SONAME '$so', se espera libonnxruntime.so.$v"; }
    install -m 0644 -o root -g root "$tmp/x/lib/libonnxruntime.so" "/usr/local/lib/libonnxruntime.so.$v"
    ln -sfn "libonnxruntime.so.$v" /usr/local/lib/libonnxruntime.so
    install -m 0644 -o root -g root "$tmp"/x/include/*.h /usr/local/include/
    rm -rf "$tmp"
    printf '%s\n' "$sha" > "$marca"
  fi
  mkdir -p /usr/local/lib64
  ln -sfn "/usr/local/lib/libonnxruntime.so.$v" "/usr/local/lib64/libonnxruntime.so.$v"
  ln -sfn "/usr/local/lib/libonnxruntime.so.$v" /usr/local/lib64/libonnxruntime.so
  ldconfig
  ldconfig -p | grep -qF "libonnxruntime.so.$v " || fallo "ldconfig no ve libonnxruntime.so.$v"
  log "✅ ONNX Runtime $v (NuGet Microsoft.ML.OnnxRuntime, SHA512 comprobado) en /usr/local/lib y /usr/local/include"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
