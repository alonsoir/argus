// crypto-transport/tests/test_integ_contexts.cpp
//
// TEST-INTEG-1: round-trip E2E usando CTX_SNIFFER_TO_ML (contexts.hpp)
// TEST-INTEG-2: JSON → LZ4 → encrypt → decrypt → decompress byte-a-byte
// TEST-INTEG-3: regresión — contextos asimétricos → MAC failure
//
// Gate obligatorio antes de arXiv — ADR-013 PHASE 2, DAY 99

#include <gtest/gtest.h>
#include <sodium.h>
#include <lz4.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

#include "crypto_transport/transport.hpp"
#include "crypto_transport/contexts.hpp"
#include <seed_client/seed_client.hpp>

// ============================================================================
// TestSeedEnv — reutilizado de test_crypto_transport.cpp
// ============================================================================
namespace {

struct TestSeedEnv {
    std::filesystem::path dir;
    std::filesystem::path json_path;

    explicit TestSeedEnv(const std::string& id = "integ") {
        dir = std::filesystem::temp_directory_path() / ("ml_defender_integ_" + id);
        std::filesystem::create_directories(dir);

        std::array<uint8_t, 32> seed{};
        randombytes_buf(seed.data(), seed.size());

        auto seed_path = dir / "seed.bin";
        std::ofstream sf(seed_path, std::ios::binary);
        sf.write(reinterpret_cast<const char*>(seed.data()), 32);
        sf.close();
        std::filesystem::permissions(seed_path,
            std::filesystem::perms::owner_read,
            std::filesystem::perm_options::replace);

        json_path = dir / (id + ".json");
        std::ofstream jf(json_path);
        jf << "{\"identity\":{\"component_id\":\"" << id
           << "\",\"keys_dir\":\"" << dir.string() << "/\"}}";
    }

    ~TestSeedEnv() { std::filesystem::remove_all(dir); }

    ml_defender::SeedClient make_client() const {
        ml_defender::SeedClient sc(json_path.string());
        sc.load();
        return sc;
    }
};

// LZ4 helpers — formato interno: [uint32_t orig_size LE] + compressed_data
std::vector<uint8_t> lz4_compress(const std::string& input) {
    const int src_size = static_cast<int>(input.size());
    const int max_dst  = LZ4_compressBound(src_size);
    std::vector<uint8_t> buf(4 + max_dst);

    // header: orig_size en little-endian
    uint32_t orig = static_cast<uint32_t>(src_size);
    std::memcpy(buf.data(), &orig, 4);

    const int compressed = LZ4_compress_default(
        input.data(),
        reinterpret_cast<char*>(buf.data() + 4),
        src_size, max_dst);

    if (compressed <= 0)
        throw std::runtime_error("LZ4_compress_default failed");

    buf.resize(4 + compressed);
    return buf;
}

std::string lz4_decompress(const std::vector<uint8_t>& buf) {
    if (buf.size() < 4)
        throw std::runtime_error("LZ4 buffer too small");

    uint32_t orig = 0;
    std::memcpy(&orig, buf.data(), 4);

    std::string out(orig, '\0');
    const int n = LZ4_decompress_safe(
        reinterpret_cast<const char*>(buf.data() + 4),
        out.data(),
        static_cast<int>(buf.size() - 4),
        static_cast<int>(orig));

    if (n < 0 || static_cast<uint32_t>(n) != orig)
        throw std::runtime_error("LZ4_decompress_safe failed");

    return out;
}

} // namespace

// ============================================================================
// Fixture
// ============================================================================
class IntegContextsTest : public ::testing::Test {
protected:
    void SetUp() override {
        if (sodium_init() < 0) GTEST_SKIP() << "libsodium init failed";
        env_ = std::make_unique<TestSeedEnv>("channel");
    }
    std::unique_ptr<TestSeedEnv> env_;
};

