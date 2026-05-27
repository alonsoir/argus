#!/bin/bash
# set-build-profile.sh
# Activa perfil debug o release creando symlinks build-active → build-{profile}
# Uso: sudo bash set-build-profile.sh debug | release
# Desde Mac: vagrant ssh -c "sudo bash /vagrant/etcd-server/config/set-build-profile.sh debug"

set -euo pipefail
set -o noclobber          # REC-2: prevenir truncado accidental con >

PROFILE="${1:-}"
if [[ "$PROFILE" != "debug" && "$PROFILE" != "release" ]]; then
    echo "Uso: $0 debug | release"
    exit 1
fi

COMPONENTS=(
    "/vagrant/etcd-server"
    "/vagrant/rag"
    "/vagrant/rag-ingester"
    "/vagrant/ml-detector"
    "/vagrant/sniffer"
    "/vagrant/firewall-acl-agent"
)

echo "═══ Activando perfil: $PROFILE ═══"

for comp in "${COMPONENTS[@]}"; do
    target="${comp}/build-${PROFILE}"
    link="${comp}/build-active"

    if [[ ! -d "$target" ]]; then
        echo "  ⚠️  No existe ${target} — saltando"
        continue
    fi

    ln -sfn "$target" "$link"
    echo "  ✅ $(basename $comp): build-active → build-${PROFILE}"
done

# Guardar perfil activo
mkdir -p /etc/ml-defender
echo "ML_DEFENDER_BUILD=build-${PROFILE}" >| /etc/ml-defender/build.env
echo "ML_DEFENDER_PROFILE=${PROFILE}" >> /etc/ml-defender/build.env

echo ""
echo "  Perfil activo guardado en /etc/ml-defender/build.env"
echo "  Recarga units: sudo systemctl daemon-reload"
echo "═══ Listo ═══"