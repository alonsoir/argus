#include "rag/rag_command_system.hpp"
#include <iostream>

namespace rag {
    void CommandSystem::initialize() {
        std::cout << "RAG Command System initialized" << std::endl;
    }
    
    void CommandSystem::process() {
        std::cout << "Processing RAG commands..." << std::endl;
    }
}
