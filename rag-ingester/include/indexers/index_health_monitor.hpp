#pragma once

namespace rag_ingester {

class IndexHealthMonitor {
public:
    IndexHealthMonitor();
    
    double compute_cv(const void* index);
    
private:
    // TODO: CV calculation
};

} // namespace rag_ingester
