// Compression Handler for eBPF Sniffer
// Handles LZ4, Zstd, and optional Snappy compression

#include "compression_handler.hpp"
#include <stdexcept>
#include <iostream>

#ifdef HAVE_LZ4
#include <lz4.h>
#include <lz4hc.h>
#endif

#ifdef HAVE_ZSTD
#include <zstd.h>
#endif

#ifdef HAVE_SNAPPY
#include <snappy.h>
#endif

namespace sniffer {

CompressionHandler::CompressionHandler() {
#ifdef HAVE_ZSTD
    zstd_cctx_ = ZSTD_createCCtx();
    zstd_dctx_ = ZSTD_createDCtx();
    if (!zstd_cctx_ || !zstd_dctx_) {
        throw std::runtime_error("Failed to create Zstd contexts");
    }
#endif
}

CompressionHandler::~CompressionHandler() {
#ifdef HAVE_ZSTD
    if (zstd_cctx_) ZSTD_freeCCtx(static_cast<ZSTD_CCtx*>(zstd_cctx_));
    if (zstd_dctx_) ZSTD_freeDCtx(static_cast<ZSTD_DCtx*>(zstd_dctx_));
#endif
}

std::vector<uint8_t> CompressionHandler::compress(
    const void* data, size_t size, CompressionType type) {

    switch (type) {
        case CompressionType::LZ4:
            return compress_lz4(data, size);
        case CompressionType::ZSTD:
            return compress_zstd(data, size);
        case CompressionType::SNAPPY:
            return compress_snappy(data, size);
        default:
            throw std::invalid_argument("Unknown compression type");
    }
}

std::vector<uint8_t> CompressionHandler::decompress(
    const void* data, size_t size, CompressionType type) {

    switch (type) {
        case CompressionType::LZ4:
            return decompress_lz4(data, size);
        case CompressionType::ZSTD:
            return decompress_zstd(data, size);
        case CompressionType::SNAPPY:
            return decompress_snappy(data, size);
        default:
            throw std::invalid_argument("Unknown compression type");
    }
}

std::vector<uint8_t> CompressionHandler::compress_lz4(const void* data, size_t size) {
#ifdef HAVE_LZ4
    const int max_compressed_size = LZ4_compressBound(static_cast<int>(size));
    std::vector<uint8_t> compressed(max_compressed_size);

    const int compressed_size = LZ4_compress_default(
        static_cast<const char*>(data),
        reinterpret_cast<char*>(compressed.data()),
        static_cast<int>(size),
        max_compressed_size
    );

    if (compressed_size <= 0) {
        throw std::runtime_error("LZ4 compression failed");
    }

    compressed.resize(compressed_size);
    return compressed;
#else
    throw std::runtime_error("LZ4 compression not available");
#endif
}

std::vector<uint8_t> CompressionHandler::decompress_lz4(const void* data, size_t size) {
#ifdef HAVE_LZ4
    // For simplicity, assume max decompressed size
    // In production, this should be stored with the compressed data
    const int max_decompressed_size = static_cast<int>(size * 10);
    std::vector<uint8_t> decompressed(max_decompressed_size);

    const int decompressed_size = LZ4_decompress_safe(
        static_cast<const char*>(data),
        reinterpret_cast<char*>(decompressed.data()),
        static_cast<int>(size),
        max_decompressed_size
    );

    if (decompressed_size < 0) {
        throw std::runtime_error("LZ4 decompression failed");
    }

    decompressed.resize(decompressed_size);
    return decompressed;
#else
    throw std::runtime_error("LZ4 decompression not available");
#endif
}

std::vector<uint8_t> CompressionHandler::compress_zstd(const void* data, size_t size) {
#ifdef HAVE_ZSTD
    const size_t max_compressed_size = ZSTD_compressBound(size);
    std::vector<uint8_t> compressed(max_compressed_size);

    const size_t compressed_size = ZSTD_compressCCtx(
        static_cast<ZSTD_CCtx*>(zstd_cctx_),
        compressed.data(),
        max_compressed_size,
        data,
        size,
        3  // Compression level
    );

    if (ZSTD_isError(compressed_size)) {
        throw std::runtime_error("Zstd compression failed: " +
                                std::string(ZSTD_getErrorName(compressed_size)));
    }

    compressed.resize(compressed_size);
    return compressed;
#else
    throw std::runtime_error("Zstd compression not available");
#endif
}

std::vector<uint8_t> CompressionHandler::decompress_zstd(const void* data, size_t size) {
#ifdef HAVE_ZSTD
    const unsigned long long decompressed_size = ZSTD_getFrameContentSize(data, size);

    if (decompressed_size == ZSTD_CONTENTSIZE_ERROR ||
        decompressed_size == ZSTD_CONTENTSIZE_UNKNOWN) {
        throw std::runtime_error("Cannot determine Zstd decompressed size");
    }

    std::vector<uint8_t> decompressed(decompressed_size);

    const size_t actual_size = ZSTD_decompressDCtx(
        static_cast<ZSTD_DCtx*>(zstd_dctx_),
        decompressed.data(),
        decompressed_size,
        data,
        size
    );

    if (ZSTD_isError(actual_size)) {
        throw std::runtime_error("Zstd decompression failed: " +
                                std::string(ZSTD_getErrorName(actual_size)));
    }

    return decompressed;
#else
    throw std::runtime_error("Zstd decompression not available");
#endif
}

std::vector<uint8_t> CompressionHandler::compress_snappy([[maybe_unused]] const void* data, [[maybe_unused]] size_t size) {
#ifdef HAVE_SNAPPY
    std::string compressed;
    snappy::Compress(static_cast<const char*>(data), size, &compressed);
    return std::vector<uint8_t>(compressed.begin(), compressed.end());
#else
    throw std::runtime_error("Snappy compression not available");
#endif
}

std::vector<uint8_t> CompressionHandler::decompress_snappy([[maybe_unused]] const void* data,[[maybe_unused]] size_t size) {
#ifdef HAVE_SNAPPY
    std::string decompressed;
    const std::string input(static_cast<const char*>(data), size);

    if (!snappy::Uncompress(input.data(), input.size(), &decompressed)) {
        throw std::runtime_error("Snappy decompression failed");
    }

    return std::vector<uint8_t>(decompressed.begin(), decompressed.end());
#else
    throw std::runtime_error("Snappy decompression not available");
#endif
}

double CompressionHandler::get_compression_ratio(size_t original_size, size_t compressed_size) {
    if (original_size == 0) return 0.0;
    return static_cast<double>(compressed_size) / static_cast<double>(original_size);
}

CompressionType CompressionHandler::get_best_compression_type([[maybe_unused]] const void* data, [[maybe_unused]] size_t size) {
    // For network packets, LZ4 is usually best balance of speed/compression
    // Zstd for better compression ratio if CPU allows
    if (size < 1024) {
        return CompressionType::LZ4;  // Fast for small packets
    } else {
        return CompressionType::ZSTD; // Better ratio for larger data
    }
}

} // namespace sniffer