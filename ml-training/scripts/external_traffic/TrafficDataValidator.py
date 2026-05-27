# ml-training-scripts/external_traffic/TrafficDataValidator.py
import json
import pandas as pd
from SyntheticDataGenerator import TRAFFIC_FEATURES

class TrafficDataValidator:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path

    def validate_separability(self):
        """Valida que las clases sean separables"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])

        # Análisis de separación por feature
        separability_scores = {}
        for feature in TRAFFIC_FEATURES:
            internet_mean = df[df['label'] == 'internet'][feature].mean()
            internal_mean = df[df['label'] == 'internal'][feature].mean()
            separation = abs(internet_mean - internal_mean) / df[feature].std()
            separability_scores[feature] = separation

        print("📊 Separabilidad de features:")
        for feature, score in sorted(separability_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {feature}: {score:.3f}")

        return separability_scores

# AÑADIR ESTO PARA EJECUCIÓN
if __name__ == "__main__":
    validator = TrafficDataValidator("traffic_classification_dataset.json")
    separability_scores = validator.validate_separability()

    # Análisis adicional
    print(f"\n🎯 Resumen de separabilidad:")
    max_score = max(separability_scores.values())
    min_score = min(separability_scores.values())
    avg_score = sum(separability_scores.values()) / len(separability_scores)

    print(f"  Máxima separación: {max_score:.3f}")
    print(f"  Mínima separación: {min_score:.3f}")
    print(f"  Promedio: {avg_score:.3f}")

    # Evaluación cualitativa
    if avg_score > 1.5:
        print("✅ Excelente separación - Datos de alta calidad")
    elif avg_score > 1.0:
        print("✅ Buena separación - Datos adecuados para entrenamiento")
    else:
        print("⚠️  Separación moderada - Considerar ajustar features")