#!/usr/bin/env bash
# test_etcd_cluster.sh — DAY324, PR2b paso 4 de DEBT-ETCD-HA-TLS-RAFT-001 [ETCD-CLUSTER-D324]: el clúster etcd de los
# nodos del plano de control, de verdad (VMs arriba: defender y los nodos). Mac, raíz del repo: make test-etcd-cluster.
# Lo esperado sale de argus_control_nodos (nodos_control.rb), nunca de una lista escrita aquí.
#   T1 idempotente: una segunda pasada de make etcd-cluster-deploy no cambia nada (changed=0, failed=0 en todos).
#   T2 miembros: member list = los nodos de la lista (nombre y URL de peer https://<ip>:2382). Y el comparador tiene que
#      FALLAR contra la lista con un nodo de más (control-99): un comparador ciego daría un verde falso.
#   T3 replicación: una clave escrita en control-1 se lee, con lectura serializable (la de cada miembro, sin pasar por
#      el líder), en cada miembro; se borra al acabar.
#   T4 TLS: un certificado que no es de la CA del laboratorio no entra (y el del etcd-server sí, como control).
#   T5 (informativo) endpoint hashkv --cluster: mismo resumen en todos; si el RBAC no lo deja, se dice NO MEDIDO.
set -u
LC_ALL=C; export LC_ALL
NODOS_RB=scripts/etcd_ha/nodos_control.rb
GV=ansible/inventory/group_vars/argus_dev.yml
falla() { echo "[TEST-ETCD-CLUSTER] FALLA: $*"; exit 1; }
[ -f "$NODOS_RB" ] && [ -f Vagrantfile ] || falla "no estoy en la raíz del repo"
command -v ruby >/dev/null || falla "falta ruby"
T=$(mktemp -d /tmp/argus_test_etcd.XXXXXX) || falla "mktemp"
trap 'rm -rf "$T"' EXIT
# < /dev/null: vagrant ssh lee la entrada estándar; dentro de un 'while read' se comería el resto de la lista
V() { local m=$1; shift; vagrant ssh "$m" -c "$*" < /dev/null 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; }
ruby "$NODOS_RB" nodos "$GV" Vagrantfile > "$T/lista.txt" 2>&1 || { cat "$T/lista.txt"; falla "la lista de nodos no vale"; }
awk -F'\t' '$1 == "nodo" {printf "{\"nombre\": \"%s\", \"ip\": \"%s\"}\n", $2, $3}' "$T/lista.txt" > "$T/nodos.jsonl"
NN=$(wc -l < "$T/nodos.jsonl" | tr -d ' ')
EPS=$(awk -F'\t' '$1 == "nodo" {printf "%shttps://%s:2381", (n++ ? "," : ""), $3}' "$T/lista.txt")
PRIMERO=$(awk -F'\t' '$1 == "nodo" {print $2; exit}' "$T/lista.txt")
E="sudo etcdctl --cacert=/etc/etcd/tls/ca.crt --cert=/etc/argus-pki/etcd-server.crt --key=/etc/argus-pki/etcd-server.key --command-timeout=5s"

# T1
make --no-print-directory etcd-cluster-deploy > "$T/deploy.txt" 2>&1 || { tail -30 "$T/deploy.txt"; falla "T1: make etcd-cluster-deploy falló"; }
# Ansible por 'vagrant ssh -t' colorea (hay terminal): se quitan los códigos ANSI y los \r antes de leer el PLAY RECAP
perl -pe 's/\e\[[0-9;]*[A-Za-z]//g; s/\r//g' "$T/deploy.txt" | grep -aE '^[a-z0-9-]+ +: ok=' > "$T/recap.txt"
[ "$(grep -c . "$T/recap.txt")" -ge "$NN" ] || { tail -20 "$T/deploy.txt"; falla "T1: sin PLAY RECAP de los $NN nodos"; }
grep -vE 'changed=0 +unreachable=0 +failed=0' "$T/recap.txt" | grep -q . && { cat "$T/recap.txt"; falla "T1: la segunda pasada cambió algo o falló"; }
echo "[TEST-ETCD-CLUSTER] T1 PASA: segunda pasada sin cambios ($(grep -c . "$T/recap.txt") máquinas con changed=0 failed=0)"

# T2
V "$PRIMERO" "$E --endpoints=$EPS member list -w json" > "$T/ml.json"
cat > "$T/compara.py" <<'PY'
import json, sys
ml = json.load(open(sys.argv[1]))["members"]
esperados = {}
for l in open(sys.argv[2]):
    n = json.loads(l); esperados[n["nombre"]] = "https://%s:2382" % n["ip"]
