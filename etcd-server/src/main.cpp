// etcd-server/src/main.cpp
// Day 54: Compatible con namespace etcd_server::
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/etcd_server.hpp"
#include "etcd_server/secrets_manager.hpp"
#include "etcd_server/etcd_server_config.hpp"
#include "etcd_server/etcd_server_authz.hpp"
#include "etcd_server/etcd_server_almacen.hpp"
#include "etcd_server/etcd_registry_store.hpp"
#include "etcd_server/etcd_server_claves.hpp"   // [ETCD-CLAVES-D314]
#include "etcd_server/vault_secret_store.hpp"   // [ETCD-CLAVES-D314]
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
    // [ETCD-AUTHZ-D313] bloques tls y authz del mismo JSON
    const auto leida_tls = argus::etcdcfg::parse_tls_config(root);
    const auto& tls = leida_tls.cfg;
    auto leida_authz = argus::etcdauthz::parse_authz(root);
    // [ETCD-REGISTRO-D313] bloque almacen (etcd real | memoria de transición)
    const auto leida_almacen = argus::etcdcfg::parse_almacen_config(root);
    const auto& almacen_cfg = leida_almacen.cfg;
    // [ETCD-CLAVES-D314] bloque almacen_claves (Vault | memoria de transición). Direcciones y certificados de Vault
    // ausentes o mal formados en modo vault: [ETCD-VAULT-FATAL], no se arranca (decisión de Alonso DAY314)
    const auto leida_claves = argus::etcdcfg::parse_almacen_claves_config(root);
    const auto& claves_cfg = leida_claves.cfg;
    const int defectos = leida.defectos + leida_tls.defectos + leida_authz.defectos + leida_almacen.defectos +
                         leida_claves.defectos;
    if (defectos > 0) {
        std::cerr << "[CONFIG-DEFAULT] " << defectos << " ajustes con valor por defecto en " << config_path
                  << ": revisarlo" << std::endl;
    }
    // En mtls, los tres ficheros deben poder leerse: si no, el servidor no arranca ([ETCD-TLS-FATAL])
    int tls_ilegibles = 0;
    if (tls.modo == "mtls") {
        for (const auto* r : {&tls.ca_file, &tls.cert_file, &tls.key_file}) {
            std::ifstream f(*r, std::ios::binary);
            if (!f.good() || f.peek() == std::ifstream::traits_type::eof()) {
                std::cerr << "[ETCD-TLS-FATAL] no se puede leer " << *r << " (o está vacío)" << std::endl;
                ++tls_ilegibles;
            }
        }
    }
    // En modo etcd, los certificados del almacén deben poder leerse; si no, el registro no estará disponible (503),
    // pero el proceso arranca igual (no es TLS de servicio): aviso [ETCD-ALMACEN-FICHERO]
    int almacen_ilegibles = 0;
    // [ETCD-ALMACEN-FATAL-D315] con campos fatales no se miran los ficheros (las rutas pueden ser las de ejemplo)
    const int almacen_fatales = static_cast<int>(leida_almacen.fatales.size());
    if (almacen_cfg.modo == "etcd" && almacen_fatales == 0) {
        for (const auto* r : {&almacen_cfg.ca_file, &almacen_cfg.cert_file, &almacen_cfg.key_file}) {
            std::ifstream f(*r, std::ios::binary);
            if (!f.good() || f.peek() == std::ifstream::traits_type::eof()) {
                std::cerr << "[ETCD-ALMACEN-FICHERO] no se puede leer " << *r
                          << " (o está vacío): el registro no estará disponible (503)" << std::endl;
                ++almacen_ilegibles;
            }
        }
    } else if (almacen_cfg.modo == "memoria") {
        std::cerr << "[ETCD-ALMACEN-MEMORIA] almacen.modo=memoria: el registro vive solo en memoria y se pierde al "
                     "reiniciar. Solo transición hasta el paso 6 de DEBT-ETCD-HA-TLS-RAFT-001" << std::endl;
    }
    // [ETCD-CLAVES-D314] en modo vault, los certificados para Vault deben poder leerse: si no, no hay claves nunca
    // (error de configuración, no un fallo pasajero): fatal como los de TLS
    int claves_ilegibles = 0;
    if (claves_cfg.modo == "vault" && leida_claves.fatales.empty()) {
        for (const auto* r : {&claves_cfg.ca_file, &claves_cfg.cert_file, &claves_cfg.key_file}) {
            std::ifstream f(*r, std::ios::binary);
            if (!f.good() || f.peek() == std::ifstream::traits_type::eof()) {
                std::cerr << "[ETCD-VAULT-FATAL] no se puede leer " << *r << " (o está vacío): sin él no hay login en "
                          << "Vault; no se arranca" << std::endl;
                ++claves_ilegibles;
            }
        }
    } else if (claves_cfg.modo == "memoria") {
        std::cerr << "[ETCD-CLAVES-MEMORIA] almacen_claves.modo=memoria: las claves HMAC viven solo en memoria y se "
                     "pierden al reiniciar. Solo transición hasta el paso 6 de DEBT-ETCD-HA-TLS-RAFT-001" << std::endl;
    }
    const int claves_fatales = static_cast<int>(leida_claves.fatales.size()) + claves_ilegibles;
    if (check_only) {
        const bool limpio = fichero_ok && defectos == 0 && tls_ilegibles == 0 && almacen_ilegibles == 0 &&
                            almacen_fatales == 0 && claves_fatales == 0;
        std::cout << "[ETCD-CONFIG-CHECK] " << config_path << ": " << (limpio ? "OK" : "CON DEFECTOS")
                  << " (defectos=" << defectos << ", obsoletos=" << leida.obsoletos << ", tls.modo=" << tls.modo
                  << ", ficheros_tls_ilegibles=" << tls_ilegibles << ", almacen.modo=" << almacen_cfg.modo
                  << ", ficheros_almacen_ilegibles=" << almacen_ilegibles << ", almacen_fatales=" << almacen_fatales
                  << ", almacen_claves.modo=" << claves_cfg.modo
                  << ", claves_fatales=" << claves_fatales << ")" << std::endl;
        return limpio ? 0 : 1;
    }

    if (almacen_fatales > 0) {
        std::cerr << "[ETCD-ALMACEN-FATAL] " << almacen_fatales << " problemas en almacen de " << config_path
                  << ": el etcd-server no arranca (revisar con --check-config)" << std::endl;
        return 1;
    }
    if (claves_fatales > 0) {
        std::cerr << "[ETCD-VAULT-FATAL] " << claves_fatales << " problemas en almacen_claves de " << config_path
                  << ": el etcd-server no arranca (revisar con --check-config)" << std::endl;
        return 1;
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

        // [ETCD-CLAVES-D314] ventana de dos sobre el almacén de claves (Vault en la VM etcd; memoria en el defender
        // hasta el paso 6). Los parámetros, del JSON (validado por argus::etcdcfg)
        std::unique_ptr<argus::claves::ISecretStore> almacen_claves;
        if (claves_cfg.modo == "vault") {
            almacen_claves = std::make_unique<argus::claves::VaultSecretStore>(claves_cfg, std::cout);
        } else {
            almacen_claves = std::make_unique<argus::claves::MemoriaSecretStore>();
        }
        const etcd_server::SecretsConfig sec{cfg.grace_period_seconds, cfg.default_key_length_bytes,
                                             cfg.min_rotation_interval_seconds};
        g_secrets_manager = std::make_shared<etcd_server::SecretsManager>(
            sec, std::move(almacen_claves), claves_cfg.modo == "memoria", claves_cfg.aviso_intervalo_s,
            claves_cfg.sondeo_s);
        g_secrets_manager->comprobar_al_arrancar();
        g_secrets_manager->arrancar_monitor();

        // ═══════════════════════════════════════════════════════════
        // STEP 2: Initialize EtcdServer
        // ═══════════════════════════════════════════════════════════
        std::cout << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;
        std::cout << "  Initializing EtcdServer" << std::endl;
        std::cout << "═══════════════════════════════════════════════════════" << std::endl;

        std::unique_ptr<argus::almacen::IRegistryStore> almacen;
        if (almacen_cfg.modo == "etcd") {
            almacen = std::make_unique<argus::almacen::EtcdRegistryStore>(almacen_cfg);
        } else {
            almacen = std::make_unique<argus::almacen::MemoriaRegistryStore>();
        }
        g_server = std::make_unique<EtcdServer>(cfg, tls, std::move(leida_authz.reglas), almacen_cfg,
                                                std::move(almacen), config_path);
        g_server->set_secrets_manager(g_secrets_manager.get());

        if (!g_server->initialize()) {
            std::cerr << "❌ Error inicializando etcd-server" << std::endl;
            return 1;
        }

        std::cout << "✅ etcd-server inicializado correctamente" << std::endl;
        std::cout << std::endl;

        // ═══════════════════════════════════════════════════════════
        // STEP 3: Start Server ([ETCD-AUTHZ-D313] rutas y permisos: las líneas [ETCD-AUTHZ] de arriba)
        // ═══════════════════════════════════════════════════════════
        std::cout << "🌐 Escuchando en " << (tls.modo == "mtls" ? "https://" : "http://") << cfg.host << ":"
                  << cfg.port << std::endl;
        g_server->start();

        // ═══════════════════════════════════════════════════════════
        // STEP 4: registro y latido del propio etcd-server, EN PROCESO ([ETCD-AUTHZ-D313], decisión de Alonso DAY313)
        // Antes: HttpEtcdRegistrar + CryptoEpochCoordinator contra sí mismo por HTTP (registro, latido cada 30 s y
        // sondeo de /v1/epoch cada 2 s, cuyo callback solo escribía en el log). Con HTTPS ese bucle fallaba; ahora va
        // directo a su ComponentRegistry y GET /components sigue mostrándolo. [ADR045-FUERA-D316] /v1/epoch, fuera.
        // ═══════════════════════════════════════════════════════════
        const std::string yo = nlohmann::json{
            {"component", "etcd-server"},
            {"key_version", crypto_material.key_version},
            {"family", crypto_material.family},
            {"started_with_cache", false}
        }.dump();
        if (g_server->register_component("etcd-server", yo)) {
            std::cout << "✅ etcd-server registrado en proceso (sin red)" << std::endl;
        } else {
            std::cerr << "❌ etcd-server no se pudo registrar en proceso (almacén no disponible): se reintenta con "
                         "cada latido" << std::endl;
        }
        auto last_self_heartbeat = std::chrono::steady_clock::now();
        auto last_tls_warning = std::chrono::steady_clock::now();

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

            // [ETCD-AUTHZ-D313] latido propio en proceso, cada heartbeat.interval_seconds
            if (std::chrono::duration_cast<std::chrono::seconds>(now - last_self_heartbeat).count() >=
                cfg.heartbeat_interval_seconds) {
                // [ETCD-REGISTRO-D313] si el almacén no respondía al arrancar (o lo perdió), se vuelve a registrar
                if (!g_server->update_heartbeat("etcd-server") && g_server->register_component("etcd-server", yo)) {
                    std::cout << "✅ etcd-server registrado en proceso (reintento)" << std::endl;
                }
                last_self_heartbeat = now;
            }
            // [ETCD-AUTHZ-D313] en modo http, aviso periódico: que nadie lo olvide encendido
            if (tls.modo != "mtls" &&
                std::chrono::duration_cast<std::chrono::seconds>(now - last_tls_warning).count() >=
                    tls.aviso_http_intervalo_s) {
                std::cerr << "[ETCD-TLS-DESACTIVADO] sirviendo HTTP en claro sin autenticación en " << cfg.host << ":"
                          << cfg.port << " (tls.modo=http, solo transición hasta el paso 6)" << std::endl;
                last_tls_warning = now;
            }

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