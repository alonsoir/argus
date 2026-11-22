#!/usr/bin/env bash
# scripts/terceros/test_libbpf_instalar.sh — [TERCEROS-LIBBPF-D334] tests de las funciones lb_* de libbpf_instalar.sh y
# de provisioning/libbpf/{VERSION,COMMIT} (Mac, sin VMs ni red: un repositorio git de juguete hecho aquí, con un tag
# ligero como el de libbpf). Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y tiene que
# fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${LIBBPF_SRC:-$aqui/../../provisioning/libbpf}
. "$aqui/libbpf_instalar.sh"

COMMIT_DAY334=fdf402b384cc42ce29bb9e27011633be3cbafe1e
# ldconfig -p del defender, medido DAY334 (la nuestra primero), y el mismo con el orden al revés
LDC_BIEN=$'\tlibbpf.so.1 (libc6,x86-64) => /usr/lib64/libbpf.so.1\n\tlibbpf.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libbpf.so.1\n\tlibbpf.so (libc6,x86-64) => /usr/lib64/libbpf.so'
LDC_REVES=$'\tlibbpf.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libbpf.so.1\n\tlibbpf.so.1 (libc6,x86-64) => /usr/lib64/libbpf.so.1\n\tlibbpf.so (libc6,x86-64) => /usr/lib64/libbpf.so'
LDC_SIN=$'\tlibz.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libz.so.1'
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# repositorio de juguete: dos commits; v1.4.6 (tag ligero) en el primero, y una copia donde el tag se ha movido al segundo
g() { git -C "$1" -c user.name=t -c user.email=t@t -c commit.gpgsign=false "${@:2}" >/dev/null 2>&1; }
mkdir -p "$T/up" && git init -q "$T/up" && echo uno > "$T/up/f" && g "$T/up" add f && g "$T/up" commit -q -m uno
g "$T/up" tag v1.4.6; C1=$(git -C "$T/up" rev-parse HEAD)
echo dos > "$T/up/f" && g "$T/up" commit -q -am dos; C2=$(git -C "$T/up" rev-parse HEAD)
git clone -q --bare "$T/up" "$T/movido.git" >/dev/null 2>&1 && g "$T/movido.git" tag -f v1.4.6 "$C2"
UP="file://$T/up"; MOVIDO="file://$T/movido.git"

printf '# comentario\n%s\n' "$C1" > "$T/c_bien"
printf '%s\n%s\n' "$C1" "$C2" > "$T/c_dos"
printf '%s\n' "${C1%?}" > "$T/c_corto"
printf '%s\n' "$(printf '%s' "$C1" | tr 'a-f' 'A-F')" > "$T/c_mayus"
printf '# solo comentarios\n' > "$T/c_vacio"

clona() { rm -rf "$T/d_$1"; lb_clonar "$2" "$3" "$T/d_$1" "$4"; }
commit_lee() { [ "$(lb_commit_de_fichero "$1")" = "$2" ]; }
primera_es() { [ "$(lb_primera_resolucion "$1")" = "$2" ]; }
version_repo() { lb_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(lb_commit_de_fichero "$src/COMMIT")" = "$1" ]; }

los_casos() {
  acepta "versión 1.4.6" lb_version_valida 1.4.6
  rechaza "versión v1.4.6 (con v)" lb_version_valida v1.4.6
  rechaza "versión 1.4 (sin parche)" lb_version_valida 1.4
  rechaza "versión latest (por nombre)" lb_version_valida latest
  rechaza "versión vacía" lb_version_valida ""
  rechaza "dos versiones en dos líneas" lb_version_valida $'1.4.6\n1.4.7'
  acepta "fichero COMMIT con comentario" commit_lee "$T/c_bien" "$C1"
  rechaza "fichero COMMIT con dos líneas" lb_commit_de_fichero "$T/c_dos"
  rechaza "fichero COMMIT corto" lb_commit_de_fichero "$T/c_corto"
  rechaza "fichero COMMIT en mayúscula" lb_commit_de_fichero "$T/c_mayus"
  rechaza "fichero COMMIT sin valor" lb_commit_de_fichero "$T/c_vacio"
  rechaza "fichero COMMIT que no existe" lb_commit_de_fichero "$T/no_existe"
  acepta "tag v1.4.6 que apunta al commit fijado" clona bien "$UP" v1.4.6 "$C1"
  rechaza "tag v1.4.6 que apunta a otro commit" clona otro "$UP" v1.4.6 "$C2"
  rechaza "tag v1.4.6 movido a otro commit en el repositorio" clona movido "$MOVIDO" v1.4.6 "$C1"
  rechaza "tag que no existe (v9.9.9)" clona falta "$UP" v9.9.9 "$C1"
  rechaza "repositorio que no existe" clona nada "file://$T/no_existe" v1.4.6 "$C1"
  acepta "ldconfig del defender (DAY334): la primera es /usr/lib64" primera_es "$LDC_BIEN" /usr/lib64/libbpf.so.1
  acepta "ldconfig al revés: la primera es la de bookworm" primera_es "$LDC_REVES" /lib/x86_64-linux-gnu/libbpf.so.1
  acepta "ldconfig sin libbpf: vacío" primera_es "$LDC_SIN" ""
  acepta "carga: /usr/lib64/libbpf.so.1 -> libbpf.so.1.4.6" lb_carga_ok 1.4.6 /usr/lib64/libbpf.so.1 /usr/lib64/libbpf.so.1.4.6
  rechaza "carga: la primera es la de bookworm (1.1.2)" lb_carga_ok 1.4.6 /lib/x86_64-linux-gnu/libbpf.so.1 /usr/lib/x86_64-linux-gnu/libbpf.so.1.1.2
  rechaza "carga: /usr/lib64 apunta a otra versión (1.4.7)" lb_carga_ok 1.4.6 /usr/lib64/libbpf.so.1 /usr/lib64/libbpf.so.1.4.7
  rechaza "carga: sin libbpf.so.1" lb_carga_ok 1.4.6 "" ""
  acepta "provisioning/libbpf/VERSION bien formado" version_repo
  acepta "provisioning/libbpf/COMMIT es el del tag v1.4.6 (medido DAY334)" commit_repo_es "$COMMIT_DAY334"
  rechaza "provisioning/libbpf/COMMIT no es otro commit" commit_repo_es "$C1"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
lb_version_valida() { return 0; }
lb_commit_de_fichero() { echo x; }
lb_clonar() { mkdir -p "$3"; return 0; }
lb_carga_ok() { return 0; }
commit_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-libbpf-instalar" || { echo "❌ test-libbpf-instalar: $total fallos"; exit 1; }
