#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <cmath>

namespace sniffer {

/**
 * @brief Thread-safe payload analyzer for malware detection
 * 
 * Analyzes packet payloads for:
 * - PE executable headers (Windows malware)
 * - Shannon entropy (encrypted/packed content)
 * - Suspicious patterns (ransom notes, crypto APIs)
 * 
 * Design:
 * - Thread-local state (no locks needed)
 * - Performance target: <10μs per 512-byte analysis
 * - Compatible with Layer 1 FastDetector architecture
 */
class PayloadAnalyzer {
public:
    /**
     * @brief Analysis results for a single payload
     */
    struct Features {
        // PE Executable Detection
        bool is_pe_executable{false};      ///< MZ/PE header detected
        uint16_t pe_machine_type{0};       ///< CPU architecture (x86, x64, ARM)
        uint32_t pe_timestamp{0};          ///< PE compilation timestamp
        
        // Entropy Analysis
        float entropy{0.0f};               ///< Shannon entropy (0.0-8.0 bits)
        bool high_entropy{false};          ///< >7.0 = likely encrypted/packed
        
        // Pattern Matching
        bool ransom_note_pattern{false};   ///< Ransom message detected
        bool crypto_api_pattern{false};    ///< Crypto API strings found
        uint16_t suspicious_strings{0};    ///< Count of suspicious patterns
        
        // Metadata
        uint16_t analyzed_bytes{0};        ///< Actual bytes analyzed
    };
    
    PayloadAnalyzer() = default;
    ~PayloadAnalyzer() = default;
    
    // Non-copyable (thread_local instance)
    PayloadAnalyzer(const PayloadAnalyzer&) = delete;
    PayloadAnalyzer& operator=(const PayloadAnalyzer&) = delete;
    
    /**
     * @brief Analyze a packet payload
     * 
     * @param payload Raw packet data (can be nullptr if len=0)
     * @param len Payload length (max 512 bytes typically)
     * @return Features struct with analysis results
     * 
     * Thread-safe: Uses only thread_local state
     * Performance: <10μs for 512 bytes
     */
    Features analyze(const uint8_t* payload, uint16_t len);
    
    /**
     * @brief Reset internal state (optional, for testing)
     */
    void reset();
    
private:
    // ===== PE Header Detection =====
    
    /**
     * @brief Check for PE executable signature
     * 
     * Validates:
     * - "MZ" magic (DOS header)
     * - PE signature location
     * - "PE\0\0" magic
     * - COFF header structure
     * 
     * @return true if valid PE file detected
     */
    bool check_pe_header(const uint8_t* data, uint16_t len);
    
    /**
     * @brief Extract PE machine type from COFF header
     * 
     * Common values:
     * - 0x014c: Intel 386 (x86)
     * - 0x8664: x64 (AMD64)
     * - 0x01c0: ARM
     * - 0xaa64: ARM64
     * 
     * @return Machine type or 0 if not PE
     */
    uint16_t extract_pe_machine_type(const uint8_t* data, uint16_t len);
    
    /**
     * @brief Extract PE compilation timestamp
     * @return Unix timestamp or 0 if not PE
     */
    uint32_t extract_pe_timestamp(const uint8_t* data, uint16_t len);
    
    // ===== Entropy Analysis =====
    
    /**
     * @brief Fast Shannon entropy calculation
     * 
     * Uses lookup table optimization for log2.
     * Formula: H = -Σ(p_i * log2(p_i))
     * 
     * Interpretation:
     * - 0.0-4.0: Plain text / low entropy
     * - 4.0-6.0: Compressed / medium entropy
     * - 6.0-7.0: Well compressed
     * - 7.0-8.0: Encrypted / highly random
     * 
     * @return Entropy in bits (0.0-8.0)
     */
    float calculate_entropy_fast(const uint8_t* data, uint16_t len);
    
    // ===== Pattern Matching =====
    
    /**
     * @brief Search for ransom note patterns
     * 
     * Patterns:
     * - "YOUR FILES HAVE BEEN ENCRYPTED"
     * - "DECRYPT", "RANSOM", "BITCOIN"
     * - ".onion" addresses
     * - Wallet addresses
     * 
     * @return true if ransom-related content found
     */
    bool match_ransom_patterns(const uint8_t* data, uint16_t len);
    
    /**
     * @brief Search for cryptographic API strings
     * 
     * Patterns:
     * - "CryptEncrypt", "CryptDecrypt"
     * - "AES", "RSA", "ChaCha"
     * - OpenSSL function names
     * 
     * @return true if crypto API strings found
     */
    bool match_crypto_api_patterns(const uint8_t* data, uint16_t len);
    
    /**
     * @brief Count all suspicious string patterns
     * @return Total count of suspicious strings
     */
    uint16_t count_suspicious_strings(const uint8_t* data, uint16_t len);
    
