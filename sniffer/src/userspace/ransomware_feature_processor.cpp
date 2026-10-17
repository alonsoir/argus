// sniffer/src/userspace/ransomware_feature_processor.cpp
#include "ransomware_feature_processor.hpp"
#include "protocol_numbers.hpp"
#include <iostream>
#include <chrono>
#include <arpa/inet.h>

namespace sniffer {

RansomwareFeatureProcessor::RansomwareFeatureProcessor() {
}

RansomwareFeatureProcessor::~RansomwareFeatureProcessor() {
    stop();
}

bool RansomwareFeatureProcessor::initialize() {
    std::cout << "[Ransomware] Initializing RansomwareFeatureProcessor..." << std::endl;

    // Create components
    flow_tracker_ = std::make_unique<FlowTracker>(100000, 300);
    dns_analyzer_ = std::make_unique<DNSAnalyzer>(1000);
    ip_whitelist_ = std::make_unique<IPWhitelist>(10000, 24 * 3600);

    // DAY 78: TimeWindowAggregator para features multi-flow
    aggregator_ = std::make_unique<TimeWindowAggregator>(
    *flow_tracker_,
    *ip_whitelist_,
    *dns_analyzer_,
    10000  // max_events — mismo valor que extractor_
    );

    extractor_ = std::make_unique<RansomwareFeatureExtractor>(
        *flow_tracker_,
        *dns_analyzer_,
        *ip_whitelist_,
        10000
    );

    std::cout << "✅ RansomwareFeatureProcessor initialized" << std::endl;
    return true;
}

bool RansomwareFeatureProcessor::start() {
    if (running_) {
        std::cerr << "⚠️  RansomwareFeatureProcessor already running" << std::endl;
        return false;
    }

    running_ = true;
    extraction_thread_ = std::thread(&RansomwareFeatureProcessor::extraction_loop, this);

    std::cout << "✅ RansomwareFeatureProcessor started (extraction every "
              << extraction_interval_seconds_ << "s)" << std::endl;

    return true;
}

void RansomwareFeatureProcessor::stop() {
    if (!running_) return;

    std::cout << "[Ransomware] Stopping..." << std::endl;
    running_ = false;
    { std::lock_guard<std::mutex> lk(parada_mtx_); }  // [PARADA-INMEDIATA-D300] sin despertar perdido
    parada_cv_.notify_all();

    if (extraction_thread_.joinable()) {
        extraction_thread_.join();
    }

    std::cout << "✅ RansomwareFeatureProcessor stopped" << std::endl;
}

void RansomwareFeatureProcessor::process_packet(const SimpleEvent& event) {
    if (!running_) return;
    parse_and_feed_packet(event);
}

void RansomwareFeatureProcessor::parse_and_feed_packet(const SimpleEvent& event) {
    uint64_t timestamp_ns = event.timestamp;

    // === 1. Feed FlowTracker ===
    PacketInfo packet_info;
    packet_info.src_ip = event.src_ip;
    packet_info.dst_ip = event.dst_ip;
    packet_info.src_port = event.src_port;
    packet_info.dst_port = event.dst_port;
    packet_info.protocol = event.protocol;
    packet_info.length = event.packet_len;
    packet_info.timestamp_ns = timestamp_ns;
    packet_info.tcp_flags = event.tcp_flags;
    packet_info.is_forward = true;  // TODO: Determinar dirección del flow

    flow_tracker_->update_flow(packet_info);

    // === 2. Feed IPWhitelist (solo IPs externas) ===
    if (TimeWindowAggregator::is_external_ip(event.dst_ip)) {
        ip_whitelist_->add_ip(event.dst_ip, timestamp_ns);
    }

    // === 3. Feed DNSAnalyzer (si es DNS) ===
    if (is_dns_packet(event)) {
        // todo
        // ⚠️ LIMITACIÓN: SimpleEvent NO tiene payload
        // Por ahora, agregamos entradas "sintéticas" basadas en la IP destino
        // En producción, necesitaríamos:
        // - Modificar eBPF para extraer DNS query name
        // - O añadir campo payload a SimpleEvent

        // Solución temporal: usar IP destino como "pseudo-domain"
        char domain_buf[32];
        uint32_t ip = event.dst_ip;
        snprintf(domain_buf, sizeof(domain_buf), "%u.%u.%u.%u",
                 (ip >> 24) & 0xFF,
                 (ip >> 16) & 0xFF,
                 (ip >> 8) & 0xFF,
                 ip & 0xFF);

        // TODO: En producción, parsear DNS query name del payload
        dns_analyzer_->add_query(domain_buf, timestamp_ns, true, event.src_ip);
    }

    // === 4. Feed TimeWindowAggregator y RansomwareFeatureExtractor ===
    TimeWindowEvent tw_event(
        timestamp_ns,
        event.src_ip, event.dst_ip,
        event.src_port, event.dst_port,
        event.protocol,
        event.packet_len
    );

    extractor_->add_event(tw_event);

    // DAY 78: mismo evento al TimeWindowAggregator para features multi-flow
    if (aggregator_) {
        aggregator_->add_event(tw_event);  // reutilizar tw_event ya construido
    }
}

bool RansomwareFeatureProcessor::is_dns_packet(const SimpleEvent& event) {
    // DNS: UDP port 53
    return (event.protocol == static_cast<uint8_t>(IPProtocol::UDP) && (event.src_port == 53 || event.dst_port == 53));
}

void RansomwareFeatureProcessor::extraction_loop() {
    std::cout << "[Ransomware] Extraction thread started" << std::endl;

    while (running_) {
        {   // [PARADA-INMEDIATA-D300] espera interrumpible: stop() no espera al intervalo
            std::unique_lock<std::mutex> lk(parada_mtx_);
            if (parada_cv_.wait_for(lk, std::chrono::seconds(extraction_interval_seconds_),
                                    [this] { return !running_.load(); })) break;
        }

        if (!running_) break;

        extract_and_store_features();
    }

    std::cout << "[Ransomware] Extraction thread stopped" << std::endl;
}

void RansomwareFeatureProcessor::extract_and_store_features() {
    // Extract Phase 1A features
    auto features = extractor_->extract_features_phase1a();

    std::cout << "\n[Ransomware] Features extracted:" << std::endl;
    std::cout << "  DNS Entropy: " << features.dns_query_entropy << std::endl;
    std::cout << "  New External IPs (30s): " << features.new_external_ips_30s << std::endl;
    std::cout << "  SMB Diversity: " << features.smb_connection_diversity << std::endl;

    // Store in protobuf format
    {
        std::lock_guard<std::mutex> lock(features_mutex_);

        latest_features_.set_dns_query_entropy(features.dns_query_entropy);
        latest_features_.set_new_external_ips_30s(features.new_external_ips_30s);
        latest_features_.set_smb_connection_diversity(features.smb_connection_diversity);

        features_ready_ = true;
    }

    // Cleanup old events
    extractor_->cleanup_old_events(600'000'000'000ULL);
}

bool RansomwareFeatureProcessor::get_features_if_ready(protobuf::RansomwareFeatures& features) {
    std::lock_guard<std::mutex> lock(features_mutex_);

    if (!features_ready_) {
        return false;
    }

    features = latest_features_;
    features_ready_ = false;

    return true;
}


void RansomwareFeatureProcessor::force_extraction_for_testing() {
    extract_and_store_features();
}
} // namespace sniffer
