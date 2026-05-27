#pragma once

#include "common/config_parser.hpp"

namespace rag_ingester {

class IngesterService {
public:
    explicit IngesterService(const Config& config);
    ~IngesterService();
    
    void run();
    void shutdown();
    
private:
    Config config_;
    bool running_{false};
};

} // namespace rag_ingester
