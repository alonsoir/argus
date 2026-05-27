#!/usr/bin/env bash
# tools/prod/deploy-hardened.sh
# Instala los binarios compilados en /opt/argus/ en la hardened VM.
# Aplica capabilities mínimas post-Consejo DAY 133 (ADR-030).
# Se ejecuta DENTRO de la hardened VM como root (sudo).
#
# Cambios post-Consejo DAY 133:
#   - sniffer: cap_sys_admin → cap_bpf (Linux ≥5.8)
#   - etcd-server: cap_net_bind_service ELIMINADA (2379 > 1024)
#   - etcd-server: cap_ipc_lock suficiente con LimitMEMLOCK=16M en systemd
#
# DEBT-KERNEL-COMPAT-001: si cap_bpf falla con XDP, documentar y revertir a cap_sys_admin.
set -euo pipefail

DIST=/vagrant/dist/x86
OPT_ARGUS=/opt/argus
ARGUS_USER=argus
ARGUS_GROUP=argus

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  aRGus NDR — Deploy to hardened-x86 (post-Consejo v133)  ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Verificar que dist/x86/ existe
if [ ! -d "${DIST}/bin" ]; then
    echo "FAIL: ${DIST}/bin no existe"
    echo "      Ejecuta: make prod-build-x86 primero"
    exit 1
fi

# Verificar SHA256SUMS
if [ -f "${DIST}/SHA256SUMS" ]; then
    echo "── Verifying SHA256SUMS ──"
    cd "${DIST}"
    sha256sum -c SHA256SUMS --quiet && echo "  ✅ SHA256SUMS OK" || \
        (echo "FAIL: SHA256SUMS mismatch — binarios comprometidos"; exit 1)
fi

# Crear estructura de directorios
echo ""
echo "── Creating /opt/argus/ structure ──"
install -d -o root -g ${ARGUS_GROUP} -m 0755 ${OPT_ARGUS}
install -d -o ${ARGUS_USER} -g ${ARGUS_GROUP} -m 0755 ${OPT_ARGUS}/bin
install -d -o root -g ${ARGUS_GROUP} -m 0755 ${OPT_ARGUS}/lib
install -d -o root -g ${ARGUS_GROUP} -m 0755 ${OPT_ARGUS}/plugins
install -d -o ${ARGUS_USER} -g ${ARGUS_GROUP} -m 0750 ${OPT_ARGUS}/models

# Instalar binarios
echo ""
echo "── Installing binaries ──"
for binary in "${DIST}/bin/"*; do
    [ -f "${binary}" ] || continue
    [[ "${binary}" == *.sig ]] && continue
    name=$(basename "${binary}")
    install -o ${ARGUS_USER} -g ${ARGUS_GROUP} -m 0550 "${binary}" "${OPT_ARGUS}/bin/${name}"
    [ -f "${binary}.sig" ] && \
        install -o ${ARGUS_USER} -g ${ARGUS_GROUP} -m 0440 "${binary}.sig" "${OPT_ARGUS}/bin/${name}.sig"
    echo "  ✅ ${name} (0550 ${ARGUS_USER}:${ARGUS_GROUP})"
done

# Instalar librerías
echo ""
echo "── Installing runtime libraries ──"
for lib in "${DIST}/lib/"*; do
    [ -f "${lib}" ] || continue
    name=$(basename "${lib}")
    install -o root -g ${ARGUS_GROUP} -m 0550 "${lib}" "${OPT_ARGUS}/lib/${name}"
    echo "  ✅ ${name}"
done
ldconfig "${OPT_ARGUS}/lib"

# Instalar plugins
echo ""
echo "── Installing plugins ──"
for plugin in "${DIST}/plugins/"*.so; do
    [ -f "${plugin}" ] || continue
    name=$(basename "${plugin}")
    install -o root -g ${ARGUS_GROUP} -m 0550 "${plugin}" "${OPT_ARGUS}/plugins/${name}"
    [ -f "${plugin}.sig" ] && \
        install -o root -g ${ARGUS_GROUP} -m 0440 "${plugin}.sig" "${OPT_ARGUS}/plugins/${name}.sig"
    echo "  ✅ ${name}"
