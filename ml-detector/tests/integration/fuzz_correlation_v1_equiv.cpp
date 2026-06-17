// fuzz_correlation_v1_equiv.cpp — aRGus NDR — DAY 187
// FUZZ DIFERENCIAL: serialize(to_row(event)) debe ser BYTE-IDÉNTICO a lo que
// write_record/build_row (ORÁCULO, aún vivo) escribe y lee de vuelta, sobre
// dominio ALEATORIO — la fortaleza que el golden (21 vectores) no da.
//
// DOMINIO: NO inyecta \n/\r. Sobre ese dominio serialize RECHAZA (guard Camino A,
// DEBT-BRONZE-EMBEDDED-NEWLINE-001) y write_record ESCRIBE → divergen A PROPÓSITO.
// Esa frontera la cubre el test P2. Aquí: equivalencia donde AMBOS coinciden.
//
// INVARIANTES (por input):
//   (1) to_row=Skip (community_id vacío) → oráculo NO escribió. Paridad SKIP.
//   (2) to_row=Ok → serialize.line == oráculo_bytes. Byte-identidad.
//   (3) to_row=Ok, sin \n/\r, serialize !ok → FALLO REAL.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
#include "correlation_writer.hpp"
#include <correlation_v1/correlation_v1.hpp>
#include <network_security.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <locale>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

// Misma clave que capture_golden / test_correlation_roundtrip (64 hex → 32 bytes).
static const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

static std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i + 1 < hex.size(); i += 2)
        out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    return out;
}

namespace {
struct Reader {
    const uint8_t* p; size_t n; size_t i = 0;
    Reader(const uint8_t* d, size_t s) : p(d), n(s) {}
    uint8_t u8()  { return i < n ? p[i++] : 0; }
    uint32_t u32(){ uint32_t v=0; for(int k=0;k<4;k++) v=(v<<8)|u8(); return v; }
    int64_t  i64(){ int64_t v=0; for(int k=0;k<8;k++) v=(v<<8)|u8(); return v; }
    double   dbl(){ uint64_t b=0; for(int k=0;k<8;k++) b=(b<<8)|u8();
                    double d; std::memcpy(&d,&b,8); return d; }
    // String SIN \n/\r (dominio de equivalencia). Longitud acotada.
    std::string str(size_t maxlen) {
        size_t len = maxlen ? (u8() % (maxlen + 1)) : 0;
        std::string s; s.reserve(len);
        for (size_t k = 0; k < len; ++k) {
            char c = static_cast<char>(u8());
            if (c == '\n' || c == '\r') c = '_';   // expulsa del dominio
            s += c;
        }
        return s;
    }
};

// Los 7 símbolos válidos de DetectorSource (proto: 0..6). Fuzzeamos col 17.
::protobuf::DetectorSource pick_source(uint8_t b) {
    switch (b % 7) {
        case 0: return ::protobuf::DETECTOR_SOURCE_UNKNOWN;
        case 1: return ::protobuf::DETECTOR_SOURCE_FAST_ONLY;
        case 2: return ::protobuf::DETECTOR_SOURCE_ML_ONLY;
        case 3: return ::protobuf::DETECTOR_SOURCE_FAST_PRIORITY;
        case 4: return ::protobuf::DETECTOR_SOURCE_ML_PRIORITY;
        case 5: return ::protobuf::DETECTOR_SOURCE_CONSENSUS;
        default:return ::protobuf::DETECTOR_SOURCE_DIVERGENCE;
    }
}

// Bytes que el ORÁCULO (write_record/build_row) escribe y se leen de vuelta.
std::optional<std::string> oracle_bytes(
        const protobuf::NetworkSecurityEvent& ev,
        std::shared_ptr<spdlog::logger> logger) {
    static uint64_t ctr = 0;
    const std::string base =
        (fs::temp_directory_path() / ("fuzz_oracle_" + std::to_string(ctr++))).string();
    fs::remove_all(base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = base;
    cfg.hmac_key_hex = KEY_HEX;

    bool ok = false; std::string path;
    {
        ml_defender::CorrelationWriter w(cfg, logger);
        ok = w.write_record(ev);
        w.flush();
        path = w.get_stats().current_file;
    }
    std::optional<std::string> result;
    if (ok && !path.empty() && fs::exists(path)) {
        std::ifstream in(path, std::ios::binary);
        std::ostringstream ss; ss << in.rdbuf();
        std::string c = ss.str();
        if (!c.empty() && c.back() == '\n') c.pop_back();
        result = c;
    }
    fs::remove_all(base);
    return result;
}

std::shared_ptr<spdlog::logger> g_logger;
}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    if (!g_logger) {
        g_logger = std::make_shared<spdlog::logger>(
            "fuzz", std::make_shared<spdlog::sinks::null_sink_mt>());
        std::locale::global(std::locale::classic());  // asunción de producción (D-E)
    }
    Reader r(data, size);

    protobuf::NetworkSecurityEvent ev;
    ev.set_event_id(r.str(24));
    ev.set_originating_node_id(r.str(24));
    ev.set_final_classification(r.str(16));
    ev.set_threat_category(r.str(16));
    ev.set_fast_detector_score(r.dbl());
    ev.set_ml_detector_score(r.dbl());
    ev.set_overall_threat_score(r.dbl());
    ev.set_authoritative_source(pick_source(r.u8()));   // col 17: fuzzea los 7 símbolos

    auto* nf = ev.mutable_network_features();
    nf->set_community_id(r.str(20));        // a veces vacío → ejercita SKIP (inv. 1)
    nf->set_source_ip(r.str(15));
    nf->set_destination_ip(r.str(15));
    nf->set_source_port(r.u32() & 0xFFFFu);
    nf->set_destination_port(r.u32() & 0xFFFFu);
    nf->set_protocol_name(r.str(8));
    nf->mutable_flow_start_time()->set_seconds(r.i64());
    nf->mutable_flow_start_time()->set_nanos(static_cast<int32_t>(r.u32()));

    const auto key = hex_to_bytes(KEY_HEX);

    auto tr = ml_defender::to_correlation_v1_row(ev);
    auto oracle = oracle_bytes(ev, g_logger);

    using S = ml_defender::ToRowResult::Status;

    if (tr.status == S::Skip) {
        if (oracle.has_value()) {
            std::fprintf(stderr,
              "DIVERGENCIA SKIP: to_row=Skip pero oraculo escribio: %s\n",
              oracle->c_str());
            __builtin_trap();
        }
        return 0;
    }
    if (tr.status == S::Error) {
        return 0;   // v1 no emite Error (D-D diferido)
    }

    // tr.status == Ok
    auto sr = correlation_v1::serialize(tr.row, key);

    if (!sr) {
        std::fprintf(stderr,
          "DIVERGENCIA SERIALIZE-FALLO: to_row=Ok, sin newline, serialize rechazo: %s\n",
          sr.error.c_str());
        __builtin_trap();
    }
    if (!oracle.has_value()) {
        std::fprintf(stderr,
          "DIVERGENCIA ORACULO-VACIO: to_row=Ok, serialize ok, oraculo no escribio\n");
        __builtin_trap();
    }
    if (sr.line != *oracle) {
        std::fprintf(stderr,
          "DIVERGENCIA BYTES:\n  serialize: %s\n  oraculo:   %s\n",
          sr.line.c_str(), oracle->c_str());
        __builtin_trap();
    }
    return 0;
}
