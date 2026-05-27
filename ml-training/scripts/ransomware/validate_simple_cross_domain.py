# validate_simple_cross_domain.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, recall_score, precision_score
import json
import os

def simple_cross_domain_validation():
    """Validación cross-domain simple y efectiva"""
    print("🎯 VALIDACIÓN CRUZADA SIMPLE ENTRE DOMINIOS...")

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

    results = {}

    for test_domain in domains.keys():
        print(f"\n🔍 TESTEANDO EN: {test_domain}")

        # Entrenar con los otros dos dominios
        train_domains = [d for d in domains.keys() if d != test_domain]

        X_train = pd.concat([domain_data[d]['X'] for d in train_domains])
        y_train = pd.concat([domain_data[d]['y'] for d in train_domains])

        X_test = domain_data[test_domain]['X']
        y_test = domain_data[test_domain]['y']

        print(f"📊 Train: {X_train.shape}, Test: {X_test.shape}")
        print(f"🎯 Balance - Train: {y_train.mean():.3f}, Test: {y_test.mean():.3f}")

        # Modelo simple
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Predecir
        y_pred = model.predict(X_test)

        f1 = f1_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)

        results[test_domain] = {
            'f1': f1,
            'recall': recall,
            'precision': precision,
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }

        print(f"🎯 F1: {f1:.4f}, Recall: {recall:.4f}, Precision: {precision:.4f}")

    # Calcular promedios
    avg_f1 = np.mean([results[d]['f1'] for d in results])
    avg_recall = np.mean([results[d]['recall'] for d in results])

    print(f"\n📈 PROMEDIOS - F1: {avg_f1:.4f}, Recall: {avg_recall:.4f}")

    # Guardar resultados
    results['averages'] = {'f1': avg_f1, 'recall': avg_recall}

    os.makedirs('results', exist_ok=True)
    with open('results/simple_cross_domain.json', 'w') as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    simple_cross_domain_validation()