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

// ============================================================================
// Day 62: Contextual request logging helper
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

static void log_request(const httplib::Request& req, int status,
                        const std::string& context = "") {
    std::string component = req.get_header_value("X-Component-Name");
    std::string client_ts  = req.get_header_value("X-Request-Timestamp");
    if (component.empty()) component = "unknown";
    if (client_ts.empty())  client_ts  = "unknown";
    std::cout << "[ETCD←] " << req.method << " " << req.path
              << " | status=" << status
              << " | component=" << component
              << " | client_ts=" << client_ts
              << " | server_ts=" << server_iso8601_now()
              << (context.empty() ? "" : " | " + context)
              << std::endl;
}
// etcd-server/src/etcd_server.cpp
using json = nlohmann::json;

EtcdServer::EtcdServer(int port) : port_(port) {
    component_registry_ = std::make_unique<ComponentRegistry>();
}

EtcdServer::~EtcdServer() {
    stop();
}

bool EtcdServer::initialize() {
    std::cout << "[ETCD-SERVER] 🔧 Inicializando servidor en puerto " << port_ << std::endl;
    return true;
}

void EtcdServer::start() {
    if (running_) {
        std::cout << "[ETCD-SERVER] ⚠️  Servidor ya está ejecutándose" << std::endl;
        return;
    }

    running_ = true;
    server_thread_ = std::thread(&EtcdServer::run_server, this);
    std::cout << "[ETCD-SERVER] 🚀 Servidor iniciado" << std::endl;
}

void EtcdServer::stop() {
    if (!running_) return;

    running_ = false;
    if (server_thread_.joinable()) {
        server_thread_.join();
    }
    std::cout << "[ETCD-SERVER] 🛑 Servidor detenido" << std::endl;
}

bool EtcdServer::register_component(const std::string& component_name, const std::string& config_json) {
    return component_registry_->register_component(component_name, config_json);
}

std::string EtcdServer::get_component_config(const std::string& component_name) {
    return component_registry_->get_component_config(component_name);
}

bool EtcdServer::update_component_config(const std::string& component_name, const std::string& config_path, const std::string& value) {
    return component_registry_->update_component_config(component_name, config_path, value);
}

std::string EtcdServer::validate_configuration() {
    return component_registry_->validate_configuration();
}

