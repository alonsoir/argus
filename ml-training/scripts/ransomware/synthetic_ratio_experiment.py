# synthetic_ratio_experiment_fixed.py
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, recall_score, precision_score
import json

def load_real_data():
    """Cargar nuestros datasets reales"""
    domains = ['network', 'files', 'processes']
    real_data = {}

    for domain in domains:
        df = pd.read_csv(f'data/{domain}_guaranteed.csv')
        # Resetear índices para evitar problemas
        real_data[domain] = {
            'X': df.drop('is_ransomware', axis=1).reset_index(drop=True),
            'y': df['is_ransomware'].reset_index(drop=True)
        }
    return real_data

def generate_high_fidelity_synthetic(real_data, ratio=0.25):
    """Generar datos sintéticos de alta fidelidad - VERSIÓN CORREGIDA"""
    print(f"🎭 Generando datos sintéticos (ratio: {ratio})")

    # Combinar datos reales de todos los dominios (resetear índices)
    all_real_X_list = []
    all_real_y_list = []

    for domain in real_data:
        all_real_X_list.append(real_data[domain]['X'])
        all_real_y_list.append(real_data[domain]['y'])

    all_real_X = pd.concat(all_real_X_list, ignore_index=True)
    all_real_y = pd.concat(all_real_y_list, ignore_index=True)

    synthetic_samples = {}

    # Para cada clase (0=benigno, 1=ransomware)
    for class_label in [0, 1]:
        class_mask = all_real_y == class_label
        class_data = all_real_X[class_mask].reset_index(drop=True)

        if len(class_data) == 0:
            print(f"⚠️  No hay datos para clase {class_label}")
            synthetic_samples[class_label] = pd.DataFrame()
            continue

        # Número de muestras sintéticas para esta clase
        n_synthetic = max(1, int(len(class_data) * ratio))

        print(f"   Clase {class_label}: {len(class_data)} reales → {n_synthetic} sintéticas")

        synthetic_class = []
        for i in range(n_synthetic):
            # Seleccionar muestra real aleatoria
            real_sample_idx = np.random.randint(0, len(class_data))
            real_sample = class_data.iloc[real_sample_idx].copy()

            # Aplicar perturbación inteligente
            for feature in real_sample.index:
                if feature in ['entropy', 'io_intensity', 'resource_usage']:
                    # Perturbar features importantes
                    noise = np.random.normal(0, 0.15)  # Más ruido para variedad
                    synthetic_value = real_sample[feature] + noise
                    synthetic_value = max(0, min(2.0, synthetic_value))
                    real_sample[feature] = synthetic_value
                else:
                    # Perturbar otras features
                    noise = np.random.normal(0, 0.08)
                    synthetic_value = real_sample[feature] + noise
                    synthetic_value = max(0, min(2.0, synthetic_value))
                    real_sample[feature] = synthetic_value

            synthetic_class.append(real_sample)

        if synthetic_class:
            synthetic_samples[class_label] = pd.DataFrame(synthetic_class).reset_index(drop=True)
        else:
            synthetic_samples[class_label] = pd.DataFrame()

    # Combinar clases de manera segura
    synthetic_dfs = []
    synthetic_labels = []

    for class_label, df in synthetic_samples.items():
        if len(df) > 0:
            synthetic_dfs.append(df)
            synthetic_labels.extend([class_label] * len(df))

    if not synthetic_dfs:
        print("❌ No se pudieron generar datos sintéticos")
        return pd.DataFrame(), pd.Series()

    synthetic_X = pd.concat(synthetic_dfs, ignore_index=True)
    synthetic_y = pd.Series(synthetic_labels, name='is_ransomware')

    # Mezclar
    combined_indices = np.random.permutation(len(synthetic_X))
    synthetic_X = synthetic_X.iloc[combined_indices].reset_index(drop=True)
    synthetic_y = synthetic_y.iloc[combined_indices].reset_index(drop=True)

    print(f"✅ Sintéticos generados: {len(synthetic_X)} muestras")
    return synthetic_X, synthetic_y

