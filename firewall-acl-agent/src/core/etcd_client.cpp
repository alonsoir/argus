#include "firewall/etcd_client.hpp"
#include <etcd_client/etcd_client.hpp>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <optional>
#include <vector>

namespace mldefender::firewall {

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
        config.encryption_enabled = true;
        config.compression_enabled = true;
        config.component_config_path = "/etc/ml-defender/firewall-acl-agent/firewall.json";
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

        std::cout << "📡 [firewall-acl-agent] Parsed endpoint: " << host_ << ":" << port_ << std::endl;
    }
};

// ============================================================================
// Implementación pública del Adapter
// ============================================================================

EtcdClient::EtcdClient(const std::string& endpoint, const std::string& component_name)
    : pImpl(std::make_unique<Impl>(endpoint, component_name)) {
    std::cout << "🔧 [firewall-acl-agent] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

bool EtcdClient::initialize() {
    std::cout << "🔗 [firewall-acl-agent] Initializing etcd client..." << std::endl;

    // Conectar y registrar (obtiene clave automáticamente)
    if (!pImpl->client_->connect()) {
        std::cerr << "❌ [firewall-acl-agent] Failed to connect to etcd-server" << std::endl;
        return false;
    }

    std::cout << "✅ [firewall-acl-agent] Connected to etcd-server" << std::endl;
    std::cout << "🔑 [firewall-acl-agent] Encryption key received automatically" << std::endl;

    return true;
}

bool EtcdClient::registerService() {
    std::cout << "📝 [firewall-acl-agent] Registering service in etcd..." << std::endl;

    // Cargar TODO el firewall.json
    std::ifstream config_file("../config/firewall.json");  // ← CAMBIAR A ../config/
    if (!config_file.is_open()) {
        std::cerr << "❌ [firewall-acl-agent] Failed to open ../config/firewall.json" << std::endl;
        return false;
    }

    nlohmann::json full_config;
    try {
        config_file >> full_config;
    } catch (const std::exception& e) {
        std::cerr << "❌ [firewall-acl-agent] Failed to parse firewall.json: " << e.what() << std::endl;
        return false;
    }
    config_file.close();

    // Añadir metadata de registro
    full_config["_registration"] = {
        {"timestamp", std::time(nullptr)},
        {"component", pImpl->component_name_},
        {"type", "firewall"},
        {"status", "active"}
    };

    // Extraer capabilities para log
    bool dry_run = full_config["operation"].value("dry_run", false);
    bool ipset_check = full_config["health_check"].value("ipset_health_check", false);
    bool iptables_check = full_config["health_check"].value("iptables_health_check", false);
    std::string zmq_endpoint = full_config["zmq"].value("endpoint", "unknown");

    std::cout << "📋 [firewall-acl-agent] Capabilities:" << std::endl;
    std::cout << "   - Mode: " << (dry_run ? "DRY-RUN" : "PRODUCTION") << std::endl;
    std::cout << "   - ZMQ Endpoint: " << zmq_endpoint << std::endl;
    std::cout << "   - IPSet Health Check: " << (ipset_check ? "✅" : "❌") << std::endl;
    std::cout << "   - IPTables Health Check: " << (iptables_check ? "✅" : "❌") << std::endl;
    std::cout << "   - Config Size: " << full_config.dump().size() << " bytes" << std::endl;

    // Registrar componente
    if (!pImpl->client_->register_component()) {
        std::cerr << "❌ [firewall-acl-agent] Failed to register component" << std::endl;
        return false;
    }

    // Subir config completo con put_config() (automáticamente cifrado+comprimido)
    if (!pImpl->client_->put_config(full_config.dump(2))) {
        std::cerr << "⚠️  [firewall-acl-agent] Failed to upload config (non-fatal, continuing)" << std::endl;
		return false;
    }

    std::cout << "✅ [firewall-acl-agent] Service registered successfully" << std::endl;
    std::cout << "🔐 [firewall-acl-agent] Config uploaded encrypted + compressed" << std::endl;

    return true;
}

std::string EtcdClient::get_crypto_seed() const {
    if (!pImpl->client_) {
        std::cerr << "❌ [firewall-acl-agent] get_crypto_seed() called before initialize()" << std::endl;
        return "";
    }

    // ADR-013 PHASE 2 — seed local, no del servidor
    const std::string seed_path = "/etc/ml-defender/firewall-acl-agent/seed.bin";
    std::ifstream f(seed_path, std::ios::binary);
    if (!f.is_open()) {
        std::cerr << "❌ [firewall-acl-agent] No se puede abrir seed.bin" << std::endl;
        return "";
    }
    std::string seed(32, '\0');
    f.read(&seed[0], 32);
    if (f.gcount() != 32) { return ""; }
    std::cout << "🔑 [firewall-acl-agent] Seed cargado localmente (32 bytes)" << std::endl;
    return seed;
}


    // ============================================================================
    // HMAC Methods (Day 58 - Pioneer Pattern)
    // ============================================================================

std::optional<std::vector<uint8_t>> EtcdClient::get_hmac_key(const std::string& key_path) {
    if (!pImpl->client_) {
        std::cerr << "❌ [firewall-acl-agent] get_hmac_key() called before initialize()" << std::endl;
        return std::nullopt;
    }

    auto key = pImpl->client_->get_hmac_key(key_path);

    if (key) {
        std::cout << "🔑 [firewall-acl-agent] Retrieved HMAC key from: " << key_path
                  << " (" << key->size() << " bytes)" << std::endl;
    } else {
        std::cerr << "⚠️ [firewall-acl-agent] HMAC key not found: " << key_path << std::endl;
    }

    return key;
}

std::string EtcdClient::compute_hmac_sha256(const std::string& data,
                                                const std::vector<uint8_t>& key) {
    if (!pImpl->client_) {
        std::cerr << "❌ [firewall-acl-agent] compute_hmac_sha256() called before initialize()" << std::endl;
        return "";
    }

    return pImpl->client_->compute_hmac_sha256(data, key);
}

std::string EtcdClient::bytes_to_hex(const std::vector<uint8_t>& bytes) {
    if (!pImpl->client_) {
        return "";
    }

    return pImpl->client_->bytes_to_hex(bytes);
}

etcd_client::ServicePaths EtcdClient::get_service_paths() const {
    if (!pImpl->client_) {
        std::cerr << "❌ [firewall-acl-agent] get_service_paths() called before initialize()" << std::endl;
        return etcd_client::ServicePaths{};
    }

    return pImpl->client_->get_service_paths();
}

} // namespace mldefender::firewall