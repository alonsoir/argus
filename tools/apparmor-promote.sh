#!/usr/bin/env bash
# =============================================================================
# tools/apparmor-promote.sh
# ML Defender — AppArmor complain → enforce con rollback automático
#
# USO:
#   sudo bash tools/apparmor-promote.sh <componente>
#
# COMPONENTES VÁLIDOS:
#   etcd-server | ml-detector |
#   firewall-acl-agent | sniffer
#
# COMPORTAMIENTO:
#   1. Verifica que el perfil existe y está en complain
#   2. Promueve a enforce (aa-enforce)
#   3. Monitorea journalctl 5 minutos buscando denials AppArmor
#   4. Si hay denials → rollback automático a complain + log
#   5. Si 0 denials → confirma enforce + log auditado
#
# Authors: Alonso Isidoro Roman + Claude (Anthropic)
# DAY 117 — 14 Abril 2026
# =============================================================================
set -euo pipefail
set -o noclobber

COMPONENT="${1:-}"
MONITOR_SECONDS=300
LOG_DIR="/var/log/ml-defender/apparmor"
AUDIT_LOG="${LOG_DIR}/promote-audit.log"

# Mapa componente → path binario (nombre del perfil AppArmor)
get_profile_path() {
    case "$1" in
        etcd-server)      echo "/vagrant/etcd-server/build-active/etcd-server" ;;
        ml-detector)      echo "/vagrant/ml-detector/build-active/ml-detector" ;;
        firewall-acl-agent) echo "/vagrant/firewall-acl-agent/build-active/firewall_acl_agent" ;;
        sniffer)          echo "/vagrant/sniffer/build-active/sniffer" ;;
        *)                echo "" ;;
    esac
}

get_profile_file() {
    case "$1" in
        etcd-server)      echo "ml-defender-etcd-server" ;;
        ml-detector)      echo "ml-defender-ml-detector" ;;
        firewall-acl-agent) echo "ml-defender-firewall-acl-agent" ;;
        sniffer)          echo "ml-defender-sniffer" ;;
        *)                echo "" ;;
    esac
}

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$AUDIT_LOG"; }

usage() {
    echo "USO: sudo bash tools/apparmor-promote.sh <componente>"
    echo "COMPONENTES: ${!PROFILE_MAP[*]}"
    exit 1
}

# Validaciones
[ -z "$COMPONENT" ] && usage
PROFILE_PATH=$(get_profile_path "$COMPONENT")
[ -z "$PROFILE_PATH" ] && { echo "❌ Componente desconocido: $COMPONENT"; usage; }
[ "$(id -u)" -ne 0 ] && { echo "❌ Requiere sudo"; exit 1; }

# PROFILE_PATH already set above
PROFILE_FILE="/etc/apparmor.d/$(get_profile_file "$COMPONENT")"

mkdir -p "$LOG_DIR"

log "═══════════════════════════════════════════════"
log "  PROMOTE: $COMPONENT → enforce"
log "  Perfil:  $PROFILE_PATH"
log "═══════════════════════════════════════════════"

# 1. Verificar que el perfil está cargado
if ! aa-status 2>/dev/null | grep -q "$(basename "$PROFILE_PATH")"; then
    log "⚠️  Perfil no cargado — cargando ahora..."
    apparmor_parser -r "$PROFILE_FILE"
fi

# 2. Verificar que está en complain (no enforce ya)
# aa-status lista perfiles bajo cada sección — extraemos solo la sección enforce
IN_ENFORCE=$(aa-status 2>/dev/null | awk -v p="$PROFILE_PATH" '/profiles are in enforce mode/{found=1; next} /profiles are in/{found=0} found && index($0,p){print}')
if [ -n "$IN_ENFORCE" ]; then
    log "ℹ️  $COMPONENT ya está en enforce mode — sin cambios"
    exit 0
fi

# 3. Promover a enforce
log "🔒 Promoviendo $COMPONENT a enforce..."
aa-enforce "$PROFILE_FILE"
log "✅ $COMPONENT → enforce activado"

# 4. Monitorear 5 minutos
log "👁️  Monitoreando denials durante ${MONITOR_SECONDS}s..."
DENIAL_COUNT=0
START=$(date +%s)

while true; do
    NOW=$(date +%s)
    ELAPSED=$(( NOW - START ))
    [ "$ELAPSED" -ge "$MONITOR_SECONDS" ] && break

    # Buscar denials en los últimos 10 segundos
    DENIALS=$(journalctl -k --since "-10s" 2>/dev/null | \
        grep -c "apparmor.*DENIED.*${COMPONENT}\|apparmor.*DENIED.*$(basename "$PROFILE_PATH")" || true)

    if [ "$DENIALS" -gt 0 ]; then
        DENIAL_COUNT=$(( DENIAL_COUNT + DENIALS ))
        log "⚠️  Denial detectado ($DENIAL_COUNT total) — comprobando..."
    fi

    sleep 10
done

# 5. Resultado
if [ "$DENIAL_COUNT" -gt 0 ]; then
    log "❌ ROLLBACK: $DENIAL_COUNT denials detectados — volviendo a complain"
    aa-complain "$PROFILE_FILE"
    log "✅ Rollback completado — $COMPONENT en complain"
    exit 1
else
    log "✅ ENFORCE CONFIRMADO: $COMPONENT — 0 denials en ${MONITOR_SECONDS}s"
    log "  Estado final: enforce"
    exit 0
fi
