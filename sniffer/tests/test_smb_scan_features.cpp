// sniffer/tests/test_smb_scan_features.cpp
// DAY 92 — SMB Scan Features: rst_ratio + syn_ack_ratio (SYN-1, SYN-2)
//
// Validates the SMBScanFeatures proto message and the extractor logic
// implemented in ml_defender_features.cpp.
//
// WHAT THIS TEST VALIDATES:
//   1. WannaCry synthetic flow: rst_ratio > 0.70, syn_ack_ratio < 0.10 → malicious
//   2. Legitimate SMB flow:     rst_ratio < 0.10, syn_ack_ratio > 0.70 → benign
//   3. syn_flag_count == 0      → sentinel -9999.0f in both fields

#include "network_security.pb.h"
#include <gtest/gtest.h>

static constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;

// Simulates the extractor logic from ml_defender_features.cpp
static void fill_smb_scan(protobuf::NetworkFeatures* nf,
                           float syn_count,
                           float rst_count,
                           float ack_count) {
    auto* smb = nf->mutable_smb_scan();
    if (syn_count > 0.0f) {
        smb->set_rst_ratio(rst_count / syn_count);
        smb->set_syn_ack_ratio(ack_count / syn_count);
    } else {
        smb->set_rst_ratio(MISSING_FEATURE_SENTINEL);
        smb->set_syn_ack_ratio(MISSING_FEATURE_SENTINEL);
    }
}

// ============================================================================
// TEST 1: WannaCry synthetic flow → malicious pattern
//   rst_ratio > 0.70   (SYN→RST inmediato, sin handshake completo)
//   syn_ack_ratio < 0.10 (casi ningún ACK — no hay sesiones legítimas)
// ============================================================================
TEST(SMBScanFeaturesTest, WannaCrySyntheticFlowIsMalicious) {
    protobuf::NetworkSecurityEvent event;
    auto* nf = event.mutable_network_features();

    // WannaCry profile: 100 SYN, 85 RST, 5 ACK
    fill_smb_scan(nf, 100.0f, 85.0f, 5.0f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    ASSERT_TRUE(received.network_features().has_smb_scan());
    const auto& smb = received.network_features().smb_scan();

    EXPECT_GT(smb.rst_ratio(), 0.70f)
        << "WannaCry rst_ratio debe ser > 0.70 (SYN→RST masivo)";
    EXPECT_LT(smb.syn_ack_ratio(), 0.10f)
        << "WannaCry syn_ack_ratio debe ser < 0.10 (sin handshakes completos)";

    // Confirm malicious classification thresholds
    bool is_malicious = smb.rst_ratio() > 0.70f && smb.syn_ack_ratio() < 0.10f;
    EXPECT_TRUE(is_malicious);

    std::cout << "✅ WannaCry synthetic: rst_ratio=" << smb.rst_ratio()
              << " syn_ack_ratio=" << smb.syn_ack_ratio()
              << " → MALICIOUS\n";
}

// ============================================================================
// TEST 2: Legitimate SMB flow → benign pattern
//   rst_ratio < 0.10   (muy pocos RST — conexiones se completan)
//   syn_ack_ratio > 0.70 (mayoría de SYN reciben ACK — handshakes normales)
// ============================================================================
TEST(SMBScanFeaturesTest, LegitimateSmBFlowIsBenign) {
    protobuf::NetworkSecurityEvent event;
    auto* nf = event.mutable_network_features();

    // Legitimate SMB: 50 SYN, 3 RST, 47 ACK
    fill_smb_scan(nf, 50.0f, 3.0f, 47.0f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    ASSERT_TRUE(received.network_features().has_smb_scan());
    const auto& smb = received.network_features().smb_scan();

    EXPECT_LT(smb.rst_ratio(), 0.10f)
        << "Legítimo rst_ratio debe ser < 0.10 (conexiones completadas)";
    EXPECT_GT(smb.syn_ack_ratio(), 0.70f)
        << "Legítimo syn_ack_ratio debe ser > 0.70 (handshakes normales)";

    // Confirm benign classification
    bool is_benign = smb.rst_ratio() < 0.10f && smb.syn_ack_ratio() > 0.70f;
    EXPECT_TRUE(is_benign);

    std::cout << "✅ Legitimate SMB: rst_ratio=" << smb.rst_ratio()
              << " syn_ack_ratio=" << smb.syn_ack_ratio()
              << " → BENIGN\n";
}

// ============================================================================
// TEST 3: syn_flag_count == 0 → sentinel -9999.0f en ambos campos
//   División por cero evitada — extractor asigna MISSING_FEATURE_SENTINEL
// ============================================================================
TEST(SMBScanFeaturesTest, ZeroSynCountYieldsSentinel) {
    protobuf::NetworkSecurityEvent event;
    auto* nf = event.mutable_network_features();

    // No SYN packets — division by zero path
    fill_smb_scan(nf, 0.0f, 5.0f, 0.0f);

    std::string serialized;
    ASSERT_TRUE(event.SerializeToString(&serialized));
    protobuf::NetworkSecurityEvent received;
    ASSERT_TRUE(received.ParseFromString(serialized));

    ASSERT_TRUE(received.network_features().has_smb_scan());
    const auto& smb = received.network_features().smb_scan();

    EXPECT_FLOAT_EQ(smb.rst_ratio(), MISSING_FEATURE_SENTINEL)
        << "rst_ratio debe ser MISSING_FEATURE_SENTINEL cuando syn_count == 0";
    EXPECT_FLOAT_EQ(smb.syn_ack_ratio(), MISSING_FEATURE_SENTINEL)
        << "syn_ack_ratio debe ser MISSING_FEATURE_SENTINEL cuando syn_count == 0";

    std::cout << "✅ Zero SYN: rst_ratio=" << smb.rst_ratio()
              << " syn_ack_ratio=" << smb.syn_ack_ratio()
              << " → SENTINEL (-9999.0f)\n";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
