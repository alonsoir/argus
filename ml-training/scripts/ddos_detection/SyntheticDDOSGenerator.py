# ml-training-scripts/ddos_detection/SyntheticDDOSGenerator.py
import numpy as np
import pandas as pd
from typing import Dict, List
import json
from DDOSFeatures import DDOS_FEATURES

class DDOSSyntheticGenerator:
    def __init__(self, n_samples=50000):
        self.n_samples = n_samples
        self.features = DDOS_FEATURES

    def generate_normal_traffic(self) -> Dict[str, List[float]]:
        """Tráfico normal de red"""
        print("🟢 Generando tráfico NORMAL...")

        data = {
            # Patrones de tráfico normal (balanceados y estables)
            'syn_ack_ratio': np.random.beta(2, 2, self.n_samples),           # Balanceado ~1.0
            'packet_symmetry': np.random.beta(5, 5, self.n_samples),         # Balanceado inbound/outbound
            'source_ip_dispersion': np.random.lognormal(2.0, 0.3, self.n_samples),  # IPs moderadas
            'protocol_anomaly_score': np.random.beta(1, 15, self.n_samples),        # Muy baja anomalía
            'packet_size_entropy': np.random.uniform(0.7, 0.95, self.n_samples),    # Entropía alta (diverso)

            # Comportamiento normal estable
            'traffic_amplification_factor': np.random.beta(1, 10, self.n_samples),  # Muy baja amplificación
            'flow_completion_rate': np.random.beta(9, 1, self.n_samples),           # Muy alta completitud
            'traffic_escalation_rate': np.random.normal(0.05, 0.02, self.n_samples),# Crecimiento estable
            'resource_saturation_score': np.random.beta(1, 20, self.n_samples)      # Muy baja saturación
        }
        return data

    def generate_ddos_attacks(self) -> Dict[str, List[float]]:
        """Diferentes tipos de ataques DDoS"""
        print("🔴 Generando ataques DDoS...")

        # Dividir muestras entre tipos de ataque
        n_per_attack = self.n_samples // 4

        # SYN Flood Attack
        syn_flood = {
            'syn_ack_ratio': np.random.lognormal(2.0, 0.4, n_per_attack),      # Muchos SYN, pocos ACK
            'packet_symmetry': np.random.beta(1, 25, n_per_attack),            # Extremadamente desbalanceado
            'source_ip_dispersion': np.random.lognormal(4.5, 0.3, n_per_attack), # IPs muy dispersas
            'flow_completion_rate': np.random.beta(1, 15, n_per_attack),       # Muy baja completitud
        }

        # UDP Amplification Attack
        udp_amplification = {
            'traffic_amplification_factor': np.random.beta(15, 2, n_per_attack), # Alta amplificación
            'protocol_anomaly_score': np.random.beta(12, 1, n_per_attack),      # Alta anomalía UDP
            'packet_size_entropy': np.random.uniform(0.1, 0.4, n_per_attack),   # Baja entropía (paquetes similares)
            'packet_symmetry': np.random.beta(1, 10, n_per_attack),             # Desbalanceado
        }

        # HTTP Flood Attack
        http_flood = {
            'flow_completion_rate': np.random.beta(3, 8, n_per_attack),         # Baja completitud
            'traffic_escalation_rate': np.random.lognormal(1.2, 0.3, n_per_attack), # Escalada rápida
            'source_ip_dispersion': np.random.lognormal(1.5, 0.2, n_per_attack), # IPs concentradas
        }

        # Mixed/Advanced Attack
        mixed_attack = {
            'resource_saturation_score': np.random.beta(12, 3, n_per_attack),   # Alta saturación
            'protocol_anomaly_score': np.random.beta(8, 2, n_per_attack),       # Anomalía media-alta
            'traffic_amplification_factor': np.random.beta(6, 3, n_per_attack), # Amplificación media
            'traffic_escalation_rate': np.random.lognormal(0.8, 0.3, n_per_attack), # Escalada media
        }

        # Combinar todos los ataques
        all_attacks = [syn_flood, udp_amplification, http_flood, mixed_attack]

        # Inicializar estructura de datos
        data = {feature: [] for feature in self.features}

        # Llenar con datos de cada tipo de ataque
        for attack in all_attacks:
            for feature in self.features:
                if feature in attack:
                    data[feature].extend(attack[feature])
                else:
                    # Valores por defecto para características no específicas
                    if feature == 'syn_ack_ratio':
                        data[feature].extend(np.random.beta(3, 1, n_per_attack))  # Moderadamente alto
                    elif feature == 'packet_symmetry':
                        data[feature].extend(np.random.beta(1, 8, n_per_attack))  # Desbalanceado
                    elif feature == 'source_ip_dispersion':
                        data[feature].extend(np.random.lognormal(3.0, 0.4, n_per_attack)) # Dispersión media
                    elif feature == 'protocol_anomaly_score':
                        data[feature].extend(np.random.beta(6, 3, n_per_attack))  # Anomalía media
                    elif feature == 'packet_size_entropy':
                        data[feature].extend(np.random.uniform(0.3, 0.7, n_per_attack)) # Entropía media-baja
                    elif feature == 'traffic_amplification_factor':
                        data[feature].extend(np.random.beta(5, 3, n_per_attack))  # Amplificación media
                    elif feature == 'flow_completion_rate':
                        data[feature].extend(np.random.beta(2, 6, n_per_attack))  # Completitud baja
                    elif feature == 'traffic_escalation_rate':
                        data[feature].extend(np.random.lognormal(0.6, 0.3, n_per_attack)) # Escalada
                    elif feature == 'resource_saturation_score':
                        data[feature].extend(np.random.beta(8, 4, n_per_attack))  # Saturación media

        return data

    def create_complete_dataset(self) -> pd.DataFrame:
        """Crea dataset balanceado normal vs DDoS"""
        np.random.seed(42)  # DAY255 reproducibilidad de artefacto: mismo dataset -> mismo .hpp (Via Appia)
        normal_data = self.generate_normal_traffic()
        ddos_data = self.generate_ddos_attacks()

        # Crear DataFrames
        df_normal = pd.DataFrame(normal_data)
        df_normal['label'] = 'normal'

        df_ddos = pd.DataFrame(ddos_data)
        df_ddos['label'] = 'ddos'

        # Combinar y mezclar
        complete_df = pd.concat([df_normal, df_ddos], ignore_index=True)
        complete_df = complete_df.sample(frac=1, random_state=42).reset_index(drop=True)

        print(f"✅ Dataset DDoS creado: {len(complete_df)} muestras")
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
                'classes': ['normal', 'ddos']
            },
            'dataset': df.to_dict('records')
        }

        with open(filename, 'w') as f:
            json.dump(dataset_dict, f, indent=2)

        print(f"💾 Dataset DDoS guardado: {filename}")

if __name__ == "__main__":
    generator = DDOSSyntheticGenerator(n_samples=25000)
    generator.save_dataset("ddos_detection_dataset.json")