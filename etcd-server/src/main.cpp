// etcd-server/src/main.cpp
// Day 54: Compatible con namespace etcd_server::
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/etcd_server.hpp"
#include "etcd_server/secrets_manager.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <csignal>
#include <exception>
#include <vault_client/crypto_provider.h>
#include <fstream>
#include <filesystem>
#include <vault_client/autonomy_publisher.h>
#include <vault_client/crypto_autonomy.h>
#include <vault_client/autonomy_state_writer.h>

std::unique_ptr<EtcdServer> g_server;
std::shared_ptr<etcd_server::SecretsManager> g_secrets_manager;

void signal_handler(int signal) {
    std::cout << std::endl << "📡 Recibida señal " << signal << ", cerrando etcd-server..." << std::endl;
    if (g_server) {
        g_server->stop();
    }
    exit(0);
}

int main() {
    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    std::cout << "🚀 Iniciando etcd-server v0.3 - Day 54 Grace Period..." << std::endl;

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    try {
        // ═══════════════════════════════════════════════════════════
        // STEP 1: Initialize SecretsManager (Day 54)
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // STEP 0: ICryptoProvider — identidad criptográfica (ADR-044 DAY 151)
        // SeedClient + CryptoTransport (canal ZeroMQ) NO se tocan — Opción B.
        // ICryptoProvider gestiona identidad Ed25519 y bootstrap status.
        // ═══════════════════════════════════════════════════════════

        // ═══════════════════════════════════════════════════════════
        // STEP 0b: CryptoAutonomyStateMachine + AutonomyPublisher (DAY 156)
        // DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
        // etcd-server es el único publisher de autonomía en el nodo (Q1 DAY 155).
        // ═══════════════════════════════════════════════════════════
        const std::string autonomy_endpoint = "ipc:///run/argus/autonomy.sock";
        ml_defender::common::AutonomyPublisher autonomy_pub(
            autonomy_endpoint, "etcd-server", 0
        );
        ml_defender::CryptoAutonomy autonomy_sm(
            "etcd-server",
            autonomy_pub.make_callback()
        );
        std::cout << "✅ AutonomyPublisher + CryptoAutonomySM inicializados" << std::endl;
        std::cout << "   endpoint: " << autonomy_endpoint << std::endl;

        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  STEP 0: ICryptoProvider — identidad Ed25519         " << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        ml_defender::CryptoProviderConfig crypto_cfg;
        crypto_cfg.component_name        = "etcd-server";
        crypto_cfg.component_config_path = "/etc/ml-defender/etcd-server/";

        auto crypto_provider = ml_defender::CryptoProvider::create(crypto_cfg);
        auto crypto_material = crypto_provider->get_material();

        // ═══════════════════════════════════════════════════════════
        // STEP 0c: AutonomyStateWriter — persistencia de estado (DAY 157)
        // DEBT-AUTONOMY-STATE-PERSISTENCE-001
        // ═══════════════════════════════════════════════════════════
        ml_defender::AutonomyStateWriter autonomy_writer;
        uint64_t autonomy_sequence = 0;

        // Leer estado previo firmado con la clave pública del componente
        auto persisted = autonomy_writer.read_and_verify(crypto_material.pk);
        if (persisted.has_value() &&
            persisted->mode == ml_defender::OperationalMode::AUTONOMOUS)
        {
            std::cout << "[autonomy] Estado persistido: AUTONOMOUS (seq="
                      << persisted->sequence << ") — arrancando en AUTONOMOUS"
                      << std::endl;
            autonomy_sm.on_vault_unreachable();
            autonomy_sequence = persisted->sequence;
        } else {
            std::cout << "[autonomy] Sin estado AUTONOMOUS persistido — arrancando NORMAL"
                      << std::endl;
        }

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
            bsf << "{\n"
                << "  \"component\": \"etcd-server\",\n"
                << "  \"provider\": \"" << (crypto_provider->is_healthy() ? "ok" : "degraded") << "\",\n"
                << "  \"fingerprint\": \"" << fingerprint_hex << "\",\n"
                << "  \"key_version\": " << crypto_material.key_version << ",\n"
                << "  \"from_cache\": " << (crypto_material.from_cache ? "true" : "false") << ",\n"
                << "  \"timestamp\": \"" << crypto_material.derivation_timestamp << "\"\n"
                << "}\n";
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

        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  Initializing SecretsManager (Day 54)" << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        nlohmann::json config = {
    		{"secrets", {
        	{"grace_period_seconds", 300},
        	{"rotation_interval_hours", 168},
        	{"default_key_length_bytes", 32},
        	{"min_rotation_interval_seconds", 300}  // AÑADIR (ADR-004)
    	}}
		};

        g_secrets_manager = std::make_shared<etcd_server::SecretsManager>(config);

        std::cout << "✅ SecretsManager inicializado correctamente" << std::endl;
        std::cout << "   - Grace period: " << g_secrets_manager->get_grace_period_seconds() << "s" << std::endl;
        std::cout << "   - Namespace: etcd_server::" << std::endl;

        // ═══════════════════════════════════════════════════════════
        // STEP 2: Initialize EtcdServer
        // ═══════════════════════════════════════════════════════════
        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  Initializing EtcdServer" << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        g_server = std::make_unique<EtcdServer>(2379);

        // NOTA: set_secrets_manager espera etcd::SecretsManager*
        // Esto puede causar incompatibilidad de tipos
        // TODO Day 55: Actualizar EtcdServer para aceptar etcd_server::SecretsManager
        // Por ahora, comentamos esta línea para que compile
        g_server->set_secrets_manager(g_secrets_manager.get());

        if (!g_server->initialize()) {
            std::cerr << "❌ Error inicializando etcd-server" << std::endl;
            return 1;
        }

        std::cout << "✅ etcd-server inicializado correctamente" << std::endl;
        std::cout << std::endl;

        // ═══════════════════════════════════════════════════════════
        // STEP 3: Display Available Endpoints
        // ═══════════════════════════════════════════════════════════
        std::cout << "🌐 Servidor HTTP escuchando en: http://0.0.0.0:2379" << std::endl;
        std::cout << "📚 Endpoints disponibles:" << std::endl;
        std::cout << "   POST /register      - Registrar componente" << std::endl;
        std::cout << "   POST /unregister    - Desregistrar componente" << std::endl;
        std::cout << "   GET  /components    - Listar componentes" << std::endl;
        std::cout << "   GET  /config/*      - Obtener configuración" << std::endl;
        std::cout << "   PUT  /config/*      - Actualizar configuración" << std::endl;
        std::cout << "   GET  /seed          - Obtener seed de cifrado ChaCha20" << std::endl;
        std::cout << "   GET  /validate      - Validar configuración global" << std::endl;
        std::cout << "   GET  /health        - Estado del servidor" << std::endl;
        std::cout << "   GET  /info          - Información del sistema" << std::endl;
        std::cout << std::endl;
        std::cout << "🔐 Secrets Endpoints (Day 54 - NEW):" << std::endl;
        std::cout << "   (SecretsManager activo pero NO integrado aún con EtcdServer)" << std::endl;
        std::cout << "   TODO Day 55: Integrar etcd_server::SecretsManager con EtcdServer" << std::endl;
        std::cout << std::endl;

        // ═══════════════════════════════════════════════════════════
        // STEP 4: Start Server
        // ═══════════════════════════════════════════════════════════
        std::cout << "🚀 Starting HTTP server..." << std::endl;
        std::cout << "💡 ChaCha20 seed encryption: ACTIVE (EtcdServer)" << std::endl;
        std::cout << "💡 HMAC Grace Period: READY (etcd_server::SecretsManager)" << std::endl;
        std::cout << "⚠️  SecretsManager NO integrado aún (namespace mismatch)" << std::endl;
        std::cout << std::endl;

        g_server->start();

        // Borrar bootstrap status — servidor activo y aceptando conexiones
        try {
            std::filesystem::remove(bootstrap_path);
            std::cout << "✅ Bootstrap status eliminado (servidor activo)" << std::endl;
        } catch (...) {}

        // ── Health-check loop con SM de autonomía (DAY 156) ──────────────
        auto   last_vault_check = std::chrono::steady_clock::now();
        bool   was_vault_healthy = true;

        while (g_server->is_running()) {
            auto now     = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                               now - last_vault_check).count();

            if (elapsed >= 5) {
                const bool healthy = crypto_provider->is_healthy();
                if (!healthy && was_vault_healthy) {
                    std::cout << "[autonomy] Vault KO → AUTONOMOUS" << std::endl;
                    autonomy_sm.on_vault_unreachable();
                    try {
                        autonomy_writer.write(
                            ml_defender::OperationalMode::AUTONOMOUS,
                            crypto_material.sk,
                            "etcd-server",
                            "vault_unreachable",
                            ++autonomy_sequence);
                        std::cout << "[autonomy] Estado AUTONOMOUS persistido (seq="
                                  << autonomy_sequence << ")" << std::endl;
                    } catch (const std::exception& e) {
                        std::cerr << "[autonomy] WARN: no se pudo persistir estado: "
                                  << e.what() << std::endl;
                    }
                } else if (healthy && !was_vault_healthy) {
                    std::cout << "[autonomy] Vault OK → RECONCILING" << std::endl;
                    autonomy_sm.on_vault_restored();
                    // on_reconciliation_ok() se llamará tras validar material
                    // DEBT-CRYPTO-RECONCILIATION-001
                    autonomy_sm.on_reconciliation_ok();
                    try {
                        autonomy_writer.write(
                            ml_defender::OperationalMode::NORMAL,
                            crypto_material.sk,
                            "etcd-server",
                            "vault_restored",
                            ++autonomy_sequence);
                        std::cout << "[autonomy] Estado NORMAL persistido (seq="
                                  << autonomy_sequence << ")" << std::endl;
                    } catch (const std::exception& e) {
                        std::cerr << "[autonomy] WARN: no se pudo persistir estado: "
                                  << e.what() << std::endl;
                    }
                }
                was_vault_healthy = healthy;
                last_vault_check  = now;
            }

            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

    } catch (const std::exception& e) {
        std::cerr << "❌ Excepción fatal: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "👋 etcd-server terminado" << std::endl;
    return 0;
}