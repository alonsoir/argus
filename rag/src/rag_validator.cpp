#include "rag/rag_validator.hpp"

namespace Rag {

    RagValidator::RagValidator() {
        registerValidationRules();
    }

    void RagValidator::registerValidationRules() {
        // Reglas específicas para RAG
        addRule("port", ValidationType::PORT);
        addRule("embedding_dimension", ValidationType::INTEGER, 64, 4096);
        addRule("model_name", ValidationType::STRING);
        addRule("host", ValidationType::HOST_NAME);

        // Podemos agregar más reglas específicas para RAG aquí según sea necesario
    }

} // namespace Rag