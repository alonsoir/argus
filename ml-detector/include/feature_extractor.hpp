#pragma once

#include <vector>
#include <memory>
#include <spdlog/spdlog.h>
#include "network_security.pb.h"

namespace ml_detector {

/**
 * @brief Feature Extractor para Level 1 (23 features)
 * 
 * Extrae features de NetworkSecurityEvent según metadata del modelo:
 * level1_attack_detector_metadata.json
 * 
 * NOTA: Este extractor evolucionará:
 * - Level 1: 23 features (attack vs benign)
 * - Level 2: 82 features (ddos/ransomware specialized)
 * - Level 3: 4 features (internal/web anomalies)
 */
class FeatureExtractor {
public:
    explicit FeatureExtractor();
    
    /**
     * @brief Extrae las 23 features del Level 1
     * @param event NetworkSecurityEvent del sniffer
     * @return vector<float>[23] listo para inference
     * @throws std::runtime_error si faltan campos críticos
     */
    std::vector<float> extract_level1_features(const protobuf::NetworkSecurityEvent& event);

    /**
     * @brief Extrae las 10 features del Level 2 DDoS Binary
     * @param nf NetworkFeatures del evento
     * @return vector<float>[10] para predicción DDoS binaria (accuracy 98.61%)
     */
    std::vector<float> extract_level2_ddos_features(const protobuf::NetworkFeatures& nf);
    /**
    * External Traffic classification (10 features)
    * @param nf NetworkFeatures del evento
    * @return vector<float>[10] para predicción External Traffic binaria
    */
    std::vector<float> extract_level3_traffic_features(const protobuf::NetworkFeatures& nf);
    /**
    * Internal traffic analysis (10 features)
    * @param nf NetworkFeatures del evento
    * @return vector<float>[10] para predicción Internal Traffic binaria
    */
    std::vector<float> extract_level3_internal_features(const protobuf::NetworkFeatures& nf);
    /**
     * @brief Valida que features sean válidas (no NaN, no Inf, rangos razonables)
     * @param features Vector de features a validar
     * @return true si válido, false si inválido
     */
    bool validate_features(const std::vector<float>& features);
    
    /**
     * @brief Obtiene nombres de las 23 features (para logging)
     */
    static const std::vector<std::string>& get_feature_names();

    /**
     * @brief Extrae las 10 features del Level 2 Ransomware Detector (Embedded C++20)
     * @param nf NetworkFeatures del evento
     * @return vector<float>[10] para detector embebido
     *
     * Features extraídas (según feature importance):
     * [0] io_intensity, [1] entropy (36% importance), [2] resource_usage (25%),
     * [3] network_activity, [4] file_operations, [5] process_anomaly,
     * [6] temporal_pattern, [7] access_frequency, [8] data_volume,
     * [9] behavior_consistency
     */
    std::vector<float> extract_level2_ransomware_features(const protobuf::NetworkFeatures& nf);
    
private:
    std::shared_ptr<spdlog::logger> logger_;
    
    // Helpers para calcular features derivadas
    float safe_divide(float numerator, float denominator, float default_value = 0.0f);
    
    // Stats helpers
    float calculate_std_dev(const std::vector<float>& values, float mean);
    float calculate_variance(const std::vector<float>& values, float mean);
    // Helper methods
    float normalize(float value, float min, float max) const;
    float safe_divide(float numerator, float denominator) const;
};

} // namespace ml_detector
