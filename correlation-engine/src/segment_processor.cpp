// correlation-engine/src/segment_processor.cpp — DAY 204
#include "correlation_engine/segment_processor.hpp"
#include "correlation_engine/correlation_reader.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <fstream>
#include <spdlog/spdlog.h>

namespace argus::correlation {

SegmentProcessResult process_segment(const std::string& path,
                                      const std::vector<uint8_t>& hmac_key,
                                      IGraphSink& sink) {
    std::ifstream in(path);
    if (!in) {
        spdlog::warn("[CONSUMER] no se puede abrir segmento: {}", path);
        return {0, 0};
    }
    std::string line;
    uint64_t seg_total = 0, seg_discarded = 0;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        auto rec = parse_and_verify(line, hmac_key);
        if (!rec) { ++seg_discarded; continue; }
        const uint64_t window = window_micros(rec->flow_start_sec, rec->flow_start_nano);
        const std::string fuid = compute_flow_uid(rec->node_id, rec->community_id, window);
        sink.write(*rec, fuid);
        ++seg_total;
    }
    spdlog::info("[CONSUMER] segmento {}: {} materializados, {} descartados",
                 path, seg_total, seg_discarded);
    return {seg_total, seg_discarded};
}

} // namespace argus::correlation
