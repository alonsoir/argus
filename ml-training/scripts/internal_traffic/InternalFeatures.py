# ml-training-scripts/internal_traffic/InternalFeatures.py
INTERNAL_FEATURES = [
    # KERNEL SPACE
    "internal_connection_rate",       # Conexiones entre hosts internos/seg
    "service_port_consistency",       # Consistencia en puertos de servicio
    "protocol_regularity",            # Regularidad en protocolos internos
    "packet_size_consistency",        # Consistencia en tamaños de paquete
    "connection_duration_std",        # Desviación en duración de conexiones

    # USER SPACE
    "lateral_movement_score",         # Patrones de movimiento entre segmentos
    "service_discovery_patterns",     # Patrones de descubrimiento de servicios
    "data_exfiltration_indicators",   # Indicadores de exfiltración
    "temporal_anomaly_score",         # Anomalías temporales en tráfico interno
    "access_pattern_entropy"          # Entropía en patrones de acceso
]