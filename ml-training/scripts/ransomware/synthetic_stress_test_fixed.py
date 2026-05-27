# synthetic_stress_test_fixed.py
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.metrics import f1_score, recall_score, precision_score

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def create_stress_test_datasets():
    """Crear datasets sintéticos extremos para stress testing"""
    print("🎯 CREANDO DATASETS DE STRESS TEST")

    # Features del modelo
    features = ['io_intensity', 'entropy', 'resource_usage', 'network_activity',
                'file_operations', 'process_anomaly', 'temporal_pattern',
                'access_frequency', 'data_volume', 'behavior_consistency']

    stress_cases = {
        'high_overlap': "Ransomware y benigno muy similares",
        'extreme_imbalance': "1% ransomware",
        'feature_collinearity': "Features altamente correlacionadas",
        'outlier_contamination': "20% outliers extremos",
        'adversarial_patterns': "Patrones diseñados para engañar"
    }

    datasets = {}

    for case_name, description in stress_cases.items():
        print(f"\n🔨 Creando: {case_name} - {description}")

        if case_name == 'high_overlap':
            # Ransomware y benigno casi indistinguibles
            n_samples = 1000
            data = {}
            for feature in features:
                # Misma distribución para ambas clases
                data[feature] = np.random.normal(1.0, 0.3, n_samples)

            df = pd.DataFrame(data)
            # Labels casi aleatorios
            labels = np.random.binomial(1, 0.5, n_samples)
            df['is_ransomware'] = labels

        elif case_name == 'extreme_imbalance':
            # Solo 1% ransomware
            n_samples = 1000
            n_ransomware = int(n_samples * 0.01)
            data = {}
            for feature in features:
                # Distribución normal para benigno
                benign_vals = np.random.normal(0.5, 0.2, n_samples - n_ransomware)
                # Valores más altos para ransomware
                ransom_vals = np.random.normal(1.5, 0.3, n_ransomware)
                data[feature] = np.concatenate([benign_vals, ransom_vals])

            df = pd.DataFrame(data)
            labels = np.concatenate([np.zeros(n_samples - n_ransomware), np.ones(n_ransomware)])
            df['is_ransomware'] = labels
            df = df.sample(frac=1).reset_index(drop=True)  # Mezclar

        elif case_name == 'feature_collinearity':
            # Features altamente correlacionadas
            n_samples = 1000
            base_feature = np.random.normal(1.0, 0.5, n_samples)
            data = {}
            for i, feature in enumerate(features):
                # Alta correlación entre features
                data[feature] = base_feature + np.random.normal(0, 0.1 * (i+1), n_samples)

            df = pd.DataFrame(data)
            # Labels basados en combinación lineal
            linear_combination = sum([df[feature] * (i+1) for i, feature in enumerate(features)])
            labels = (linear_combination > linear_combination.median()).astype(int)
            df['is_ransomware'] = labels

        elif case_name == 'outlier_contamination':
            # 20% de outliers extremos
            n_samples = 1000
            n_outliers = int(n_samples * 0.2)
            data = {}
            for feature in features:
                # Valores normales
                normal_vals = np.random.normal(1.0, 0.3, n_samples - n_outliers)
                # Outliers extremos
                outlier_vals = np.random.uniform(5.0, 10.0, n_outliers)
                data[feature] = np.concatenate([normal_vals, outlier_vals])

            df = pd.DataFrame(data)
            # Labels realistas pero con outliers mezclados
            base_labels = np.random.binomial(1, 0.3, n_samples)
            df['is_ransomware'] = base_labels
            df = df.sample(frac=1).reset_index(drop=True)

        elif case_name == 'adversarial_patterns':
            # Patrones diseñados específicamente para engañar
            n_samples = 1000
            data = {}

            # Crear patrones adversariales
            for feature in features:
                if 'entropy' in feature or 'intensity' in feature:
                    # Para ransomware real: valores moderados
                    # Para adversarial: valores que cruzan umbrales de decisión
                    ransom_vals = np.random.normal(1.2, 0.2, n_samples//2)
                    adv_vals = np.random.normal(0.8, 0.1, n_samples//2)  # Justo debajo del umbral
                    data[feature] = np.concatenate([ransom_vals, adv_vals])
                else:
                    data[feature] = np.random.normal(1.0, 0.3, n_samples)

            df = pd.DataFrame(data)
            labels = np.concatenate([np.ones(n_samples//2), np.zeros(n_samples//2)])
            df['is_ransomware'] = labels
            df = df.sample(frac=1).reset_index(drop=True)

        datasets[case_name] = df
        print(f"   ✅ {len(df)} samples, {df['is_ransomware'].sum()} ransomware")

    return datasets

def run_stress_tests():
    """Ejecutar stress tests con datasets extremos"""
    print("\n🎯 EJECUTANDO STRESS TESTS")
    print("=" * 60)

    model = joblib.load('models/simple_effective_model.pkl')
    stress_datasets = create_stress_test_datasets()

    results = {}

    for case_name, df in stress_datasets.items():
        print(f"\n🔍 TESTEANDO: {case_name}")
        X = df.drop('is_ransomware', axis=1)
        y = df['is_ransomware']

        y_pred = model.predict(X)
        f1 = f1_score(y, y_pred)
        recall = recall_score(y, y_pred)
        precision = precision_score(y, y_pred)

        results[case_name] = {
            'f1': float(f1),
            'recall': float(recall),
            'precision': float(precision),
            'samples': int(len(df)),
            'ransomware_count': int(y.sum())
        }

        print(f"   📊 F1: {f1:.4f}, Recall: {recall:.4f}, Precision: {precision:.4f}")

        if f1 < 0.5:
            print("   ⚠️  ALERTA: Performance pobre en caso extremo")

    # Guardar resultados
    with open('results/stress_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)

    print(f"\n💾 Resultados de stress test guardados")
    return results

if __name__ == "__main__":
    run_stress_tests()