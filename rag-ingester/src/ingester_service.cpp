#include "ingester_service.hpp"
#include <spdlog/spdlog.h>

namespace rag_ingester {

IngesterService::IngesterService(const Config& config) 
    : config_(config) {
    spdlog::info("IngesterService initialized");
}

IngesterService::~IngesterService() {
    spdlog::info("IngesterService destroyed");
}

void IngesterService::run() {
    spdlog::info("TODO: IngesterService::run()");
    running_ = true;
}

void IngesterService::shutdown() {
    spdlog::info("TODO: IngesterService::shutdown()");
    running_ = false;
}

} // namespace rag_ingester
