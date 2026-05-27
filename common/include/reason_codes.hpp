#pragma once
#include <string>

namespace ml_defender {

    // 🎯 ADR-002: Multi-Engine Detection Provenance
    // Códigos de razón estandarizados para todos los detectores

    enum class ReasonCode {
        SIG_MATCH,         // Exact signature match → Immediate block
        STAT_ANOMALY,      // Statistical deviation (Z-score) → Unusual behavior
        PCA_OUTLIER,       // Outside normal latent space → 0-day detection 🎯
        PROT_VIOLATION,    // Protocol malformation → Technical attack
        ENGINE_CONFLICT,   // Engines disagree → High-priority alert 🚨
        UNKNOWN
    };

    inline const char* to_string(ReasonCode code) {
        switch(code) {
            case ReasonCode::SIG_MATCH:       return "SIG_MATCH";
            case ReasonCode::STAT_ANOMALY:    return "STAT_ANOMALY";
            case ReasonCode::PCA_OUTLIER:     return "PCA_OUTLIER";
            case ReasonCode::PROT_VIOLATION:  return "PROT_VIOLATION";
            case ReasonCode::ENGINE_CONFLICT: return "ENGINE_CONFLICT";
            default:                          return "UNKNOWN";
        }
    }

    inline ReasonCode from_string(const std::string& str) {
        if (str == "SIG_MATCH")       return ReasonCode::SIG_MATCH;
        if (str == "STAT_ANOMALY")    return ReasonCode::STAT_ANOMALY;
        if (str == "PCA_OUTLIER")     return ReasonCode::PCA_OUTLIER;
        if (str == "PROT_VIOLATION")  return ReasonCode::PROT_VIOLATION;
        if (str == "ENGINE_CONFLICT") return ReasonCode::ENGINE_CONFLICT;
        return ReasonCode::UNKNOWN;
    }

} // namespace ml_defender