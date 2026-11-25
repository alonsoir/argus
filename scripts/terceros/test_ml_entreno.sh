#!/usr/bin/env bash
# scripts/terceros/test_ml_entreno.sh — [ML-ENTRENO-D337] tests de las funciones me_* de ml_entreno_instalar.sh, del lock
# provisioning/ml-entreno/requirements.txt, del Vagrantfile y del Makefile (Mac, sin VMs ni red). Cada caso de rechazo
# se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
raiz=$aqui/../..
vf=${ML_ENTRENO_VAGRANTFILE:-$raiz/Vagrantfile}
lock=$raiz/provisioning/ml-entreno/requirements.txt
. "$aqui/ml_entreno_instalar.sh"

casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
h=89cd468399cfd2504718f0ba50e410dca55a170b61a02ad92bb18c8a65186e93
g=5fc3c5039fc5ca8c0276333a188bbd59d6b7ab37fe6632daa76bc7f9ec18e713
# Locks de juguete
printf '# comentario\n\nnumpy==2.4.6 --hash=sha256:%s\njoblib==1.5.3 --hash=sha256:%s\n' "$h" "$g" > "$tmp/l_bien"
printf 'numpy==2.4.6\n' > "$tmp/l_sin_hash"
printf 'numpy>=2.4 --hash=sha256:%s\n' "$h" > "$tmp/l_sin_igual"
printf 'numpy --hash=sha256:%s\n' "$h" > "$tmp/l_sin_version"
printf 'numpy==2.4.6 --hash=sha256:%s\n' "${h%?}" > "$tmp/l_hash_corto"
printf 'numpy==2.4.6 --hash=sha256:%s0\n' "$h" > "$tmp/l_hash_largo"
printf 'numpy==2.4.6 --hash=sha256:%s\n' "$(printf '%s' "$h" | tr a-f A-F)" > "$tmp/l_hash_mayus"
printf 'numpy==2.4.6 --hash=md5:%s\n' "$h" > "$tmp/l_md5"
printf 'numpy==2.4.6 --hash=sha256:%s --hash=sha256:%s\n' "$h" "$g" > "$tmp/l_dos_hashes"
printf -- '--index-url https://otro.example/simple\nnumpy==2.4.6 --hash=sha256:%s\n' "$h" > "$tmp/l_index"
printf 'numpy==2.4.6 --hash=sha256:%s\nNumPy==2.4.6 --hash=sha256:%s\n' "$h" "$h" > "$tmp/l_repetido"
printf 'scikit_learn==1.9.0 --hash=sha256:%s\nscikit-learn==1.9.0 --hash=sha256:%s\n' "$h" "$h" > "$tmp/l_repetido_guion"
printf '# solo comentarios\n\n' > "$tmp/l_vacio"
# Salidas de pip freeze de juguete, contra l_bien
printf 'joblib==1.5.3\nnumpy==2.4.6\n' > "$tmp/f_igual"
printf 'NumPy==2.4.6\nJoblib==1.5.3\n' > "$tmp/f_mayus"
printf 'joblib==1.5.3\nnumpy==2.4.6\ntzdata==2025.2\n' > "$tmp/f_sobra"
printf 'numpy==2.4.6\n' > "$tmp/f_falta"
printf 'joblib==1.5.3\nnumpy==2.4.5\n' > "$tmp/f_version"
printf 'joblib @ file:///tmp/joblib-1.5.3-py3-none-any.whl\nnumpy==2.4.6\n' > "$tmp/f_file"
: > "$tmp/f_vacio"
# Vagrantfiles de juguete (la línea de antes de DAY337 y variantes)
printf '      pip3 install -r /vagrant/ml-training/requirements-ddos-pinned.txt \\\n      --break-system-packages --timeout=300\n' > "$tmp/v_antes"
printf '      pip3 install pandas==3.0.5 --break-system-packages\n' > "$tmp/v_pandas"
printf '      pip install scikit-learn\n' > "$tmp/v_sklearn"
printf '      # antes: pip3 install -r /vagrant/ml-training/requirements-ddos-pinned.txt\n      pip3 install semgrep --break-system-packages --quiet\n      apt-get install -y python3-six\n' > "$tmp/v_limpio"
printf '      pip3 install numpyro\n' > "$tmp/v_otro"

