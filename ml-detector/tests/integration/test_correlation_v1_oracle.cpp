// test_correlation_v1_oracle.cpp — aRGus NDR — DAY 185 (B3)
// CIERRE DEL LAZO: prueba la byte-identidad del refactor. Por cada vector compartido
// (correlation_v1_golden_vectors.hpp), exige que serialize(to_row(event)) coincida
//   (a) con el GOLDEN congelado por capture_golden (B2), y
//   (b) con write_record(event) EN VIVO (guard de la opción B: el oráculo aún existe).
// Vectores SKIPPED: to_row debe devolver Skip exacto (sella D-F).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// LOCALE: fija classic. write_record (build_row, sin imbue) debe producir bytes
// classic para casar con serialize() (que fuerza classic) y con el golden (classic).
// Es la asunción de producción; la robustez de serialize ante otros locales la
// prueba el test de la lib (P0b), no este.
//
// DIAGNÓSTICO: en divergencia, reporta longitudes, offset del primer byte distinto,
// el byte esperado vs obtenido (hex + char), columna aprox y ventana de contexto.
#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include "correlation_v1_golden_vectors.hpp"
#include <correlation_v1/correlation_v1.hpp>
#include <network_security.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <locale>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

#ifndef GOLDEN_PATH
#define GOLDEN_PATH "data/correlation_v1_golden.tsv"
#endif

namespace {

// Misma clave que capture_golden y test_correlation_roundtrip.
const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

std::string hex_to_str(const std::string& hex) {
    std::string out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        unsigned int b;
        if (std::sscanf(hex.c_str() + i, "%02x", &b) != 1) break;
        out += static_cast<char>(b);
    }
    return out;
}

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        unsigned int b;
        if (std::sscanf(hex.c_str() + i, "%02x", &b) != 1) break;
        out.push_back(static_cast<uint8_t>(b));
    }
    return out;
}

std::vector<std::string> split_tab(const std::string& s) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : s) {
        if (c == '\t') { out.push_back(cur); cur.clear(); }
        else cur += c;
    }
    out.push_back(cur);
    return out;
}

// id -> (status, bytes-decodificados). bytes vacío si SKIPPED.
std::map<std::string, std::pair<std::string, std::string>> load_golden(const std::string& path) {
    std::map<std::string, std::pair<std::string, std::string>> out;
    std::ifstream f(path);
    std::string line;
    while (std::getline(f, line)) {
        if (line.empty() || line[0] == '#') continue;
        auto cols = split_tab(line);
        if (cols.size() < 3) continue;
        const std::string& id     = cols[0];
        const std::string& status = cols[2];
        std::string hexb = (cols.size() >= 4) ? cols[3] : "";
        out[id] = {status, hex_to_str(hexb)};
    }
    return out;
}

std::string esc_char(char c) {
    unsigned char u = static_cast<unsigned char>(c);
    if (u == '\n') return "\\n";
    if (u == '\r') return "\\r";
    if (u == '\t') return "\\t";
    if (u >= 32 && u < 127) return std::string(1, c);
    char b[8];
    std::snprintf(b, sizeof(b), "\\x%02x", u);
    return std::string(b);
}

std::string esc_window(const std::string& s, size_t center, size_t radius) {
    size_t a = (center > radius) ? center - radius : 0;
    size_t b = std::min(s.size(), center + radius + 1);
    std::string out;
    for (size_t k = a; k < b; ++k) out += esc_char(s[k]);
    return out;
}

// Reporte de divergencia byte a byte.
std::string byte_diff_report(const std::string& id, const std::string& which,
                             const std::string& expected, const std::string& actual) {
    std::ostringstream os;
    os << "\n[" << id << "] divergencia vs " << which << ":\n";
    os << "  len esperado=" << expected.size()
       << "  len obtenido=" << actual.size() << "\n";

    const size_t n = std::min(expected.size(), actual.size());
    size_t i = 0;
    while (i < n && expected[i] == actual[i]) ++i;

    // columna aprox: cuenta comas (naive; los campos entrecomillados con coma la
    // sobrecuentan, por eso "aprox"). La ventana de contexto es el diagnóstico real.
    size_t col = 0;
    for (size_t k = 0; k < i && k < expected.size(); ++k)
        if (expected[k] == ',') ++col;

    os << "  primer byte distinto en offset " << i
       << " (columna aprox " << col << ")\n";

    auto at = [](const std::string& s, size_t k) -> std::string {
        if (k >= s.size()) return "(fin)";
        char b[16];
        std::snprintf(b, sizeof(b), "0x%02x '%s'",
                      static_cast<unsigned char>(s[k]), esc_char(s[k]).c_str());
        return std::string(b);
    };
    os << "    esperado[" << i << "] = " << at(expected, i) << "\n";
    os << "    obtenido[" << i << "] = " << at(actual, i) << "\n";
    os << "    contexto esperado: ...|" << esc_window(expected, i, 12) << "|...\n";
    os << "    contexto obtenido: ...|" << esc_window(actual, i, 12) << "|...\n";
    return os.str();
}

