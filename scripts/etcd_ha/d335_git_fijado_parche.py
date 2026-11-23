#!/usr/bin/env python3
# d335_git_fijado_parche.py — [TERCEROS-GIT-FIJADO-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, pieza 1:
# libbpf_instalar.sh pasa a usar scripts/terceros/lib_git_fijado.sh (gf_version_valida, gf_commit_de_fichero, gf_clonar);
# su test se queda con lo de libbpf; el Makefile gana test-lib-git-fijado y su paso en el EMECAS.
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_git_fijado_parche.py
# Comprueba el sha256 de partida de los tres ficheros, cada ancla las veces exactas, y no escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {
    'scripts/terceros/libbpf_instalar.sh': '6d68553a9d4b2ed7ebbd2801e06cfbbef75754d1ef48f7f561cb59aa63b19dc0',
    'scripts/terceros/test_libbpf_instalar.sh': 'da11403adce12e99a7dbad967eca2026190e51cccfbca436a027fb7c0576cac3',
    'Makefile': '69a3ba9ecc89a9831fd5c32b001ede8a07f1b5679e9dc497651d3fef04497047',
}
LLEGADA = {
    'scripts/terceros/libbpf_instalar.sh': '63a996f6122e973e263ea0fcdb6312f554661f0bb7159cb5c67c317911546441',
    'scripts/terceros/test_libbpf_instalar.sh': '0209c9a3ebc706e3bf5a39dad2aac7b462cb7e3cdaf8947ff0715a535706e7fd',
    'Makefile': '4ac9573e1c6cf19b4a7cfa084fa18d127c753f936389c218bbdd0eb4d80f7a63',
}

LIB_TRES = '''# lb_version_valida VERSION -> rc 0 si es X.Y.Z (la cadena entera: un salto de línea dentro también es error)
lb_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$ ]]
}

# lb_commit_de_fichero FICHERO -> la única línea sin comentar, si son 40 hex en minúscula; rc 1 si no
lb_commit_de_fichero() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \\t\\r' | grep -v '^$')
  [ "$(printf '%s\\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\\n' "$s" | grep -Eqx '[0-9a-f]{40}' || return 1
  printf '%s\\n' "$s"
}

# lb_clonar URL TAG DESTINO COMMIT -> clona TAG (solo ese, profundidad 1) en DESTINO y rc 0 si HEAD es COMMIT; si no,
# rc 1 y el commit al que apunta por la salida. No compila nada.
lb_clonar() {
  local h
  git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3" >/dev/null 2>&1 \\
    || { echo "no se pudo clonar el tag $2 de $1"; return 1; }
  h=$(git -C "$3" rev-parse HEAD 2>/dev/null)
  [ "$h" = "$4" ] || { echo "el tag $2 apunta a ${h:-nada}, se exige $4"; return 1; }
}

'''
LIB_CARGA = '''# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado (la
# comparten los instaladores que traen código de terceros por git)
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

'''

CAMBIOS = {
    'scripts/terceros/libbpf_instalar.sh': [
        ('''# se resuelve a la nuestra, no baja ni compila nada. Las funciones lb_* no tocan el sistema (las prueba
# scripts/terceros/test_libbpf_instalar.sh en el Mac, sin red: con un repositorio git hecho allí).
''', '''# se resuelve a la nuestra, no baja ni compila nada. Las funciones lb_*, y las gf_* de lib_git_fijado.sh, no tocan el
# sistema (las prueban scripts/terceros/test_libbpf_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
''', 1),
        (LIB_TRES, LIB_CARGA, 1),
        ('  lb_version_valida "$v" || fallo', '  gf_version_valida "$v" || fallo', 1),
        ('  c=$(lb_commit_de_fichero "$src/COMMIT") || fallo', '  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo', 1),
        ('  r=$(lb_clonar "$LB_URL"', '  r=$(gf_clonar "$LB_URL"', 1),
    ],
    'Makefile': [
        ('\t@$(EMECAS_PASO) test-libbpf-instalar -- $(MAKE) test-libbpf-instalar\n',
         '\t@$(EMECAS_PASO) test-lib-git-fijado -- $(MAKE) test-lib-git-fijado\n'
         '\t@$(EMECAS_PASO) test-libbpf-instalar -- $(MAKE) test-libbpf-instalar\n', 1),
        ('''# [TERCEROS-LIBBPF-D334] test-libbpf-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/libbpf_instalar.sh
# (VERSION, COMMIT, el tag contra el commit fijado con un repositorio git de juguete, y a qué libbpf.so.1 resuelve
# ldconfig) y provisioning/libbpf/{VERSION,COMMIT}, también contra funciones que lo aceptan todo.
''', '''# [TERCEROS-GIT-FIJADO-D335] test-lib-git-fijado (Mac, sin VMs ni red): las funciones de scripts/terceros/lib_git_fijado.sh
# (VERSION, COMMIT y el tag contra el commit fijado, con un repositorio git de juguete y un tag movido), las que
# comparten los instaladores que traen código de terceros por git; también contra funciones que lo aceptan todo.
.PHONY: test-lib-git-fijado
test-lib-git-fijado:
\t@bash scripts/terceros/test_lib_git_fijado.sh

# [TERCEROS-LIBBPF-D334] test-libbpf-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/libbpf_instalar.sh
# (a qué libbpf.so.1 resuelve ldconfig y qué se exige de la carga) y provisioning/libbpf/{VERSION,COMMIT}, también contra
# funciones que lo aceptan todo. Versión, COMMIT y tag, en test-lib-git-fijado desde DAY335.
''', 1),
    ],
}
TEST_NUEVO = r'''#!/usr/bin/env bash
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
'''

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    raiz = pathlib.Path('.')
    for f in ['scripts/terceros/lib_git_fijado.sh', 'scripts/terceros/test_lib_git_fijado.sh']:
        if not (raiz / f).is_file():
            sys.exit(f'FALLA: falta {f} (se crea antes con su bloque cat > … <<EOF)')
    nuevos = {}
    for f, esperado in PARTIDA.items():
        b = (raiz / f).read_bytes()
        if sha(b) != esperado:
            sys.exit(f'FALLA: {f} sha256 de partida {sha(b)}, se espera {esperado}. Nada escrito.')
        t = b.decode()
        for viejo, nuevo, veces in CAMBIOS.get(f, []):
            n = t.count(viejo)
            if n != veces:
                sys.exit(f'FALLA: {f}: el ancla aparece {n} veces, se esperan {veces}:\n{viejo[:120]}\nNada escrito.')
            t = t.replace(viejo, nuevo)
        nuevos[f] = t.encode()
    nuevos['scripts/terceros/test_libbpf_instalar.sh'] = TEST_NUEVO.encode()
    for f, b in nuevos.items():
        if sha(b) != LLEGADA[f]:
            sys.exit(f'FALLA: {f} sha256 de llegada {sha(b)}, se espera {LLEGADA[f]}. Nada escrito.')
    for f, b in nuevos.items():
        (raiz / f).write_bytes(b)
        print(f'OK {f} {sha(b)}')

if __name__ == '__main__':
    main()
