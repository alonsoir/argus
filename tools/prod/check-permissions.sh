#!/usr/bin/env bash
# tools/prod/check-permissions.sh
# Verifica que los permisos del filesystem son correctos en la hardened VM.
# Principio: mínimo necesario, nada más.
# Se ejecuta DENTRO de la hardened VM.
#
# DAY 133 — aRGus NDR — ADR-030 Variant A
set -euo pipefail

FAIL=0
ARGUS_USER=argus
ARGUS_GROUP=argus

check_dir() {
    local path=$1
    local expected_mode=$2
    local expected_owner=$3
    local expected_group=$4

    if [ ! -d "${path}" ]; then
        echo "  FAIL: ${path} no existe"
        FAIL=1
        return
    fi

    local actual_mode actual_owner actual_group
    actual_mode=$(stat -c "%a" "${path}")
    actual_owner=$(stat -c "%U" "${path}")
    actual_group=$(stat -c "%G" "${path}")

    if [ "${actual_mode}" = "${expected_mode}" ] && \
       [ "${actual_owner}" = "${expected_owner}" ] && \
       [ "${actual_group}" = "${expected_group}" ]; then
        echo "  ✅ ${path} (${actual_mode} ${actual_owner}:${actual_group})"
    else
        echo "  FAIL: ${path}"
        echo "        expected: ${expected_mode} ${expected_owner}:${expected_group}"
        echo "        actual:   ${actual_mode} ${actual_owner}:${actual_group}"
        FAIL=1
    fi
}

check_file() {
    local path=$1
    local expected_mode=$2
    local expected_owner=$3
    local expected_group=$4

    if [ ! -f "${path}" ]; then
        echo "  WARN: ${path} no existe (puede ser normal si aún no se ha provisionado)"
        return
    fi

    local actual_mode actual_owner actual_group
    actual_mode=$(stat -c "%a" "${path}")
    actual_owner=$(stat -c "%U" "${path}")
    actual_group=$(stat -c "%G" "${path}")

    if [ "${actual_mode}" = "${expected_mode}" ] && \
       [ "${actual_owner}" = "${expected_owner}" ] && \
       [ "${actual_group}" = "${expected_group}" ]; then
        echo "  ✅ ${path} (${actual_mode} ${actual_owner}:${actual_group})"
    else
        echo "  FAIL: ${path}"
        echo "        expected: ${expected_mode} ${expected_owner}:${expected_group}"
        echo "        actual:   ${actual_mode} ${actual_owner}:${actual_group}"
        FAIL=1
    fi
}

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Filesystem permissions audit (ADR-030 Variant A)        ║"
echo "╚════════════════════════════════════════════════════════════╝"

echo ""
echo "── /opt/argus/ ──"
check_dir "/opt/argus"              "755" "root"        "${ARGUS_GROUP}"
check_dir "/opt/argus/bin"          "755" "${ARGUS_USER}" "${ARGUS_GROUP}"
check_dir "/opt/argus/lib"          "755" "root"        "${ARGUS_GROUP}"
check_dir "/opt/argus/plugins"      "755" "root"        "${ARGUS_GROUP}"
check_dir "/opt/argus/models"       "750" "${ARGUS_USER}" "${ARGUS_GROUP}"

echo ""
echo "── /etc/ml-defender/ ──"
check_dir "/etc/ml-defender"        "750" "root"        "${ARGUS_GROUP}"
for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do
    check_dir "/etc/ml-defender/${comp}" "750" "${ARGUS_USER}" "${ARGUS_GROUP}"
    # seed.bin debe ser solo-lectura por argus
    check_file "/etc/ml-defender/${comp}/seed.bin" "400" "${ARGUS_USER}" "${ARGUS_GROUP}"
done
check_dir "/etc/ml-defender/plugins" "750" "root"       "${ARGUS_GROUP}"
check_file "/etc/ml-defender/plugins/plugin_signing.pk" "444" "root" "${ARGUS_GROUP}"

echo ""
echo "── /var/log/argus/ ──"
check_dir "/var/log/argus"          "750" "root"        "${ARGUS_GROUP}"
for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do
    check_dir "/var/log/argus/${comp}" "750" "${ARGUS_USER}" "${ARGUS_GROUP}"
done

echo ""
echo "── /tmp y /var/tmp — noexec ──"
if mount | grep -q "/tmp.*noexec"; then
    echo "  ✅ /tmp: noexec"
else
    echo "  FAIL: /tmp no tiene noexec"
    FAIL=1
fi
if mount | grep -q "/var/tmp.*noexec"; then
    echo "  ✅ /var/tmp: noexec"
else
    echo "  WARN: /var/tmp no tiene noexec (verificar /etc/fstab)"
fi

echo ""
echo "── Binarios sin SUID/SGID ──"
SUID_COUNT=$(find /opt/argus/bin -perm /6000 2>/dev/null | wc -l)
if [ "${SUID_COUNT}" -eq 0 ]; then
    echo "  ✅ Ningún binario con SUID/SGID (capabilities via setcap)"
else
    echo "  FAIL: ${SUID_COUNT} binario(s) con SUID/SGID encontrados"
    find /opt/argus/bin -perm /6000 2>/dev/null
    FAIL=1
fi

echo ""
if [ ${FAIL} -eq 0 ]; then
    echo "✅ check-prod-permissions PASSED"
else
    echo "FAIL: check-prod-permissions — ver errores arriba"
    exit 1
fi