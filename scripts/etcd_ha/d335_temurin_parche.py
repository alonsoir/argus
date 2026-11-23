#!/usr/bin/env python3
# d335_temurin_parche.py — [TERCEROS-TEMURIN-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Temurin: crea
# provisioning/temurin/{VERSION,CLAVE}, scripts/terceros/temurin_instalar.sh y su test; jenkins_instalar.sh lo llama y
# toma su JAVA_DIR; el Vagrantfile deja de instalar SDKMAN con curl | bash; el Makefile gana test-temurin-instalar y su
# paso en el EMECAS. Va encima de terceros/d335-cmake-cryptopp (7cdad31).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_temurin_parche.py
# Comprueba el sha256 de partida, que los nuevos no existan, cada ancla las veces exactas, el sha256 de llegada, y no
# escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {'Vagrantfile': '01783dec16c7620bcff037340c44b25315b642ec517529de7b54caf3d0e3d13d', 'scripts/jenkins/jenkins_instalar.sh': 'ab502b6cdfd53dc2dd94e748527780021c06c0e74e29b296b7205aa9ce6c53e8', 'Makefile': 'fa9647779498a2daecab4f8e315e4619def21aba41d18d16ab9d6ce52689e278'}
LLEGADA = {'Vagrantfile': '7b1d8afa10b28fbb6505612a136716e045a42fd8b4f9a890b07c14e6f5050a1a', 'scripts/jenkins/jenkins_instalar.sh': 'e373f9e3fc69c0350b371d86d2f8cc7d6c387e0805facb599b5d7c6bfb04fc37', 'Makefile': '172cb7a798975c8a3603a5a00d54e8565a611eb40558d1aa9883f6bcb4468c46', 'provisioning/temurin/VERSION': '6b1d7d4b99ec1473e27b174e3b375e57ff2627af5c497228e8339690d6853125', 'provisioning/temurin/CLAVE': '6024d439f4dd633407010491d33dc03db3b0188bf50429de7b5c7499d5293219', 'scripts/terceros/temurin_instalar.sh': '15a39b52278f9fe0f2247180c61e78f5c5c95edcc55edfd9ff78df9e23eb39bb', 'scripts/terceros/test_temurin_instalar.sh': '8e894810222afb2d6cdc3447c5ffa58754416c2ae6ccd231b629df39583311aa'}
NUEVOS = {
    'provisioning/temurin/VERSION': r'''21.0.7.0.0+6-0
''',
    'provisioning/temurin/CLAVE': r'''# provisioning/temurin/CLAVE — [TERCEROS-TEMURIN-D335] huella de la clave con la que Adoptium (Eclipse Foundation) firma
# su repositorio apt (https://packages.adoptium.net/artifactory/deb) y los binarios de Temurin. Clave:
# https://packages.adoptium.net/artifactory/api/gpg/key/public ("Adoptium GPG Key (DEB/RPM Signing Key)
# <temurin-dev@eclipse.org>", RSA, creada el 16-nov-2021, sin caducidad). scripts/vigilancia/lib_apt_oficial.sh la
# descarga y SOLO la instala si todas sus claves principales están aquí.
# Medido DAY335 por dos canales: la huella de la clave descargada de packages.adoptium.net, y la que publica Adoptium en
# su página de verificación (https://adoptium.net/installation/gpg-verification/) y en su blog de julio de 2022
# (https://adoptium.net/blog/2022/07/gpg-signed-releases/). Con ella, gpgv da firma buena al InRelease de bookworm.
3B04D753C9050D9A5D343F39843C48A565F8F04B
''',
    'scripts/terceros/temurin_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/temurin_instalar.sh — [TERCEROS-TEMURIN-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# Temurin: el JDK de Eclipse Temurin (Adoptium) desde su repositorio apt oficial, con la clave comprobada por huella y
# la versión fijada. Solo lo usa Jenkins (2.555+ pide Java 21): lo llama scripts/jenkins/jenkins_instalar.sh, en el
# defender, como root. Lee de provisioning/temurin/:
#   VERSION  versión exacta del paquete deb, A.B.C.D.E+N-M (p. ej. 21.0.7.0.0+6-0); el paquete es temurin-<A>-jdk
#   CLAVE    huella de la clave de firma del repositorio (lib_apt_oficial.sh)
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): `curl -s https://get.sdkman.io | bash` como root, sin firma ni hash, y `sdk install java
# 21.0.7-tem` en /root/.sdkman. Medido DAY335: el .deb de temurin-21-jdk deja el JDK en /usr/lib/jvm/temurin-21-jdk-amd64
# y su postinst registra java, javac, keytool... en update-alternatives (prioridad 2111); en el repo solo Jenkins usa
# Java. Depende de adoptium-ca-certificates, del mismo repositorio firmado.
# Si algo falla, retira el repositorio de Adoptium (para no romper los apt-get update siguientes) y sale con 1.
# Idempotente: con el paquete en su versión y su java diciendo esa versión, no toca nada. Al acabar borra /root/.sdkman
# (lo de antes; ya nadie lo usa). Las funciones tm_* no tocan el sistema (las prueba
# scripts/terceros/test_temurin_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-TEMURIN] $*"; }
fallo() { echo "[TERCEROS-TEMURIN] FALLA: $*"; exit 1; }
TM_URL_CLAVE=https://packages.adoptium.net/artifactory/api/gpg/key/public
TM_URL_REPO=https://packages.adoptium.net/artifactory/deb
TM_LISTA=/etc/apt/sources.list.d/adoptium.list
TM_ANILLO=/usr/share/keyrings/adoptium.gpg

