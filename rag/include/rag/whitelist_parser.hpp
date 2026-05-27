// include/rag/whitelist_parser.hpp
#pragma once
#include <string>
#include <iostream>

namespace rag {
    class WhitelistParser {
    public:
        void loadWhitelist();  // Solo declaración
        bool isAllowed(const std::string& command);  // Solo declaración
    };
}