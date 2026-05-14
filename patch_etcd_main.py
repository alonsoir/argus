#!/usr/bin/env python3
# patch_etcd_main.py — Añade STEP 0 ICryptoProvider a etcd-server/src/main.cpp
# Ejecutar desde la raíz del proyecto: python3 patch_etcd_main.py

import sys

MAIN_PATH = "etcd-server/src/main.cpp"

with open(MAIN_PATH, "r") as f:
    content = f.read()

# ── Guardia: no aplicar dos veces ────────────────────────────────────────────
if "ICryptoProvider" in content:
    print("⚠️  patch ya aplicado — nada que hacer")
    sys.exit(0)

# ── 1. Añadir includes tras el bloque existente ───────────────────────────────
OLD_INCLUDES = '#include <exception>'

NEW_INCLUDES = '''#include <exception>
#include <vault_client/crypto_provider.h>
#include <fstream>
#include <filesystem>'''

if OLD_INCLUDES not in content:
    print("❌ No se encontró '#include <exception>' en main.cpp")
    sys.exit(1)

content = content.replace(OLD_INCLUDES, NEW_INCLUDES, 1)

# ── 2. Insertar STEP 0 antes de STEP 1 (SecretsManager) ─────────────────────
STEP1_MARKER = '''        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  Initializing SecretsManager (Day 54)" << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;'''

STEP0_BLOCK = '''        // ═══════════════════════════════════════════════════════════
        // STEP 0: ICryptoProvider — identidad criptográfica (ADR-044 DAY 151)
        // SeedClient + CryptoTransport (canal ZeroMQ) NO se tocan — Opción B.
        // ICryptoProvider gestiona identidad Ed25519 y bootstrap status.
        // ═══════════════════════════════════════════════════════════
        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  STEP 0: ICryptoProvider — identidad Ed25519         " << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        ml_defender::CryptoProviderConfig crypto_cfg;
        crypto_cfg.component_name        = "etcd-server";
        crypto_cfg.component_config_path = "/etc/ml-defender/etcd-server/";

        auto crypto_provider = ml_defender::CryptoProvider::create(crypto_cfg);
        auto crypto_material = crypto_provider->get_material();

        // Fingerprint hex
        char fp_buf[65] = {};
        for (size_t i = 0; i < crypto_material.fingerprint.size(); ++i) {
            snprintf(fp_buf + i * 2, 3, "%02x", crypto_material.fingerprint[i]);
        }
        std::string fingerprint_hex(fp_buf);

        // Escribir /run/argus/etcd-bootstrap-status.json (0600)
        // Fichero efímero: indica material criptográfico válido antes del arranque.
        // Se borra tras g_server->start().
        const std::string bootstrap_path = "/run/argus/etcd-bootstrap-status.json";
        try {
            std::filesystem::create_directories("/run/argus");
            std::ofstream bsf(bootstrap_path);
            bsf << "{\\n"
                << "  \\"component\\": \\"etcd-server\\",\\n"
                << "  \\"provider\\": \\"" << (crypto_provider->is_healthy() ? "ok" : "degraded") << "\\",\\n"
                << "  \\"fingerprint\\": \\"" << fingerprint_hex << "\\",\\n"
                << "  \\"key_version\\": " << crypto_material.key_version << ",\\n"
                << "  \\"from_cache\\": " << (crypto_material.from_cache ? "true" : "false") << ",\\n"
                << "  \\"timestamp\\": \\"" << crypto_material.derivation_timestamp << "\\"\\n"
                << "}\\n";
            bsf.close();
            std::filesystem::permissions(bootstrap_path,
                std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
                std::filesystem::perm_options::replace);
            std::cout << "✅ ICryptoProvider OK — fingerprint: "
                      << fingerprint_hex.substr(0, 16) << "..." << std::endl;
            std::cout << "✅ Bootstrap status escrito: " << bootstrap_path << std::endl;
        } catch (const std::exception& e) {
            // No fatal — el fichero es informativo, no bloquea el arranque
            std::cerr << "⚠️  No se pudo escribir bootstrap status: " << e.what() << std::endl;
        }

'''

if STEP1_MARKER not in content:
    print("❌ No se encontró el marker de STEP 1 (SecretsManager) en main.cpp")
    sys.exit(1)

content = content.replace(STEP1_MARKER, STEP0_BLOCK + STEP1_MARKER, 1)

# ── 3. Borrar bootstrap status tras g_server->start() ────────────────────────
OLD_START = "        g_server->start();"

NEW_START = '''        g_server->start();

        // Borrar bootstrap status — servidor activo y aceptando conexiones
        try {
            std::filesystem::remove(bootstrap_path);
            std::cout << "✅ Bootstrap status eliminado (servidor activo)" << std::endl;
        } catch (...) {}'''

if OLD_START not in content:
    print("❌ No se encontró 'g_server->start()' en main.cpp")
    sys.exit(1)

content = content.replace(OLD_START, NEW_START, 1)

# ── Escribir resultado ────────────────────────────────────────────────────────
with open(MAIN_PATH, "w") as f:
    f.write(content)

print("✅ etcd-server/src/main.cpp parcheado correctamente")
print("   + includes: vault_client/crypto_provider.h, fstream, filesystem")
print("   + STEP 0: ICryptoProvider::create() + bootstrap status")
print("   + bootstrap status eliminado tras g_server->start()")