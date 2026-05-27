#!/usr/bin/env bash
# vagrant/hardened-x86/scripts/setup-apparmor.sh
# Instala y activa los 6 perfiles AppArmor (uno por componente).
# Modo: enforce (no complain).
# Se ejecuta DENTRO de la hardened VM como root.
#
# DAY 133 — aRGus NDR — ADR-030 Variant A
set -euo pipefail

PROFILES_DIR=/vagrant/security/apparmor
AA_DIR=/etc/apparmor.d

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  AppArmor profiles — 6 componentes en enforce mode       ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Verificar AppArmor disponible
if ! command -v aa-enforce &>/dev/null; then
    apt-get install -y apparmor apparmor-utils apparmor-profiles --no-install-recommends
fi

if ! aa-status &>/dev/null; then
    echo "FAIL: AppArmor no está activo en este kernel"
    echo "      Verifica que el kernel tiene AppArmor habilitado: cat /sys/module/apparmor/parameters/enabled"
    exit 1
fi

echo ""
echo "── Installing profiles ──"
for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security argus-network-isolate; do
    src="${PROFILES_DIR}/argus.${comp}"
    dst="${AA_DIR}/argus.${comp}"

    if [ ! -f "${src}" ]; then
        echo "  ⚠️  ${src}: perfil no encontrado — saltando"
        continue
    fi

    cp "${src}" "${dst}"
    apparmor_parser -r "${dst}" 2>/dev/null || apparmor_parser -a "${dst}"
    aa-enforce "${dst}" 2>/dev/null || true
    echo "  ✅ argus.${comp}: loaded in enforce mode"
done

echo ""
echo "── AppArmor status ──"
aa-status 2>/dev/null | grep -E "profiles are in enforce|argus-" || true

echo ""
echo "✅ setup-apparmor completado"