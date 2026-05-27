#include "contract_validator.h"
#include "logger.hpp"
#include <spdlog/spdlog.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <algorithm>

namespace mldefender {

ContractStats g_contract_stats;

int ContractValidator::count_features(const protobuf::NetworkSecurityEvent& event) {
    if (!event.has_network_features()) {
        return 0;
    }
    
    const auto& nf = event.network_features();
    const google::protobuf::Reflection* reflection = nf.GetReflection();
    
    int count = 0;
    std::vector<const google::protobuf::FieldDescriptor*> fields;
    reflection->ListFields(nf, &fields);
    
    for (const auto* field : fields) {
        if (field->is_repeated()) {
            // Contar elementos en arrays
            int size = reflection->FieldSize(nf, field);
            count += size;
        } else if (field->type() == google::protobuf::FieldDescriptor::TYPE_MESSAGE) {
            // Contar campos en sub-mensajes recursivamente
            const google::protobuf::Message& sub_msg = reflection->GetMessage(nf, field);
            const google::protobuf::Reflection* sub_reflection = sub_msg.GetReflection();
            std::vector<const google::protobuf::FieldDescriptor*> sub_fields;
            sub_reflection->ListFields(sub_msg, &sub_fields);
            count += static_cast<int>(sub_fields.size());
        } else {
            // Campo escalar simple
            count++;
        }
    }
    
    return count;
}

void ContractValidator::log_missing_features(const protobuf::NetworkSecurityEvent& event,
                                               uint64_t event_id) {
    auto logger = spdlog::get("ml-detector");
    if (!logger) return;
    
    if (!event.has_network_features()) {
        logger->warn("[CONTRACT-VIOLATION] Event {} missing entire network_features", 
                    event_id);
        return;
    }
    
    const auto& nf = event.network_features();
    
    logger->warn("[CONTRACT-VIOLATION] Event {} - Network features present but incomplete", 
                event_id);
    
    // ========================================================================
    // CRITICAL FIELDS VALIDATION
    // ========================================================================
    
    // Basic flow identification
    if (nf.source_ip().empty()) {
        logger->warn("  Missing: source_ip");
    }
    if (nf.destination_ip().empty()) {
        logger->warn("  Missing: destination_ip");
    }
    if (nf.protocol_number() == 0) {
        logger->warn("  Missing: protocol_number");
    }
    
    // ========================================================================
    // EMBEDDED MESSAGES VALIDATION (CRITICAL for ML classification)
    // ========================================================================
    
    // Level 2 DDoS Features (10 fields required)
    if (!nf.has_ddos_embedded()) {
        logger->warn("  Missing: ddos_embedded (CRITICAL - Level 2 DDoS detector requires this)");
    } else {
        const auto& ddos = nf.ddos_embedded();
        int ddos_fields = 0;
        const google::protobuf::Reflection* reflection = ddos.GetReflection();
        std::vector<const google::protobuf::FieldDescriptor*> fields;
        reflection->ListFields(ddos, &fields);
        ddos_fields = static_cast<int>(fields.size());
        
        if (ddos_fields < 10) {
            logger->warn("  ddos_embedded incomplete: {} / 10 fields", ddos_fields);
        }
    }
    
    // Level 2 Ransomware Features (10 fields required)
    if (!nf.has_ransomware_embedded()) {
        logger->warn("  Missing: ransomware_embedded (CRITICAL - Level 2 Ransomware detector requires this)");
    } else {
        const auto& ransomware = nf.ransomware_embedded();
        int ransomware_fields = 0;
        const google::protobuf::Reflection* reflection = ransomware.GetReflection();
        std::vector<const google::protobuf::FieldDescriptor*> fields;
        reflection->ListFields(ransomware, &fields);
        ransomware_fields = static_cast<int>(fields.size());
        
        if (ransomware_fields < 10) {
            logger->warn("  ransomware_embedded incomplete: {} / 10 fields", ransomware_fields);
        }
    }
    
    // Level 3 Traffic Classification Features (10 fields required)
    if (!nf.has_traffic_classification()) {
        logger->warn("  Missing: traffic_classification (CRITICAL - Level 3 Traffic detector requires this)");
    } else {
        const auto& traffic = nf.traffic_classification();
        int traffic_fields = 0;
        const google::protobuf::Reflection* reflection = traffic.GetReflection();
        std::vector<const google::protobuf::FieldDescriptor*> fields;
        reflection->ListFields(traffic, &fields);
        traffic_fields = static_cast<int>(fields.size());
        
        if (traffic_fields < 10) {
            logger->warn("  traffic_classification incomplete: {} / 10 fields", traffic_fields);
        }
    }
    
    // Level 3 Internal Anomaly Features (10 fields required)
    if (!nf.has_internal_anomaly()) {
        logger->warn("  Missing: internal_anomaly (CRITICAL - Level 3 Internal detector requires this)");
    } else {
        const auto& internal = nf.internal_anomaly();
        int internal_fields = 0;
        const google::protobuf::Reflection* reflection = internal.GetReflection();
        std::vector<const google::protobuf::FieldDescriptor*> fields;
        reflection->ListFields(internal, &fields);
        internal_fields = static_cast<int>(fields.size());
        
        if (internal_fields < 10) {
            logger->warn("  internal_anomaly incomplete: {} / 10 fields", internal_fields);
        }
    }
}

void ContractStats::record(int feature_count) {
    total_events++;
    
    std::lock_guard<std::mutex> lock(distribution_mutex_);
    feature_distribution_[feature_count]++;
}

void ContractStats::log_progress(uint64_t event_counter) {
    if (event_counter % 1000 == 0) {
        auto logger = spdlog::get("ml-detector");
        if (!logger) return;
        
        std::lock_guard<std::mutex> lock(distribution_mutex_);
        
        if (!feature_distribution_.empty()) {
            auto max_it = std::max_element(
                feature_distribution_.begin(),
                feature_distribution_.end(),
                [](const auto& a, const auto& b) { return a.second < b.second; }
            );
            
            logger->info(
                "[CONTRACT-PROGRESS] Events: {}, Most common count: {} ({} events)",
                event_counter,
                max_it->first,
                max_it->second
            );
        }
    }
}

void ContractStats::log_summary() {
    auto logger = spdlog::get("ml-detector");
    if (!logger) return;
    
    logger->info("[CONTRACT-SUMMARY] ════════════════════════════");
    logger->info("[CONTRACT-SUMMARY] Total events: {}", total_events.load());
    
    std::lock_guard<std::mutex> lock(distribution_mutex_);
    
    if (!feature_distribution_.empty()) {
        logger->info("[CONTRACT-SUMMARY] Feature count distribution:");
        
        // Sort by count
        std::vector<std::pair<int, uint64_t>> sorted(
            feature_distribution_.begin(), 
            feature_distribution_.end()
        );
        std::sort(sorted.begin(), sorted.end());
        
        for (const auto& [count, freq] : sorted) {
            double pct = 100.0 * static_cast<double>(freq) / static_cast<double>(total_events.load());
            logger->info("[CONTRACT-SUMMARY]   {:3d} features: {:6} events ({:5.2f}%)",
                        count, freq, pct);
        }
        
        // Encuentra el más común
        auto max_it = std::max_element(
            sorted.begin(), sorted.end(),
            [](const auto& a, const auto& b) { return a.second < b.second; }
        );
        
        logger->info("[CONTRACT-SUMMARY] ════════════════════════════");
        logger->info("[CONTRACT-SUMMARY] 🎯 EXPECTED FEATURE COUNT: {}", max_it->first);
        logger->info("[CONTRACT-SUMMARY] Baseline: 74 scalars + 40 embedded (4x10) = 114 minimum");
        logger->info("[CONTRACT-SUMMARY] ════════════════════════════");
    }
    
    logger->info("[CONTRACT-SUMMARY] ════════════════════════════");
}

} // namespace mldefender