    /**
     * @brief Case-insensitive substring search
     * 
     * Uses fast Boyer-Moore-like approach for long patterns.
     * Falls back to simple search for short patterns (<4 bytes).
     * 
     * @param haystack Data to search in
     * @param haystack_len Length of data
     * @param needle Pattern to find
     * @param needle_len Length of pattern
     * @return true if pattern found
     */
    bool find_pattern_nocase(const uint8_t* haystack, uint16_t haystack_len,
                             const char* needle, uint16_t needle_len);
    
    // ===== Thread-local State =====
    
    /// Byte frequency table for entropy calculation (reused across calls)
    std::array<uint32_t, 256> byte_freq_{};
    
    /// Pre-computed log2 lookup table for byte frequencies (0-256)
    /// Note: For len > 256, we calculate log2(len) dynamically
    static constexpr float log2_table_[257] = {
        0.0f, 0.0f, 1.0f, 1.585f, 2.0f, 2.322f, 2.585f, 2.807f,
        3.0f, 3.17f, 3.322f, 3.459f, 3.585f, 3.7f, 3.807f, 3.907f,
        4.0f, 4.087f, 4.17f, 4.248f, 4.322f, 4.392f, 4.459f, 4.524f,
        4.585f, 4.644f, 4.7f, 4.755f, 4.807f, 4.858f, 4.907f, 4.954f,
        5.0f, 5.044f, 5.087f, 5.129f, 5.17f, 5.209f, 5.248f, 5.285f,
        5.322f, 5.358f, 5.392f, 5.426f, 5.459f, 5.492f, 5.524f, 5.555f,
        5.585f, 5.615f, 5.644f, 5.672f, 5.7f, 5.728f, 5.755f, 5.781f,
        5.807f, 5.833f, 5.858f, 5.883f, 5.907f, 5.931f, 5.954f, 5.977f,
        6.0f, 6.022f, 6.044f, 6.066f, 6.087f, 6.109f, 6.129f, 6.15f,
        6.17f, 6.19f, 6.209f, 6.229f, 6.248f, 6.267f, 6.285f, 6.304f,
        6.322f, 6.34f, 6.358f, 6.375f, 6.392f, 6.41f, 6.426f, 6.443f,
        6.459f, 6.476f, 6.492f, 6.508f, 6.524f, 6.539f, 6.555f, 6.57f,
        6.585f, 6.6f, 6.615f, 6.629f, 6.644f, 6.658f, 6.672f, 6.686f,
        6.7f, 6.714f, 6.728f, 6.741f, 6.755f, 6.768f, 6.781f, 6.795f,
        6.807f, 6.82f, 6.833f, 6.845f, 6.858f, 6.87f, 6.883f, 6.895f,
        6.907f, 6.918f, 6.931f, 6.943f, 6.954f, 6.966f, 6.977f, 6.988f,
        7.0f, 7.011f, 7.022f, 7.033f, 7.044f, 7.055f, 7.066f, 7.077f,
        7.087f, 7.098f, 7.109f, 7.119f, 7.129f, 7.14f, 7.15f, 7.16f,
        7.17f, 7.18f, 7.19f, 7.2f, 7.209f, 7.219f, 7.229f, 7.238f,
        7.248f, 7.257f, 7.267f, 7.276f, 7.285f, 7.295f, 7.304f, 7.313f,
        7.322f, 7.331f, 7.34f, 7.349f, 7.358f, 7.366f, 7.375f, 7.384f,
        7.392f, 7.401f, 7.41f, 7.418f, 7.426f, 7.435f, 7.443f, 7.451f,
        7.459f, 7.468f, 7.476f, 7.484f, 7.492f, 7.5f, 7.508f, 7.516f,
        7.524f, 7.531f, 7.539f, 7.547f, 7.555f, 7.562f, 7.57f, 7.577f,
        7.585f, 7.593f, 7.6f, 7.607f, 7.615f, 7.622f, 7.629f, 7.636f,
        7.644f, 7.651f, 7.658f, 7.665f, 7.672f, 7.679f, 7.686f, 7.693f,
        7.7f, 7.707f, 7.714f, 7.72f, 7.728f, 7.734f, 7.741f, 7.748f,
        7.755f, 7.761f, 7.768f, 7.775f, 7.781f, 7.788f, 7.795f, 7.801f,
        7.807f, 7.814f, 7.82f, 7.827f, 7.833f, 7.839f, 7.845f, 7.852f,
        7.858f, 7.864f, 7.87f, 7.877f, 7.883f, 7.889f, 7.895f, 7.901f,
        7.907f, 7.913f, 7.918f, 7.925f, 7.931f, 7.937f, 7.943f, 7.948f,
        7.954f, 7.96f, 7.966f, 7.977f, 7.988f, 8.0f, 8.011f  // Extended for common sizes
    };
};

} // namespace sniffer
