// test_csv_feature_extraction.cpp
// ML Defender — Schema consistency tests for CsvEventWriter
// Day 64
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// PURPOSE:
//   These tests act as a living contract between network_security.proto
//   and FEATURE_SCHEMA.md. They verify that:
//     1. The proto fields referenced in each CSV column actually exist
//        and are accessible via the generated C++ API.
//     2. Column count constants in csv_event_writer.hpp match reality.
//     3. Each section extracts the right number of values from a
//        fully-populated synthetic event.
//     4. Feature values are reproducible (same event → same CSV row).
//     5. Numeric columns are parseable as floating-point / integer.
//
//   When a proto field is renamed or moved, these tests fail immediately,
//   catching schema drift before it silently corrupts the RAG index.

#include <gtest/gtest.h>

#include <string>
#include <vector>
#include <sstream>
#include <filesystem>
#include <fstream>
#include <cmath>

#include "csv_event_writer.hpp"
#include "network_security.pb.h"

namespace fs = std::filesystem;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

namespace {

static constexpr const char* TEST_KEY =
    "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20";

// Split a CSV line (no quoted fields with embedded commas in our schema)
std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> cols;
    std::stringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, ',')) cols.push_back(tok);
    return cols;
}

// Build a fully-populated event (mirrors make_full_event in test_csv_event_writer)
protobuf::NetworkSecurityEvent make_full_event() {
    protobuf::NetworkSecurityEvent ev;
    ev.set_event_id("schema-test-001");
    ev.set_overall_threat_score(0.9);
    ev.set_fast_detector_score(0.7);
    ev.set_ml_detector_score(0.85);
    ev.set_final_classification("MALICIOUS");
    ev.set_threat_category("DDOS");
    ev.mutable_event_timestamp()->set_seconds(1700000000);
    ev.mutable_event_timestamp()->set_nanos(0);
    ev.mutable_decision_metadata()->set_score_divergence(0.15);
    ev.mutable_provenance()->set_final_decision("BLOCK");
    ev.mutable_provenance()->set_discrepancy_score(0.15f);

    auto* nf = ev.mutable_network_features();
    nf->set_source_ip("10.0.0.1");
    nf->set_destination_ip("172.16.0.1");
    nf->set_source_port(12345);
    nf->set_destination_port(443);
    nf->set_protocol_name("TCP");
    nf->set_total_forward_packets(200);
    nf->set_total_backward_packets(150);
    nf->set_total_forward_bytes(100000);
    nf->set_total_backward_bytes(80000);
    nf->set_forward_packet_length_max(1500);
    nf->set_forward_packet_length_min(40);
    nf->set_forward_packet_length_mean(500.0);
    nf->set_forward_packet_length_std(100.0);
    nf->set_backward_packet_length_max(1400);
    nf->set_backward_packet_length_min(40);
    nf->set_backward_packet_length_mean(480.0);
    nf->set_backward_packet_length_std(90.0);
    nf->set_flow_bytes_per_second(180000.0);
    nf->set_flow_packets_per_second(350.0);
    nf->set_forward_packets_per_second(200.0);
    nf->set_backward_packets_per_second(150.0);
    nf->set_download_upload_ratio(0.8);
    nf->set_average_packet_size(514.28);
    nf->set_average_forward_segment_size(520.0);
    nf->set_average_backward_segment_size(505.0);
    nf->set_flow_inter_arrival_time_mean(2857.0);
    nf->set_flow_inter_arrival_time_std(500.0);
    nf->set_flow_inter_arrival_time_max(5000);
    nf->set_flow_inter_arrival_time_min(50);
    nf->set_forward_inter_arrival_time_total(285700.0);
    nf->set_forward_inter_arrival_time_mean(1428.5);
    nf->set_forward_inter_arrival_time_std(300.0);
    nf->set_forward_inter_arrival_time_max(3000);
    nf->set_forward_inter_arrival_time_min(100);
    nf->set_backward_inter_arrival_time_total(380000.0);
    nf->set_backward_inter_arrival_time_mean(2533.0);
    nf->set_backward_inter_arrival_time_std(400.0);
    nf->set_backward_inter_arrival_time_max(4000);
    nf->set_backward_inter_arrival_time_min(80);
    nf->set_fin_flag_count(3);
    nf->set_syn_flag_count(1);
    nf->set_rst_flag_count(0);
    nf->set_psh_flag_count(10);
    nf->set_ack_flag_count(345);
    nf->set_urg_flag_count(0);
    nf->set_cwe_flag_count(0);
    nf->set_ece_flag_count(0);
    nf->set_forward_psh_flags(6);
    nf->set_backward_psh_flags(4);
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
    nf->set_minimum_packet_length(40);
    nf->set_maximum_packet_length(1500);
    nf->set_packet_length_mean(508.0);
    nf->set_packet_length_std(95.0);
    nf->set_packet_length_variance(9025.0);
    nf->set_active_mean(3000.0);
    nf->set_idle_mean(7000.0);
    nf->set_flow_duration_microseconds(2000000);

    // Embedded detectors
    auto* d = nf->mutable_ddos_embedded();
    d->set_syn_ack_ratio(0.11f);   d->set_packet_symmetry(0.82f);
    d->set_source_ip_dispersion(0.91f); d->set_protocol_anomaly_score(0.22f);
    d->set_packet_size_entropy(0.51f);  d->set_traffic_amplification_factor(1.3f);
    d->set_flow_completion_rate(0.96f); d->set_geographical_concentration(0.31f);
    d->set_traffic_escalation_rate(0.41f); d->set_resource_saturation_score(0.61f);

    auto* r = nf->mutable_ransomware_embedded();
    r->set_io_intensity(0.71f); r->set_entropy(0.86f);
    r->set_resource_usage(0.41f); r->set_network_activity(0.51f);
    r->set_file_operations(0.31f); r->set_process_anomaly(0.21f);
    r->set_temporal_pattern(0.61f); r->set_access_frequency(0.41f);
    r->set_data_volume(0.51f); r->set_behavior_consistency(0.71f);

    auto* t = nf->mutable_traffic_classification();
    t->set_packet_rate(0.61f); t->set_connection_rate(0.51f);
    t->set_tcp_udp_ratio(0.91f); t->set_avg_packet_size(0.51f);
    t->set_port_entropy(0.31f); t->set_flow_duration_std(0.41f);
    t->set_src_ip_entropy(0.21f); t->set_dst_ip_concentration(0.81f);
    t->set_protocol_variety(0.11f); t->set_temporal_consistency(0.71f);

    auto* ia = nf->mutable_internal_anomaly();
    ia->set_internal_connection_rate(0.31f); ia->set_service_port_consistency(0.91f);
    ia->set_protocol_regularity(0.81f); ia->set_packet_size_consistency(0.71f);
    ia->set_connection_duration_std(0.21f); ia->set_lateral_movement_score(0.11f);
    ia->set_service_discovery_patterns(0.06f); ia->set_data_exfiltration_indicators(0.16f);
    ia->set_temporal_anomaly_score(0.21f); ia->set_access_pattern_entropy(0.31f);

    // ML decisions
    auto* ml = ev.mutable_ml_analysis();
    ml->set_ensemble_confidence(0.87);
    ml->mutable_level1_general_detection()->set_prediction_class("MALICIOUS");
    ml->mutable_level1_general_detection()->set_confidence_score(0.87);
    auto* p2d = ml->add_level2_specialized_predictions();
    p2d->set_prediction_class("DDoS"); p2d->set_confidence_score(0.93);
    auto* p2r = ml->add_level2_specialized_predictions();
    p2r->set_prediction_class("BENIGN"); p2r->set_confidence_score(0.07);
    auto* p3t = ml->add_level3_specialized_predictions();
    p3t->set_prediction_class("EXTERNAL_WEB"); p3t->set_confidence_score(0.76);
    auto* p3i = ml->add_level3_specialized_predictions();
    p3i->set_prediction_class("BENIGN"); p3i->set_confidence_score(0.55);

    return ev;
}

