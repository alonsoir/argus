# extract_full_forest.py
import joblib
import numpy as np
import json

def extract_complete_forest():
    """Extraer la estructura completa de los 100 árboles"""
    print("🌳 EXTRAYENDO BOSQUE COMPLETO (100 ÁRBOLES)...")

    # Cargar modelo
    model = joblib.load('models/simple_effective_model.pkl')

    # Verificar que tenemos 100 árboles
    n_trees = len(model.estimators_)
    print(f"📊 Modelo tiene {n_trees} árboles")

    # Extraer TODOS los árboles
    complete_forest = {}

    for tree_idx, tree in enumerate(model.estimators_):
        tree_data = {
            'n_nodes': int(tree.tree_.node_count),
            'children_left': tree.tree_.children_left.astype(int).tolist(),
            'children_right': tree.tree_.children_right.astype(int).tolist(),
            'feature': tree.tree_.feature.astype(int).tolist(),
            'threshold': tree.tree_.threshold.astype(float).tolist(),
            'value': tree.tree_.value.astype(float).tolist(),
            'n_node_samples': tree.tree_.n_node_samples.astype(int).tolist()
        }
        complete_forest[f'tree_{tree_idx}'] = tree_data

        if tree_idx % 10 == 0:  # Progress
            print(f"   ✅ Árbol {tree_idx}/{n_trees} extraído")

    # Información del modelo
    model_info = {
        'n_trees': n_trees,
        'n_features': int(model.n_features_in_),
        'n_classes': int(model.n_classes_),
        'feature_names': ['io_intensity', 'entropy', 'resource_usage', 'network_activity',
                          'file_operations', 'process_anomaly', 'temporal_pattern',
                          'access_frequency', 'data_volume', 'behavior_consistency'],
        'class_names': model.classes_.astype(int).tolist(),
        'feature_importances': model.feature_importances_.astype(float).tolist()
    }

    # Compilar datos completos
    full_data = {
        'model_info': model_info,
        'complete_forest': complete_forest
    }

    # Guardar JSON completo
    output_file = 'complete_forest_100_trees.json'
    with open(output_file, 'w') as f:
        json.dump(full_data, f, indent=2)

    print(f"✅ Bosque completo guardado en: {output_file}")

    # Estadísticas
    total_nodes = sum([data['n_nodes'] for data in complete_forest.values()])
    avg_nodes = total_nodes / n_trees

    print(f"\n📊 ESTADÍSTICAS DEL BOSQUE:")
    print(f"   🌳 Total de árboles: {n_trees}")
    print(f"   📍 Total de nodos: {total_nodes}")
    print(f"   📍 Promedio nodos por árbol: {avg_nodes:.1f}")
    print(f"   💾 Tamaño del archivo: {total_nodes * 4} bytes aprox. en C++")

    return full_data

def generate_cpp_implementation():
    """Generar implementación C++ con los 100 árboles"""
    print("\n🔄 GENERANDO IMPLEMENTACIÓN C++...")

    # Cargar datos completos
    with open('complete_forest_100_trees.json', 'r') as f:
        forest_data = json.load(f)

    # Generar código C++ para el primer árbol como ejemplo
    first_tree = forest_data['complete_forest']['tree_0']
    feature_names = forest_data['model_info']['feature_names']

    cpp_code = f'''
// ransomware_forest.h
#pragma once
#include <vector>
#include <array>

class RandomForestRansomwareDetector {{
public:
    double predict(const std::vector<double>& features) const;
    
private:
    // Feature names for reference
    static constexpr const char* FEATURE_NAMES[10] = {{
        "io_intensity", "entropy", "resource_usage", "network_activity",
        "file_operations", "process_anomaly", "temporal_pattern", 
        "access_frequency", "data_volume", "behavior_consistency"
    }};
    
    // Feature importances
    static constexpr double FEATURE_IMPORTANCE[10] = {{
        {forest_data['model_info']['feature_importances'][0]:.6f},  // io_intensity
        {forest_data['model_info']['feature_importances'][1]:.6f},  // entropy
        {forest_data['model_info']['feature_importances'][2]:.6f},  // resource_usage
        {forest_data['model_info']['feature_importances'][3]:.6f},  // network_activity
        {forest_data['model_info']['feature_importances'][4]:.6f},  // file_operations
        {forest_data['model_info']['feature_importances'][5]:.6f},  // process_anomaly
        {forest_data['model_info']['feature_importances'][6]:.6f},  // temporal_pattern
        {forest_data['model_info']['feature_importances'][7]:.6f},  // access_frequency
        {forest_data['model_info']['feature_importances'][8]:.6f},  // data_volume
        {forest_data['model_info']['feature_importances'][9]:.6f}   // behavior_consistency
    }};
    
    // Tree prediction functions
    double predict_tree_0(const std::vector<double>& features) const;
    // ... (se generarían las 99 funciones restantes)
}};

// Ejemplo de implementación del primer árbol
double RandomForestRansomwareDetector::predict_tree_0(const std::vector<double>& features) const {{
    /* 
    Árbol 0 - {first_tree['n_nodes']} nodos
    Estructura completa disponible en complete_forest_100_trees.json
    */
    
    // Implementación simplificada del primer nivel
    if (features[{first_tree['feature'][0]}] <= {first_tree['threshold'][0]:.6f}) {{
        // Ir al nodo {first_tree['children_left'][0]}
        if (features[{first_tree['feature'][first_tree['children_left'][0]]}] <= {first_tree['threshold'][first_tree['children_left'][0]]:.6f}) {{
            return {first_tree['value'][first_tree['children_left'][first_tree['children_left'][0]]][0][1]:.6f}; // Probabilidad ransomware
        }} else {{
            return {first_tree['value'][first_tree['children_right'][first_tree['children_left'][0]]][0][1]:.6f};
        }}
    }} else {{
        // Ir al nodo {first_tree['children_right'][0]}
        if (features[{first_tree['feature'][first_tree['children_right'][0]]}] <= {first_tree['threshold'][first_tree['children_right'][0]]:.6f}) {{
            return {first_tree['value'][first_tree['children_left'][first_tree['children_right'][0]]][0][1]:.6f};
        }} else {{
            return {first_tree['value'][first_tree['children_right'][first_tree['children_right'][0]]][0][1]:.6f};
        }}
    }}
}}
'''

    with open('complete_forest_cpp_example.h', 'w') as f:
        f.write(cpp_code)

    print("✅ Ejemplo C++ generado en: complete_forest_cpp_example.h")

    return cpp_code

