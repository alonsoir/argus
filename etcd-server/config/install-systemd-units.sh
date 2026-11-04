#!/bin/bash
# install-systemd-units.sh
# Instala los 4 units systemd de ML Defender (PHASE 3)
# Ejecutar DENTRO de la VM: sudo bash /vagrant/etcd-server/config/install-systemd-units.sh
# O desde Mac: vagrant ssh -c "sudo bash /vagrant/etcd-server/config/install-systemd-units.sh"

set -euo pipefail
set -o noclobber          # REC-2: prevenir truncado accidental con >

UNITS_DIR="/vagrant/etcd-server/config"
SYSTEMD_DIR="/etc/systemd/system"

# [ETCD-VM-D317] el etcd-server ya no corre en el defender: vive en la VM etcd (ml-defender-etcd-server.service del
# Vagrantfile, [ETCD-SERVER-UNIT-D317]). Aquí, los tres componentes (TEST-PROVISION-1 comprobación 5 espera 3).
UNITS=(
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

# [ETCD-VM-D317] retira la unidad vieja del etcd-server del defender (solo si es la del defender: ExecStart en
# /vagrant/etcd-server/build-active; la de la VM etcd, con el mismo nombre, no se toca nunca)
OBSOLETA="${SYSTEMD_DIR}/ml-defender-etcd-server.service"
if [[ -f "$OBSOLETA" ]] && grep -q "^ExecStart=/vagrant/etcd-server/build-active/etcd-server" "$OBSOLETA"; then
    systemctl disable --now ml-defender-etcd-server.service > /dev/null 2>&1 || true
    rm -f "$OBSOLETA"
    echo "  🗑️  Retirada: $OBSOLETA (el etcd-server vive en la VM etcd)"
fi

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