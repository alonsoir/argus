// crypto-transport/src/compression.cpp
#include "crypto_transport/compression.hpp"
#include <lz4.h>
#include <stdexcept>
#include <cstring>

namespace crypto_transport {

    std::vector<uint8_t> compress(const std::vector<uint8_t>& data) {
        if (data.empty()) {
            return {};
        }

        // Calculate max compressed size
        int max_compressed_size = LZ4_compressBound(static_cast<int>(data.size()));
        if (max_compressed_size == 0) {
            throw std::runtime_error("LZ4_compressBound failed (data too large?)");
        }

        // Allocate buffer for compressed data
        std::vector<uint8_t> compressed(max_compressed_size);

        // Compress
        int compressed_size = LZ4_compress_default(
            reinterpret_cast<const char*>(data.data()),
            reinterpret_cast<char*>(compressed.data()),
            static_cast<int>(data.size()),
            max_compressed_size
        );

        if (compressed_size <= 0) {
            throw std::runtime_error("LZ4 compression failed");
        }

        // ===================================================================
        // REMOVED: No header needed - caller tracks original_size separately
        // ===================================================================
        compressed.resize(compressed_size);
        return compressed;
    }

    std::vector<uint8_t> decompress(const std::vector<uint8_t>& compressed_data,
                                     size_t original_size) {
        if (compressed_data.empty()) {
            return {};
        }

        if (original_size == 0) {
            throw std::runtime_error("Original size must be > 0 for decompression");
        }

        // Allocate buffer for decompressed data
        std::vector<uint8_t> decompressed(original_size);

        // Decompress (no header - just pure LZ4 data)
        int decompressed_size = LZ4_decompress_safe(
            reinterpret_cast<const char*>(compressed_data.data()),
            reinterpret_cast<char*>(decompressed.data()),
            static_cast<int>(compressed_data.size()),
            static_cast<int>(original_size)
        );

        if (decompressed_size < 0) {
            throw std::runtime_error("LZ4 decompression failed (corrupted data?)");
        }

        if (static_cast<size_t>(decompressed_size) != original_size) {
            throw std::runtime_error("LZ4 decompression size mismatch (expected " +
                                     std::to_string(original_size) + " got " +
                                     std::to_string(decompressed_size) + ")");
        }

        return decompressed;
    }

bool should_compress(size_t data_size, size_t min_threshold) {
    return data_size >= min_threshold;
}

double get_compression_ratio(size_t original_size, size_t compressed_size) {
    if (original_size == 0) {
        return 1.0;
    }
    return static_cast<double>(compressed_size) / static_cast<double>(original_size);
}

} // namespace crypto_transport
