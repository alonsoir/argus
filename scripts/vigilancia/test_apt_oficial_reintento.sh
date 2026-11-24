#!/usr/bin/env bash
# scripts/vigilancia/test_apt_oficial_reintento.sh — [APT-REINTENTO-D336] tests de actualizar_indices, ao_esperas y
# ao_version_visible (lib_apt_oficial.sh) y de quién los llama (Mac, sin VMs ni red). apt-get y apt-cache son de
# juguete, en un PATH propio: con --error-on=any un repositorio caído sale con 100 y sin él con 0, como se midió en
# DAY336 con apt 2.6.2. Cada caso de rechazo se vuelve a correr contra las funciones de antes (apt-get update -qq a
# secas) y contra funciones que lo aceptan todo, y tiene que fallar ahí.
set -u
LC_ALL=C; export LC_ALL
aqui=$(cd "$(dirname "$0")" && pwd)
raiz=$aqui/../..
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
cat > "$tmp/bin/apt-get" <<'APTGET'
#!/usr/bin/env bash
d=$AO_TEST_DIR
n=$(cat "$d/n" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$d/n"
echo "$*" >> "$d/args"
case " $* " in *" update "*) ;; *) exit 0 ;; esac
if [ "$n" -le "${AO_TEST_FALLOS:-0}" ]; then
  case " $* " in
    *" --error-on=any "*) echo "E: Failed to fetch https://download.falco.org/packages/deb/dists/stable/InRelease  503  Service Temporarily Unavailable"; echo "E: Some index files failed to download."; exit 100 ;;
    *) echo "W: Failed to fetch https://download.falco.org/packages/deb/dists/stable/InRelease  503  Service Temporarily Unavailable"; exit 0 ;;
  esac
fi
exit 0
APTGET
cat > "$tmp/bin/apt-cache" <<'APTCACHE'
#!/usr/bin/env bash
[ "$1" = madison ] && [ "$2" = falco ] || exit 0
printf '     falco |     0.45.2 | https://download.falco.org/packages/deb stable/main amd64 Packages\n'
printf '     falco |     0.43.1 | https://download.falco.org/packages/deb stable/main amd64 Packages\n'
APTCACHE
chmod +x "$tmp/bin/apt-get" "$tmp/bin/apt-cache"
PATH="$tmp/bin:$PATH"; export PATH
. "$aqui/lib_apt_oficial.sh"
export AO_TEST_DIR="$tmp/estado"; mkdir -p "$AO_TEST_DIR"
printf '0 0\n' > "$tmp/esperas_0"; export APT_OFICIAL_ESPERAS="$tmp/esperas_0"

casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# esperas: ESPERADO CONTENIDO_DEL_FICHERO (o -ausente-)
esperas_dan() { local f="$tmp/esp"; rm -f "$f"; [ "$2" = -ausente- ] || printf '%b' "$2" > "$f"; [ "$(ao_esperas "$f" 2>/dev/null)" = "$1" ]; }
# esperas que se rechazan: caen al defecto 30 60 (y el fichero no decía 30 60)
esperas_rechazadas() { local f="$tmp/esp"; rm -f "$f"; [ "$1" = -ausente- ] || printf '%b' "$1" > "$f"; [ "$(ao_esperas "$f" 2>/dev/null)" != "30 60" ]; }
# corrida FALLOS -> rc de actualizar_indices; deja llamadas y argumentos en el estado
corrida() { rm -f "$AO_TEST_DIR/n" "$AO_TEST_DIR/args"; AO_TEST_FALLOS=$1 actualizar_indices > "$tmp/salida" 2>&1; }
llamadas() { [ "$(cat "$AO_TEST_DIR/n" 2>/dev/null || echo 0)" = "$1" ]; }
todas_con_error_on() { [ "$(grep -c -- '--error-on=any' "$AO_TEST_DIR/args")" = "$(grep -c . "$AO_TEST_DIR/args")" ]; }
bien_con() { corrida "$1" && llamadas "$2" && todas_con_error_on; }
# rechazo: con FALLOS caídas seguidas, actualizar_indices debe salir con 1 y decir FALLA
sale_bien_con() { corrida "$1"; }
falla_dice_falla() { ! corrida 3 && grep -q 'FALLA: apt-get update sin éxito en 3 intentos' "$tmp/salida" && grep -q '503' "$tmp/salida"; }

