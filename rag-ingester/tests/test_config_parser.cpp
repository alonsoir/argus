#include "common/config_parser.hpp"
#include <spdlog/spdlog.h>
#include <cassert>

int main() {
    spdlog::set_level(spdlog::level::info);
    
    spdlog::info("=== Test: ConfigParser ===");
    
    try {
        // Load config
        auto config = rag_ingester::ConfigParser::load(
            "/etc/ml-defender/rag-ingester/rag-ingester.json"
        );
        
        // Validate values
        assert(config.service.id == "rag-ingester-default");
        assert(config.service.location == "default");
        assert(config.service.version == "0.1.0");
        
        assert(config.service.etcd.endpoints[0] == "127.0.0.1:2379");
        assert(config.service.etcd.heartbeat_interval_sec == 10);
        assert(config.service.etcd.partner_detector == "ml-detector-default");
        
        assert(config.ingester.threading.mode == "single");
        assert(config.ingester.threading.embedding_workers == 1);
        assert(config.ingester.threading.indexing_workers == 1);
        
        assert(config.ingester.embedders.chronos.enabled == true);
        assert(config.ingester.embedders.chronos.input_dim == 83);
        assert(config.ingester.embedders.chronos.output_dim == 512);
        
        assert(config.ingester.health.cv_warning_threshold == 0.20f);
        assert(config.ingester.health.cv_critical_threshold == 0.15f);
        
        spdlog::info("✅ All assertions passed");
        
        return 0;
        
    } catch (const std::exception& e) {
        spdlog::error("❌ Test failed: {}", e.what());
        return 1;
    }
}
