# ml-training-scripts/external_traffic/TrafficModelTrainer.py
import json
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import MinMaxScaler
import joblib
from SyntheticDataGenerator import TRAFFIC_FEATURES
from TrafficDataValidator import TrafficDataValidator

class TrafficModelTrainer:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.model = None
        self.scaler = None  # ✅ AGREGAR scaler

    def load_and_prepare_data(self):
        """Carga y prepara datos para entrenamiento CON NORMALIZACIÓN"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])

        # Convertir labels a numéricos
        df['label_num'] = df['label'].map({'internet': 0, 'internal': 1})

        # Separar features y target
        X = df[TRAFFIC_FEATURES].values
        y = df['label_num'].values

        # ✅✅✅ NORMALIZACIÓN CRÍTICA
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        X_normalized = self.scaler.fit_transform(X)

        print("📈 Features normalizadas a rango [0.0, 1.0]")
        for i, feature in enumerate(TRAFFIC_FEATURES):
            min_val = X_normalized[:, i].min()
            max_val = X_normalized[:, i].max()
            print(f"   {feature}: [{min_val:.3f}, {max_val:.3f}]")

        return X_normalized, y, data['model_info']

    def train_model(self, n_estimators=100, test_size=0.2):
        """Entrena el modelo RandomForest CON NORMALIZACIÓN"""
        print("🎯 Entrenando modelo de clasificación de tráfico CON NORMALIZACIÓN...")

        X_normalized, y, model_info = self.load_and_prepare_data()  # ✅ Usar datos normalizados

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_normalized, y, test_size=test_size, random_state=42, stratify=y
        )

        # Entrenar RandomForest
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train, y_train)

        # Evaluar
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        print(f"✅ Modelo de tráfico entrenado - Accuracy: {accuracy:.4f}")
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred,
                                    target_names=['internet', 'internal']))

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': TRAFFIC_FEATURES,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"\n🎯 Feature Importance:")
        for _, row in feature_importance.head(5).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        # ✅ GUARDAR SCALER
        joblib.dump(self.scaler, 'traffic_scaler.pkl')
        print("💾 Scaler guardado: traffic_scaler.pkl")

        return self.model, accuracy, model_info

    def save_model(self, filename: str):
        """Guarda modelo en formato PKL"""
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train_model() primero.")

        with open(filename, 'wb') as f:
            pickle.dump(self.model, f)

        print(f"💾 Modelo de tráfico guardado: {filename}")

# Entrenar y guardar modelo
if __name__ == "__main__":
    # 1. Validar datos primero
    validator = TrafficDataValidator("traffic_classification_dataset.json")
    separability_scores = validator.validate_separability()

    # 2. Entrenar modelo
    if separability_scores and max(separability_scores.values()) > 1.0:
        trainer = TrafficModelTrainer("traffic_classification_dataset.json")
        model, accuracy, model_info = trainer.train_model(n_estimators=100)
        trainer.save_model("traffic_classification_model.pkl")

        print(f"\n🎉 Modelo de tráfico completado!")
        print(f"📈 Accuracy: {accuracy:.4f}")
        print(f"🌳 Árboles: {len(TRAFFIC_FEATURES)} features")
        print(f"📊 Muestras: {model_info['n_samples']}")
    else:
        print("❌ Datos no separables suficientes para entrenar modelo")