#!/usr/bin/env bash
# test_vm_estado_almacen.sh — DAY324 [ALMACEN-ESCRIBE-D324]: etcd_vm_estado.sh da NO SANO cuando el etcd-server no
# escribe en etcd (medido DAY324: /health 200 y etcd 3/3 sanos, pero el etcd-server sin alcanzar etcd y el check en SANO).
# Sin VMs (Mac, raíz del repo: make test-vm-estado-almacen): el script de verdad sobre una copia que solo cambia la ruta
# del JSON, con sudo, systemctl, curl y etcdctl de mentira en el PATH (etcd 1/1 sano, Vault activo, /health 200). Lo
# único que cambia entre casos es el latido propio del etcd-server en etcd y el bloque heartbeat del JSON.
#   A1 fresco (hace 10 s, límite 30x3=90 del JSON)    -> ✅ almacén, SANO, rc 0
#   A2 viejo (hace 200 s, límite 90)                   -> ❌ almacén, NO SANO, rc 1 (--estricto)
#   A3 ausente (el caso medido DAY324)                 -> ❌ almacén, NO SANO, rc 1
#   A4 etcd no responde a la lectura                   -> ❌ almacén, NO SANO, rc 1
#   A5 hace 200 s con heartbeat 100x3=300 en el JSON   -> ✅ (el límite sale del JSON, no de una constante)
#   A6 hace 200 s con interval_seconds "abc"           -> ❌ y el informe dice "defecto: 'abc' mal formado" (30x3=90)
set -u
LC_ALL=C; export LC_ALL
ORIG=scripts/etcd_ha/etcd_vm_estado.sh
falla() { echo "[TEST-VM-ESTADO-ALMACEN] FALLA: $*"; exit 1; }
[ -f "$ORIG" ] || falla "no estoy en la raíz del repo (falta $ORIG)"
T=$(mktemp -d /tmp/argus_test_vmest.XXXXXX) || falla "mktemp"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
grep -c '^JSON=/etc/ml-defender/etcd-server/etcd-server.json$' "$ORIG" | grep -qx 1 || falla "$ORIG: la línea JSON= no aparece exactamente una vez"
sed "s|^JSON=/etc/ml-defender/etcd-server/etcd-server.json\$|JSON=$T/etcd-server.json|" "$ORIG" > "$T/estado.sh"

cat > "$T/bin/sudo" <<'S'
#!/usr/bin/env bash
exec "$@"
S
cat > "$T/bin/systemctl" <<'S'
#!/usr/bin/env bash
echo active
S
cat > "$T/bin/curl" <<'S'
#!/usr/bin/env bash
printf 200
S
cat > "$T/bin/etcdctl" <<'S'
#!/usr/bin/env bash
a="$*"
case "$a" in
  *"member list"*) echo '{"members":[{"ID":1,"name":"control-1","clientURLs":["https://192.168.100.20:2381"]}]}';;
  *"endpoint status"*) echo '[{"Endpoint":"https://192.168.100.20:2381","Status":{"header":{"member_id":1},"leader":1,"raftIndex":5,"raftAppliedIndex":5,"raftTerm":2}}]';;
  *"endpoint health"*) echo '[{"endpoint":"https://192.168.100.20:2381","health":true}]';;
  *"get /argus/latido/etcd-server"*)
    case "$ARGUS_T_LATIDO" in
      nada) exit 1;;
      ausente) echo '{"kvs":[]}';;
      *) v=$(printf '{"estado":"activo","ultimo":%s}' "$ARGUS_T_LATIDO" | base64 | tr -d '\n')
         printf '{"kvs":[{"key":"L2FyZ3VzL2xhdGlkby9ldGNkLXNlcnZlcg==","value":"%s"}]}\n' "$v";;
    esac;;
  *"get "*) echo '{"kvs":[]}';;
  *) exit 1;;
esac
S
chmod +x "$T/bin/"*

json() {  # $1 = bloque heartbeat
  cat > "$T/etcd-server.json" <<J
{"almacen": {"endpoints": ["https://127.0.0.1:2381"], "ca_file": "/x/ca.crt", "cert_file": "/x/e.crt", "key_file": "/x/e.key", "prefijo": "/argus/"},
 "almacen_claves": {"vault_addrs": ["https://127.0.0.1:8200"], "ca_file": "/x/ca.crt", "cert_file": "/x/v.crt", "key_file": "/x/v.key"},
 "tls": {"ca_file": "/x/ca.crt", "cert_file": "/x/e.crt", "key_file": "/x/e.key"}, "server": {"port": 2379}, "heartbeat": $1}
J
}
caso() {  # nombre latido rc_esperado marca_esperada [texto_esperado]
  local n=$1 lat=$2 rce=$3 marca=$4 txt=${5:-} rc
  ARGUS_T_LATIDO=$lat PATH="$T/bin:$PATH" bash "$T/estado.sh" --estricto > "$T/$n.txt" 2>&1; rc=$?
  grep -q "^  $marca almacén:" "$T/$n.txt" && [ "$rc" = "$rce" ] && { [ -z "$txt" ] || grep -qF "$txt" "$T/$n.txt"; } \
    || { cat "$T/$n.txt"; falla "$n: esperado $marca almacén, rc $rce${txt:+ y '$txt'}; rc real $rc"; }
  echo "[TEST-VM-ESTADO-ALMACEN] $n PASA: $(grep "almacén:" "$T/$n.txt" | sed 's/^ *//')"
}
AHORA=$(date +%s)
json '{"interval_seconds": 30, "timeout_multiplier": 3, "check_interval_seconds": 10}'
caso A1 $((AHORA - 10))  0 ✅
caso A2 $((AHORA - 200)) 1 ❌
caso A3 ausente          1 ❌ "ausente"
caso A4 nada             1 ❌ "no responde"
json '{"interval_seconds": 100, "timeout_multiplier": 3, "check_interval_seconds": 10}'
caso A5 $((AHORA - 200)) 0 ✅ "límite 300 s"
json '{"interval_seconds": "abc", "timeout_multiplier": 3, "check_interval_seconds": 10}'
caso A6 $((AHORA - 200)) 1 ❌ "defecto: 'abc' mal formado"
echo "[TEST-VM-ESTADO-ALMACEN] RESULTADO PASA: 6 casos"
