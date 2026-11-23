#!/usr/bin/env python3
# d335_etcdcpp_parche.py — [TERCEROS-ETCDCPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente etcd-cpp-apiv3:
# crea provisioning/etcd-cpp-apiv3/{VERSION,COMMIT}, scripts/terceros/etcdcpp_instalar.sh y su test; el Vagrantfile
# llama al instalador en lugar del git clone y checkout del tag; el Makefile gana test-etcdcpp-instalar y su paso en el
# EMECAS. Va encima de la lente cpp-httplib (d335_httplib_parche.py).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_etcdcpp_parche.py
# Comprueba el sha256 de partida, que los nuevos no existan, cada ancla las veces exactas, el sha256 de llegada, y no
# escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {'Vagrantfile': '6362c2a91ac883d276867a2d557f4c35b39cd345902cb42baf2fbd688e4cea3a', 'Makefile': 'a4560e2df118c8a90567ebf0627609cf74e679fa3d3d8b0de6a31c9c50a39f35'}
LLEGADA = {'Vagrantfile': '2b6bcc6fc23f8ec199d4017e93d59a5f3f2389c83ad33e6d98136f7831052982', 'Makefile': 'ff0be8aaef26953e4f01b77da8f8d2741d46a8ab360fa8655dce279ab4b24daf', 'provisioning/etcd-cpp-apiv3/VERSION': 'fad958a3c5fecd33c2b2bc667b8ad8661fce304517d3167543e93761fd155599', 'provisioning/etcd-cpp-apiv3/COMMIT': '1628bf838e77aa1f316cfa272d0f4b2591700e5e174d6b10f3b016ed0704eabd', 'scripts/terceros/etcdcpp_instalar.sh': 'be4803cdd515e797764c46be74125d58214fb234b0f45afa0769f167b80b2f16', 'scripts/terceros/test_etcdcpp_instalar.sh': '233a5749460539a238e63b0675e001fff4a1fc876da721c65f452044de61e347'}
NUEVOS = {
    'provisioning/etcd-cpp-apiv3/VERSION': r'''0.15.3
''',
    'provisioning/etcd-cpp-apiv3/COMMIT': r'''# provisioning/etcd-cpp-apiv3/COMMIT — [TERCEROS-ETCDCPP-D335] commit del repositorio oficial de etcd-cpp-apiv3
# (https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3) al que apunta el tag v<VERSION> de provisioning/etcd-cpp-apiv3/VERSION.
# Medido DAY335: el tag v0.15.3 es ligero (sin objeto tag ni firma) y apunta a e31ac4d4caa55fa662e207150ba40f8151b7ad96,
# "Bump up etcd-cpp-apiv3 to v0.15.3" (Tao He, 2023-07-27), commit sin firma; git ls-remote da el mismo. etcd-cpp-apiv3
# no publica firma ni hash de sus versiones: lo que manda es este commit (SHA-1 de git). Un tag ligero se puede mover;
# si el tag deja de apuntar aquí, la instalación para. Antes (hasta DAY334): git clone y git checkout v0.15.3, sin
# comprobar a qué commit apuntaba el tag. Hay una v0.15.4 (ba621638…): subir de versión es otro cambio, con su EMECAS.
# Si cambia VERSION, cambia esto (medido igual). Una sola línea sin comentar: 40 hexadecimales en minúscula.
e31ac4d4caa55fa662e207150ba40f8151b7ad96
''',
    'scripts/terceros/etcdcpp_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/etcdcpp_instalar.sh — [TERCEROS-ETCDCPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# etcd-cpp-apiv3: el cliente C++ de etcd (libetcd-cpp-api.so), compilado desde el repositorio oficial
# (github.com/etcd-cpp-apiv3/etcd-cpp-apiv3), en el tag v<VERSION> y comprobado que el tag apunta al commit fijado. Lo
# usan etcd-server y ml-detector. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del Vagrantfile,
# después de instalar gRPC, protobuf y cpprest de apt. Lee de provisioning/etcd-cpp-apiv3/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 0.15.3)
#   COMMIT   commit al que apunta el tag v<VERSION> (40 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): git clone y git checkout v0.15.3 sin comprobar a qué commit apuntaba, solo si no había
# libetcd-cpp-api.so ni .a, y un fallo de make no paraba el aprovisionamiento.
# Medido DAY335 (CMakeLists.txt de la v0.15.3): con el build por defecto la única biblioteca real es libetcd-cpp-api.so
# (etcd-cpp-api-core es una interfaz de CMake), sin SOVERSION, en /usr/local/lib; la versión queda en
# lib/cmake/etcd-cpp-api/etcd-cpp-api-config-version.cmake (PACKAGE_VERSION).
# Idempotente: si la marca /usr/local/lib/argus-etcd-cpp-api.commit dice este commit y el sha256 de la
# libetcd-cpp-api.so instalada, y el fichero de versión de CMake dice esta versión, no baja ni compila nada. Una sin
# marca (la de antes) o cambiada después se recompila. Las funciones ec_*, y las gf_* de lib_git_fijado.sh, no tocan el
# sistema (las prueban scripts/terceros/test_etcdcpp_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ETCDCPP] $*"; }
fallo() { echo "[TERCEROS-ETCDCPP] FALLA: $*"; exit 1; }
EC_URL=https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git
EC_PREFIJO=/usr/local
EC_SO=$EC_PREFIJO/lib/libetcd-cpp-api.so
EC_CFGVER=$EC_PREFIJO/lib/cmake/etcd-cpp-api/etcd-cpp-api-config-version.cmake

# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

# ec_version_de_cmake FICHERO -> la versión de su set(PACKAGE_VERSION "X.Y.Z"); vacío si no hay
ec_version_de_cmake() {
  sed -n 's/^set(PACKAGE_VERSION "\([^"]*\)")$/\1/p' "$1" 2>/dev/null | head -1
}

# ec_sha256 FICHERO -> el sha256 del fichero al que apunta (sigue enlaces); vacío si no existe
ec_sha256() {
  local f
  [ -e "$1" ] || return 0
  f=$(readlink -f "$1" 2>/dev/null || echo "$1")
  if command -v sha256sum >/dev/null; then sha256sum "$f" | cut -d' ' -f1; else shasum -a 256 "$f" | cut -d' ' -f1; fi
}

# ec_estado VERSION COMMIT SO CFGVER MARCA -> rc 0 si existe SO, CFGVER dice VERSION y la marca dice "COMMIT <sha256 de
# SO>"; si no, rc 1 y el motivo
ec_estado() {
  local v s
  [ -e "$3" ] || { echo "no hay $3"; return 1; }
  v=$(ec_version_de_cmake "$4")
  [ "$v" = "$1" ] || { echo "$4 dice la versión '${v}', se espera $1"; return 1; }
  s=$(ec_sha256 "$3")
  [ "$(cat "$5" 2>/dev/null)" = "$2 $s" ] || { echo "la marca $5 no dice el commit $2 y el sha256 $s de $3"; return 1; }
}

main() {
  local src=${ETCDCPP_SRC:-/vagrant/provisioning/etcd-cpp-apiv3} v c tmp r marca=/usr/local/lib/argus-etcd-cpp-api.commit
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  gf_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z: p. ej. 0.15.3). ERROR DE FABRICANTE: avisar a aRGus"
  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo "$src/COMMIT: hace falta una línea sin comentar de 40 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y commit ${c:0:12}... (de $src)"
  if r=$(ec_estado "$v" "$c" "$EC_SO" "$EC_CFGVER" "$marca"); then
    log "✅ etcd-cpp-apiv3 $v ya instalada (marca $marca)"; return 0
  fi
  log "hay que instalar: $r"
  command -v git >/dev/null || apt-get install -y git >/dev/null || fallo "apt-get install git"
  tmp=$(mktemp -d)
  r=$(gf_clonar "$EC_URL" "v$v" "$tmp/etcd-cpp-apiv3" "$c") || { rm -rf "$tmp"; fallo "$r"; }
  log "tag v$v clonado de $EC_URL y comprobado: commit $c"
  cmake -S "$tmp/etcd-cpp-apiv3" -B "$tmp/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX="$EC_PREFIJO" >/dev/null || { rm -rf "$tmp"; fallo "cmake de etcd-cpp-apiv3"; }
  make -C "$tmp/build" -j"$(nproc)" >/dev/null || { rm -rf "$tmp"; fallo "make de etcd-cpp-apiv3"; }
  make -C "$tmp/build" install >/dev/null || { rm -rf "$tmp"; fallo "make install de etcd-cpp-apiv3"; }
  rm -rf "$tmp"
  ldconfig
  printf '%s %s\n' "$c" "$(ec_sha256 "$EC_SO")" > "$marca"
  r=$(ec_estado "$v" "$c" "$EC_SO" "$EC_CFGVER" "$marca") || fallo "tras instalar: $r"
  log "✅ etcd-cpp-apiv3 $v (commit $c del repositorio oficial) en $EC_SO, sha256 $(ec_sha256 "$EC_SO")"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
''',
    'scripts/terceros/test_etcdcpp_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/test_etcdcpp_instalar.sh — [TERCEROS-ETCDCPP-D335] tests de las funciones ec_* de etcdcpp_instalar.sh
# y de provisioning/etcd-cpp-apiv3/{VERSION,COMMIT} (Mac, sin VMs ni red). El tag contra el commit fijado y los
# reintentos, en test_lib_git_fijado.sh. Medido DAY335: dos compilaciones del mismo commit dan libetcd-cpp-api.so con
# sha256 distinto (el build no es reproducible bit a bit); la marca guarda el sha256 de la instalada para ver si alguien
# la cambia después, no un sha256 de referencia: lo que se contrasta con el mantenedor es el commit. Cada caso de rechazo
# se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${ETCDCPP_SRC:-$aqui/../../provisioning/etcd-cpp-apiv3}
. "$aqui/etcdcpp_instalar.sh"

COMMIT_DAY335=e31ac4d4caa55fa662e207150ba40f8151b7ad96
OTRO_COMMIT=0123456789abcdef0123456789abcdef01234567
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# fichero de versión de CMake de juguete: su primera línea es la de la v0.15.3 instalada (medido DAY335)
cfgver() { printf 'set(PACKAGE_VERSION "%s")\n\n# Check whether the requested PACKAGE_FIND_VERSION is compatible\n' "$1"; }
cfgver 0.15.3 > "$T/v_bien"
cfgver 0.15.4 > "$T/v_otra"
printf '# sin versión\n' > "$T/v_sin"
printf 'biblioteca de juguete\n' > "$T/so_real"
ln -s so_real "$T/so_enlace"
cp "$T/so_real" "$T/so_tocada"; printf 'x' >> "$T/so_tocada"
printf '%s %s\n' "$COMMIT_DAY335" "$(ec_sha256 "$T/so_real")" > "$T/m_bien"
printf '%s %s\n' "$OTRO_COMMIT" "$(ec_sha256 "$T/so_real")" > "$T/m_otro"
printf '%s\n' "$COMMIT_DAY335" > "$T/m_sin_sha"

version_es() { [ "$(ec_version_de_cmake "$1")" = "$2" ]; }
mismo_sha() { [ -n "$(ec_sha256 "$1")" ] && [ "$(ec_sha256 "$1")" = "$(ec_sha256 "$2")" ]; }
sha_vacio() { [ -z "$(ec_sha256 "$1")" ]; }
version_repo() { gf_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(gf_commit_de_fichero "$src/COMMIT")" = "$1" ]; }
carga_lib() { declare -F gf_clonar >/dev/null; }

los_casos() {
  acepta "etcdcpp_instalar.sh carga lib_git_fijado.sh (gf_clonar definida)" carga_lib
  acepta "versión del fichero de CMake de la v0.15.3" version_es "$T/v_bien" 0.15.3
  acepta "versión de un fichero de CMake 0.15.4" version_es "$T/v_otra" 0.15.4
  acepta "fichero de CMake sin PACKAGE_VERSION: vacío" version_es "$T/v_sin" ""
  acepta "fichero de CMake que no existe: vacío" version_es "$T/no_existe" ""
  acepta "sha256 de un enlace = el del fichero al que apunta" mismo_sha "$T/so_enlace" "$T/so_real"
  acepta "sha256 de lo que no existe: vacío" sha_vacio "$T/no_existe"
  acepta "estado: .so, versión 0.15.3 y marca con su commit y su sha256" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_bien"
  acepta "estado: la .so por un enlace" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_enlace" "$T/v_bien" "$T/m_bien"
  rechaza "estado: el fichero de CMake dice otra versión (0.15.4)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_otra" "$T/m_bien"
  rechaza "estado: sin fichero de versión de CMake" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/no_existe" "$T/m_bien"
  rechaza "estado: .so cambiada después de instalar (otro sha256)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_tocada" "$T/v_bien" "$T/m_bien"
  rechaza "estado: la marca dice otro commit" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_otro"
  rechaza "estado: marca sin sha256 (solo el commit)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_sin_sha"
  rechaza "estado: sin marca (la .so de antes)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/no_existe"
  rechaza "estado: sin .so" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/no_existe" "$T/v_bien" "$T/m_bien"
  acepta "provisioning/etcd-cpp-apiv3/VERSION bien formado" version_repo
  acepta "provisioning/etcd-cpp-apiv3/COMMIT es el del tag v0.15.3 (medido DAY335)" commit_repo_es "$COMMIT_DAY335"
  rechaza "provisioning/etcd-cpp-apiv3/COMMIT no es otro commit" commit_repo_es "$OTRO_COMMIT"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
ec_estado() { return 0; }
commit_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-etcdcpp-instalar" || { echo "❌ test-etcdcpp-instalar: $total fallos"; exit 1; }
''',
}
CAMBIOS = {
    'Vagrantfile': [(r'''      # etcd-cpp-api
      if [ ! -f /usr/local/lib/libetcd-cpp-api.so ] && [ ! -f /usr/local/lib/libetcd-cpp-api.a ]; then
        cd /tmp && rm -rf etcd-cpp-apiv3
        git clone https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git
        cd etcd-cpp-apiv3 && git checkout v0.15.3
        mkdir build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=/usr/local
        make -j4 && make install
        ldconfig
      fi
''', r'''      # [TERCEROS-ETCDCPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente etcd-cpp-apiv3: libetcd-cpp-api.so
      # compilada desde el repositorio oficial (github.com/etcd-cpp-apiv3/etcd-cpp-apiv3) en el tag de
      # provisioning/etcd-cpp-apiv3/VERSION, comprobado contra el commit de provisioning/etcd-cpp-apiv3/COMMIT
      # (scripts/terceros/etcdcpp_instalar.sh). Antes: git clone y checkout del tag sin comprobar a qué apuntaba, y un
      # fallo de make no paraba. Si falla, para aquí.
      bash /vagrant/scripts/terceros/etcdcpp_instalar.sh || { echo "❌ etcd-cpp-apiv3"; exit 1; }
''', 1)],
    'Makefile': [('\t@$(EMECAS_PASO) test-cpphttplib-instalar -- $(MAKE) test-cpphttplib-instalar\n', '\t@$(EMECAS_PASO) test-cpphttplib-instalar -- $(MAKE) test-cpphttplib-instalar\n\t@$(EMECAS_PASO) test-etcdcpp-instalar -- $(MAKE) test-etcdcpp-instalar\n', 1), ('.PHONY: test-cpphttplib-instalar\ntest-cpphttplib-instalar:\n\t@bash scripts/terceros/test_cpphttplib_instalar.sh\n', '.PHONY: test-cpphttplib-instalar\ntest-cpphttplib-instalar:\n\t@bash scripts/terceros/test_cpphttplib_instalar.sh\n\n# [TERCEROS-ETCDCPP-D335] test-etcdcpp-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/etcdcpp_instalar.sh\n# (versión del fichero de CMake, la marca con el commit y el sha256 de la libetcd-cpp-api.so instalada) y\n# provisioning/etcd-cpp-apiv3/{VERSION,COMMIT}, también contra funciones que lo aceptan todo. El tag contra el commit y\n# los reintentos, en test-lib-git-fijado.\n.PHONY: test-etcdcpp-instalar\ntest-etcdcpp-instalar:\n\t@bash scripts/terceros/test_etcdcpp_instalar.sh\n', 1)],
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
