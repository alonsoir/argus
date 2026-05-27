// test_csv_event_writer.cpp
// ML Defender — Unit tests for CsvEventWriter
// Day 64
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// Test strategy:
//   - Build synthetic NetworkSecurityEvent covering all 4 sections
//   - Verify column count, HMAC validity, filter behaviour, rotation
//   - Does NOT require a real etcd server (uses a fixed test key)

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include <openssl/hmac.h>
#include <openssl/evp.h>

#include "csv_event_writer.hpp"
#include "network_security.pb.h"

namespace fs = std::filesystem;

// ============================================================================
// Test fixture
// ============================================================================

class CsvEventWriterTest : public ::testing::Test {
protected:
    // 64-char hex key (32 zero-bytes) — deterministic for tests
    static constexpr const char* TEST_KEY_HEX =
        "0000000000000000000000000000000000000000000000000000000000000000";

    std::string tmp_dir_;
    std::unique_ptr<ml_defender::CsvEventWriter> writer_;

    void SetUp() override {
        tmp_dir_ = fs::temp_directory_path() / "csv_writer_test_XXXXXX";
        // mkdtemp needs a non-const char*
        std::string tmpl = tmp_dir_;
        char* result = mkdtemp(tmpl.data());
        ASSERT_NE(result, nullptr) << "mkdtemp failed";
        tmp_dir_ = result;

        ml_defender::CsvEventWriterConfig cfg;
        cfg.base_dir            = tmp_dir_;
        cfg.hmac_key_hex        = TEST_KEY_HEX;
        cfg.max_events_per_file = 5;    // small to test rotation
        cfg.min_score_threshold = 0.5f;

        auto logger = spdlog::default_logger();
        writer_ = std::make_unique<ml_defender::CsvEventWriter>(cfg, logger);
    }

    void TearDown() override {
        writer_.reset();
        fs::remove_all(tmp_dir_);
    }

