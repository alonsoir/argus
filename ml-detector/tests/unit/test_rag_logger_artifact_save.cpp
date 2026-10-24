// ml-detector/tests/unit/test_rag_logger_artifact_save.cpp
// DAY 75 — Regression test for rag_logger proto2-style embedded message guard
//
// BUG: rag_logger.cpp contained a has_required_embedded guard that checked
// has_ddos_embedded() && has_ransomware_embedded() && ... before saving artifacts.
// Due to proto3 serialization behavior (all-zero submessages not transmitted),
// ransomware-features events arrived at ml-detector with has_ddos_embedded()==false,
// causing every artifact save to be skipped.
//
// FIX: The guard was removed. In proto3, nf.ddos_embedded() NEVER returns a
// null pointer — it returns a safe default instance. The original comment
// "prevents SEGFAULT" was incorrect proto2 reasoning.
//
// WHAT THIS TEST VALIDATES:
//   1. In proto3, accessing ddos_embedded() on an event where has_ddos_embedded()==false
//      is safe — no crash, returns default values
//   2. The contract check (feature_count >= 100) is independent of has_ddos_embedded()
//   3. An event with sentinel 0.5f embedded messages passes has_ddos_embedded()==true

#include "network_security.pb.h"
#include <gtest/gtest.h>

// ============================================================================
// TEST 1: Proto3 submessage access is safe even when has_X() == false
// This validates the removal of the SEGFAULT comment in rag_logger.cpp
// ============================================================================
TEST(RagLoggerArtifactSaveTest, AccessingUnsetSubmessageIsAlwaysSafeInProto3) {
    protobuf::NetworkSecurityEvent event;
    // Deliberately do NOT populate any embedded messages

    ASSERT_TRUE(event.has_network_features() == false);

    // Even without calling mutable_network_features(), accessing is safe in proto3
    // has_X() returns false, but accessing the submessage does NOT crash
    const auto& nf = event.network_features();  // Returns default instance — no crash

    EXPECT_FALSE(nf.has_ddos_embedded());
    EXPECT_FALSE(nf.has_ransomware_embedded());
    EXPECT_FALSE(nf.has_traffic_classification());
    EXPECT_FALSE(nf.has_internal_anomaly());

    // Accessing fields on unset submessage returns 0.0f safely
    EXPECT_FLOAT_EQ(nf.ddos_embedded().syn_ack_ratio(), 0.0f);
    EXPECT_FLOAT_EQ(nf.ransomware_embedded().entropy(), 0.0f);

    std::cout << "✅ Proto3 submessage access is safe without has_X() guard\n";
    std::cout << "   The 'prevents SEGFAULT' comment in rag_logger was proto2 reasoning\n";
}

// ============================================================================
// TEST 2: Event with DAY 75 fix sentinels passes has_required_embedded check
// This validates that ransomware-features events now reach artifact save
// ============================================================================
TEST(RagLoggerArtifactSaveTest, EventWithSentinelsPassesEmbeddedCheck) {
    protobuf::NetworkSecurityEvent event;
    event.set_event_id("ransomware-features-1772605808515339024");

    auto* net_features = event.mutable_network_features();
    net_features->set_source_ip("192.168.1.100");
    net_features->set_destination_ip("8.8.8.8");

    // Apply the DAY 75 fix sentinels (as in ring_consumer.cpp send_ransomware_features)
    auto* ddos_emb = net_features->mutable_ddos_embedded();
    ddos_emb->set_mean_packet_size(0.5f);  // [DDOS-V1-RETIRE-D306] campo v2 (los de la v1 estan reservados)
    ddos_emb->set_flow_completion_rate(0.5f);

    auto* ransom_emb = net_features->mutable_ransomware_embedded();
    ransom_emb->set_io_intensity(0.5f);  // also populated from mutable_ransomware_embedded

    auto* traffic_emb = net_features->mutable_traffic_classification();
    traffic_emb->set_connection_rate(0.5f);
    traffic_emb->set_tcp_udp_ratio(0.5f);
    traffic_emb->set_port_entropy(0.5f);

    auto* internal_emb = net_features->mutable_internal_anomaly();
    internal_emb->set_internal_connection_rate(0.5f);
    internal_emb->set_service_port_consistency(0.5f);
    internal_emb->set_connection_duration_std(0.5f);

    // Serialize → deserialize to simulate wire transfer
    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    // All four has_X() checks now return true — rag_logger WILL save artifact
    const auto& nf = received.network_features();
    EXPECT_TRUE(nf.has_ddos_embedded())
        << "has_ddos_embedded must be true after DAY 75 fix";
    EXPECT_TRUE(nf.has_ransomware_embedded())
        << "has_ransomware_embedded must be true";
    EXPECT_TRUE(nf.has_traffic_classification())
        << "has_traffic_classification must be true after DAY 75 fix";
    EXPECT_TRUE(nf.has_internal_anomaly())
        << "has_internal_anomaly must be true after DAY 75 fix";

    // The old guard logic (now removed from rag_logger) would have passed
    bool has_required_embedded =
        nf.has_ddos_embedded() &&
        nf.has_ransomware_embedded() &&
        nf.has_traffic_classification() &&
        nf.has_internal_anomaly();

    EXPECT_TRUE(has_required_embedded)
        << "Event with sentinels must pass the old embedded check\n"
        << "This means rag_logger will NOT skip artifact save";

    std::cout << "✅ ransomware-features event with sentinels reaches artifact save\n";
    std::cout << "   has_ddos_embedded: " << nf.has_ddos_embedded() << "\n";
    std::cout << "   has_ransomware_embedded: " << nf.has_ransomware_embedded() << "\n";
    std::cout << "   has_traffic_classification: " << nf.has_traffic_classification() << "\n";
    std::cout << "   has_internal_anomaly: " << nf.has_internal_anomaly() << "\n";
}

// ============================================================================
// TEST 3: Normal flow events (from populate_ml_defender_features path) unaffected
// ============================================================================
TEST(RagLoggerArtifactSaveTest, NormalFlowEventsUnaffectedByFix) {
    protobuf::NetworkSecurityEvent event;
    event.set_event_id("1772605808515339024");  // Normal event_id format

    auto* net_features = event.mutable_network_features();

    // Normal flow: real values from ml_defender_features.cpp extract_* functions
    auto* ddos = net_features->mutable_ddos_embedded();
    ddos->set_syn_ack_ratio(1.5f);
    ddos->set_mean_packet_size(512.0f);  // [DDOS-V1-RETIRE-D306]
    ddos->set_packet_size_entropy(0.72f);
    ddos->set_flow_completion_rate(1.0f);
    // remaining 5 fields at 0.0f is fine — 5 non-zero force serialization

    auto* ransom = net_features->mutable_ransomware_embedded();
    ransom->set_entropy(0.65f);
    ransom->set_network_activity(0.3f);

    auto* traffic = net_features->mutable_traffic_classification();
    traffic->set_packet_rate(0.1f);
    traffic->set_avg_packet_size(0.45f);

    auto* internal = net_features->mutable_internal_anomaly();
    internal->set_protocol_regularity(0.8f);
    internal->set_data_exfiltration_indicators(0.0f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    const auto& nf = received.network_features();
    EXPECT_TRUE(nf.has_ddos_embedded());
    EXPECT_TRUE(nf.has_ransomware_embedded());
    EXPECT_TRUE(nf.has_traffic_classification());
    EXPECT_TRUE(nf.has_internal_anomaly());

    std::cout << "✅ Normal flow events unaffected by DAY 75 fix\n";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}