# ml-training-scripts/internal_traffic/SyntheticInternalGenerator.py
import numpy as np
import pandas as pd
from typing import Dict, List
import json
from InternalFeatures import INTERNAL_FEATURES

class InternalSyntheticGenerator:
    def __init__(self, n_samples=50000):
        self.n_samples = n_samples
        self.features = INTERNAL_FEATURES

    def generate_benign_internal(self) -> Dict[str, List[float]]:
        """Tráfico interno benigno típico"""
        print("🟢 Generando tráfico INTERNO BENIGNO...")

        data = {
            # Patrones benignos (estables y consistentes)
            'internal_connection_rate': np.random.lognormal(2.0, 0.3, self.n_samples),  # Conexiones moderadas
            'service_port_consistency': np.random.beta(8, 2, self.n_samples),           # Alta consistencia
            'protocol_regularity': np.random.beta(9, 1, self.n_samples),                # Muy regular
            'packet_size_consistency': np.random.beta(7, 3, self.n_samples),            # Consistente
            'connection_duration_std': np.random.lognormal(1.0, 0.2, self.n_samples),   # Baja desviación

            # Comportamiento benigno
            'lateral_movement_score': np.random.beta(1, 15, self.n_samples),            # Muy bajo
            'service_discovery_patterns': np.random.beta(1, 12, self.n_samples),        # Muy bajo
            'data_exfiltration_indicators': np.random.beta(1, 20, self.n_samples),      # Muy bajo
            'temporal_anomaly_score': np.random.beta(1, 10, self.n_samples),            # Bajo
            'access_pattern_entropy': np.random.uniform(0.1, 0.4, self.n_samples)       # Baja entropía
        }
        return data

    def generate_suspicious_internal(self) -> Dict[str, List[float]]:
        """Tráfico interno sospechoso (movimiento lateral, escaneo, etc.)"""
        print("🔴 Generando tráfico INTERNO SOSPECHOSO...")

        # Dividir entre diferentes patrones sospechosos
        n_per_pattern = self.n_samples // 4

        # Lateral Movement
        lateral_movement = {
            'lateral_movement_score': np.random.beta(12, 3, n_per_pattern),           # Alto
            'internal_connection_rate': np.random.lognormal(3.0, 0.4, n_per_pattern), # Conexiones elevadas
            'service_port_consistency': np.random.beta(2, 8, n_per_pattern),          # Baja consistencia
            'access_pattern_entropy': np.random.uniform(0.7, 0.95, n_per_pattern),    # Alta entropía
        }

        # Service Discovery/Scanning
        service_discovery = {
            'service_discovery_patterns': np.random.beta(15, 2, n_per_pattern),       # Muy alto
            'protocol_regularity': np.random.beta(2, 8, n_per_pattern),               # Irregular
            'internal_connection_rate': np.random.lognormal(3.5, 0.3, n_per_pattern), # Muy elevado
            'connection_duration_std': np.random.lognormal(2.8, 0.3, n_per_pattern),  # Alta desviación
        }

        # Data Exfiltration
        data_exfiltration = {
            'data_exfiltration_indicators': np.random.beta(14, 2, n_per_pattern),     # Muy alto
            'packet_size_consistency': np.random.beta(3, 7, n_per_pattern),           # Inconsistente
            'temporal_anomaly_score': np.random.beta(12, 3, n_per_pattern),           # Alto
            'protocol_regularity': np.random.beta(4, 6, n_per_pattern),               # Irregular
        }

        # Temporal Anomalies
        temporal_anomalies = {
            'temporal_anomaly_score': np.random.beta(12, 3, n_per_pattern),           # Alto
            'internal_connection_rate': np.random.lognormal(1.0, 0.5, n_per_pattern), # Irregular
            'service_port_consistency': np.random.beta(3, 7, n_per_pattern),          # Baja consistencia
            'lateral_movement_score': np.random.beta(8, 4, n_per_pattern),            # Medio-alto
        }

        # Combinar todos los patrones
        all_patterns = [lateral_movement, service_discovery, data_exfiltration, temporal_anomalies]

        data = {feature: [] for feature in self.features}

        for pattern in all_patterns:
            for feature in self.features:
                if feature in pattern:
                    data[feature].extend(pattern[feature])
                else:
                    # Valores por defecto para características no específicas
                    if feature == 'internal_connection_rate':
                        data[feature].extend(np.random.lognormal(2.5, 0.4, n_per_pattern))
                    elif feature == 'service_port_consistency':
                        data[feature].extend(np.random.beta(3, 7, n_per_pattern))
                    elif feature == 'protocol_regularity':
                        data[feature].extend(np.random.beta(4, 6, n_per_pattern))
                    elif feature == 'packet_size_consistency':
                        data[feature].extend(np.random.beta(3, 7, n_per_pattern))
                    elif feature == 'connection_duration_std':
                        data[feature].extend(np.random.lognormal(2.0, 0.4, n_per_pattern))
                    elif feature == 'lateral_movement_score':
                        data[feature].extend(np.random.beta(6, 4, n_per_pattern))
                    elif feature == 'service_discovery_patterns':
                        data[feature].extend(np.random.beta(7, 3, n_per_pattern))
                    elif feature == 'data_exfiltration_indicators':
                        data[feature].extend(np.random.beta(8, 4, n_per_pattern))
                    elif feature == 'temporal_anomaly_score':
                        data[feature].extend(np.random.beta(7, 3, n_per_pattern))
                    elif feature == 'access_pattern_entropy':
                        data[feature].extend(np.random.uniform(0.5, 0.9, n_per_pattern))

        return data

    def create_complete_dataset(self) -> pd.DataFrame:
        """Crea dataset balanceado benigno vs sospechoso"""
        benign_data = self.generate_benign_internal()
        suspicious_data = self.generate_suspicious_internal()

        df_benign = pd.DataFrame(benign_data)
        df_benign['label'] = 'benign'

        df_suspicious = pd.DataFrame(suspicious_data)
        df_suspicious['label'] = 'suspicious'

        complete_df = pd.concat([df_benign, df_suspicious], ignore_index=True)
        complete_df = complete_df.sample(frac=1).reset_index(drop=True)

        print(f"✅ Dataset Internal creado: {len(complete_df)} muestras")
        print(f"📊 Distribución: {complete_df['label'].value_counts().to_dict()}")

        return complete_df

    def save_dataset(self, filename: str):
        """Guarda dataset en JSON"""
        df = self.create_complete_dataset()

        dataset_dict = {
            'model_info': {
                'n_samples': len(df),
                'n_features': len(self.features),
                'feature_names': self.features,
                'classes': ['benign', 'suspicious']
            },
            'dataset': df.to_dict('records')
        }

        with open(filename, 'w') as f:
            json.dump(dataset_dict, f, indent=2)

        print(f"💾 Dataset Internal guardado: {filename}")

if __name__ == "__main__":
    generator = InternalSyntheticGenerator(n_samples=25000)
    generator.save_dataset("internal_traffic_dataset.json")