# tm_version_valida VERSION -> rc 0 si es A.B.C.D.E+N-M (la cadena entera: un salto de línea dentro también es error)
tm_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}([.][0-9]{1,3}){4}[+][0-9]{1,3}-[0-9]{1,3}$ ]]
}

# tm_mayor VERSION -> la versión mayor de Java (21 de 21.0.7.0.0+6-0)
tm_mayor() { printf '%s\n' "${1%%.*}"; }

# tm_esperado VERSION -> lo que dice `java -version` en su línea "Runtime Environment Temurin-X+B": de 21.0.7.0.0+6-0
# sale 21.0.7+6 y de 21.0.12.1.0+1-0, 21.0.12.1+1 (se quitan los .0 del final, dejando al menos tres números)
tm_esperado() {
  local n=${1%%+*} b=${1#*+} p
  b=${b%%-*}
  p=${n//[^.]/}
  while [ "${#p}" -gt 2 ] && [[ "$n" == *.0 ]]; do n=${n%.0}; p=${n//[^.]/}; done
  printf 'Temurin-%s+%s\n' "$n" "$b"
}

# tm_java_cuadra VERSION SALIDA -> rc 0 si SALIDA (de `java -version`) tiene la línea "Runtime Environment
# Temurin-X+B (build ..." de esa versión (medido DAY335 con la 21.0.7 de SDKMAN:
# "OpenJDK Runtime Environment Temurin-21.0.7+6 (build 21.0.7+6-LTS)")
tm_java_cuadra() {
  printf '%s\n' "$2" | grep -qF "Runtime Environment $(tm_esperado "$1") (build "
}

tm_retirar() { rm -f "$TM_LISTA" "$TM_ANILLO"; }

main() {
  local src=${TEMURIN_SRC:-/vagrant/provisioning/temurin} v mayor paquete dir codigo actual
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  tm_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (A.B.C.D.E+N-M: p. ej. 21.0.7.0.0+6-0). ERROR DE FABRICANTE: avisar a aRGus"
  mayor=$(tm_mayor "$v"); paquete=temurin-$mayor-jdk; dir=/usr/lib/jvm/temurin-$mayor-jdk-amd64
  log "paquete $paquete $v (de $src); se espera $(tm_esperado "$v") en $dir"
  actual=$(dpkg-query -W -f='${Version}' "$paquete" 2>/dev/null)
  if [ "$actual" = "$v" ] && tm_java_cuadra "$v" "$("$dir/bin/java" -version 2>&1)"; then
    log "✅ $paquete $v ya instalado"
  else
    codigo=$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")
    [[ "$codigo" =~ ^[a-z]{3,20}$ ]] || fallo "VERSION_CODENAME '$codigo' de /etc/os-release mal formado"
    # shellcheck source=../vigilancia/lib_apt_oficial.sh
    . "$(dirname "${BASH_SOURCE[0]}")/../vigilancia/lib_apt_oficial.sh" || fallo "no se pudo cargar lib_apt_oficial.sh"
    repo_oficial adoptium "$TM_URL_CLAVE" "$src/CLAVE" "$TM_URL_REPO" "$codigo main" \
      || { tm_retirar; fallo "la clave de $TM_URL_CLAVE no se pudo comprobar con $src/CLAVE (repositorio retirado)"; }
    apt-get update -qq || { tm_retirar; fallo "apt-get update con el repositorio de Adoptium (repositorio retirado)"; }
    instalar_fijado "$paquete" "$v" || { tm_retirar; fallo "apt-get install $paquete=$v (repositorio retirado)"; }
    tm_java_cuadra "$v" "$("$dir/bin/java" -version 2>&1)" \
      || { tm_retirar; fallo "$dir/bin/java no dice $(tm_esperado "$v") (repositorio retirado)"; }
    log "✅ $paquete $v (Adoptium, repositorio firmado con la clave de $src/CLAVE) en $dir, en hold"
  fi
  if [ -d /root/.sdkman ]; then
    rm -rf /root/.sdkman && log "borrado /root/.sdkman (el Java de antes, de SDKMAN)"
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
''',
    'scripts/terceros/test_temurin_instalar.sh': r'''#!/usr/bin/env bash
# scripts/terceros/test_temurin_instalar.sh — [TERCEROS-TEMURIN-D335] tests de las funciones tm_* de temurin_instalar.sh
# y de provisioning/temurin/{VERSION,CLAVE} (Mac, sin VMs ni red). La clave contra sus huellas, en repo_oficial
# (lib_apt_oficial.sh). Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar
# ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${TEMURIN_SRC:-$aqui/../../provisioning/temurin}
. "$aqui/temurin_instalar.sh"

HUELLA_DAY335=3B04D753C9050D9A5D343F39843C48A565F8F04B
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# `java -version` del Temurin 21.0.7 de SDKMAN en el defender (medido DAY335), y variantes
JAVA_21_0_7=$'openjdk version "21.0.7" 2025-04-15 LTS\nOpenJDK Runtime Environment Temurin-21.0.7+6 (build 21.0.7+6-LTS)\nOpenJDK 64-Bit Server VM Temurin-21.0.7+6 (build 21.0.7+6-LTS, mixed mode, sharing)'
JAVA_21_0_8=$'openjdk version "21.0.8" 2025-07-15 LTS\nOpenJDK Runtime Environment Temurin-21.0.8+9 (build 21.0.8+9-LTS)\nOpenJDK 64-Bit Server VM Temurin-21.0.8+9 (build 21.0.8+9-LTS, mixed mode, sharing)'
JAVA_OPENJDK=$'openjdk version "21.0.7" 2025-04-15\nOpenJDK Runtime Environment (build 21.0.7+6-Debian-1)\nOpenJDK 64-Bit Server VM (build 21.0.7+6-Debian-1, mixed mode, sharing)'
JAVA_NADA=$'bash: /usr/lib/jvm/temurin-21-jdk-amd64/bin/java: No such file or directory'

esperado_es() { [ "$(tm_esperado "$1")" = "$2" ]; }
mayor_es() { [ "$(tm_mayor "$1")" = "$2" ]; }
version_repo() { tm_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
version_repo_es() { [ "$(tr -d '[:space:]' < "$src/VERSION")" = "$1" ]; }
clave_repo_es() { [ "$(grep -v '^#' "$src/CLAVE" | tr -d ' \t\r' | grep -v '^$')" = "$1" ]; }

los_casos() {
  acepta "versión 21.0.7.0.0+6-0" tm_version_valida 21.0.7.0.0+6-0
  acepta "versión 21.0.12.1.0+1-0" tm_version_valida 21.0.12.1.0+1-0
  rechaza "versión 21.0.7+6 (la de java, no la del paquete)" tm_version_valida 21.0.7+6
  rechaza "versión 21.0.7.0.0+6 (sin revisión del paquete)" tm_version_valida 21.0.7.0.0+6
  rechaza "versión latest (por nombre)" tm_version_valida latest
  rechaza "dos versiones en dos líneas" tm_version_valida $'21.0.7.0.0+6-0\n21.0.8.0.0+9-0'
  acepta "mayor de 21.0.7.0.0+6-0: 21" mayor_es 21.0.7.0.0+6-0 21
  acepta "esperado de 21.0.7.0.0+6-0: Temurin-21.0.7+6" esperado_es 21.0.7.0.0+6-0 Temurin-21.0.7+6
  acepta "esperado de 21.0.12.1.0+1-0: Temurin-21.0.12.1+1" esperado_es 21.0.12.1.0+1-0 Temurin-21.0.12.1+1
  acepta "esperado de 21.0.0.0.0+35-0: Temurin-21.0.0+35 (deja tres números)" esperado_es 21.0.0.0.0+35-0 Temurin-21.0.0+35
  acepta "java de la 21.0.7 (medido DAY335) cuadra con 21.0.7.0.0+6-0" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_21_0_7"
  rechaza "java de la 21.0.8 con 21.0.7.0.0+6-0" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_21_0_8"
  rechaza "un OpenJDK que no es Temurin, misma versión" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_OPENJDK"
  rechaza "sin java" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_NADA"
  rechaza "salida vacía" tm_java_cuadra 21.0.7.0.0+6-0 ""
  acepta "provisioning/temurin/VERSION bien formado" version_repo
  acepta "provisioning/temurin/VERSION es la 21.0.7 de antes (la de SDKMAN, medido DAY335)" version_repo_es 21.0.7.0.0+6-0
  acepta "provisioning/temurin/CLAVE es la huella de Adoptium (medido DAY335, dos canales)" clave_repo_es "$HUELLA_DAY335"
  rechaza "provisioning/temurin/CLAVE no es otra huella" clave_repo_es 5E386EADB55F01504CAE8BCF7198F4B714ABFC68
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
tm_version_valida() { return 0; }
tm_java_cuadra() { return 0; }
clave_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-temurin-instalar" || { echo "❌ test-temurin-instalar: $total fallos"; exit 1; }
''',
}
CAMBIOS = {
    'Vagrantfile': [('      # ── Java 21 via SDKMAN (requerido por Jenkins 2.555+) ──────────────────\n      # Fix DAY 160: Java 21 no está en repos Bookworm — SDKMAN + Temurin\n      # Jenkins 2.555.2 requiere Java 21 mínimo (Java 17 falla silenciosamente)\n      if [ ! -f /root/.sdkman/candidates/java/21.0.7-tem/bin/java ]; then\n        echo "📦 Instalando prereqs SDKMAN (unzip, zip)..."\n        apt-get install -y unzip zip 2>&1 | tail -1\n        echo "📦 Instalando SDKMAN..."\n        curl -s https://get.sdkman.io | bash\n        echo "📦 Instalando Java 21.0.7 Temurin via SDKMAN..."\n        source /root/.sdkman/bin/sdkman-init.sh\n        sdk install java 21.0.7-tem < /dev/null\n        echo "✅ Java 21 Temurin instalado"\n      else\n        echo "✅ Java 21 Temurin ya instalado"\n      fi\n', '      # ── Java 21 (requerido por Jenkins 2.555+) ──────────────────────────────\n      # [TERCEROS-TEMURIN-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: lo instala\n      # scripts/jenkins/jenkins_instalar.sh (justo debajo) con scripts/terceros/temurin_instalar.sh: Temurin del\n      # repositorio apt de Adoptium, con la clave comprobada por huella (provisioning/temurin/CLAVE) y versión fijada.\n      # Antes, aquí: SDKMAN con `curl -s https://get.sdkman.io | bash` como root, sin firma ni hash, y unzip y zip solo\n      # para él.\n', 1)],
    'scripts/jenkins/jenkins_instalar.sh': [('JAVA_DIR=/root/.sdkman/candidates/java/21.0.7-tem   # Fix DAY 160: Jenkins 2.555+ requiere Java 21 (SDKMAN + Temurin)\n', '# [TERCEROS-TEMURIN-D335] Jenkins 2.555+ requiere Java 21 (Fix DAY 160): el de scripts/terceros/temurin_instalar.sh,\n# en el directorio del paquete temurin-<mayor>-jdk (la mayor, de provisioning/temurin/VERSION)\nTEMURIN_VERSION=$(tr -d \'[:space:]\' < "$RAIZ/provisioning/temurin/VERSION" 2>/dev/null)\nJAVA_DIR=/usr/lib/jvm/temurin-${TEMURIN_VERSION%%.*}-jdk-amd64\n', 1), ('rm -f /etc/default/jenkins\n', 'rm -f /etc/default/jenkins\n# [TERCEROS-TEMURIN-D335] sin Java no hay Jenkins: se avisa en alto y el lab sigue sin él (decisión de Alonso DAY323)\nbash "$RAIZ/scripts/terceros/temurin_instalar.sh" || retirar "Temurin (Java en $JAVA_DIR) no se pudo instalar"\n', 1), ('# Fix DAY 160: Jenkins como root en dev, con Java 21 de /root/.sdkman\n', '# Fix DAY 160: Jenkins como root en dev, con el Java 21 de Temurin ($JAVA_DIR)\n', 1)],
    'Makefile': [('\t@$(EMECAS_PASO) test-kuzu-instalar -- $(MAKE) test-kuzu-instalar\n', '\t@$(EMECAS_PASO) test-kuzu-instalar -- $(MAKE) test-kuzu-instalar\n\t@$(EMECAS_PASO) test-temurin-instalar -- $(MAKE) test-temurin-instalar\n', 1), ('.PHONY: test-kuzu-instalar\ntest-kuzu-instalar:\n\t@bash scripts/terceros/test_kuzu_instalar.sh\n', '.PHONY: test-kuzu-instalar\ntest-kuzu-instalar:\n\t@bash scripts/terceros/test_kuzu_instalar.sh\n\n# [TERCEROS-TEMURIN-D335] test-temurin-instalar (Mac, sin VMs ni red): las funciones de\n# scripts/terceros/temurin_instalar.sh (VERSION del paquete, qué dice java -version de esa versión) y\n# provisioning/temurin/{VERSION,CLAVE}, también contra funciones que lo aceptan todo. La clave contra sus huellas, en\n# repo_oficial (lib_apt_oficial.sh).\n.PHONY: test-temurin-instalar\ntest-temurin-instalar:\n\t@bash scripts/terceros/test_temurin_instalar.sh\n', 1)],
}

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    raiz = pathlib.Path('.')
    if not (raiz / 'scripts/terceros/lib_git_fijado.sh').is_file():
        sys.exit('FALLA: falta scripts/terceros/lib_git_fijado.sh (¿rama equivocada?). Nada escrito.')
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
