#include "etcd_client.hpp"
#include <etcd_client/etcd_client.hpp>
#include <nlohmann/json.hpp>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <iostream>

namespace ml_detector {

// ============================================================================
// Implementación del Adapter (PIMPL)
// ============================================================================

struct EtcdClient::Impl {
    std::unique_ptr<etcd_client::EtcdClient> client_;
    std::string endpoint_;
    std::string component_name_;
    std::string host_;
    int port_;

    Impl(const std::string& endpoint, const std::string& component_name)
        : endpoint_(endpoint), component_name_(component_name) {

        // Parse endpoint (formato: "host:port" o "http://host:port")
        parseEndpoint(endpoint);

        // Configurar etcd-client
        etcd_client::Config config;
        config.component_name = component_name;
        config.host = host_;
        config.port = port_;
        config.encryption_enabled = (endpoint.find("http://") != 0);
        config.compression_enabled = true;
        // component_config_path solo cuando encryption activo (seed no disponible en tests)
        if (config.encryption_enabled) {
            config.component_config_path = "/etc/ml-defender/ml-detector/ml_detector_config.json";
        }
        // INVARIANT (ADR-027): encryption_enabled requiere component_config_path.
        // Sin él, SeedClient no inicializa, datos van en claro → MAC failure garantizado.
        if (config.encryption_enabled && config.component_config_path.empty()) {
            if (getenv("MLD_ALLOW_UNCRYPTED")) {
                std::cerr << "FATAL[DEV]: encryption_enabled pero component_config_path vacio. "
                          << "MLD_ALLOW_UNCRYPTED activo - continuando sin cifrado. "
                          << "NUNCA en produccion.\n";
                return; // constructor: continuar sin cifrado en dev mode
            } else {
                std::terminate(); // FATAL: produccion - fallo total garantizado
            }
        }
        client_ = std::make_unique<etcd_client::EtcdClient>(config);
        client_->connect();
    }

    void parseEndpoint(const std::string& endpoint) {
        // Remover http:// si existe
        std::string clean_endpoint = endpoint;
        if (endpoint.find("http://") == 0) {
            clean_endpoint = endpoint.substr(7);
        }

        // Buscar ':'
        size_t colon_pos = clean_endpoint.find(':');
        if (colon_pos != std::string::npos) {
            host_ = clean_endpoint.substr(0, colon_pos);
            port_ = std::stoi(clean_endpoint.substr(colon_pos + 1));
        } else {
            host_ = clean_endpoint;
            port_ = 2379; // Puerto por defecto
        }

        std::cout << "📡 [ml-detector] Parsed endpoint: " << host_ << ":" << port_ << std::endl;
    }

