#!/usr/bin/env bash
# vagrant/hardened-x86/scripts/setup-apt-integrity.sh
# DEBT-PROD-APT-SOURCES-INTEGRITY-001 — Decisión Mistral D7 (DAY 134)
#
# Captura SHA-256 de apt sources al momento del provisioning.
# Systemd oneshot verifica en cada boot — fail-closed si cambia.
# AppArmor + Falco cubren la capa de prevención y detección.
set -euo pipefail

INTEGRITY_DIR="/etc/argus-integrity"
CHECKSUMS_FILE="${INTEGRITY_DIR}/apt-sources.sha256"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  APT Sources Integrity (DEBT-PROD-APT-SOURCES-001)       ║"
echo "║  Decisión Mistral D7 — DAY 134                           ║"
echo "╚════════════════════════════════════════════════════════════╝"

# ── 1. Crear directorio de integridad ─────────────────────────────────────────
mkdir -p "${INTEGRITY_DIR}"
chmod 750 "${INTEGRITY_DIR}"
chown root:root "${INTEGRITY_DIR}"

# ── 2. Capturar SHA-256 de apt sources ───────────────────────────────────────
echo "── Capturando SHA-256 de apt sources ──"
{
    [ -f /etc/apt/sources.list ] && sha256sum /etc/apt/sources.list
    find /etc/apt/sources.list.d/ -name "*.list" -o -name "*.sources" 2>/dev/null | \
        sort | xargs -r sha256sum
} > "${CHECKSUMS_FILE}"
chmod 640 "${CHECKSUMS_FILE}"
chown root:root "${CHECKSUMS_FILE}"
echo "  ✅ ${CHECKSUMS_FILE}: $(wc -l < ${CHECKSUMS_FILE}) entradas"
cat "${CHECKSUMS_FILE}" | sed 's/^/    /'

# ── 3. Instalar script de verificación ───────────────────────────────────────
cat > /usr/local/bin/argus-apt-integrity-check << 'CHECK_EOF'
#!/usr/bin/env bash
# Verificación de integridad de apt sources — ejecutado por systemd en boot
set -euo pipefail

INTEGRITY_DIR="/etc/argus-integrity"
CHECKSUMS_FILE="${INTEGRITY_DIR}/apt-sources.sha256"
LOG_TAG="argus-apt-integrity"

if [ ! -f "${CHECKSUMS_FILE}" ]; then
    logger -t "${LOG_TAG}" -p security.crit "FAIL: ${CHECKSUMS_FILE} no existe — sistema comprometido"
    exit 1
fi

# Verificar cada entrada del CHECKSUMS
FAILED=0
while IFS= read -r line; do
    EXPECTED_HASH=$(echo "${line}" | cut -d' ' -f1)
    FILE=$(echo "${line}" | cut -d' ' -f3)
    if [ ! -f "${FILE}" ]; then
        logger -t "${LOG_TAG}" -p security.crit "FAIL: ${FILE} desapareció"
        FAILED=1
        continue
    fi
    ACTUAL_HASH=$(sha256sum "${FILE}" | cut -d' ' -f1)
    if [ "${ACTUAL_HASH}" != "${EXPECTED_HASH}" ]; then
        logger -t "${LOG_TAG}" -p security.crit "FAIL: ${FILE} modificado (esperado=${EXPECTED_HASH} actual=${ACTUAL_HASH})"
        FAILED=1
    fi
done < "${CHECKSUMS_FILE}"

if [ "${FAILED}" -eq 1 ]; then
    logger -t "${LOG_TAG}" -p security.crit "APT SOURCES INTEGRITY VIOLATION — fail-closed"
    exit 1
fi

logger -t "${LOG_TAG}" -p security.info "OK: apt sources íntegros"
exit 0
CHECK_EOF
chmod 750 /usr/local/bin/argus-apt-integrity-check
chown root:root /usr/local/bin/argus-apt-integrity-check
echo "  ✅ /usr/local/bin/argus-apt-integrity-check instalado"

# ── 4. Instalar systemd unit (oneshot en boot) ───────────────────────────────
cat > /etc/systemd/system/argus-apt-integrity.service << 'UNIT_EOF'
[Unit]
Description=aRGus APT Sources Integrity Check (ADR-030 / DEBT-PROD-APT-001)
Documentation=https://github.com/alonsoir/argus
DefaultDependencies=no
Before=network.target
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/argus-apt-integrity-check
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

# Fail-closed REAL (Decisión Alonso DAY 135):
# Un nodo con apt sources comprometidos NO puede arrancar — riesgo de infección
# a toda la red aRGus via ZeroMQ/etcd. Reboot tras 30s para que los logs
# lleguen a la central antes de apagar.
# Los logs en journald persisten y son consultables post-reboot.
# POWEROFF INMEDIATO — Voto de Oro Alonso DAY 135.
#
# Filosofía: un nodo con apt sources comprometidos es material radiactivo.
# No se reanima. Se aisla, se analiza en autopsia, se restaura desde cero.
#
# Razones:
#   1. Reboot da tiempo al atacante para persistir, evadir, contaminar.
#   2. La red aRGus puede tener miles/millones de nodos. Un nodo infectado
#      que vuelve a la red via ZeroMQ/etcd puede fundir la flota entera.
#   3. El análisis forense (journald en disco) queda intacto con poweroff.
#      Con reboot, el atacante tiene ciclos para destruir evidencia.
#   4. Un humano DEBE intervenir físicamente o via consola de gestión
#      (IPMI, iDRAC) para restaurar. No hay vuelta atrás automática.
#
# Flujo post-poweroff:
#   → Admin accede via consola física o IPMI (sin red)
#   → Autopsia: journalctl, /etc/argus-integrity/, /var/log/
#   → Restauración desde imagen limpia conocida y firmada
#   → Re-provisioning completo: make hardened-full
#
# Si en el futuro los admins consideran esta política demasiado restrictiva,
# pueden modificarla con pleno conocimiento del riesgo que asumen.
# Pero el default es y debe ser: POWEROFF INMEDIATO. Sin excepciones.
# Sin configuración externa. Hardcoded. Inmutable sin acceso físico.
#
# "Mientras más tiempo esté expuesto a la red, más tiempo ha tenido
#  el atacante para colocar sus mierdas y hacer daño." — Alonso, DAY 135
FailureAction=poweroff
# Anti-bootloop: si falla 2 veces en 5 min, systemd no reintenta
StartLimitIntervalSec=300
StartLimitBurst=2

[Install]
WantedBy=multi-user.target
UNIT_EOF

systemctl daemon-reload
systemctl enable argus-apt-integrity.service
echo "  ✅ argus-apt-integrity.service habilitado (oneshot en boot)"

# ── 5. Verificación inmediata ─────────────────────────────────────────────────
echo ""
echo "── Verificación inmediata ──"
if /usr/local/bin/argus-apt-integrity-check; then
    echo "  ✅ apt sources íntegros (verificación post-instalación OK)"
else
    echo "  ❌ FAIL: verificación falló — revisar ${CHECKSUMS_FILE}"
    exit 1
fi

echo ""
echo "✅ setup-apt-integrity completado (DEBT-PROD-APT-SOURCES-INTEGRITY-001)"
