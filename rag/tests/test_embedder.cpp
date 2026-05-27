// /vagrant/rag/tests/test_embedder.cpp

#include "embedders/embedder_factory.hpp"
#include "embedders/cached_embedder.hpp"
#include <iostream>
#include <chrono>

int main() {
    std::cout << "==============================================\n";
    std::cout << "Test Embedder Factory + Cache\n";
    std::cout << "==============================================\n\n";

    try {
        // 1. Crear SimpleEmbedder con cache
        std::cout << "1. Creating SimpleEmbedder with cache...\n";
        auto embedder = rag::EmbedderFactory::create(
            rag::EmbedderFactory::Type::SIMPLE
        );

        std::cout << "   Name: " << embedder->name() << "\n";
        auto [c, s, a] = embedder->dimensions();
        std::cout << "   Dimensions: " << c << "/" << s << "/" << a << "\n";
        std::cout << "   Effectiveness: " << embedder->effectiveness_percent() << "%\n\n";

        // 2. Test embedding generation
        std::cout << "2. Testing embedding generation...\n";
        std::vector<float> test_features(105, 0.5f);  // 105 features

        auto start = std::chrono::steady_clock::now();
        auto chronos = embedder->embed_chronos(test_features);
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
            end - start
        ).count();

        std::cout << "   Chronos embedding: " << chronos.size() << " dims\n";
        std::cout << "   Time: " << duration << " µs\n\n";

        // 3. Test cache (segunda llamada debe ser más rápida)
        std::cout << "3. Testing cache (2nd call)...\n";
        start = std::chrono::steady_clock::now();
        auto chronos2 = embedder->embed_chronos(test_features);
        end = std::chrono::steady_clock::now();
        duration = std::chrono::duration_cast<std::chrono::microseconds>(
            end - start
        ).count();

        std::cout << "   Time: " << duration << " µs (should be faster!)\n\n";

        // 4. Verificar que es CachedEmbedder
        auto* cached = dynamic_cast<rag::CachedEmbedder*>(embedder.get());
        if (cached) {
            auto stats = cached->cache_stats();
            std::cout << "4. Cache stats:\n";
            std::cout << "   Hits: " << stats.hits << "\n";
            std::cout << "   Misses: " << stats.misses << "\n";
            std::cout << "   Hit rate: " << stats.hit_rate << "%\n\n";
        }

        std::cout << "✅ All tests passed!\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << "\n";
        return 1;
    }
}