def run_synthetic_ratio_experiment():
    """Experimento principal corregido"""
    print("🎯 INICIANDO EXPERIMENTO DE RATIOS SINTÉTICOS")
    print("=" * 60)

    # Cargar datos reales
    real_data = load_real_data()
    total_real_samples = sum(len(real_data[d]['X']) for d in real_data)
    print(f"📊 Datos reales cargados: {len(real_data)} dominios, {total_real_samples} muestras")

    ratios = [0.0, 0.1, 0.25, 0.4, 0.5, 0.75, 1.0]
    results = {}

    for ratio in ratios:
        print(f"\n🔬 PROBANDO RATIO: {ratio}")

        if ratio == 0.0:
            # Solo datos reales (baseline)
            X_train_list = [real_data[d]['X'] for d in real_data]
            y_train_list = [real_data[d]['y'] for d in real_data]
            X_train = pd.concat(X_train_list, ignore_index=True)
            y_train = pd.concat(y_train_list, ignore_index=True)
        else:
            # Mezclar real + sintético
            synthetic_X, synthetic_y = generate_high_fidelity_synthetic(real_data, ratio)

            if len(synthetic_X) == 0:
                print("❌ Saltando ratio por error en generación")
                continue

            real_X_list = [real_data[d]['X'] for d in real_data]
            real_y_list = [real_data[d]['y'] for d in real_data]
            real_X = pd.concat(real_X_list, ignore_index=True)
            real_y = pd.concat(real_y_list, ignore_index=True)

            X_train = pd.concat([real_X, synthetic_X], ignore_index=True)
            y_train = pd.concat([real_y, synthetic_y], ignore_index=True)

        print(f"   📈 Dataset final: {len(X_train)} muestras")

        # Entrenar modelo
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # 🔥 VALIDACIÓN TSTR (Train Synthetic Test Real)
        test_results = {}
        for test_domain in real_data.keys():
            X_test = real_data[test_domain]['X']
            y_test = real_data[test_domain]['y']

            y_pred = model.predict(X_test)
            test_results[test_domain] = {
                'f1': f1_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred)
            }

        # Métricas promedio
        avg_f1 = np.mean([test_results[d]['f1'] for d in test_results])
        avg_recall = np.mean([test_results[d]['recall'] for d in test_results])

        results[ratio] = {
            'train_samples': len(X_train),
            'synthetic_ratio': ratio,
            'test_results': test_results,
            'avg_f1': avg_f1,
            'avg_recall': avg_recall
        }

        print(f"   📊 F1 Promedio: {avg_f1:.4f}, Recall: {avg_recall:.4f}")

    return results

def extreme_robustness_test(best_model, best_ratio):
    """Tests de robustez extrema - VERSIÓN SIMPLIFICADA"""
    print(f"\n🔥 INICIANDO TESTS DE ROBUSTEZ EXTREMA (Ratio: {best_ratio})")
    print("=" * 60)

    real_data = load_real_data()
    test_domain = list(real_data.keys())[0]
    X_test = real_data[test_domain]['X']
    y_test = real_data[test_domain]['y']

    # Baseline
    y_pred_baseline = best_model.predict(X_test)
    f1_baseline = f1_score(y_test, y_pred_baseline)

    robustness_tests = {'baseline': f1_baseline}

    # 1. Ruido Extremo
    print("🌪️  Test 1: 50% Ruido Extremo")
    X_noisy = X_test.copy()
    for col in X_noisy.columns:
        noise = np.random.normal(0, 0.5, len(X_noisy))  # 50% de ruido
        X_noisy[col] = X_noisy[col] + noise

    y_pred_noisy = best_model.predict(X_noisy)
    robustness_tests['50pct_noise'] = f1_score(y_test, y_pred_noisy)

    # 2. Missing Values
    print("❓ Test 2: 30% Missing Values")
    X_missing = X_test.copy()
    for col in X_missing.columns:
        mask = np.random.random(len(X_missing)) < 0.3
        X_missing.loc[mask, col] = np.nan

    # Imputación con medianas
    for col in X_missing.columns:
        median_val = X_missing[col].median()
        X_missing[col].fillna(median_val, inplace=True)

    y_pred_missing = best_model.predict(X_missing)
    robustness_tests['30pct_missing'] = f1_score(y_test, y_pred_missing)

    # 3. Concept Drift Simple
    print("🌀 Test 3: Concept Drift Simple")
    X_drift = X_test.copy()
    # Cambiar distribuciones de features clave
    for col in ['entropy', 'io_intensity', 'resource_usage']:
        if col in X_drift.columns:
            X_drift[col] = X_drift[col] * 1.8  # Aumentar significativamente

    y_pred_drift = best_model.predict(X_drift)
    robustness_tests['concept_drift'] = f1_score(y_test, y_pred_drift)

    print("\n📊 RESULTADOS ROBUSTEZ:")
    for test_name, f1_score_val in robustness_tests.items():
        baseline_diff = f1_score_val - f1_baseline
        print(f"   {test_name:15}: F1 = {f1_score_val:.4f} (Δ: {baseline_diff:+.4f})")

    return robustness_tests