done

# ── Linux Capabilities (post-Consejo DAY 133) ────────────────────────────────
echo ""
echo "── Setting Linux Capabilities (no SUID root) ──"
echo "   Post-Consejo: cap_bpf reemplaza cap_sys_admin en sniffer"
echo "   Post-Consejo: cap_net_bind_service eliminada de etcd-server"

# sniffer: XDP/eBPF
# cap_bpf (Linux ≥5.8) reemplaza cap_sys_admin — decisión unánime Consejo DAY 133
# DEBT-KERNEL-COMPAT-001: si falla con XDP, revertir a cap_sys_admin y documentar
KERNEL_VERSION=$(uname -r | cut -d. -f1-2 | tr -d '.')
KERNEL_MAJOR=$(uname -r | cut -d. -f1)
KERNEL_MINOR=$(uname -r | cut -d. -f2)

if [ "${KERNEL_MAJOR}" -gt 5 ] || ([ "${KERNEL_MAJOR}" -eq 5 ] && [ "${KERNEL_MINOR}" -ge 8 ]); then
    setcap cap_net_admin,cap_net_raw,cap_bpf,cap_ipc_lock+eip "${OPT_ARGUS}/bin/sniffer"
    echo "  ✅ sniffer: cap_net_admin,cap_net_raw,cap_bpf,cap_ipc_lock+eip"
    echo "     (cap_bpf — kernel $(uname -r) ≥ 5.8)"
else
    # Fallback para kernels antiguos (no debería ocurrir con Debian bookworm)
    setcap cap_net_admin,cap_net_raw,cap_sys_admin,cap_ipc_lock+eip "${OPT_ARGUS}/bin/sniffer"
    echo "  ⚠️  sniffer: cap_sys_admin usado como fallback (kernel $(uname -r) < 5.8)"
    echo "     DEBT-KERNEL-COMPAT-001: documentar y planificar upgrade de kernel"
fi

# firewall-acl-agent: iptables/ipset
setcap cap_net_admin+eip "${OPT_ARGUS}/bin/firewall-acl-agent"
echo "  ✅ firewall-acl-agent: cap_net_admin+eip"

# etcd-server: mlock() del seed
# cap_net_bind_service ELIMINADA (puerto 2379 > 1024, no necesaria)
# LimitMEMLOCK=16M en la unit systemd es suficiente para seed.bin (32 bytes)
setcap cap_ipc_lock+eip "${OPT_ARGUS}/bin/etcd-server"
echo "  ✅ etcd-server: cap_ipc_lock+eip"
echo "     (cap_net_bind_service eliminada — 2379 > 1024)"
echo "     (LimitMEMLOCK=16M en systemd unit para mlock del seed)"

# Componentes no-root reales
for comp in ml-detector rag-ingester rag-security; do
    echo "  ✅ ${comp}: sin capabilities (corre como ${ARGUS_USER}, no-root real)"
done

echo ""
echo "── Deployment summary ──"
echo "  Binaries:  $(ls ${OPT_ARGUS}/bin/ | grep -v '\.sig' | wc -l) installed"
echo "  Libraries: $(ls ${OPT_ARGUS}/lib/ | wc -l) installed"
echo "  Plugins:   $(ls ${OPT_ARGUS}/plugins/*.so 2>/dev/null | wc -l) installed"
echo ""
echo "── Capabilities summary ──"
for bin in sniffer firewall-acl-agent etcd-server ml-detector rag-ingester rag-security; do
    CAPS=$(getcap "${OPT_ARGUS}/bin/${bin}" 2>/dev/null || echo "none")
    echo "  ${bin}: ${CAPS}"
done
echo ""
echo "✅ deploy-hardened completado (post-Consejo DAY 133)"