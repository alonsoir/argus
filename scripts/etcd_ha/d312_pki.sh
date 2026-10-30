#!/usr/bin/env bash
# d312_pki.sh — PKI del laboratorio para el etcd-server con mTLS (DAY312, paso 0 de DEBT-ETCD-HA-TLS-RAFT-001)
# Se ejecuta en el Mac. Las claves privadas NUNCA entran en el repo: el directorio debe estar fuera de cualquier repo git.
#   bash d312_pki.sh init    DIR [IP_VM_ETCD]   crea la CA y los certificados de servidor y de cliente
#   bash d312_pki.sh cliente DIR ROL [INSTANCIA] añade un certificado de cliente (CN=INSTANCIA, defecto ROL; OU=ROL)
# Identidad (DAY312): CN = instancia (clave HMAC propia, /secrets/{CN}); OU = rol (permisos de todo el rol).
# Parámetros (entorno): PKI_DIAS_CA (defecto 3650, rango 365-7300), PKI_DIAS_HOJA (defecto 397, rango 30-825).
# Por la terminal solo salen huellas SHA-256 de certificados; nunca una clave.
set -euo pipefail
umask 077
LC_ALL=C; export LC_ALL

falla() { echo "[PKI] FALLA: $*" >&2; exit 1; }
log()   { echo "[PKI] $*"; }

entero_en_rango() {  # nombre valor defecto min max
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then log "$n=$d (defecto: ausente)"; echo "$d" >&3; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then
    log "$n=$d (defecto: '$v' mal formado; entero en [$lo, $hi])"; echo "$d" >&3; return
  fi
  log "$n=$v (entorno)"; echo "$v" >&3
}

perm() { if [ "$(uname -s)" = Darwin ]; then stat -f %Lp "$1"; else stat -c %a "$1"; fi; }
huella() { openssl x509 -in "$1" -noout -fingerprint -sha256 | sed 's/^.*=//; s/://g' | tr 'A-F' 'a-f'; }

firmar() {  # nombre cn ou eku san
  local nom=$1 cn=$2 ou=$3 eku=$4 san=$5
  [ -e "$D/$nom.crt" ] && falla "$D/$nom.crt ya existe"
  openssl ecparam -name prime256v1 -genkey -noout -out "$D/$nom.key"
  openssl req -new -key "$D/$nom.key" -subj "/O=aRGus-lab/OU=$ou/CN=$cn" -out "$D/$nom.csr"
  {
    echo "basicConstraints=critical,CA:FALSE"
    echo "keyUsage=critical,digitalSignature,keyAgreement"
    echo "extendedKeyUsage=$eku"
    echo "subjectKeyIdentifier=hash"
    echo "authorityKeyIdentifier=keyid"
    [ -n "$san" ] && echo "subjectAltName=$san"
  } > "$D/$nom.ext"
  openssl x509 -req -in "$D/$nom.csr" -CA "$D/ca.crt" -CAkey "$D/ca.key" \
    -set_serial "0x$(openssl rand -hex 16)" -days "$DIAS_HOJA" -sha256 -extfile "$D/$nom.ext" -out "$D/$nom.crt" 2>/dev/null
  rm -f "$D/$nom.csr" "$D/$nom.ext"
  chmod 600 "$D/$nom.key"; chmod 644 "$D/$nom.crt"
}

comprobar() {
  local mal=0 n=0 f
  for f in "$D"/*.crt; do
    [ "$(basename "$f")" = ca.crt ] && continue
    n=$((n+1))
    if openssl verify -CAfile "$D/ca.crt" "$f" >/dev/null 2>&1; then v=OK; else v=FALLA; mal=$((mal+1)); fi
    k="${f%.crt}.key"; p=$(perm "$k")
    [ "$p" = 600 ] || { mal=$((mal+1)); v="$v perm_clave=$p"; }
    sj=$(openssl x509 -in "$f" -noout -subject -nameopt RFC2253)
    cn=$(echo "$sj" | sed -n 's/.*CN=\([^,]*\).*/\1/p'); ou=$(echo "$sj" | sed -n 's/.*OU=\([^,]*\).*/\1/p')
    [ -n "$cn" ] && [ -n "$ou" ] || { mal=$((mal+1)); v="$v sin_CN_u_OU"; }
    log "$(basename "$f") CN=$cn OU=$ou verify=$v huella=$(huella "$f" | cut -c1-16)"
  done
  log "certificados_hoja=$n fallos=$mal"
  [ "$mal" -eq 0 ] || falla "hay $mal fallos"
}