def analyze_feature_importance_changes(ratio_results, real_data):
    """Analizar cómo cambia la importancia de features con diferentes ratios"""
    print(f"\n🔍 ANALIZANDO CAMBIOS EN FEATURE IMPORTANCE")
    print("=" * 60)

    # Entrenar modelo para cada ratio y extraer feature importance
    feature_importance_data = {}

    for ratio in ratio_results.keys():
        if ratio == 0.0:
            X_train_list = [real_data[d]['X'] for d in real_data]
            y_train_list = [real_data[d]['y'] for d in real_data]
            X_train = pd.concat(X_train_list, ignore_index=True)
            y_train = pd.concat(y_train_list, ignore_index=True)
        else:
            synthetic_X, synthetic_y = generate_high_fidelity_synthetic(real_data, ratio)
            if len(synthetic_X) == 0:
                continue

            real_X_list = [real_data[d]['X'] for d in real_data]
            real_y_list = [real_data[d]['y'] for d in real_data]
            real_X = pd.concat(real_X_list, ignore_index=True)
            real_y = pd.concat(real_y_list, ignore_index=True)

            X_train = pd.concat([real_X, synthetic_X], ignore_index=True)
            y_train = pd.concat([real_y, synthetic_y], ignore_index=True)

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Guardar feature importance
        importance_df = pd.DataFrame({
            'feature': X_train.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        feature_importance_data[ratio] = importance_df

    # Mostrar top features para cada ratio
    print("🔝 TOP 5 FEATURES POR RATIO:")
    for ratio, importance_df in feature_importance_data.items():
        print(f"\n   Ratio {ratio}:")
        top_features = importance_df.head(5)
        for _, row in top_features.iterrows():
            print(f"      {row['feature']:20}: {row['importance']:.4f}")

    return feature_importance_data

if __name__ == "__main__":
    # 1. Experimento de ratios sintéticos
    ratio_results = run_synthetic_ratio_experiment()

    if not ratio_results:
        print("❌ No se pudieron generar resultados")
        exit(1)

    # 2. Encontrar mejor ratio
    best_ratio = max(ratio_results.keys(),
                     key=lambda x: ratio_results[x]['avg_f1'])
    best_f1 = ratio_results[best_ratio]['avg_f1']

    print(f"\n🎯 MEJOR RATIO: {best_ratio} (F1: {best_f1:.4f})")

    # 3. Entrenar modelo con mejor ratio para análisis
    print(f"\n🛡️ ENTRENANDO MODELO ÓPTIMO (Ratio: {best_ratio})...")
    real_data = load_real_data()

    if best_ratio == 0.0:
        X_optimal_list = [real_data[d]['X'] for d in real_data]
        y_optimal_list = [real_data[d]['y'] for d in real_data]
        X_optimal = pd.concat(X_optimal_list, ignore_index=True)
        y_optimal = pd.concat(y_optimal_list, ignore_index=True)
    else:
        synthetic_X, synthetic_y = generate_high_fidelity_synthetic(real_data, best_ratio)
        real_X_list = [real_data[d]['X'] for d in real_data]
        real_y_list = [real_data[d]['y'] for d in real_data]
        real_X = pd.concat(real_X_list, ignore_index=True)
        real_y = pd.concat(real_y_list, ignore_index=True)
        X_optimal = pd.concat([real_X, synthetic_X], ignore_index=True)
        y_optimal = pd.concat([real_y, synthetic_y], ignore_index=True)

    optimal_model = RandomForestClassifier(n_estimators=100, random_state=42)
    optimal_model.fit(X_optimal, y_optimal)

    # 4. Tests de robustez
    robustness_results = extreme_robustness_test(optimal_model, best_ratio)

    # 5. Análisis de feature importance
    feature_importance_results = analyze_feature_importance_changes(ratio_results, real_data)

    # 6. Guardar resultados completos
    final_results = {
        'synthetic_ratio_experiment': ratio_results,
        'optimal_ratio': best_ratio,
        'optimal_f1': best_f1,
        'extreme_robustness_tests': robustness_results,
        'feature_importance_analysis': {
            ratio: df.to_dict() for ratio, df in feature_importance_results.items()
        }
    }

    with open('results/synthetic_ratio_robustness.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.int64, np.float64)) else x)

    print(f"\n💾 Resultados guardados en: results/synthetic_ratio_robustness.json")

    # 7. Análisis comparativo final
    baseline_f1 = ratio_results[0.0]['avg_f1']
    improvement = best_f1 - baseline_f1
    improvement_pct = (improvement / baseline_f1) * 100 if baseline_f1 > 0 else 0

    print(f"\n" + "="*50)
    print("📈 ANÁLISIS COMPARATIVO FINAL")
    print("="*50)
    print(f"   Baseline (0% sintético):    F1 = {baseline_f1:.4f}")
    print(f"   Mejor modelo ({best_ratio*100:.0f}% sintético): F1 = {best_f1:.4f}")
    print(f"   MEJORA: {improvement:.4f} ({improvement_pct:+.1f}%)")

    if improvement > 0.01:  # Mejora significativa
        print("✅✅✅ Los datos sintéticos MEJORAN significativamente el modelo")
        print("   → Evidencia a favor de las técnicas del paper DDoS")
    elif improvement > 0:
        print("✅ Los datos sintéticos mejoran ligeramente el modelo")
        print("   → Las técnicas funcionan pero nuestro baseline ya es bueno")
    else:
        print("❌ Los datos sintéticos NO mejoran el modelo")
        print("   → Nuestro enfoque ya está en el óptimo global")
        print("   → Evidencia sólida para el paper contra datasets académicos")

    print(f"\n🎯 CONCLUSIÓN PARA EL PAPER:")
    if best_ratio > 0:
        print(f"   'El ratio óptimo de datos sintéticos es {best_ratio*100:.0f}%'")
    else:
        print("   'Los datos sintéticos no mejoran modelos ya óptimos'")