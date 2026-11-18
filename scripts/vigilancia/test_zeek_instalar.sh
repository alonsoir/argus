#!/usr/bin/env bash
# scripts/vigilancia/test_zeek_instalar.sh — [TERCEROS-ZEEK-D330] tests de las funciones zeek_* de zeek_instalar.sh
# (Mac, sin VMs: no tocan el sistema). Cada caso de rechazo se vuelve a correr contra un comprobador que lo acepta todo,
# y tiene que fallar ahí: así se ve que el test distingue (que no da verde en falso).
set -u
LC_ALL=C; export LC_ALL
. "$(dirname "$0")/zeek_instalar.sh"

BIEN=$'zeek-9.0=9.0.1-0\nzeek-9.0-core=9.0.1-0\nzeek-9.0-core-dev=9.0.1-0\nzeek-9.0-spicy-dev=9.0.1-0\nzeek-9.0-zkg=9.0.1-0\nzeek-9.0-client=9.0.1-0\nzeekctl-9.0=9.0.1-0'
BIN='/opt/zeek/bin/zeek version 9.0.1'
casos=0; fallos=0; rechazos=0; rechazos_vistos=0

# acepta NOMBRE ORDEN...  /  rechaza NOMBRE ORDEN...
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }
fuera_vacio() { [ -z "$(printf '%s\n' "$2" | zeek_fuera_de_serie "$1")" ]; }
fuera_es() { [ "$(printf '%s\n' "$2" | zeek_fuera_de_serie "$1")" = "$3" ]; }
comprueba() { printf '%s\n' "$4" | zeek_comprobar "$1" "$2" "$3"; }

los_casos() {
  acepta "serie 9.0 válida" zeek_serie_valida 9.0
  acepta "serie 10.12 válida" zeek_serie_valida 10.12
  rechaza "serie 9 (sin menor)" zeek_serie_valida 9
  rechaza "serie 9.0.1 (versión exacta, no serie)" zeek_serie_valida 9.0.1
  rechaza "serie vacía" zeek_serie_valida ""
  rechaza "serie 9.x" zeek_serie_valida 9.x
  rechaza "serie lts (por nombre)" zeek_serie_valida lts
  acepta "todo de la serie 9.0: nada fuera" fuera_vacio 9.0 $'zeek-9.0\nzeek-9.0-core\nzeekctl-9.0'
  acepta "lista vacía: nada fuera" fuera_vacio 9.0 ""
  rechaza "zeek y zeek-core (sin serie) están fuera" fuera_vacio 9.0 $'zeek\nzeek-core\nzeek-9.0'
  acepta "fuera: exactamente los sin serie" fuera_es 9.0 $'zeek\nzeek-9.0\nzeek-core' $'zeek\nzeek-core'
  rechaza "zeek-9.01-core no es de la serie 9.0" fuera_vacio 9.0 "zeek-9.01-core"
  rechaza "zeek-90-core no es de la serie 9.0 (el punto es literal)" fuera_vacio 9.0 "zeek-90-core"
  rechaza "zeek-8.0 no es de la serie 9.0" fuera_vacio 9.0 "zeek-8.0"
  acepta "lo instalado medido DAY330 en la serie 9.0" comprueba 9.0 9.0.1-0 "$BIN" "$BIEN"
  rechaza "un paquete en otra versión" comprueba 9.0 9.0.1-0 "$BIN" "${BIEN/zeek-9.0-zkg=9.0.1-0/zeek-9.0-zkg=9.0.0-0}"
  rechaza "versión del paquete de serie fuera de la serie" comprueba 9.0 9.1.0-0 '/opt/zeek/bin/zeek version 9.1.0' "${BIEN//9.0.1-0/9.1.0-0}"
  rechaza "el binario dice otra versión" comprueba 9.0 9.0.1-0 '/opt/zeek/bin/zeek version 8.0.4' "$BIEN"
  rechaza "el binario no responde" comprueba 9.0 9.0.1-0 '' "$BIEN"
  rechaza "falta zeek-9.0-core" comprueba 9.0 9.0.1-0 "$BIN" "${BIEN/zeek-9.0-core=9.0.1-0/}"
  rechaza "falta el metapaquete zeek-9.0" comprueba 9.0 9.0.1-0 "$BIN" "${BIEN/zeek-9.0=9.0.1-0/}"
  rechaza "un paquete sin serie entre lo instalado" comprueba 9.0 9.0.1-0 "$BIN" "$BIEN"$'\nzeek-core=9.0.1-0'
  rechaza "nada instalado" comprueba 9.0 9.0.1-0 "$BIN" ""
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra un comprobador que lo acepta todo, cada rechazo tiene que dar ❌.
zeek_serie_valida() { return 0; }
zeek_en_serie() { return 0; }
zeek_comprobar() { cat >/dev/null; return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra un comprobador que lo acepta todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra un comprobador que lo acepta todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ]
