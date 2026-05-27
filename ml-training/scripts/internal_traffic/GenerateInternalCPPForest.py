# ml-training-scripts/internal_traffic/GenerateInternalCPPForest.py
import json
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Any
from sklearn.preprocessing import MinMaxScaler
import joblib
import numpy as np

def normalize_thresholds(forest_data, scaler):
    """Normaliza todos los thresholds usando el scaler entrenado"""
    print("🔧 Normalizando thresholds a rango [0.0, 1.0]...")

    normalized_forest = {}

    for tree_name, tree_data in forest_data.items():
        normalized_tree = tree_data.copy()
        normalized_thresholds = []

        for feature_idx, threshold in zip(tree_data['feature'], tree_data['threshold']):
            if feature_idx >= 0:  # Solo nodos de decisión (no hojas)
                # Crear array ficticio para la transformación
                dummy_data = np.zeros((1, scaler.n_features_in_))
                dummy_data[0, feature_idx] = threshold

                try:
                    # Transformar a rango normalizado
                    normalized = scaler.transform(dummy_data)
                    normalized_threshold = normalized[0, feature_idx]
                    # Asegurar que esté en [0,1]
                    normalized_threshold = max(0.0, min(1.0, normalized_threshold))
                    normalized_thresholds.append(normalized_threshold)
                except Exception as e:
                    print(f"⚠️  Error normalizando threshold: {e}, usando original")
                    normalized_thresholds.append(threshold)
            else:
                # Para nodos hoja, mantener el valor especial
                normalized_thresholds.append(threshold)

        normalized_tree['threshold'] = normalized_thresholds
        normalized_forest[tree_name] = normalized_tree

    return normalized_forest

def load_internal_model(model_path: str, dataset_path: str):
    """Carga el modelo de tráfico interno, scaler y metadata"""
    print(f"📂 Loading Internal Traffic model from: {model_path}")

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # ✅ CARGAR SCALER
    scaler_path = 'internal_scaler.pkl'
    try:
        scaler = joblib.load(scaler_path)
        print(f"✅ Internal Traffic Scaler loaded: {scaler_path}")
    except FileNotFoundError:
        print(f"❌ Scaler no encontrado: {scaler_path}")
        scaler = None

    with open(dataset_path, 'r') as f:
        dataset_info = json.load(f)

    print(f"✅ Internal Traffic Model loaded: {model.n_estimators} trees, {dataset_info['model_info']['n_features']} features")
    return model, dataset_info, scaler  # ✅ Retornar scaler también

def extract_tree_structure(forest_model, feature_names):
    """Extrae la estructura de todos los árboles del RandomForest"""
    print("🌳 Extracting internal traffic tree structures...")

    complete_forest = {}
    for i, estimator in enumerate(forest_model.estimators_):
        tree = estimator.tree_

        tree_data = {
            'n_nodes': tree.node_count,
            'children_left': tree.children_left.tolist(),
            'children_right': tree.children_right.tolist(),
            'feature': tree.feature.tolist(),
            'threshold': tree.threshold.tolist(),
            'value': tree.value.tolist()  # Probabilidades por clase [external, internal]
        }
        complete_forest[f'tree_{i}'] = tree_data

        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed {i + 1} trees")

    return complete_forest

