#!/usr/bin/env bash
# =============================================================================
# provision_crypto.sh — ADR-044 Vault Crypto Pipeline
# Genera y almacena seeds criptográficos por familia en HashiCorp Vault.
#
# USO:
#   provision_crypto.sh [--env dev|prod] [--force] [--audit-out PATH]
#
# PATHS Vault:
#   argus/{env}/families/family_{A,B,C}/seed   (componentes por familia)
#   argus/{env}/components/etcd/seed           (bootstrap especial)
#
# DECISIONES CONSEJO DAY 149:
#   Q4: backend file suficiente para dev/FEDER
#   Q5: rotación MANUAL orquestada
#   Q7: paths por familia argus/{env}/families/family_{A,B,C}/seed
#   D12 (Kimi): kdf_derive -> component_seed -> sign_seed_keypair
#   D13 (Kimi): fingerprint = sha256(pk), NO de seed
# =============================================================================
set -euo pipefail

ENV="${ARGUS_ENV:-dev}"
FORCE=0
AUDIT_OUT="/vagrant/logs/crypto_audit.json"
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"
SEED_BYTES=32
FAMILIES=(A B C)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[provision_crypto]${NC} $*" >&2; }
warn()  { echo -e "${YELLOW}[provision_crypto] WARN${NC} $*" >&2; }
error() { echo -e "${RED}[provision_crypto] ERROR${NC} $*" >&2; }

while [[ $# -gt 0 ]]; do
  case $1 in
    --env)        ENV="$2";       shift 2 ;;
    --force)      FORCE=1;        shift   ;;
    --audit-out)  AUDIT_OUT="$2"; shift 2 ;;
    *) error "Argumento desconocido: $1"; exit 1 ;;
  esac
done

[[ "$ENV" == "dev" || "$ENV" == "prod" ]] || \
  { error "--env debe ser 'dev' o 'prod'"; exit 1; }

export VAULT_ADDR VAULT_TOKEN

vault_running() {
  curl -sf "${VAULT_ADDR}/v1/sys/health" \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    --max-time 5 > /dev/null 2>&1
}

start_vault_dev() {
  info "Arrancando Vault en modo dev..."
  mkdir -p /vagrant/logs
  nohup vault server \
    -dev \
    -dev-root-token-id="${VAULT_TOKEN}" \
    -dev-listen-address="127.0.0.1:8200" \
    > /vagrant/logs/vault-dev.log 2>&1 &
  local VAULT_PID=$!
  info "Vault PID: ${VAULT_PID}"
  for i in $(seq 1 20); do
    sleep 0.5
    vault_running && { info "Vault listo (${i} intentos)"; return 0; }
  done
  error "Vault no respondio tras 10s"
  exit 1
}

if ! vault_running; then
  start_vault_dev
fi

if ! vault secrets list 2>/dev/null | grep -q "^argus/"; then
  info "Habilitando KV v1 en argus/..."
  vault secrets enable -path=argus kv
fi

generate_seed() {
  od -A n -t x1 -N "${SEED_BYTES}" /dev/urandom | tr -d ' \n'
}

write_seed() {
  local path="$1"
  local full_path="argus/${ENV}/${path}"
  local existing
  existing=$(vault kv get -field=value "${full_path}" 2>/dev/null || echo "")
  if [[ -n "$existing" && "$FORCE" -eq 0 ]]; then
    info "SKIP: ${full_path} ya existe (--force para regenerar)"
    echo "$existing"; return 0
  fi
  local seed
  seed=$(generate_seed)
  vault kv put "${full_path}" \
    value="${seed}" env="${ENV}" \
    created_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /dev/null
  info "WRITE: ${full_path}"
  echo "$seed"
}

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  aRGus NDR — Provision Crypto (ADR-044)                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

declare -A SEEDS

for FAM in "${FAMILIES[@]}"; do
  SEED=$(write_seed "families/family_${FAM}/seed")
  SEEDS["family_${FAM}"]="$SEED"
  info "family_${FAM}: ${SEED:0:16}..."
done

ETCD_SEED=$(write_seed "components/etcd/seed")
SEEDS["etcd"]="$ETCD_SEED"
info "etcd (bootstrap): ${ETCD_SEED:0:16}..."

if [[ "$ENV" == "prod" ]]; then
  info "Verificando seed_dev != seed_prod..."
  for FAM in "${FAMILIES[@]}"; do
    DEV_SEED=$(vault kv get -field=value \
      "argus/dev/families/family_${FAM}/seed" 2>/dev/null || echo "")
    PROD_SEED="${SEEDS["family_${FAM}"]}"
    if [[ -n "$DEV_SEED" && "$DEV_SEED" == "$PROD_SEED" ]]; then
      error "ABORT: family_${FAM} seed_dev == seed_prod"
      exit 1
    fi
  done
  info "Assert seed_dev != seed_prod: OK"
fi

mkdir -p "$(dirname "${AUDIT_OUT}")"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
AUDIT_JSON="{\"version\":\"1.0\",\"env\":\"${ENV}\",\"timestamp\":\"${TIMESTAMP}\","
AUDIT_JSON+="\"vault_addr\":\"${VAULT_ADDR}\",\"forced\":${FORCE},\"families\":{"
FIRST=1
for FAM in "${FAMILIES[@]}"; do
  [[ $FIRST -eq 0 ]] && AUDIT_JSON+=","
  SEED="${SEEDS["family_${FAM}"]}"
  FP=$(echo -n "$SEED" | sha256sum | cut -d' ' -f1)
  AUDIT_JSON+="\"family_${FAM}\":{\"path\":\"argus/${ENV}/families/family_${FAM}/seed\","
  AUDIT_JSON+="\"fingerprint\":\"${FP}\"}"
  FIRST=0
done
ETCD_FP=$(echo -n "$ETCD_SEED" | sha256sum | cut -d' ' -f1)
AUDIT_JSON+="},\"etcd\":{\"path\":\"argus/${ENV}/components/etcd/seed\","
AUDIT_JSON+="\"fingerprint\":\"${ETCD_FP}\",\"bootstrap_special\":true}}"
echo "$AUDIT_JSON" > "${AUDIT_OUT}"
info "Artifact: ${AUDIT_OUT}"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ provision_crypto COMPLETADO — ENV: ${ENV}             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
