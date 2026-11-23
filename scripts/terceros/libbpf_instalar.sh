#!/usr/bin/env bash
# scripts/terceros/libbpf_instalar.sh — [TERCEROS-LIBBPF-D334] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# libbpf: libbpf compilada desde el repositorio oficial (github.com/libbpf/libbpf), en el tag v<VERSION> y comprobado
# que el tag apunta al commit fijado. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del
# Vagrantfile. Lee de provisioning/libbpf/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 1.4.6)
#   COMMIT   commit al que apunta el tag v<VERSION> (40 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY333): git clone del tag sin comprobar a qué apuntaba, y solo si la libbpf instalada era < 1.2.0 (una
# 1.3 o una 1.8 se daban por buenas). Medido DAY334:
#   - el sniffer enlaza libbpf.so.1 dinámica (objdump -p), aunque se compilaba con BUILD_STATIC_ONLY=y: en src/Makefile
#     de la v1.4.6, install depende de all, y sin BUILD_STATIC_ONLY en esa llamada all incluye la compartida. Aquí se
#     compilan las dos a la vez, sin ese engaño.
#   - hay dos libbpf.so.1 con el mismo SONAME: la nuestra en /usr/lib64 y la 1.1.2 de bookworm (libbpf1, la pide
#     iproute2: no se puede quitar) en /usr/lib/x86_64-linux-gnu. El sniffer carga la de /usr/lib64 (/proc/<pid>/maps)
#     solo porque ldconfig la pone primero (/etc/ld.so.conf.d/libbpf.conf). Este script comprueba al final que
#     libbpf.so.1 se resuelve a /usr/lib64/libbpf.so.<VERSION>; si no, para: la 1.1.2 tiene el fallo de mapas BPF que
#     se corrigió en la 1.2.0.
# Idempotente: si la marca /usr/local/lib/argus-libbpf.commit dice este commit, pkg-config da esta versión y libbpf.so.1
# se resuelve a la nuestra, no baja ni compila nada. Las funciones lb_*, y las gf_* de lib_git_fijado.sh, no tocan el
# sistema (las prueban scripts/terceros/test_libbpf_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-LIBBPF] $*"; }
fallo() { echo "[TERCEROS-LIBBPF] FALLA: $*"; exit 1; }
LB_URL=https://github.com/libbpf/libbpf.git
LB_LIBDIR=/usr/lib64

# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado (la
# comparten los instaladores que traen código de terceros por git)
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

# lb_primera_resolucion TEXTO_LDCONFIG -> la ruta de la primera entrada libbpf.so.1 de `ldconfig -p` (la que usa el
# cargador); vacío si no hay
lb_primera_resolucion() {
  printf '%s\n' "$1" | sed -n 's/^[[:space:]]*libbpf\.so\.1 (.*) => //p' | head -1
}

# lb_carga_ok VERSION PRIMERA REAL -> rc 0 si la primera entrada de ldconfig es LB_LIBDIR/libbpf.so.1 y su destino real
# es LB_LIBDIR/libbpf.so.VERSION
lb_carga_ok() {
  [ "$2" = "$LB_LIBDIR/libbpf.so.1" ] && [ "$3" = "$LB_LIBDIR/libbpf.so.$1" ]
}

# lb_estado VERSION COMMIT MARCA -> rc 0 si todo dice la versión y el commit fijados; si no, rc 1 y el motivo
lb_estado() {
  local pc primera real
  pc=$(PKG_CONFIG_PATH=$LB_LIBDIR/pkgconfig pkg-config --modversion libbpf 2>/dev/null)
  [ "$pc" = "$1" ] || { echo "pkg-config da '${pc}', se espera $1"; return 1; }
  [ "$(cat "$3" 2>/dev/null)" = "$2" ] || { echo "la marca $3 no dice el commit $2"; return 1; }
  primera=$(lb_primera_resolucion "$(/sbin/ldconfig -p)")
  real=$(readlink -f "${primera:-/no-existe}" 2>/dev/null)
  lb_carga_ok "$1" "$primera" "$real" || { echo "libbpf.so.1 se resuelve a '${primera}' (-> '${real}'), se espera $LB_LIBDIR/libbpf.so.$1"; return 1; }
}

main() {
  local src=${LIBBPF_SRC:-/vagrant/provisioning/libbpf} v c tmp r marca=/usr/local/lib/argus-libbpf.commit
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  gf_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z: p. ej. 1.4.6). ERROR DE FABRICANTE: avisar a aRGus"
  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo "$src/COMMIT: hace falta una línea sin comentar de 40 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y commit ${c:0:12}... (de $src)"
  if r=$(lb_estado "$v" "$c" "$marca"); then
    log "✅ libbpf $v ya instalada (marca $marca; libbpf.so.1 -> $LB_LIBDIR/libbpf.so.$v)"; return 0
  fi
  log "hay que instalar: $r"
  apt-get install -y libelf-dev zlib1g-dev pkg-config git >/dev/null || fallo "apt-get install libelf-dev zlib1g-dev pkg-config git"
  tmp=$(mktemp -d)
  r=$(gf_clonar "$LB_URL" "v$v" "$tmp/libbpf" "$c") || { rm -rf "$tmp"; fallo "$r"; }
  log "tag v$v clonado de $LB_URL y comprobado: commit $c"
  make -C "$tmp/libbpf/src" -j"$(nproc)" >/dev/null || { rm -rf "$tmp"; fallo "make de libbpf"; }
  make -C "$tmp/libbpf/src" install install_headers >/dev/null || { rm -rf "$tmp"; fallo "make install de libbpf"; }
  rm -rf "$tmp"
  grep -q "PKG_CONFIG_PATH.*usr/lib64/pkgconfig" /etc/environment 2>/dev/null \
    || echo 'PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"' >> /etc/environment
  cat > /etc/profile.d/libbpf.sh <<'PERFIL'
export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"
PERFIL
  chmod 0755 /etc/profile.d/libbpf.sh
  echo "$LB_LIBDIR" > /etc/ld.so.conf.d/libbpf.conf
  ldconfig
  printf '%s\n' "$c" > "$marca"
  r=$(lb_estado "$v" "$c" "$marca") || fallo "tras instalar: $r"
  log "✅ libbpf $v (commit $c del repositorio oficial) en $LB_LIBDIR; libbpf.so.1 -> $LB_LIBDIR/libbpf.so.$v"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
