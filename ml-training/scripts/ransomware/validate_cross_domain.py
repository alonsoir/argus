# validate_cross_domain.py (VERSIÓN SIMPLIFICADA Y ROBUSTA)
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, classification_report
import joblib
import json
import os

def load_all_domains():
    """Cargar datos de los 3 dominios con features consistentes"""
    domains = {
        'network': 'data/ugransome_processed.csv',
        'files': 'data/ransomware_2024_processed.csv',
        'processes': 'data/process_data_processed.csv'
    }

    domain_data = {}
    for name, path in domains.items():
        try:
            df = pd.read_csv(path)
            # Seleccionar solo features numéricas y el target
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            feature_cols = [col for col in numeric_cols if col != 'is_ransomware']

            # Asegurar que tenemos features y target
            if len(feature_cols) == 0:
                print(f"❌ No hay features numéricas en {name}")
                continue

            if 'is_ransomware' not in df.columns:
                print(f"❌ No hay columna target en {name}")
                continue

            domain_data[name] = {
                'features': df[feature_cols],
                'target': df['is_ransomware']
            }
            print(f"✅ {name}: {len(df)} samples, {df['is_ransomware'].sum()} ransomware, {len(feature_cols)} features")

        except Exception as e:
            print(f"❌ Error cargando {name}: {e}")
            return None

    return domain_data

def align_features(X_train, X_test):
    """Alinear features entre train y test para que tengan las mismas columnas"""
    common_features = set(X_train.columns) & set(X_test.columns)

    if len(common_features) == 0:
        print("❌ No hay features comunes entre train y test")
        return None, None

    print(f"🔧 Alineando features: {len(common_features)} comunes")

    X_train_aligned = X_train[list(common_features)]
    X_test_aligned = X_test[list(common_features)]

    return X_train_aligned, X_test_aligned

def cross_domain_validation():
    """Validación cruzada entre los 3 dominios"""
    print("🚀 INICIANDO VALIDACIÓN CRUZADA ENTRE DOMINIOS")

    # Crear directorios necesarios
    os.makedirs('results', exist_ok=True)

    domain_data = load_all_domains()
    if domain_data is None or len(domain_data) < 2:
        print("❌ No hay suficientes dominios para validación cruzada")
        return None, 0

    domains = list(domain_data.keys())
    results = {}

    for test_domain in domains:
        print(f"\n🔍 TESTEANDO EN DOMINIO: {test_domain}")

        # Dominios de entrenamiento (todos excepto test)
        train_domains = [d for d in domains if d != test_domain]

        # Combinar datos de entrenamiento
        X_train_list = []
        y_train_list = []

        for train_domain in train_domains:
            X_train_list.append(domain_data[train_domain]['features'])
            y_train_list.append(domain_data[train_domain]['target'])

        X_train = pd.concat(X_train_list, ignore_index=True)
        y_train = pd.concat(y_train_list, ignore_index=True)

        # Datos de test
        X_test = domain_data[test_domain]['features']
        y_test = domain_data[test_domain]['target']

        # Alinear features entre train y test
        X_train_aligned, X_test_aligned = align_features(X_train, X_test)

        if X_train_aligned is None:
            continue

        print(f"📊 Train: {X_train_aligned.shape}, Test: {X_test_aligned.shape}")
        print(f"🎯 Balance - Train: {y_train.mean():.3f}, Test: {y_test.mean():.3f}")

        # Entrenar modelo
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_aligned, y_train)

        # Predecir y evaluar
        y_pred = model.predict(X_test_aligned)
        f1 = f1_score(y_test, y_pred)

        results[test_domain] = {
            'f1_score': f1,
            'train_samples': len(X_train_aligned),
            'test_samples': len(X_test_aligned),
            'train_domains': train_domains,
            'feature_count': X_train_aligned.shape[1]
        }

        print(f"🎯 F1 Score en {test_domain}: {f1:.4f}")

    # Calcular promedio si hay resultados
    if results:
        avg_f1 = np.mean([results[d]['f1_score'] for d in results.keys()])
        print(f"\n📈 F1 PROMEDIO CROSS-DOMAIN: {avg_f1:.4f}")

        # Guardar resultados
        results['average_f1'] = avg_f1
        with open('results/cross_domain_validation.json', 'w') as f:
            json.dump(results, f, indent=2)

        return results, avg_f1
    else:
        print("❌ No se pudieron calcular resultados")
        return None, 0

if __name__ == "__main__":
    results, avg_f1 = cross_domain_validation()