fuera_de_git() {  # el directorio (o su padre si no existe) no puede estar dentro de un repo git
  local p=$1; [ -d "$p" ] || p=$(dirname "$p")
  if git -C "$p" rev-parse --is-inside-work-tree >/dev/null 2>&1; then falla "$1 está dentro de un repo git: las claves no pueden ir ahí"; fi
}

MODO=${1:-}; D=${2:-}
[ -n "$MODO" ] && [ -n "$D" ] || falla "uso: $0 init DIR [IP_VM_ETCD] | $0 cliente DIR ROL [INSTANCIA]"
command -v openssl >/dev/null || falla "no hay openssl"
log "openssl: $(openssl version)"
exec 3>/tmp/d312_pki_val.$$
entero_en_rango PKI_DIAS_CA   "${PKI_DIAS_CA:-}"   3650 365 7300
entero_en_rango PKI_DIAS_HOJA "${PKI_DIAS_HOJA:-}" 397  30  825
exec 3>&-
{ read -r DIAS_CA; read -r DIAS_HOJA; } < /tmp/d312_pki_val.$$; rm -f /tmp/d312_pki_val.$$

case "$MODO" in
  init)
    IP=${3:-192.168.100.20}
    [[ "$IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || falla "IP '$IP' mal formada"
    log "IP_VM_ETCD=$IP ($([ -n "${3:-}" ] && echo argumento || echo 'defecto: ausente'))"
    [ -e "$D" ] && falla "$D ya existe: no se sobrescribe una PKI"
    fuera_de_git "$D"
    mkdir -p "$D"; chmod 700 "$D"
    openssl ecparam -name prime256v1 -genkey -noout -out "$D/ca.key"
    printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n' > "$D/ca.ext"
    openssl req -new -key "$D/ca.key" -subj "/O=aRGus-lab/CN=aRGus lab CA" -out "$D/ca.csr"
    openssl x509 -req -in "$D/ca.csr" -signkey "$D/ca.key" -days "$DIAS_CA" -sha256 \
      -set_serial "0x$(openssl rand -hex 16)" -extfile "$D/ca.ext" -out "$D/ca.crt" 2>/dev/null
    rm -f "$D/ca.csr" "$D/ca.ext"; chmod 600 "$D/ca.key"; chmod 644 "$D/ca.crt"
    log "CA creada huella=$(huella "$D/ca.crt" | cut -c1-16)"
    # Servidores
    firmar etcd-server   etcd-server   etcd-server "serverAuth,clientAuth" "DNS:etcd,DNS:localhost,IP:$IP,IP:127.0.0.1"
    firmar vault         vault         vault       serverAuth              "DNS:localhost,IP:127.0.0.1"
    firmar etcd          etcd          etcd        serverAuth              "DNS:localhost,IP:127.0.0.1"
    # Clientes: una instancia por rol en el PR1 (CN = OU = nombre con el que cada componente se registra hoy)
    for r in sniffer ml-detector firewall-acl-agent admin; do firmar "$r" "$r" "$r" clientAuth ""; done
    comprobar
    ;;
  cliente)
    ROL=${3:-}; CN=${4:-$ROL}
    for x in "$ROL" "$CN"; do
      [[ "$x" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]] || falla "nombre '$x' mal formado (minúsculas, cifras y guiones, 1-63)"
    done
    log "ROL=$ROL INSTANCIA=$CN ($([ -n "${4:-}" ] && echo argumento || echo 'defecto: igual al rol'))"
    [ -f "$D/ca.crt" ] && [ -f "$D/ca.key" ] || falla "$D no tiene CA: primero init"
    fuera_de_git "$D"
    firmar "$CN" "$CN" "$ROL" clientAuth ""
    comprobar
    ;;
  *) falla "modo '$MODO' desconocido (init | cliente)";;
esac
log "HECHO en $D"