lock_tiene() { me_normaliza "$lock" | grep -q -x -E "$1==.+"; }
makefile_llama() { grep -q -E '^[[:space:]]+@vagrant ssh defender -c "sudo bash /vagrant/scripts/terceros/ml_entreno_instalar\.sh"$' "$raiz/Makefile"; }
viejo_borrado() { [ ! -e "$raiz/ml-training/requirements-ddos-pinned.txt" ]; }

los_casos() {
  acepta "lock bueno (con comentarios y líneas vacías)" me_lock_valido "$tmp/l_bien"
  acepta "el lock del repo" me_lock_valido "$lock"
  rechaza "sin hash" me_lock_valido "$tmp/l_sin_hash"
  rechaza "versión con >= en vez de ==" me_lock_valido "$tmp/l_sin_igual"
  rechaza "sin versión" me_lock_valido "$tmp/l_sin_version"
  rechaza "hash de 63 hex" me_lock_valido "$tmp/l_hash_corto"
  rechaza "hash de 65 hex" me_lock_valido "$tmp/l_hash_largo"
  rechaza "hash en mayúsculas" me_lock_valido "$tmp/l_hash_mayus"
  rechaza "hash md5" me_lock_valido "$tmp/l_md5"
  rechaza "dos hashes en una línea" me_lock_valido "$tmp/l_dos_hashes"
  rechaza "una opción de pip (--index-url)" me_lock_valido "$tmp/l_index"
  rechaza "paquete repetido (mayúsculas)" me_lock_valido "$tmp/l_repetido"
  rechaza "paquete repetido (_ y -)" me_lock_valido "$tmp/l_repetido_guion"
  rechaza "lock sin paquetes" me_lock_valido "$tmp/l_vacio"
  rechaza "lock que no existe" me_lock_valido "$tmp/no_existe"
  acepta "freeze igual al lock" me_freeze_igual "$tmp/l_bien" "$tmp/f_igual"
  acepta "freeze igual salvo mayúsculas" me_freeze_igual "$tmp/l_bien" "$tmp/f_mayus"
  rechaza "freeze con un paquete de más" me_freeze_igual "$tmp/l_bien" "$tmp/f_sobra"
  rechaza "freeze con un paquete de menos" me_freeze_igual "$tmp/l_bien" "$tmp/f_falta"
  rechaza "freeze con otra versión" me_freeze_igual "$tmp/l_bien" "$tmp/f_version"
  rechaza "freeze con un paquete instalado desde fichero" me_freeze_igual "$tmp/l_bien" "$tmp/f_file"
  rechaza "freeze vacío (venv nuevo)" me_freeze_igual "$tmp/l_bien" "$tmp/f_vacio"
  rechaza "freeze que no existe" me_freeze_igual "$tmp/l_bien" "$tmp/no_existe"
  rechaza "pip3 install -r requirements-ddos-pinned.txt (Vagrantfile DAY336)" me_sin_pip "$tmp/v_antes" "$lock"
  rechaza "pip3 install pandas==3.0.5" me_sin_pip "$tmp/v_pandas" "$lock"
  rechaza "pip install scikit-learn" me_sin_pip "$tmp/v_sklearn" "$lock"
  rechaza "Vagrantfile que no existe" me_sin_pip "$tmp/no_existe" "$lock"
  acepta "comentarios, semgrep y apt-get no cuentan" me_sin_pip "$tmp/v_limpio" "$lock"
  acepta "numpyro no es numpy" me_sin_pip "$tmp/v_otro" "$lock"
  acepta "el Vagrantfile no instala el entorno de entrenamiento" me_sin_pip "$vf" "$lock"
  acepta "el lock tiene el cierre medido DAY337: narwhals (de pandas)" lock_tiene narwhals
  acepta "el lock tiene el cierre medido DAY337: six (de python-dateutil)" lock_tiene six
  acepta "el lock tiene scikit-learn (export_ddos_v2_fact_rf.py)" lock_tiene scikit-learn
  acepta "make ml-entreno llama a ml_entreno_instalar.sh como root en el defender" makefile_llama
  acepta "ml-training/requirements-ddos-pinned.txt ya no existe" viejo_borrado
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
me_lock_valido() { return 0; }
me_freeze_igual() { return 0; }
me_sin_pip() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-ml-entreno" || { echo "❌ test-ml-entreno: $total fallos"; exit 1; }
