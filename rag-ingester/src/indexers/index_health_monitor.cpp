#include "indexers/index_health_monitor.hpp"
#include <spdlog/spdlog.h>

namespace rag_ingester {

IndexHealthMonitor::IndexHealthMonitor() {
    spdlog::info("IndexHealthMonitor initialized");
}

double IndexHealthMonitor::compute_cv(const void* /*index*/) {
    spdlog::debug("TODO: compute_cv()");
    return 0.35;  // Stub value
}

} // namespace rag_ingester