    // -------------------------------------------------------------------------
    // Build a complete synthetic event with all sections populated
    // -------------------------------------------------------------------------
    static protobuf::NetworkSecurityEvent make_full_event(
        const std::string& id   = "evt-001",
        double score             = 0.9,
        double fast_score        = 0.7,
        double ml_score          = 0.85)
    {
        protobuf::NetworkSecurityEvent ev;
        ev.set_event_id(id);
        ev.set_overall_threat_score(score);
        ev.set_fast_detector_score(fast_score);
        ev.set_ml_detector_score(ml_score);
        ev.set_final_classification("MALICIOUS");
        ev.set_threat_category("DDOS");
        ev.set_fast_detector_triggered(true);

        // Timestamp
        ev.mutable_event_timestamp()->set_seconds(1700000000);
        ev.mutable_event_timestamp()->set_nanos(123456789);

        // DecisionMetadata / Provenance
        ev.mutable_decision_metadata()->set_score_divergence(0.15);
        ev.mutable_provenance()->set_final_decision("BLOCK");
        ev.mutable_provenance()->set_discrepancy_score(0.15f);

        // --- Section 2: NetworkFeatures (sniffer) ---
        auto* nf = ev.mutable_network_features();
        nf->set_source_ip("192.168.1.10");
        nf->set_destination_ip("8.8.8.8");
        nf->set_source_port(54321);
        nf->set_destination_port(80);
        nf->set_protocol_name("TCP");

        nf->set_total_forward_packets(100);
        nf->set_total_backward_packets(80);
        nf->set_total_forward_bytes(50000);
        nf->set_total_backward_bytes(40000);
        nf->set_forward_packet_length_max(1500);
        nf->set_forward_packet_length_min(64);
        nf->set_forward_packet_length_mean(500.0);
        nf->set_forward_packet_length_std(120.5);
        nf->set_backward_packet_length_max(1400);
        nf->set_backward_packet_length_min(60);
        nf->set_backward_packet_length_mean(480.0);
        nf->set_backward_packet_length_std(110.0);
        nf->set_flow_bytes_per_second(90000.0);
        nf->set_flow_packets_per_second(180.0);
        nf->set_forward_packets_per_second(100.0);
        nf->set_backward_packets_per_second(80.0);
        nf->set_download_upload_ratio(0.8);
        nf->set_average_packet_size(500.0);
        nf->set_average_forward_segment_size(510.0);
        nf->set_average_backward_segment_size(488.0);
        nf->set_flow_inter_arrival_time_mean(5000.0);
        nf->set_flow_inter_arrival_time_std(1000.0);
        nf->set_flow_inter_arrival_time_max(10000);
        nf->set_flow_inter_arrival_time_min(100);
        nf->set_forward_inter_arrival_time_total(500000.0);
        nf->set_forward_inter_arrival_time_mean(5000.0);
        nf->set_forward_inter_arrival_time_std(900.0);
        nf->set_forward_inter_arrival_time_max(9000);
        nf->set_forward_inter_arrival_time_min(200);
        nf->set_backward_inter_arrival_time_total(480000.0);
        nf->set_backward_inter_arrival_time_mean(6000.0);
        nf->set_backward_inter_arrival_time_std(800.0);
        nf->set_backward_inter_arrival_time_max(8000);
        nf->set_backward_inter_arrival_time_min(150);
        nf->set_fin_flag_count(2);
        nf->set_syn_flag_count(1);
        nf->set_rst_flag_count(0);
        nf->set_psh_flag_count(5);
        nf->set_ack_flag_count(180);
        nf->set_urg_flag_count(0);
        nf->set_cwe_flag_count(0);
        nf->set_ece_flag_count(0);
        nf->set_forward_psh_flags(3);
        nf->set_backward_psh_flags(2);
        nf->set_forward_urg_flags(0);
        nf->set_backward_urg_flags(0);
        nf->set_forward_header_length(20.0);
        nf->set_backward_header_length(20.0);
        nf->set_forward_average_bytes_bulk(0.0);
        nf->set_forward_average_packets_bulk(0.0);
        nf->set_forward_average_bulk_rate(0.0);
        nf->set_backward_average_bytes_bulk(0.0);
        nf->set_backward_average_packets_bulk(0.0);
        nf->set_backward_average_bulk_rate(0.0);
        nf->set_minimum_packet_length(60);
        nf->set_maximum_packet_length(1500);
        nf->set_packet_length_mean(495.0);
        nf->set_packet_length_std(115.0);
        nf->set_packet_length_variance(13225.0);
        nf->set_active_mean(5000.0);
        nf->set_idle_mean(10000.0);
        nf->set_flow_duration_microseconds(1000000);

        // --- Section 3: Embedded detector features ---
        auto* ddos = nf->mutable_ddos_embedded();
        ddos->set_syn_ack_ratio(0.1f);
        ddos->set_packet_symmetry(0.8f);
        ddos->set_source_ip_dispersion(0.9f);
        ddos->set_protocol_anomaly_score(0.2f);
        ddos->set_packet_size_entropy(0.5f);
        ddos->set_traffic_amplification_factor(1.2f);
        ddos->set_flow_completion_rate(0.95f);
        ddos->set_geographical_concentration(0.3f);
        ddos->set_traffic_escalation_rate(0.4f);
        ddos->set_resource_saturation_score(0.6f);

        auto* rsw = nf->mutable_ransomware_embedded();
        rsw->set_io_intensity(0.7f);
        rsw->set_entropy(0.85f);
        rsw->set_resource_usage(0.4f);
        rsw->set_network_activity(0.5f);
        rsw->set_file_operations(0.3f);
        rsw->set_process_anomaly(0.2f);
        rsw->set_temporal_pattern(0.6f);
        rsw->set_access_frequency(0.4f);
        rsw->set_data_volume(0.5f);
        rsw->set_behavior_consistency(0.7f);

        auto* trf = nf->mutable_traffic_classification();
        trf->set_packet_rate(0.6f);
        trf->set_connection_rate(0.5f);
        trf->set_tcp_udp_ratio(0.9f);
        trf->set_avg_packet_size(0.5f);
        trf->set_port_entropy(0.3f);
        trf->set_flow_duration_std(0.4f);
        trf->set_src_ip_entropy(0.2f);
        trf->set_dst_ip_concentration(0.8f);
        trf->set_protocol_variety(0.1f);
        trf->set_temporal_consistency(0.7f);

        auto* ia = nf->mutable_internal_anomaly();
        ia->set_internal_connection_rate(0.3f);
        ia->set_service_port_consistency(0.9f);
        ia->set_protocol_regularity(0.8f);
        ia->set_packet_size_consistency(0.7f);
        ia->set_connection_duration_std(0.2f);
        ia->set_lateral_movement_score(0.1f);
        ia->set_service_discovery_patterns(0.05f);
        ia->set_data_exfiltration_indicators(0.15f);
        ia->set_temporal_anomaly_score(0.2f);
        ia->set_access_pattern_entropy(0.3f);

        // --- Section 4: ML model decisions ---
        auto* ml = ev.mutable_ml_analysis();
        ml->set_ensemble_confidence(0.88);

        // Level 1
        auto* l1 = ml->mutable_level1_general_detection();
        l1->set_prediction_class("MALICIOUS");
        l1->set_confidence_score(0.88);

        // Level 2 — index 0 = DDoS, index 1 = Ransomware
        auto* l2d = ml->add_level2_specialized_predictions();
        l2d->set_model_name("RANDOM_FOREST_DDOS");
        l2d->set_prediction_class("DDoS");
        l2d->set_confidence_score(0.92);

        auto* l2r = ml->add_level2_specialized_predictions();
        l2r->set_model_name("RANDOM_FOREST_RANSOMWARE");
        l2r->set_prediction_class("BENIGN");
        l2r->set_confidence_score(0.10);

        // Level 3 — index 0 = Traffic, index 1 = Internal
        auto* l3t = ml->add_level3_specialized_predictions();
        l3t->set_model_name("INTERNAL_TRAFFIC_CLASSIFIER");
        l3t->set_prediction_class("EXTERNAL_WEB");
        l3t->set_confidence_score(0.75);

        auto* l3i = ml->add_level3_specialized_predictions();
        l3i->set_model_name("INTERNAL_TRAFFIC_CLASSIFIER");
        l3i->set_prediction_class("BENIGN");
        l3i->set_confidence_score(0.60);

        return ev;
    }