// ============================================================================
// TEST-INTEG-1: round-trip E2E — CTX_SNIFFER_TO_ML simétrico
// ============================================================================
TEST_F(IntegContextsTest, INTEG1_SnifferToMlRoundTrip) {
    auto sc = env_->make_client();

    // Emisor (sniffer) y receptor (ml-detector) usan LA MISMA constante
    crypto_transport::CryptoTransport tx(sc, ml_defender::crypto::CTX_SNIFFER_TO_ML);
    crypto_transport::CryptoTransport rx(sc, ml_defender::crypto::CTX_SNIFFER_TO_ML);

    const std::string payload =
        R"({"event":"flow","src":"192.168.1.100","dst":"10.0.0.1","bytes":1024})";
    const std::vector<uint8_t> plaintext(payload.begin(), payload.end());

    auto ciphertext = tx.encrypt(plaintext);
    auto recovered  = rx.decrypt(ciphertext);

    EXPECT_EQ(plaintext, recovered)
        << "INTEG-1 FAILED: round-trip sniffer→ml-detector no recuperó el payload";
}

// ============================================================================
// TEST-INTEG-1b: todos los canales — round-trip simétrico
// ============================================================================
TEST_F(IntegContextsTest, INTEG1b_AllChannelsRoundTrip) {
    auto sc = env_->make_client();
    const std::vector<uint8_t> payload = {0x01, 0x02, 0x03, 0x04, 0xDE, 0xAD};

    const std::vector<const char*> channels = {
        ml_defender::crypto::CTX_SNIFFER_TO_ML,
        ml_defender::crypto::CTX_ML_TO_FIREWALL,
        ml_defender::crypto::CTX_ETCD_TX,
        ml_defender::crypto::CTX_ETCD_RX,
        ml_defender::crypto::CTX_RAG_ARTIFACTS,
    };

    for (const auto* ctx : channels) {
        crypto_transport::CryptoTransport tx(sc, ctx);
        crypto_transport::CryptoTransport rx(sc, ctx);
        EXPECT_EQ(payload, rx.decrypt(tx.encrypt(payload)))
            << "FAILED for context: " << ctx;
    }
}

// ============================================================================
// TEST-INTEG-2: JSON → LZ4 → encrypt → decrypt → decompress byte-a-byte
// ============================================================================
TEST_F(IntegContextsTest, INTEG2_JsonLz4EncryptRoundTrip) {
    auto sc = env_->make_client();

    crypto_transport::CryptoTransport tx(sc, ml_defender::crypto::CTX_SNIFFER_TO_ML);
    crypto_transport::CryptoTransport rx(sc, ml_defender::crypto::CTX_SNIFFER_TO_ML);

    const std::string json =
        R"({"src_ip":"192.168.1.100","dst_ip":"10.0.0.1","protocol":"tcp",)"
        R"("bytes_sent":2048,"bytes_recv":512,"label":"malicious"})";

    // Pipeline TX: JSON → LZ4 → encrypt
    auto compressed = lz4_compress(json);
    auto ciphertext = tx.encrypt(compressed);

    // Pipeline RX: decrypt → LZ4 decompress → assert
    auto decrypted    = rx.decrypt(ciphertext);
    auto decompressed = lz4_decompress(decrypted);

    EXPECT_EQ(json, decompressed)
        << "INTEG-2 FAILED: JSON no recuperado byte-a-byte tras LZ4+cifrado";

    // Verificar reducción de tamaño
    EXPECT_LT(compressed.size(), json.size() + 4)
        << "LZ4 no comprimió el JSON (inesperado para texto repetitivo)";
}

// ============================================================================
// TEST-INTEG-3: regresión — contextos asimétricos → MAC failure (bug original)
// ============================================================================
TEST_F(IntegContextsTest, INTEG3_AsymmetricContextsProduceMacFailure) {
    auto sc = env_->make_client();

    // Simula el bug DAY 98: sniffer cifraba con "sniffer:v1:tx"
    // y ml-detector descifraba con "ml-detector:v1:rx" → claves distintas
    crypto_transport::CryptoTransport tx_wrong(sc, "ml-defender:sniffer:v1:tx");
    crypto_transport::CryptoTransport rx_wrong(sc, "ml-defender:ml-detector:v1:rx");

    const std::vector<uint8_t> payload = {0xCA, 0xFE, 0xBA, 0xBE};
    auto ciphertext = tx_wrong.encrypt(payload);

    EXPECT_THROW(rx_wrong.decrypt(ciphertext), std::runtime_error)
        << "INTEG-3 FAILED: contextos asimétricos deberían producir MAC failure";
}
