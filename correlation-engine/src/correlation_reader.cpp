#include "correlation_engine/correlation_reader.hpp"
#include "correlation_engine/canonical_double.hpp"
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <iomanip>
#include <sstream>
#include <charconv>

namespace argus::correlation {

namespace {

// Split CSV con comillas (RFC4180-ish): respeta campos entre "..." con "" escapado.
std::vector<std::string> split_csv(const std::string& s) {
    std::vector<std::string> out;
    std::string field;
    bool in_quotes = false;
    for (std::size_t i = 0; i < s.size(); ++i) {
        char c = s[i];
        if (in_quotes) {
            if (c == '"') {
                if (i + 1 < s.size() && s[i + 1] == '"') { field += '"'; ++i; }
                else in_quotes = false;
            } else field += c;
        } else {
            if (c == '"') in_quotes = true;
            else if (c == ',') { out.push_back(field); field.clear(); }
            else field += c;
        }
    }
    out.push_back(field);
    return out;
}

std::string hmac_hex(const std::vector<uint8_t>& key, const std::string& msg) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int dl = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(msg.data()), msg.size(), digest, &dl);
    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < dl; ++i) ss << std::setw(2) << static_cast<unsigned int>(digest[i]);
    return ss.str();
}

// Comparación en tiempo constante para el HMAC (evita timing oracle).
bool ct_equal(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return false;
    unsigned char acc = 0;
    for (std::size_t i = 0; i < a.size(); ++i)
        acc |= static_cast<unsigned char>(a[i]) ^ static_cast<unsigned char>(b[i]);
    return acc == 0;
}

template <typename T>
bool parse_num(const std::string& s, T& out) {
    auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), out);
    return ec == std::errc{} && p == s.data() + s.size();
}

bool parse_double(const std::string& s, double& out) {
    try { std::size_t pos; out = std::stod(s, &pos); return pos == s.size(); }
    catch (...) { return false; }
}

}  // namespace

std::optional<CorrelationRecord> parse_and_verify(const std::string& line,
                                                  const std::vector<uint8_t>& hmac_key) {
    // 1. Separar body | hmac por la ÚLTIMA coma (el HMAC es hex puro, sin comas/comillas).
    std::size_t last = line.rfind(',');
    if (last == std::string::npos) return std::nullopt;
    std::string body = line.substr(0, last);
    std::string sig  = line.substr(last + 1);

    // 2. Validar HMAC ANTES de parsear (frontera de confianza). Detecta tampering Y truncado.
    if (!ct_equal(sig, hmac_hex(hmac_key, body))) return std::nullopt;

    // 3. Parsear body. Debe haber exactamente 18 campos (cols 0-17).
    auto f = split_csv(body);
    if (f.size() != CORRELATION_V1_COLS - 1) return std::nullopt;

    CorrelationRecord r;
    r.schema_version       = f[0];
    r.source_sensor        = f[1];
    r.event_id             = f[2];
    r.node_id              = f[3];
    r.community_id         = f[4];
    if (!parse_num(f[5], r.flow_start_sec))  return std::nullopt;
    if (!parse_num(f[6], r.flow_start_nano)) return std::nullopt;
    r.src_ip               = f[7];
    r.dst_ip               = f[8];
    if (!parse_num(f[9],  r.src_port)) return std::nullopt;
    if (!parse_num(f[10], r.dst_port)) return std::nullopt;
    r.protocol             = f[11];
    r.final_classification = f[12];
    r.threat_category      = f[13];
    if (!parse_double(f[14], r.fast_detector_score))  return std::nullopt;
    if (!parse_double(f[15], r.ml_detector_score))    return std::nullopt;
    if (!parse_double(f[16], r.overall_threat_score)) return std::nullopt;
    // DAY 207 — canonicalizar tras parseo, punto único compartido por
    // Camino 0 (Kuzu) y Flujo A+B (Parquet): ambos parten de aquí.
    r.fast_detector_score   = canonicalize_double(r.fast_detector_score);
    r.ml_detector_score     = canonicalize_double(r.ml_detector_score);
    r.overall_threat_score  = canonicalize_double(r.overall_threat_score);
    r.authoritative_source = f[17];
    return r;
}

}  // namespace argus::correlation