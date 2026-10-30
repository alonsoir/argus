#!/bin/bash
# d312_etcd_medir.sh — DAY312, medidas del paso 3 (etcd de 1 nodo en la VM etcd). Instrumento: se commitea.
# Se ejecuta EN la VM etcd con sudo:  sudo bash /vagrant/scripts/etcd_ha/d312_etcd_medir.sh [CERT_OTRO KEY_OTRO]
# CERT_OTRO/KEY_OTRO: otra identidad de la CA (p. ej. sniffer) para comprobar que el RBAC la rechaza.
# Escribe UNA vez /argus/d312/prueba (si ya existe, la relee: así se mide la persistencia tras un reinicio).
set -u
EP=https://127.0.0.1:2381; CA=/etc/etcd/tls/ca.crt
ES="etcdctl --endpoints=$EP --cacert=$CA --cert=/etc/argus-pki/etcd-server.crt --key=/etc/argus-pki/etcd-server.key"
R=0; ok() { echo "[ETCD-MEDIR] PASA $*"; }; ko() { echo "[ETCD-MEDIR] FALLA $*"; R=1; }
echo "[ETCD-MEDIR] host=$(hostname) $(date -u +%FT%TZ)"

V=$($ES endpoint status -w json 2>/dev/null | python3 -c 'import sys,json; s=json.load(sys.stdin)[0]["Status"]; print(s["version"], "si" if s["leader"]==s["header"]["member_id"] else "no")' 2>/dev/null)
[ "$V" = "3.6.16 si" ] && ok "M1 etcd 3.6.16 sano y líder único" || ko "M1 estado: '$V'"
if [ -n "$($ES get /argus/d312/prueba --print-value-only 2>/dev/null)" ]; then
  ok "M2a /argus/d312/prueba ya existe (corrida anterior)"
else
  $ES put /argus/d312/prueba d312etcd > /dev/null 2>&1 && ok "M2a escrita /argus/d312/prueba" || ko "M2a escritura"
fi
[ "$($ES get /argus/d312/prueba --print-value-only 2>/dev/null)" = "d312etcd" ] && ok "M2b relectura d312etcd" || ko "M2b relectura"
$ES put /fuera-de-argus 1 2>&1 | grep -q 'permission denied' && ok "M3 escribir fuera de /argus/ -> permission denied" || ko "M3 fuera de /argus/ no se negó"
if [ $# -eq 2 ]; then
  CN=$(openssl x509 -in "$1" -noout -subject -nameopt RFC2253 | sed 's/^subject=//; s/^CN=\([^,]*\).*/\1/')
  O=$(etcdctl --endpoints=$EP --cacert=$CA --cert="$1" --key="$2" get /argus/d312/prueba --print-value-only 2>&1)
  echo "$O" | grep -qiE 'permission denied|user name not found|authentication failed' && ok "M4 identidad $CN sin permiso en /argus/ (RBAC)" || ko "M4 identidad $CN leyó: '$O'"
else
  echo "[ETCD-MEDIR] M4 omitida (sin CERT_OTRO KEY_OTRO)"
fi
H=$(curl -s -o /dev/null -w '%{http_code}' --cacert $CA $EP/health); RC=$?
[ "$RC" -ne 0 ] && [ "$H" = "000" ] && ok "M5 sin certificado de cliente: sin TLS (curl rc=$RC)" || ko "M5 sin certificado: http=$H rc=$RC"
L=$(ss -ltnH '( sport = :2381 or sport = :2382 )' | awk '{print $4}' | sort -u | tr '\n' ' ')
[ "$L" = "127.0.0.1:2381 127.0.0.1:2382 " ] && ok "M6 escucha solo en 127.0.0.1:2381 y :2382" || ko "M6 escucha: $L"
P=$(stat -c '%a %U' /var/lib/etcd 2>/dev/null)
[ "$P" = "700 etcd" ] && ok "M7 /var/lib/etcd 700 etcd" || ko "M7 /var/lib/etcd: $P"
N=$(journalctl -u etcd -b --no-pager 2>/dev/null | grep -c 'incompatible key usage')
[ "$N" = "0" ] && ok "M8 0 rechazos 'incompatible key usage' desde el arranque" || ko "M8 $N rechazos 'incompatible key usage' (¿certificado etcd sin clientAuth?)"
echo "[ETCD-MEDIR] RESULTADO $([ $R -eq 0 ] && echo PASA || echo FALLA)"
exit $R