    // -------------------------------------------------------------------------
    // Read today's CSV file and split into rows and columns
    // -------------------------------------------------------------------------
    std::vector<std::vector<std::string>> read_csv() const {
        // Find the single .csv file in tmp_dir_
        std::vector<std::vector<std::string>> result;
        for (const auto& entry : fs::directory_iterator(tmp_dir_)) {
            if (entry.path().extension() != ".csv") continue;
            std::ifstream f(entry.path());
            std::string line;
            while (std::getline(f, line)) {
                if (line.empty()) continue;
                std::vector<std::string> cols;
                std::stringstream ss(line);
                std::string token;
                // Simple CSV split — sufficient for our unquoted numeric fields
                while (std::getline(ss, token, ',')) {
                    cols.push_back(token);
                }
                result.push_back(cols);
            }
        }
        return result;
    }

    // -------------------------------------------------------------------------
    // Recompute HMAC-SHA256 using the test key over the first 126 cols.
    // Returns empty string if cols has wrong size (caller should ASSERT first).
    // NOTE: Cannot use ASSERT_* here because this is a non-void function.
    // -------------------------------------------------------------------------
    static std::string recompute_hmac(const std::vector<std::string>& cols) {
        if (cols.size() != ml_defender::CSV_TOTAL_COLS) {
            ADD_FAILURE() << "recompute_hmac: wrong column count "
                          << cols.size() << " (expected "
                          << ml_defender::CSV_TOTAL_COLS << ")";
            return "";
        }

        // Reconstruct row_content = join(cols[0..125], ",")
        std::ostringstream ss;
        for (size_t i = 0; i < ml_defender::CSV_TOTAL_COLS - 1; ++i) {
            if (i > 0) ss << ',';
            ss << cols[i];
        }
        std::string row_content = ss.str();

        // Decode test key (32 zero-bytes)
        uint8_t key[32] = {};

        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int digest_len = 0;
        HMAC(EVP_sha256(), key, 32,
             reinterpret_cast<const unsigned char*>(row_content.data()),
             row_content.size(), digest, &digest_len);

        std::ostringstream hex;
        hex << std::hex << std::setfill('0');
        for (unsigned int i = 0; i < digest_len; ++i)
            hex << std::setw(2) << static_cast<unsigned int>(digest[i]);
        return hex.str();
    }
};

// ============================================================================
// Tests — Construction
// ============================================================================

TEST_F(CsvEventWriterTest, ConstructorCreatesOutputDirectory) {
    // The constructor should have created tmp_dir_
    EXPECT_TRUE(fs::exists(tmp_dir_));
}

TEST_F(CsvEventWriterTest, ConstructorThrowsOnEmptyKey) {
    ml_defender::CsvEventWriterConfig cfg;
    cfg.base_dir     = tmp_dir_;
    cfg.hmac_key_hex = "";   // invalid
    auto logger = spdlog::default_logger();
    EXPECT_THROW(
        ml_defender::CsvEventWriter(cfg, logger),
        std::invalid_argument);
}

