# create_guaranteed_ransomware.py
import pandas as pd
import numpy as np
import os

def create_guaranteed_ransomware():
    """Crear datasets con ransomware GARANTIZADO y patrones claros"""
    print("🎯 CREANDO DATASETS CON RANSOMWARE GARANTIZADO...")

    # Features universales basadas en comportamiento real
    features = [
        'io_intensity',           # Intensidad de operaciones I/O
        'entropy',                # Nivel de entropía (encriptación)
        'resource_usage',         # Uso de recursos (CPU, memoria)
        'network_activity',       # Actividad de red
        'file_operations',        # Operaciones de archivo
        'process_anomaly',        # Anomalías de proceso
        'temporal_pattern',       # Patrón temporal
        'access_frequency',       # Frecuencia de acceso
        'data_volume',            # Volumen de datos
        'behavior_consistency'    # Consistencia de comportamiento
    ]

    np.random.seed(42)

    datasets_config = {
        'network': {'size': 1000, 'base_multiplier': 1.0},
        'files': {'size': 800, 'base_multiplier': 0.8},
        'processes': {'size': 1200, 'base_multiplier': 1.2}
    }

    for domain, config in datasets_config.items():
        n_samples = config['size']
        base_multiplier = config['base_multiplier']

        # 🔥 GARANTIZAR que el 20-30% sean ransomware
        n_ransomware = int(n_samples * np.random.uniform(0.2, 0.3))
        n_benign = n_samples - n_ransomware

        print(f"🎯 {domain}: {n_ransomware} ransomware, {n_benign} benigno")

        data = {feature: [] for feature in features}
        labels = []

        # GENERAR COMPORTAMIENTO BENIGNO (70-80%)
        for _ in range(n_benign):
            for feature in features:
                # Comportamiento normal: valores bajos/medios
                if feature in ['io_intensity', 'resource_usage', 'network_activity']:
                    data[feature].append(np.random.beta(2, 5) * base_multiplier)
                elif feature == 'entropy':
                    data[feature].append(np.random.beta(1, 3) * base_multiplier)  # Entropía baja
                else:
                    data[feature].append(np.random.beta(2, 4) * base_multiplier)
            labels.append(0)

        # GENERAR COMPORTAMIENTO RANSOMWARE (20-30%)
        for _ in range(n_ransomware):
            for feature in features:
                if feature == 'io_intensity':
                    # Ransomware: alta intensidad I/O
                    data[feature].append(np.random.beta(5, 2) * base_multiplier * 1.5)
                elif feature == 'entropy':
                    # Ransomware: alta entropía (encriptación)
                    data[feature].append(np.random.beta(4, 1) * base_multiplier * 2.0)
                elif feature == 'resource_usage':
                    # Ransomware: alto uso de recursos
                    data[feature].append(np.random.beta(4, 2) * base_multiplier * 1.8)
                elif feature == 'network_activity':
                    # Ransomware: alta actividad de red
                    data[feature].append(np.random.beta(3, 2) * base_multiplier * 1.6)
                else:
                    # Otros features con valores elevados
                    data[feature].append(np.random.beta(3, 3) * base_multiplier * 1.3)
            labels.append(1)

        # Crear DataFrame
        df = pd.DataFrame(data)
        df['is_ransomware'] = labels

        # 🔥 MEZCLAR LOS DATOS
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        # Añadir algo de ruido/solapamiento (10% de muestras)
        noise_indices = np.random.choice(len(df), size=int(len(df) * 0.1), replace=False)
        for idx in noise_indices:
            if df.loc[idx, 'is_ransomware'] == 0:
                # Hacer que algunos benignos parezcan ransomware
                if np.random.random() < 0.3:
                    df.loc[idx, 'io_intensity'] *= 1.8
                    df.loc[idx, 'entropy'] *= 2.0
            else:
                # Hacer que algunos ransomware parezcan benignos (sigilosos)
                if np.random.random() < 0.2:
                    df.loc[idx, 'io_intensity'] *= 0.5
                    df.loc[idx, 'resource_usage'] *= 0.6

        # Guardar
        filename = f"data/{domain}_guaranteed.csv"
        df.to_csv(filename, index=False)

        # Verificación
        actual_ransomware = df['is_ransomware'].sum()
        print(f"✅ {domain}: {len(df)} total, {actual_ransomware} ransomware ({actual_ransomware/len(df):.1%})")

    print("🎯 DATASETS CON RANSOMWARE GARANTIZADO CREADOS EXITOSAMENTE")

def analyze_datasets():
    """Analizar los datasets creados"""
    print("\n🔍 ANALIZANDO PATRONES DE DATASETS...")

    domains = ['network', 'files', 'processes']

    for domain in domains:
        df = pd.read_csv(f"data/{domain}_guaranteed.csv")

        ransom = df[df['is_ransomware'] == 1]
        benign = df[df['is_ransomware'] == 0]

        print(f"\n📊 {domain.upper()}:")
        print(f"   Total: {len(df)}, Ransomware: {len(ransom)}, Benigno: {len(benign)}")

        # Comparar características clave
        key_features = ['io_intensity', 'entropy', 'resource_usage']

        for feature in key_features:
            r_mean = ransom[feature].mean()
            b_mean = benign[feature].mean()
            ratio = r_mean / b_mean if b_mean > 0 else float('inf')
            print(f"   {feature}: Ransomware={r_mean:.3f}, Benigno={b_mean:.3f} (Ratio: {ratio:.2f}x)")

if __name__ == "__main__":
    create_guaranteed_ransomware()
    analyze_datasets()