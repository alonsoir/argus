#pragma once
// sniffer/src/userspace/compression_handler.hpp
#include <vector>
#include <cstdint>
#include <cstddef>

namespace sniffer {

/**
 * @brief Compression types available
 */
enum class CompressionType {
    LZ4,     ///< LZ4 - Fast compression/decompression
    ZSTD,    ///< Zstandard - Better compression ratio
    SNAPPY   ///< Snappy - Google's fast compression (optional)
};

/**
 * @brief Compression Handler for packet data
 *
 * Handles compression/decompression of network packet data using
 * multiple algorithms (LZ4, Zstd, Snappy) for optimal performance
 * in different scenarios.
 */
class CompressionHandler {
public:
    /**
     * @brief Construct compression handler
     */
    CompressionHandler();

    /**
     * @brief Destructor - cleanup compression contexts
     */
    ~CompressionHandler();

    // Non-copyable
    CompressionHandler(const CompressionHandler&) = delete;
    CompressionHandler& operator=(const CompressionHandler&) = delete;

    /**
     * @brief Compress data using specified algorithm
     * @param data Data to compress
     * @param size Size of data
     * @param type Compression algorithm to use
     * @return Compressed data
     */
    std::vector<uint8_t> compress(const void* data, size_t size, CompressionType type);

    /**
     * @brief Decompress data using specified algorithm
     * @param data Compressed data
     * @param size Size of compressed data
     * @param type Compression algorithm used
     * @return Decompressed data
     */
    std::vector<uint8_t> decompress(const void* data, size_t size, CompressionType type);

    /**
     * @brief Get compression ratio
     * @param original_size Original data size
     * @param compressed_size Compressed data size
     * @return Compression ratio (compressed/original)
     */
    static double get_compression_ratio(size_t original_size, size_t compressed_size);

    /**
     * @brief Get best compression type for data
     * @param data Sample data to analyze
     * @param size Size of sample data
     * @return Recommended compression type
     */
    static CompressionType get_best_compression_type(const void* data, size_t size);

    // LZ4 compression/decompression
    std::vector<uint8_t> compress_lz4(const void* data, size_t size);
    std::vector<uint8_t> decompress_lz4(const void* data, size_t size);

    // Zstd compression/decompression
    std::vector<uint8_t> compress_zstd(const void* data, size_t size);
    std::vector<uint8_t> decompress_zstd(const void* data, size_t size);

    // Snappy compression/decompression
    std::vector<uint8_t> compress_snappy(const void* data, size_t size);
    std::vector<uint8_t> decompress_snappy(const void* data, size_t size);

private:


    // Compression contexts (for thread-safety and performance)
    void* zstd_cctx_{nullptr};  ///< Zstd compression context
    void* zstd_dctx_{nullptr};  ///< Zstd decompression context
};

} // namespace sniffer