TEST_F(CsvEventWriterTest, ConstructorThrowsOnShortKey) {
    ml_defender::CsvEventWriterConfig cfg;
    cfg.base_dir     = tmp_dir_;
    cfg.hmac_key_hex = "deadbeef";  // only 8 chars, need 64
    auto logger = spdlog::default_logger();
    EXPECT_THROW(
        ml_defender::CsvEventWriter(cfg, logger),
        std::invalid_argument);
}

// ============================================================================
// Tests — Schema correctness
// ============================================================================

TEST_F(CsvEventWriterTest, WrittenRowHasExactly127Columns) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    EXPECT_EQ(rows[0].size(), ml_defender::CSV_TOTAL_COLS)
        << "Expected " << ml_defender::CSV_TOTAL_COLS
        << " columns, got " << rows[0].size();
}

TEST_F(CsvEventWriterTest, Section1MetadataColumnsCorrect) {
    auto ev = make_full_event("test-id-42", 0.9, 0.7, 0.85);
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    const auto& cols = rows[0];

    // col 1: event_id
    EXPECT_EQ(cols[1], "test-id-42");
    // col 2: src_ip
    EXPECT_EQ(cols[2], "192.168.1.10");
    // col 3: dst_ip
    EXPECT_EQ(cols[3], "8.8.8.8");
    // col 4: src_port
    EXPECT_EQ(cols[4], "54321");
    // col 5: dst_port
    EXPECT_EQ(cols[5], "80");
    // col 6: protocol
    EXPECT_EQ(cols[6], "TCP");
    // col 7: final_class
    EXPECT_EQ(cols[7], "MALICIOUS");
    // col 9: threat_category
    EXPECT_EQ(cols[9], "DDOS");
    // col 13: final_decision
    EXPECT_EQ(cols[13], "BLOCK");
}

TEST_F(CsvEventWriterTest, Section2SnifferFeaturesStartAtCol14) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    const auto& cols = rows[0];

    // col 14: total_fwd_packets = 100
    EXPECT_EQ(cols[14], "100");
    // col 15: total_bwd_packets = 80
    EXPECT_EQ(cols[15], "80");
    // col 16: total_fwd_bytes = 50000
    EXPECT_EQ(cols[16], "50000");
    // col 17: total_bwd_bytes = 40000
    EXPECT_EQ(cols[17], "40000");
    // col 49: syn_flag_count = 1
    EXPECT_EQ(cols[49], "1");
    // col 75: flow_duration_us = 1000000
    EXPECT_EQ(cols[75], "1000000");
}

TEST_F(CsvEventWriterTest, Section3EmbeddedFeaturesStartAtCol76) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    const auto& cols = rows[0];

    // col 76: ddos_syn_ack_ratio = 0.1
    EXPECT_NEAR(std::stod(cols[76]), 0.1, 1e-4);
    // col 87: rsw_entropy = 0.85
    EXPECT_NEAR(std::stod(cols[87]), 0.85, 1e-4);
    // col 96: trf_packet_rate = 0.6
    EXPECT_NEAR(std::stod(cols[96]), 0.6, 1e-4);
    // col 106: int_connection_rate = 0.3
    EXPECT_NEAR(std::stod(cols[106]), 0.3, 1e-4);
    // col 115: int_access_pattern_entropy = 0.3 (last S3 col)
    EXPECT_NEAR(std::stod(cols[115]), 0.3, 1e-4);
}

TEST_F(CsvEventWriterTest, Section4MLDecisionsStartAtCol116) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    const auto& cols = rows[0];

    // col 116: level1_prediction
    EXPECT_EQ(cols[116], "MALICIOUS");
    // col 117: level1_confidence ≈ 0.88
    EXPECT_NEAR(std::stod(cols[117]), 0.88, 1e-4);
    // col 118: level2_ddos_prediction
    EXPECT_EQ(cols[118], "DDoS");
    // col 119: level2_ddos_confidence ≈ 0.92
    EXPECT_NEAR(std::stod(cols[119]), 0.92, 1e-4);
    // col 120: level2_rsw_prediction
    EXPECT_EQ(cols[120], "BENIGN");
    // col 122: level3_traffic_prediction
    EXPECT_EQ(cols[122], "EXTERNAL_WEB");
    // col 124: level3_internal_prediction
    EXPECT_EQ(cols[124], "BENIGN");
    // col 125: level3_internal_confidence ≈ 0.60 (last S4 col)
    EXPECT_NEAR(std::stod(cols[125]), 0.60, 1e-4);
}

