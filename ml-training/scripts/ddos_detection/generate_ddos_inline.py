# /vagrant/ml-training/scripts/ddos_detection/generate_ddos_inline.py
import joblib
import json
import numpy as np

def generate_ddos_inline_header():
    """Generar header C++ inline para DDoS detection"""
    print("🛡️ GENERANDO HEADER C++ INLINE PARA DDoS...")

    try:
        # Cargar modelo
        model = joblib.load('models/ddos_model.pkl')

        # Extraer estructura del árbol
        # (Implementar lógica similar a extract_full_forest.py)

        # Generar código C++
        header_content = """// AUTO-GENERATED DDoS Detection Trees
// Source: generate_ddos_inline.py  
#ifndef DDOS_TREES_INLINE_HPP
#define DDOS_TREES_INLINE_HPP

#include <array>
#include <cstdint>

struct DDoSNode {
    int16_t feature_idx;
    float threshold;      // NORMALIZADO [0.0-1.0]
    int16_t left_child;
    int16_t right_child;
    std::array<float, 2> value;
};

inline float ddos_predict(const std::array<float, 8>& features) {
    // Implementación de árboles DDoS...
    return 0.0f;
}

#endif // DDOS_TREES_INLINE_HPP
"""

        # Guardar en ml-detector
        with open('/vagrant/ml-detector/src/ddos_trees_inline.hpp', 'w') as f:
            f.write(header_content)

        print("✅ HEADER DDoS GENERADO: /vagrant/ml-detector/src/ddos_trees_inline.hpp")

    except Exception as e:
        print(f"❌ ERROR generando header DDoS: {e}")

if __name__ == "__main__":
    generate_ddos_inline_header()