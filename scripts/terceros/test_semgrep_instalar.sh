#!/usr/bin/env bash
# scripts/terceros/test_semgrep_instalar.sh — [SEMGREP-D340] tests de las funciones sg_* de semgrep_instalar.sh, del lock
# provisioning/semgrep/requirements.txt, del Vagrantfile, del Makefile y de contrib/audit/audit.mk (Mac, sin VMs ni red).
# Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el
# test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
raiz=$aqui/../..
vf=${SEMGREP_VAGRANTFILE:-$raiz/Vagrantfile}
lock=$raiz/provisioning/semgrep/requirements.txt
amk=$raiz/contrib/audit/audit.mk
. "$aqui/semgrep_instalar.sh"

casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
h=ad160ed527bd153b96616814366a6d17f451d37babf75df6705327aede0cc8bd
g=0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3
# Locks de juguete
printf '# comentario\n\nsemgrep==1.187.0 --hash=sha256:%s\nurllib3==2.8.0 --hash=sha256:%s\n' "$h" "$g" > "$tmp/l_bien"
printf 'semgrep==1.187.0\n' > "$tmp/l_sin_hash"
printf 'semgrep>=1.187 --hash=sha256:%s\n' "$h" > "$tmp/l_sin_igual"
printf 'semgrep --hash=sha256:%s\n' "$h" > "$tmp/l_sin_version"
printf 'semgrep==1.187.0 --hash=sha256:%s\n' "${h%?}" > "$tmp/l_hash_corto"
printf 'semgrep==1.187.0 --hash=sha256:%s0\n' "$h" > "$tmp/l_hash_largo"
printf 'semgrep==1.187.0 --hash=sha256:%s\n' "$(printf '%s' "$h" | tr a-f A-F)" > "$tmp/l_hash_mayus"
printf 'semgrep==1.187.0 --hash=md5:%s\n' "$h" > "$tmp/l_md5"
printf 'semgrep==1.187.0 --hash=sha256:%s --hash=sha256:%s\n' "$h" "$g" > "$tmp/l_dos_hashes"
printf -- '--index-url https://otro.example/simple\nsemgrep==1.187.0 --hash=sha256:%s\n' "$h" > "$tmp/l_index"
printf 'semgrep==1.187.0 --hash=sha256:%s\nSemgrep==1.187.0 --hash=sha256:%s\n' "$h" "$h" > "$tmp/l_repetido"
printf 'ruamel.yaml==0.19.1 --hash=sha256:%s\nruamel_yaml==0.19.1 --hash=sha256:%s\n' "$h" "$h" > "$tmp/l_repetido_punto"
printf '# solo comentarios\n\n' > "$tmp/l_vacio"
printf 'urllib3==2.8.0 --hash=sha256:%s\n' "$g" > "$tmp/l_sin_semgrep"
# Salidas de pip freeze de juguete, contra l_bien
printf 'semgrep==1.187.0\nurllib3==2.8.0\n' > "$tmp/f_igual"
printf 'Semgrep==1.187.0\nURLLIB3==2.8.0\n' > "$tmp/f_mayus"
printf 'semgrep==1.187.0\nurllib3==2.8.0\nsix==1.17.0\n' > "$tmp/f_sobra"
printf 'semgrep==1.187.0\n' > "$tmp/f_falta"
printf 'semgrep==1.186.0\nurllib3==2.8.0\n' > "$tmp/f_version"
printf 'semgrep @ file:///tmp/semgrep-1.187.0.whl\nurllib3==2.8.0\n' > "$tmp/f_file"
: > "$tmp/f_vacio"
# Salidas de semgrep --version de juguete
printf '1.187.0\n' > "$tmp/v_bien"
printf '1.187.0\nA new version of Semgrep is available\n' > "$tmp/v_aviso"
printf '1.186.0\n' > "$tmp/v_otra"
printf '1.187.01\n' > "$tmp/v_prefijo"
: > "$tmp/v_vacia"
# Vagrantfiles de juguete (el bloque de antes de DAY340 y variantes)
printf '      if ! command -v semgrep &>/dev/null; then\n        pip3 install semgrep --break-system-packages --quiet\n      fi\n' > "$tmp/vf_antes"
printf '      pip install semgrep==1.187.0\n' > "$tmp/vf_fijado"
printf '      pip3 install urllib3\n' > "$tmp/vf_urllib3"
printf '      # antes: pip3 install semgrep --break-system-packages --quiet\n      apt-get install -y cppcheck\n' > "$tmp/vf_limpio"
printf '      pip3 install semgrep-rules-manager\n' > "$tmp/vf_otro"

lock_tiene() { sg_normaliza "$lock" | grep -q -x -E "$1"; }
lock_paquetes() { [ "$(sg_normaliza "$lock" | wc -l | tr -d ' ')" = "$1" ]; }
audit_semgrep_llama() { grep -q -E '^[[:space:]]+@vagrant ssh defender -c "sudo SG_VENV=\$\(SEMGREP_VENV\) bash /vagrant/scripts/terceros/semgrep_instalar\.sh"$' "$amk"; }
venv_un_sitio() {  # el venv de audit.mk es el defecto del instalador, y audit.mk ya no llama a un semgrep del PATH
  local m; m=$(sed -n 's/^SEMGREP_VENV[[:space:]]*:=[[:space:]]*//p' "$amk")
  [ -n "$m" ] && [ "$m" = "$(SG_VENV= ; unset SG_VENV; . "$aqui/semgrep_instalar.sh"; printf '%s' "$SG_VENV")" ] &&
    ! grep -v '^[[:space:]]*#' "$amk" | grep -q -E '(command -v semgrep|&& semgrep )'
}
audit_usa_venv() { grep -q -F '$(SEMGREP_VENV)/bin/semgrep scan' "$amk"; }

