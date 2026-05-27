// test_secrets_manager_simple.cpp
// Tests básicos para nueva API Day 55

#include "etcd_server/secrets_manager.hpp"
#include <nlohmann/json.hpp>
#include <cassert>
#include <iostream>
#include <thread>

using namespace etcd_server;

void test_generate_and_get() {
    nlohmann::json config = {
        {"secrets", {
                {"grace_period_seconds", 300},
                {"rotation_interval_hours", 168},
                {"default_key_length_bytes", 32}
        }}
    };

    SecretsManager manager(config);
    auto key = manager.generate_hmac_key("test_component");

    assert(key.key_data.size() == 64);  // 32 bytes = 64 hex chars
    assert(key.is_active == true);
    assert(key.component == "test_component");

    std::cout << "✅ test_generate_and_get PASSED\n";
}

void test_rotation_grace_period() {
    nlohmann::json config = {
        {"secrets", {
                {"grace_period_seconds", 5},  // 5 segundos para test rápido
                {"rotation_interval_hours", 168},
                {"default_key_length_bytes", 32}
        }}
    };

    SecretsManager manager(config);

    auto key1 = manager.generate_hmac_key("test_rotate");
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    auto key2 = manager.rotate_hmac_key("test_rotate");

    auto valid_keys = manager.get_valid_keys("test_rotate");
    assert(valid_keys.size() == 2);  // Active + grace
    assert(valid_keys[0].is_active == true);
    assert(valid_keys[1].is_active == false);

    std::cout << "✅ test_rotation_grace_period PASSED\n";
}

int main() {
    test_generate_and_get();
    test_rotation_grace_period();
    std::cout << "🎉 All tests passed!\n";
    return 0;
}