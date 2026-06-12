// test_correlation_roundtrip.cpp — DAY 175 PRUEBA DE ORO del contrato correlation_v1.
// Escribe con el CorrelationWriter REAL (ml-detector) y lee con parse_and_verify REAL
// (correlation-engine). Garantiza cero deriva entre las 19 columnas: writer produce,
// reader consume, byte a byte. Authors: Alonso Isidoro Roman + Claude (Anthropic)
#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include <correlation_engine/correlation_reader.hpp>

#include <network_security.pb.h>
#include <google/protobuf/timestamp.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <cstdint>
#include <cstdio>
#include <memory>

namespace fs = std::filesystem;
using namespace argus::correlation;

namespace {

// Misma clave en ambos lados: hex de 64 chars -> 32 bytes crudos.
// El writer la consume como hex (config.hmac_key_hex); el reader como bytes.
const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned int b;
        std::sscanf(hex.c_str() + i, "%02x", &b);
        out.push_back(static_cast<uint8_t>(b));
    }
    return out;
}

std::string last_line(const std::string& path) {
    std::ifstream f(path);
    std::string line, last;
    while (std::getline(f, line)) {
        if (!line.empty()) last = line;
    }
    return last;
}

}  // namespace

TEST(CorrelationRoundTrip, WriterToReader) {
    // 1. Evento con valores conocidos
    protobuf::NetworkSecurityEvent event;
    event.set_event_id("evt-rt-001");
    event.set_originating_node_id("node-uuid-roundtrip");
    event.set_final_classification("MALICIOUS");
    event.set_threat_category("DDOS");
    event.set_fast_detector_score(0.910000);
    event.set_ml_detector_score(0.870000);
    event.set_overall_threat_score(0.890000);
    event.set_authoritative_source(::protobuf::DETECTOR_SOURCE_ML_PRIORITY);  // = 4

    auto* nf = event.mutable_network_features();
    nf->set_community_id("1:IN7uqVpMWxpmuhQTowSQB2XEe0E=");
    nf->set_source_ip("147.32.84.165");
    nf->set_destination_ip("74.125.232.195");
    nf->set_source_port(1027u);
    nf->set_destination_port(80u);
    nf->set_protocol_name("tcp");
    nf->mutable_flow_start_time()->set_seconds(1717480800);
    nf->mutable_flow_start_time()->set_nanos(123456000);

    // 2. Writer REAL escribe a un tmpdir
    std::string base = (fs::temp_directory_path() /
        ("corr_rt_" + std::to_string(::getpid()))).string();
    fs::remove_all(base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = base;
    cfg.hmac_key_hex = KEY_HEX;

    auto logger = std::make_shared<spdlog::logger>(
        "rt-test", std::make_shared<spdlog::sinks::null_sink_mt>());

    std::string written_path;
    {
        ml_defender::CorrelationWriter writer(cfg, logger);
        ASSERT_TRUE(writer.write_record(event));
        writer.flush();
        written_path = writer.get_stats().current_file;
    }
    ASSERT_FALSE(written_path.empty());
    ASSERT_TRUE(fs::exists(written_path));

    // 3. Reader REAL consume la linea escrita
    std::string line = last_line(written_path);
    ASSERT_FALSE(line.empty());

    auto rec = parse_and_verify(line, hex_to_bytes(KEY_HEX));
    ASSERT_TRUE(rec.has_value()) << "HMAC invalido o parseo fallido: " << line;

    // 4. Cero deriva: cada columna del record == lo que metio el evento
    EXPECT_EQ(rec->schema_version,       "1");
    EXPECT_EQ(rec->source_sensor,        "argus");
    EXPECT_EQ(rec->event_id,             "evt-rt-001");
    EXPECT_EQ(rec->node_id,              "node-uuid-roundtrip");
    EXPECT_EQ(rec->community_id,         "1:IN7uqVpMWxpmuhQTowSQB2XEe0E=");
    EXPECT_EQ(rec->flow_start_sec,       1717480800);
    EXPECT_EQ(rec->flow_start_nano,      123456000);
    EXPECT_EQ(rec->src_ip,               "147.32.84.165");
    EXPECT_EQ(rec->dst_ip,               "74.125.232.195");
    EXPECT_EQ(rec->src_port,             1027u);
    EXPECT_EQ(rec->dst_port,             80u);
    EXPECT_EQ(rec->protocol,             "tcp");
    EXPECT_EQ(rec->final_classification, "MALICIOUS");
    EXPECT_EQ(rec->threat_category,      "DDOS");
    EXPECT_DOUBLE_EQ(rec->fast_detector_score,  0.91);
    EXPECT_DOUBLE_EQ(rec->ml_detector_score,    0.87);
    EXPECT_DOUBLE_EQ(rec->overall_threat_score, 0.89);
    EXPECT_EQ(rec->authoritative_source, "DETECTOR_SOURCE_ML_PRIORITY");  // SELLO columna 17: simbolo DetectorSource

    fs::remove_all(base);
}
