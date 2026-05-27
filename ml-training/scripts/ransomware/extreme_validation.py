# extreme_validation.py
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import f1_score, recall_score, precision_score, classification_report
from sklearn.model_selection import cross_val_score, StratifiedKFold
import json
import os

def load_model_and_data():
    """Cargar modelo y datasets"""
    model_path = 'models/simple_effective_model.pkl'
    model = joblib.load(model_path)
    print(f"✅ Modelo cargado: {model_path}")

    # Cargar datasets
    domains = {
        'network': 'data/network_guaranteed.csv',
        'files': 'data/files_guaranteed.csv',
        'processes': 'data/processes_guaranteed.csv'
    }

    domain_data = {}
    for name, path in domains.items():
        df = pd.read_csv(path)
        X = df.drop('is_ransomware', axis=1)
        y = df['is_ransomware']
        domain_data[name] = {'X': X, 'y': y}
        print(f"✅ {name}: {len(X)} samples, {y.sum()} ransomware")

    return model, domain_data

def extreme_cross_domain_test(model, domain_data):
    """Validación cross-domain con condiciones extremas"""
    print("\n🔥 VALIDACIÓN CROSS-DOMAIN EXTREMA")
    print("=" * 60)

    domains = list(domain_data.keys())
    results = {}

    for test_domain in domains:
        print(f"\n🎯 DOMINIO DE TEST: {test_domain}")

        # Entrenar con otros dominios
        train_domains = [d for d in domains if d != test_domain]
        X_train = pd.concat([domain_data[d]['X'] for d in train_domains])
        y_train = pd.concat([domain_data[d]['y'] for d in train_domains])

        X_test = domain_data[test_domain]['X']
        y_test = domain_data[test_domain]['y']

        # 🔥 TEST 1: Baseline
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        f1_baseline = f1_score(y_test, y_pred)
        recall_baseline = recall_score(y_test, y_pred)

        # 🔥 TEST 2: Con 30% de ruido en features
        X_test_noisy = X_test.copy()
        for col in X_test_noisy.columns:
            noise = np.random.normal(0, 0.3, len(X_test_noisy))
            X_test_noisy[col] = X_test_noisy[col] + noise

        y_pred_noisy = model.predict(X_test_noisy)
        f1_noisy = f1_score(y_test, y_pred_noisy)

        # 🔥 TEST 3: Con missing values (20% NaN)
        X_test_missing = X_test.copy()
        for col in X_test_missing.columns:
            mask = np.random.random(len(X_test_missing)) < 0.2
            X_test_missing.loc[mask, col] = np.nan

        # Imputar con medianas de training
        for col in X_test_missing.columns:
            median_val = X_train[col].median()
            X_test_missing[col].fillna(median_val, inplace=True)

        y_pred_missing = model.predict(X_test_missing)
        f1_missing = f1_score(y_test, y_pred_missing)

        # 🔥 TEST 4: Con desbalance extremo (subsample ransomware)
        ransomware_indices = y_test[y_test == 1].index
        subsample_size = max(1, int(len(ransomware_indices) * 0.3))  # 70% menos ransomware
        subsample_indices = np.random.choice(ransomware_indices, subsample_size, replace=False)

        X_test_imbalanced = X_test.drop(subsample_indices)
        y_test_imbalanced = y_test.drop(subsample_indices)

        y_pred_imbalanced = model.predict(X_test_imbalanced)
        f1_imbalanced = f1_score(y_test_imbalanced, y_pred_imbalanced)

        results[test_domain] = {
            'baseline': {'f1': f1_baseline, 'recall': recall_baseline},
            'noisy_30pct': {'f1': f1_noisy, 'drop': f1_baseline - f1_noisy},
            'missing_20pct': {'f1': f1_missing, 'drop': f1_baseline - f1_missing},
            'imbalanced_70pct_reduction': {'f1': f1_imbalanced, 'drop': f1_baseline - f1_imbalanced}
        }

        print(f"   📊 Baseline: F1={f1_baseline:.4f}, Recall={recall_baseline:.4f}")
        print(f"   🌪️  30% Ruido: F1={f1_noisy:.4f} (Drop: {f1_baseline - f1_noisy:.4f})")
        print(f"   ❓ 20% Missing: F1={f1_missing:.4f} (Drop: {f1_baseline - f1_missing:.4f})")
        print(f"   ⚖️  70% Menos ransomware: F1={f1_imbalanced:.4f} (Drop: {f1_baseline - f1_imbalanced:.4f})")

    return results

