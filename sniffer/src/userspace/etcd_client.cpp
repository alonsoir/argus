// sniffer/src/userspace/etcd_client.cpp - Adapter para etcd_client library
#include "etcd_client.hpp"
#include "etcd_client/etcd_client.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <fstream>

namespace sniffer {

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
        config.compression_min_size = 0;
        config.component_config_path = "/etc/ml-defender/sniffer/sniffer.json";
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

        std::cout << "📡 [Sniffer] Parsed endpoint: " << host_ << ":" << port_ << std::endl;
    }
};

// ============================================================================
// Implementación pública del Adapter
// ============================================================================

EtcdClient::EtcdClient(const std::string& endpoint, const std::string& component_name)
    : pImpl(std::make_unique<Impl>(endpoint, component_name)) {
    std::cout << "🔧 [Sniffer] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

bool EtcdClient::initialize() {
    std::cout << "🔗 [Sniffer] Initializing etcd client..." << std::endl;

    // Conectar y registrar (obtiene clave automáticamente)
    if (!pImpl->client_->connect()) {
        std::cerr << "❌ [Sniffer] Failed to connect to etcd-server" << std::endl;
        return false;
    }

    std::cout << "✅ [Sniffer] Connected to etcd-server" << std::endl;
    std::cout << "🔑 [Sniffer] Encryption key received automatically" << std::endl;

    return true;
}

bool EtcdClient::is_connected() const {
    return pImpl->client_ != nullptr;
}

bool EtcdClient::registerService() {
    std::cout << "📝 [Sniffer] Registering sniffer service in etcd..." << std::endl;

    if (!pImpl->client_->register_component()) {
        std::cerr << "❌ [Sniffer] Failed to register component" << std::endl;
        return false;
    }

    // Cargar TODO el sniffer.json (Via Appia Quality: single source of truth)
    std::ifstream config_file("/vagrant/sniffer/config/sniffer.json");
    if (!config_file.is_open()) {
        std::cerr << "❌ [Sniffer] Failed to open sniffer.json" << std::endl;
        return false;
    }

    nlohmann::json full_config;
    try {
        config_file >> full_config;
    } catch (const std::exception& e) {
        std::cerr << "❌ [Sniffer] Failed to parse sniffer.json: " << e.what() << std::endl;
        return false;
    }
    config_file.close();

    // Añadir metadata de registro
    full_config["_registration"] = {
        {"timestamp", std::time(nullptr)},
        {"component", pImpl->component_name_},
        {"type", "packet-sniffer"},
        {"status", "active"}
    };

    // Extraer capabilities para log
    bool dual_nic = full_config["deployment"]["mode"] == "dual";
    bool fast_detector = full_config.value("fast_detector", nlohmann::json::object()).value("enabled", false);
    std::string filter_mode = full_config["capture"]["filter"].value("mode", "unknown");

    std::cout << "📋 [Sniffer] Capabilities:" << std::endl;
    std::cout << "   - Deployment: " << full_config["deployment"]["mode"] << std::endl;
    std::cout << "   - Dual-NIC: " << (dual_nic ? "✅" : "❌") << std::endl;
    std::cout << "   - Fast Detector: " << (fast_detector ? "✅" : "❌") << std::endl;
    std::cout << "   - Filter Mode: " << filter_mode << std::endl;
    std::cout << "   - Config Size: " << full_config.dump().size() << " bytes" << std::endl;

    // Subir config completo con put_config() (automáticamente cifrado+comprimido)
    if (!pImpl->client_->put_config(full_config.dump(2))) {
        std::cerr << "❌ [Sniffer] Failed to register service" << std::endl;
        return false;
    }

    std::cout << "✅ [Sniffer] Service registered successfully" << std::endl;
    std::cout << "🔐 [Sniffer] Config uploaded encrypted + compressed" << std::endl;

    return true;
}

bool EtcdClient::unregisterService() {
    std::cout << "🗑️ [Sniffer] Unregistering service..." << std::endl;
    return pImpl->client_->unregister_component();
}

bool EtcdClient::upload_full_config(const std::string& config_json) {
    std::cout << "📤 [Sniffer] Uploading config update..." << std::endl;
    return pImpl->client_->put_config(config_json);
}

bool EtcdClient::get_component_config(const std::string& component_name) {
    std::cout << "📥 [Sniffer] Fetching config for: " << component_name << std::endl;

    std::string config_json = pImpl->client_->get_component_config(component_name);
    if (config_json.empty()) {
        std::cerr << "❌ [Sniffer] Component not found: " << component_name << std::endl;
        return false;
    }

    std::cout << "✅ [Sniffer] Config received for " << component_name << std::endl;
    std::cout << config_json << std::endl;

    return true;
}

bool EtcdClient::get_pipeline_status() {
    std::cout << "📊 [Sniffer] Getting pipeline status..." << std::endl;

    // Obtener lista de componentes
    auto components = pImpl->client_->list_components();
    std::cout << "✅ [Sniffer] Found " << components.size() << " components" << std::endl;

    for (const auto& comp : components) {
        std::cout << "   - " << comp.name << std::endl;
    }

    return true;
}

std::string EtcdClient::get_encryption_status() {
    return "🔐 Encryption: ChaCha20-Poly1305 (managed by etcd-client library)";
}

std::string EtcdClient::get_encryption_seed() const {
    // ADR-013 PHASE 2 — seed local
    const std::string seed_path = "/etc/ml-defender/sniffer/seed.bin";
    std::ifstream f(seed_path, std::ios::binary);
    if (!f.is_open()) {
        std::cerr << "❌ [Sniffer] No se puede abrir seed.bin" << std::endl;
        return "";
    }
    std::string seed(32, '\0');
    f.read(&seed[0], 32);
    if (f.gcount() != 32) { return ""; }
    std::cout << "🔑 [Sniffer] Seed cargado localmente (32 bytes)" << std::endl;
    return seed;
}
} // namespace sniffer