los_casos() {
  acepta "ESPERAS_S del repo: 30 60" esperas_dan "30 60" "$(cat "$raiz/provisioning/apt-oficial/ESPERAS_S")"
  acepta "comentarios y una espera por línea" esperas_dan "5 10" "# x\n5\n10\n"
  acepta "una espera de 0 s (2 intentos)" esperas_dan "0" "0\n"
  rechaza "fichero ausente: defecto" esperas_rechazadas -ausente-
  rechaza "no entero: defecto" esperas_rechazadas "30 abc\n"
  rechaza "negativo: defecto" esperas_rechazadas "-5\n"
  rechaza "más de 600 s: defecto" esperas_rechazadas "601\n"
  rechaza "seis esperas: defecto" esperas_rechazadas "1 2 3 4 5 6\n"
  rechaza "fichero sin esperas: defecto" esperas_rechazadas "# nada\n"
  acepta "repositorio sano: 1 llamada, con --error-on=any" bien_con 0 1
  acepta "un 503: bien al segundo intento" bien_con 1 2
  acepta "dos 503: bien al tercer intento" bien_con 2 3
  rechaza "tres 503: sale con 1" sale_bien_con 3
  acepta "tres 503: dice FALLA y el 503 de apt" falla_dice_falla
  acepta "falco 0.43.1 visible" ao_version_visible falco 0.43.1
  rechaza "falco 0.43 no es 0.43.1" ao_version_visible falco 0.43
  rechaza "falco 0.43.10 no es 0.43.1" ao_version_visible falco 0.43.10
  rechaza "paquete sin versiones" ao_version_visible vault 2.2.1-1
}

# Quién los llama: nadie hace ya apt-get update -qq tras añadir un repositorio oficial.
estaticos() {
  local f c
  for f in scripts/vigilancia/falco_instalar.sh scripts/vigilancia/zeek_instalar.sh scripts/vigilancia/wazuh_agente_instalar.sh \
           scripts/terceros/vault_instalar.sh scripts/terceros/arrow_instalar.sh scripts/terceros/temurin_instalar.sh \
           scripts/jenkins/jenkins_instalar.sh; do
    c=$(grep -c 'apt-get update -qq' "$raiz/$f")
    acepta "$f sin apt-get update -qq" test "$c" = 0
    c=$(grep -c '^[[:space:]]*actualizar_indices || ' "$raiz/$f")
    acepta "$f llama una vez a actualizar_indices" test "$c" = 1
  done
  c=$(grep -c '^[[:space:]]*actualizar_indices || ' "$raiz/Vagrantfile")
  acepta "el Vagrantfile llama dos veces a actualizar_indices (dist/vendor de Falco y wazuh-manager)" test "$c" = 2
  c=$(grep -c -A2 'ao_version_visible "\$paquete" "\$version"' "$raiz/scripts/vigilancia/lib_apt_oficial.sh")
  acepta "instalar_fijado comprueba la versión antes de instalar" test "$c" -ge 1
}

los_casos
estaticos
echo "$((casos - fallos))/$casos casos"
total=$fallos
esperados=$rechazos

# Contra las funciones de antes: apt-get update -qq a secas (el W: se cuela) y sin comprobar la versión.
actualizar_indices() { apt-get update -qq; }
ao_version_visible() { return 0; }
ao_esperas() { grep -v '^[[:space:]]*#' "$1" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//'; }
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra las funciones de antes y las que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra las funciones de antes fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-apt-oficial-reintento" || { echo "❌ test-apt-oficial-reintento: $total fallos"; exit 1; }
