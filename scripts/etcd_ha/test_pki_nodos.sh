#!/usr/bin/env bash
# test_pki_nodos.sh — DAY324, PR2b paso 3 de DEBT-ETCD-HA-TLS-RAFT-001 [PKI-NODOS-D324]: el modo 'nodos' de
# d312_pki.sh sobre una PKI de usar y tirar en /tmp (nunca la del laboratorio). Mac, raíz del repo: make test-pki-nodos.
#   T1 por cada nodo de la lista (la que valida nodos_control.rb, no una escrita aquí): etcd-, vault- y etcd-server-<nodo>
#      firmados por la CA, CN=<perfil>-<nodo>, OU=<perfil>, SAN con la IP del nodo y 127.0.0.1, EKU servidor y
#      cliente, clave 600.
#   T2 idempotente: una segunda pasada no emite ninguno y deja las mismas huellas.
#   T3 falla cuando debe (IP): con una copia del group_vars donde control-2 cambia de IP, 'nodos' falla nombrando el
#      certificado y la IP nueva, y no toca el certificado.
#   T4 falla cuando debe (CA): un certificado de nodo firmado por OTRA CA hace fallar 'nodos' (comprobar: verify).
set -u
LC_ALL=C; export LC_ALL
PKI_SH=scripts/etcd_ha/d312_pki.sh
NODOS_RB=scripts/etcd_ha/nodos_control.rb
GV=ansible/inventory/group_vars/argus_dev.yml
falla() { echo "[TEST-PKI-NODOS] FALLA: $*"; exit 1; }
[ -f "$PKI_SH" ] && [ -f "$NODOS_RB" ] && [ -f Vagrantfile ] || falla "no estoy en la raíz del repo"
for c in openssl ruby; do command -v "$c" >/dev/null || falla "falta $c"; done
T=$(mktemp -d /tmp/argus_test_pki.XXXXXX) || falla "mktemp"
trap 'rm -rf "$T"' EXIT
P="$T/pki"

bash "$PKI_SH" init "$P" > "$T/init.txt" 2>&1 || { cat "$T/init.txt"; falla "init de la PKI de prueba"; }
ruby "$NODOS_RB" nodos "$GV" Vagrantfile > "$T/lista.txt" 2>&1 || { cat "$T/lista.txt"; falla "la lista de nodos no vale"; }
NN=$(awk -F'\t' '$1 == "nodo"' "$T/lista.txt" | wc -l | tr -d ' ')
[ "$NN" -ge 1 ] || falla "la lista no trae nodos"

# T1
bash "$PKI_SH" nodos "$P" > "$T/n1.txt" 2>&1 || { cat "$T/n1.txt"; falla "T1: 'nodos' falló"; }
grep -q "nodos: $((NN * 3)) certificados nuevos, 0 ya estaban" "$T/n1.txt" || { cat "$T/n1.txt"; falla "T1: esperaba $((NN * 3)) nuevos"; }
mal=0
while IFS=$'\t' read -r k nodo ip mac; do
  [ "$k" = nodo ] || continue
  for perfil in etcd vault etcd-server; do
    f="$P/$perfil-$nodo.crt"; key="$P/$perfil-$nodo.key"
    [ -s "$f" ] && [ -s "$key" ] || { echo "  falta $f o su clave"; mal=$((mal+1)); continue; }
    openssl verify -CAfile "$P/ca.crt" "$f" > /dev/null 2>&1 || { echo "  $f no lo firmó la CA"; mal=$((mal+1)); }
    sj=$(openssl x509 -in "$f" -noout -subject -nameopt RFC2253)
    echo "$sj" | grep -q "CN=$perfil-$nodo" && echo "$sj" | grep -q "OU=$perfil" || { echo "  $f: sujeto $sj"; mal=$((mal+1)); }
    san=$(openssl x509 -in "$f" -noout -text | sed -n '/Subject Alternative Name/{n;p;}')
    for e in "IP Address:$ip" "IP Address:127.0.0.1"; do echo "$san" | grep -qF "$e" || { echo "  $f: SAN '$san' sin $e"; mal=$((mal+1)); }; done
    eku=$(openssl x509 -in "$f" -noout -text | sed -n '/Extended Key Usage/{n;p;}')
    for e in "TLS Web Server Authentication" "TLS Web Client Authentication"; do echo "$eku" | grep -qF "$e" || { echo "  $f: EKU '$eku' sin $e"; mal=$((mal+1)); }; done
    if [ "$(uname -s)" = Darwin ]; then pm=$(stat -f %Lp "$key"); else pm=$(stat -c %a "$key"); fi
    [ "$pm" = 600 ] || { echo "  $key con permisos $pm"; mal=$((mal+1)); }
  done
