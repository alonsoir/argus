// etcd-server/tests/test_hmac_integration.cpp
// Reescrito DAY 99 para la API actual de SecretsManager
// Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)

#include "etcd_server/secrets_manager.hpp"
#include <iostream>
#include <cassert>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <iomanip>
#include <sstream>
#include <nlohmann/json.hpp>

using namespace etcd_server;

#define GREEN  "\033[32m"
#define RED    "\033[31m"
#define BLUE   "\033[34m"
#define YELLOW "\033[33m"
#define RESET  "\033[0m"

// ============================================================================
// Helpers
// ============================================================================

nlohmann::json make_config(bool auto_generate = false) {
    return nlohmann::json{
        {"secrets", {
            {"grace_period_seconds", 300},
            {"rotation_interval_hours", 168},
            {"default_key_length_bytes", 32},
            {"min_rotation_interval_seconds", 300},
            {"auto_generate_on_startup", auto_generate}
        }}
    };
}

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    }
    return bytes;
}

std::string compute_hmac_sha256(const std::string& data, const std::vector<uint8_t>& key) {
    unsigned char result[EVP_MAX_MD_SIZE];
    unsigned int len = 0;
    HMAC(EVP_sha256(), key.data(), key.size(),
         reinterpret_cast<const unsigned char*>(data.data()), data.size(),
         result, &len);
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < len; ++i)
        oss << std::setw(2) << static_cast<int>(result[i]);
    return oss.str();
}

bool validate_hmac_sha256(const std::string& data, const std::string& expected,
                          const std::vector<uint8_t>& key) {
    std::string computed = compute_hmac_sha256(data, key);
    if (computed.size() != expected.size()) return false;
    unsigned char diff = 0;
    for (size_t i = 0; i < computed.size(); ++i)
        diff |= static_cast<unsigned char>(computed[i] ^ expected[i]);
    return diff == 0;
}

void log_test(const std::string& name, bool passed) {
    std::cout << (passed ? GREEN "✅ PASS" : RED "❌ FAIL") << RESET
              << ": " << name << std::endl;
}

// ============================================================================
// Test 1: E2E HMAC generation and validation
// ============================================================================
bool test_e2e_hmac_workflow() {
    std::cout << BLUE << "\n─── Test: E2E HMAC Workflow ───" << RESET << std::endl;

    SecretsManager sm(make_config());

    auto hmac_key = sm.generate_hmac_key("rag-ingester");
    assert(hmac_key.is_active);
    assert(!hmac_key.key_data.empty());
    std::cout << "  ✅ Key generated (" << hmac_key.key_data.size()/2 << " bytes)" << std::endl;

    auto key_bytes = hex_to_bytes(hmac_key.key_data);
    std::string log_data = R"({"timestamp":"2026-03-27T06:00:00Z","ip":"192.168.1.100","confidence":0.95})";

    std::string hmac_hex = compute_hmac_sha256(log_data, key_bytes);
    assert(validate_hmac_sha256(log_data, hmac_hex, key_bytes));
    std::cout << "  ✅ HMAC validation correct" << std::endl;

    std::string tampered = log_data;
    tampered[10] = 'X';
    assert(!validate_hmac_sha256(tampered, hmac_hex, key_bytes));
    std::cout << "  ✅ Tampering detected" << std::endl;

    return true;
}

// ============================================================================
// Test 2: Multiple components, same key
// ============================================================================
bool test_multi_component_access() {
    std::cout << BLUE << "\n─── Test: Multi-component Key Access ───" << RESET << std::endl;

    SecretsManager sm(make_config());
    sm.generate_hmac_key("rag-ingester");

    auto key1 = sm.get_hmac_key("rag-ingester");
    auto key2 = sm.get_hmac_key("rag-ingester");

    assert(key1.key_data == key2.key_data);
    std::cout << "  ✅ Both components retrieved identical keys" << std::endl;

    auto key_bytes = hex_to_bytes(key1.key_data);
    std::string data = "shared log entry";
    assert(compute_hmac_sha256(data, key_bytes) == compute_hmac_sha256(data, key_bytes));
    std::cout << "  ✅ HMACs idénticos en ambos componentes" << std::endl;

    return true;
}

// ============================================================================
// Test 3: Key rotation
// ============================================================================
bool test_key_rotation_workflow() {
    std::cout << BLUE << "\n─── Test: Key Rotation ───" << RESET << std::endl;

    SecretsManager sm(make_config());
    sm.generate_hmac_key("sniffer");

    auto old_key = sm.get_hmac_key("sniffer");
    std::string data = "data signed with old key";
    auto old_bytes = hex_to_bytes(old_key.key_data);
    std::string old_hmac = compute_hmac_sha256(data, old_bytes);

    auto new_key = sm.rotate_hmac_key("sniffer", true); // force=true bypass cooldown
    assert(new_key.key_data != old_key.key_data);
    std::cout << "  ✅ Key rotated successfully" << std::endl;

    auto new_bytes = hex_to_bytes(new_key.key_data);
    std::string new_hmac = compute_hmac_sha256(data, new_bytes);
    assert(old_hmac != new_hmac);
    std::cout << "  ✅ HMACs differ after rotation" << std::endl;

    assert(!validate_hmac_sha256(data, old_hmac, new_bytes));
    std::cout << "  ✅ Old HMAC correctly rejected with new key" << std::endl;

    return true;
}

// ============================================================================
// Test 4: RAG-ingester simulation
// ============================================================================
bool test_rag_ingester_simulation() {
    std::cout << BLUE << "\n─── Test: RAG-Ingester Simulation ───" << RESET << std::endl;

    SecretsManager sm(make_config(true)); // auto_generate=true
    auto hmac_key = sm.get_hmac_key("rag-ingester");
    auto key_bytes = hex_to_bytes(hmac_key.key_data);
    std::cout << "  ✅ RAG HMAC key retrieved (" << key_bytes.size() << " bytes)" << std::endl;

    int valid_count = 0, tampered_count = 0;
    for (int i = 0; i < 10; ++i) {
        std::ostringstream oss;
        oss << R"({"id":)" << i
            << R"(,"ip":"192.168.1.)" << (100 + i)
            << R"(","confidence":0.)" << (90 + i) << "}";
        std::string log_data = oss.str();
        std::string hmac = compute_hmac_sha256(log_data, key_bytes);
        if (i % 5 == 0) log_data[5] = 'X'; // tamper 2/10
        validate_hmac_sha256(log_data, hmac, key_bytes) ? valid_count++ : tampered_count++;
    }

    std::cout << "  ✅ Valid: " << valid_count << " | Tampered: " << tampered_count << std::endl;
    assert(valid_count == 8 && tampered_count == 2);
    std::cout << "  ✅ RAG-ingester simulation correcta" << std::endl;

    return true;
}

// ============================================================================
// Main
// ============================================================================
int main() {
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  HMAC Integration Tests — DAY 99" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;

    int passed = 0, total = 0;

    #define RUN(fn) do { total++; bool r = fn(); log_test(#fn, r); if (r) passed++; } while(0)
    RUN(test_e2e_hmac_workflow);
    RUN(test_multi_component_access);
    RUN(test_key_rotation_workflow);
    RUN(test_rag_ingester_simulation);
    #undef RUN

    std::cout << "\n═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  Results: " << passed << "/" << total << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;

    if (passed == total) {
        std::cout << GREEN "🎉 ALL HMAC INTEGRATION TESTS PASSED!" RESET << std::endl;
        return 0;
    }
    std::cout << RED "❌ SOME TESTS FAILED" RESET << std::endl;
    return 1;
}
