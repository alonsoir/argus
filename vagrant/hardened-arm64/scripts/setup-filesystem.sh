#!/usr/bin/env bash
# vagrant/hardened-x86/scripts/setup-filesystem.sh
# Crea el usuario argus (no-root), la estructura de directorios y
# los permisos del filesystem para la hardened VM.
# Principio: mínimo necesario, nada más.
# Se ejecuta DENTRO de la hardened VM como root.
#
# DAY 133 — aRGus NDR — ADR-030 Variant A
set -euo pipefail

ARGUS_USER=argus
ARGUS_GROUP=argus

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  aRGus NDR — Filesystem setup (hardened-x86)             ║"
echo "║  Usuario: argus (no-root, nologin)                       ║"
echo "╚════════════════════════════════════════════════════════════╝"

# ── Usuario del sistema ───────────────────────────────────────────────────────
echo ""
echo "── Creating argus system user ──"
if id "${ARGUS_USER}" &>/dev/null; then
    echo "  ✅ usuario ${ARGUS_USER} ya existe"
else
    useradd \
        --system \
        --no-create-home \
        --shell /usr/sbin/nologin \
        --comment "aRGus NDR pipeline user" \
        "${ARGUS_USER}"
    echo "  ✅ usuario ${ARGUS_USER} creado (nologin, no home)"
fi

# ── /opt/argus/ — binarios y librerías ───────────────────────────────────────
echo ""
echo "── /opt/argus/ ──"
install -d -o root        -g "${ARGUS_GROUP}" -m 0755 /opt/argus
install -d -o "${ARGUS_USER}" -g "${ARGUS_GROUP}" -m 0750 /opt/argus/bin
install -d -o root        -g "${ARGUS_GROUP}" -m 0755 /opt/argus/lib
install -d -o root        -g "${ARGUS_GROUP}" -m 0755 /opt/argus/plugins
install -d -o "${ARGUS_USER}" -g "${ARGUS_GROUP}" -m 0750 /opt/argus/models

# ── /etc/ml-defender/ — configuración y seeds ────────────────────────────────
echo ""
echo "── /etc/ml-defender/ ──"
install -d -o root        -g "${ARGUS_GROUP}" -m 0750 /etc/ml-defender
install -d -o root        -g "${ARGUS_GROUP}" -m 0750 /etc/ml-defender/plugins

for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do
    install -d -o "${ARGUS_USER}" -g "${ARGUS_GROUP}" -m 0750 /etc/ml-defender/${comp}
    echo "  ✅ /etc/ml-defender/${comp}/ (750 ${ARGUS_USER}:${ARGUS_GROUP})"
done

# ── /var/log/argus/ — logs por componente ────────────────────────────────────
echo ""
echo "── /var/log/argus/ ──"
install -d -o root        -g "${ARGUS_GROUP}" -m 0750 /var/log/argus

for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do
    install -d -o "${ARGUS_USER}" -g "${ARGUS_GROUP}" -m 0750 /var/log/argus/${comp}
    echo "  ✅ /var/log/argus/${comp}/ (750 ${ARGUS_USER}:${ARGUS_GROUP})"
done

# ── /tmp y /var/tmp — noexec, nosuid, nodev ──────────────────────────────────
echo ""
echo "── /tmp noexec ──"
if ! grep -q "^tmpfs /tmp" /etc/fstab; then
    echo "tmpfs /tmp     tmpfs defaults,noexec,nosuid,nodev,size=128M 0 0" >> /etc/fstab
    mount -o remount /tmp 2>/dev/null || mount tmpfs /tmp -t tmpfs -o noexec,nosuid,nodev,size=128M
    echo "  ✅ /tmp: tmpfs noexec,nosuid,nodev"
else
    echo "  ✅ /tmp: ya configurado"
fi

if ! grep -q "/var/tmp" /etc/fstab; then
    echo "tmpfs /var/tmp tmpfs defaults,noexec,nosuid,nodev,size=64M  0 0" >> /etc/fstab
    mount -o remount /var/tmp 2>/dev/null || mount tmpfs /var/tmp -t tmpfs -o noexec,nosuid,nodev,size=64M
    echo "  ✅ /var/tmp: tmpfs noexec,nosuid,nodev"
else
    echo "  ✅ /var/tmp: ya configurado"
fi

# ── Verificación final ────────────────────────────────────────────────────────
echo ""
echo "── Verification ──"
id "${ARGUS_USER}" && echo "  ✅ user ok"
ls -la /opt/argus/ && echo "  ✅ /opt/argus/ ok"
ls -la /etc/ml-defender/ && echo "  ✅ /etc/ml-defender/ ok"
ls -la /var/log/argus/ && echo "  ✅ /var/log/argus/ ok"

echo ""
echo "✅ setup-filesystem completado"