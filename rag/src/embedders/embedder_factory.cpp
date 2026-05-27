// /vagrant/rag/src/embedders/embedder_factory.cpp

#include "embedders/embedder_factory.hpp"
#include "embedders/simple_embedder.hpp"
#include "embedders/cached_embedder.hpp"
#include <stdexcept>
#include <iostream>

namespace rag {

std::unique_ptr<IEmbedder> EmbedderFactory::create(
    Type type,
    const std::map<std::string, std::string>& config
) {
    validate_config(type, config);

    // Extraer config de cache (opcional)
    bool enable_cache = true;
    uint32_t cache_ttl = 300;
    size_t cache_max = 1000;

    if (config.count("cache_enabled")) {
        enable_cache = (config.at("cache_enabled") == "true");
    }
    if (config.count("cache_ttl_seconds")) {
        cache_ttl = std::stoul(config.at("cache_ttl_seconds"));
    }
    if (config.count("cache_max_entries")) {
        cache_max = std::stoull(config.at("cache_max_entries"));
    }

    // Crear embedder base
    std::unique_ptr<IEmbedder> embedder;

    switch (type) {
        case Type::SIMPLE:
            std::cout << "[Factory] Creating SimpleEmbedder" << std::endl;
            embedder = std::make_unique<SimpleEmbedder>();
            break;

        case Type::ONNX:
            throw std::runtime_error(
                "ONNXEmbedder not implemented yet (Phase 2B)"
            );

        case Type::SBERT:
            throw std::runtime_error(
                "SBERTEmbedder not implemented yet (Phase 3)"
            );

        default:
            throw std::runtime_error("Unknown embedder type");
    }

    // Wrap con cache si está habilitado
    if (enable_cache) {
        std::cout << "[Factory] Wrapping with cache (TTL="
                  << cache_ttl << "s, max=" << cache_max << ")" << std::endl;

        embedder = std::make_unique<CachedEmbedder>(
            std::move(embedder),
            cache_ttl,
            cache_max
        );
    }

    return embedder;
}

std::unique_ptr<IEmbedder> EmbedderFactory::create_from_string(
    const std::string& type_str,
    const std::map<std::string, std::string>& config
) {
    Type type = parse_type(type_str);
    return create(type, config);
}

EmbedderFactory::Type EmbedderFactory::parse_type(
    const std::string& type_str
) {
    if (type_str == "simple") return Type::SIMPLE;
    if (type_str == "onnx") return Type::ONNX;
    if (type_str == "sbert") return Type::SBERT;

    throw std::runtime_error(
        "Invalid embedder type: '" + type_str + "'. "
        "Available: simple, onnx, sbert"
    );
}

void EmbedderFactory::validate_config(
    Type type,
    const std::map<std::string, std::string>& config
) {
    switch (type) {
        case Type::SIMPLE:
            // No config required
            break;

        case Type::ONNX:
            if (config.count("chronos_model") == 0 ||
                config.count("sbert_model") == 0 ||
                config.count("attack_model") == 0) {
                throw std::runtime_error(
                    "ONNXEmbedder requires model paths"
                );
            }
            break;

        case Type::SBERT:
            // model_path optional
            break;
    }
}

} // namespace rag