    std::string get_hmac_key() {
        if (!client_) {
            std::cerr << "[etcd] Client not initialized" << std::endl;
            return "";
        }
        std::string key_path = "/secrets/" + component_name_;
        auto result = client_->get_hmac_key(key_path);
        if (!result.has_value() || result->empty()) {
            std::cerr << "[etcd] Failed to get HMAC key from " << key_path << std::endl;
            return "";
        }
        // Convertir vector<uint8_t> a hex string
        std::ostringstream hex;
        hex << std::hex << std::setfill('0');
        for (uint8_t b : result.value()) {
            hex << std::setw(2) << static_cast<unsigned int>(b);
        }
        std::string key_hex = hex.str();
        std::cout << "[etcd] HMAC key received for " << key_path
                  << " (" << key_hex.size() << " chars)" << std::endl;
        return key_hex;
    }
};  // ← cierre de struct Impl

// ============================================================================
// Implementación pública del Adapter
// ============================================================================

EtcdClient::EtcdClient(const std::string& endpoint, const std::string& component_name)
    : pImpl(std::make_unique<Impl>(endpoint, component_name)) {
    std::cout << "🔧 [ml-detector] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

bool EtcdClient::initialize() {
    std::cout << "🔗 [ml-detector] Initializing etcd client..." << std::endl;

    // Conectar y registrar (obtiene clave automáticamente)
    if (!pImpl->client_->connect()) {
        std::cerr << "❌ [ml-detector] Failed to connect to etcd-server" << std::endl;
        return false;
    }

    std::cout << "✅ [ml-detector] Connected to etcd-server" << std::endl;
    std::cout << "🔑 [ml-detector] Encryption key received automatically" << std::endl;

    return true;
}

bool EtcdClient::registerService() {
    std::cout << "📝 [ml-detector] Registering ml-detector service in etcd..." << std::endl;

    // Cargar TODO el ml_detector_config.json
    std::ifstream config_file("config/ml_detector_config.json");
    if (!config_file.is_open()) {
        std::cerr << "❌ [ml-detector] Failed to open ml_detector_config.json" << std::endl;
        return false;
    }

    nlohmann::json full_config;
    try {
        config_file >> full_config;
    } catch (const std::exception& e) {
        std::cerr << "❌ [ml-detector] Failed to parse ml_detector_config.json: " << e.what() << std::endl;
        return false;
    }
    config_file.close();

    // Añadir metadata de registro
    full_config["_registration"] = {
        {"timestamp", std::time(nullptr)},
        {"component", pImpl->component_name_},
        {"type", "ml-detector"},
        {"status", "active"}
    };

    // Extraer capabilities para log
    std::string profile = full_config.value("profile", "unknown");
    bool level1_enabled = full_config["ml"]["level1"].value("enabled", false);
    // [DDOS-V1-RETIRE-D306] ml.level2.ddos (v1) se retiro. Sobre un JSON no constante, operator[] con una clave ausente
    // crea un null y value() lanzaria: se lee ml.ddos_v2 solo si existe. Es informativo; el estado efectivo
    // de cada cabeza lo da la linea [HEADS].
    const auto& ml_cfg = full_config["ml"];
    const bool ddos_v2_enabled = ml_cfg.contains("ddos_v2") && ml_cfg["ddos_v2"].is_object() &&
                                 ml_cfg["ddos_v2"].contains("enabled") &&
                                 ml_cfg["ddos_v2"]["enabled"].is_boolean() &&
                                 ml_cfg["ddos_v2"]["enabled"].get<bool>();
    bool ransomware_enabled = full_config["ml"]["level2"]["ransomware"].value("enabled", false);
    bool traffic_enabled = full_config["ml"]["level3"]["web"].value("enabled", false);
    bool internal_enabled = full_config["ml"]["level3"]["internal"].value("enabled", false);

    std::cout << "📋 [ml-detector] Capabilities:" << std::endl;
    std::cout << "   - Profile: " << profile << std::endl;
    std::cout << "   - Level 1 (Attack): " << (level1_enabled ? "✅" : "❌") << std::endl;
    std::cout << "   - DDoS v2: " << (ddos_v2_enabled ? "✅" : "❌") << std::endl;
    std::cout << "   - Level 2 Ransomware: " << (ransomware_enabled ? "✅" : "❌") << std::endl;
    std::cout << "   - Level 3 Traffic: " << (traffic_enabled ? "✅" : "❌") << std::endl;
    std::cout << "   - Level 3 Internal: " << (internal_enabled ? "✅" : "❌") << std::endl;
    std::cout << "   - Config Size: " << full_config.dump().size() << " bytes" << std::endl;

    // Registrar componente
    if (!pImpl->client_->register_component()) {
        std::cerr << "❌ [ml-detector] Failed to register component" << std::endl;
        return false;
    }

    // Subir config completo con put_config() (automáticamente cifrado+comprimido)
    if (!pImpl->client_->put_config(full_config.dump(2))) {
        std::cerr << "❌ [ml-detector] Failed to upload config" << std::endl;
        return false;
    }

    std::cout << "✅ [ml-detector] Service registered successfully" << std::endl;
    std::cout << "🔐 [ml-detector] Config uploaded encrypted + compressed" << std::endl;

    return true;
}

std::string EtcdClient::get_encryption_seed() const {
    if (!pImpl || !pImpl->client_) {
        std::cerr << "❌ [ml-detector] EtcdClient not initialized" << std::endl;
        return "";
    }

    std::string seed = pImpl->client_->get_encryption_key();

    if (seed.empty()) {
        std::cerr << "❌ [ml-detector] Failed to get encryption seed" << std::endl;
    } else {
        std::cout << "🔑 [ml-detector] Retrieved encryption seed ("
                  << seed.size() << " bytes)" << std::endl;
    }

    return seed;
}

std::string EtcdClient::get_hmac_key() const {
    return pImpl->get_hmac_key();
}

} // namespace ml_detector