// ============================================================================
// Tests — HMAC integrity
// ============================================================================

TEST_F(CsvEventWriterTest, HmacCol126Is64HexChars) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    const std::string& hmac = rows[0][126];

    ASSERT_EQ(hmac.size(), 64u)
        << "HMAC must be 64 hex chars (SHA256), got: " << hmac;
    EXPECT_TRUE(std::all_of(hmac.begin(), hmac.end(),
        [](char c){ return std::isxdigit(c) && !std::isupper(c); }))
        << "HMAC must be lowercase hex";
}

TEST_F(CsvEventWriterTest, HmacVerifiesCorrectly) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);

    std::string expected_hmac = recompute_hmac(rows[0]);
    EXPECT_EQ(rows[0][126], expected_hmac)
        << "HMAC verification failed — row was tampered or HMAC computation differs";
}

TEST_F(CsvEventWriterTest, HmacChangeWhenFieldChanges) {
    // Write two events with different src_ip — HMACs must differ
    auto ev1 = make_full_event("evt-a", 0.9);
    auto ev2 = make_full_event("evt-b", 0.9);
    ev2.mutable_network_features()->set_source_ip("10.0.0.99");

    ASSERT_TRUE(writer_->write_event(ev1));
    ASSERT_TRUE(writer_->write_event(ev2));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 2u);
    EXPECT_NE(rows[0][126], rows[1][126])
        << "Different events must produce different HMACs";
}

TEST_F(CsvEventWriterTest, SameEventProducesSameHmac) {
    // Deterministic: identical events → identical HMACs
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));
    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 2u);
    EXPECT_EQ(rows[0][126], rows[1][126]);
}

// ============================================================================
// Tests — Score filtering
// ============================================================================

TEST_F(CsvEventWriterTest, EventBelowThresholdIsNotWritten) {
    // threshold = 0.5, event score = 0.3 → should be skipped
    auto ev = make_full_event("low-score", 0.3);
    bool written = writer_->write_event(ev);

    EXPECT_FALSE(written);
    auto rows = read_csv();
    EXPECT_TRUE(rows.empty());
}

TEST_F(CsvEventWriterTest, EventAtThresholdIsNotWritten) {
    // strict less-than: score == threshold → filtered
    auto ev = make_full_event("at-threshold", 0.5);
    bool written = writer_->write_event(ev);
    EXPECT_FALSE(written);
}

TEST_F(CsvEventWriterTest, EventAboveThresholdIsWritten) {
    auto ev = make_full_event("above-threshold", 0.51);
    bool written = writer_->write_event(ev);
    EXPECT_TRUE(written);
    EXPECT_EQ(read_csv().size(), 1u);
}

TEST_F(CsvEventWriterTest, StatsReflectFilteredAndWrittenCounts) {
    auto ev_low  = make_full_event("low",  0.3);
    auto ev_high = make_full_event("high", 0.9);

    writer_->write_event(ev_low);
    writer_->write_event(ev_high);

    auto stats = writer_->get_stats();
    EXPECT_EQ(stats.events_written,  1u);
    EXPECT_EQ(stats.events_skipped,  1u);
    EXPECT_EQ(stats.rows_failed,     0u);
}

// ============================================================================
// Tests — File creation and rotation
// ============================================================================

TEST_F(CsvEventWriterTest, CsvFileCreatedOnFirstWrite) {
    auto ev = make_full_event();
    ASSERT_TRUE(writer_->write_event(ev));
    writer_->flush();

    bool found = false;
    for (const auto& e : fs::directory_iterator(tmp_dir_)) {
        if (e.path().extension() == ".csv") { found = true; break; }
    }
    EXPECT_TRUE(found) << "No .csv file found in " << tmp_dir_;
}

