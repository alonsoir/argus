
// ransomware_forest.h
#pragma once
#include <vector>
#include <array>

class RandomForestRansomwareDetector {
public:
    double predict(const std::vector<double>& features) const;
    
private:
    // Feature names for reference
    static constexpr const char* FEATURE_NAMES[10] = {
        "io_intensity", "entropy", "resource_usage", "network_activity",
        "file_operations", "process_anomaly", "temporal_pattern", 
        "access_frequency", "data_volume", "behavior_consistency"
    };
    
    // Feature importances
    static constexpr double FEATURE_IMPORTANCE[10] = {
        0.243322,  // io_intensity
        0.360733,  // entropy
        0.248849,  // resource_usage
        0.076472,  // network_activity
        0.024454,  // file_operations
        0.003335,  // process_anomaly
        0.004905,  // temporal_pattern
        0.016204,  // access_frequency
        0.006181,  // data_volume
        0.015543   // behavior_consistency
    };
    
    // Tree prediction functions
    double predict_tree_0(const std::vector<double>& features) const;
    // ... (se generarían las 99 funciones restantes)
};

// Ejemplo de implementación del primer árbol
double RandomForestRansomwareDetector::predict_tree_0(const std::vector<double>& features) const {
    /* 
    Árbol 0 - 29 nodos
    Estructura completa disponible en complete_forest_100_trees.json
    */
    
    // Implementación simplificada del primer nivel
    if (features[1] <= 0.381458) {
        // Ir al nodo 1
        if (features[1] <= 0.327371) {
            return 0.011319; // Probabilidad ransomware
        } else {
            return 0.495001;
        }
    } else {
        // Ir al nodo 18
        if (features[2] <= 0.096105) {
            return 0.000000;
        } else {
            return 0.995136;
        }
    }
}
