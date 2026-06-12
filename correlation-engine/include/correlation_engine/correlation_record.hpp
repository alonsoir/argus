// correlation_record.hpp — registro de correlación parseado (contrato correlation_v1).
// Espejo consumidor del CorrelationWriter (ml-detector). 19 columnas, sin header.
#pragma once
#include <cstdint>
#include <string>

namespace argus::correlation {

    inline constexpr std::size_t CORRELATION_V1_COLS = 19;  // incluye HMAC (col 18)

    struct CorrelationRecord {
        std::string schema_version;        // 0
        std::string source_sensor;         // 1  "argus" | "suricata" | ...
        std::string event_id;              // 2
        std::string node_id;               // 3
        std::string community_id;          // 4  clave de join (nunca vacía: el writer las descarta)
        int64_t     flow_start_sec  = 0;   // 5
        int32_t     flow_start_nano = 0;   // 6
        std::string src_ip;                // 7
        std::string dst_ip;                // 8
        uint32_t    src_port = 0;          // 9
        uint32_t    dst_port = 0;          // 10
        std::string protocol;              // 11
        std::string final_classification;  // 12
        std::string threat_category;       // 13
        double      fast_detector_score   = 0.0;  // 14
        double      ml_detector_score     = 0.0;  // 15
        double      overall_threat_score  = 0.0;  // 16
        std::string authoritative_source;  // 17  simbolo DetectorSource (string auto-descriptivo)
        // col 18 (HMAC) se valida, no se almacena.
    };

}  // namespace argus::correlation