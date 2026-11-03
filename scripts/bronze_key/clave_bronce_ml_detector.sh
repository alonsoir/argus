#!/usr/bin/env bash
# [ETCD-CLIENTE-D316] E5 (DEBT-ETCD-HA-TLS-RAFT-001 paso 5). Se ejecuta EN EL DEFENDER con sudo (las .key son 0600 root).
# Imprime en stdout la clave HMAC ACTIVA de ml-detector (64 hex) que mitre/ctu/custom-start pasan al
# bronze-to-gold-converter. La pide por mTLS, con la identidad del converter (OU=CN=bronze-to-gold-converter, la
# regla de /secrets/valid/{c} le deja leerla), a la primera dirección del bloque etcd de ml-detector: así el
# converter y ml-detector hablan con el mismo etcd-server y no pueden quedar con claves distintas.
# La misma clave firma también el bronce de Suricata/Zeek: DEBT-BRONZE-HMAC-KEY-POLICY-001 (sin cambios aquí).
# Errores: a stderr, salida 1.
set -euo pipefail
JSON=${JSON:-/etc/ml-defender/ml-detector/ml_detector_config.json}
PKI=${PKI:-/etc/argus-pki}
ID=bronze-to-gold-converter

for f in "$JSON" "$PKI/ca.crt" "$PKI/$ID.crt" "$PKI/$ID.key"; do
    [ -r "$f" ] || { echo "[CLAVE-BRONCE] no se puede leer $f" >&2; exit 1; }
done
EP=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["etcd"]["endpoints"][0])' "$JSON") \
    || { echo "[CLAVE-BRONCE] $JSON sin etcd.endpoints[0]" >&2; exit 1; }
case "$EP" in
    https://*) ;;
    *) echo "[CLAVE-BRONCE] etcd.endpoints[0]=$EP no es https://" >&2; exit 1 ;;
esac
RESP=$(curl -sS -f --max-time 10 --cacert "$PKI/ca.crt" --cert "$PKI/$ID.crt" --key "$PKI/$ID.key" \
            "$EP/secrets/valid/ml-detector") \
    || { echo "[CLAVE-BRONCE] GET $EP/secrets/valid/ml-detector falló (¿etcd-server de la VM etcd arrancado?)" >&2; exit 1; }
printf '%s' "$RESP" | python3 -c '
import json, re, sys
d = json.load(sys.stdin)
activas = [k.get("key", "") for k in d.get("keys", []) if k.get("is_active") is True]
if len(activas) != 1:
    sys.exit("[CLAVE-BRONCE] se esperaba 1 clave activa y hay %d" % len(activas))
if not re.fullmatch(r"[0-9a-f]{64}", activas[0]):
    sys.exit("[CLAVE-BRONCE] la clave activa no son 64 hex")
print(activas[0])
'
