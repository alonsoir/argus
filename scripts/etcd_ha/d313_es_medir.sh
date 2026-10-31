#!/bin/bash
# d313_es_medir.sh — DAY313, paso 4b.2 de DEBT-ETCD-HA-TLS-RAFT-001: medidas del etcd-server con HTTPS + mTLS y
# autorización por (OU, CN). Se ejecuta en el DEFENDER (el único que alcanza el 2379 de la VM etcd por nftables).
#   bash d313_es_medir.sh URL DIR
#     URL: https://192.168.100.20:2379 (sin barra final)
#     DIR: directorio con ca.crt y los certificados de cliente (admin, sniffer, ml-detector, vault; opcionales
#          sniffer-2 y bronze-to-gold-converter) con sus .key. Debe estar en memoria (/dev/shm), nunca en /vagrant.
# Nunca imprime una clave: los cuerpos de /secrets van a /dev/null y solo se escribe el código HTTP y el rc de curl.
# Predicciones escritas antes de medir: columna "esperado". Resultado: RESULTADO PASA solo si todas cuadran.
set -uo pipefail
LC_ALL=C; export LC_ALL
URL=${1:-}; DIR=${2:-}
ts() { date -u +%FT%TZ; }
[[ "$URL" =~ ^https://[0-9.]+:[0-9]+$ ]] || { echo "[D313] FALLA: URL '$URL' (https://IP:PUERTO)"; exit 1; }
[ -f "$DIR/ca.crt" ] || { echo "[D313] FALLA: no hay $DIR/ca.crt"; exit 1; }
case "$DIR" in /vagrant*|/home*) echo "[D313] FALLA: $DIR no debe estar en disco compartido (usar /dev/shm)"; exit 1;; esac
for r in admin sniffer ml-detector vault; do
  [ -f "$DIR/$r.crt" ] && [ -f "$DIR/$r.key" ] || { echo "[D313] FALLA: falta $DIR/$r.crt o .key"; exit 1; }
done
HP=${URL#https://}
TMP=$(mktemp -d /dev/shm/d313.XXXXXX); trap 'rm -rf "$TMP"' EXIT
FALLOS=0; N=0

# medir NOMBRE ESPERADO METODO RUTA [ROL]  — ESPERADO: código HTTP (200, 403, 404) o "tls" (sin respuesta HTTP)
medir() {
  local nom=$1 esp=$2 met=$3 ruta=$4 rol=${5:-}
  local args=(-sS -o /dev/null -w '%{http_code}' --max-time 10 --path-as-is --cacert "$DIR/ca.crt" -X "$met")
  [ -n "$rol" ] && args+=(--cert "$DIR/$rol.crt" --key "$DIR/$rol.key")
  [ "$met" = POST ] && args+=(-H 'Content-Type: application/json' --data '{"timestamp": 1}')
  local code rc
  code=$(curl "${args[@]}" "$URL$ruta" 2>/dev/null); rc=$?
  medir_fin "$nom" "$esp" "$code" "$rc" "$met $ruta ${rol:-sin-certificado}"
}
medir_fin() {
  local nom=$1 esp=$2 code=$3 rc=$4 que=$5 ok=FALLA
  N=$((N+1))
  if [ "$esp" = tls ]; then
    [ "$code" = 000 ] && [ "$rc" != 0 ] && ok=PASA
  else
    [ "$code" = "$esp" ] && [ "$rc" = 0 ] && ok=PASA
  fi
  [ "$ok" = PASA ] || FALLOS=$((FALLOS+1))
  printf '[D313] %s %-4s %-58s esperado=%-3s http=%s rc=%s %s\n' "$(ts)" "$nom" "$que" "$esp" "$code" "$rc" "$ok"
}

echo "[D313] $(ts) $(hostname) -> $URL; certificados en $DIR"
# ── sin TLS válido no se llega a ninguna ruta ───────────────────────────────
medir M1 tls GET /health
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 1 \
  -subj "/O=aRGus-lab/OU=admin/CN=admin" -keyout "$TMP/otra.key" -out "$TMP/otra.crt" > /dev/null 2>&1
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 --cacert "$DIR/ca.crt" \
  --cert "$TMP/otra.crt" --key "$TMP/otra.key" "$URL/health" 2>/dev/null); rc=$?
medir_fin M2 tls "$code" "$rc" "GET /health admin-de-OTRA-CA"
medir M3 tls GET /health vault   # vault.crt: solo serverAuth (sin clientAuth)
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "http://$HP/health" 2>/dev/null); rc=$?
medir_fin M4 tls "$code" "$rc" "GET /health HTTP-en-claro"
# ── con certificado de la CA: autorización por (OU, CN) ─────────────────────
medir M5a 200 GET /health admin
medir M5b 200 GET /components admin
medir M5c 200 GET /health sniffer
medir M6 403 GET /secrets/ml-detector sniffer
medir M7 200 GET /secrets/sniffer sniffer
medir M8 404 POST /v1/heartbeat/ml-detector ml-detector
medir M9a 403 GET /seed admin
medir M9b 403 GET /secrets/keys admin
medir M10 403 POST /secrets/rotate/sniffer sniffer
medir M11 403 GET /components sniffer
medir M12 403 GET /secrets/sniffer%2Fx sniffer
medir M13 403 GET /secrets/sniffer/ sniffer
if [ -f "$DIR/sniffer-2.crt" ]; then
  medir M14 403 GET /secrets/sniffer sniffer-2
else
  echo "[D313] $(ts) M14  sin sniffer-2.crt: no se mide (opcional)"
fi
if [ -f "$DIR/bronze-to-gold-converter.crt" ]; then
  medir M15a 200 GET /secrets/valid/ml-detector bronze-to-gold-converter
  medir M15b 403 GET /secrets/ml-detector bronze-to-gold-converter
else
  echo "[D313] $(ts) M15  sin bronze-to-gold-converter.crt: no se mide (opcional)"
fi
# el propio etcd-server aparece registrado (en proceso) en /components
body=$(curl -sS --max-time 10 --cacert "$DIR/ca.crt" --cert "$DIR/admin.crt" --key "$DIR/admin.key" "$URL/components" 2>/dev/null)
N=$((N+1))
if printf '%s' "$body" | grep -q '"etcd-server"'; then
  echo "[D313] $(ts) M16  /components incluye etcd-server (registro en proceso)                        PASA"
else
  echo "[D313] $(ts) M16  /components NO incluye etcd-server: $body  FALLA"; FALLOS=$((FALLOS+1))
fi
echo "[D313] $(ts) medidas=$N fallos=$FALLOS"
[ "$FALLOS" = 0 ] && echo "[D313] RESULTADO PASA" || { echo "[D313] RESULTADO FALLA"; exit 1; }
