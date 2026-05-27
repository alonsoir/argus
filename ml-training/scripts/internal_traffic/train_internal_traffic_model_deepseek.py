#!/usr/bin/env python3
"""
INTERNAL TRAFFIC DETECTOR - CORREGIDO PARA ONNX
Versión corregida sin early_stopping_rounds
"""

import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =====================================================================
# CONFIG - INTERNAL TRAFFIC DETECTOR
# =====================================================================
BASE_PATH = Path(__file__).parent.parent
DATASET_PATH = BASE_PATH / "datasets" / "internal-normal"
OUTPUT_PATH = BASE_PATH / "outputs"
MODEL_NAME = "internal_traffic_detector_onnx_ready"

# Parámetros XGBoost optimizados para ONNX
XGBOOST_PARAMS = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'n_jobs': -1
    # NOTA: early_stopping_rounds removido para compatibilidad
}

def load_internal_traffic_data():
    """Carga datos de tráfico interno"""
    print("📥 CARGANDO DATOS DE TRÁFICO INTERNO")

    dataset_path = DATASET_PATH / "internal_traffic_dataset.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"❌ Dataset no encontrado: {dataset_path}")

    df = pd.read_csv(dataset_path)
    print(f"   ✅ {len(df)} muestras cargadas")
    return df

def prepare_internal_features(df):
    """Prepara features para detección de tráfico interno"""
    print("🔧 PREPARANDO FEATURES INTERNAS")

    # Features básicas de tráfico interno
    features = []

    # 1. Estadísticas básicas de flujo
    if 'sbytes' in df.columns and 'dbytes' in df.columns:
        df['total_bytes'] = df['sbytes'] + df['dbytes']
        df['byte_ratio'] = df['sbytes'] / (df['dbytes'] + 1)  # +1 para evitar división por cero
        features.extend(['sbytes', 'dbytes', 'total_bytes', 'byte_ratio'])

    # 2. Patrones de puertos internos
    if 'sport' in df.columns and 'dport' in df.columns:
        df['is_common_internal_port'] = df['dport'].apply(
            lambda x: 1 if x in [80, 443, 22, 21, 25, 53, 110, 143, 993, 995] else 0
        )
        features.append('is_common_internal_port')

    # 3. Características de protocolo
    if 'proto' in df.columns:
        # Codificar protocolos comunes internos
        common_protocols = ['tcp', 'udp', 'icmp']
        for proto in common_protocols:
            df[f'proto_{proto}'] = df['proto'].apply(lambda x: 1 if str(x).lower() == proto else 0)
            features.append(f'proto_{proto}')

    # 4. Features temporales (si existen)
    if 'ts' in df.columns:
        df['ts'] = pd.to_datetime(df['ts'])
        df['hour_of_day'] = df['ts'].dt.hour
        df['is_business_hours'] = df['hour_of_day'].apply(lambda x: 1 if 9 <= x <= 17 else 0)
        features.extend(['hour_of_day', 'is_business_hours'])

    # 5. Features de comportamiento
    if 'spkts' in df.columns and 'dpkts' in df.columns:
        df['total_packets'] = df['spkts'] + df['dpkts']
        df['packet_imbalance'] = abs(df['spkts'] - df['dpkts']) / (df['total_packets'] + 1)
        features.extend(['spkts', 'dpkts', 'total_packets', 'packet_imbalance'])

    print(f"   ✅ {len(features)} features preparadas")
    return df[features]

def create_external_traffic_data(n_samples=1000):
    """Crea datos sintéticos de tráfico externo"""
    print("🌐 CREANDO DATOS EXTERNOS SINTÉTICOS")

    data = []
    for i in range(n_samples):
        # Patrones típicos de tráfico externo
        sample = {
            'sbytes': np.random.exponential(5000),      # Más bytes enviados
            'dbytes': np.random.exponential(1000),      # Menos bytes recibidos
            'total_bytes': np.random.exponential(6000),
            'byte_ratio': np.random.exponential(5),     # Ratio más alto
            'is_common_internal_port': np.random.choice([0, 1], p=[0.8, 0.2]),  # Menos puertos comunes
            'proto_tcp': np.random.choice([0, 1], p=[0.3, 0.7]),
            'proto_udp': np.random.choice([0, 1], p=[0.7, 0.3]),
            'proto_icmp': np.random.choice([0, 1], p=[0.9, 0.1]),
            'hour_of_day': np.random.randint(0, 24),
            'is_business_hours': np.random.choice([0, 1], p=[0.6, 0.4]),
            'spkts': np.random.poisson(100),
            'dpkts': np.random.poisson(20),
            'total_packets': np.random.poisson(120),
            'packet_imbalance': np.random.exponential(0.8)  # Mayor desbalance
        }
        data.append(sample)

    df_external = pd.DataFrame(data)
    print(f"   ✅ {len(df_external)} muestras externas creadas")
    return df_external

