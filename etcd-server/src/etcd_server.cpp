#include "etcd_server/etcd_server.hpp"
#include "etcd_server/component_registry.hpp"
#include "etcd_server/compression_lz4.hpp"
#include "httplib.h"
#include <nlohmann/json.hpp>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include "etcd_server/secrets_manager.hpp"
#include <fstream>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <openssl/x509_vfy.h>

// ============================================================================
// Day 62: Contextual request logging helper
// [ETCD-AUTHZ-D313] se llama desde set_logger, DESPUÉS de responder: el status es el real
// (DEBT-ETCD-HEARTBEAT-LOG-STATUS-001: antes cada ruta escribía 200 antes de decidir)
// ============================================================================
static std::string server_iso8601_now() {
    auto now = std::chrono::system_clock::now();
    auto now_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    std::ostringstream ss;
    ss << std::put_time(std::gmtime(&now_t), "%Y-%m-%dT%H:%M:%S")
       << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    return ss.str();
}

// [ETCD-AUTHZ-D313] identidad (CN, OU) del certificado de cliente de la conexión. req.ssl es "const SSL*" en las
// versiones antiguas de cpp-httplib y "const void*" (sesión del backend; OpenSSL aquí) en las nuevas: static_cast vale
// para las dos. Sin sesión TLS (modo http) o con una verificación que no sea X509_V_OK, identidad no válida.
static argus::etcdauthz::Identidad identidad_de_peticion(const httplib::Request& req) {
    argus::etcdauthz::Identidad id;
    const SSL* s = static_cast<const SSL*>(req.ssl);
    if (s == nullptr) {
        id.motivo = "sin sesión TLS";
        return id;
    }
    if (SSL_get_verify_result(s) != X509_V_OK) {
        id.motivo = "verificación del certificado de cliente no superada";
        return id;
    }
    X509* cert = SSL_get1_peer_certificate(s);
    id = argus::etcdauthz::identidad_de_certificado(cert);
    if (cert != nullptr) X509_free(cert);
    return id;
}

static void log_request(const httplib::Request& req, const httplib::Response& res, bool con_tls) {
    using argus::etcdauthz::para_log;
    std::string component = req.get_header_value("X-Component-Name");
    std::string client_ts  = req.get_header_value("X-Request-Timestamp");
    if (component.empty()) component = "unknown";
    if (client_ts.empty())  client_ts  = "unknown";
    std::string cn = "-", ou = "-";
    if (con_tls) {
        const auto id = identidad_de_peticion(req);
        if (id.valida) { cn = id.cn; ou = id.ou; } else { cn = ou = "?"; }
    }
    std::cout << "[ETCD←] " << para_log(req.method, 16) << " " << para_log(req.path)
              << " | status=" << res.status
              << " | cn=" << cn << " | ou=" << ou
              << " | component=" << para_log(component, 64)
              << " | client_ts=" << para_log(client_ts, 64)
              << " | server_ts=" << server_iso8601_now()
              << std::endl;
}
// etcd-server/src/etcd_server.cpp
using json = nlohmann::json;

EtcdServer::EtcdServer(const argus::etcdcfg::EtcdServerConfig& cfg, const argus::etcdcfg::TlsConfig& tls,
                       std::vector<argus::etcdauthz::Regla> reglas, const argus::etcdcfg::AlmacenConfig& almacen_cfg,
                       std::unique_ptr<argus::almacen::IRegistryStore> almacen, const std::string& config_path)
    : host_(cfg.host), port_(cfg.port), heartbeat_interval_seconds_(cfg.heartbeat_interval_seconds),
      tls_(tls), reglas_(std::move(reglas)) {
    component_registry_ = std::make_unique<ComponentRegistry>(
        config_path, std::move(almacen), cfg.heartbeat_interval_seconds, cfg.heartbeat_timeout_multiplier,
        cfg.heartbeat_check_interval_seconds, almacen_cfg.aviso_intervalo_s, almacen_cfg.modo == "memoria");
}

EtcdServer::~EtcdServer() {
    stop();
}

static bool legible(const std::string& ruta) {
    std::ifstream f(ruta, std::ios::binary);
    return f.good() && f.peek() != std::ifstream::traits_type::eof();
}

