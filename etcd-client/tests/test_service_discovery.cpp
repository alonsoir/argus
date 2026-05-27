// test_service_discovery.cpp - Day 59: Service Discovery Paths
#include "etcd_client/etcd_client.hpp"
#include <iostream>
#include <cassert>

using namespace etcd_client;

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Test: Service Discovery Paths" << std::endl;
    std::cout << "========================================" << std::endl;

    // Setup
    Config config;
    config.component_name = "test-service-discovery";
    config.host = "127.0.0.1";
    config.port = 2379;
    config.heartbeat_enabled = false;  // Disable for test

    EtcdClient client(config);

    // Test 1: Connect
    std::cout << "\n[TEST 1] Connecting to etcd-server..." << std::endl;
    bool connected = client.connect();
    assert(connected && "Failed to connect");
    std::cout << "✅ Connected" << std::endl;

    // Test 2: Register and get paths
    std::cout << "\n[TEST 2] Registering component..." << std::endl;
    bool registered = client.register_component();
    assert(registered && "Failed to register");
    std::cout << "✅ Registered" << std::endl;

    // Test 3: Verify paths were received
    std::cout << "\n[TEST 3] Verifying service paths..." << std::endl;
    ServicePaths paths = client.get_service_paths();

    assert(!paths.hmac_key.empty() && "HMAC key path is empty");
    assert(!paths.crypto_token.empty() && "Crypto token path is empty");
    assert(!paths.config.empty() && "Config path is empty");
    assert(paths.is_valid() && "Paths are not valid");

    std::cout << "✅ Paths received:" << std::endl;
    std::cout << "   - HMAC key: " << paths.hmac_key << std::endl;
    std::cout << "   - Crypto token: " << paths.crypto_token << std::endl;
    std::cout << "   - Config: " << paths.config << std::endl;

    // Test 4: Verify path format
    std::cout << "\n[TEST 4] Verifying path format..." << std::endl;
    assert(paths.hmac_key.find("/secrets/") == 0 && "HMAC path doesn't start with /secrets/");
    assert(paths.crypto_token.find("/crypto/") == 0 && "Crypto path doesn't start with /crypto/");
    assert(paths.config.find("/config/") == 0 && "Config path doesn't start with /config/");
    std::cout << "✅ Path formats correct" << std::endl;

    // Test 5: Use HMAC path to get key
    std::cout << "\n[TEST 5] Testing HMAC key retrieval with discovered path..." << std::endl;
    auto hmac_key = client.get_hmac_key(paths.hmac_key);

    if (hmac_key.has_value()) {
        std::cout << "✅ HMAC key retrieved using service discovery path" << std::endl;
        std::cout << "   Key size: " << hmac_key->size() << " bytes" << std::endl;
    } else {
        std::cout << "⚠️  No HMAC key found (expected if etcd-server hasn't generated one yet)" << std::endl;
    }

    // Cleanup
    client.unregister_component();
    client.disconnect();

    std::cout << "\n========================================" << std::endl;
    std::cout << "✅ All service discovery tests PASSED" << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}