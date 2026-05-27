#include "rag/query_validator.hpp"
#include <iostream>

namespace rag {
    bool QueryValidator::validate(const std::string& query) {
        std::cout << "Validating query: " << query << std::endl;
        return !query.empty();
    }
}