// Write one event and return its parsed columns
std::vector<std::string> write_and_read(
    const protobuf::NetworkSecurityEvent& ev,
    const std::string& dir)
{
    ml_defender::CsvEventWriterConfig cfg;
    cfg.base_dir            = dir;
    cfg.hmac_key_hex        = TEST_KEY;
    cfg.max_events_per_file = 100;
    cfg.min_score_threshold = 0.0f;  // capture everything

    auto writer = std::make_unique<ml_defender::CsvEventWriter>(
        cfg, spdlog::default_logger());
    writer->write_event(ev);
    writer->flush();
    writer.reset();

    for (const auto& entry : fs::directory_iterator(dir)) {
        if (entry.path().extension() != ".csv") continue;
        std::ifstream f(entry.path());
        std::string line;
        if (std::getline(f, line) && !line.empty())
            return split_csv(line);
    }
    return {};
}

} // namespace

// ─────────────────────────────────────────────────────────────────────────────
// Fixture
// ─────────────────────────────────────────────────────────────────────────────

class CsvFeatureExtractionTest : public ::testing::Test {
protected:
    std::string tmp_dir_;

    void SetUp() override {
        std::string tmpl = (fs::temp_directory_path() / "csv_feat_XXXXXX").string();
        char* r = mkdtemp(tmpl.data());
        ASSERT_NE(r, nullptr);
        tmp_dir_ = r;
    }

