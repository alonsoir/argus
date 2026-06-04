#include <gtest/gtest.h>
#include <correlation_engine/correlation_reader.hpp>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

using namespace argus::correlation;

namespace {
const std::vector<uint8_t> KEY(32, 0xAB);  // clave de test, 32 bytes

std::string hmac_hex(const std::vector<uint8_t>& key, const std::string& msg) {
    unsigned char d[EVP_MAX_MD_SIZE]; unsigned int dl = 0;
    HMAC(EVP_sha256(), key.data(), (int)key.size(),
         (const unsigned char*)msg.data(), msg.size(), d, &dl);
    std::ostringstream s; s << std::hex << std::setfill('0');
    for (unsigned i = 0; i < dl; ++i) s << std::setw(2) << (unsigned)d[i];
    return s.str();
}

// body de 18 campos (cols 0-17), igual layout que produce el CorrelationWriter.
const std::string BODY =
    "1,argus,evt-1,node-uuid-xyz,1:IN7uqVpMWxpmuhQTowSQB2XEe0E=,"
    "1717480800,123456000,147.32.84.165,74.125.232.195,1027,80,tcp,"
    "MALICIOUS,DDOS,0.910000,0.870000,0.890000,4";

std::string valid_line() { return BODY + "," + hmac_hex(KEY, BODY); }
}  // namespace

TEST(CorrelationReader, ValidRoundTrip) {
    auto r = parse_and_verify(valid_line(), KEY);
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(r->schema_version, "1");
    EXPECT_EQ(r->source_sensor, "argus");
    EXPECT_EQ(r->community_id, "1:IN7uqVpMWxpmuhQTowSQB2XEe0E=");
    EXPECT_EQ(r->flow_start_sec, 1717480800);
    EXPECT_EQ(r->flow_start_nano, 123456000);
    EXPECT_EQ(r->src_port, 1027u);
    EXPECT_EQ(r->dst_port, 80u);
    EXPECT_EQ(r->protocol, "tcp");
    EXPECT_EQ(r->final_classification, "MALICIOUS");
    EXPECT_EQ(r->authoritative_source, 4);
    EXPECT_DOUBLE_EQ(r->ml_detector_score, 0.87);
}

TEST(CorrelationReader, RejectsTampering) {
    // Alterar el cuerpo sin recomputar el HMAC -> debe rechazar.
    std::string tampered = valid_line();
    auto pos = tampered.find("MALICIOUS");
    tampered.replace(pos, 9, "BENIGN!!!");  // misma longitud, HMAC ya no cuadra
    EXPECT_FALSE(parse_and_verify(tampered, KEY).has_value());
}

TEST(CorrelationReader, RejectsTruncatedLine) {
    // Simula append no-atómico: última línea cortada a la mitad.
    std::string line = valid_line();
    std::string truncated = line.substr(0, line.size() / 2);
    EXPECT_FALSE(parse_and_verify(truncated, KEY).has_value());
}

TEST(CorrelationReader, RejectsWrongKey) {
    std::vector<uint8_t> wrong(32, 0xCD);
    EXPECT_FALSE(parse_and_verify(valid_line(), wrong).has_value());
}

TEST(CorrelationReader, RejectsWrongColumnCount) {
    // body con una columna de más, HMAC recalculado sobre el body malo:
    std::string bad_body = BODY + ",extra";
    std::string line = bad_body + "," + hmac_hex(KEY, bad_body);
    EXPECT_FALSE(parse_and_verify(line, KEY).has_value());  // HMAC válido pero 19 != 20 campos
}

TEST(CorrelationReader, RejectsNonNumericField) {
    // src_port no numérico, HMAC recalculado para aislar el fallo de parseo:
    std::string bad = BODY;
    bad.replace(bad.find(",1027,"), 6, ",NOPE,");
    std::string line = bad + "," + hmac_hex(KEY, bad);
    EXPECT_FALSE(parse_and_verify(line, KEY).has_value());
}