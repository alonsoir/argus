#!/usr/bin/env bash
# tools/prod/build-x86.sh
# Compila el pipeline usando el Makefile raíz como fuente de verdad (DAY 134).
# Invoca pipeline-build (orden canónico: proto→seed→crypto→etcd→plugin→componentes)
# y luego recolecta los binarios en dist/x86/bin/.
# ADR-039 (BSR): este script NUNCA corre en la hardened VM.
set -euo pipefail

DIST=/vagrant/dist/x86/bin
VAGRANT=/vagrant

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  aRGus NDR — Production Build (x86-64)                   ║"
echo "║  Orden canónico via pipeline-build (Makefile raíz)       ║"
echo "╚════════════════════════════════════════════════════════════╝"

mkdir -p "${DIST}"

# ── Paso 1: pipeline-build (fuente de verdad) ─────────────────────────────────
echo ""
echo "── Recolectando binarios PROFILE=production (ya compilados por Makefile) ──"

# ── Paso 2: recolectar binarios en dist/x86/bin/ ─────────────────────────────
echo ""
echo "── Step 2: recolecting binaries → dist/x86/bin/ ──"

declare -A BINARIES=(
    ["etcd-server"]="${VAGRANT}/etcd-server/build-production/etcd-server"
    ["sniffer"]="${VAGRANT}/sniffer/build-production/sniffer"
    ["ml-detector"]="${VAGRANT}/ml-detector/build-production/ml-detector"
    ["firewall-acl-agent"]="${VAGRANT}/firewall-acl-agent/build-production/firewall-acl-agent"
    ["rag-ingester"]="${VAGRANT}/rag-ingester/build-production/rag-ingester"
)

for name in "${!BINARIES[@]}"; do
    src="${BINARIES[$name]}"
    if [ -f "${src}" ]; then
        cp "${src}" "${DIST}/${name}"
        echo "  ✅ ${name} → dist/x86/bin/${name}"
    else
        echo "  ❌ ${name} NOT FOUND at ${src}"
        exit 1
    fi
done

# ── Paso 3: plugins ───────────────────────────────────────────────────────────
echo ""
echo "── Step 3: plugins → dist/x86/plugins/ ──"
mkdir -p /vagrant/dist/x86/plugins

PLUGIN_SRC="${VAGRANT}/plugins/xgboost/build/libplugin_xgboost.so"
if [ -f "${PLUGIN_SRC}" ]; then
    cp "${PLUGIN_SRC}" /vagrant/dist/x86/plugins/
    echo "  ✅ libplugin_xgboost.so → dist/x86/plugins/"
else
    echo "  ⚠️  libplugin_xgboost.so not found — skipping (optional)"
fi

# plugin-loader shared lib
LOADER_SRC="${VAGRANT}/plugin-loader/build/libplugin_loader.so"
if [ -f "${LOADER_SRC}" ]; then
    cp "${LOADER_SRC}" /vagrant/dist/x86/lib/
    echo "  ✅ libplugin_loader.so → dist/x86/lib/"
fi

echo ""
echo "✅ prod-build-x86 completado — binarios en dist/x86/bin/"
