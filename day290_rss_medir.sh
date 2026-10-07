#!/usr/bin/env bash
# DAY290 — muestreo de memoria (VmRSS/VmHWM) del sniffer durante y después de una corrida. SOLO LECTURA.
# Uso: bash day290_rss_medir.sh TAG [DURACION_S] [INTERVALO_S]
#   TAG          obligatorio: letras, números, _ . -
#   DURACION_S   segundos totales de muestreo (defecto 300 = ~90 s de corrida + 180 s de espera + margen)
#   INTERVALO_S  segundos entre muestras (defecto 5)
set -eu
TAG="${1:-}"
DURACION_S="${2:-300}"
INTERVALO_S="${3:-5}"

es_entero_pos() { [[ "$1" =~ ^[0-9]+$ ]] && [ "$1" -gt 0 ]; }

if [ -z "$TAG" ] || ! [[ "$TAG" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR: TAG obligatorio (letras, números, _ . -)" >&2; exit 2
fi
es_entero_pos "$DURACION_S"  || { echo "ERROR: DURACION_S debe ser entero > 0 (recibido: $DURACION_S)" >&2; exit 2; }
es_entero_pos "$INTERVALO_S" || { echo "ERROR: INTERVALO_S debe ser entero > 0 (recibido: $INTERVALO_S)" >&2; exit 2; }
[ "$INTERVALO_S" -le "$DURACION_S" ] || { echo "ERROR: INTERVALO_S ($INTERVALO_S) > DURACION_S ($DURACION_S)" >&2; exit 2; }

PID="$(pgrep -x sniffer | head -1 || true)"
[ -n "$PID" ] || { echo "ERROR: no hay proceso sniffer" >&2; exit 3; }

OUTDIR=/vagrant/logs/lab/day290/rss
mkdir -p "$OUTDIR"
OUT="$OUTDIR/rss_${TAG}.tsv"
[ ! -e "$OUT" ] || { echo "ERROR: $OUT ya existe; usa otro TAG" >&2; exit 2; }

printf "t_s\tvmrss_kb\tvmhwm_kb\n" > "$OUT"
T0=$(date +%s)
echo "sniffer PID=$PID tag=$TAG duracion=${DURACION_S}s intervalo=${INTERVALO_S}s -> $OUT"
while :; do
  T=$(( $(date +%s) - T0 ))
  [ "$T" -le "$DURACION_S" ] || break
  if [ ! -r "/proc/$PID/status" ]; then
    echo "AVISO: el sniffer (PID $PID) ha terminado en t=${T}s" >&2; break
  fi
  RSS=$(awk '/^VmRSS:/{print $2}' "/proc/$PID/status")
  HWM=$(awk '/^VmHWM:/{print $2}' "/proc/$PID/status")
  printf "%d\t%s\t%s\n" "$T" "$RSS" "$HWM" >> "$OUT"
  sleep "$INTERVALO_S"
done
echo "OK -> $OUT"
