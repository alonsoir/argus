# ml-training-scripts/external_traffic/SyntheticDataGenerator.py
import numpy as np
import pandas as pd
from typing import Dict, List
import json

TRAFFIC_FEATURES = [
    "packet_rate", "connection_rate", "tcp_udp_ratio",
    "avg_packet_size", "port_entropy", "flow_duration_std",
    "src_ip_entropy", "dst_ip_concentration", "protocol_variety",
    "temporal_consistency"
]

class TrafficSyntheticGenerator:
    def __init__(self, n_samples=50000):
        self.n_samples = n_samples
        self.features = TRAFFIC_FEATURES

    def generate_internet_traffic(self) -> Dict[str, List[float]]:
        """Tráfico típico hacia Internet (usuarios navegando, APIs, etc.)"""
        print("🌐 Generando tráfico INTERNET...")

        data = {
            # Alto volumen, muchas conexiones efímeras
            'packet_rate': np.random.lognormal(6.5, 0.8, self.n_samples),  # 500-1500 pps
            'connection_rate': np.random.lognormal(3.5, 0.6, self.n_samples), # 20-80 conn/s
            'tcp_udp_ratio': np.random.beta(8, 2, self.n_samples),  # 80% TCP, 20% UDP
            'avg_packet_size': np.random.normal(1200, 300, self.n_samples), # Paquetes grandes
            'port_entropy': np.random.uniform(0.7, 0.95, self.n_samples), # Alta diversidad puertos

            # Flujos cortos y variables
            'flow_duration_std': np.random.lognormal(2.5, 0.7, self.n_samples),
            'src_ip_entropy': np.random.uniform(0.6, 0.9, self.n_samples), # Muchas IPs origen
            'dst_ip_concentration': np.random.beta(2, 8, self.n_samples),  # Pocos destinos populares
            'protocol_variety': np.random.poisson(4, self.n_samples),      # Múltiples protocolos
            'temporal_consistency': np.random.beta(3, 7, self.n_samples)   # Patrones inconsistentes
        }

        return data

    def generate_internal_traffic(self) -> Dict[str, List[float]]:
        """Tráfico interno típico (servicios, backups, replicación)"""
        print("🏠 Generando tráfico INTERNO...")

        data = {
            # Volumen moderado, conexiones estables
            'packet_rate': np.random.lognormal(5.0, 0.5, self.n_samples),  # 100-300 pps
            'connection_rate': np.random.lognormal(1.5, 0.4, self.n_samples), # 3-10 conn/s
            'tcp_udp_ratio': np.random.beta(9, 1, self.n_samples),    # 90% TCP, 10% UDP
            'avg_packet_size': np.random.normal(800, 150, self.n_samples),  # Paquetes medianos
            'port_entropy': np.random.uniform(0.2, 0.5, self.n_samples),   # Baja diversidad puertos

            # Flujos largos y estables
            'flow_duration_std': np.random.lognormal(1.0, 0.3, self.n_samples),
            'src_ip_entropy': np.random.uniform(0.1, 0.4, self.n_samples), # Pocas IPs origen
            'dst_ip_concentration': np.random.beta(8, 2, self.n_samples),  # Destinos concentrados
            'protocol_variety': np.random.poisson(2, self.n_samples),      # Pocos protocolos
            'temporal_consistency': np.random.beta(8, 2, self.n_samples)   # Patrones consistentes
        }

        return data

    def create_complete_dataset(self) -> pd.DataFrame:
        """Crea dataset balanceado con ambos tipos de tráfico"""
        internet_data = self.generate_internet_traffic()
        internal_data = self.generate_internal_traffic()

        # Crear DataFrames con labels
        df_internet = pd.DataFrame(internet_data)
        df_internet['label'] = 'internet'

        df_internal = pd.DataFrame(internal_data)
        df_internal['label'] = 'internal'

        # Combinar y mezclar
        complete_df = pd.concat([df_internet, df_internal], ignore_index=True)
        complete_df = complete_df.sample(frac=1).reset_index(drop=True)  # Shuffle

        print(f"✅ Dataset creado: {len(complete_df)} muestras")
        print(f"📊 Distribución: {complete_df['label'].value_counts().to_dict()}")

        return complete_df

    def save_dataset(self, filename: str):
        """Guarda dataset en formato JSON para reproducibilidad"""
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

# Generar dataset
if __name__ == "__main__":
    generator = TrafficSyntheticGenerator(n_samples=25000)
    generator.save_dataset("traffic_classification_dataset.json")