def adversarial_robustness_test(model, domain_data):
    """Test de robustez adversarial avanzado"""
    print("\n🔥 TEST DE ROBUSTEZ ADVERSARIAL")
    print("=" * 60)

    # Usar primer dominio para tests adversariales
    test_domain = list(domain_data.keys())[0]
    X_test = domain_data[test_domain]['X']
    y_test = domain_data[test_domain]['y']

    results = {}

    # Ataques basados en feature importance
    feature_importance = pd.DataFrame({
        'feature': X_test.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    top_features = feature_importance.head(3)['feature'].tolist()
    print(f"🎯 Top 3 features atacadas: {top_features}")

    attack_intensities = [0.1, 0.3, 0.5, 0.8]

    for intensity in attack_intensities:
        X_adv = X_test.copy()

        # Ataque: perturbar features más importantes
        for feature in top_features:
            # Ataque dirigido: aumentar valores para ransomware, disminuir para benigno
            for idx in X_adv.index:
                if y_test.loc[idx] == 1:  # Es ransomware real
                    # Hacer que parezca más benigno (evasión)
                    X_adv.loc[idx, feature] *= (1 - intensity)
                else:  # Es benigno real
                    # Hacer que parezca ransomware (false positivo)
                    X_adv.loc[idx, feature] *= (1 + intensity)

        y_pred_adv = model.predict(X_adv)
        f1_adv = f1_score(y_test, y_pred_adv)
        recall_adv = recall_score(y_test, y_pred_adv)

        # Baseline para comparación
        y_pred_base = model.predict(X_test)
        f1_base = f1_score(y_test, y_pred_base)

        results[f'adversarial_{intensity}'] = {
            'f1': f1_adv,
            'recall': recall_adv,
            'f1_drop': f1_base - f1_adv,
            'recall_drop': recall_score(y_test, y_pred_base) - recall_adv
        }

        print(f"   💀 Ataque {intensity}: F1={f1_adv:.4f} (Drop: {f1_base - f1_adv:.4f}), Recall={recall_adv:.4f}")

    return results

def concept_drift_simulation(model, domain_data):
    """Simulación de concept drift"""
    print("\n🔥 SIMULACIÓN DE CONCEPT DRIFT")
    print("=" * 60)

    # Crear datos con distribución diferente
    original_domain = list(domain_data.keys())[0]
    X_original = domain_data[original_domain]['X']
    y_original = domain_data[original_domain]['y']

    # Simular drift: cambiar distribución de features
    X_drift = X_original.copy()
    for col in X_drift.columns:
        if 'intensity' in col or 'usage' in col:
            # Drift: valores más altos en general
            X_drift[col] = X_drift[col] * 1.5 + np.random.normal(0, 0.2, len(X_drift))
        elif 'entropy' in col:
            # Drift: distribución más uniforme
            X_drift[col] = np.random.uniform(0.5, 1.5, len(X_drift))

    y_pred_drift = model.predict(X_drift)
    f1_drift = f1_score(y_original, y_pred_drift)

    # Baseline
    y_pred_original = model.predict(X_original)
    f1_original = f1_score(y_original, y_pred_original)

    print(f"   📊 Original: F1={f1_original:.4f}")
    print(f"   🌀 Con Drift: F1={f1_drift:.4f} (Drop: {f1_original - f1_drift:.4f})")

    return {
        'original_f1': f1_original,
        'drift_f1': f1_drift,
        'f1_drop': f1_original - f1_drift
    }

def run_complete_validation():
    """Ejecutar validación completa y agresiva"""
    print("🎯 INICIANDO VALIDACIÓN AGRESIVA COMPLETA")
    print("=" * 60)

    model, domain_data = load_model_and_data()

    results = {
        'cross_domain_extreme': extreme_cross_domain_test(model, domain_data),
        'adversarial_robustness': adversarial_robustness_test(model, domain_data),
        'concept_drift': concept_drift_simulation(model, domain_data)
    }

    # 🔥 CALCULAR PUNTAJE FINAL DE ROBUSTEZ
    print("\n" + "=" * 60)
    print("📊 PUNTAJE FINAL DE ROBUSTEZ")
    print("=" * 60)

    # Métrica compuesta de robustez
    f1_drops = []

    # Cross-domain drops
    for domain_result in results['cross_domain_extreme'].values():
        f1_drops.extend([
            domain_result['noisy_30pct']['drop'],
            domain_result['missing_20pct']['drop'],
            domain_result['imbalanced_70pct_reduction']['drop']
        ])

    # Adversarial drops
    for adv_result in results['adversarial_robustness'].values():
        f1_drops.append(adv_result['f1_drop'])

    # Concept drift drop
    f1_drops.append(results['concept_drift']['f1_drop'])

    avg_f1_drop = np.mean(f1_drops)
    robustness_score = max(0, 1 - avg_f1_drop)  # 1 = perfecta robustez

    results['final_robustness_score'] = robustness_score
    results['average_f1_drop'] = avg_f1_drop

    print(f"🎯 PUNTAJE DE ROBUSTEZ: {robustness_score:.4f}")
    print(f"📉 CAÍDA PROMEDIO DE F1: {avg_f1_drop:.4f}")

    if robustness_score >= 0.8:
        print("✅✅✅ EXCELENTE - Modelo muy robusto")
    elif robustness_score >= 0.6:
        print("✅✅ BUENO - Modelo aceptablemente robusto")
    elif robustness_score >= 0.4:
        print("✅ REGULAR - Modelo necesita mejoras")
    else:
        print("❌❌❌ PÉSIMO - Modelo no es robusto")

    # Guardar resultados detallados
    os.makedirs('results', exist_ok=True)
    with open('results/aggressive_validation.json', 'w') as f:
        json.dump(results, f, indent=2, default=float)

    print(f"\n💾 Resultados guardados en: results/aggressive_validation.json")

    return results, robustness_score

if __name__ == "__main__":
    results, robustness_score = run_complete_validation()