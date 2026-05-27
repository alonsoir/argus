# train_robust_universal.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os

def train_robust_universal_model():
    """Entrenar modelo con validación robusta para evitar sobreajuste"""
    print("🛡️ ENTRENANDO MODELO ROBUSTO CON VALIDACIÓN ESTRICTA...")

    # Cargar datasets realistas
    domains = {
        'network': 'data/network_realistic.csv',
        'files': 'data/files_realistic.csv',
        'processes': 'data/processes_realistic.csv'
    }

    all_features = []
    all_labels = []

    for domain_name, path in domains.items():
        df = pd.read_csv(path)
        feature_cols = [col for col in df.columns if col != 'is_ransomware']

        all_features.append(df[feature_cols])
        all_labels.append(df['is_ransomware'])

        print(f"✅ {domain_name}: {len(df)} samples, {df['is_ransomware'].sum()} ransomware")

    # Combinar datos
    X_combined = pd.concat(all_features, ignore_index=True)
    y_combined = pd.concat(all_labels, ignore_index=True)

    print(f"📊 DATASET COMBINADO: {X_combined.shape}")
    print(f"🎯 BALANCE: {y_combined.sum()}/{len(y_combined)} ({y_combined.mean():.1%}) ransomware")

    # 🔧 VALIDACIÓN CRUZADA ESTRICTA
    print("\n📊 VALIDACIÓN CRUZADA ESTRICTA (5-fold):")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,  # Más restrictivo para evitar sobreajuste
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight='balanced',
        random_state=42
    )

    # Cross-validation scores
    cv_scores = cross_val_score(model, X_combined, y_combined,
                                cv=cv, scoring='f1', n_jobs=-1)

    print(f"🎯 F1 Cross-Validation: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    # Entrenar modelo final
    model.fit(X_combined, y_combined)

    # Guardar modelo
    os.makedirs('models', exist_ok=True)
    model_path = 'models/universal_ransomware_robust.pkl'
    joblib.dump(model, model_path)

    print(f"💾 MODELO ROBUSTO GUARDADO: {model_path}")

    # Evaluación honesta (usando CV para evitar sobreoptimismo)
    from sklearn.model_selection import cross_val_predict
    y_pred_cv = cross_val_predict(model, X_combined, y_combined, cv=5)

    print("\n📈 EVALUACIÓN HONESTA (Cross-Validation):")
    print(classification_report(y_combined, y_pred_cv))

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_combined.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n🔝 FEATURES MÁS IMPORTANTES:")
    print(feature_importance)

    return model, X_combined, y_combined

if __name__ == "__main__":
    train_robust_universal_model()