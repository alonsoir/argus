#!/bin/bash
# install-systemd-units.sh
# Instala los 6 units systemd de ML Defender (PHASE 3)
# Ejecutar DENTRO de la VM: sudo bash /vagrant/etcd-server/config/install-systemd-units.sh
# O desde Mac: vagrant ssh -c "sudo bash /vagrant/etcd-server/config/install-systemd-units.sh"

set -euo pipefail
set -o noclobber          # REC-2: prevenir truncado accidental con >

UNITS_DIR="/vagrant/etcd-server/config"
SYSTEMD_DIR="/etc/systemd/system"

UNITS=(
    ml-defender-etcd-server.service
    ml-defender-rag-security.service
    ml-defender-rag-ingester.service
    ml-defender-ml-detector.service
    ml-defender-sniffer.service
    ml-defender-firewall-acl-agent.service
)

echo "═══ Instalando systemd units ML Defender (PHASE 3) ═══"

for unit in "${UNITS[@]}"; do
    src="${UNITS_DIR}/${unit}"
    dst="${SYSTEMD_DIR}/${unit}"
    if [[ ! -f "$src" ]]; then
        echo "  ❌ No encontrado: $src"
        exit 1
    fi
    install -m 0644 "$src" "$dst"
    echo "  ✅ Instalado: $dst"
done

echo ""
echo "⏳ Recargando systemd daemon..."
systemctl daemon-reload

echo ""
echo "⚠️  Units instalados pero NO habilitados ni iniciados."
echo "   Para habilitar en arranque:"
for unit in "${UNITS[@]}"; do
    echo "     systemctl enable $unit"
done
echo ""
echo "   Para verificar:"
echo "     systemctl status ml-defender-*.service"
echo ""
echo "═══ Instalación completada ═══"