done < "$T/lista.txt"
[ "$mal" -eq 0 ] || falla "T1: $mal problemas (arriba)"
echo "[TEST-PKI-NODOS] T1 PASA: $NN nodos x 3 certificados, firmados por la CA, CN/OU, SAN con su IP y 127.0.0.1, EKU y claves 600"

# T2
h1=$(for f in "$P"/*.crt; do openssl x509 -in "$f" -noout -fingerprint -sha256; done | sort)
bash "$PKI_SH" nodos "$P" > "$T/n2.txt" 2>&1 || { cat "$T/n2.txt"; falla "T2: la segunda pasada falló"; }
grep -q "nodos: 0 certificados nuevos, $((NN * 3)) ya estaban con su IP" "$T/n2.txt" || { cat "$T/n2.txt"; falla "T2: la segunda pasada emitió algo"; }
h2=$(for f in "$P"/*.crt; do openssl x509 -in "$f" -noout -fingerprint -sha256; done | sort)
[ "$h1" = "$h2" ] || falla "T2: cambiaron huellas en la segunda pasada"
echo "[TEST-PKI-NODOS] T2 PASA: segunda pasada sin emitir nada y con las mismas huellas"

# T3 (necesita un control-2 en la lista: es el que se estropea)
IP2=$(awk -F'\t' '$1 == "nodo" && $2 == "control-2" {print $3}' "$T/lista.txt")
[ -n "$IP2" ] || falla "T3: la lista no trae control-2"
NUEVA=192.168.100.23
awk -F'\t' -v n="$NUEVA" '$3 == n' "$T/lista.txt" | grep -q . && falla "T3: $NUEVA ya está en la lista"
sed "s/nombre: control-2, ip: $IP2,/nombre: control-2, ip: $NUEVA,/" "$GV" > "$T/gv_ip.yml"
cmp -s "$GV" "$T/gv_ip.yml" && falla "T3: la copia del group_vars no cambió (¿otro formato de línea?)"
h_antes=$(openssl x509 -in "$P/etcd-control-2.crt" -noout -fingerprint -sha256)
if bash "$PKI_SH" nodos "$P" "$T/gv_ip.yml" Vagrantfile > "$T/n3.txt" 2>&1; then cat "$T/n3.txt"; falla "T3: con la IP cambiada debía fallar"; fi
grep -q "etcd-control-2.crt existe sin IP:$NUEVA" "$T/n3.txt" || { cat "$T/n3.txt"; falla "T3: falló, pero sin nombrar el certificado y la IP"; }
[ "$h_antes" = "$(openssl x509 -in "$P/etcd-control-2.crt" -noout -fingerprint -sha256)" ] || falla "T3: tocó el certificado"
echo "[TEST-PKI-NODOS] T3 PASA: una IP cambiada hace fallar nombrando etcd-control-2.crt e IP:$NUEVA, sin tocarlo"

# T4
bash "$PKI_SH" init "$T/otra" > "$T/init2.txt" 2>&1 || { cat "$T/init2.txt"; falla "T4: init de la segunda PKI"; }
bash "$PKI_SH" nodos "$T/otra" > "$T/n4a.txt" 2>&1 || { cat "$T/n4a.txt"; falla "T4: nodos en la segunda PKI"; }
cp "$T/otra/vault-control-1.crt" "$P/vault-control-1.crt"; cp "$T/otra/vault-control-1.key" "$P/vault-control-1.key"
if bash "$PKI_SH" nodos "$P" > "$T/n4.txt" 2>&1; then cat "$T/n4.txt"; falla "T4: con un certificado de otra CA debía fallar"; fi
grep -q "vault-control-1.crt .*verify=FALLA" "$T/n4.txt" || { cat "$T/n4.txt"; falla "T4: falló, pero no por el verify de vault-control-1.crt"; }
echo "[TEST-PKI-NODOS] T4 PASA: un certificado de otra CA hace fallar (verify=FALLA en vault-control-1.crt)"
echo "[TEST-PKI-NODOS] RESULTADO PASA"
