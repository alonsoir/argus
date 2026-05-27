#!/usr/bin/env bash
# tools/prod/collect-libs.sh
# Recolecta las librerías runtime mínimas necesarias para ejecutar
# el pipeline en la hardened VM (sin dev deps).
# Se ejecuta DENTRO de la dev VM.
#
# DAY 133 — aRGus NDR — ADR-030 Variant A
set -euo pipefail

DIST_LIB=/vagrant/dist/x86/lib
mkdir -p "${DIST_LIB}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Collecting runtime libraries (x86-64)                    ║"
echo "║  Solo runtime — sin headers, sin -dev packages            ║"
echo "╚════════════════════════════════════════════════════════════╝"

copy_lib() {
    local pattern=$1
    local desc=$2
    local found=0
    for path in $(ldconfig -p 2>/dev/null | grep "${pattern}" | awk '{print $NF}'); do
        if [ -f "${path}" ]; then
            cp -L "${path}" "${DIST_LIB}/"
            echo "  ✅ ${desc}: $(basename ${path})"
            found=1
            break
        fi
    done
    [ ${found} -eq 1 ] || echo "  ⚠️  ${desc}: NOT FOUND (${pattern})"
}

# Librerías propias del proyecto (instaladas en /usr/local/lib)
for lib in \
    libsodium.so.26 \
    libcrypto_transport.so.1 \
    libseed_client.so.1 \
    libplugin_loader.so.1 \
    libetcd_client.so.1 \
    libetcd-cpp-api.so \
    libonnxruntime.so.1.17.1 \
    libfaiss.so \
    libxgboost.so; do
    if [ -f "/usr/local/lib/${lib}" ]; then
        cp -L "/usr/local/lib/${lib}" "${DIST_LIB}/"
        echo "  ✅ ${lib}"
    else
        echo "  ⚠️  ${lib}: not found in /usr/local/lib"
    fi
done

# Librerías del sistema necesarias en runtime
# (debian/bookworm64 ya las tiene, pero las listamos para documentar)
echo ""
echo "── System libs (already present in hardened VM) ──"
for lib in \
    libzmq.so.5 \
    libprotobuf.so.32 \
    liblz4.so.1 \
    libzstd.so.1 \
    libgomp.so.1 \
    libstdc++.so.6 \
    libgcc_s.so.1; do
    path=$(ldconfig -p 2>/dev/null | grep "^\s*${lib}" | awk '{print $NF}' | head -1) || true
    if [ -n "${path}" ] && [ -f "${path}" ]; then
        echo "  📋 ${lib} (system, no copy needed)"
    else
        echo "  ⚠️  ${lib}: not found"
    fi
done

# Symlinks para compatibilidad
echo ""
echo "── Creating symlinks ──"
cd "${DIST_LIB}"
[ -f libsodium.so.26 ] && ln -sf libsodium.so.26 libsodium.so 2>/dev/null || true
[ -f libonnxruntime.so.1.17.1 ] && ln -sf libonnxruntime.so.1.17.1 libonnxruntime.so 2>/dev/null || true

echo ""
echo "── Library inventory ──"
ls -lh "${DIST_LIB}/"
echo ""
echo "✅ collect-libs completado"