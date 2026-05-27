# ml-training-scripts/ddos_detection/DDOSModelTrainer.py
import json
import pickle
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from DDOSFeatures import DDOS_FEATURES
from DDOSDataValidator import DDOSDataValidator

class DDOSModelTrainer:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.model = None
        self.scaler = None

    def load_and_prepare_data(self):
        """Carga y prepara datos para entrenamiento CON NORMALIZACIÓN"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])

        # Convertir labels a numéricos
        df['label_num'] = df['label'].map({'normal': 0, 'ddos': 1})

        # Separar features y target
        X = df[DDOS_FEATURES].values
        y = df['label_num'].values

        # ✅✅✅ NORMALIZACIÓN CRÍTICA - AGREGAR ESTO
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        X_normalized = self.scaler.fit_transform(X)

        print("📈 Features normalizadas a rango [0.0, 1.0]")
        for i, feature in enumerate(DDOS_FEATURES):
            min_val = X_normalized[:, i].min()
            max_val = X_normalized[:, i].max()
            print(f"   {feature}: [{min_val:.3f}, {max_val:.3f}]")

        return X_normalized, y, data['model_info']

    def train_model(self, n_estimators=100, test_size=0.2):
        """Entrena el modelo RandomForest para DDoS CON NORMALIZACIÓN"""
        print("🎯 Entrenando modelo de detección DDoS CON NORMALIZACIÓN...")

        X_normalized, y, model_info = self.load_and_prepare_data()

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

        print(f"✅ Modelo DDoS entrenado - Accuracy: {accuracy:.4f}")
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred,
                                    target_names=['normal', 'ddos']))

        # Matriz de confusión
        cm = confusion_matrix(y_test, y_pred)
        print(f"📊 Matriz de Confusión:")
        print(f"  Verdaderos Negativos: {cm[0][0]} | Falsos Positivos: {cm[0][1]}")
        print(f"  Falsos Negativos: {cm[1][0]} | Verdaderos Positivos: {cm[1][1]}")

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': DDOS_FEATURES,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"\n🎯 Feature Importance:")
        for _, row in feature_importance.head(5).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        # Guardar scaler
        joblib.dump(self.scaler, 'ddos_scaler.pkl')
        print("💾 Scaler guardado: ddos_scaler.pkl")

        return self.model, accuracy, model_info

    def save_model(self, filename: str):
        """Guarda modelo en formato PKL"""
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train_model() primero.")

        with open(filename, 'wb') as f:
            pickle.dump(self.model, f)

        print(f"💾 Modelo DDoS guardado: {filename}")

# Entrenar y guardar modelo
if __name__ == "__main__":
    # 1. Validar datos primero
    validator = DDOSDataValidator("ddos_detection_dataset.json")
    separability_scores = validator.validate_separability()

    # 2. Entrenar modelo (solo si separabilidad es buena)
    if separability_scores and max(separability_scores.values()) > 1.0:
        trainer = DDOSModelTrainer("ddos_detection_dataset.json")
        model, accuracy, model_info = trainer.train_model(n_estimators=100)
        trainer.save_model("ddos_detection_model.pkl")

        print(f"\n🎉 Modelo DDoS completado!")
        print(f"📈 Accuracy: {accuracy:.4f}")
        print(f"🌳 Árboles: {model_info['n_features']} features")
        print(f"📊 Muestras: {model_info['n_samples']}")
    else:
        print("❌ Separabilidad insuficiente. Ajustar generador de datos.")