TEST_F(CsvEventWriterTest, RotationCreatesNewFileAfterMaxEvents) {
    // max_events_per_file = 5 (set in SetUp)
    auto ev = make_full_event();

    // Write 5 events → fills first file
    for (int i = 0; i < 5; ++i) {
        ev.set_event_id("evt-" + std::to_string(i));
        ASSERT_TRUE(writer_->write_event(ev));
    }

    // 6th event → should trigger rotation (new file or same file flushed)
    ev.set_event_id("evt-5");
    ASSERT_TRUE(writer_->write_event(ev));
    writer_->flush();

    // At least 6 rows total across all files
    size_t total_rows = 0;
    for (const auto& entry : fs::directory_iterator(tmp_dir_)) {
        if (entry.path().extension() != ".csv") continue;
        std::ifstream f(entry.path());
        std::string line;
        while (std::getline(f, line))
            if (!line.empty()) ++total_rows;
    }
    EXPECT_EQ(total_rows, 6u);
}

// ============================================================================
// Tests — Zero-fill for absent sub-messages
// ============================================================================

TEST_F(CsvEventWriterTest, Section2ZeroFilledWhenNetworkFeaturesAbsent) {
    protobuf::NetworkSecurityEvent ev;
    ev.set_event_id("no-nf");
    ev.set_overall_threat_score(0.9);
    // No network_features set

    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);
    ASSERT_EQ(rows[0].size(), ml_defender::CSV_TOTAL_COLS);

    // All S2 cols (14–75) must be "0"
    for (size_t c = ml_defender::CSV_S2_SNIFFER_START;
         c < ml_defender::CSV_S2_SNIFFER_START + ml_defender::CSV_S2_SNIFFER_COUNT;
         ++c) {
        EXPECT_EQ(rows[0][c], "0")
            << "col " << c << " should be 0 when network_features absent";
    }
}

TEST_F(CsvEventWriterTest, Section3ZeroFilledWhenEmbeddedSubMessagesAbsent) {
    protobuf::NetworkSecurityEvent ev;
    ev.set_event_id("no-embedded");
    ev.set_overall_threat_score(0.9);
    // network_features present but embedded sub-messages not set
    ev.mutable_network_features()->set_source_ip("1.2.3.4");

    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);

    // All S3 cols (76–115) must be "0"
    for (size_t c = ml_defender::CSV_S3_EMBEDDED_START;
         c < ml_defender::CSV_S3_EMBEDDED_START + ml_defender::CSV_S3_EMBEDDED_COUNT;
         ++c) {
        EXPECT_EQ(rows[0][c], "0")
            << "col " << c << " should be 0 when embedded sub-messages absent";
    }
}

TEST_F(CsvEventWriterTest, Section4ZeroFilledWhenMlAnalysisAbsent) {
    protobuf::NetworkSecurityEvent ev;
    ev.set_event_id("no-ml");
    ev.set_overall_threat_score(0.9);
    // No ml_analysis set

    ASSERT_TRUE(writer_->write_event(ev));

    auto rows = read_csv();
    ASSERT_EQ(rows.size(), 1u);

    // S4 prediction cols (even indices 116,118,120,122,124) must be empty
    // S4 confidence cols (odd indices 117,119,121,123,125) must be "0.000000"
    EXPECT_EQ(rows[0][116], "");
    EXPECT_EQ(rows[0][117], "0.000000");
    EXPECT_EQ(rows[0][118], "");
    EXPECT_EQ(rows[0][125], "0.000000");
}

// ============================================================================
// Tests — Thread safety (smoke test)
// ============================================================================

TEST_F(CsvEventWriterTest, ConcurrentWritesDoNotCorruptRows) {
    constexpr int NUM_THREADS = 4;
    constexpr int EVENTS_PER_THREAD = 10;

    std::vector<std::thread> threads;
    threads.reserve(NUM_THREADS);

    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([this, t]() {
            for (int i = 0; i < EVENTS_PER_THREAD; ++i) {
                auto ev = make_full_event(
                    "t" + std::to_string(t) + "-" + std::to_string(i), 0.9);
                writer_->write_event(ev);
            }
        });
    }
    for (auto& th : threads) th.join();
    writer_->flush();

    // All rows must have exactly CSV_TOTAL_COLS columns
    auto rows = read_csv();
    for (size_t r = 0; r < rows.size(); ++r) {
        EXPECT_EQ(rows[r].size(), ml_defender::CSV_TOTAL_COLS)
            << "Row " << r << " has wrong column count (concurrency corruption?)";
    }
    // Total written = NUM_THREADS * EVENTS_PER_THREAD (none filtered, all score=0.9)
    auto stats = writer_->get_stats();
    EXPECT_EQ(stats.events_written,
              static_cast<uint64_t>(NUM_THREADS * EVENTS_PER_THREAD));
}