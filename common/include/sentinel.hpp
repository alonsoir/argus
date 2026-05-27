#pragma once

// ============================================================================
// MISSING_FEATURE_SENTINEL — ML Defender shared constant
// ============================================================================
// Valor centinela para features no calculables (flujo insuficiente, división
// por cero, feature fuera del hot path actual).
//
// Propiedades:
//   - Matemáticamente inalcanzable por cualquier ratio real de red
//   - Determinístico: siempre el mismo valor, sin NaN propagation
//   - Compatible con ONNX Runtime y FAISS (float32 well-defined)
//   - Compartido por todos los componentes — NO redefinir localmente
//
// Uso:
//   #include "common/sentinel.hpp"
//   smb->set_rst_ratio(ml_defender::MISSING_FEATURE_SENTINEL);
//
// Referencia: ADR-012 §4 (MISSING_FEATURE_SENTINEL desde cabecera común)
// ============================================================================

namespace ml_defender {

inline constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;

}  // namespace ml_defender
