#!/bin/bash
# d315_paso3_medir.sh — [ETCD-ALMACEN-FATAL-D315] medida del paso 3 en la VM etcd, con el binario real y el JSON que
# escribió Ansible. Se ejecuta EN LA VM etcd. El etcd-server debe estar parado (nadie en 2379).
#   F1 el JSON desplegado: --check-config rc=0, almacen_fatales=0
#   F2 sin almacen.endpoints:          --check-config rc=1 y [ETCD-ALMACEN-FATAL] almacen.endpoints ausente
#   F3 prefijo con errata (/Argus/):   rc=1 y [ETCD-ALMACEN-FATAL] almacen.prefijo mal formado
#   F4 endpoints repetidos:            rc=1 y [ETCD-ALMACEN-FATAL] almacen.endpoints mal formado
#   F5 sin cert_file:                  rc=1 y [ETCD-ALMACEN-FATAL] almacen.cert_file ausente
#   F6 ARRANQUE real sin endpoints:    sale con rc=1 en < 5 s, [ETCD-ALMACEN-FATAL] 1 problemas, nadie escucha en 2379
# Los JSON de prueba van a un directorio temporal de root y se borran al salir.
set -uo pipefail
LC_ALL=C; export LC_ALL
BIN=/opt/argus/etcd-server/bin/etcd-server
LIB=/opt/argus/etcd-server/lib
JSON=/etc/ml-defender/etcd-server/etcd-server.json
ts() { date -u +%FT%TZ; }
falla() { echo "[D315-P3] $(ts) FALLA: $*"; exit 1; }
sudo test -x "$BIN" || falla "no existe $BIN"
sudo test -f "$JSON" || falla "no existe $JSON (make deploy-configs desde el Mac)"
sudo ss -ltnH 'sport = :2379' | grep -q . && falla "el 2379 está ocupado: parar antes el etcd-server"
T=$(sudo mktemp -d /root/d315p3.XXXXXX) || falla "mktemp"
trap 'sudo rm -rf "$T"' EXIT
N=0; FALLOS=0
medir() {  # id esperado obtenido descripción
    N=$((N+1)); local r=PASA
    [ "$2" = "$3" ] || { r=FALLA; FALLOS=$((FALLOS+1)); }
    printf '[D315-P3] %s %-4s %-58s esperado=%-6s obtenido=%-6s %s\n' "$(ts)" "$1" "$4" "$2" "$3" "$r"
}
variante() {  # nombre código-python que modifica d["almacen"]
    sudo python3 - "$JSON" "$T/$1.json" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); a = d["almacen"]
exec(sys.argv[3])
json.dump(d, open(sys.argv[2], "w"), indent=2)
PY
}
chk() {  # fichero -> imprime el rc; la salida completa queda en $T/salida.txt (todo dentro de un sudo: $T es de root)
    sudo bash -c 'LD_LIBRARY_PATH="$2" "$1" --check-config -c "$3" > "$4" 2>&1; echo $?' _ "$BIN" "$LIB" "$1" "$T/salida.txt"
}
cuenta() { sudo grep -c -- "$1" "$T/salida.txt" || true; }

echo "[D315-P3] $(ts) $(hostname) binario sha256 $(sudo sha256sum "$BIN" | cut -c1-16) JSON $JSON ($(sudo sha256sum "$JSON" | cut -c1-16))"
rc=$(chk "$JSON");                         medir F1  0 "$rc" "JSON desplegado: --check-config rc"
medir F1b 1 "$(cuenta 'almacen_fatales=0')" "JSON desplegado: almacen_fatales=0"

variante sin_ep 'del a["endpoints"]'
rc=$(chk "$T/sin_ep.json");                medir F2  1 "$rc" "sin endpoints: --check-config rc"
medir F2b 1 "$(cuenta '\[ETCD-ALMACEN-FATAL\] almacen.endpoints ausente')" "sin endpoints: [ETCD-ALMACEN-FATAL] almacen.endpoints ausente"
medir F2c 0 "$(cuenta '\[CONFIG-DEFAULT\] almacen.endpoints')" "sin endpoints: NO se aplica un defecto"

variante errata 'a["prefijo"] = "/Argus/"'
rc=$(chk "$T/errata.json");                medir F3  1 "$rc" "prefijo /Argus/: --check-config rc"
medir F3b 1 "$(cuenta '\[ETCD-ALMACEN-FATAL\] almacen.prefijo mal formado')" "prefijo /Argus/: [ETCD-ALMACEN-FATAL] almacen.prefijo"

variante repe 'a["endpoints"] = a["endpoints"] * 2'
rc=$(chk "$T/repe.json");                  medir F4  1 "$rc" "endpoints repetidos: --check-config rc"
medir F4b 1 "$(cuenta '\[ETCD-ALMACEN-FATAL\] almacen.endpoints mal formado')" "endpoints repetidos: [ETCD-ALMACEN-FATAL] almacen.endpoints"

variante sin_cert 'del a["cert_file"]'
rc=$(chk "$T/sin_cert.json");              medir F5  1 "$rc" "sin cert_file: --check-config rc"
medir F5b 1 "$(cuenta '\[ETCD-ALMACEN-FATAL\] almacen.cert_file ausente')" "sin cert_file: [ETCD-ALMACEN-FATAL] almacen.cert_file"

# F6: arranque real (sin --check-config) con el JSON sin endpoints: tiene que negarse antes de escuchar
T0=$(date +%s.%N)
rc=$(sudo bash -c 'LD_LIBRARY_PATH="$2" timeout 30 "$1" -c "$3" > "$4" 2>&1; echo $?' _ "$BIN" "$LIB" "$T/sin_ep.json" "$T/salida.txt")
T1=$(date +%s.%N)
DT=$(awk -v a="$T0" -v b="$T1" 'BEGIN{printf "%.2f", b-a}')
medir F6  1 "$rc" "arranque sin endpoints: rc (124 = timeout: arrancó)"
medir F6b si "$(awk -v d="$DT" 'BEGIN{print (d < 5.0) ? "si" : "no"}')" "arranque sin endpoints: sale en < 5 s (fue $DT s)"
medir F6c 1 "$(cuenta '\[ETCD-ALMACEN-FATAL\] 1 problemas en almacen')" "arranque sin endpoints: [ETCD-ALMACEN-FATAL] 1 problemas"
medir F6d 0 "$(sudo ss -ltnH 'sport = :2379' | grep -c .)" "nadie escucha en 2379 después"

echo "[D315-P3] $(ts) medidas=$N fallos=$FALLOS"
[ "$FALLOS" = 0 ] && echo "[D315-P3] RESULTADO PASA" || { echo "[D315-P3] RESULTADO FALLA"; exit 1; }
