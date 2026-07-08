#pragma once

#include "ml_defender/internal_detector.hpp"
#include <vector>
#include <cstddef>
#include <stdexcept>

namespace ml_defender {

/// Número de features que el modelo interno espera. Contrato del detector.
inline constexpr std::size_t kInternalFeatureCount = 10;

/// Construye el struct tipado Features desde el vector crudo del extractor.
///
/// El ORDEN de los índices ES el contrato del modelo — un desalineamiento
/// aquí envía lateral_movement al slot equivocado y rompe la detección en
/// silencio. Por eso es lógica pura con test dedicado: el mapeo se ancla,
/// no se confía.
///
/// Índices (auditados DAY 211):
///   [0] internal_connection_rate    [5] lateral_movement_score      (REAL)
///   [1] service_port_consistency    [6] service_discovery_patterns
///   [2] protocol_regularity         [7] data_exfiltration_indicators(REAL)
///   [3] packet_size_consistency     [8] temporal_anomaly_score
///   [4] connection_duration_std     [9] access_pattern_entropy
///
/// @throws std::invalid_argument si feats.size() != kInternalFeatureCount.
inline InternalDetector::Features
build_internal_features(const std::vector<float>& feats) {
    if (feats.size() != kInternalFeatureCount) {
        throw std::invalid_argument(
            "build_internal_features: se esperaban 10 features");
    }
    return InternalDetector::Features{
        .internal_connection_rate     = feats[0],
        .service_port_consistency     = feats[1],
        .protocol_regularity          = feats[2],
        .packet_size_consistency      = feats[3],
        .connection_duration_std      = feats[4],
        .lateral_movement_score       = feats[5],
        .service_discovery_patterns   = feats[6],
        .data_exfiltration_indicators = feats[7],
        .temporal_anomaly_score       = feats[8],
        .access_pattern_entropy       = feats[9],
    };
}

/// Resultado de evaluar una predicción interna contra el veredicto de L1.
struct InternalEval {
    bool suspicious;      ///< is_suspicious(pred) sobre el umbral.
    bool is_discrepancy;  ///< suspicious && L1 marcó el flujo como benigno.
};

/// Evalúa una predicción interna: ¿es amenaza?, ¿es un hueco de L1?
///
/// PURA: sin efectos. El handler decide qué hacer con el resultado (contar,
/// loguear, sellar). Aquí solo se calcula.
///
/// is_discrepancy es la métrica central de DEBT-VERDICT-MONOCAPA-001: el
/// interno ve amenaza (lateral/exfil) en un flujo que L1 (genérico) selló
/// como benigno. Cuantifica la cobertura que el paper atribuye a la cabeza
/// interna sobre el clasificador de primer nivel.
///
/// @param label_l1  etiqueta de L1: 1 = attack, cualquier otro = benigno.
inline InternalEval
evaluate_internal(const InternalDetector::Prediction& pred,
                  float threshold, int64_t label_l1) noexcept {
    const bool suspicious = pred.is_suspicious(threshold);
    const bool l1_said_benign = (label_l1 != 1);
    return InternalEval{
        .suspicious     = suspicious,
        .is_discrepancy = suspicious && l1_said_benign,
    };
}

}  // namespace ml_defender
