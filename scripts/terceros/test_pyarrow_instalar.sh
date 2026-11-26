#!/usr/bin/env bash
# scripts/terceros/test_pyarrow_instalar.sh — [PYARROW-D338] tests de pyarrow_instalar.sh, del lock
# provisioning/pyarrow/requirements.txt, del Vagrantfile y del Makefile (Mac, sin VMs ni red: python3, pip3 e id son de
# juguete). Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí.
set -u
LC_ALL=C; export LC_ALL
aqui=$(cd "$(dirname "$0")" && pwd)
raiz=$aqui/../..
vf=${PYARROW_VAGRANTFILE:-$raiz/Vagrantfile}
mf=${PYARROW_MAKEFILE:-$raiz/Makefile}
lock=$raiz/provisioning/pyarrow/requirements.txt
. "$aqui/pyarrow_instalar.sh"

casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
h=39cb0f2418282c24bea6ceda77b03e5a8f0a5766b63a8bf194d4e2a2c423548c
L=/usr/local/lib/python3.11/dist-packages/pyarrow/__init__.py
# Locks de juguete
printf '# comentario\n\npyarrow==26.0.1 --hash=sha256:%s\n' "$h" > "$tmp/l_bien"
printf 'pyarrow==26.0.1\n' > "$tmp/l_sin_hash"
printf 'pyarrow>=26 --hash=sha256:%s\n' "$h" > "$tmp/l_sin_igual"
printf 'pyarrow --hash=sha256:%s\n' "$h" > "$tmp/l_sin_version"
printf 'pyarrow==26.0.1 --hash=sha256:%s\n' "${h%?}" > "$tmp/l_hash_corto"
printf 'pyarrow==26.0.1 --hash=sha256:%s\n' "$(printf '%s' "$h" | tr a-f A-F)" > "$tmp/l_hash_mayus"
printf 'pyarrow==26.0.1 --hash=md5:%s\n' "$h" > "$tmp/l_md5"
printf 'pyarrow==26.0.1 --hash=sha256:%s\nnumpy==2.4.6 --hash=sha256:%s\n' "$h" "$h" > "$tmp/l_dos"
printf 'numpy==2.4.6 --hash=sha256:%s\n' "$h" > "$tmp/l_otro"
printf -- '--index-url https://otro.example/simple\npyarrow==26.0.1 --hash=sha256:%s\n' "$h" > "$tmp/l_index"
printf '# solo comentarios\n' > "$tmp/l_vacio"
# Ficheros de juguete (la línea de parquet-convert de antes de DAY338 y variantes)
printf '\t@vagrant ssh -c "pip3 install --upgrade pyarrow --break-system-packages --quiet 2>&1 | tail -1"\n' > "$tmp/m_antes"
printf '      pip install pyarrow==26.0.1\n' > "$tmp/m_pip"
printf '      pip3 install "pyarrow"\n' > "$tmp/m_comillas"
printf '\t# antes: pip3 install --upgrade pyarrow\n\t@vagrant ssh -c "bash pyarrow_instalar.sh --comprobar"\n      pip3 install semgrep\n      pip3 install pyarrow-stubs\n' > "$tmp/m_limpio"

# python3, pip3 e id de juguete: el import da lo que haya en $tmp/import (vacío = no importa); pip3 apunta sus
# argumentos en $tmp/pip3.args y deja instalada la versión de $tmp/tras_pip
mkdir -p "$tmp/bin"
cat > "$tmp/bin/python3" <<'P'
#!/bin/sh
[ -s "$JUGUETE/import" ] || exit 1
cat "$JUGUETE/import"
P
cat > "$tmp/bin/pip3" <<'P'
#!/bin/sh
echo "$*" >> "$JUGUETE/pip3.args"
cp "$JUGUETE/tras_pip" "$JUGUETE/import"
P
chmod +x "$tmp/bin/python3" "$tmp/bin/pip3"
# corre main en un subshell con los de juguete; $1 = uid, $2 = lo que da el import, $3 = lo que deja pip3, resto = args
con_juguete() {
  local uid=$1 imp=$2 tras=$3; shift 3
  ( export JUGUETE=$tmp PATH="$tmp/bin:$PATH" PYA_LOCK=$tmp/l_bien
    printf '%s' "$imp" > "$tmp/import"; printf '%s' "$tras" > "$tmp/tras_pip"; rm -f "$tmp/pip3.args"
    id() { [ "${1:-}" = -u ] && echo "$uid" || echo vagrant; }
    main "$@" )
}
comprobar_bien() { con_juguete 1000 "26.0.1 $L" "" --comprobar; }
comprobar_local() { con_juguete 1000 "26.0.1 /home/vagrant/.local/lib/python3.11/site-packages/pyarrow/__init__.py" "" --comprobar; }
comprobar_version() { con_juguete 1000 "27.0.0 $L" "" --comprobar; }
comprobar_no_importa() { con_juguete 1000 "" "" --comprobar; }
comprobar_instala() { local rc; con_juguete 1000 "" "26.0.1 $L" --comprobar; rc=$?; [ "$rc" = 0 ] || [ -e "$tmp/pip3.args" ]; }
instala_ya_esta() { con_juguete 0 "26.0.1 $L" "" && [ ! -e "$tmp/pip3.args" ]; }
instala_con_hashes() {
  con_juguete 0 "" "26.0.1 $L" || return 1
  grep -q -- '--require-hashes' "$tmp/pip3.args" && grep -q -- '--no-deps' "$tmp/pip3.args" &&
    grep -q -- '--only-binary=:all:' "$tmp/pip3.args" && grep -q -- "-r $tmp/l_bien" "$tmp/pip3.args" &&
    ! grep -q -- '--upgrade' "$tmp/pip3.args"
}
instala_vieja() { con_juguete 0 "25.0.0 $L" "26.0.1 $L" && [ -e "$tmp/pip3.args" ]; }
instala_pero_queda_mal() { con_juguete 0 "" "27.0.0 $L"; }
sin_root_falla() { ! con_juguete 1000 "" "26.0.1 $L" && [ ! -e "$tmp/pip3.args" ]; }

