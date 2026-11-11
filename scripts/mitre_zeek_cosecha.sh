#!/usr/bin/env bash
# mitre_zeek_cosecha.sh — DAY323 [MITRE-ZEEK-COSECHA-D323] (se ejecuta DENTRO de la VM zeek, con sudo): para Zeek y
# junta TODOS los conn.log de la ventana [T0, T1], también los que una rotación horaria ya archivó.
# Medido DAY323: (1) a las 10:00:00 zeekctl rotó el conn.log a mitad de la corrida y la cosecha antigua (copiar
# spool/zeek/conn.log) se quedó con 8 filas de etcd y NTP, sin el barrido (1072 líneas de .50 en el archivado);
# (2) `zeekctl stop` vuelve en el acto y el archivado sigue en segundo plano: post-terminate mueve el spool a
# spool/tmp/post-terminate-* y lanza un archive-log por fichero, uno tras otro (~55 s cada uno; 121 s para dos).
# Por eso: stop, esperar a que no quede ningún post-terminate/archive-log ni ningún conn* en spool/tmp (máximo
# ESPERA_MAX_S, si no FALLA), y concatenar los conn.*.log.gz de los días de T0 y T1 (el adapter acepta #fields
# repetidos; el filtro por la ventana se hace después, en el bronce, igual para los tres sensores).
# Uso: sudo bash /vagrant/scripts/mitre_zeek_cosecha.sh T0 T1 SALIDA [ESPERA_MAX_S]
# rc: 0 bien; 1 el archivado no termina; 2 uso; 3 sin ficheros conn de esos días; 4 un .gz roto.
set -u -o pipefail
export LC_ALL=C
T0=${1:-}; T1=${2:-}; SALIDA=${3:-}; ESPERA_MAX_S=${4:-300}
ZEEK=${ZEEK_DIR:-/opt/zeek}
TAG="[MITRE-ZEEK-COSECHA]"
echo "$T0" | grep -Eq '^[0-9]+(\.[0-9]+)?$' && echo "$T1" | grep -Eq '^[0-9]+(\.[0-9]+)?$' && [ -n "$SALIDA" ] \
  && echo "$ESPERA_MAX_S" | grep -Eq '^[0-9]+$' || { echo "$TAG uso: $0 T0 T1 SALIDA [ESPERA_MAX_S]"; exit 2; }

"$ZEEK/bin/zeekctl" stop
archivando() {
  pgrep -f 'zeekctl/scripts/(post-terminate|archive-log)' > /dev/null && return 0
  find "$ZEEK/spool/tmp" -name 'conn*' 2>/dev/null | grep -q . && return 0
  return 1
}
i=0
while archivando; do
  i=$((i + 1))
  if [ "$i" -gt "$ESPERA_MAX_S" ]; then
    echo "$TAG FALLA: el archivado de zeekctl stop sigue tras $ESPERA_MAX_S s"
    pgrep -af 'zeekctl/scripts/(post-terminate|archive-log)'; find "$ZEEK/spool/tmp" -name 'conn*'
    exit 1
  fi
  sleep 1
done
echo "$TAG archivado terminado en $i s"

D0=$(date -u -d "@${T0%.*}" +%F); D1=$(date -u -d "@${T1%.*}" +%F)
FICHEROS=$(ls "$ZEEK/logs/$D0"/conn.*.log.gz "$ZEEK/logs/$D1"/conn.*.log.gz 2>/dev/null | sort -u)
[ -n "$FICHEROS" ] || { echo "$TAG FALLA: ningún conn.*.log.gz en logs/$D0 ni logs/$D1"; exit 3; }
: > "$SALIDA" || exit 4
for f in $FICHEROS; do
  zcat "$f" >> "$SALIDA" || { echo "$TAG FALLA: $f no se puede descomprimir entero"; exit 4; }
done
chmod 644 "$SALIDA"
echo "$TAG $(echo "$FICHEROS" | wc -l | tr -d ' ') ficheros de $D0..$D1, $(grep -vc '^#' "$SALIDA") filas -> $SALIDA"
