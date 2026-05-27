#pragma once

#include <vector>
#include <cstdint>
#include <cstddef>

namespace crypto_transport {

    /**
     * Compress data using LZ4 algorithm
     * @param data Data to compress
     * @return Compressed data
     * @throws std::runtime_error if compression fails
     *
     * Note: Returns empty vector if input is empty
     * Warning: Compression may increase size for very small data
     */
    std::vector<uint8_t> compress(const std::vector<uint8_t>& data);

    /**
     * Decompress LZ4-compressed data
     * @param compressed_data Compressed data
     * @param original_size Original uncompressed size (must be exact)
     * @return Decompressed data
     * @throws std::runtime_error if decompression fails or size mismatch
     *
     * Note: Returns empty vector if input is empty
     * Critical: original_size must match exactly, or decompression fails
     */
    std::vector<uint8_t> decompress(const std::vector<uint8_t>& compressed_data,
                                     size_t original_size);

    /**
     * Check if data should be compressed based on size threshold
     * @param data_size Size of data in bytes
     * @param min_threshold Minimum size to consider compression (default: 256)
     * @return true if data_size >= min_threshold
     *
     * Rationale: Very small data often doesn't compress well and adds overhead
     */
    bool should_compress(size_t data_size, size_t min_threshold = 256);

    /**
     * Calculate compression ratio
     * @param original_size Original data size
     * @param compressed_size Compressed data size
     * @return Ratio (0.0 to 1.0+, lower is better)
     *
     * Example: 1000 bytes → 400 bytes = 0.40 ratio (60% reduction)
     */
    double get_compression_ratio(size_t original_size, size_t compressed_size);

} // namespace crypto_transport