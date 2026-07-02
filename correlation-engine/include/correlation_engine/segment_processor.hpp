#pragma once
// correlation-engine/include/correlation_engine/segment_processor.hpp
// DAY 204 — extraido de main.cpp (antes lambda inline) para que produccion
// y los tests de circuito completo (emecas+++, DEBT-EMECAS-PLUS-PLUS)
// ejerzan EXACTAMENTE el mismo codigo. Cero reimplementacion, cero deriva.
#include <string>
#include <vector>
#include <cstdint>
#include "correlation_engine/i_graph_sink.hpp"

namespace argus::correlation {

struct SegmentProcessResult {
    uint64_t total;
    uint64_t discarded;
};

// Lee un segmento bronce COMPLETO (fichero .csv inmutable, DAY 203) linea a
// linea: parse_and_verify -> flow_uid -> sink.write. Devuelve contadores del
// segmento (el llamador decide si acumula globales, como hace main()).
SegmentProcessResult process_segment(const std::string& path,
                                      const std::vector<uint8_t>& hmac_key,
                                      IGraphSink& sink);

} // namespace argus::correlation
