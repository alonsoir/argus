// test_graph_sink_loop.cpp — DAY 179 (Caso B actualizado DAY 180). Consumidor bronce -> sink.
// Caso A: MockGraphSink cuenta writes -> valida invariante de descarte (Mistral):
//         fila corrupta/HMAC-malo NO llega al sink.
// Caso B: LoggingGraphSink real -> valida que el Cypher se forma con el MODELO NUEVO
//         (NetworkFlow identidad + Alert + ALERT_ABOUT; sin RAISED, sin 5-tupla).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include <gtest/gtest.h>

#include "correlation_engine/i_graph_sink.hpp"
#include "correlation_engine/logging_graph_sink.hpp"
#include "correlation_engine/correlation_reader.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <openssl/hmac.h>
#include <openssl/evp.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
#include <cstdint>

using namespace argus::correlation;

namespace {

const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i + 1 < hex.size(); i += 2)
        out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    return out;
}

std::string hmac_hex(const std::vector<uint8_t>& key, const std::string& msg) {
    unsigned char d[EVP_MAX_MD_SIZE];
    unsigned int dl = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(msg.data()), msg.size(), d, &dl);
    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < dl; ++i) ss << std::setw(2) << static_cast<int>(d[i]);
    return ss.str();
}

// Construye una fila bronce valida (18 cols + HMAC) con community_id no vacio.
std::string make_valid_row(const std::vector<uint8_t>& key, const std::string& event_id) {
    std::ostringstream body;
    body << "1,"                         // 0 schema_version
         << "argus,"                      // 1 source_sensor
         << event_id << ","               // 2 event_id
         << "node-test,"                  // 3 node_id
         << "1:abcdEF==,"                 // 4 community_id (no vacio)
         << "1700000000,"                 // 5 flow_start_sec
         << "123456,"                     // 6 flow_start_nano
         << "10.0.0.1,"                   // 7 src_ip
         << "10.0.0.2,"                   // 8 dst_ip
         << "1234,"                       // 9 src_port
         << "443,"                        // 10 dst_port
         << "TCP,"                        // 11 protocol
         << "MALICIOUS,"                  // 12 final_classification
         << "c2,"                         // 13 threat_category
         << "0.91,"                       // 14 fast_detector_score
         << "0.97,"                       // 15 ml_detector_score
         << "0.95,"                       // 16 overall_threat_score
         << "DETECTOR_SOURCE_CONSENSUS";  // 17 authoritative_source
    const std::string b = body.str();
    return b + "," + hmac_hex(key, b);
}

// MockGraphSink: cuenta writes, no toca disco.
class MockGraphSink final : public IGraphSink {
public:
    bool write(const CorrelationRecord&, std::string_view) override { ++n_; return true; }
    void flush() override {}
    int count() const { return n_; }
private:
    int n_ = 0;
};

// Procesa un conjunto de lineas igual que hara el loop del main: parse_and_verify
// -> flow_uid -> sink.write. Devuelve nº de filas que llegaron al sink.
int process_lines(const std::vector<std::string>& lines,
                  const std::vector<uint8_t>& key,
                  IGraphSink& sink) {
    int delivered = 0;
    for (const auto& line : lines) {
        auto rec = parse_and_verify(line, key);
        if (!rec) continue;  // invariante: corrupta/HMAC-malo descartada antes del sink
        const uint64_t window = window_micros(rec->flow_start_sec, rec->flow_start_nano);
        const std::string fuid = compute_flow_uid(rec->node_id, rec->community_id, window);
        if (sink.write(*rec, fuid)) ++delivered;
    }
    sink.flush();
    return delivered;
}

}  // namespace

// ── Caso A: invariante de descarte con MockGraphSink ────────────────────────
TEST(GraphSinkLoop, DiscardsInvalidBeforeSink) {
    const auto key = hex_to_bytes(KEY_HEX);
    std::vector<std::string> lines;
    lines.push_back(make_valid_row(key, "ev-1"));
    lines.push_back(make_valid_row(key, "ev-2"));
    lines.push_back("solo,tres,columnas");                 // corrupta: != 19 cols
    {
        // fila con HMAC manipulado (tampering): body valido, HMAC de otra clave
        const auto wrong = hex_to_bytes(
            "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd");
        lines.push_back(make_valid_row(wrong, "ev-tampered"));
    }
    lines.push_back(make_valid_row(key, "ev-3"));

    MockGraphSink sink;
    const int delivered = process_lines(lines, key, sink);

    EXPECT_EQ(delivered, 3);          // 3 validas
    EXPECT_EQ(sink.count(), 3);       // exactamente las 3 llegaron al sink
}

// ── Caso B: el Cypher se forma con LoggingGraphSink real (MODELO NUEVO) ──────
TEST(GraphSinkLoop, LoggingSinkFormsCypher) {
    const auto key = hex_to_bytes(KEY_HEX);
    auto logger = std::make_shared<spdlog::logger>(
        "test", std::make_shared<spdlog::sinks::null_sink_mt>());

    LoggingGraphSink sink(logger);
    std::vector<std::string> lines{ make_valid_row(key, "ev-cypher") };
    const int delivered = process_lines(lines, key, sink);

    EXPECT_EQ(delivered, 1);
    EXPECT_EQ(sink.writes(), 1u);

    // Verifica el formato del Cypher directamente (sin depender del log).
    auto rec = parse_and_verify(lines[0], key);
    ASSERT_TRUE(rec.has_value());
    const uint64_t window = window_micros(rec->flow_start_sec, rec->flow_start_nano);
    const std::string fuid = compute_flow_uid(rec->node_id, rec->community_id, window);
    const std::string cypher = LoggingGraphSink::build_cypher(*rec, fuid);

    // Modelo nuevo: la fila es MALICIOUS -> Alert + ALERT_ABOUT.
    EXPECT_NE(cypher.find("MERGE (f:NetworkFlow"), std::string::npos);
    EXPECT_NE(cypher.find("e:Alert"), std::string::npos);
    EXPECT_NE(cypher.find(":ALERT_ABOUT"), std::string::npos);
    EXPECT_NE(cypher.find("final_classification='MALICIOUS'"), std::string::npos);
    EXPECT_NE(cypher.find(fuid), std::string::npos);           // flow_uid presente
    EXPECT_NE(cypher.find("ev-cypher"), std::string::npos);    // event_id presente

    // Modelo viejo RETIRADO + identidad pura: ni :RAISED ni la 5-tupla en el grafo.
    EXPECT_EQ(cypher.find(":RAISED"), std::string::npos);
    EXPECT_EQ(cypher.find("10.0.0.1"), std::string::npos);     // src_ip NO viaja al grafo
    EXPECT_EQ(cypher.find("TelemetryEvent"), std::string::npos); // MALICIOUS no enruta a Telemetry
}