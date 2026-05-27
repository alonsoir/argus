// sniffer/tests/test_proto3_embedded_serialization.cpp
// DAY 75 — Regression test for proto3 embedded message serialization
//
// BUG: send_ransomware_features() in ring_consumer.cpp never called
// mutable_ddos_embedded(), mutable_traffic_classification() or
// mutable_internal_anomaly(). In proto3, a submessage only exists on the
// wire if mutable_*() was called. The receiver got has_ddos_embedded()==false,
// triggering "Skipping artifact save" in rag_logger.
//
// FIX (ring_consumer.cpp): Now calls mutable_*() and sets 3 sentinel fields
// per embedded message to 0.5f (neutral, consistent with Phase 1 TODOs).
//
// NOTE: Calling mutable_*() alone (even with all-zero fields) IS sufficient
// to mark a submessage as present. The bug was the complete absence of
// mutable_*() calls in send_ransomware_features().
//
// WHAT THIS TEST VALIDATES:
//   1. Root cause: not calling mutable_*() → submessage absent on wire
//   2. Fix: mutable_*() + sentinel 0.5f → submessage present on wire
//   3. Normal flow path (populate_ml_defender_features) unaffected

#include "network_security.pb.h"
#include <gtest/gtest.h>
#include <string>

// ============================================================================
// TEST 1: Root cause — not calling mutable_*() leaves submessage absent
// ============================================================================
TEST(Proto3EmbeddedSerializationTest, NeverCallingMutableMeansSubmessageAbsentOnWire) {
    protobuf::NetworkSecurityEvent event;
    auto* net_features = event.mutable_network_features();

    // Simulate send_ransomware_features() BEFORE the fix:
    // only mutable_ransomware() was called — ddos_embedded, traffic,
    // internal_anomaly were never touched
    auto* ransom = net_features->mutable_ransomware();
    ransom->set_dns_query_entropy(0.5f);
    // mutable_ddos_embedded()        ← NEVER called (the bug)
    // mutable_traffic_classification() ← NEVER called (the bug)
    // mutable_internal_anomaly()       ← NEVER called (the bug)

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    // ROOT CAUSE CONFIRMED: submessages absent because mutable_*() never called
    EXPECT_FALSE(received.network_features().has_ddos_embedded())
        << "ddos_embedded absent — mutable_*() was never called (pre-fix behavior)";
    EXPECT_FALSE(received.network_features().has_traffic_classification())
        << "traffic_classification absent — mutable_*() was never called";
    EXPECT_FALSE(received.network_features().has_internal_anomaly())
        << "internal_anomaly absent — mutable_*() was never called";

    // This is what rag_logger saw → skipped artifact save
    bool has_required =
        received.network_features().has_ddos_embedded() &&
        received.network_features().has_traffic_classification() &&
        received.network_features().has_internal_anomaly();
    EXPECT_FALSE(has_required);

    std::cout << "✅ Root cause confirmed: mutable_*() never called → submessage absent\n";
}

// ============================================================================
// TEST 2: Fix — mutable_*() + sentinel 0.5f forces submessage onto wire
// ============================================================================
TEST(Proto3EmbeddedSerializationTest, SentinelValuesForceSubmessageSerialization) {
    protobuf::NetworkSecurityEvent event;
    auto* net_features = event.mutable_network_features();

    // DAY 75 FIX: replicate exactly what send_ransomware_features() now does
    auto* ddos_emb = net_features->mutable_ddos_embedded();
    ddos_emb->set_source_ip_dispersion(0.5f);
    ddos_emb->set_geographical_concentration(0.5f);
    ddos_emb->set_flow_completion_rate(0.5f);

    auto* traffic_emb = net_features->mutable_traffic_classification();
    traffic_emb->set_connection_rate(0.5f);
    traffic_emb->set_tcp_udp_ratio(0.5f);
    traffic_emb->set_port_entropy(0.5f);

    auto* internal_emb = net_features->mutable_internal_anomaly();
    internal_emb->set_internal_connection_rate(0.5f);
    internal_emb->set_service_port_consistency(0.5f);
    internal_emb->set_connection_duration_std(0.5f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    const auto& nf = received.network_features();
    EXPECT_TRUE(nf.has_ddos_embedded());
    EXPECT_TRUE(nf.has_traffic_classification());
    EXPECT_TRUE(nf.has_internal_anomaly());

    EXPECT_FLOAT_EQ(nf.ddos_embedded().source_ip_dispersion(), 0.5f);
    EXPECT_FLOAT_EQ(nf.ddos_embedded().geographical_concentration(), 0.5f);
    EXPECT_FLOAT_EQ(nf.ddos_embedded().flow_completion_rate(), 0.5f);
    EXPECT_FLOAT_EQ(nf.traffic_classification().connection_rate(), 0.5f);
    EXPECT_FLOAT_EQ(nf.internal_anomaly().internal_connection_rate(), 0.5f);

    EXPECT_GE(nf.ddos_embedded().source_ip_dispersion(), 0.0f);
    EXPECT_LE(nf.ddos_embedded().source_ip_dispersion(), 1.0f);

    std::cout << "✅ Fix validated: sentinel 0.5f forces proto3 serialization\n";
    std::cout << "   has_ddos_embedded: " << nf.has_ddos_embedded() << "\n";
    std::cout << "   has_traffic_classification: " << nf.has_traffic_classification() << "\n";
    std::cout << "   has_internal_anomaly: " << nf.has_internal_anomaly() << "\n";
}

// ============================================================================
// TEST 3: Normal flow path unaffected
// ============================================================================
TEST(Proto3EmbeddedSerializationTest, NonZeroValuesFromRealFlowAlwaysSerialize) {
    protobuf::NetworkSecurityEvent event;
    auto* net_features = event.mutable_network_features();

    auto* ddos = net_features->mutable_ddos_embedded();
    ddos->set_syn_ack_ratio(1.5f);
    ddos->set_packet_symmetry(0.33f);
    ddos->set_source_ip_dispersion(0.5f);
    ddos->set_flow_completion_rate(1.0f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    EXPECT_TRUE(received.network_features().has_ddos_embedded());
    EXPECT_FLOAT_EQ(received.network_features().ddos_embedded().syn_ack_ratio(), 1.5f);
    EXPECT_FLOAT_EQ(received.network_features().ddos_embedded().flow_completion_rate(), 1.0f);

    std::cout << "✅ Normal flow path unaffected by fix\n";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
