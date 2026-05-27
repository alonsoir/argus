# create_test_datasets.py
import pandas as pd
import numpy as np
import os

# ==================== FUNCIONES AUXILIARES ====================
def calculate_entropy_vectorized(data):
    """Calcular entropía para cada fila de la matriz"""
    data_normalized = data / (np.sum(data, axis=1, keepdims=True) + 1e-10)
    return -np.sum(data_normalized * np.log2(data_normalized + 1e-10), axis=1)

def calculate_iqr_vectorized(data):
    """Calcular IQR para cada fila"""
    q1 = np.percentile(data, 25, axis=1)
    q3 = np.percentile(data, 75, axis=1)
    return q3 - q1

def calculate_skewness_vectorized(data):
    """Calcular asimetría aproximada"""
    mean = np.mean(data, axis=1)
    std = np.std(data, axis=1)
    return np.mean((data - mean[:, np.newaxis])**3, axis=1) / (std**3 + 1e-10)

def calculate_kurtosis_vectorized(data):
    """Calcular curtosis aproximada"""
    mean = np.mean(data, axis=1)
    std = np.std(data, axis=1)
    return np.mean((data - mean[:, np.newaxis])**4, axis=1) / (std**4 + 1e-10)

# ==================== GENERACIÓN DE DATASETS ====================
def create_test_dataset_network():
    """Crear dataset sintético de dominio de red con ransomware REAL"""
    np.random.seed(42)
    n_samples = 1000

    # Generar métricas base específicas de red
    base_metrics = {
        'packet_size': np.random.exponential(500, n_samples),
        'flow_duration': np.random.gamma(2, 2, n_samples),
        'src_bytes': np.random.lognormal(6, 2, n_samples),
        'dst_bytes': np.random.lognormal(6, 2, n_samples),
    }

    # Calcular features universales a partir de métricas base
    universal_data = {}

    # Para cada métrica base, calcular características universales
    for metric_name, metric_values in base_metrics.items():
        universal_data[f'{metric_name}_mean'] = np.full(n_samples, metric_values.mean())
        universal_data[f'{metric_name}_std'] = np.full(n_samples, metric_values.std())
        universal_data[f'{metric_name}_max'] = np.full(n_samples, metric_values.max())
        universal_data[f'{metric_name}_min'] = np.full(n_samples, metric_values.min())
        universal_data[f'{metric_name}_median'] = np.full(n_samples, np.median(metric_values))

    # Features universales agregadas
    all_metrics = np.column_stack(list(base_metrics.values()))
    universal_data['entropy'] = calculate_entropy_vectorized(all_metrics)
    universal_data['variance'] = np.var(all_metrics, axis=1)
    universal_data['cv'] = np.std(all_metrics, axis=1) / (np.mean(all_metrics, axis=1) + 1e-10)
    universal_data['iqr'] = calculate_iqr_vectorized(all_metrics)
    universal_data['skewness'] = calculate_skewness_vectorized(all_metrics)
    universal_data['kurtosis'] = calculate_kurtosis_vectorized(all_metrics)

    # Crear DataFrame con features universales
    df = pd.DataFrame(universal_data)

    # 🔥 PATRÓN MEJORADO DE RANSOMWARE - MÁS REALISTA
    # Ransomware típicamente tiene: alto tráfico, conexiones cortas, asimetría
    ransomware_probability = (
        # Alto tamaño de paquetes (posible encriptación)
            (base_metrics['packet_size'] > 800) * 0.3 +
            # Flujos muy cortos (comunicación rápida con C&C)
            (base_metrics['flow_duration'] < 0.5) * 0.3 +
            # Alta asimetría bytes src/dst (descarga de claves/encriptación)
            (base_metrics['src_bytes'] / (base_metrics['dst_bytes'] + 1) > 8) * 0.4
    )

    # Normalizar probabilidad y generar labels
    ransomware_probability = ransomware_probability / ransomware_probability.max()
    ransomware_labels = np.random.binomial(1, ransomware_probability * 0.6)  # 60% de probabilidad máxima

    df['is_ransomware'] = ransomware_labels

    # Guardar
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/ugransome_processed.csv', index=False)
    print(f"✅ Dataset red creado: {len(df)} muestras, {df['is_ransomware'].sum()} ransomware")
    return df

