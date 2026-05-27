# ml-training-scripts/internal_traffic/InternalDataValidator.py
import json
import pandas as pd
from InternalFeatures import INTERNAL_FEATURES

class InternalDataValidator:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path

    def validate_separability(self):
        """Valida que las clases sean separables"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])

        # Análisis de separación por feature
        separability_scores = {}
        for feature in INTERNAL_FEATURES:
            benign_mean = df[df['label'] == 'benign'][feature].mean()
            suspicious_mean = df[df['label'] == 'suspicious'][feature].mean()
            separation = abs(benign_mean - suspicious_mean) / df[feature].std()
            separability_scores[feature] = separation

        print("📊 Separabilidad de features Internal Traffic:")
        for feature, score in sorted(separability_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {feature}: {score:.3f}")

        return separability_scores

    def analyze_threat_patterns(self):
        """Análisis específico de patrones de amenaza interna"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])
        suspicious_data = df[df['label'] == 'suspicious']

        print("\n🔍 Análisis de Patrones de Amenaza Interna:")

        # Lateral Movement patterns
        high_lateral = len(suspicious_data[suspicious_data['lateral_movement_score'] > 0.7])
        print(f"  Lateral Movement indicators: {high_lateral}/{len(suspicious_data)} muestras")

        # Service Discovery patterns
        high_discovery = len(suspicious_data[suspicious_data['service_discovery_patterns'] > 0.7])
        print(f"  Service Discovery indicators: {high_discovery}/{len(suspicious_data)} muestras")

        # Data Exfiltration patterns
        high_exfiltration = len(suspicious_data[suspicious_data['data_exfiltration_indicators'] > 0.7])
        print(f"  Data Exfiltration indicators: {high_exfiltration}/{len(suspicious_data)} muestras")

        # Temporal Anomalies
        high_temporal = len(suspicious_data[suspicious_data['temporal_anomaly_score'] > 0.7])
        print(f"  Temporal Anomalies indicators: {high_temporal}/{len(suspicious_data)} muestras")

# AÑADIR ESTO PARA EJECUCIÓN
if __name__ == "__main__":
    validator = InternalDataValidator("internal_traffic_dataset.json")
    separability_scores = validator.validate_separability()

    # Análisis adicional
    print(f"\n🎯 Resumen de separabilidad Internal Traffic:")
    max_score = max(separability_scores.values())
    min_score = min(separability_scores.values())
    avg_score = sum(separability_scores.values()) / len(separability_scores)

    print(f"  Máxima separación: {max_score:.3f}")
    print(f"  Mínima separación: {min_score:.3f}")
    print(f"  Promedio: {avg_score:.3f}")

    # Evaluación cualitativa
    if avg_score > 1.5:
        print("✅ Excelente separación - Datos de alta calidad para Internal Traffic")
    elif avg_score > 1.0:
        print("✅ Buena separación - Datos adecuados para entrenamiento")
    else:
        print("⚠️  Separación moderada - Considerar ajustar features")

    # Análisis de patrones específicos
    validator.analyze_threat_patterns()