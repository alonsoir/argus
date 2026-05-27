#pragma once
#include "rag/base_validator.hpp"

namespace Rag {

    class RagValidator : public BaseValidator {
    public:
        RagValidator();
        void registerValidationRules() override;
    };

} // namespace Rag