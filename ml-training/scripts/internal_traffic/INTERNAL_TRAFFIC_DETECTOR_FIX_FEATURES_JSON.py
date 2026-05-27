#!/usr/bin/env python3
"""
INTERNAL TRAFFIC DETECTOR - FIX FEATURES.JSON
Arregla el archivo de features faltante para el modelo interno
"""

import json
from pathlib import Path

def fix_internal_traffic_features():
    """Arregla el archivo de features del modelo interno"""
    model_dir = Path("../outputs/models/internal_traffic_detector_onnx_ready")

    if not model_dir.exists():
        print("❌ Directorio del modelo no encontrado")
        return

    # Features que debería tener el modelo interno (basado en el output anterior)
    features = [
        'sbytes', 'dbytes', 'total_bytes', 'byte_ratio',
        'is_common_internal_port', 'proto_tcp', 'proto_udp',
        'proto_icmp', 'hour_of_day', 'is_business_hours',
        'spkts', 'dpkts', 'total_packets', 'packet_imbalance'
    ]

    # Guardar archivo de features
    features_file = model_dir / "internal_traffic_detector_onnx_ready_features.json"
    with open(features_file, 'w') as f:
        json.dump(features, f, indent=2)

    print(f"✅ Archivo de features creado: {features_file}")
    print(f"📋 Features: {len(features)}")
    for feature in features:
        print(f"   - {feature}")

if __name__ == "__main__":
    print("🔧 ARREGLANDO ARCHIVO DE FEATURES DEL MODELO INTERNO")
    fix_internal_traffic_features()