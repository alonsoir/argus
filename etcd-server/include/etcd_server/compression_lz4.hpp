#pragma once
#include <string>

namespace compression {
    std::string decompress_lz4(const std::string& compressed_data, size_t original_size);
}