lock_es_26() { [ "$(pya_version_lock "$lock")" = 26.0.1 ] && grep -q -- "--hash=sha256:$h\$" "$lock"; }
vagrant_llama() {
  grep -v '^[[:space:]]*#' "$vf" | grep -c -x -E '[[:space:]]+bash /vagrant/scripts/terceros/pyarrow_instalar\.sh \|\| \{ echo "❌ pyarrow"; exit 1; \}' | grep -q -x 1
}
makefile_comprueba() {
  awk '/^parquet-convert:/ { d = 1; next } d && /^[^\t]/ { d = 0 } d' "$mf" |
    grep -q -x -E '[[:space:]]+@vagrant ssh defender -c "bash /vagrant/scripts/terceros/pyarrow_instalar\.sh --comprobar"'
}

los_casos() {
  acepta "lock bueno (con comentarios y líneas vacías)" pya_lock_valido "$tmp/l_bien"
  acepta "el lock del repo" pya_lock_valido "$lock"
  rechaza "sin hash" pya_lock_valido "$tmp/l_sin_hash"
  rechaza "versión con >= en vez de ==" pya_lock_valido "$tmp/l_sin_igual"
  rechaza "sin versión" pya_lock_valido "$tmp/l_sin_version"
  rechaza "hash de 63 hex" pya_lock_valido "$tmp/l_hash_corto"
  rechaza "hash en mayúsculas" pya_lock_valido "$tmp/l_hash_mayus"
  rechaza "hash md5" pya_lock_valido "$tmp/l_md5"
  rechaza "dos paquetes (el cierre medido es solo pyarrow)" pya_lock_valido "$tmp/l_dos"
  rechaza "otro paquete" pya_lock_valido "$tmp/l_otro"
  rechaza "una opción de pip (--index-url)" pya_lock_valido "$tmp/l_index"
  rechaza "lock sin paquetes" pya_lock_valido "$tmp/l_vacio"
  rechaza "lock que no existe" pya_lock_valido "$tmp/no_existe"
  acepta "origen /usr/local (pip como root en Debian)" pya_origen_local "$L"
  rechaza "origen ~/.local (el de antes)" pya_origen_local "/home/vagrant/.local/lib/python3.11/site-packages/pyarrow/__init__.py"
  rechaza "origen dist-packages de apt" pya_origen_local "/usr/lib/python3/dist-packages/pyarrow/__init__.py"
  rechaza "origen con .." pya_origen_local "/usr/local/lib/python3.11/dist-packages/../../x/pyarrow/__init__.py"
  rechaza "origen de un venv" pya_origen_local "/opt/argus/ml-entreno/lib/python3.11/site-packages/pyarrow/__init__.py"
  acepta "instalado: versión y origen buenos" pya_instalado_ok 26.0.1 "26.0.1 $L"
  rechaza "instalado: otra versión" pya_instalado_ok 26.0.1 "26.0.10 $L"
  rechaza "instalado: no importa" pya_instalado_ok 26.0.1 ""
  rechaza "instalado: sin ruta" pya_instalado_ok 26.0.1 "26.0.1"
  rechaza "pip3 install --upgrade pyarrow (parquet-convert hasta DAY337)" pya_sin_pip "$tmp/m_antes"
  rechaza "pip install pyarrow==26.0.1" pya_sin_pip "$tmp/m_pip"
  rechaza "pip3 install \"pyarrow\"" pya_sin_pip "$tmp/m_comillas"
  rechaza "fichero que no existe" pya_sin_pip "$tmp/no_existe"
  acepta "comentarios, semgrep y pyarrow-stubs no cuentan" pya_sin_pip "$tmp/m_limpio"
  acepta "el Makefile no instala pyarrow con pip" pya_sin_pip "$mf"
  acepta "el Vagrantfile no instala pyarrow con pip" pya_sin_pip "$vf"
  acepta "--comprobar: 26.0.1 de /usr/local" comprobar_bien
  rechaza "--comprobar: una copia en ~/.local la tapa" comprobar_local
  rechaza "--comprobar: otra versión" comprobar_version
  rechaza "--comprobar: no importa" comprobar_no_importa
  rechaza "--comprobar sin pyarrow: falla y no instala nada" comprobar_instala
  acepta "root, ya instalada: no llama a pip3" instala_ya_esta
  acepta "root, sin pyarrow: pip3 con --require-hashes --no-deps --only-binary y el lock, sin --upgrade" instala_con_hashes
  acepta "root, otra versión instalada: llama a pip3" instala_vieja
  rechaza "root: tras pip3 queda otra versión" instala_pero_queda_mal
  acepta "sin root ni --comprobar: sale con error y no llama a pip3" sin_root_falla
  acepta "el lock del repo: pyarrow 26.0.1 con el sha256 medido DAY336 y DAY338" lock_es_26
  acepta "el Vagrantfile llama una vez a pyarrow_instalar.sh y para si falla" vagrant_llama
  acepta "make parquet-convert solo comprueba (--comprobar en el defender)" makefile_comprueba
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
pya_lock_valido() { return 0; }
pya_origen_local() { return 0; }
pya_instalado_ok() { return 0; }
pya_sin_pip() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-pyarrow-instalar" || { echo "❌ test-pyarrow-instalar: $total fallos"; exit 1; }
