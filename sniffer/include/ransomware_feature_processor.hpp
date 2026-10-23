// sniffer/include/ransomware_feature_processor.hpp
#pragma once

#include "time_window_aggregator.hpp"
#include "ransomware_feature_extractor.hpp"
#include "flow_tracker.hpp"
#include "dns_analyzer.hpp"
#include "ip_whitelist.hpp"
#include "main.h"
#include "network_security.pb.h"
#include <thread>
#include <atomic>
#include <mutex>               // [PARADA-INMEDIATA-D300]
#include <condition_variable>  // [PARADA-INMEDIATA-D300]
#include <memory>

namespace sniffer {

    class RansomwareFeatureProcessor {
    public:
        explicit RansomwareFeatureProcessor();
        ~RansomwareFeatureProcessor();

        // Lifecycle
        bool initialize();
        bool start();
        void stop();

        void process_packet(const SimpleEvent& event);

        // Get extracted features (for ZMQ sender)
        bool get_features_if_ready(protobuf::RansomwareFeatures& features);

        // For testing: force immediate extraction without waiting for timer
        void force_extraction_for_testing();

        TimeWindowAggregator* get_aggregator() { return aggregator_.get(); }
        // [HEADS-SNIFFER-D305] intervalo de extraccion = fast_detector.ransomware.window_interval_seconds (JSON)
        void set_extraction_interval_seconds(uint32_t s) { extraction_interval_seconds_ = s; }

    private:
        // Components
        std::unique_ptr<FlowTracker> flow_tracker_;
        std::unique_ptr<DNSAnalyzer> dns_analyzer_;
        std::unique_ptr<IPWhitelist> ip_whitelist_;
        std::unique_ptr<RansomwareFeatureExtractor> extractor_;

        std::unique_ptr<TimeWindowAggregator> aggregator_;

        // Timer thread for periodic extraction
        std::thread extraction_thread_;
        std::atomic<bool> running_{false};
        std::mutex parada_mtx_;               // [PARADA-INMEDIATA-D300] espera interrumpible de la extraccion
        std::condition_variable parada_cv_;   // [PARADA-INMEDIATA-D300]

        // Config
        uint32_t extraction_interval_seconds_ = 30;

        // Internal state
        std::mutex features_mutex_;
        protobuf::RansomwareFeatures latest_features_;
        bool features_ready_ = false;

        // Thread function
        void extraction_loop();

        // Helpers
        void parse_and_feed_packet(const SimpleEvent& event);  // ⭐ CAMBIADO
        bool is_dns_packet(const SimpleEvent& event);          // ⭐ CAMBIADO
        void extract_and_store_features();
    };

} // namespace sniffer