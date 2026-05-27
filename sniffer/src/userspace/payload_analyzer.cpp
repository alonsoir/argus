#include "payload_analyzer.hpp"
#include <algorithm>
#include <cctype>

namespace sniffer {

// ===== Public Interface =====

PayloadAnalyzer::Features PayloadAnalyzer::analyze(const uint8_t* payload, uint16_t len) {
    Features features;
    
    // Safety check
    if (!payload || len == 0) {
        return features;
    }
    
    features.analyzed_bytes = len;
    
    // 1. PE Header Detection (~1-2μs)
    features.is_pe_executable = check_pe_header(payload, len);
    if (features.is_pe_executable) {
        features.pe_machine_type = extract_pe_machine_type(payload, len);
        features.pe_timestamp = extract_pe_timestamp(payload, len);
    }
    
    // 2. Entropy Analysis (~5-7μs for 512 bytes)
    features.entropy = calculate_entropy_fast(payload, len);
    features.high_entropy = (features.entropy > 7.0f);
    
    // 3. Lazy Pattern Matching: Only if suspicious
    // Optimization: Skip expensive pattern matching for normal traffic
    // Trigger: High entropy (>7.0) OR PE executable detected
    if (features.high_entropy || features.is_pe_executable) {
        // Pattern matching only for suspicious payloads (~100μs)
        features.ransom_note_pattern = match_ransom_patterns(payload, len);
        features.crypto_api_pattern = match_crypto_api_patterns(payload, len);
        features.suspicious_strings = count_suspicious_strings(payload, len);
    } else {
        // Fast path: skip pattern matching for normal traffic
        features.ransom_note_pattern = false;
        features.crypto_api_pattern = false;
        features.suspicious_strings = 0;
    }
    
    return features;
}

void PayloadAnalyzer::reset() {
    byte_freq_.fill(0);
}

// ===== PE Header Detection =====

bool PayloadAnalyzer::check_pe_header(const uint8_t* data, uint16_t len) {
    // Need at least DOS header (64 bytes)
    if (len < 64) {
        return false;
    }
    
    // Check MZ signature (DOS header)
    if (data[0] != 'M' || data[1] != 'Z') {
        return false;
    }
    
    // Get PE header offset (at offset 0x3C in DOS header)
    uint32_t pe_offset = data[0x3C] | (data[0x3D] << 8) | 
                         (data[0x3E] << 16) | (data[0x3F] << 24);
    
    // PE offset sanity check (should be < 1024 typically)
    // Cast len to uint32_t to avoid signed/unsigned comparison warning
    if (pe_offset + 4 > static_cast<uint32_t>(len) || pe_offset > 1024) {
        return false;
    }
    
    // Check PE signature "PE\0\0"
    if (data[pe_offset] != 'P' || data[pe_offset + 1] != 'E' ||
        data[pe_offset + 2] != 0 || data[pe_offset + 3] != 0) {
        return false;
    }
    
    return true;
}

uint16_t PayloadAnalyzer::extract_pe_machine_type(const uint8_t* data, uint16_t len) {
    if (!check_pe_header(data, len)) {
        return 0;
    }
    
    uint32_t pe_offset = data[0x3C] | (data[0x3D] << 8) | 
                         (data[0x3E] << 16) | (data[0x3F] << 24);
    
    // Machine type is at PE_offset + 4 (COFF header start)
    if (pe_offset + 6 > len) {
        return 0;
    }
    
    uint16_t machine_type = data[pe_offset + 4] | (data[pe_offset + 5] << 8);
    return machine_type;
}

uint32_t PayloadAnalyzer::extract_pe_timestamp(const uint8_t* data, uint16_t len) {
    if (!check_pe_header(data, len)) {
        return 0;
    }
    
    uint32_t pe_offset = data[0x3C] | (data[0x3D] << 8) | 
                         (data[0x3E] << 16) | (data[0x3F] << 24);
    
    // Timestamp is at PE_offset + 8 (COFF header, 4 bytes)
    if (pe_offset + 12 > len) {
        return 0;
    }
    
    uint32_t timestamp = data[pe_offset + 8] | (data[pe_offset + 9] << 8) |
                        (data[pe_offset + 10] << 16) | (data[pe_offset + 11] << 24);
    return timestamp;
}

// ===== Entropy Analysis =====

float PayloadAnalyzer::calculate_entropy_fast(const uint8_t* data, uint16_t len) {
    if (len == 0) {
        return 0.0f;
    }
    
    // Reset frequency table
    byte_freq_.fill(0);
    
    // Count byte frequencies
    for (uint16_t i = 0; i < len; ++i) {
        byte_freq_[data[i]]++;
    }
    
    // Calculate Shannon entropy: H = -Σ(p * log2(p))
    // Optimized: H = -Σ((freq/len) * (log2(freq) - log2(len)))
    //              = -Σ((freq/len) * log2(freq)) + log2(len)
    
    float entropy = 0.0f;
    const float len_f = static_cast<float>(len);
    
    // Calculate log2(len) dynamically (not in lookup table for len > 256)
    const float log2_len = (len <= 256) ? log2_table_[len] : std::log2f(len_f);
    
    for (uint32_t freq : byte_freq_) {
        if (freq > 0) {
            // Use lookup table for frequencies (always <= len <= 512)
            const float log2_freq = (freq <= 256) ? log2_table_[freq] : std::log2f(static_cast<float>(freq));
            
            // H -= (freq/len) * (log2(freq) - log2(len))
            entropy -= (static_cast<float>(freq) / len_f) * (log2_freq - log2_len);
        }
    }
    
    return entropy;
}

// ===== Pattern Matching =====

bool PayloadAnalyzer::match_ransom_patterns(const uint8_t* data, uint16_t len) {
    // Common ransom note patterns
    static const char* patterns[] = {
        "ENCRYPTED",
        "DECRYPT",
        "RANSOM",
        "BITCOIN",
        "BTC",
        "PAYMENT",
        "YOUR FILES",
        ".onion",
        "WALLET",
        "RESTORE",
        "LOCKED"
    };
    
    for (const char* pattern : patterns) {
        if (find_pattern_nocase(data, len, pattern, std::strlen(pattern))) {
            return true;
        }
    }
    
    return false;
}

bool PayloadAnalyzer::match_crypto_api_patterns(const uint8_t* data, uint16_t len) {
    // Cryptographic API strings (Windows Crypto API, OpenSSL, etc.)
    static const char* patterns[] = {
        "CryptEncrypt",
        "CryptDecrypt",
        "CryptAcquireContext",
        "AES",
        "RSA",
        "ChaCha",
        "Salsa20",
        "CryptGenKey",
        "BCryptEncrypt",
        "OpenSSL",
        "EVP_Encrypt",
        "EVP_Decrypt"
    };
    
    for (const char* pattern : patterns) {
        if (find_pattern_nocase(data, len, pattern, std::strlen(pattern))) {
            return true;
        }
    }
    
    return false;
}

uint16_t PayloadAnalyzer::count_suspicious_strings(const uint8_t* data, uint16_t len) {
    uint16_t count = 0;
    
    // Combine all suspicious patterns
    static const char* patterns[] = {
        // Ransom-related
        "ENCRYPTED", "DECRYPT", "RANSOM", "BITCOIN", "BTC",
        "PAYMENT", "YOUR FILES", ".onion", "WALLET", "RESTORE", "LOCKED",
        
        // Crypto APIs
        "CryptEncrypt", "CryptDecrypt", "AES", "RSA", "ChaCha",
        
        // File operations (mass file access)
        "DeleteFile", "MoveFile", "CopyFile",
        
        // Network exfiltration
        "InternetOpen", "HttpSendRequest", "send", "recv",
        
        // Suspicious registry
        "RegSetValue", "HKEY_LOCAL_MACHINE",
        
        // Anti-analysis
        "IsDebuggerPresent", "VirtualProtect", "CreateRemoteThread"
    };
    
    for (const char* pattern : patterns) {
        if (find_pattern_nocase(data, len, pattern, std::strlen(pattern))) {
            ++count;
        }
    }
    
    return count;
}

bool PayloadAnalyzer::find_pattern_nocase(const uint8_t* haystack, uint16_t haystack_len,
                                          const char* needle, uint16_t needle_len) {
    if (needle_len > haystack_len || needle_len == 0) {
        return false;
    }
    
    // Simple case-insensitive search
    // For better performance with long patterns, could use Boyer-Moore
    for (uint16_t i = 0; i <= haystack_len - needle_len; ++i) {
        bool match = true;
        for (uint16_t j = 0; j < needle_len; ++j) {
            if (std::tolower(haystack[i + j]) != std::tolower(static_cast<unsigned char>(needle[j]))) {
                match = false;
                break;
            }
        }
        if (match) {
            return true;
        }
    }
    
    return false;
}

} // namespace sniffer
