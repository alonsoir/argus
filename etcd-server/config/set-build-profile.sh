#!/bin/bash
# set-build-profile.sh
# Activa un perfil de build creando symlinks build-active → build-{profile}
# [BUILD-PROFILE-D296] perfiles = los del Makefile raiz (PROFILE ?= debug): debug | production | tsan | asan
# Uso: sudo bash set-build-profile.sh debug | production | tsan | asan
# Desde Mac: vagrant ssh -c "sudo bash /vagrant/etcd-server/config/set-build-profile.sh debug"

set -euo pipefail
set -o noclobber          # REC-2: prevenir truncado accidental con >

PROFILE="${1:-}"
case "$PROFILE" in  # [BUILD-PROFILE-D296]
    debug|production|tsan|asan) ;;
    *) echo "Uso: $0 debug | production | tsan | asan  (recibido: '${PROFILE}')"; exit 1 ;;
esac

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