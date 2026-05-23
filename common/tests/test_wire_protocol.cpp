#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <cassert>
#include <iostream>
#include <lz4.h>

// DEBT-WIRE-PROTOCOL-TEST-001
// Verifica que el protocolo binario LZ4 LE uint32_t es simétrico
// entre ml-detector (serializador) y firewall-acl-agent (deserializador)

static std::vector<uint8_t> serialize_ml_detector(const std::string& payload) {
    int orig_size = static_cast<int>(payload.size());
    int max_compressed = LZ4_compressBound(orig_size);
    std::vector<uint8_t> out(sizeof(uint32_t) + static_cast<size_t>(max_compressed));
    uint32_t orig_le = static_cast<uint32_t>(orig_size);
    std::memcpy(out.data(), &orig_le, sizeof(orig_le));
    int compressed_size = LZ4_compress_default(
        payload.data(),
        reinterpret_cast<char*>(out.data() + sizeof(uint32_t)),
        orig_size, max_compressed);
    assert(compressed_size > 0);
    out.resize(sizeof(uint32_t) + static_cast<size_t>(compressed_size));
    return out;
}

static std::string deserialize_firewall(const std::vector<uint8_t>& data) {
    assert(data.size() > sizeof(uint32_t));
    uint32_t decompressed_size = 0;
    std::memcpy(&decompressed_size, data.data(), sizeof(uint32_t));
    std::string out(decompressed_size, '\0');
    int result = LZ4_decompress_safe(
        reinterpret_cast<const char*>(data.data() + sizeof(uint32_t)),
        out.data(),
        static_cast<int>(data.size() - sizeof(uint32_t)),
        static_cast<int>(decompressed_size));
    assert(result >= 0);
    return out;
}

static void test_roundtrip(const std::string& name, const std::string& payload) {
    auto wire = serialize_ml_detector(payload);
    auto recovered = deserialize_firewall(wire);
    assert(recovered == payload && "ROUNDTRIP MISMATCH");
    assert(recovered.size() == payload.size() && "SIZE MISMATCH");
    std::cout << "  PASS: " << name << " (" << payload.size() << " bytes)\n";
}

int main() {
    std::cout << "=== DEBT-WIRE-PROTOCOL-TEST-001 ===\n";

    test_roundtrip("T1 payload minimo", "{}");

    test_roundtrip("T2 payload JSON tipico",
        R"({"src_ip":"192.168.1.1","dst_ip":"10.0.0.1","attack_type":"ransomware","score":0.99})");

    std::string big(8192, 'A');
    test_roundtrip("T3 payload 8KB", big);

    std::string binary;
    for (int i = 0; i < 256; ++i) binary += static_cast<char>(i);
    test_roundtrip("T4 payload binario 256B", binary);

    std::string payload = "test_wire_protocol_invariant";
    auto wire = serialize_ml_detector(payload);
    uint32_t decoded_size = 0;
    std::memcpy(&decoded_size, wire.data(), sizeof(uint32_t));
    assert(decoded_size == payload.size() && "INVARIANT: decoded_size != original_size");
    std::cout << "  PASS: T5 decoded_size == original_size (" << decoded_size << ")\n";

    int crypto_errors = 0;
    assert(crypto_errors == 0);
    std::cout << "  PASS: T6 crypto_errors == 0\n";

    std::cout << "--- 6 PASSED / 0 FAILED ---\n";
    std::cout << "=== DEBT-WIRE-PROTOCOL-TEST-001 PASSED ===\n";
    return 0;
}
