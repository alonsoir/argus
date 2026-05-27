// etcd-client/src/compression_lz4.cpp
#include <lz4.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstring>

namespace etcd_client {
namespace compression {

// Compress data using LZ4
std::string compress_lz4(const std::string& data) {
    if (data.empty()) {
        return "";
    }
    
    // Calculate max compressed size
    int max_compressed_size = LZ4_compressBound(data.size());
    if (max_compressed_size == 0) {
        throw std::runtime_error("LZ4_compressBound failed");
    }
    
    // Allocate buffer for compressed data
    std::vector<char> compressed(max_compressed_size);
    
    // Compress
    int compressed_size = LZ4_compress_default(
        data.data(),
        compressed.data(),
        data.size(),
        max_compressed_size
    );
    
    if (compressed_size <= 0) {
        throw std::runtime_error("LZ4 compression failed");
    }
    
    // Return compressed data (resize to actual size)
    return std::string(compressed.data(), compressed_size);
}

// Decompress data using LZ4
std::string decompress_lz4(const std::string& compressed_data, size_t original_size) {
    if (compressed_data.empty()) {
        return "";
    }
    
    // Allocate buffer for decompressed data
    std::vector<char> decompressed(original_size);
    
    // Decompress
    int decompressed_size = LZ4_decompress_safe(
        compressed_data.data(),
        decompressed.data(),
        compressed_data.size(),
        original_size
    );
    
    if (decompressed_size < 0) {
        throw std::runtime_error("LZ4 decompression failed (corrupted data?)");
    }
    
    if (static_cast<size_t>(decompressed_size) != original_size) {
        throw std::runtime_error("LZ4 decompression size mismatch");
    }
    
    return std::string(decompressed.data(), decompressed_size);
}

// Check if data should be compressed based on size threshold
bool should_compress(size_t data_size, size_t min_size_threshold) {
    return data_size >= min_size_threshold;
}

// Get compression ratio
double get_compression_ratio(size_t original_size, size_t compressed_size) {
    if (original_size == 0) return 1.0;
    return static_cast<double>(compressed_size) / static_cast<double>(original_size);
}

} // namespace compression
} // namespace etcd_client
