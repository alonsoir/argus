#!/usr/bin/env bash
# d323_zeek_archivo.sh — DAY323, medida (se ejecuta DENTRO de la VM zeek): qué hace `zeekctl stop` con los logs.
# Dónde quedan los conn.* tras el stop, cuánto tarda el archivado y qué procesos lo hacen. Hace deploy, espera 20 s,
# stop, y durante 120 s imprime el estado SOLO cuando cambia (ficheros conn* en spool y en logs/<hoy>, y procesos
# de archivado). Deja Zeek parado, como mitre_start.sh. No toca nada más.
# Uso (VM zeek): sudo bash /vagrant/scripts/etcd_ha/d323_zeek_archivo.sh
set -u
export LC_ALL=C
Z=/opt/zeek; ZC=$Z/bin/zeekctl; HOY=$(date -u +%F)
foto() {
  find "$Z/spool" -name 'conn*' -printf 'spool %p %s\n' 2>/dev/null | sort
  find "$Z/logs/$HOY" -name 'conn*' -mmin -5 -printf 'logs  %p %s\n' 2>/dev/null | sort
  ps -eo pid,etimes,args | grep -E 'archive-log|post-terminate|gzip|zeek-archiver' | grep -v grep | sed 's/^/proc  /'
}
"$ZC" deploy > /dev/null 2>&1 || { echo "[ZEEK-ARCHIVO] FALLA: zeekctl deploy"; exit 1; }
sleep 20
echo "== $(date -u +%T) antes del stop"; foto
"$ZC" stop
echo "== $(date -u +%T) zeekctl stop devuelve rc=$?"
ANT=""
for i in $(seq 1 120); do
  F=$(foto)
  if [ "$F" != "$ANT" ]; then echo "-- t+${i}s $(date -u +%T)"; echo "$F"; ANT=$F; fi
  sleep 1
done
echo "== $(date -u +%T) fin (120 s)"
