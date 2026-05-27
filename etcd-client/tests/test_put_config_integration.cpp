#include "etcd_client/etcd_client.hpp"
#include <nlohmann/json.hpp>
#include <iostream>

int main() {
    std::cout << "=== Testing put_config() Integration (ChaCha20) ===" << std::endl;

    etcd_client::Config config;
    config.component_name = "test-cpp-client";
    config.host = "localhost";
    config.port = 2379;
    config.encryption_enabled = true;
    config.compression_enabled = true;
    config.heartbeat_enabled = false;  // ← Añadir esto

    etcd_client::EtcdClient client(config);

    if (!client.connect()) {
        std::cerr << "❌ Failed to connect" << std::endl;
        return 1;
    }

    // ← AÑADIR ESTO: Registrar componente para obtener encryption key
    if (!client.register_component()) {
        std::cerr << "❌ Failed to register component" << std::endl;
        return 1;
    }
    std::cout << "✅ Component registered, encryption key received" << std::endl;

    nlohmann::json test_config = {
        {"component", "test-cpp-client"},
        {"component_name", "test-cpp-client"},
        {"enabled", true},
        {"threshold", 0.75},
        {"models", {
                {"model_a", {{"enabled", true}, {"path", "/models/a.bin"}}},
                {"model_b", {{"enabled", false}, {"path", "/models/b.bin"}}}
        }},
        {"rag_logger", {
                {"enabled", true},
                {"output_dir", "/logs/rag"}
        }}
    };

    std::string json_str = test_config.dump(2);
    std::cout << "\n📝 Test config (" << json_str.size() << " bytes):" << std::endl;
    std::cout << json_str << std::endl;

    std::cout << "\n📤 Uploading config..." << std::endl;
    if (client.put_config(json_str)) {
        std::cout << "\n✅ SUCCESS: Config uploaded with ChaCha20 encryption!" << std::endl;
        return 0;
    } else {
        std::cerr << "\n❌ FAILED: Config upload failed" << std::endl;
        return 1;
    }
}