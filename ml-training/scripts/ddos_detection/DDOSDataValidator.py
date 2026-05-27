# ml-training-scripts/ddos_detection/DDOSDataValidator.py
import json
import pandas as pd
from DDOSFeatures import DDOS_FEATURES

class DDOSDataValidator:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path

    def validate_separability(self):
        """Valida que las clases sean separables"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])

        # Análisis de separación por feature
        separability_scores = {}
        for feature in DDOS_FEATURES:
            normal_mean = df[df['label'] == 'normal'][feature].mean()
            ddos_mean = df[df['label'] == 'ddos'][feature].mean()
            separation = abs(normal_mean - ddos_mean) / df[feature].std()
            separability_scores[feature] = separation

        print("📊 Separabilidad de features DDoS:")
        for feature, score in sorted(separability_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {feature}: {score:.3f}")

        return separability_scores

    def analyze_attack_patterns(self):
        """Análisis específico de patrones de ataque"""
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['dataset'])
        ddos_data = df[df['label'] == 'ddos']

        print("\n🔍 Análisis de Patrones DDoS:")

        # SYN Flood patterns
        high_syn_ratio = len(ddos_data[ddos_data['syn_ack_ratio'] > 5.0])
        print(f"  SYN Flood indicators: {high_syn_ratio}/{len(ddos_data)} muestras")

        # UDP Amplification patterns
        high_amplification = len(ddos_data[ddos_data['traffic_amplification_factor'] > 0.7])
        print(f"  UDP Amplification indicators: {high_amplification}/{len(ddos_data)} muestras")

        # HTTP Flood patterns
        high_concentration = len(ddos_data[ddos_data['geographical_concentration'] > 0.7])
        print(f"  HTTP Flood indicators: {high_concentration}/{len(ddos_data)} muestras")

# AÑADIR ESTO PARA EJECUCIÓN
if __name__ == "__main__":
    validator = DDOSDataValidator("ddos_detection_dataset.json")
    separability_scores = validator.validate_separability()

    # Análisis adicional
    print(f"\n🎯 Resumen de separabilidad DDoS:")
    max_score = max(separability_scores.values())
    min_score = min(separability_scores.values())
    avg_score = sum(separability_scores.values()) / len(separability_scores)

    print(f"  Máxima separación: {max_score:.3f}")
    print(f"  Mínima separación: {min_score:.3f}")
    print(f"  Promedio: {avg_score:.3f}")

    # Evaluación cualitativa
    if avg_score > 1.5:
        print("✅ Excelente separación - Datos de alta calidad para DDoS")
    elif avg_score > 1.0:
        print("✅ Buena separación - Datos adecuados para entrenamiento")
    else:
        print("⚠️  Separación moderada - Considerar ajustar features")

    # Análisis de patrones específicos
    validator.analyze_attack_patterns()