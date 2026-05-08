#!/usr/bin/env bash
# scripts/check-sniffer-mutex.sh
# DEBT-VARIANT-B-MUTEX-001 — DAY 142
# Exclusion mutua via tmux sessions — la logica NO entra en los binarios.
# Variant A session: "sniffer" | Variant B session: "sniffer-libpcap"
#
# USO: bash scripts/check-sniffer-mutex.sh <variant>
#      variant: "ebpf" | "libpcap"
# EXIT: 0=OK arrancar, 1=bloqueado

set -euo pipefail

VARIANT="${1:-unknown}"

echo "=== [sniffer-mutex] Verificando exclusion mutua (variant=${VARIANT}) ==="

A_ACTIVE=0
B_ACTIVE=0
tmux has-session -t sniffer 2>/dev/null && A_ACTIVE=1 || true
tmux has-session -t sniffer-libpcap 2>/dev/null && B_ACTIVE=1 || true

echo "[sniffer-mutex] Variant A (ebpf/tmux:sniffer):         $([ $A_ACTIVE -eq 1 ] && echo ACTIVE || echo inactive)"
echo "[sniffer-mutex] Variant B (libpcap/tmux:sniffer-libpcap): $([ $B_ACTIVE -eq 1 ] && echo ACTIVE || echo inactive)"

if [[ "$VARIANT" == "ebpf" && $B_ACTIVE -eq 1 ]]; then
    echo ""
    echo "======================================================"
    echo "[sniffer-mutex] ERROR: EXCLUSION MUTUA VIOLADA"
    echo "  Solicitada: Variant A (ebpf)"
    echo "  Activa:     Variant B (libpcap) — tmux:sniffer-libpcap"
    echo "======================================================"
    echo "[sniffer-mutex] Deteniendo Variant B..."
    tmux kill-session -t sniffer-libpcap 2>/dev/null || true
    echo "[sniffer-mutex] EXIT 1 — arranque bloqueado hasta confirmar parada"
    exit 1
fi

if [[ "$VARIANT" == "libpcap" && $A_ACTIVE -eq 1 ]]; then
    echo ""
    echo "======================================================"
    echo "[sniffer-mutex] ERROR: EXCLUSION MUTUA VIOLADA"
    echo "  Solicitada: Variant B (libpcap)"
    echo "  Activa:     Variant A (ebpf) — tmux:sniffer"
    echo "======================================================"
    echo "[sniffer-mutex] Deteniendo Variant A..."
    tmux kill-session -t sniffer 2>/dev/null || true
    echo "[sniffer-mutex] EXIT 1 — arranque bloqueado hasta confirmar parada"
    exit 1
fi

echo "[sniffer-mutex] OK — puede arrancar variant=${VARIANT}"
exit 0