bool EtcdServer::initialize() {
    std::cout << "[ETCD-SERVER] 🔧 Inicializando servidor en " << host_ << ":" << port_
              << " (tls.modo=" << tls_.modo << ")" << std::endl;
    if (tls_.modo == "mtls") {
        // Sin TLS válido no hay forma segura de servir: no se arranca (day312_diseno.md §4b.2)
        bool ok = true;
        for (const auto* r : {&tls_.ca_file, &tls_.cert_file, &tls_.key_file}) {
            if (!legible(*r)) {
                std::cerr << "[ETCD-TLS-FATAL] no se puede leer " << *r << " (o está vacío): sin TLS válido no se sirve"
                          << std::endl;
                ok = false;
            }
        }
        if (!ok) return false;
        // Con CA de cliente, cpp-httplib exige certificado de cliente (SSL_VERIFY_PEER | FAIL_IF_NO_PEER_CERT)
        auto ssl = std::make_unique<httplib::SSLServer>(tls_.cert_file.c_str(), tls_.key_file.c_str(),
                                                        tls_.ca_file.c_str(), nullptr);
        if (!ssl->is_valid()) {
            std::cerr << "[ETCD-TLS-FATAL] certificado, clave o CA no válidos (" << tls_.cert_file << ", "
                      << tls_.key_file << ", " << tls_.ca_file << "): sin TLS válido no se sirve" << std::endl;
            return false;
        }
        server_ = std::move(ssl);
        std::cout << "[ETCD-TLS] HTTPS con mTLS: CA de cliente " << tls_.ca_file << ", certificado " << tls_.cert_file
                  << "; " << reglas_.size() << " reglas de autorización, denegar por defecto" << std::endl;
    } else {
        server_ = std::make_unique<httplib::Server>();
        std::cout << "[ETCD-TLS-DESACTIVADO] tls.modo=http: HTTP en claro, SIN autenticación ni autorización. Solo "
                     "para la transición (defender hasta el paso 6 de DEBT-ETCD-HA-TLS-RAFT-001)" << std::endl;
    }
    configurar_rutas();
    return true;
}

void EtcdServer::start() {
    if (running_) {
        std::cout << "[ETCD-SERVER] ⚠️  Servidor ya está ejecutándose" << std::endl;
        return;
    }

    if (!server_) {
        std::cerr << "[ETCD-SERVER] ❌ start() sin initialize() correcto: no hay servidor que arrancar" << std::endl;
        return;
    }
    running_ = true;
    server_thread_ = std::thread(&EtcdServer::run_server, this);
    std::cout << "[ETCD-SERVER] 🚀 Servidor iniciado" << std::endl;
}

void EtcdServer::stop() {
    if (!running_) return;

    running_ = false;
    // [ETCD-AUTHZ-D313] sin esto listen() no vuelve nunca y el join se queda colgado
    if (server_) server_->stop();
    if (server_thread_.joinable()) {
        server_thread_.join();
    }
    std::cout << "[ETCD-SERVER] 🛑 Servidor detenido" << std::endl;
}

bool EtcdServer::register_component(const std::string& component_name, const std::string& config_json) {
    try {
        return component_registry_->registro().registrar(component_name, json::parse(config_json)) ==
               argus::registro::Resultado::Ok;
    } catch (const std::exception&) {
        return false;
    }
}

bool EtcdServer::update_heartbeat(const std::string& component_name) {
    std::time_t t = 0;
    return component_registry_->registro().latir(component_name, t) == argus::registro::Resultado::Ok;
}

// ── Epoch management (ADR-045 v2 — DAY 164) ──────────────────────────────────
// [ETCD-REGISTRO-D313] la época se guarda en el almacén (clave "epoca"); si nunca se guardó, la de defecto
bool EtcdServer::set_epoch(uint16_t epoch_id, const std::string& not_before) {
    std::lock_guard<std::mutex> lk(epoch_mutex_);
    EpochInfo ep = epoch_;
    nlohmann::json j;
    if (component_registry_->registro().leer_epoca(j) == argus::registro::Resultado::Ok)
        ep.revision = j.value("revision", ep.revision);
    ep.epoch_id = epoch_id;
    ep.not_before = not_before;
    ep.revision++;
    const nlohmann::json nueva = {{"epoch_id", ep.epoch_id}, {"not_before", ep.not_before}, {"revision", ep.revision}};
    if (component_registry_->registro().guardar_epoca(nueva) != argus::registro::Resultado::Ok) return false;
    epoch_ = ep;
    return true;
}

