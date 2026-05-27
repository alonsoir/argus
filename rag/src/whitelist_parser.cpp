#include "rag/whitelist_parser.hpp"
#include <iostream>

namespace rag {
    void WhitelistParser::loadWhitelist() {
        std::cout << "Loading whitelist..." << std::endl;
    }
    
    bool WhitelistParser::isAllowed(const std::string& command) {
        std::cout << "Checking if command is allowed: " << command << std::endl;
        return true;
    }
}
