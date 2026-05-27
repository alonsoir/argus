# ml-training-scripts/external_traffic/SyntheticDataGeneratorLight.py
import random
import pandas as pd
from typing import Dict, List
import json

TRAFFIC_FEATURES = [
    "packet_rate", "connection_rate", "tcp_udp_ratio",
    "avg_packet_size", "port_entropy", "flow_duration_std",
    "src_ip_entropy", "dst_ip_concentration", "protocol_variety",
    "temporal_consistency"
]

class TrafficSyntheticGeneratorLight:
    def __init__(self, n_samples=50000):
        self.n_samples = n_samples
        self.features = TRAFFIC_FEATURES

    def random_lognormal(self, mu, sigma, n):
        """Implementación simple de distribución log-normal"""
        return [random.lognormvariate(mu, sigma) for _ in range(n)]

    def random_beta(self, alpha, beta, n):
        """Implementación simple de distribución beta"""
        return [random.betavariate(alpha, beta) for _ in range(n)]

    def random_normal(self, mu, sigma, n):
        """Implementación simple de distribución normal"""
        return [random.gauss(mu, sigma) for _ in range(n)]

    def random_poisson(self, lam, n):
        """Implementación simple de distribución Poisson"""
        return [random.poisson(lam) for _ in range(n)]

    def generate_internet_traffic(self) -> Dict[str, List[float]]:
        """Tráfico típico hacia Internet"""
        print("🌐 Generando tráfico INTERNET...")

        data = {
            'packet_rate': self.random_lognormal(6.5, 0.8, self.n_samples),
            'connection_rate': self.random_lognormal(3.5, 0.6, self.n_samples),
            'tcp_udp_ratio': self.random_beta(8, 2, self.n_samples),
            'avg_packet_size': self.random_normal(1200, 300, self.n_samples),
            'port_entropy': [random.uniform(0.7, 0.95) for _ in range(self.n_samples)],
            'flow_duration_std': self.random_lognormal(2.5, 0.7, self.n_samples),
            'src_ip_entropy': [random.uniform(0.6, 0.9) for _ in range(self.n_samples)],
            'dst_ip_concentration': self.random_beta(2, 8, self.n_samples),
            'protocol_variety': self.random_poisson(4, self.n_samples),
            'temporal_consistency': self.random_beta(3, 7, self.n_samples)
        }
        return data

    def generate_internal_traffic(self) -> Dict[str, List[float]]:
        """Tráfico interno típico"""
        print("🏠 Generando tráfico INTERNO...")

        data = {
            'packet_rate': self.random_lognormal(5.0, 0.5, self.n_samples),
            'connection_rate': self.random_lognormal(1.5, 0.4, self.n_samples),
            'tcp_udp_ratio': self.random_beta(9, 1, self.n_samples),
            'avg_packet_size': self.random_normal(800, 150, self.n_samples),
            'port_entropy': [random.uniform(0.2, 0.5) for _ in range(self.n_samples)],
            'flow_duration_std': self.random_lognormal(1.0, 0.3, self.n_samples),
            'src_ip_entropy': [random.uniform(0.1, 0.4) for _ in range(self.n_samples)],
            'dst_ip_concentration': self.random_beta(8, 2, self.n_samples),
            'protocol_variety': self.random_poisson(2, self.n_samples),
            'temporal_consistency': self.random_beta(8, 2, self.n_samples)
        }
        return data

    def create_complete_dataset(self) -> pd.DataFrame:
        """Crea dataset balanceado con ambos tipos de tráfico"""
        internet_data = self.generate_internet_traffic()
        internal_data = self.generate_internal_traffic()

        df_internet = pd.DataFrame(internet_data)
        df_internet['label'] = 'internet'

        df_internal = pd.DataFrame(internal_data)
        df_internal['label'] = 'internal'

        complete_df = pd.concat([df_internet, df_internal], ignore_index=True)
        complete_df = complete_df.sample(frac=1).reset_index(drop=True)

        print(f"✅ Dataset creado: {len(complete_df)} muestras")
        print(f"📊 Distribución: {complete_df['label'].value_counts().to_dict()}")

        return complete_df

    def save_dataset(self, filename: str):
        """Guarda dataset en formato JSON"""
        df = self.create_complete_dataset()

        dataset_dict = {
            'model_info': {
                'n_samples': len(df),
                'n_features': len(self.features),
                'feature_names': self.features,
                'classes': ['internet', 'internal']
            },
            'dataset': df.to_dict('records')
        }

        with open(filename, 'w') as f:
            json.dump(dataset_dict, f, indent=2)

        print(f"💾 Dataset guardado: {filename}")

if __name__ == "__main__":
    generator = TrafficSyntheticGeneratorLight(n_samples=1000)  # Menos muestras para prueba
    generator.save_dataset("traffic_classification_dataset_light.json")