def generate_internal_cpp_header(forest_data, dataset_info, output_path: str):
    """Genera el header C++20 para el modelo de tráfico interno con predict() COMPLETO"""
    print(f"🔧 Generating C++ header: {output_path}")

    model_info = dataset_info['model_info']
    feature_names = model_info['feature_names']
    n_trees = len(forest_data)

    # Generar definiciones de árboles
    trees_definitions = ""
    tree_pointers = []

    for i in range(n_trees):
        tree_key = f'tree_{i}'
        tree_data = forest_data[tree_key]

        # Generar árbol individual
        trees_definitions += f"""
// Tree {i}: {tree_data['n_nodes']} nodes
inline constexpr InternalNode {tree_key}[] = {{
"""
        # Generar nodos del árbol
        for j in range(tree_data['n_nodes']):
            feature_idx = tree_data['feature'][j]
            threshold = tree_data['threshold'][j]
            left_child = tree_data['children_left'][j]
            right_child = tree_data['children_right'][j]
            value_0 = tree_data['value'][j][0][0]  # P(benign)
            value_1 = tree_data['value'][j][0][1]  # P(suspicious)

            trees_definitions += f"    {{{feature_idx}, {threshold}f, {left_child}, {right_child}, {{{value_0}f, {value_1}f}}}},"

            # Agregar comentario para nodos de decisión
            if feature_idx >= 0:
                trees_definitions += f"  // {feature_names[feature_idx]} <= {threshold:.4f}?"
            else:
                trees_definitions += f"  // Leaf: P(suspicious)={value_1:.4f}"

            trees_definitions += "\n"

        trees_definitions += "};\n\n"
        tree_pointers.append(tree_key)

    # Generar array de punteros a árboles
    tree_pointers_str = ",\n    ".join(tree_pointers)

    header_content = f"""// AUTO-GENERATED Internal Traffic Classification Trees
// Source: GenerateInternalCPPForest.py
// Model: Internal Traffic Classification
// Features: {', '.join(feature_names)}
// Trees: {n_trees}
// Total Nodes: {sum(tree['n_nodes'] for tree in forest_data.values())}

#ifndef INTERNAL_TREES_INLINE_HPP
#define INTERNAL_TREES_INLINE_HPP

#include <array>
#include <cstdint>

struct InternalNode {{
    int16_t feature_idx;     // Feature index for split
    float threshold;         // Split threshold (NORMALIZADO 0.0-1.0)
    int16_t left_child;      // Left child index  
    int16_t right_child;     // Right child index
    std::array<float, 2> value; // Class probabilities [benign, suspicious]
}};

{trees_definitions}
// Array de punteros a todos los árboles
inline constexpr InternalNode* internal_trees[] = {{
    {tree_pointers_str}
}};

inline constexpr size_t INTERNAL_NUM_TREES = {n_trees};
inline constexpr size_t INTERNAL_NUM_FEATURES = {len(feature_names)};

/// @brief Predice si el tráfico es benigno o sospechoso
/// @param features Array de features normalizadas [0.0-1.0]:
///   [0] {feature_names[0]}
///   [1] {feature_names[1]}
///   [2] {feature_names[2]}
///   [3] {feature_names[3]}
///   [4] {feature_names[4]}
///   [5] {feature_names[5]}
///   [6] {feature_names[6]}
///   [7] {feature_names[7]}
///   [8] {feature_names[8]}
///   [9] {feature_names[9]}
/// @return Probability of SUSPICIOUS traffic (0.0 to 1.0)
inline float internal_traffic_predict(const std::array<float, INTERNAL_NUM_FEATURES>& features) {{
    float benign_prob = 0.0f;
    float suspicious_prob = 0.0f;
    
    for (size_t tree_idx = 0; tree_idx < INTERNAL_NUM_TREES; ++tree_idx) {{
        const InternalNode* tree = internal_trees[tree_idx];
        size_t node_idx = 0;
        
        while (true) {{
            const auto& node = tree[node_idx];
            
            if (node.feature_idx == -2) {{ // Leaf node
                benign_prob += node.value[0];
                suspicious_prob += node.value[1];
                break;
            }}
            
            if (features[node.feature_idx] <= node.threshold) {{
                node_idx = node.left_child;
            }} else {{
                node_idx = node.right_child;
            }}
        }}
    }}
    
    // Return probability of SUSPICIOUS traffic (class 1)
    return suspicious_prob / INTERNAL_NUM_TREES;
}}

#endif // INTERNAL_TREES_INLINE_HPP
"""

    with open(output_path, 'w') as f:
        f.write(header_content)

    print(f"✅ Generated COMPLETE Internal Traffic header: {output_path}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python GenerateInternalCPPForest.py <input_pkl> <output_hpp>")
        print("Example: python GenerateInternalCPPForest.py internal_traffic_model.pkl internal_trees_inline.hpp")
        sys.exit(1)

    input_pkl = sys.argv[1]
    output_hpp = sys.argv[2]

    model, dataset_info, scaler = load_internal_model(
        input_pkl,
        "internal_traffic_dataset.json"
    )

    feature_names = dataset_info['model_info']['feature_names']
    forest_data = extract_tree_structure(model, feature_names)

    # ✅ NORMALIZAR THRESHOLDS ANTES DE GENERAR HEADER
    if scaler is not None:
        forest_data = normalize_thresholds(forest_data, scaler)
        print("✅ Todos los thresholds normalizados a [0.0, 1.0]")
    else:
        print("⚠️  No se pudo normalizar thresholds - scaler no disponible")

    generate_internal_cpp_header(forest_data, dataset_info, output_hpp)

if __name__ == "__main__":
    main()