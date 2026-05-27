// /vagrant/rag/include/embedders/embedder_factory.hpp
#pragma once

#include "embedder_interface.hpp"
#include <memory>
#include <string>
#include <map>

namespace rag {

    class EmbedderFactory {
    public:
        enum class Type {
            SIMPLE,      // Random projection (Phase 2A)
            ONNX,        // ONNX models (Phase 2B - futuro)
            SBERT        // Sentence-BERT (Phase 3 - futuro)
        };

        /**
         * @brief Crea embedder según tipo
         * @param type Tipo de embedder
         * @param config Configuración (opcional)
         * @return Embedder creado
         */
        static std::unique_ptr<IEmbedder> create(
            Type type,
            const std::map<std::string, std::string>& config = {}
        );

        /**
         * @brief Crea embedder desde string
         * @param type_str "simple", "onnx", "sbert"
         * @param config Configuración
         * @return Embedder creado
         */
        static std::unique_ptr<IEmbedder> create_from_string(
            const std::string& type_str,
            const std::map<std::string, std::string>& config = {}
        );

    private:
        static Type parse_type(const std::string& type_str);
        static void validate_config(
            Type type,
            const std::map<std::string, std::string>& config
        );
    };

} // namespace rag