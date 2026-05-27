# extract_model_params_ds.py
import joblib
import numpy as np
import json
import pandas as pd

def extract_model_parameters():
    """Extraer todos los parámetros del modelo para Claude"""
    print("🔍 EXTRAYENDO PARÁMETROS DEL MODELO...")

    # Cargar modelo
    model = joblib.load('models/simple_effective_model.pkl')

    # Información básica del modelo
    model_info = {
        'model_type': str(type(model)),
        'n_estimators': model.n_estimators,
        'n_features': model.n_features_in_,
        'n_classes': model.n_classes_,
        'feature_names': ['io_intensity', 'entropy', 'resource_usage', 'network_activity',
                          'file_operations', 'process_anomaly', 'temporal_pattern',
                          'access_frequency', 'data_volume', 'behavior_consistency'],
        'class_names': model.classes_.tolist()
    }

    # Feature importances
    feature_importance = {
        'io_intensity': float(model.feature_importances_[0]),
        'entropy': float(model.feature_importances_[1]),
        'resource_usage': float(model.feature_importances_[2]),
        'network_activity': float(model.feature_importances_[3]),
        'file_operations': float(model.feature_importances_[4]),
        'process_anomaly': float(model.feature_importances_[5]),
        'temporal_pattern': float(model.feature_importances_[6]),
        'access_frequency': float(model.feature_importances_[7]),
        'data_volume': float(model.feature_importances_[8]),
        'behavior_consistency': float(model.feature_importances_[9])
    }

    # Extraer parámetros de los primeros 3 árboles (para no hacerlo demasiado largo)
    trees_data = {}
    for i, tree in enumerate(model.estimators_[:3]):  # Solo primeros 3 árboles
        tree_params = {
            'n_nodes': tree.tree_.node_count,
            'n_features': tree.tree_.n_features,
            'n_outputs': tree.tree_.n_outputs,
            'max_depth': tree.tree_.max_depth,
            # Estructura del árbol
            'children_left': tree.tree_.children_left.tolist(),
            'children_right': tree.tree_.children_right.tolist(),
            'feature': tree.tree_.feature.tolist(),
            'threshold': tree.tree_.threshold.tolist(),
            'value': tree.tree_.value.tolist()
        }
        trees_data[f'tree_{i}'] = tree_params

    # Información de las primeras 10 hojas del primer árbol (para ejemplo)
    first_tree = model.estimators_[0]
    leaf_info = []
    for i in range(min(10, first_tree.tree_.node_count)):
        if first_tree.tree_.children_left[i] == -1:  # Es hoja
            leaf_info.append({
                'node_id': i,
                'value': float(first_tree.tree_.value[i][0][1]),  # Probabilidad clase 1 (ransomware)
                'samples': int(first_tree.tree_.n_node_samples[i])
            })

    # Compilar toda la información
    all_params = {
        'model_info': model_info,
        'feature_importance': feature_importance,
        'trees_sample': trees_data,
        'leaf_samples': leaf_info,
        'model_parameters': model.get_params()
    }

    # Guardar en JSON
    with open('model_parameters_for_claude.json', 'w') as f:
        json.dump(all_params, f, indent=2, default=convert_numpy)

    print("✅ Parámetros guardados en: model_parameters_for_claude.json")

    # También mostrar resumen en consola
    print("\n" + "="*60)
    print("📊 RESUMEN PARA CLAUDE:")
    print("="*60)
    print(f"🎯 Tipo de modelo: {model_info['model_type']}")
    print(f"🌳 Número de árboles: {model_info['n_estimators']}")
    print(f"📏 Número de features: {model_info['n_features']}")
    print(f"🎯 Clases: {model_info['class_names']}")

    print("\n🔝 FEATURE IMPORTANCE:")
    for feature, importance in feature_importance.items():
        print(f"   {feature:20}: {importance:.4f}")

    print(f"\n🌳 Primer árbol: {trees_data['tree_0']['n_nodes']} nodos")
    print(f"📊 Ejemplo de hojas: {len(leaf_info)} hojas extraídas")

    return all_params

def convert_numpy(obj):
    """Convertir tipos numpy a Python nativo para JSON"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def generate_cpp_ready_params():
    """Generar parámetros listos para implementación en C++"""
    print("\n🔄 GENERANDO PARÁMETROS PARA C++...")

    model = joblib.load('models/simple_effective_model.pkl')

    # Feature thresholds basados en el primer árbol
    first_tree = model.estimators_[0]

    # Encontrar thresholds importantes
    important_thresholds = {}
    for i, feature_idx in enumerate(first_tree.tree_.feature):
        if feature_idx >= 0:  # No es hoja
            feature_name = ['io_intensity', 'entropy', 'resource_usage', 'network_activity',
                            'file_operations', 'process_anomaly', 'temporal_pattern',
                            'access_frequency', 'data_volume', 'behavior_consistency'][feature_idx]
            threshold = first_tree.tree_.threshold[i]

            if feature_name not in important_thresholds:
                important_thresholds[feature_name] = []
            important_thresholds[feature_name].append(float(threshold))

    # Promedio de thresholds por feature
    avg_thresholds = {}
    for feature, thresholds in important_thresholds.items():
        avg_thresholds[feature] = float(np.mean(thresholds))

    cpp_params = {
        'feature_importance': {k: float(v) for k, v in zip(
            ['io_intensity', 'entropy', 'resource_usage', 'network_activity',
             'file_operations', 'process_anomaly', 'temporal_pattern',
             'access_frequency', 'data_volume', 'behavior_consistency'],
            model.feature_importances_
        )},
        'average_thresholds': avg_thresholds,
        'decision_boundary': 0.5,  # Para clasificación binaria
        'n_trees': model.n_estimators,
        'expected_ranges': {
            'io_intensity': [0.0, 2.0],
            'entropy': [0.0, 2.0],
            'resource_usage': [0.0, 2.0],
            'network_activity': [0.0, 2.0],
            'file_operations': [0.0, 2.0],
            'process_anomaly': [0.0, 2.0],
            'temporal_pattern': [0.0, 2.0],
            'access_frequency': [0.0, 2.0],
            'data_volume': [0.0, 2.0],
            'behavior_consistency': [0.0, 1.0]
        }
    }

    with open('cpp_model_params.json', 'w') as f:
        json.dump(cpp_params, f, indent=2)

    print("✅ Parámetros C++ guardados en: cpp_model_params.json")

    return cpp_params

if __name__ == "__main__":
    # Extraer parámetros completos
    all_params = extract_model_parameters()

    # Generar parámetros para C++
    cpp_params = generate_cpp_ready_params()

    print("\n" + "="*60)
    print("🎯 DATOS LISTOS PARA CLAUDE:")
    print("="*60)
    print("📁 Archivos generados:")
    print("   - model_parameters_for_claude.json (parámetros completos)")
    print("   - cpp_model_params.json (parámetros simplificados para C++)")
    print("\n📊 Datos clave:")
    print(f"   - {all_params['model_info']['n_estimators']} árboles Random Forest")
    print(f"   - {all_params['model_info']['n_features']} features de entrada")
    print(f"   - Feature importance: entropy ({all_params['feature_importance']['entropy']:.3f}) es la más importante")
    print(f"   - Clasificación binaria: {all_params['model_info']['class_names']}")