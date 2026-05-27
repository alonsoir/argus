// etcd-server/tests/test_secrets_manager_simple.cpp
// Day 55: Basic HMAC functionality tests
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/secrets_manager.hpp"
#include <nlohmann/json.hpp>
#include <cassert>
#include <iostream>
#include <thread>
#include <chrono>

using namespace etcd_server;

#define GREEN "\033[32m"
#define RED "\033[31m"
#define RESET "\033[0m"

void test_generate_and_get() {
    std::cout << "Test 1: Generate and get HMAC key..." << std::flush;
    
    nlohmann::json config = {
    	{"secrets", {
        	{"grace_period_seconds", 300},
        	{"rotation_interval_hours", 168},
        	{"default_key_length_bytes", 32},
        	{"min_rotation_interval_seconds", 300}  // AÑADIR
    	}}
	};
    
    SecretsManager manager(config);
    auto key = manager.generate_hmac_key("test_component");
    
    assert(key.key_data.size() == 64);  // 32 bytes = 64 hex chars
    assert(key.is_active == true);
    assert(key.component == "test_component");
    
    // Get the same key
    auto retrieved = manager.get_hmac_key("test_component");
    assert(retrieved.key_data == key.key_data);
    
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_rotation_grace_period() {
    std::cout << "Test 2: Rotation with grace period..." << std::flush;
    
    nlohmann::json config = {
    	{"secrets", {
        	{"grace_period_seconds", 5},
        	{"rotation_interval_hours", 168},
        	{"default_key_length_bytes", 32},
        	{"min_rotation_interval_seconds", 5}  // AÑADIR
    	}}
	};
    
    SecretsManager manager(config);
    
    // Generate initial key
    auto key1 = manager.generate_hmac_key("test_rotate");
    std::string key1_data = key1.key_data;
    
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    // Rotate
    auto key2 = manager.rotate_hmac_key("test_rotate");
    std::string key2_data = key2.key_data;
    
    // Keys should be different
    assert(key1_data != key2_data);
    
    // Should have 2 valid keys (active + grace)
    auto valid_keys = manager.get_valid_keys("test_rotate");
    assert(valid_keys.size() == 2);
    
    // First should be active
    assert(valid_keys[0].is_active == true);
    assert(valid_keys[0].key_data == key2_data);
    
    // Second should be in grace period
    assert(valid_keys[1].is_active == false);
    assert(valid_keys[1].key_data == key1_data);
    
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_grace_period_expiry() {
    std::cout << "Test 3: Grace period expiry..." << std::flush;
    
    nlohmann::json config = {
    	{"secrets", {
        	{"grace_period_seconds", 2},
        	{"rotation_interval_hours", 168},
        	{"default_key_length_bytes", 32},
        	{"min_rotation_interval_seconds", 2}  // AÑADIR
    	}}
	};
    
    SecretsManager manager(config);
    
    // Generate and rotate
    manager.generate_hmac_key("test_expiry");
    manager.rotate_hmac_key("test_expiry");
    
    // Should have 2 valid keys immediately
    auto valid_before = manager.get_valid_keys("test_expiry");
    assert(valid_before.size() == 2);
    
    // Wait for grace period to expire
    std::this_thread::sleep_for(std::chrono::seconds(3));
    
    // Should only have 1 valid key (old one expired)
    auto valid_after = manager.get_valid_keys("test_expiry");
    assert(valid_after.size() == 1);
    assert(valid_after[0].is_active == true);
    
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_grace_period_config() {
    std::cout << "Test 4: Grace period configuration..." << std::flush;
    
    nlohmann::json config = {
    	{"secrets", {
        	{"grace_period_seconds", 42},
        	{"rotation_interval_hours", 168},
        	{"default_key_length_bytes", 32},
        	{"min_rotation_interval_seconds", 42}  // AÑADIR
    	}}
	};
    
    SecretsManager manager(config);
    
    assert(manager.get_grace_period_seconds() == 42);
    
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_cooldown_enforcement() {
    std::cout << "Test 5: Cooldown enforcement (ADR-004)..." << std::flush;

    nlohmann::json config = {
        {"secrets", {
            {"grace_period_seconds", 5},
            {"rotation_interval_hours", 168},
            {"default_key_length_bytes", 32},
            {"min_rotation_interval_seconds", 5}  // Cooldown = grace period
        }}
    };

    SecretsManager manager(config);

    // Primera rotación OK
    manager.generate_hmac_key("test_cooldown");
    auto key1 = manager.rotate_hmac_key("test_cooldown");

    // Segunda rotación inmediata: debe fallar (cooldown activo)
    bool threw = false;
    try {
        manager.rotate_hmac_key("test_cooldown");  // Sin force
    } catch (const std::runtime_error& e) {
        std::string msg(e.what());
        assert(msg.find("Rotation too soon") != std::string::npos);
        threw = true;
    }
    assert(threw);  // Debe haber lanzado excepción

    // Con force=true: debe pasar (emergency override)
    auto key2 = manager.rotate_hmac_key("test_cooldown", true);  // force=true
    assert(key2.key_data != key1.key_data);  // Debe ser clave diferente

    // Esperar a que expire cooldown
    std::this_thread::sleep_for(std::chrono::seconds(6));

    // Ahora debe permitir rotación normal
    auto key3 = manager.rotate_hmac_key("test_cooldown");  // Sin force, debe pasar
    assert(key3.key_data != key2.key_data);

    std::cout << GREEN << " PASS" << RESET << std::endl;
}

int main() {
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  SecretsManager Basic Tests (Day 55)" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;

    try {
        test_generate_and_get();
        test_rotation_grace_period();
        test_grace_period_expiry();
        test_grace_period_config();
        test_cooldown_enforcement();

        std::cout << std::endl;
        std::cout << GREEN << "🎉 ALL 5 TESTS PASSED!" << RESET << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << std::endl;
        std::cout << RED << "❌ TEST FAILED: " << e.what() << RESET << std::endl;
        return 1;
    }
}