// Bytes que el ORÁCULO produce AHORA mismo (write_record), por su path público.
std::optional<std::string> oracle_live_bytes(
        const protobuf::NetworkSecurityEvent& ev, const std::string& id,
        std::shared_ptr<spdlog::logger> logger) {
    const std::string base =
        (fs::temp_directory_path() / ("oracle_live_" + id)).string();
    fs::remove_all(base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = base;
    cfg.hmac_key_hex = KEY_HEX;

    bool ok = false;
    std::string path;
    {
        ml_defender::CorrelationWriter w(cfg, logger);
        ok = w.write_record(ev);
        w.flush();
        path = w.get_stats().current_file;
    }

    std::optional<std::string> result;
    if (ok && !path.empty() && fs::exists(path)) {
        std::ifstream in(path, std::ios::binary);
        std::ostringstream ss;
        ss << in.rdbuf();
        std::string content = ss.str();
        if (!content.empty() && content.back() == '\n') content.pop_back();
        result = content;
    }
    fs::remove_all(base);
    return result;
}

}  // namespace

class OracleByteIdentity : public ::testing::Test {
protected:
    void SetUp() override {
        std::locale::global(std::locale::classic());  // ver nota de cabecera
    }
};

TEST_F(OracleByteIdentity, SerializeMatchesGoldenAndLiveOracle) {
    auto golden = load_golden(GOLDEN_PATH);
    ASSERT_FALSE(golden.empty())
        << "golden vacío o no encontrado: " << GOLDEN_PATH;

    const auto key = hex_to_bytes(KEY_HEX);
    ASSERT_EQ(key.size(), 32u) << "clave HMAC de test mal formada";

    auto null_logger = std::make_shared<spdlog::logger>(
        "oracle-test", std::make_shared<spdlog::sinks::null_sink_mt>());

    std::set<std::string> seen;

    for (const auto& gv : argus_golden::make_golden_vectors()) {
        seen.insert(gv.id);
        auto it = golden.find(gv.id);
        ASSERT_NE(it, golden.end())
            << "vector '" << gv.id << "' sin entrada en el golden";
        const std::string& g_status = it->second.first;
        const std::string& g_bytes  = it->second.second;

        auto tr = ml_defender::to_correlation_v1_row(gv.event);

        if (gv.expect_skip) {
            // D-F: community_id vacío -> Skip exacto (ni Ok ni Error).
            EXPECT_EQ(tr.status, ml_defender::ToRowResult::Status::Skip)
                << "[" << gv.id << "] esperaba Skip (D-F)";
            EXPECT_EQ(g_status, "SKIPPED")
                << "[" << gv.id << "] golden no marca SKIPPED";
            continue;
        }

        EXPECT_EQ(g_status, "WRITTEN")
            << "[" << gv.id << "] golden no marca WRITTEN";
        ASSERT_EQ(tr.status, ml_defender::ToRowResult::Status::Ok)
            << "[" << gv.id << "] to_row no devolvió Ok: " << tr.error;

        auto sr = correlation_v1::serialize(tr.row, key);
        ASSERT_TRUE(sr.ok)
            << "[" << gv.id << "] serialize falló: " << sr.error;

        // (a) byte-identidad contra el golden congelado (B2).
        if (sr.line != g_bytes) {
            ADD_FAILURE() << byte_diff_report(gv.id, "golden", g_bytes, sr.line);
        }

        // (b) guard en vivo: contra write_record AHORA (el oráculo aún existe, opción B).
        auto live = oracle_live_bytes(gv.event, gv.id, null_logger);
        ASSERT_TRUE(live.has_value())
            << "[" << gv.id << "] el oráculo en vivo no escribió (¿skip inesperado?)";
        if (sr.line != *live) {
            ADD_FAILURE() << byte_diff_report(gv.id, "oraculo-en-vivo", *live, sr.line);
        }
    }

    // Cobertura inversa: ningún id del golden sin vector.
    for (const auto& kv : golden) {
        EXPECT_TRUE(seen.count(kv.first) > 0)
            << "golden tiene id '" << kv.first
            << "' sin vector en make_golden_vectors()";
    }
}