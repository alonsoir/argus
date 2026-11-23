#!/usr/bin/env python3
# d335_httplib_parche.py — [TERCEROS-HTTPLIB-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente cpp-httplib:
# crea provisioning/cpp-httplib/{VERSION,COMMIT}, scripts/terceros/cpphttplib_instalar.sh y su test; el Vagrantfile
# llama al instalador en lugar del git clone de la rama principal; el Makefile gana test-cpphttplib-instalar y su paso
# en el EMECAS. Va encima de las piezas 1 y 1b (lib_git_fijado.sh).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_httplib_parche.py
# Comprueba el sha256 de partida, que los nuevos no existan, cada ancla las veces exactas, el sha256 de llegada, y no
# escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {'Vagrantfile': '3f69ef0b5052a0ca6c4e47b607922d8a55c0465492cff8a750921850300a2cc1', 'Makefile': '4ac9573e1c6cf19b4a7cfa084fa18d127c753f936389c218bbdd0eb4d80f7a63'}
LLEGADA = {'Vagrantfile': '6362c2a91ac883d276867a2d557f4c35b39cd345902cb42baf2fbd688e4cea3a', 'Makefile': 'a4560e2df118c8a90567ebf0627609cf74e679fa3d3d8b0de6a31c9c50a39f35', 'provisioning/cpp-httplib/VERSION': 'a6fcc5d96eed4f7ab817b3efc0da1f6ef4e1e736e7aa83361a66f2b965ccdb1e', 'provisioning/cpp-httplib/COMMIT': 'b5b174f3e54cbf1a0bfaaa853685a74c7ae6b137283788a0bd86aaf05a271f1d', 'scripts/terceros/cpphttplib_instalar.sh': '220ebf77b935a094a9a13d7b05e49f35fed9d3da90f6d87579db212a5102cefd', 'scripts/terceros/test_cpphttplib_instalar.sh': '9444b18e98de76f1d9ca8f907842e1667395c46e6a9423f78f13430ed15e7f89'}
NUEVOS = {
    'provisioning/cpp-httplib/VERSION': r'''0.67.0
''',
    'provisioning/cpp-httplib/COMMIT': r'''# provisioning/cpp-httplib/COMMIT — [TERCEROS-HTTPLIB-D335] commit del repositorio oficial de cpp-httplib
# (https://github.com/yhirose/cpp-httplib) al que apunta el tag v<VERSION> de provisioning/cpp-httplib/VERSION. Medido
# DAY335: el tag v0.67.0 es ligero (sin objeto tag ni firma) y apunta a 7800c3dc5b33285cbb18baa5998de4ff7ef63515,
# "Release v0.67.0" (yhirose, 2026-11-18), commit sin firma; git ls-remote da el mismo. cpp-httplib no publica firma ni
# hash de sus versiones: lo que manda es este commit (SHA-1 de git). Un tag ligero se puede mover; si el tag deja de
# apuntar aquí, la instalación para. Antes (hasta DAY334) se clonaba la rama principal, sin tag ni commit: el lab tenía
# una httplib.h que dice 0.67.0 sin saber de qué commit.
# Si cambia VERSION, cambia esto (medido igual). Una sola línea sin comentar: 40 hexadecimales en minúscula.
7800c3dc5b33285cbb18baa5998de4ff7ef63515
''',
    'scripts/terceros/cpphttplib_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/cpphttplib_instalar.sh — [TERCEROS-HTTPLIB-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# cpp-httplib: httplib.h (biblioteca de una sola cabecera) del repositorio oficial (github.com/yhirose/cpp-httplib), en
# el tag v<VERSION> y comprobado que el tag apunta al commit fijado. La usan common, etcd-client, etcd-server,
# firewall-acl-agent y ml-detector. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del
# Vagrantfile. Lee de provisioning/cpp-httplib/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 0.67.0)
#   COMMIT   commit al que apunta el tag v<VERSION> (40 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): git clone de la rama principal, sin tag ni commit, y solo si no había httplib.h: entraba en el
# pipeline lo que hubiera ese día. Medido DAY335: la del lab dice "0.67.0", y el tag v0.67.0 es ligero.
# Idempotente: si la marca /usr/local/lib/argus-cpp-httplib.commit dice este commit y el sha256 de la httplib.h
# instalada, y la cabecera dice esta versión, no baja nada. Una httplib.h sin marca (la de antes) o cambiada después se
# sustituye. Las funciones ch_*, y las gf_* de lib_git_fijado.sh, no tocan el sistema (las prueban
# scripts/terceros/test_cpphttplib_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-HTTPLIB] $*"; }
fallo() { echo "[TERCEROS-HTTPLIB] FALLA: $*"; exit 1; }
CH_URL=https://github.com/yhirose/cpp-httplib.git
CH_DESTINO=/usr/local/include/httplib.h

# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

# ch_version_de_cabecera FICHERO -> la versión de su #define CPPHTTPLIB_VERSION "X.Y.Z"; vacío si no hay
ch_version_de_cabecera() {
  sed -n 's/^#define CPPHTTPLIB_VERSION "\([^"]*\)"$/\1/p' "$1" 2>/dev/null | head -1
}

# ch_sha256 FICHERO -> su sha256 (sha256sum en Debian, shasum en el Mac); vacío si no existe
ch_sha256() {
  [ -f "$1" ] || return 0
  if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# ch_estado VERSION COMMIT CABECERA MARCA -> rc 0 si la cabecera dice VERSION y la marca dice "COMMIT <sha256 de la
# cabecera>"; si no, rc 1 y el motivo
ch_estado() {
  local v s
  [ -f "$3" ] || { echo "no hay $3"; return 1; }
  v=$(ch_version_de_cabecera "$3")
  [ "$v" = "$1" ] || { echo "$3 dice la versión '${v}', se espera $1"; return 1; }
  s=$(ch_sha256 "$3")
  [ "$(cat "$4" 2>/dev/null)" = "$2 $s" ] || { echo "la marca $4 no dice el commit $2 y el sha256 $s de $3"; return 1; }
}

main() {
  local src=${CPPHTTPLIB_SRC:-/vagrant/provisioning/cpp-httplib} v c tmp r marca=/usr/local/lib/argus-cpp-httplib.commit
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  gf_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z: p. ej. 0.67.0). ERROR DE FABRICANTE: avisar a aRGus"
  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo "$src/COMMIT: hace falta una línea sin comentar de 40 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y commit ${c:0:12}... (de $src)"
  if r=$(ch_estado "$v" "$c" "$CH_DESTINO" "$marca"); then
    log "✅ cpp-httplib $v ya instalada (marca $marca)"; return 0
  fi
  log "hay que instalar: $r"
  command -v git >/dev/null || apt-get install -y git >/dev/null || fallo "apt-get install git"
  tmp=$(mktemp -d)
  r=$(gf_clonar "$CH_URL" "v$v" "$tmp/cpp-httplib" "$c") || { rm -rf "$tmp"; fallo "$r"; }
  log "tag v$v clonado de $CH_URL y comprobado: commit $c"
  r=$(ch_version_de_cabecera "$tmp/cpp-httplib/httplib.h")
  [ "$r" = "$v" ] || { rm -rf "$tmp"; fallo "la httplib.h del tag v$v dice la versión '${r}'"; }
  mkdir -p "$(dirname "$CH_DESTINO")" "$(dirname "$marca")"
  install -m 0644 "$tmp/cpp-httplib/httplib.h" "$CH_DESTINO" || { rm -rf "$tmp"; fallo "no se pudo copiar a $CH_DESTINO"; }
  rm -rf "$tmp"
  printf '%s %s\n' "$c" "$(ch_sha256 "$CH_DESTINO")" > "$marca"
  r=$(ch_estado "$v" "$c" "$CH_DESTINO" "$marca") || fallo "tras instalar: $r"
  log "✅ cpp-httplib $v (commit $c del repositorio oficial) en $CH_DESTINO, sha256 $(ch_sha256 "$CH_DESTINO")"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
''',
    'scripts/terceros/test_cpphttplib_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/test_cpphttplib_instalar.sh — [TERCEROS-HTTPLIB-D335] tests de las funciones ch_* de
# cpphttplib_instalar.sh y de provisioning/cpp-httplib/{VERSION,COMMIT} (Mac, sin VMs ni red). El tag contra el commit
# fijado y los reintentos, en test_lib_git_fijado.sh. Cada caso de rechazo se vuelve a correr contra funciones que lo
# aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${CPPHTTPLIB_SRC:-$aqui/../../provisioning/cpp-httplib}
. "$aqui/cpphttplib_instalar.sh"

COMMIT_DAY335=7800c3dc5b33285cbb18baa5998de4ff7ef63515
OTRO_COMMIT=0123456789abcdef0123456789abcdef01234567
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# cabeceras de juguete: las líneas 11 y 12 de la httplib.h del tag v0.67.0 (medido DAY335), otra versión, y sin define
cabecera() { printf '//\n//  httplib.h\n//\n#ifndef CPPHTTPLIB_HTTPLIB_H\n#define CPPHTTPLIB_HTTPLIB_H\n\n#define CPPHTTPLIB_VERSION "%s"\n#define CPPHTTPLIB_VERSION_NUM "0x004300"\n' "$1"; }
cabecera 0.67.0 > "$T/h_bien"
cabecera 0.66.0 > "$T/h_otra"
printf '#ifndef CPPHTTPLIB_HTTPLIB_H\n#endif\n' > "$T/h_sin"
cp "$T/h_bien" "$T/h_tocada"; echo '// cambiada' >> "$T/h_tocada"
printf '%s %s\n' "$COMMIT_DAY335" "$(ch_sha256 "$T/h_bien")" > "$T/m_bien"
printf '%s %s\n' "$OTRO_COMMIT" "$(ch_sha256 "$T/h_bien")" > "$T/m_otro"
printf '%s\n' "$COMMIT_DAY335" > "$T/m_sin_sha"

version_es() { [ "$(ch_version_de_cabecera "$1")" = "$2" ]; }
sha_es() { [ "$(ch_sha256 "$1")" = "$2" ]; }
version_repo() { gf_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(gf_commit_de_fichero "$src/COMMIT")" = "$1" ]; }
carga_lib() { declare -F gf_clonar >/dev/null; }

los_casos() {
  acepta "cpphttplib_instalar.sh carga lib_git_fijado.sh (gf_clonar definida)" carga_lib
  acepta "versión de la cabecera del tag v0.67.0" version_es "$T/h_bien" 0.67.0
  acepta "versión de una cabecera 0.66.0" version_es "$T/h_otra" 0.66.0
  acepta "cabecera sin CPPHTTPLIB_VERSION: vacío" version_es "$T/h_sin" ""
  acepta "cabecera que no existe: vacío" version_es "$T/no_existe" ""
  acepta "sha256 de un fichero conocido" sha_es "$T/h_sin" "$(printf '#ifndef CPPHTTPLIB_HTTPLIB_H\n#endif\n' | { command -v sha256sum >/dev/null && sha256sum || shasum -a 256; } | cut -d' ' -f1)"
  acepta "estado: cabecera 0.67.0 y marca con su commit y su sha256" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_bien"
  rechaza "estado: la cabecera dice otra versión (0.66.0)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_otra" "$T/m_bien"
  rechaza "estado: cabecera cambiada después de instalar (otro sha256)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_tocada" "$T/m_bien"
  rechaza "estado: la marca dice otro commit" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_otro"
  rechaza "estado: marca sin sha256 (solo el commit)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_sin_sha"
  rechaza "estado: sin marca (la httplib.h de antes, de la rama principal)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/no_existe"
  rechaza "estado: sin cabecera" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/no_existe" "$T/m_bien"
  acepta "provisioning/cpp-httplib/VERSION bien formado" version_repo
  acepta "provisioning/cpp-httplib/COMMIT es el del tag v0.67.0 (medido DAY335)" commit_repo_es "$COMMIT_DAY335"
  rechaza "provisioning/cpp-httplib/COMMIT no es otro commit" commit_repo_es "$OTRO_COMMIT"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
ch_estado() { return 0; }
commit_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-cpphttplib-instalar" || { echo "❌ test-cpphttplib-instalar: $total fallos"; exit 1; }
''',
}
CAMBIOS = {
    'Vagrantfile': [(r'''      # cpp-httplib
      if [ ! -f /usr/local/include/httplib.h ]; then
        cd /tmp && rm -rf cpp-httplib
        git clone https://github.com/yhirose/cpp-httplib.git
        mkdir -p /usr/local/include
        cp cpp-httplib/httplib.h /usr/local/include/
      fi
''', r'''      # [TERCEROS-HTTPLIB-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente cpp-httplib: httplib.h del repositorio
      # oficial (github.com/yhirose/cpp-httplib) en el tag de provisioning/cpp-httplib/VERSION, comprobado contra el commit
      # de provisioning/cpp-httplib/COMMIT (scripts/terceros/cpphttplib_instalar.sh). Antes: git clone de la rama
      # principal, sin tag ni commit, y solo si no había httplib.h (medido DAY335: la del lab decía 0.67.0 sin saber de
      # qué commit). Si falla, para aquí.
      bash /vagrant/scripts/terceros/cpphttplib_instalar.sh || { echo "❌ cpp-httplib"; exit 1; }
''', 1)],
    'Makefile': [('\t@$(EMECAS_PASO) test-libbpf-instalar -- $(MAKE) test-libbpf-instalar\n', '\t@$(EMECAS_PASO) test-libbpf-instalar -- $(MAKE) test-libbpf-instalar\n\t@$(EMECAS_PASO) test-cpphttplib-instalar -- $(MAKE) test-cpphttplib-instalar\n', 1), ('.PHONY: test-libbpf-instalar\ntest-libbpf-instalar:\n\t@bash scripts/terceros/test_libbpf_instalar.sh\n', '.PHONY: test-libbpf-instalar\ntest-libbpf-instalar:\n\t@bash scripts/terceros/test_libbpf_instalar.sh\n\n# [TERCEROS-HTTPLIB-D335] test-cpphttplib-instalar (Mac, sin VMs ni red): las funciones de\n# scripts/terceros/cpphttplib_instalar.sh (versión de la cabecera, la marca con el commit y el sha256 de la httplib.h\n# instalada) y provisioning/cpp-httplib/{VERSION,COMMIT}, también contra funciones que lo aceptan todo. El tag contra el\n# commit y los reintentos, en test-lib-git-fijado.\n.PHONY: test-cpphttplib-instalar\ntest-cpphttplib-instalar:\n\t@bash scripts/terceros/test_cpphttplib_instalar.sh\n', 1)],
}

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    raiz = pathlib.Path('.')
    if not (raiz / 'scripts/terceros/lib_git_fijado.sh').is_file():
        sys.exit('FALLA: falta scripts/terceros/lib_git_fijado.sh (piezas 1 y 1b). Nada escrito.')
    salida = {}
    for f in NUEVOS:
        if (raiz / f).exists():
            sys.exit(f'FALLA: {f} ya existe. Nada escrito.')
        salida[f] = NUEVOS[f].encode()
    for f, esperado in PARTIDA.items():
        b = (raiz / f).read_bytes()
        if sha(b) != esperado:
            sys.exit(f'FALLA: {f} sha256 de partida {sha(b)}, se espera {esperado}. Nada escrito.')
        t = b.decode()
        for viejo, nuevo, veces in CAMBIOS[f]:
            n = t.count(viejo)
            if n != veces:
                sys.exit(f'FALLA: {f}: el ancla aparece {n} veces, se esperan {veces}:\n{viejo[:120]}\nNada escrito.')
            t = t.replace(viejo, nuevo)
        salida[f] = t.encode()
    for f, b in salida.items():
        if sha(b) != LLEGADA[f]:
            sys.exit(f'FALLA: {f} sha256 de llegada {sha(b)}, se espera {LLEGADA[f]}. Nada escrito.')
    for f, b in salida.items():
        (raiz / f).parent.mkdir(parents=True, exist_ok=True)
        (raiz / f).write_bytes(b)
        print(f'OK {f} {sha(b)}')

if __name__ == '__main__':
    main()