los_casos() {
  acepta "lock bueno (con comentarios y líneas vacías)" sg_lock_valido "$tmp/l_bien"
  acepta "el lock del repo" sg_lock_valido "$lock"
  rechaza "sin hash" sg_lock_valido "$tmp/l_sin_hash"
  rechaza "versión con >= en vez de ==" sg_lock_valido "$tmp/l_sin_igual"
  rechaza "sin versión" sg_lock_valido "$tmp/l_sin_version"
  rechaza "hash de 63 hex" sg_lock_valido "$tmp/l_hash_corto"
  rechaza "hash de 65 hex" sg_lock_valido "$tmp/l_hash_largo"
  rechaza "hash en mayúsculas" sg_lock_valido "$tmp/l_hash_mayus"
  rechaza "hash md5" sg_lock_valido "$tmp/l_md5"
  rechaza "dos hashes en una línea" sg_lock_valido "$tmp/l_dos_hashes"
  rechaza "una opción de pip (--index-url)" sg_lock_valido "$tmp/l_index"
  rechaza "paquete repetido (mayúsculas)" sg_lock_valido "$tmp/l_repetido"
  rechaza "paquete repetido (. y _)" sg_lock_valido "$tmp/l_repetido_punto"
  rechaza "lock sin paquetes" sg_lock_valido "$tmp/l_vacio"
  rechaza "lock que no existe" sg_lock_valido "$tmp/no_existe"
  acepta "la versión de semgrep del lock de juguete" test "$(sg_version_lock "$tmp/l_bien")" = 1.187.0
  acepta "la versión de semgrep del lock del repo es 1.187.0 (medida DAY340)" test "$(sg_version_lock "$lock")" = 1.187.0
  acepta "lock sin semgrep: versión vacía" test -z "$(sg_version_lock "$tmp/l_sin_semgrep")"
  acepta "freeze igual al lock" sg_freeze_igual "$tmp/l_bien" "$tmp/f_igual"
  acepta "freeze igual salvo mayúsculas" sg_freeze_igual "$tmp/l_bien" "$tmp/f_mayus"
  rechaza "freeze con un paquete de más" sg_freeze_igual "$tmp/l_bien" "$tmp/f_sobra"
  rechaza "freeze con un paquete de menos" sg_freeze_igual "$tmp/l_bien" "$tmp/f_falta"
  rechaza "freeze con otra versión" sg_freeze_igual "$tmp/l_bien" "$tmp/f_version"
  rechaza "freeze con un paquete instalado desde fichero" sg_freeze_igual "$tmp/l_bien" "$tmp/f_file"
  rechaza "freeze vacío (venv nuevo)" sg_freeze_igual "$tmp/l_bien" "$tmp/f_vacio"
  rechaza "freeze que no existe" sg_freeze_igual "$tmp/l_bien" "$tmp/no_existe"
  acepta "semgrep --version igual" sg_version_igual "$tmp/v_bien" 1.187.0
  acepta "semgrep --version igual, con un aviso detrás" sg_version_igual "$tmp/v_aviso" 1.187.0
  rechaza "semgrep --version de otra versión" sg_version_igual "$tmp/v_otra" 1.187.0
  rechaza "semgrep --version 1.187.01 no es 1.187.0" sg_version_igual "$tmp/v_prefijo" 1.187.0
  rechaza "semgrep --version vacía" sg_version_igual "$tmp/v_vacia" 1.187.0
  rechaza "versión esperada vacía" sg_version_igual "$tmp/v_bien" ""
  rechaza "pip3 install semgrep (Vagrantfile DAY339)" sg_sin_pip "$tmp/vf_antes" "$lock"
  rechaza "pip install semgrep==1.187.0" sg_sin_pip "$tmp/vf_fijado" "$lock"
  rechaza "pip3 install urllib3 (del cierre)" sg_sin_pip "$tmp/vf_urllib3" "$lock"
  rechaza "Vagrantfile que no existe" sg_sin_pip "$tmp/no_existe" "$lock"
  acepta "comentarios y apt-get no cuentan" sg_sin_pip "$tmp/vf_limpio" "$lock"
  acepta "semgrep-rules-manager no es semgrep" sg_sin_pip "$tmp/vf_otro" "$lock"
  acepta "el Vagrantfile no instala semgrep ni nada de su cierre con pip" sg_sin_pip "$vf" "$lock"
  acepta "el lock tiene 67 paquetes (medido DAY340)" lock_paquetes 67
  acepta "el lock tiene cryptography (mcp pide pyjwt[crypto])" lock_tiene 'cryptography==.+'
  acepta "el lock tiene requests (en el venv no llega de apt)" lock_tiene 'requests==.+'
  acepta "make audit-semgrep llama a semgrep_instalar.sh como root en el defender" audit_semgrep_llama
  acepta "test-semgrep-instalar está en el EMECAS" grep -q -E '^[[:space:]]+@\$\(EMECAS_PASO\) test-semgrep-instalar -- \$\(MAKE\) test-semgrep-instalar$' "$raiz/Makefile"
  acepta "audit.mk y el instalador dicen el mismo venv; audit.mk no busca semgrep en el PATH" venv_un_sitio
  acepta "audit-taint corre el semgrep del venv" audit_usa_venv
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
sg_lock_valido() { return 0; }
sg_freeze_igual() { return 0; }
sg_sin_pip() { return 0; }
sg_version_igual() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-semgrep-instalar" || { echo "❌ test-semgrep-instalar: $total fallos"; exit 1; }
