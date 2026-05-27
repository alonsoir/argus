#pragma once

#include "network_security.pb.h"  // DEBT-COMPILER-WARNINGS-CLEANUP-001: path unificado
#include <atomic>
#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace mldefender {

class ContractValidator {
public:
    // Cuenta features dinámicamente usando protobuf reflection
    static int count_features(const protobuf::NetworkSecurityEvent& event);
    static void log_missing_features(const protobuf::NetworkSecurityEvent& event, 
                                      uint64_t event_id);
};

class ContractStats {
public:
    void record(int feature_count);
    void log_progress(uint64_t event_counter);
    void log_summary();
    
    std::atomic<uint64_t> total_events{0};
    
private:
    std::mutex distribution_mutex_;
    std::map<int, uint64_t> feature_distribution_;
};

extern ContractStats g_contract_stats;

} // namespace mldefender