def create_test_dataset_files():
    """Crear dataset sintético de dominio de archivos con ransomware REAL"""
    np.random.seed(43)
    n_samples = 800

    # Métricas base específicas de archivos
    base_metrics = {
        'file_size': np.random.lognormal(10, 2, n_samples),
        'entropy_value': np.random.uniform(0, 8, n_samples),
        'modification_rate': np.random.exponential(0.5, n_samples),
        'encryption_indicators': np.random.beta(0.5, 2, n_samples),
    }

    # MISMA estructura de features universales
    universal_data = {}

    for metric_name, metric_values in base_metrics.items():
        universal_data[f'{metric_name}_mean'] = np.full(n_samples, metric_values.mean())
        universal_data[f'{metric_name}_std'] = np.full(n_samples, metric_values.std())
        universal_data[f'{metric_name}_max'] = np.full(n_samples, metric_values.max())
        universal_data[f'{metric_name}_min'] = np.full(n_samples, metric_values.min())
        universal_data[f'{metric_name}_median'] = np.full(n_samples, np.median(metric_values))

    # MISMAS features universales agregadas
    all_metrics = np.column_stack(list(base_metrics.values()))
    universal_data['entropy'] = calculate_entropy_vectorized(all_metrics)
    universal_data['variance'] = np.var(all_metrics, axis=1)
    universal_data['cv'] = np.std(all_metrics, axis=1) / (np.mean(all_metrics, axis=1) + 1e-10)
    universal_data['iqr'] = calculate_iqr_vectorized(all_metrics)
    universal_data['skewness'] = calculate_skewness_vectorized(all_metrics)
    universal_data['kurtosis'] = calculate_kurtosis_vectorized(all_metrics)

    df = pd.DataFrame(universal_data)

    # 🔥 PATRÓN MEJORADO DE RANSOMWARE PARA ARCHIVOS
    # Ransomware en archivos: alta entropía (encriptación), muchas modificaciones
    ransomware_probability = (
        # Alta entropía (contenido encriptado)
            (base_metrics['entropy_value'] > 6.5) * 0.4 +
            # Alta tasa de modificación (sobreescritura de archivos)
            (base_metrics['modification_rate'] > 1.5) * 0.4 +
            # Indicadores de encriptación
            (base_metrics['encryption_indicators'] > 0.6) * 0.2
    )

    ransomware_probability = ransomware_probability / ransomware_probability.max()
    ransomware_labels = np.random.binomial(1, ransomware_probability * 0.7)  # 70% de probabilidad máxima

    df['is_ransomware'] = ransomware_labels

    df.to_csv('data/ransomware_2024_processed.csv', index=False)
    print(f"✅ Dataset archivos creado: {len(df)} muestras, {df['is_ransomware'].sum()} ransomware")
    return df

def create_test_dataset_processes():
    """Crear dataset sintético de dominio de procesos con ransomware REAL"""
    np.random.seed(44)
    n_samples = 1200

    # Métricas base específicas de procesos
    base_metrics = {
        'cpu_usage': np.random.exponential(5, n_samples),
        'memory_usage': np.random.lognormal(3, 1, n_samples),
        'io_operations': np.random.poisson(50, n_samples),
        'network_connections': np.random.poisson(10, n_samples),
    }

    # MISMA estructura de features
    universal_data = {}

    for metric_name, metric_values in base_metrics.items():
        universal_data[f'{metric_name}_mean'] = np.full(n_samples, metric_values.mean())
        universal_data[f'{metric_name}_std'] = np.full(n_samples, metric_values.std())
        universal_data[f'{metric_name}_max'] = np.full(n_samples, metric_values.max())
        universal_data[f'{metric_name}_min'] = np.full(n_samples, metric_values.min())
        universal_data[f'{metric_name}_median'] = np.full(n_samples, np.median(metric_values))

    # MISMAS features universales
    all_metrics = np.column_stack(list(base_metrics.values()))
    universal_data['entropy'] = calculate_entropy_vectorized(all_metrics)
    universal_data['variance'] = np.var(all_metrics, axis=1)
    universal_data['cv'] = np.std(all_metrics, axis=1) / (np.mean(all_metrics, axis=1) + 1e-10)
    universal_data['iqr'] = calculate_iqr_vectorized(all_metrics)
    universal_data['skewness'] = calculate_skewness_vectorized(all_metrics)
    universal_data['kurtosis'] = calculate_kurtosis_vectorized(all_metrics)

    df = pd.DataFrame(universal_data)

    # 🔥 PATRÓN MEJORADO DE RANSOMWARE PARA PROCESOS
    # Ransomware en procesos: alto CPU, mucho I/O, muchas conexiones
    ransomware_probability = (
        # Alto uso de CPU (encriptación)
            (base_metrics['cpu_usage'] > 12) * 0.4 +
            # Muchas operaciones I/O (lectura/escritura de archivos)
            (base_metrics['io_operations'] > 80) * 0.3 +
            # Muchas conexiones de red (C&C, propagación)
            (base_metrics['network_connections'] > 15) * 0.3
    )

    ransomware_probability = ransomware_probability / ransomware_probability.max()
    ransomware_labels = np.random.binomial(1, ransomware_probability * 0.5)  # 50% de probabilidad máxima

    df['is_ransomware'] = ransomware_labels

    df.to_csv('data/process_data_processed.csv', index=False)
    print(f"✅ Dataset procesos creado: {len(df)} muestras, {df['is_ransomware'].sum()} ransomware")
    return df

def create_all_test_datasets():
    """Crear todos los datasets con ransomware REAL"""
    print("🛠️ CREANDO DATASETS CON RANSOMWARE REAL...")
    df_network = create_test_dataset_network()
    df_files = create_test_dataset_files()
    df_processes = create_test_dataset_processes()

    # Verificar que tienen ransomware
    total_ransomware = (
            df_network['is_ransomware'].sum() +
            df_files['is_ransomware'].sum() +
            df_processes['is_ransomware'].sum()
    )

    print(f"🎯 TOTAL RANSOMWARE GENERADO: {total_ransomware} muestras")
    print(f"📊 Distribución - Network: {df_network['is_ransomware'].sum()}, "
          f"Files: {df_files['is_ransomware'].sum()}, "
          f"Processes: {df_processes['is_ransomware'].sum()}")

    return df_network, df_files, df_processes

if __name__ == "__main__":
    create_all_test_datasets()