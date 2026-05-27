// firewall_csv_event_loader.cpp
// Day 69
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)

#include "firewall_csv_event_loader.hpp"

#include <sstream>
#include <vector>
#include <stdexcept>
#include <iomanip>
#include <openssl/hmac.h>
#include <openssl/sha.h>

namespace ml_defender {

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

FirewallCsvEventLoader::FirewallCsvEventLoader(const std::string& hmac_key_hex)
    : hmac_key_hex_(hmac_key_hex)
    , hmac_enabled_(!hmac_key_hex.empty())
{}

// ---------------------------------------------------------------------------
// parse()
// ---------------------------------------------------------------------------

FirewallParseResult FirewallCsvEventLoader::parse(const std::string& line,
                                                   FirewallEvent& out) const
{
    // Skip empty lines and comment lines
    if (line.empty() || line[0] == '#' || line[0] == '\r') {
        return FirewallParseResult::EMPTY_LINE;
    }

    // Split on commas
    std::vector<std::string> cols;
    cols.reserve(EXPECTED_COLS);
    std::stringstream ss(line);
    std::string token;
    while (std::getline(ss, token, ',')) {
        // Trim CR if present (Windows line endings)
        if (!token.empty() && token.back() == '\r') token.pop_back();
        cols.push_back(std::move(token));
    }

    if (static_cast<int>(cols.size()) != EXPECTED_COLS) {
        ++parse_errors_;
        return FirewallParseResult::MALFORMED;
    }

    // Parse fields
    try {
        out.timestamp_ms    = std::stoull(cols[0]);
        out.source_ip       = cols[1];
        out.dest_ip         = cols[2];
        out.classification  = cols[3];
        out.action          = cols[4];
        out.score           = std::stof(cols[5]);
        out.hmac_hex        = cols[6];
        out.trace_id        = "";  // populated externally once trace_id is wired
    } catch (const std::exception&) {
        ++parse_errors_;
        return FirewallParseResult::MALFORMED;
    }

    // HMAC verification
    // The signed payload is cols[0..5] joined with commas (everything except the HMAC itself)
    if (hmac_enabled_) {
        std::string payload = cols[0] + "," + cols[1] + "," + cols[2] + ","
                            + cols[3] + "," + cols[4] + "," + cols[5];
        if (!verify_hmac(payload, out.hmac_hex)) {
            ++hmac_failures_;
            return FirewallParseResult::HMAC_FAILURE;
        }
    }

    ++parsed_ok_;
    return FirewallParseResult::OK;
}

// ---------------------------------------------------------------------------
// HMAC verification — same approach as CsvEventLoader
// ---------------------------------------------------------------------------

bool FirewallCsvEventLoader::verify_hmac(const std::string& payload,
                                          const std::string& expected_hex) const
{
    // Decode hex key
    if (hmac_key_hex_.size() % 2 != 0) return false;
    std::vector<unsigned char> key;
    key.reserve(hmac_key_hex_.size() / 2);
    for (size_t i = 0; i < hmac_key_hex_.size(); i += 2) {
        unsigned int byte;
        if (std::sscanf(hmac_key_hex_.c_str() + i, "%02x", &byte) != 1) return false;
        key.push_back(static_cast<unsigned char>(byte));
    }

    // Compute HMAC-SHA256
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int  digest_len = 0;
    HMAC(EVP_sha256(),
         key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(payload.data()),
         payload.size(),
         digest, &digest_len);

    // Encode to hex
    std::ostringstream hex_ss;
    hex_ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < digest_len; ++i)
        hex_ss << std::setw(2) << static_cast<unsigned int>(digest[i]);

    return hex_ss.str() == expected_hex;
}

// ---------------------------------------------------------------------------
// Stats accessors
// ---------------------------------------------------------------------------

uint64_t FirewallCsvEventLoader::parsed_ok()     const { return parsed_ok_.load(); }
uint64_t FirewallCsvEventLoader::hmac_failures() const { return hmac_failures_.load(); }
uint64_t FirewallCsvEventLoader::parse_errors()  const { return parse_errors_.load(); }

} // namespace ml_defender