def train_internal_traffic_model():
    """Entrena el modelo de detección de tráfico interno"""
    print("🚀 ENTRENANDO MODELO DE TRÁFICO INTERNO")
    print("=" * 60)

    # 1. Cargar datos internos
    df_internal = load_internal_traffic_data()

    # 2. Preparar features internas
    X_internal = prepare_internal_features(df_internal)

    # 3. Crear datos externos
    X_external = create_external_traffic_data(n_samples=len(X_internal))

    # 4. Combinar y crear labels
    X_combined = pd.concat([X_internal, X_external], ignore_index=True)
    y_combined = np.array([1] * len(X_internal) + [0] * len(X_external))  # 1=interno, 0=externo

    print(f"\n📊 DATASET FINAL:")
    print(f"   Muestras internas: {len(X_internal)}")
    print(f"   Muestras externas: {len(X_external)}")
    print(f"   Total: {len(X_combined)}")
    print(f"   Features: {len(X_combined.columns)}")

    # 5. Split de datos
    X_train, X_test, y_train, y_test = train_test_split(
        X_combined, y_combined, test_size=0.3, stratify=y_combined, random_state=42
    )

    # 6. Escalar features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"\n🔧 ENTRENANDO MODELO...")
    print(f"   Entrenamiento: {X_train.shape[0]} muestras")
    print(f"   Prueba: {X_test.shape[0]} muestras")

    # 7. Entrenar modelo (SIN early_stopping_rounds)
    model = xgb.XGBClassifier(**XGBOOST_PARAMS)
    model.fit(X_train_scaled, y_train)

    # 8. Evaluar modelo
    print(f"\n📈 EVALUANDO MODELO...")
    y_pred = model.predict(X_test_scaled)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"🎯 MÉTRICAS FINALES:")
    print(f"   Accuracy:  {acc:.4f}")
    print(f"   Precision: {prec:.4f}")
    print(f"   Recall:    {rec:.4f}")
    print(f"   F1-Score:  {f1:.4f}")

    # Reporte de clasificación
    print(f"\n📋 REPORTE DE CLASIFICACIÓN:")
    print(classification_report(y_test, y_pred, target_names=['Externo', 'Interno']))

    # 9. Validación cruzada simple
    print(f"🔍 VALIDACIÓN CRUZADA...")
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='f1')
    print(f"   F1-Score CV: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    # 10. Guardar modelo
    print(f"\n💾 GUARDANDO MODELO...")
    model_dir = OUTPUT_PATH / "models" / MODEL_NAME
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / f"{MODEL_NAME}.pkl")
    joblib.dump(scaler, model_dir / f"{MODEL_NAME}_scaler.pkl")

    # 11. Metadata
    metadata = {
        'model_name': MODEL_NAME,
        'model_type': 'INTERNAL_TRAFFIC_DETECTOR',
        'version': '1.0',
        'created': datetime.now().isoformat(),
        'features_used': list(X_combined.columns),
        'feature_count': len(X_combined.columns),
        'metrics': {
            'accuracy': float(acc),
            'precision': float(prec),
            'recall': float(rec),
            'f1_score': float(f1),
            'cv_f1_mean': float(cv_scores.mean()),
            'cv_f1_std': float(cv_scores.std())
        },
        'training_params': XGBOOST_PARAMS,
        'dataset_info': {
            'internal_samples': len(X_internal),
            'external_samples': len(X_external),
            'total_samples': len(X_combined),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        },
        'onnx_ready': True,
        'compatibility_note': 'Modelo preparado para conversión a ONNX'
    }

    with open(model_dir / f"{MODEL_NAME}_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    # Feature importance
    if hasattr(model, 'feature_importances_'):
        importance_df = pd.DataFrame({
            'feature': X_combined.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"\n🔝 TOP 10 FEATURES MÁS IMPORTANTES:")
        for idx, row in importance_df.head(10).iterrows():
            print(f"   {row['feature']:<25} {row['importance']:.4f}")

    print(f"\n✅ MODELO GUARDADO EN: {model_dir}")
    print(f"🎯 LISTO PARA CONVERSIÓN ONNX")

    return model_dir, metadata

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 INTERNAL TRAFFIC DETECTOR - ONNX READY")
    print("=" * 60)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        model_dir, metadata = train_internal_traffic_model()

        print(f"\n🎉 ENTRENAMIENTO COMPLETADO!")
        print(f"✅ Modelo de tráfico interno entrenado")
        print(f"✅ Recall: {metadata['metrics']['recall']:.4f} (detección interna)")
        print(f"✅ F1-Score: {metadata['metrics']['f1_score']:.4f}")
        print(f"✅ Dataset: {metadata['dataset_info']['total_samples']} muestras")
        print(f"✅ ONNX Ready: {metadata['onnx_ready']}")
        print(f"💾 Guardado en: {model_dir}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()