void EtcdServer::run_server() {
    httplib::Server server;

    // Endpoint de registro de componentes
    server.Post("/register", [this](const httplib::Request& req, httplib::Response& res) {
        log_request(req, 200, "register");

        try {
            auto json_body = json::parse(req.body);

            if (!json_body.contains("component") || !json_body["component"].is_string()) {
                res.status = 400;
                res.set_content(R"({"status": "error", "message": "Campo 'component' requerido"})", "application/json");
                return;
            }

            std::string component_name = json_body["component"];

            if (component_registry_->register_component(component_name, req.body)) {
                // Extract component short name (e.g., "firewall-acl-agent" -> "firewall")
                std::string short_name = component_name;
                size_t dash_pos = component_name.find('-');
                if (dash_pos != std::string::npos) {
                    short_name = component_name.substr(0, dash_pos);
                }

                json response = {
                    {"status", "success"},
                    {"message", "Componente registrado correctamente"},
                    {"component", component_name},
                    {"encryption_key", component_registry_->get_encryption_key()},
                    {"paths", {
                        {"hmac_key", "/secrets/" + short_name},
                        {"crypto_token", "/crypto/" + short_name + "/tokens"},
                        {"config", "/config/" + short_name}
                    }}
                };
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 400;
                res.set_content(R"({"status": "error", "message": "Error en el registro"})", "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {
                {"status", "error"},
                {"message", "JSON inválido"},
                {"details", e.what()}
            };
            res.set_content(error.dump(), "application/json");
        }
    });

    // Endpoint para desregistrar componentes - IMPLEMENTACIÓN REAL
    server.Post("/unregister", [this](const httplib::Request& req, httplib::Response& res) {
        log_request(req, 200, "unregister");

        try {
            auto json_body = json::parse(req.body);

            if (!json_body.contains("component") || !json_body["component"].is_string()) {
                res.status = 400;
                res.set_content(R"({"status": "error", "message": "Campo 'component' requerido"})", "application/json");
                return;
            }

            std::string component_name = json_body["component"];

            // Usar el método real de desregistro del ComponentRegistry
            if (component_registry_->unregister_component(component_name)) {
                json response = {
                    {"status", "success"},
                    {"message", "Componente desregistrado correctamente"},
                    {"component", component_name},
                    {"remaining_components", component_registry_->get_component_count()}
                };
                res.set_content(response.dump(), "application/json");
                std::cout << "[ETCD-SERVER] ✅ Desregistro completado para: " << component_name << std::endl;
            } else {
                res.status = 404;
                json error = {
                    {"status", "error"},
                    {"message", "Componente no encontrado: " + component_name}
                };
                res.set_content(error.dump(), "application/json");
                std::cout << "[ETCD-SERVER] ❌ Componente no encontrado: " << component_name << std::endl;
            }

        } catch (const std::exception& e) {
            res.status = 400;
            json error = {
                {"status", "error"},
                {"message", "JSON inválido"},
                {"details", e.what()}
            };
            res.set_content(error.dump(), "application/json");
            std::cerr << "[ETCD-SERVER] ❌ Error en /unregister: " << e.what() << std::endl;
        }
    });

    // Endpoint para listar componentes registrados
    server.Get("/components", [this](const httplib::Request& req, httplib::Response& res) {
        log_request(req, 200, "list_components");

        auto components = component_registry_->get_registered_components();
        json response = {
            {"status", "success"},
            {"component_count", components.size()},
            {"components", components}
        };
        res.set_content(response.dump(), "application/json");
        std::cout << "[ETCD-SERVER] 📊 Listando " << components.size() << " componentes" << std::endl;
    });

    // Endpoint para obtener seed de cifrado
    server.Get("/seed", [this](const httplib::Request& req, httplib::Response& res) {
        log_request(req, 200, "seed");

        std::string seed = component_registry_->get_encryption_seed();
        json response = {
            {"status", "success"},
            {"seed", seed}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Endpoint de validación de configuración
    server.Get("/validate", [this](const httplib::Request& req, httplib::Response& res) {
        log_request(req, 200, "validate");

        std::string validation = component_registry_->validate_configuration();
        res.set_content(validation, "application/json");
    });

    // Endpoint para obtener configuración de componente
    server.Get("/config/(.*)", [this](const httplib::Request& req, httplib::Response& res) {
        std::string component = req.matches[1];
        log_request(req, 200, "get_config:" + component);

        std::string config = component_registry_->get_component_config(component);
        if (config == "{}") {
            res.status = 404;
            json error = {
                {"status", "error"},
                {"message", "Componente no encontrado: " + component}
            };
            res.set_content(error.dump(), "application/json");
        } else {
            res.set_content(config, "application/json");
        }
    });

    // Endpoint para actualizar configuración
    server.Put("/config/(.*)", [this](const httplib::Request& req, httplib::Response& res) {
        std::string component = req.matches[1];
        log_request(req, 200, "put_config:" + component);

        try {
            auto json_body = json::parse(req.body);

            if (!json_body.contains("path") || !json_body.contains("value")) {
                res.status = 400;
                res.set_content(R"({"status": "error", "message": "Campos 'path' y 'value' requeridos"})", "application/json");
                return;
            }

            std::string path = json_body["path"];
            std::string value = json_body["value"];

            if (component_registry_->update_component_config(component, path, value)) {
                json response = {
                    {"status", "success"},
                    {"message", "Configuración actualizada"},
                    {"component", component},
                    {"path", path},
                    {"value", value}
                };
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 400;
                res.set_content(R"({"status", "error", "message": "Error actualizando configuración"})", "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {
                {"status", "error"},
                {"message", "JSON inválido"},
                {"details", e.what()}
            };
            res.set_content(error.dump(), "application/json");
        }
    });

    // Endpoint v1 para subir configuración completa (cifrada/comprimida)
server.Put("/v1/config/(.*)", [this](const httplib::Request& req, httplib::Response& res) {
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

        // Step 3: Validate JSON
        auto parsed = json::parse(processed_data);

        // Step 4: Register component
        if (component_registry_->register_component(component, processed_data)) {
            json response = {
                {"status", "success"},
                {"component_id", component},
                {"size_bytes", processed_data.size()},
                {"timestamp", std::time(nullptr)}
            };
            res.set_content(response.dump(2), "application/json");
            std::cout << "[ETCD-SERVER] ✅ Config guardada para " << component << std::endl;
        } else {
            res.status = 500;
            json error = {
                {"status", "error"},
                {"message", "Error guardando configuración"}
            };
            res.set_content(error.dump(), "application/json");
        }

    } catch (const json::parse_error& e) {
        res.status = 400;
        json error = {
            {"status", "error"},
            {"error", "Invalid JSON"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
    } catch (const std::exception& e) {
        res.status = 500;
        json error = {
            {"status", "error"},
            {"error", "Internal error"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
    }
});

    // Endpoint de heartbeat - Añadir después del endpoint /v1/config
server.Post("/v1/heartbeat/(.*)", [this](const httplib::Request& req, httplib::Response& res) {
    std::string component_name = req.matches[1];
    log_request(req, 200, "heartbeat:" + component_name);

    try {
        auto json_body = json::parse(req.body);

        if (!json_body.contains("timestamp") || !json_body["timestamp"].is_number()) {
            res.status = 400;
            json error = {
                {"status", "error"},
                {"message", "Campo 'timestamp' requerido y debe ser numérico"}
            };
            res.set_content(error.dump(), "application/json");
            return;
        }

        std::time_t client_timestamp = json_body["timestamp"];

        // Actualizar heartbeat
        if (component_registry_->update_heartbeat(component_name)) {
            std::time_t server_time = std::time(nullptr);
            std::time_t last_hb = component_registry_->get_last_heartbeat(component_name);

            json response = {
                {"status", "ok"},
                {"component", component_name},
                {"last_heartbeat", last_hb},
                {"server_time", server_time},
                {"client_timestamp", client_timestamp},
                {"next_heartbeat_expected", server_time + 30}  // Hardcoded por ahora
            };
            res.set_content(response.dump(), "application/json");
            std::cout << "[ETCD-SERVER] ✅ Heartbeat registrado para: " << component_name << std::endl;
        } else {
            res.status = 404;
            json error = {
                {"status", "error"},
                {"message", "Componente no registrado: " + component_name}
            };
            res.set_content(error.dump(), "application/json");
            std::cout << "[ETCD-SERVER] ❌ Componente no encontrado: " << component_name << std::endl;
        }

    } catch (const json::parse_error& e) {
        res.status = 400;
        json error = {
            {"status", "error"},
            {"message", "JSON inválido"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
    } catch (const std::exception& e) {
        res.status = 500;
        json error = {
            {"status", "error"},
            {"message", "Error interno"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
    }
});

    // Endpoint de salud
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
            {"components_registered", component_registry_->get_component_count()},
            {"port", port_}
        };
        res.set_content(response.dump(), "application/json");
    });

    // ============================================================================
// SECRETS ENDPOINTS (Day 55 - ACTIVE)
// ============================================================================

// Endpoint: GET /secrets/keys - List all components with HMAC keys
server.Get("/secrets/keys", [this](const httplib::Request& req, httplib::Response& res) {
    log_request(req, 200, "secrets_keys");

    if (!secrets_manager_) {
        res.status = 503;
        json error = {
            {"status", "error"},
            {"message", "SecretsManager not initialized"}
        };
        res.set_content(error.dump(), "application/json");
        return;
    }

    // TODO Day 56: Implementar listado de todos los componentes
    // Por ahora devolvemos instrucciones de uso
    json response = {
        {"status", "success"},
        {"message", "Use GET /secrets/{component} to get active key"},
        {"endpoints", {
            {"get_key", "GET /secrets/{component}"},
            {"rotate_key", "POST /secrets/rotate/{component}"},
            {"valid_keys", "GET /secrets/valid/{component}"}
        }}
    };
    res.set_content(response.dump(), "application/json");
});

// Endpoint: GET /secrets/{component} - Get active HMAC key (hex-encoded)
server.Get(R"(/secrets/([^/]+))", [this](const httplib::Request& req, httplib::Response& res) {
    std::string component = req.matches[1];
    std::cout << "[ETCD-SERVER] 🔑 GET /secrets/" << component << " solicitado" << std::endl;

    if (!secrets_manager_) {
        res.status = 503;
        json error = {
            {"status", "error"},
            {"message", "SecretsManager not initialized"}
        };
        res.set_content(error.dump(), "application/json");
        return;
    }

    try {
        auto key = secrets_manager_->get_hmac_key(component);

        json response = {
            {"status", "success"},
            {"component", component},
            {"key", key.key_data},  // Hex-encoded
            {"created_at", secrets_manager_->format_time(key.created_at)},
            {"is_active", key.is_active}
        };
        res.set_content(response.dump(), "application/json");

        std::cout << "[ETCD-SERVER] ✅ Devuelta clave activa para: " << component << std::endl;

    } catch (const std::exception& e) {
        res.status = 500;
        json error = {
            {"status", "error"},
            {"message", "Error retrieving HMAC key"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
        std::cerr << "[ETCD-SERVER] ❌ Error en GET /secrets/" << component << ": " << e.what() << std::endl;
    }
});

// Endpoint: POST /secrets/rotate/{component} - Rotate HMAC key with grace period
server.Post(R"(/secrets/rotate/([^/]+))", [this](const httplib::Request& req, httplib::Response& res) {
    std::string component = req.matches[1];
    bool force = req.has_param("force") && req.get_param_value("force") == "true";

    std::cout << "[ETCD-SERVER] 🔄 POST /secrets/rotate/" << component
              << (force ? " (FORCE)" : "") << std::endl;

    if (!secrets_manager_) {
        res.status = 503;
        json error = {
            {"status", "error"},
            {"message", "SecretsManager not initialized"}
        };
        res.set_content(error.dump(), "application/json");
        return;
    }

    try {
        auto new_key = secrets_manager_->rotate_hmac_key(component, force);
        auto valid_keys = secrets_manager_->get_valid_keys(component);

        json response = {
            {"status", "success"},
            {"component", component},
            {"new_key", {
                {"key", new_key.key_data},
                {"created_at", secrets_manager_->format_time(new_key.created_at)},
                {"is_active", true}
            }},
            {"valid_keys_count", valid_keys.size()},
            {"grace_period_seconds", secrets_manager_->get_grace_period_seconds()},
            {"message", "Old key valid for " + std::to_string(secrets_manager_->get_grace_period_seconds()) + " seconds"},
            {"forced", force}
        };
        res.set_content(response.dump(), "application/json");

        std::cout << "[ETCD-SERVER] ✅ Rotación completada para: " << component
                  << " (" << valid_keys.size() << " claves válidas)" << std::endl;

    } catch (const std::runtime_error& e) {
        // Check if it's a cooldown violation
        std::string error_msg(e.what());
        if (error_msg.find("Rotation too soon") != std::string::npos) {
            // Extract retry seconds from message
            size_t pos = error_msg.find("retry in ");
            int retry_seconds = 240;  // default
            if (pos != std::string::npos) {
                retry_seconds = std::stoi(error_msg.substr(pos + 9));
            }

            res.status = 429;  // Too Many Requests
            json error = {
                {"status", "error"},
                {"message", "Rotation cooldown active"},
                {"details", error_msg},
                {"retry_after_seconds", retry_seconds}
            };
            res.set_header("Retry-After", std::to_string(retry_seconds));
            res.set_content(error.dump(), "application/json");

            std::cout << "[ETCD-SERVER] ⏳ Rotación rechazada (cooldown): " << component << std::endl;
        } else {
            // Other runtime errors
            res.status = 500;
            json error = {
                {"status", "error"},
                {"message", "Error rotating HMAC key"},
                {"details", e.what()}
            };
            res.set_content(error.dump(), "application/json");
            std::cerr << "[ETCD-SERVER] ❌ Error en POST /secrets/rotate/" << component << ": " << e.what() << std::endl;
        }
    }
});

// Endpoint: GET /secrets/valid/{component} - Get all valid keys (active + grace period)
server.Get(R"(/secrets/valid/([^/]+))", [this](const httplib::Request& req, httplib::Response& res) {
    std::string component = req.matches[1];
    std::cout << "[ETCD-SERVER] 🔑 GET /secrets/valid/" << component << " solicitado" << std::endl;

    if (!secrets_manager_) {
        res.status = 503;
        json error = {
            {"status", "error"},
            {"message", "SecretsManager not initialized"}
        };
        res.set_content(error.dump(), "application/json");
        return;
    }

    try {
        auto valid_keys = secrets_manager_->get_valid_keys(component);

        json keys_array = json::array();
        for (const auto& key : valid_keys) {
            keys_array.push_back({
                {"key", key.key_data},
                {"created_at", secrets_manager_->format_time(key.created_at)},
                {"expires_at", secrets_manager_->format_time(key.expires_at)},
                {"is_active", key.is_active}
            });
        }

        json response = {
            {"status", "success"},
            {"component", component},
            {"valid_keys_count", valid_keys.size()},
            {"keys", keys_array}
        };
        res.set_content(response.dump(), "application/json");

        std::cout << "[ETCD-SERVER] ✅ Devueltas " << valid_keys.size() << " claves válidas para: " << component << std::endl;

    } catch (const std::exception& e) {
        res.status = 500;
        json error = {
            {"status", "error"},
            {"message", "Error retrieving valid keys"},
            {"details", e.what()}
        };
        res.set_content(error.dump(), "application/json");
        std::cerr << "[ETCD-SERVER] ❌ Error en GET /secrets/valid/" << component << ": " << e.what() << std::endl;
    }
});

    std::cout << "[ETCD-SERVER] 🌐 Iniciando servidor HTTP en 0.0.0.0:" << port_ << std::endl;

    try {
        if (!server.listen("0.0.0.0", port_)) {
            std::cerr << "[ETCD-SERVER] ❌ Error iniciando servidor en puerto " << port_ << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ETCD-SERVER] 💥 Excepción en servidor: " << e.what() << std::endl;
    }

    running_ = false;
    std::cout << "[ETCD-SERVER] 📡 Servidor HTTP terminado" << std::endl;
}