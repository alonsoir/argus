import json

import pandas as pd
# ml-training-scripts/external_traffic/Validator_Data_Generator.py

TRAFFIC_FEATURES = [
    # Kernel Space (captura directa)
    "packet_rate",                    # Paquetes/segundo
    "connection_rate",                # Nuevas conexiones/segundo
    "tcp_udp_ratio",                  # Ratio TCP vs UDP
    "avg_packet_size",                # Tamaño promedio paquetes
    "port_entropy",                   # Diversidad de puertos

    # User Space (cálculos complejos)
    "flow_duration_std",              # Desviación estándar duración flujos
    "src_ip_entropy",                 # Entropía IPs origen
    "dst_ip_concentration",           # Concentración IPs destino
    "protocol_variety",               # Variedad de protocolos
    "temporal_consistency"            # Consistencia patrones temporales
]

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