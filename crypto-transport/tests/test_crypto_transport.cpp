// crypto-transport/tests/test_crypto_transport.cpp
#include <gtest/gtest.h>
#include <sodium.h>
#include <fstream>
#include <tuple>
#include <filesystem>
#include "crypto_transport/transport.hpp"
#include <seed_client/seed_client.hpp>

// ============================================================================
// TestSeedEnv — crea seed.bin + JSON temporal en /tmp
// Ejercita el path completo incluyendo lectura de fichero
// ============================================================================
namespace {
struct TestSeedEnv {
    std::filesystem::path dir;
    std::filesystem::path json_path;

    explicit TestSeedEnv(const std::string& id = "test") {
        dir = std::filesystem::temp_directory_path() / ("ml_defender_test_" + id);
        std::filesystem::create_directories(dir);

        // seed aleatorio de 32 bytes
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
} // namespace

class CryptoTransportTest : public ::testing::Test {
protected:
    void SetUp() override {
        if (sodium_init() < 0) GTEST_SKIP() << "libsodium init failed";
        env_ = std::make_unique<TestSeedEnv>("sniffer");
    }
    std::unique_ptr<TestSeedEnv> env_;
};

// TC-CT-001: Constructor con SeedClient cargado
TEST_F(CryptoTransportTest, ConstructorSucceedsWithLoadedSeedClient) {
    auto sc = env_->make_client();
    EXPECT_NO_THROW(crypto_transport::CryptoTransport ct(sc, "ml-defender:sniffer:v1:tx"));
}

// TC-CT-002: Constructor lanza si SeedClient no está cargado
TEST_F(CryptoTransportTest, ConstructorThrowsIfSeedNotLoaded) {
    ml_defender::SeedClient sc(env_->json_path.string());
    EXPECT_THROW(crypto_transport::CryptoTransport ct(sc, "ml-defender:sniffer:v1:tx"),
                 std::runtime_error);
}

// TC-CT-003: Round-trip encrypt/decrypt recupera el plaintext exacto
TEST_F(CryptoTransportTest, EncryptDecryptRoundTrip) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:sniffer:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:sniffer:v1:tx");

    const std::string msg = R"({"event":"flow","src":"192.168.1.1","dst":"10.0.0.1"})";
    std::vector<uint8_t> plaintext(msg.begin(), msg.end());

    auto recovered = rx.decrypt(tx.encrypt(plaintext));
    EXPECT_EQ(plaintext, recovered);
}

// TC-CT-004: Wire format = epoch_header(4) + nonce(12) + ciphertext(N) + mac(16)
TEST_F(CryptoTransportTest, WireFormatCorrect) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct(sc, "ml-defender:test:v1:tx");
    std::vector<uint8_t> plaintext(64, 0xAB);
    EXPECT_EQ(ct.encrypt(plaintext).size(), 4u + 12u + 64u + 16u);
}

// TC-CT-011: encrypt(p, epoch_id) + decrypt_v2 recupera epoch_id correcto
TEST_F(CryptoTransportTest, EpochIdRoundTrip) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");

    std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03};
    const uint16_t expected_epoch = 42;

    auto wire = tx.encrypt(plaintext, expected_epoch);
    auto result = rx.decrypt_v2(wire);

    EXPECT_EQ(result.data, plaintext);
    EXPECT_EQ(result.epoch_id, expected_epoch);
}

// TC-CT-012: wire format con epoch_id explícito tiene tamaño correcto
TEST_F(CryptoTransportTest, WireFormatWithEpochId) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct(sc, "ml-defender:test:v1:tx");
    std::vector<uint8_t> plaintext(64, 0xAB);
    EXPECT_EQ(ct.encrypt(plaintext, 7).size(), 4u + 12u + 64u + 16u);
}

// TC-CT-013: backward-compat encrypt() produce epoch_id=0 en wire header
TEST_F(CryptoTransportTest, BackwardCompatEpochIdIsZero) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");

    std::vector<uint8_t> plaintext = {0xDE, 0xAD};
    auto wire = tx.encrypt(plaintext);      // backward-compat -> epoch_id=0
    auto result = rx.decrypt_v2(wire);

    EXPECT_EQ(result.data, plaintext);
    EXPECT_EQ(result.epoch_id, 0u);
}

// TC-CT-005: Plaintext vacío → resultado vacío
TEST_F(CryptoTransportTest, EmptyPlaintextReturnsEmpty) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct(sc, "ml-defender:test:v1:tx");
    EXPECT_TRUE(ct.encrypt({}).empty());
    EXPECT_TRUE(ct.decrypt({}).empty());
}

// TC-CT-006: Nonce counter incrementa monótonamente
TEST_F(CryptoTransportTest, NonceCounterIncrementsMonotonically) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct(sc, "ml-defender:test:v1:tx");
    EXPECT_EQ(ct.nonce_count(), 0u);
    std::vector<uint8_t> data = {0x01, 0x02, 0x03};
    std::ignore = ct.encrypt(data); EXPECT_EQ(ct.nonce_count(), 1u);
    std::ignore = ct.encrypt(data); EXPECT_EQ(ct.nonce_count(), 2u);
}

// TC-CT-007: Dos cifrados del mismo plaintext producen ciphertexts distintos
TEST_F(CryptoTransportTest, ConsecutiveEncryptionsProduceDifferentCiphertexts) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct(sc, "ml-defender:test:v1:tx");
    std::vector<uint8_t> p = {0xDE, 0xAD, 0xBE, 0xEF};
    EXPECT_NE(ct.encrypt(p), ct.encrypt(p));
}

// TC-CT-008: Ciphertext manipulado → MAC failure
TEST_F(CryptoTransportTest, TamperedCiphertextThrows) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");
    auto ct = tx.encrypt({0x01, 0x02, 0x03, 0x04});
    ct[15] ^= 0xFF;
    EXPECT_THROW(rx.decrypt(ct), std::runtime_error);
}

// TC-CT-009: Contextos distintos → claves distintas → MAC failure al descifrar
TEST_F(CryptoTransportTest, DifferentContextsProduceDifferentKeys) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:sniffer:v1:tx");
    crypto_transport::CryptoTransport rx_wrong(sc, "ml-defender:sniffer:v1:rx");
    EXPECT_THROW(rx_wrong.decrypt(tx.encrypt({0xCA, 0xFE})), std::runtime_error);
}

// TC-CT-010: Move constructor — instancia movida descifra correctamente
TEST_F(CryptoTransportTest, MoveConstructorWorks) {
    auto sc = env_->make_client();
    crypto_transport::CryptoTransport ct1(sc, "ml-defender:test:v1:tx");
    std::vector<uint8_t> plaintext = {0x11, 0x22, 0x33};
    auto ciphertext = ct1.encrypt(plaintext);
    crypto_transport::CryptoTransport ct2(std::move(ct1));

    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");
    EXPECT_EQ(plaintext, rx.decrypt(ciphertext));
}
