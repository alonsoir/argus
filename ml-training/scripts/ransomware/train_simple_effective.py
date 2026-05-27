# train_simple_effective.py - CON NORMALIZACIÓN
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

def train_simple_effective_model():
    """Entrenar modelo simple pero efectivo CON NORMALIZACIÓN"""
    print("🎯 ENTRENANDO MODELO SIMPLE Y EFECTIVO CON NORMALIZACIÓN...")

    # Cargar datasets garantizados
    domains = {
        'network': 'data/network_guaranteed.csv',
        'files': 'data/files_guaranteed.csv',
        'processes': 'data/processes_guaranteed.csv'
    }

    all_data = []

    for domain_name, path in domains.items():
        df = pd.read_csv(path)
        all_data.append(df)
        print(f"✅ {domain_name}: {len(df)} samples, {df['is_ransomware'].sum()} ransomware")

    # Combinar todos los datos
    combined_df = pd.concat(all_data, ignore_index=True)
    X = combined_df.drop('is_ransomware', axis=1)
    y = combined_df['is_ransomware']

    print(f"\n📊 DATASET COMBINADO: {X.shape}")
    print(f"🎯 BALANCE: {y.sum()}/{len(y)} ransomware ({y.mean():.1%})")

    # ✅✅✅ NORMALIZACIÓN CRÍTICA: Asegurar features en [0.0, 1.0]
    print("\n🔧 APLICANDO NORMALIZACIÓN MinMaxScaler [0.0, 1.0]...")
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_normalized = scaler.fit_transform(X)

    # Verificar normalización
    print("📈 RANGOS DE FEATURES DESPUÉS DE NORMALIZACIÓN:")
    for i, feature in enumerate(X.columns):
        min_val = X_normalized[:, i].min()
        max_val = X_normalized[:, i].max()
        print(f"   {feature}: [{min_val:.3f}, {max_val:.3f}]")

    # Validación cruzada simple
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        class_weight='balanced',
        random_state=42
    )

    # Cross-validation CON DATOS NORMALIZADOS
    cv_scores = cross_val_score(model, X_normalized, y, cv=cv, scoring='f1')
    print(f"\n🎯 F1 Cross-Validation: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    # Entrenar modelo final CON DATOS NORMALIZADOS
    model.fit(X_normalized, y)

    # Guardar modelo Y scaler
    os.makedirs('models', exist_ok=True)
    model_path = 'models/simple_effective_model.pkl'
    scaler_path = 'models/ransomware_scaler.pkl'

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    print(f"💾 Modelo guardado: {model_path}")
    print(f"💾 Scaler guardado: {scaler_path}")

    # Evaluación CON DATOS NORMALIZADOS
    y_pred = model.predict(X_normalized)
    print(f"\n📈 EVALUACIÓN EN TRAIN (con datos normalizados):")
    print(classification_report(y, y_pred))

    # Feature importance
    importance_df = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n🔝 FEATURES MÁS IMPORTANTES:")
    print(importance_df.head(10))

    return model, scaler, X, y

if __name__ == "__main__":
    train_simple_effective_model()