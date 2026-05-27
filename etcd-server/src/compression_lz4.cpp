// etcd-server/src/compression_lz4.cpp
#include <lz4.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <iostream>

namespace compression {

std::string decompress_lz4(const std::string& compressed_data, size_t original_size) {
    if (compressed_data.empty()) {
        return "";
    }
    
    std::vector<char> decompressed(original_size);
    
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
    
    std::cout << "[COMPRESSION] 📦 Descomprimido: " << compressed_data.size() 
              << " → " << decompressed_size << " bytes" << std::endl;
    
    return std::string(decompressed.data(), decompressed_size);
}

} // namespace compression
