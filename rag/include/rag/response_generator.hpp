#pragma once
#include <string>

namespace rag {
    class ResponseGenerator {
    public:
        std::string generateResponse(const std::string& query);
    };
}
