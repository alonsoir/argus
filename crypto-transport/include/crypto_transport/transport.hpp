#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <string>
#include <vector>
#include <seed_client/seed_client.hpp>

namespace crypto_transport {

/**
 * @brief RAII session with HKDF-derived key and monotonic 96-bit nonce.
 *
 * Replaces CryptoManager for components that integrate with the seed-client
 * trust chain. Key derivation uses RFC 5869 HKDF-SHA256 via libsodium 1.0.19
 * native API (crypto_kdf_hkdf_sha256_extract / expand).
 *
 * Encryption: ChaCha20-Poly1305 IETF (12-byte nonce, 16-byte MAC).
 * Nonce policy: monotonic counter, 96-bit = [0x00000000 || uint64_LE].
 *
 * Wire format: [nonce(12) || ciphertext(N) || mac(16)]
 *
 * TX and RX MUST use separate instances with different contexts:
 *   CryptoTransport tx(sc, "ml-defender:sniffer:v1:tx");
 *   CryptoTransport rx(sc, "ml-defender:sniffer:v1:rx");
 *
 * ADR refs: ADR-013 PHASE 2, ADR-020, DEBT-CRYPTO-001, DEBT-CRYPTO-002
 */
class CryptoTransport {
public:
    static constexpr size_t KEY_SIZE         = 32;
    static constexpr size_t NONCE_SIZE       = 12;
    static constexpr size_t MAC_SIZE         = 16;
    static constexpr size_t EPOCH_HEADER_SIZE = 4; // uint16_t epoch_id LE + 2B reserved

    /**
     * @brief Result of decrypt_v2: decrypted data + epoch_id from wire header.
     */
    struct DecryptResult {
        std::vector<uint8_t> data;
        uint16_t             epoch_id{0};
    };

    /**
     * @brief Construct and immediately derive session key via HKDF-SHA256.
     *
     * @param seed_client  Fully loaded SeedClient (is_loaded() must be true).
     * @param context      HKDF info: "ml-defender:{component}:{version}:{tx|rx}"
     * @throws std::runtime_error if seed_client not loaded or HKDF fails.
     */
    explicit CryptoTransport(const ml_defender::SeedClient& seed_client,
                             const std::string& context = "ml-defender:transport:v1:tx");

    ~CryptoTransport();

    CryptoTransport(CryptoTransport&&) noexcept;
    CryptoTransport& operator=(CryptoTransport&&) noexcept;

    CryptoTransport(const CryptoTransport&)            = delete;
    CryptoTransport& operator=(const CryptoTransport&) = delete;

    /**
     * @brief Encrypt plaintext with epoch_id in wire header.
     * @return [epoch_id(2) || reserved(2) || nonce(12) || ciphertext(N) || mac(16)]
     * @throws std::runtime_error if AEAD encryption fails.
     */
    [[nodiscard]] std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext,
                                                uint16_t epoch_id);

    /**
     * @brief Decrypt wire-format buffer, returning data + epoch_id.
     * @throws std::runtime_error on MAC failure or truncated input.
     */
    [[nodiscard]] DecryptResult decrypt_v2(const std::vector<uint8_t>& ciphertext);

    /**
     * @brief Backward-compat: encrypt with epoch_id=0.
     * @return [epoch_id=0(2) || reserved(2) || nonce(12) || ciphertext(N) || mac(16)]
     */
    [[nodiscard]] std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext);

    /**
     * @brief Backward-compat: decrypt, discards epoch_id.
     * @throws std::runtime_error on MAC failure or truncated input.
     */
    [[nodiscard]] std::vector<uint8_t> decrypt(const std::vector<uint8_t>& ciphertext);

    /** Current nonce counter — for diagnostics only. */
    [[nodiscard]] uint64_t nonce_count() const noexcept;

private:
    void derive_key(const std::array<uint8_t, 32>& ikm, const std::string& context);
    [[nodiscard]] std::array<uint8_t, NONCE_SIZE> next_nonce();

    std::array<uint8_t, KEY_SIZE> session_key_{};
    std::atomic<uint64_t>         nonce_counter_{0};
};

} // namespace crypto_transport
