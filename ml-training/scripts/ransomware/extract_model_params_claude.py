#!/usr/bin/env python3
"""
Extrae TODOS los árboles del RandomForest para C++20
"""

import pickle
import json

def extract_all_trees(model_path: str, output_path: str):
    """Extrae estructura completa de los 100 árboles"""

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    rf = model
    print(f"🌳 Extrayendo {rf.n_estimators} árboles...")

    # Extraer TODOS los árboles
    all_trees = []
    for i, estimator in enumerate(rf.estimators_):
        tree = estimator.tree_

        tree_data = {
            "tree_id": i,
            "n_nodes": int(tree.node_count),
            "max_depth": int(tree.max_depth),
            "children_left": tree.children_left.tolist(),
            "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(),
            "threshold": tree.threshold.tolist(),
            "value": tree.value.tolist()
        }
        all_trees.append(tree_data)

        if (i + 1) % 20 == 0:
            print(f"  ✓ Procesados {i+1} árboles...")

    output = {
        "n_trees": rf.n_estimators,
        "n_features": rf.n_features_in_,
        "feature_names": [
            "io_intensity", "entropy", "resource_usage",
            "network_activity", "file_operations", "process_anomaly",
            "temporal_pattern", "access_frequency", "data_volume",
            "behavior_consistency"
        ],
        "trees": all_trees
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    total_nodes = sum(t['n_nodes'] for t in all_trees)
    print(f"\n✅ COMPLETO:")
    print(f"   Árboles: {len(all_trees)}")
    print(f"   Nodos totales: {total_nodes:,}")
    print(f"   Promedio: {total_nodes/len(all_trees):.1f} nodos/árbol")
    print(f"   Archivo: {output_path}")

if __name__ == "__main__":
    extract_all_trees(
        "models/simple_effective_model.pkl",
        "forest_complete_100_trees.json"
    )