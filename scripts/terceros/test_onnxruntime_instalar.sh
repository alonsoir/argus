#!/usr/bin/env bash
# scripts/terceros/test_onnxruntime_instalar.sh — [TERCEROS-ONNX-D330] tests de las funciones ort_* de
# onnxruntime_instalar.sh (Mac, sin VMs, sin red: un paquete falso hecho aquí). Los casos de rechazo se vuelven a correr
# contra funciones que lo aceptan todo: tienen que fallar ahí, para ver que el test distingue.
set -u
LC_ALL=C; export LC_ALL
. "$(dirname "$0")/onnxruntime_instalar.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# paquetes falsos
python3 -I - "$T" <<'PY'
import sys, zipfile, os
t = sys.argv[1]
H = ["onnxruntime_cxx_api.h", "onnxruntime_c_api.h", "onnxruntime_cxx_inline.h", "provider_options.h"]
def hacer(nombre, lib=True, cabs=H, extra=()):
    with zipfile.ZipFile(os.path.join(t, nombre), "w") as z:
        if lib: z.writestr("runtimes/linux-x64/native/libonnxruntime.so", b"ELF falso")
        for h in cabs: z.writestr("build/native/include/" + h, b"// " + h.encode())
        for n, c in extra: z.writestr(n, c)
hacer("bueno.nupkg", extra=[("runtimes/win-x64/native/onnxruntime.dll", b"x"), ("lib/net6.0/x.dll", b"x")])
hacer("sin_lib.nupkg", lib=False)
hacer("sin_cabecera.nupkg", cabs=H[1:])
hacer("trampa.nupkg", extra=[("build/native/include/../../../../evil.h", b"x"), ("build/native/include/sub/otro.h", b"x")])
open(os.path.join(t, "no_zip.nupkg"), "wb").write(b"esto no es un zip")
PY
printf 'contenido\n' > "$T/f"
SHA_F=$(openssl dgst -sha512 -binary "$T/f" | openssl base64 -A)
printf '# comentario\n%s\n' "$SHA_F" > "$T/sha_bien"
printf '# c\n%s\n%s\n' "$SHA_F" "$SHA_F" > "$T/sha_dos"
printf '%s\n' "${SHA_F%==}" > "$T/sha_corta"
printf '# solo comentarios\n' > "$T/sha_vacia"

sha_igual() { [ "$(ort_sha512 "$1")" = "$2" ]; }
sha_lee() { [ "$(ort_sha_de_fichero "$1")" = "$2" ]; }
extrae_bien() { local d="$T/x_$1"; rm -rf "$d"; ort_extraer "$T/$1" "$d" && [ -f "$d/lib/libonnxruntime.so" ] \
  && [ "$(ls "$d/include" | tr '\n' ' ')" = "onnxruntime_c_api.h onnxruntime_cxx_api.h onnxruntime_cxx_inline.h provider_options.h " ]; }
sin_trampa() { local d="$T/x_trampa"; rm -rf "$d" "$T/evil.h"; ort_extraer "$T/trampa.nupkg" "$d" >/dev/null; \
  [ ! -e "$T/evil.h" ] && [ ! -e "$d/include/otro.h" ] && [ ! -e "$d/include/sub" ] && [ ! -e "$d/evil.h" ]; }

los_casos() {
  acepta "versión 1.17.1" ort_version_valida 1.17.1
  rechaza "versión 1.17 (sin parche)" ort_version_valida 1.17
  rechaza "versión v1.17.1" ort_version_valida v1.17.1
  rechaza "versión vacía" ort_version_valida ""
  acepta "SHA512 de un fichero (base64, 88)" sha_igual "$T/f" "$SHA_F"
  rechaza "SHA512 de otro contenido" sha_igual "$T/sha_bien" "$SHA_F"
  acepta "fichero SHA512 con comentario" sha_lee "$T/sha_bien" "$SHA_F"
  rechaza "fichero SHA512 con dos líneas" ort_sha_de_fichero "$T/sha_dos"
  rechaza "fichero SHA512 corto" ort_sha_de_fichero "$T/sha_corta"
  rechaza "fichero SHA512 sin valor" ort_sha_de_fichero "$T/sha_vacia"
  rechaza "fichero SHA512 que no existe" ort_sha_de_fichero "$T/no_existe"
  acepta "paquete bueno: la biblioteca y solo las cabeceras" extrae_bien bueno.nupkg
  rechaza "paquete sin la biblioteca" ort_extraer "$T/sin_lib.nupkg" "$T/x1"
  rechaza "paquete sin onnxruntime_cxx_api.h" ort_extraer "$T/sin_cabecera.nupkg" "$T/x2"
  rechaza "fichero que no es un zip" ort_extraer "$T/no_zip.nupkg" "$T/x3"
  acepta "nombres con ../ o subdirectorios: no se sacan" sin_trampa
}
los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

ort_version_valida() { return 0; }
ort_sha_de_fichero() { echo x; }
ort_sha512() { cat "$1" >/dev/null 2>&1; echo "$SHA_F"; }
ort_extraer() { mkdir -p "$2/lib" "$2/include"; return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ]