def generate_tree_statistics():
    """Generar estadísticas detalladas de los árboles"""
    print("\n📈 GENERANDO ESTADÍSTICAS DETALLADAS...")

    with open('complete_forest_100_trees.json', 'r') as f:
        forest_data = json.load(f)

    stats = {
        'total_trees': forest_data['model_info']['n_trees'],
        'feature_names': forest_data['model_info']['feature_names'],
        'feature_importances': forest_data['model_info']['feature_importances'],
        'tree_statistics': {}
    }

    # Estadísticas por árbol
    for tree_name, tree_data in forest_data['complete_forest'].items():
        tree_idx = int(tree_name.split('_')[1])
        stats['tree_statistics'][tree_name] = {
            'n_nodes': tree_data['n_nodes'],
            'max_depth': calculate_tree_depth(tree_data),
            'n_leaves': count_leaves(tree_data),
            'most_used_feature': get_most_used_feature(tree_data, forest_data['model_info']['feature_names'])
        }

    # Estadísticas generales
    all_nodes = [s['n_nodes'] for s in stats['tree_statistics'].values()]
    all_depths = [s['max_depth'] for s in stats['tree_statistics'].values()]

    stats['general_statistics'] = {
        'total_nodes': sum(all_nodes),
        'avg_nodes_per_tree': sum(all_nodes) / len(all_nodes),
        'max_nodes': max(all_nodes),
        'min_nodes': min(all_nodes),
        'avg_depth': sum(all_depths) / len(all_depths),
        'max_depth': max(all_depths)
    }

    with open('forest_statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print("✅ Estadísticas guardadas en: forest_statistics.json")

    # Mostrar resumen
    print(f"\n📊 RESUMEN ESTADÍSTICAS:")
    print(f"   🌳 Total árboles: {stats['general_statistics']['total_nodes']} nodos")
    print(f"   📍 Promedio: {stats['general_statistics']['avg_nodes_per_tree']:.1f} nodos/árbol")
    print(f"   📏 Profundidad máxima: {stats['general_statistics']['max_depth']} niveles")
    print(f"   🎯 Feature más importante: {stats['feature_names'][np.argmax(stats['feature_importances'])]}")

    return stats

def calculate_tree_depth(tree_data, node=0, depth=0):
    """Calcular profundidad de un árbol recursivamente"""
    if tree_data['children_left'][node] == -1:  # Es hoja
        return depth

    left_depth = calculate_tree_depth(tree_data, tree_data['children_left'][node], depth + 1)
    right_depth = calculate_tree_depth(tree_data, tree_data['children_right'][node], depth + 1)

    return max(left_depth, right_depth)

def count_leaves(tree_data):
    """Contar número de hojas en un árbol"""
    leaves = 0
    for i in range(tree_data['n_nodes']):
        if tree_data['children_left'][i] == -1:  # Es hoja
            leaves += 1
    return leaves

def get_most_used_feature(tree_data, feature_names):
    """Obtener la feature más usada en un árbol"""
    feature_counts = {}
    for feature_idx in tree_data['feature']:
        if feature_idx >= 0:  # No es hoja
            feature_name = feature_names[feature_idx]
            feature_counts[feature_name] = feature_counts.get(feature_name, 0) + 1

    if feature_counts:
        return max(feature_counts.items(), key=lambda x: x[1])
    return ("none", 0)

if __name__ == "__main__":
    # 1. Extraer bosque completo
    forest_data = extract_complete_forest()

    # 2. Generar estadísticas
    stats = generate_tree_statistics()

    # 3. Generar ejemplo C++
    cpp_example = generate_cpp_implementation()

    print("\n" + "="*60)
    print("🎯 DATOS COMPLETOS LISTOS PARA CLAUDE:")
    print("="*60)
    print("📁 Archivos generados:")
    print("   - complete_forest_100_trees.json (100 ÁRBOLES COMPLETOS)")
    print("   - forest_statistics.json (estadísticas detalladas)")
    print("   - complete_forest_cpp_example.h (ejemplo implementación C++)")
    print("\n📊 Lo que contiene complete_forest_100_trees.json:")
    print("   ✅ 100 árboles Random Forest completos")
    print("   ✅ children_left[] - hijos izquierdos de cada nodo")
    print("   ✅ children_right[] - hijos derechos de cada nodo")
    print("   ✅ feature[] - índice de feature a evaluar")
    print("   ✅ threshold[] - valor de comparación")
    print("   ✅ value[] - predicción en hojas")
    print("   ✅ n_node_samples[] - muestras en cada nodo")
    print(f"\n🌳 Total: {stats['general_statistics']['total_nodes']} nodos para implementar")