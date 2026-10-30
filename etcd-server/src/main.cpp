// etcd-server/src/main.cpp
// Day 54: Compatible con namespace etcd_server::
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/etcd_server.hpp"
#include "etcd_server/secrets_manager.hpp"
#include "etcd_server/etcd_server_config.hpp"
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
#include <sodium.h>
#include <sstream>
#include "alert_client.hpp"
#include <vault_client/http_etcd_registrar.h>
#include <vault_client/crypto_epoch_coordinator.h>
#include <iomanip>
#include <cstdio>

std::unique_ptr<EtcdServer> g_server;
std::shared_ptr<etcd_server::SecretsManager> g_secrets_manager;

void signal_handler(int signal) {
    std::cout << std::endl << "📡 Recibida señal " << signal << ", cerrando etcd-server..." << std::endl;
    if (g_server) {
        g_server->stop();
    }
    exit(0);
}

int main(int argc, char** argv) {
    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    std::cout << "🚀 Iniciando etcd-server v0.3 - Day 54 Grace Period..." << std::endl;

    // [ETCD-CONFIG-D312] -c/--config RUTA (defecto: la de siempre) y --check-config (lee y valida el JSON y sale:
    // 0 sin defectos, 1 con alguno; los obsoletos solo avisan). El JSON es la ley: si no se puede leer, o un campo
    // falta o está mal, se avisa ([CONFIG-DEFAULT]) y se usa el defecto validado.
    std::string config_path = "/etc/ml-defender/etcd-server/etcd-server.json";
    bool check_only = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if ((a == "-c" || a == "--config") && i + 1 < argc) {
            config_path = argv[++i];
        } else if (a == "--check-config") {
            check_only = true;
        } else {
            std::cerr << "Uso: etcd-server [-c|--config RUTA] [--check-config]" << std::endl;
            return 2;
        }
    }
    nlohmann::json root = nlohmann::json::object();
    bool fichero_ok = false;
    {
        std::ifstream f(config_path);
        if (!f.good()) {
            std::cerr << "[CONFIG-DEFAULT] no se puede abrir " << config_path
                      << ": se usan los defectos de todos los campos" << std::endl;
        } else {
            try {
                root = nlohmann::json::parse(f);
                fichero_ok = true;
            } catch (const std::exception& e) {
                std::cerr << "[CONFIG-DEFAULT] " << config_path << " no es JSON válido (" << e.what()
                          << "): se usan los defectos de todos los campos" << std::endl;
            }
        }
    }
    const auto leida = argus::etcdcfg::parse_etcd_server_config(root);
    const auto& cfg = leida.cfg;
    if (check_only) {
        const bool limpio = fichero_ok && leida.defectos == 0;
        std::cout << "[ETCD-CONFIG-CHECK] " << config_path << ": " << (limpio ? "OK" : "CON DEFECTOS")
                  << " (defectos=" << leida.defectos << ", obsoletos=" << leida.obsoletos << ")" << std::endl;
        return limpio ? 0 : 1;
    }

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
        // [ETCD-CONFIG-D312] /run/argus ANTES del AutonomyPublisher: su socket ipc vive ahí. Si faltaba (VM etcd,
        // DAY312) el arranque moría con "No such file or directory"; se creaba más abajo, tarde.
        std::filesystem::create_directories("/run/argus");
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
            // DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (DAY 157)
            // Construir JSON canónico a firmar (sin signature_hex, claves ordenadas)
            const std::string provider_str =
                crypto_provider->is_healthy() ? "ok" : "degraded";
            const std::string canonical =
                std::string("{") +
                "\"component\":\"etcd-server\"," +
                "\"fingerprint\":\"" + fingerprint_hex + "\"," +
                "\"from_cache\":" + (crypto_material.from_cache ? "true" : "false") + "," +
                "\"key_version\":" + std::to_string(crypto_material.key_version) + "," +
                "\"provider\":\"" + provider_str + "\"," +
                "\"timestamp\":\"" + crypto_material.derivation_timestamp + "\"" +
                "}";

            // Firmar con Ed25519 (mismo patrón que autonomy_state_writer.h)
            std::array<uint8_t, crypto_sign_BYTES> sig{};
            unsigned long long sig_len = 0;
            if (crypto_sign_detached(
                    sig.data(), &sig_len,
                    reinterpret_cast<const uint8_t*>(canonical.data()),
                    canonical.size(),
                    crypto_material.sk.data()) != 0)
            {
                throw std::runtime_error("crypto_sign_detached falló en bootstrap status");
            }

            // Convertir firma a hex
            std::ostringstream sig_oss;
            sig_oss << std::hex << std::setfill('0');
            for (size_t i = 0; i < sig_len; ++i)
                sig_oss << std::setw(2) << static_cast<unsigned>(sig[i]);
            const std::string sig_hex = sig_oss.str();

            // Escribir JSON final con signature_hex — escritura atómica tmp→rename
            const std::string tmp_path = bootstrap_path + ".tmp";
            {
                std::ofstream bsf(tmp_path);
                bsf << "{\n"
                    << "  \"component\": \"etcd-server\",\n"
                    << "  \"provider\": \"" << provider_str << "\",\n"
                    << "  \"fingerprint\": \"" << fingerprint_hex << "\",\n"
                    << "  \"key_version\": " << crypto_material.key_version << ",\n"
                    << "  \"from_cache\": " << (crypto_material.from_cache ? "true" : "false") << ",\n"
                    << "  \"timestamp\": \"" << crypto_material.derivation_timestamp << "\",\n"
                    << "  \"signature_hex\": \"" << sig_hex << "\"\n"
                    << "}\n";
                bsf.flush();
            }
            // fsync via FILE* para durabilidad antes del rename
            {
                FILE* f = ::fopen(tmp_path.c_str(), "r");
                if (f) { ::fsync(::fileno(f)); ::fclose(f); }
            }
            std::rename(tmp_path.c_str(), bootstrap_path.c_str());
            std::filesystem::permissions(bootstrap_path,
                std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
                std::filesystem::perm_options::replace);
            std::cout << "✅ ICryptoProvider OK — fingerprint: "
                      << fingerprint_hex.substr(0, 16) << "..." << std::endl;
            std::cout << "✅ Bootstrap status firmado (Ed25519): " << bootstrap_path << std::endl;
        } catch (const std::exception& e) {
            // No fatal — el fichero es informativo, no bloquea el arranque
            std::cerr << "⚠️  No se pudo escribir bootstrap status: " << e.what() << std::endl;
        }

        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  Initializing SecretsManager (Day 54)" << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        // [ETCD-CONFIG-D312] del JSON (validado por argus::etcdcfg), no fijo en el código
        const nlohmann::json config = {
            {"secrets", {
                {"grace_period_seconds", cfg.grace_period_seconds},
                {"default_key_length_bytes", cfg.default_key_length_bytes},
                {"min_rotation_interval_seconds", cfg.min_rotation_interval_seconds}
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

        g_server = std::make_unique<EtcdServer>(cfg, config_path);
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
        std::cout << "🌐 Servidor HTTP escuchando en: http://" << cfg.host << ":" << cfg.port << std::endl;
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

        // ═══════════════════════════════════════════════════════════
        // STEP 4b: CryptoEpochCoordinator (ADR-045 v2 — DAY 164)
        // Registra etcd-server en el servidor de configuración y
        // observa /v1/epoch para coordinar rotaciones de época.
        // ═══════════════════════════════════════════════════════════
        // [ETCD-CONFIG-D312] mismo host:puerto que el servidor; si escucha en todas (0.0.0.0) se entra por loopback
        const std::string etcd_server_url = "http://" + (cfg.host == "0.0.0.0" ? std::string("127.0.0.1") : cfg.host)
                                          + ":" + std::to_string(cfg.port);
        ml_defender::HttpEtcdRegistrar epoch_registrar(
            etcd_server_url, "etcd-server",
            /*keepalive_ms=*/30000,
            /*poll_ms=*/2000);
        std::this_thread::sleep_for(std::chrono::milliseconds(1500)); // esperar servidor listo
        epoch_registrar.register_status(crypto_material, "etcd-server");
        epoch_registrar.start_keepalive();

        ml_defender::CryptoEpochCoordinator epoch_coordinator(
            epoch_registrar, "etcd-server");
        epoch_coordinator.start([&](uint16_t eid, const std::string& nb) {
            std::cout << "[epoch] 🔄 Nueva época " << eid
                      << " not_before=" << nb
                      << " — handle.reload() pendiente FASE 3" << std::endl;
            // FASE 3 (BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001):
            // handle.reload(CryptoProvider::create(new_cfg));
        });
        std::cout << "✅ CryptoEpochCoordinator arrancado (watch /v1/epoch)" << std::endl;

        // Borrar bootstrap status — servidor activo y aceptando conexiones
        try {
            std::filesystem::remove(bootstrap_path);
            std::cout << "✅ Bootstrap status eliminado (servidor activo)" << std::endl;
        } catch (...) {}

        // ── Health-check loop con SM de autonomía (DAY 156) ──────────────
        auto   last_vault_check = std::chrono::steady_clock::now();
        bool   was_vault_healthy = true;

        // ── AlertClient (DEBT-ALERTING-EDGE-SOS-001) ─────────────────────────────
        // [ETCD-CONFIG-D312] el mismo JSON ya leído (-c/--config), no una segunda lectura de una ruta fija
        argus::AlertClient alert_client([&]() -> nlohmann::json {
            if (root.is_object() && root.contains("alerting")) return root;
            return nlohmann::json{{"alerting", {{"enabled", false}}}};
        }());
        while (g_server->is_running()) {
            auto now     = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                               now - last_vault_check).count();

            if (elapsed >= 5) {
                const bool healthy = crypto_provider->is_healthy();
                if (!healthy && was_vault_healthy) {
                    std::cout << "[autonomy] Vault KO → AUTONOMOUS" << std::endl;
                    autonomy_sm.on_vault_unreachable();
                    alert_client.send_sos({
                        .node            = "etcd-server",
                        .component       = "etcd-server",
                        .event           = "AUTONOMOUS_STATE_ACTIVATED",
                        .pipeline_status = "vault_unreachable"
                    });
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