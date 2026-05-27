#pragma once
#include <string>

namespace rag {
    class QueryValidator {
    public:
        bool validate(const std::string& query);
    };
}
