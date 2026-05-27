// /vagrant/rag/include/embedders/embedder_interface.hpp
#pragma once

#include <vector>
#include <string>
#include <tuple>

namespace rag {

    /**
     * @brief Interface base para embedders (Phase 2A integration)
     *
     * NOTA: Versión simplificada para integración inicial
     * No requiere network_event.pb.h por ahora
     */
    class IEmbedder {
    public:
        virtual ~IEmbedder() = default;

        /**
         * @brief Genera embedding para búsqueda chronological
         * @param features Vector de features (103-105 dims)
         * @return Embedding chronos (128-d por defecto)
         */
        virtual std::vector<float> embed_chronos(
            const std::vector<float>& features
        ) = 0;

        /**
         * @brief Genera embedding para búsqueda semántica
         * @param features Vector de features (103-105 dims)
         * @return Embedding SBERT (96-d por defecto)
         */
        virtual std::vector<float> embed_sbert(
            const std::vector<float>& features
        ) = 0;

        /**
         * @brief Genera embedding para búsqueda de ataques
         * @param features Vector de features (103-105 dims)
         * @return Embedding attack (64-d por defecto)
         */
        virtual std::vector<float> embed_attack(
            const std::vector<float>& features
        ) = 0;

        virtual std::string name() const = 0;
        virtual std::tuple<size_t, size_t, size_t> dimensions() const = 0;
        virtual int effectiveness_percent() const = 0;
        virtual std::string capabilities() const = 0;
    };

} // namespace rag