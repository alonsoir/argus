#!/usr/bin/env bash
# scripts/terceros/test_libbpf_instalar.sh — [TERCEROS-LIBBPF-D334] tests de las funciones lb_* de libbpf_instalar.sh y
# de provisioning/libbpf/{VERSION,COMMIT} (Mac, sin VMs ni red). Desde DAY335 ([TERCEROS-GIT-FIJADO-D335]) la versión, el
# fichero COMMIT y el tag contra el commit fijado (con el repositorio git de juguete) se prueban en
# test_lib_git_fijado.sh, junto a lib_git_fijado.sh; aquí queda lo de libbpf. Cada caso de rechazo se vuelve a correr
# contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${LIBBPF_SRC:-$aqui/../../provisioning/libbpf}
. "$aqui/libbpf_instalar.sh"

COMMIT_DAY334=fdf402b384cc42ce29bb9e27011633be3cbafe1e
OTRO_COMMIT=0123456789abcdef0123456789abcdef01234567
# ldconfig -p del defender, medido DAY334 (la nuestra primero), y el mismo con el orden al revés
LDC_BIEN=$'\tlibbpf.so.1 (libc6,x86-64) => /usr/lib64/libbpf.so.1\n\tlibbpf.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libbpf.so.1\n\tlibbpf.so (libc6,x86-64) => /usr/lib64/libbpf.so'
LDC_REVES=$'\tlibbpf.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libbpf.so.1\n\tlibbpf.so.1 (libc6,x86-64) => /usr/lib64/libbpf.so.1\n\tlibbpf.so (libc6,x86-64) => /usr/lib64/libbpf.so'
LDC_SIN=$'\tlibz.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libz.so.1'
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

primera_es() { [ "$(lb_primera_resolucion "$1")" = "$2" ]; }
version_repo() { gf_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(gf_commit_de_fichero "$src/COMMIT")" = "$1" ]; }
# el instalador carga lib_git_fijado.sh: sin ella no habría gf_clonar
carga_lib() { declare -F gf_clonar >/dev/null; }

los_casos() {
  acepta "libbpf_instalar.sh carga lib_git_fijado.sh (gf_clonar definida)" carga_lib
  acepta "ldconfig del defender (DAY334): la primera es /usr/lib64" primera_es "$LDC_BIEN" /usr/lib64/libbpf.so.1
  acepta "ldconfig al revés: la primera es la de bookworm" primera_es "$LDC_REVES" /lib/x86_64-linux-gnu/libbpf.so.1
  acepta "ldconfig sin libbpf: vacío" primera_es "$LDC_SIN" ""
  acepta "carga: /usr/lib64/libbpf.so.1 -> libbpf.so.1.4.6" lb_carga_ok 1.4.6 /usr/lib64/libbpf.so.1 /usr/lib64/libbpf.so.1.4.6
  rechaza "carga: la primera es la de bookworm (1.1.2)" lb_carga_ok 1.4.6 /lib/x86_64-linux-gnu/libbpf.so.1 /usr/lib/x86_64-linux-gnu/libbpf.so.1.1.2
  rechaza "carga: /usr/lib64 apunta a otra versión (1.4.7)" lb_carga_ok 1.4.6 /usr/lib64/libbpf.so.1 /usr/lib64/libbpf.so.1.4.7
  rechaza "carga: sin libbpf.so.1" lb_carga_ok 1.4.6 "" ""
  acepta "provisioning/libbpf/VERSION bien formado" version_repo
  acepta "provisioning/libbpf/COMMIT es el del tag v1.4.6 (medido DAY334)" commit_repo_es "$COMMIT_DAY334"
  rechaza "provisioning/libbpf/COMMIT no es otro commit" commit_repo_es "$OTRO_COMMIT"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
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