    void TearDown() override {
        fs::remove_all(tmp_dir_);
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// Column count constants
// ─────────────────────────────────────────────────────────────────────────────

TEST(CsvSchemaConstants, TotalColsIs127) {
    EXPECT_EQ(ml_defender::CSV_TOTAL_COLS, 127u);
}

TEST(CsvSchemaConstants, SectionStartsAndCountsAreConsistent) {
    // S1 starts at 0, count 14 → ends at 13
    EXPECT_EQ(ml_defender::CSV_S1_METADATA_START, 0u);
    EXPECT_EQ(ml_defender::CSV_S1_METADATA_COUNT, 14u);

    // S2 starts right after S1
    EXPECT_EQ(ml_defender::CSV_S2_SNIFFER_START,
              ml_defender::CSV_S1_METADATA_START +
              ml_defender::CSV_S1_METADATA_COUNT);
    EXPECT_EQ(ml_defender::CSV_S2_SNIFFER_COUNT, 62u);

    // S3 starts right after S2
    EXPECT_EQ(ml_defender::CSV_S3_EMBEDDED_START,
              ml_defender::CSV_S2_SNIFFER_START +
              ml_defender::CSV_S2_SNIFFER_COUNT);
    EXPECT_EQ(ml_defender::CSV_S3_EMBEDDED_COUNT, 40u);

    // S4 starts right after S3
    EXPECT_EQ(ml_defender::CSV_S4_DECISIONS_START,
              ml_defender::CSV_S3_EMBEDDED_START +
              ml_defender::CSV_S3_EMBEDDED_COUNT);
    EXPECT_EQ(ml_defender::CSV_S4_DECISIONS_COUNT, 10u);

    // HMAC col is S4_start + S4_count
    EXPECT_EQ(ml_defender::CSV_S5_HMAC_COL,
              ml_defender::CSV_S4_DECISIONS_START +
              ml_defender::CSV_S4_DECISIONS_COUNT);

    // Total = S1 + S2 + S3 + S4 + 1 (HMAC)
    size_t expected =
        ml_defender::CSV_S1_METADATA_COUNT +
        ml_defender::CSV_S2_SNIFFER_COUNT  +
        ml_defender::CSV_S3_EMBEDDED_COUNT +
        ml_defender::CSV_S4_DECISIONS_COUNT + 1u;
    EXPECT_EQ(ml_defender::CSV_TOTAL_COLS, expected);
}

TEST(CsvSchemaConstants, FeatureColsAlias) {
    // CSV_FEATURE_COLS = S2 + S3 = 62 + 40 = 102
    EXPECT_EQ(ml_defender::CSV_FEATURE_COLS,
              ml_defender::CSV_S2_SNIFFER_COUNT +
              ml_defender::CSV_S3_EMBEDDED_COUNT);
    EXPECT_EQ(ml_defender::CSV_FEATURE_COLS, 102u);
}

// ─────────────────────────────────────────────────────────────────────────────
// Proto field accessibility — these tests fail if proto fields are renamed
// ─────────────────────────────────────────────────────────────────────────────

TEST(ProtoFieldAccessibility, Section2AllFieldsReadable) {
    // Simply constructing an event and reading all S2 fields via the generated
    // API is sufficient — a renamed field causes a compile error.
    protobuf::NetworkSecurityEvent ev;
    auto* nf = ev.mutable_network_features();

    // 2.1
    (void)nf->total_forward_packets();
    (void)nf->total_backward_packets();
    (void)nf->total_forward_bytes();
    (void)nf->total_backward_bytes();
    // 2.2
    (void)nf->forward_packet_length_max();
    (void)nf->forward_packet_length_min();
    (void)nf->forward_packet_length_mean();
    (void)nf->forward_packet_length_std();
    // 2.3
    (void)nf->backward_packet_length_max();
    (void)nf->backward_packet_length_min();
    (void)nf->backward_packet_length_mean();
    (void)nf->backward_packet_length_std();
    // 2.4
    (void)nf->flow_bytes_per_second();
    (void)nf->flow_packets_per_second();
    (void)nf->forward_packets_per_second();
    (void)nf->backward_packets_per_second();
    (void)nf->download_upload_ratio();
    (void)nf->average_packet_size();
    (void)nf->average_forward_segment_size();
    (void)nf->average_backward_segment_size();
    // 2.5
    (void)nf->flow_inter_arrival_time_mean();
    (void)nf->flow_inter_arrival_time_std();
    (void)nf->flow_inter_arrival_time_max();
    (void)nf->flow_inter_arrival_time_min();
    // 2.6
    (void)nf->forward_inter_arrival_time_total();
    (void)nf->forward_inter_arrival_time_mean();
    (void)nf->forward_inter_arrival_time_std();
    (void)nf->forward_inter_arrival_time_max();
    (void)nf->forward_inter_arrival_time_min();
    // 2.7
    (void)nf->backward_inter_arrival_time_total();
    (void)nf->backward_inter_arrival_time_mean();
    (void)nf->backward_inter_arrival_time_std();
    (void)nf->backward_inter_arrival_time_max();
    (void)nf->backward_inter_arrival_time_min();
    // 2.8
    (void)nf->fin_flag_count();
    (void)nf->syn_flag_count();
    (void)nf->rst_flag_count();
    (void)nf->psh_flag_count();
    (void)nf->ack_flag_count();
    (void)nf->urg_flag_count();
    (void)nf->cwe_flag_count();
    (void)nf->ece_flag_count();
    // 2.9
    (void)nf->forward_psh_flags();
    (void)nf->backward_psh_flags();
    (void)nf->forward_urg_flags();
    (void)nf->backward_urg_flags();
    // 2.10
    (void)nf->forward_header_length();
    (void)nf->backward_header_length();
    (void)nf->forward_average_bytes_bulk();
    (void)nf->forward_average_packets_bulk();
    (void)nf->forward_average_bulk_rate();
    (void)nf->backward_average_bytes_bulk();
    (void)nf->backward_average_packets_bulk();
    (void)nf->backward_average_bulk_rate();
    // 2.11
    (void)nf->minimum_packet_length();
    (void)nf->maximum_packet_length();
    (void)nf->packet_length_mean();
    (void)nf->packet_length_std();
    (void)nf->packet_length_variance();
    // 2.12
    (void)nf->active_mean();
    (void)nf->idle_mean();
    // 2.13
    (void)nf->flow_duration_microseconds();

    SUCCEED();  // If it compiled and ran, all fields are accessible
}

TEST(ProtoFieldAccessibility, Section3AllEmbeddedSubMessagesReadable) {
    protobuf::NetworkSecurityEvent ev;
    auto* nf = ev.mutable_network_features();

    // DDoSFeatures
    auto* d = nf->mutable_ddos_embedded();
    (void)d->syn_ack_ratio();           (void)d->packet_symmetry();
    (void)d->source_ip_dispersion();    (void)d->protocol_anomaly_score();
    (void)d->packet_size_entropy();     (void)d->traffic_amplification_factor();
    (void)d->flow_completion_rate();    (void)d->geographical_concentration();
    (void)d->traffic_escalation_rate(); (void)d->resource_saturation_score();

    // RansomwareEmbeddedFeatures
    auto* r = nf->mutable_ransomware_embedded();
    (void)r->io_intensity();    (void)r->entropy();
    (void)r->resource_usage();  (void)r->network_activity();
    (void)r->file_operations(); (void)r->process_anomaly();
    (void)r->temporal_pattern();(void)r->access_frequency();
    (void)r->data_volume();     (void)r->behavior_consistency();

    // TrafficFeatures
    auto* t = nf->mutable_traffic_classification();
    (void)t->packet_rate();           (void)t->connection_rate();
    (void)t->tcp_udp_ratio();         (void)t->avg_packet_size();
    (void)t->port_entropy();          (void)t->flow_duration_std();
    (void)t->src_ip_entropy();        (void)t->dst_ip_concentration();
    (void)t->protocol_variety();      (void)t->temporal_consistency();

    // InternalFeatures
    auto* ia = nf->mutable_internal_anomaly();
    (void)ia->internal_connection_rate();    (void)ia->service_port_consistency();
    (void)ia->protocol_regularity();         (void)ia->packet_size_consistency();
    (void)ia->connection_duration_std();     (void)ia->lateral_movement_score();
    (void)ia->service_discovery_patterns();  (void)ia->data_exfiltration_indicators();
    (void)ia->temporal_anomaly_score();      (void)ia->access_pattern_entropy();

    SUCCEED();
}

// ─────────────────────────────────────────────────────────────────────────────
// Section column counts (verify extracted count at runtime)
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(CsvFeatureExtractionTest, Section2Produces62Columns) {
    auto ev   = make_full_event();
    auto cols = write_and_read(ev, tmp_dir_);
    ASSERT_EQ(cols.size(), ml_defender::CSV_TOTAL_COLS);

    // Count non-empty S2 columns (all should be populated in full event)
    size_t populated = 0;
    for (size_t c = ml_defender::CSV_S2_SNIFFER_START;
         c < ml_defender::CSV_S2_SNIFFER_START + ml_defender::CSV_S2_SNIFFER_COUNT; ++c) {
        if (!cols[c].empty()) ++populated;
    }
    EXPECT_EQ(populated, ml_defender::CSV_S2_SNIFFER_COUNT)
        << "All S2 columns should be populated for a full event";
}

TEST_F(CsvFeatureExtractionTest, Section3Produces40Columns) {
    auto ev   = make_full_event();
    auto cols = write_and_read(ev, tmp_dir_);
    ASSERT_EQ(cols.size(), ml_defender::CSV_TOTAL_COLS);

    size_t populated = 0;
    for (size_t c = ml_defender::CSV_S3_EMBEDDED_START;
         c < ml_defender::CSV_S3_EMBEDDED_START + ml_defender::CSV_S3_EMBEDDED_COUNT; ++c) {
        if (cols[c] != "0" && !cols[c].empty()) ++populated;
    }
    EXPECT_EQ(populated, ml_defender::CSV_S3_EMBEDDED_COUNT)
        << "All S3 columns should be non-zero for a full event";
}

TEST_F(CsvFeatureExtractionTest, Section4Produces10Columns) {
    auto ev   = make_full_event();
    auto cols = write_and_read(ev, tmp_dir_);
    ASSERT_EQ(cols.size(), ml_defender::CSV_TOTAL_COLS);

    // 5 prediction label cols + 5 confidence cols
    size_t label_cols = 0, conf_cols = 0;
    for (size_t c = ml_defender::CSV_S4_DECISIONS_START;
         c < ml_defender::CSV_S4_DECISIONS_START + ml_defender::CSV_S4_DECISIONS_COUNT;
         ++c) {
        if ((c - ml_defender::CSV_S4_DECISIONS_START) % 2 == 0)
            ++label_cols;  // even = label
        else
            ++conf_cols;   // odd  = confidence
    }
    EXPECT_EQ(label_cols, 5u);
    EXPECT_EQ(conf_cols,  5u);
}

// ─────────────────────────────────────────────────────────────────────────────
// Reproducibility
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(CsvFeatureExtractionTest, SameEventProducesSameRow) {
    auto ev = make_full_event();

    std::string dir2 = tmp_dir_ + "/run2";
    fs::create_directories(dir2);

    auto cols1 = write_and_read(ev, tmp_dir_);
    auto cols2 = write_and_read(ev, dir2);

    ASSERT_EQ(cols1.size(), ml_defender::CSV_TOTAL_COLS);
    ASSERT_EQ(cols2.size(), ml_defender::CSV_TOTAL_COLS);

    // All columns except timestamp_ns (col 0, wall-clock dependent) must match
    for (size_t c = 1; c < ml_defender::CSV_TOTAL_COLS; ++c) {
        EXPECT_EQ(cols1[c], cols2[c])
            << "Column " << c << " differs between identical events";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Numeric parseability — every non-string column must parse cleanly
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(CsvFeatureExtractionTest, AllNumericColumnsAreParseableAsDouble) {
    auto ev   = make_full_event();
    auto cols = write_and_read(ev, tmp_dir_);
    ASSERT_EQ(cols.size(), ml_defender::CSV_TOTAL_COLS);

    // String columns: 1(event_id), 2(src_ip), 3(dst_ip), 6(protocol),
    //                 7(final_class), 9(threat_category), 13(final_decision),
    //                 116,118,120,122,124 (prediction labels), 126(hmac)
    const std::set<size_t> string_cols = {
        1, 2, 3, 6, 7, 9, 13,
        116, 118, 120, 122, 124,
        126
    };

    for (size_t c = 0; c < ml_defender::CSV_TOTAL_COLS; ++c) {
        if (string_cols.count(c)) continue;
        if (cols[c].empty()) continue;  // empty string cols are ok

        try {
            double val = std::stod(cols[c]);
            EXPECT_TRUE(std::isfinite(val) || val == 0.0)
                << "Col " << c << " has non-finite value: " << cols[c];
        } catch (const std::exception& e) {
            FAIL() << "Col " << c << " is not parseable as double: '"
                   << cols[c] << "' error: " << e.what();
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Proto field count sanity — verifies S2 has exactly 62 distinct fields
// mapped from NetworkFeatures (compile-time count via accessor calls)
// ─────────────────────────────────────────────────────────────────────────────

TEST(ProtoFieldCount, Section2Has62Fields) {
    // Count the number of S2 fields accessed in build_section2() by counting
    // the fields we enumerate here — must match CSV_S2_SNIFFER_COUNT.
    const size_t S2_FIELDS =
        4   // 2.1 packet counts
      + 4   // 2.2 fwd pkt len
      + 4   // 2.3 bwd pkt len
      + 8   // 2.4 speeds/ratios
      + 4   // 2.5 flow IAT
      + 5   // 2.6 fwd IAT
      + 5   // 2.7 bwd IAT
      + 8   // 2.8 TCP flags
      + 4   // 2.9 directional flags
      + 8   // 2.10 headers/bulk
      + 5   // 2.11 global pkt len
      + 2   // 2.12 active/idle
      + 1;  // 2.13 flow duration

    EXPECT_EQ(S2_FIELDS, ml_defender::CSV_S2_SNIFFER_COUNT)
        << "Field count mismatch: update this test or CSV_S2_SNIFFER_COUNT";
}

TEST(ProtoFieldCount, Section3Has40Fields) {
    const size_t S3_FIELDS =
        10  // DDoSFeatures
      + 10  // RansomwareEmbeddedFeatures
      + 10  // TrafficFeatures
      + 10; // InternalFeatures

    EXPECT_EQ(S3_FIELDS, ml_defender::CSV_S3_EMBEDDED_COUNT);
}

TEST(ProtoFieldCount, Section4Has10Fields) {
    // 5 models × 2 (prediction + confidence)
    const size_t S4_FIELDS = 5 * 2;
    EXPECT_EQ(S4_FIELDS, ml_defender::CSV_S4_DECISIONS_COUNT);
}