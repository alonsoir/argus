#!/usr/bin/env bash
# scripts/terceros/test_python_apt.sh — [PYTHON-APT-D336] tests de las funciones pa_* de python_apt.sh y del
# Vagrantfile (Mac, sin VMs ni red). Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y
# tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
vf=${PYTHON_APT_VAGRANTFILE:-$aqui/../../Vagrantfile}
. "$aqui/python_apt.sh"

casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
# Las líneas de antes (Vagrantfile hasta DAY335) y variantes
printf '      apt-get install -y ansible\n        pip3 install jinja2 --break-system-packages --quiet\n' > "$tmp/jinja2"
printf '      python3 -c "import cryptography" 2>/dev/null || \\\n        pip3 install cryptography --break-system-packages --quiet\n' > "$tmp/cryptography"
printf '      pip install cryptography==41.0.0\n' > "$tmp/pip_versionado"
printf '      pip3 install -r req.txt jinja2\n' > "$tmp/al_final"
printf '      # antes: pip3 install jinja2 --break-system-packages\n      pip3 install semgrep\n      apt-get install -y python3-jinja2 python3-cryptography\n' > "$tmp/limpio"
printf '      pip3 install jinja2-time\n' > "$tmp/otro_paquete"

vagrantfile_apt() { grep -E '^[[:space:]]*apt-get install -y python3 ' "$vf" | grep -q -E '(^|[[:space:]])python3-jinja2([[:space:]]|$)' && grep -E '^[[:space:]]*apt-get install -y python3 ' "$vf" | grep -q -E '(^|[[:space:]])python3-cryptography([[:space:]]|$)'; }
vagrantfile_llama() { [ "$(grep -c -E '^[[:space:]]*bash /vagrant/scripts/terceros/python_apt\.sh ' "$vf")" = 2 ]; }

los_casos() {
  acepta "ruta de apt: cryptography (medido DAY336)" pa_origen_apt /usr/lib/python3/dist-packages/cryptography/__init__.py
  acepta "ruta de apt: jinja2 (medido DAY336)" pa_origen_apt /usr/lib/python3/dist-packages/jinja2/__init__.py
  rechaza "ruta de pip en /usr/local" pa_origen_apt /usr/local/lib/python3.11/dist-packages/jinja2/__init__.py
  rechaza "ruta de pip en el usuario" pa_origen_apt /home/vagrant/.local/lib/python3.11/site-packages/jinja2/__init__.py
  rechaza "ruta que sale del directorio con .." pa_origen_apt /usr/lib/python3/dist-packages/../../local/x.py
  rechaza "el directorio solo, sin fichero" pa_origen_apt /usr/lib/python3/dist-packages/
  rechaza "ruta vacía" pa_origen_apt ""
  rechaza "pip3 install jinja2 (Vagrantfile DAY335)" pa_sin_pip "$tmp/jinja2"
  rechaza "pip3 install cryptography (Vagrantfile DAY335)" pa_sin_pip "$tmp/cryptography"
  rechaza "pip install cryptography==41.0.0" pa_sin_pip "$tmp/pip_versionado"
  rechaza "jinja2 al final de un pip3 install -r" pa_sin_pip "$tmp/al_final"
  rechaza "fichero que no existe" pa_sin_pip "$tmp/no_existe"
  acepta "comentario, semgrep y apt-get no cuentan" pa_sin_pip "$tmp/limpio"
  acepta "jinja2-time no es jinja2" pa_sin_pip "$tmp/otro_paquete"
  acepta "el Vagrantfile no instala con pip ningún módulo de PA_MODULOS" pa_sin_pip "$vf"
  acepta "el Vagrantfile pide python3-jinja2 y python3-cryptography en el apt-get de Python" vagrantfile_apt
  acepta "el Vagrantfile llama a python_apt.sh dos veces (provisión y vault-enterprise-bootstrap)" vagrantfile_llama
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
pa_origen_apt() { return 0; }
pa_sin_pip() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-python-apt" || { echo "❌ test-python-apt: $total fallos"; exit 1; }
