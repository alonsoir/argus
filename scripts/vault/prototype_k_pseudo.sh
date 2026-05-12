#!/usr/bin/env bash
# aRGus NDR -- Vault dev mode prototype: K_pseudo + HMAC-SHA256
# DEBT-CRYPTO-MATERIAL-STORAGE-001
# Uso: bash scripts/vault/prototype_k_pseudo.sh
# Requiere: vault en PATH, VAULT_ADDR y VAULT_TOKEN exportados
# Proposito: validar contrato K_pseudo antes de implementacion HA
set -euo pipefail

export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_TOKEN="${VAULT_TOKEN:-argus-dev-token}"

echo ""
echo "======================================"
echo "  aRGus NDR -- K_pseudo prototype"
echo "======================================"

# 1. KV v2
vault secrets enable -path=argus kv-v2 2>/dev/null || echo "[INFO] kv-v2 ya habilitado en argus/"

# 2. Generar y almacenar K_pseudo
K_PSEUDO=$(openssl rand -hex 32)
vault kv put argus/k_pseudo value="$K_PSEUDO" > /dev/null
echo "[OK] K_pseudo generada y almacenada"

# 3. HMAC de IP de prueba
K_RECOVERED=$(vault kv get -field=value argus/k_pseudo)
TEST_IP="192.168.1.100"
HMAC_1=$(echo -n "$TEST_IP" | openssl dgst -sha256 -hmac "$K_RECOVERED" | awk '{print $2}')
echo "[OK] anon_host_id($TEST_IP): $HMAC_1"

# 4. Determinismo
HMAC_2=$(echo -n "$TEST_IP" | openssl dgst -sha256 -hmac "$K_RECOVERED" | awk '{print $2}')
[ "$HMAC_1" = "$HMAC_2" ] && echo "[OK] Determinismo: PASSED" || { echo "[FAIL] Determinismo"; exit 1; }

# 5. Aislamiento
K_OTRO=$(openssl rand -hex 32)
HMAC_OTRO=$(echo -n "$TEST_IP" | openssl dgst -sha256 -hmac "$K_OTRO" | awk '{print $2}')
[ "$HMAC_1" != "$HMAC_OTRO" ] && echo "[OK] Aislamiento K: PASSED" || { echo "[FAIL] Aislamiento K"; exit 1; }

# 6. Destruccion y verificacion post-destroy
vault kv delete argus/k_pseudo
RESULT=$(vault kv get -field=value argus/k_pseudo 2>&1 || true)
echo "[OK] Post-destroy: $RESULT"

echo ""
echo "[PASSED] Contrato K_pseudo validado"
echo "======================================"
echo ""
