#include "rag/response_generator.hpp"
#include <iostream>

namespace rag {
    std::string ResponseGenerator::generateResponse(const std::string& query) {
        std::cout << "Generating response for: " << query << std::endl;
        return "Response to: " + query;
    }
}