reales = {m.get("name", "?"): (m.get("peerURLs") or ["?"])[0] for m in ml}
print("reales=%s esperados=%s" % (sorted(reales.items()), sorted(esperados.items())))
sys.exit(0 if reales == esperados else 1)
PY
python3 -I "$T/compara.py" "$T/ml.json" "$T/nodos.jsonl" > "$T/c1.txt" 2>&1 || { cat "$T/c1.txt"; falla "T2: los miembros no son los de la lista"; }
cp "$T/nodos.jsonl" "$T/nodos_mas.jsonl"; echo '{"nombre": "control-99", "ip": "192.168.100.99"}' >> "$T/nodos_mas.jsonl"
python3 -I "$T/compara.py" "$T/ml.json" "$T/nodos_mas.jsonl" > "$T/c2.txt" 2>&1 && { cat "$T/c2.txt"; falla "T2: el comparador no ve un nodo de más (ciego)"; }
echo "[TEST-ETCD-CLUSTER] T2 PASA: $NN miembros con su URL de peer; contra una lista con control-99 el comparador falla"

# T3
K="/argus/test-etcd-cluster/$(date -u +%Y%m%dT%H%M%SZ)"; VAL="d324-$RANDOM-$RANDOM"
V "$PRIMERO" "$E --endpoints=https://127.0.0.1:2381 put $K $VAL" | grep -q '^OK$' || falla "T3: no se pudo escribir $K"
mal=0; leidos=0
while IFS=$'\t' read -r k nodo ip mac; do
  [ "$k" = nodo ] || continue
  leidos=$((leidos+1))
  got=$(V "$PRIMERO" "$E --endpoints=https://$ip:2381 --consistency=s get $K --print-value-only")
  [ "$got" = "$VAL" ] && echo "  $nodo ($ip): leído '$got'" || { echo "  $nodo ($ip): leído '$got', esperado '$VAL'"; mal=$((mal+1)); }
done < "$T/lista.txt"
V "$PRIMERO" "$E --endpoints=https://127.0.0.1:2381 del $K" > /dev/null
[ "$mal" -eq 0 ] || falla "T3: $mal miembros sin la clave"
[ "$leidos" -eq "$NN" ] || falla "T3: leídos $leidos miembros de $NN (el bucle no recorrió la lista entera)"
echo "[TEST-ETCD-CLUSTER] T3 PASA: escrita en $PRIMERO, leída (serializable) en los $leidos miembros; borrada"

# T4
V "$PRIMERO" "cd /tmp && openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 1 -subj /CN=intruso -keyout argus_intruso.key -out argus_intruso.crt 2>/dev/null; $E --endpoints=https://127.0.0.1:2381 endpoint health > /tmp/argus_t4_bien.txt 2>&1; echo BIEN=\$?; sudo etcdctl --cacert=/etc/etcd/tls/ca.crt --cert=/tmp/argus_intruso.crt --key=/tmp/argus_intruso.key --command-timeout=5s --endpoints=https://127.0.0.1:2381 endpoint health > /tmp/argus_t4_mal.txt 2>&1; echo INTRUSO=\$?; rm -f /tmp/argus_intruso.*" > "$T/t4.txt"
grep -q '^BIEN=0$' "$T/t4.txt" || { cat "$T/t4.txt"; falla "T4: el certificado del etcd-server no entra (el control falla)"; }
grep -q '^INTRUSO=0$' "$T/t4.txt" && { cat "$T/t4.txt"; falla "T4: un certificado ajeno a la CA ENTRA"; }
echo "[TEST-ETCD-CLUSTER] T4 PASA: el certificado del etcd-server entra; uno ajeno a la CA no"

# T5 (informativo)
V "$PRIMERO" "$E --endpoints=$EPS endpoint hashkv -w json 2>&1" > "$T/hk.txt"
python3 -I - "$T/hk.txt" <<'PY'
import json, sys
t = open(sys.argv[1]).read()
try:
    hs = json.loads(t)
except Exception:
    ult = (t.strip().splitlines() or ["(vacío)"])[-1]  # la causa va en la última línea, tras los avisos de reintento
    print("[TEST-ETCD-CLUSTER] T5 NO MEDIDO: hashkv no devuelve JSON (%s)" % ult[:200]); sys.exit(0)
v = {h["Endpoint"]: h["HashKV"]["hash"] for h in hs}
print("[TEST-ETCD-CLUSTER] T5 %s: hashkv %s" % ("PASA" if len(set(v.values())) == 1 else "DISTINTO", v))
PY
echo "[TEST-ETCD-CLUSTER] RESULTADO PASA"