EtcdServer::EpochInfo EtcdServer::get_epoch() const {
    std::lock_guard<std::mutex> lk(epoch_mutex_);
    EpochInfo ep = epoch_;
    nlohmann::json j;
    if (component_registry_->registro().leer_epoca(j) == argus::registro::Resultado::Ok) {
        ep.epoch_id = j.value("epoch_id", ep.epoch_id);
        ep.not_before = j.value("not_before", ep.not_before);
        ep.revision = j.value("revision", ep.revision);
    }
    return ep;
}

void EtcdServer::configurar_rutas() {
    httplib::Server& server = *server_;
    const bool con_tls = (tls_.modo == "mtls");

    // [ETCD-AUTHZ-D313] un único punto de autorización antes del enrutado. Solo con mTLS (en http no hay identidad).
    if (con_tls) {
        server.set_pre_routing_handler([this](const httplib::Request& req, httplib::Response& res) {
            const auto id = identidad_de_peticion(req);
            const auto d = argus::etcdauthz::decidir(reglas_, req.method, req.path, id);
            if (d.permitido) return httplib::Server::HandlerResponse::Unhandled;
            using argus::etcdauthz::para_log;
            std::cout << "[ETCD-AUTHZ-DENEGADO] cn=" << (id.valida ? id.cn : "?") << " ou=" << (id.valida ? id.ou : "?")
                      << " metodo=" << para_log(req.method, 16) << " ruta=" << para_log(req.path)
                      << " motivo=" << d.motivo << std::endl;
            res.status = 403;
            res.set_content(R"({"status": "error", "message": "prohibido"})", "application/json");
            return httplib::Server::HandlerResponse::Handled;
        });
    }
    server.set_logger([con_tls](const httplib::Request& req, const httplib::Response& res) {
        log_request(req, res, con_tls);
    });

    // [ETCD-REGISTRO-D313] traducción común de Resultado a HTTP
    auto error = [](httplib::Response& res, int status, const std::string& mensaje) {
        res.status = status;
        res.set_content(json{{"status", "error"}, {"message", mensaje}}.dump(), "application/json");
    };
    auto fallo = [error](httplib::Response& res, argus::registro::Resultado r, const std::string& nombre) {
        using argus::registro::Resultado;
        switch (r) {
            case Resultado::NoEncontrado: error(res, 404, "Componente no registrado: " + nombre); break;
            case Resultado::NoDisponible: error(res, 503, "almacén del registro no disponible"); break;
            case Resultado::NombreInvalido: error(res, 400, "nombre de componente mal formado ([a-z0-9-]{1,63})"); break;
            case Resultado::DocumentoInvalido: error(res, 400, "documento del componente sin campo 'component'"); break;
            case Resultado::Ok: break;
        }
    };
    // [ETCD-REGISTRO-D313] con mTLS, el nombre del cuerpo de /register y /unregister debe ser el CN (B3 DAY312)
    auto nombre_es_cn = [this, con_tls](const httplib::Request& req, httplib::Response& res, const std::string& nombre) {
        if (!con_tls) return true;
        const auto id = identidad_de_peticion(req);
        if (id.valida && id.cn == nombre) return true;
        using argus::etcdauthz::para_log;
        std::cout << "[ETCD-AUTHZ-DENEGADO] cn=" << (id.valida ? id.cn : "?") << " ou=" << (id.valida ? id.ou : "?")
                  << " metodo=" << para_log(req.method, 16) << " ruta=" << para_log(req.path)
                  << " motivo=el nombre del cuerpo (" << para_log(nombre, 64) << ") no es el CN" << std::endl;
        res.status = 403;
        res.set_content(R"({"status": "error", "message": "prohibido: el nombre no es el del certificado"})",
                        "application/json");
        return false;
    };

    // Endpoint de registro de componentes
    server.Post("/register", [this, error, fallo, nombre_es_cn](const httplib::Request& req, httplib::Response& res) {
        json body;
        try {
            body = json::parse(req.body);
        } catch (const std::exception& e) {
            error(res, 400, std::string("JSON inválido: ") + e.what());
            return;
        }
        if (!body.is_object() || !body.contains("component") || !body["component"].is_string()) {
            error(res, 400, "Campo 'component' requerido");
            return;
        }
        const std::string component_name = body["component"];
        if (!nombre_es_cn(req, res, component_name)) return;
        const auto r = component_registry_->registro().registrar(component_name, body);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component_name);
            return;
        }
        // Extract component short name (e.g., "firewall-acl-agent" -> "firewall")
        std::string short_name = component_name;
        size_t dash_pos = component_name.find('-');
        if (dash_pos != std::string::npos) short_name = component_name.substr(0, dash_pos);
        json response = {
            {"status", "success"},
            {"message", "Componente registrado correctamente"},
            {"component", component_name},
            {"paths", {
                {"hmac_key", "/secrets/" + short_name},
                {"crypto_token", "/crypto/" + short_name + "/tokens"},
                {"config", "/config/" + short_name}
            }}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Endpoint para desregistrar componentes
    server.Post("/unregister", [this, error, fallo, nombre_es_cn](const httplib::Request& req, httplib::Response& res) {
        json body;
        try {
            body = json::parse(req.body);
        } catch (const std::exception& e) {
            error(res, 400, std::string("JSON inválido: ") + e.what());
            return;
        }
        if (!body.is_object() || !body.contains("component") || !body["component"].is_string()) {
            error(res, 400, "Campo 'component' requerido");
            return;
        }
        const std::string component_name = body["component"];
        if (!nombre_es_cn(req, res, component_name)) return;
        const auto r = component_registry_->registro().desregistrar(component_name);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component_name);
            return;
        }
        json response = {
            {"status", "success"},
            {"message", "Componente desregistrado correctamente"},
            {"component", component_name},
            {"remaining_components", component_registry_->registro().cuenta()}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Endpoint para listar componentes registrados (de etcd; si no responde, de la copia: lo dice "desde_copia")
    server.Get("/components", [this](const httplib::Request& /*req*/, httplib::Response& res) {
        std::vector<std::string> components;
        bool desde_copia = false;
        component_registry_->registro().listar(components, desde_copia);
        json response = {
            {"status", "success"},
            {"component_count", components.size()},
            {"components", components},
            {"desde_copia", desde_copia}
        };
        res.set_content(response.dump(), "application/json");
    });

    // [ETCD-AUTHZ-D313] GET /seed borrada (sin uso: day312_inventario_etcd.md); sin regla en authz -> 403
    // Endpoint de validación de configuración
    server.Get("/validate", [this](const httplib::Request& /*req*/, httplib::Response& res) {
        res.set_content(component_registry_->validate_configuration(), "application/json");
    });

    // Endpoint para obtener configuración de componente (de etcd; si no responde, de la copia)
    server.Get("/config/(.*)", [this, fallo](const httplib::Request& req, httplib::Response& res) {
        const std::string component = req.matches[1];
        json doc;
        const auto r = component_registry_->registro().leer_documento(component, doc);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component);
            return;
        }
        res.set_content(doc.dump(), "application/json");
    });

    // Endpoint para actualizar configuración
    server.Put("/config/(.*)", [this, error, fallo](const httplib::Request& req, httplib::Response& res) {
        const std::string component = req.matches[1];
        json body;
        try {
            body = json::parse(req.body);
        } catch (const std::exception& e) {
            error(res, 400, std::string("JSON inválido: ") + e.what());
            return;
        }
        if (!body.is_object() || !body.contains("path") || !body.contains("value") || !body["path"].is_string() ||
            !body["value"].is_string()) {
            error(res, 400, "Campos 'path' y 'value' (texto) requeridos");
            return;
        }
        const std::string path = body["path"];
        const std::string value = body["value"];
        const auto r = component_registry_->registro().actualizar_campo(component, path, value);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component);
            return;
        }
        json response = {
            {"status", "success"},
            {"message", "Configuración actualizada"},
            {"component", component},
            {"path", path},
            {"value", value}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Endpoint v1 para subir configuración completa (cifrada/comprimida)
    server.Put("/v1/config/(.*)", [this, error, fallo](const httplib::Request& req, httplib::Response& res) {
    std::string component = req.matches[1];
    std::cout << "[ETCD-SERVER] 📤 PUT /v1/config/" << component
              << " (" << req.body.size() << " bytes)" << std::endl;

    try {
        std::string processed_data = req.body;
        std::string content_type = req.get_header_value("Content-Type");

        // Step 1: Decrypt if encrypted (octet-stream indicates encryption)
        if (content_type == "application/octet-stream") {
            std::cout << "[ETCD-SERVER] 🔓 Descifrando datos..." << std::endl;
            processed_data = component_registry_->decrypt_data(processed_data);
            std::cout << "[ETCD-SERVER] ✅ Descifrado: " << processed_data.size() << " bytes" << std::endl;
        }

        // Step 2: Decompress if compressed (extract 4-byte header from crypto_transport format)
        std::string original_size_header = req.get_header_value("X-Original-Size");
        if (!original_size_header.empty()) {
            size_t original_size = std::stoull(original_size_header);

            // Check if data has the 4-byte LZ4 header from crypto_transport::compress()
            if (processed_data.size() >= 4) {
                // Extract original size from 4-byte big-endian header
                uint32_t header_size =
                    (static_cast<uint32_t>(static_cast<uint8_t>(processed_data[0])) << 24) |
                    (static_cast<uint32_t>(static_cast<uint8_t>(processed_data[1])) << 16) |
                    (static_cast<uint32_t>(static_cast<uint8_t>(processed_data[2])) << 8) |
                    static_cast<uint32_t>(static_cast<uint8_t>(processed_data[3]));

                std::cout << "[ETCD-SERVER] 📦 Descomprimiendo datos..." << std::endl;
                std::cout << "   Header size: " << header_size << " bytes" << std::endl;
                std::cout << "   HTTP header size: " << original_size << " bytes" << std::endl;

                // Verify header matches HTTP header
                if (header_size != original_size) {
                    std::cerr << "[ETCD-SERVER] ⚠️  Size mismatch: header=" << header_size
                              << " vs HTTP=" << original_size << std::endl;
                }

                // Extract compressed data (skip 4-byte header)
                std::string compressed_only = processed_data.substr(4);

                std::cout << "[ETCD-SERVER] 📦 Decompressing " << compressed_only.size()
                          << " bytes → " << original_size << " bytes" << std::endl;

                processed_data = compression::decompress_lz4(compressed_only, original_size);
                std::cout << "[ETCD-SERVER] ✅ Descomprimido: " << processed_data.size() << " bytes" << std::endl;
            } else {
                std::cout << "[ETCD-SERVER] ℹ️  Datos no comprimidos (tamaño: "
                          << processed_data.size() << " bytes)" << std::endl;
            }
        }

        // Step 3: Validate JSON + Step 4: Register component
        const auto parsed = json::parse(processed_data);
        const auto r = component_registry_->registro().registrar(component, parsed);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component);
            return;
        }
        json response = {
            {"status", "success"},
            {"component_id", component},
            {"size_bytes", processed_data.size()},
            {"timestamp", std::time(nullptr)}
        };
        res.set_content(response.dump(2), "application/json");
        std::cout << "[ETCD-SERVER] ✅ Config guardada para " << component << std::endl;

    } catch (const json::parse_error& e) {
        error(res, 400, std::string("Invalid JSON: ") + e.what());
    } catch (const std::exception& e) {
        error(res, 500, std::string("Internal error: ") + e.what());
    }
    });

    // Endpoint de heartbeat: 200, 404 (no registrado) o 503 (almacén no disponible); revive a un muerto
    server.Post("/v1/heartbeat/(.*)", [this, error, fallo](const httplib::Request& req, httplib::Response& res) {
        const std::string component_name = req.matches[1];
        json body;
        try {
            body = json::parse(req.body);
        } catch (const std::exception& e) {
            error(res, 400, std::string("JSON inválido: ") + e.what());
            return;
        }
        if (!body.is_object() || !body.contains("timestamp") || !body["timestamp"].is_number()) {
            error(res, 400, "Campo 'timestamp' requerido y debe ser numérico");
            return;
        }
        const std::time_t client_timestamp = body["timestamp"];
        std::time_t last_hb = 0;
        const auto r = component_registry_->registro().latir(component_name, last_hb);
        if (r != argus::registro::Resultado::Ok) {
            fallo(res, r, component_name);
            return;
        }
        const std::time_t server_time = std::time(nullptr);
        json response = {
            {"status", "ok"},
            {"component", component_name},
            {"last_heartbeat", last_hb},
            {"server_time", server_time},
            {"client_timestamp", client_timestamp},
            {"next_heartbeat_expected", server_time + heartbeat_interval_seconds_}  // heartbeat.interval_seconds
        };
        res.set_content(response.dump(), "application/json");
    });

    server.Get("/v1/epoch", [this](const httplib::Request& /*req*/, httplib::Response& res) {
        auto ep = get_epoch();
        nlohmann::json j;
        j["epoch_id"]   = ep.epoch_id;
        j["not_before"] = ep.not_before;
        j["revision"]   = ep.revision;
        res.set_content(j.dump(), "application/json");
    });

    server.Put("/v1/epoch", [this, error](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j          = nlohmann::json::parse(req.body);
            uint16_t eid    = j.at("epoch_id").get<uint16_t>();
            std::string nb  = j.at("not_before").get<std::string>();
            if (!set_epoch(eid, nb)) {
                error(res, 503, "almacén del registro no disponible");
                return;
            }
            nlohmann::json resp;
            resp["status"]   = "ok";
            resp["epoch_id"] = eid;
            res.set_content(resp.dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 400;
            res.set_content(R"({"status":"error"})", "application/json");
        }
    });

    server.Get("/health", [](const httplib::Request& /*req*/, httplib::Response& res) {
        json response = {
            {"status", "healthy"},
            {"service", "etcd-server"},
            {"timestamp", time(nullptr)}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Endpoint de información del sistema
    server.Get("/info", [this](const httplib::Request& /*req*/, httplib::Response& res) {
        json response = {
            {"status", "success"},
            {"service", "etcd-server"},
            {"version", "1.0.0"},
            {"components_registered", component_registry_->registro().cuenta()},
            {"almacen_disponible", component_registry_->registro().almacen_disponible()},
            {"port", port_}
        };
        res.set_content(response.dump(), "application/json");
    });

    // ============================================================================
// SECRETS ENDPOINTS (Day 55 - ACTIVE)
// ============================================================================

// [ETCD-AUTHZ-D313] GET /secrets/keys borrada (sin uso: day312_inventario_etcd.md); sin regla en authz -> 403

// [ETCD-CLAVES-D314] Rutas de claves sobre SecretsManager con ventana de dos persistida (Vault | memoria de transición).
// Mismo formato de respuesta que antes, más "huella" (8 hex) y "desde_copia" (almacén caído: última ventana conocida).
// 503 = almacén de claves no disponible y sin copia (nunca se genera una clave que no quede guardada); 409 = otra
// instancia rotó a la vez; 429 = enfriamiento. En el log solo la huella.
auto clave_json = [](const etcd_server::ClaveHMAC& k) {
    return json{{"key", k.hex},
                {"huella", k.huella},
                {"created_at", etcd_server::SecretsManager::iso(k.creada)},
                {"expires_at", k.expira == 0 ? std::string() : etcd_server::SecretsManager::iso(k.expira)},
                {"is_active", k.activa}};
};
auto responder_error = [](httplib::Response& res, int status, const std::string& msg) {
    res.status = status;
    res.set_content(json{{"status", "error"}, {"message", msg}}.dump(), "application/json");
};
const std::string kSinAlmacen =
    "almacén de claves no disponible y sin copia de la clave (no se genera una clave que no quede guardada)";

// Endpoint: GET /secrets/{component} - clave activa (hex); la crea si es la primera vez
server.Get(R"(/secrets/([^/]+))", [this, clave_json, responder_error, kSinAlmacen](const httplib::Request& req,
                                                                                    httplib::Response& res) {
    const std::string component = req.matches[1];
    if (!secrets_manager_) return responder_error(res, 503, "SecretsManager not initialized");
    etcd_server::ClaveHMAC k;
    bool copia = false;
    switch (secrets_manager_->activa(component, k, copia)) {
        case etcd_server::ResultadoClaves::Ok: {
            json r = clave_json(k);
            r["status"] = "success";
            r["component"] = component;
            r["desde_copia"] = copia;
            r.erase("expires_at");
            res.set_content(r.dump(), "application/json");
            std::cout << "[ETCD-SERVER] clave activa de " << component << " (huella " << k.huella << ")"
                      << (copia ? " DESDE LA COPIA (almacén de claves no disponible)" : "") << std::endl;
            return;
        }
        case etcd_server::ResultadoClaves::NombreInvalido: return responder_error(res, 400, "nombre de componente inválido");
        default:
            std::cerr << "[ETCD-SERVER] GET /secrets/" << component << ": 503 (" << kSinAlmacen << ")" << std::endl;
            return responder_error(res, 503, kSinAlmacen);
    }
});

// Endpoint: POST /secrets/rotate/{component}[?force=true] - rotar con ventana de dos
server.Post(R"(/secrets/rotate/([^/]+))", [this, clave_json, responder_error](const httplib::Request& req,
                                                                             httplib::Response& res) {
    const std::string component = req.matches[1];
    const bool force = req.has_param("force") && req.get_param_value("force") == "true";
    if (!secrets_manager_) return responder_error(res, 503, "SecretsManager not initialized");
    etcd_server::ClaveHMAC k;
    int reintentar = 0;
    switch (secrets_manager_->rotar(component, force, k, reintentar)) {
        case etcd_server::ResultadoClaves::Ok: {
            std::vector<etcd_server::ClaveHMAC> v;
            bool copia = false;
            secrets_manager_->validas(component, v, copia);
            json nk = clave_json(k);
            nk.erase("expires_at");
            const int g = secrets_manager_->get_grace_period_seconds();
            res.set_content(json{{"status", "success"},
                                 {"component", component},
                                 {"new_key", nk},
                                 {"valid_keys_count", v.size()},
                                 {"grace_period_seconds", g},
                                 {"message", "Old key valid for " + std::to_string(g) + " seconds"},
                                 {"forced", force}}
                                .dump(),
                            "application/json");
            return;
        }
        case etcd_server::ResultadoClaves::Enfriamiento: {
            res.status = 429;
            res.set_header("Retry-After", std::to_string(reintentar));
            res.set_content(json{{"status", "error"},
                                 {"message", "Rotation cooldown active"},
                                 {"retry_after_seconds", reintentar}}
                                .dump(),
                            "application/json");
            return;
        }
        case etcd_server::ResultadoClaves::Conflicto:
            return responder_error(res, 409, "otra instancia rotó la clave a la vez; volver a leerla");
        case etcd_server::ResultadoClaves::NombreInvalido: return responder_error(res, 400, "nombre de componente inválido");
        default:
            std::cerr << "[ETCD-SERVER] POST /secrets/rotate/" << component << ": 503 (sin almacén de claves no se rota)"
                      << std::endl;
            return responder_error(res, 503, "almacén de claves no disponible: no se rota");
    }
});

// Endpoint: GET /secrets/valid/{component} - activa + anterior si no ha caducado
server.Get(R"(/secrets/valid/([^/]+))", [this, clave_json, responder_error, kSinAlmacen](const httplib::Request& req,
                                                                                          httplib::Response& res) {
    const std::string component = req.matches[1];
    if (!secrets_manager_) return responder_error(res, 503, "SecretsManager not initialized");
    std::vector<etcd_server::ClaveHMAC> v;
    bool copia = false;
    switch (secrets_manager_->validas(component, v, copia)) {
        case etcd_server::ResultadoClaves::Ok: {
            json arr = json::array();
            std::string huellas;
            for (const auto& k : v) {
                arr.push_back(clave_json(k));
                if (!huellas.empty()) huellas += ',';
                huellas += k.huella;
            }
            res.set_content(json{{"status", "success"},
                                 {"component", component},
                                 {"valid_keys_count", v.size()},
                                 {"desde_copia", copia},
                                 {"keys", arr}}
                                .dump(),
                            "application/json");
            std::cout << "[ETCD-SERVER] claves válidas de " << component << ": " << v.size() << " (" << huellas << ")"
                      << (copia ? " DESDE LA COPIA" : "") << std::endl;
            return;
        }
        case etcd_server::ResultadoClaves::NombreInvalido: return responder_error(res, 400, "nombre de componente inválido");
        default: return responder_error(res, 503, kSinAlmacen);
    }
});

}

void EtcdServer::run_server() {
    std::cout << "[ETCD-SERVER] 🌐 Iniciando servidor " << (tls_.modo == "mtls" ? "HTTPS (mTLS)" : "HTTP (SIN TLS)")
              << " en " << host_ << ":" << port_ << std::endl;

    try {
        if (!server_->listen(host_, port_)) {
            std::cerr << "[ETCD-SERVER] ❌ Error iniciando servidor en " << host_ << ":" << port_ << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ETCD-SERVER] 💥 Excepción en servidor: " << e.what() << std::endl;
    }

    running_ = false;
    std::cout << "[ETCD-SERVER] 📡 Servidor terminado" << std::endl;
}