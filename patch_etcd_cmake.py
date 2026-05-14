#!/usr/bin/env python3
# patch_etcd_cmake.py — Añade crypto_provider a etcd-server/CMakeLists.txt
# Ejecutar desde la raíz del proyecto: python3 patch_etcd_cmake.py

import sys

CMAKE_PATH = "etcd-server/CMakeLists.txt"

with open(CMAKE_PATH, "r") as f:
    content = f.read()

# ── Guardia: no aplicar dos veces ────────────────────────────────────────────
if "CRYPTO_PROVIDER_LIB" in content:
    print("⚠️  patch ya aplicado — nada que hacer")
    sys.exit(0)

# ── 1. Añadir find_library + find_path tras el bloque seed_client ────────────
SEED_BLOCK = """find_path(SEED_CLIENT_INCLUDE_DIR
        NAMES seed_client/seed_client.hpp
        PATHS /usr/local/include
        NO_DEFAULT_PATH
)"""

CRYPTO_PROVIDER_BLOCK = """find_library(CRYPTO_PROVIDER_LIB
        NAMES crypto_provider
        PATHS /usr/local/lib
        NO_DEFAULT_PATH
)
find_path(CRYPTO_PROVIDER_INCLUDE_DIR
        NAMES vault_client/crypto_provider.h
        PATHS /usr/local/include
        NO_DEFAULT_PATH
)"""

if SEED_BLOCK not in content:
    print("❌ No se encontró el bloque seed_client en CMakeLists.txt")
    sys.exit(1)

content = content.replace(
    SEED_BLOCK,
    SEED_BLOCK + "\n" + CRYPTO_PROVIDER_BLOCK
)

# ── 2. Añadir ${CRYPTO_PROVIDER_LIB} en target_link_libraries(etcd-server) ──
OLD_LINK = """target_link_libraries(etcd-server
        PRIVATE
        crypto_transport
        seed_client"""

NEW_LINK = """target_link_libraries(etcd-server
        PRIVATE
        crypto_transport
        seed_client
        ${CRYPTO_PROVIDER_LIB}"""

if OLD_LINK not in content:
    print("❌ No se encontró target_link_libraries(etcd-server)")
    sys.exit(1)

content = content.replace(OLD_LINK, NEW_LINK)

# ── 3. Añadir ${CRYPTO_PROVIDER_INCLUDE_DIR} en target_include_directories ──
# Buscamos la línea de SEED_CLIENT_INCLUDE_DIR dentro de target_include_directories
OLD_INCLUDE = "${SEED_CLIENT_INCLUDE_DIR}"
NEW_INCLUDE = "${SEED_CLIENT_INCLUDE_DIR}\n        ${CRYPTO_PROVIDER_INCLUDE_DIR}"

# Solo reemplazar la primera ocurrencia dentro de target_include_directories
idx = content.find("target_include_directories(etcd-server")
if idx == -1:
    print("⚠️  No se encontró target_include_directories(etcd-server) — include manual requerido")
else:
    # Buscar SEED_CLIENT_INCLUDE_DIR solo después de idx
    seed_idx = content.find(OLD_INCLUDE, idx)
    if seed_idx != -1:
        content = content[:seed_idx] + NEW_INCLUDE + content[seed_idx + len(OLD_INCLUDE):]
    else:
        print("⚠️  SEED_CLIENT_INCLUDE_DIR no encontrado en target_include_directories — include manual requerido")

# ── Escribir resultado ────────────────────────────────────────────────────────
with open(CMAKE_PATH, "w") as f:
    f.write(content)

print("✅ etcd-server/CMakeLists.txt parcheado correctamente")
print("   + find_library(CRYPTO_PROVIDER_LIB)")
print("   + find_path(CRYPTO_PROVIDER_INCLUDE_DIR)")
print("   + target_link_libraries: ${CRYPTO_PROVIDER_LIB}")
print("   + target_include_directories: ${CRYPTO_PROVIDER_INCLUDE_DIR}")