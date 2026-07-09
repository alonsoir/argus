#pragma once

// DAY 213 — 1b-extract: lógica PURA de la cabeza de traffic, espejo de
// internal_head_logic.hpp. Sin dependencias del handler: mapeo de índices +
// validación de tamaño, testeable con asserts rápidos. El handler (run_traffic_head)
// sólo orquesta. Comportamiento idéntico al bloque inline anterior (zmq_handler
// líneas ~771-782): mismos índices, mismos campos.

#include <vector>
#include <stdexcept>
#include "ml_defender/traffic_detector.hpp"

namespace ml_defender {

    // Mapea el vector de 10 features (salida de extract_level3_traffic_features) al
    // struct Features del TrafficDetector. Índices auditados contra zmq_handler 772-781.
    // Lanza std::invalid_argument si size != 10 (defensa en profundidad; en producción
    // el size-check del extractor dispara antes y cuenta feature_extraction_errors —
    // esta validación es la red del test unitario). Espejo exacto de build_internal_features.
    inline TrafficDetector::Features
    build_traffic_features(const std::vector<float>& v) {
        if (v.size() != 10) {
            throw std::invalid_argument(
                "build_traffic_features: expected 10 features, got " +
                std::to_string(v.size()));
        }
        return TrafficDetector::Features{
            .packet_rate          = v[0],
            .connection_rate      = v[1],
            .tcp_udp_ratio        = v[2],
            .avg_packet_size      = v[3],
            .port_entropy         = v[4],
            .flow_duration_std    = v[5],
            .src_ip_entropy       = v[6],
            .dst_ip_concentration = v[7],
            .protocol_variety     = v[8],
            .temporal_consistency = v[9]
        };
    }

}  // namespace ml_defender