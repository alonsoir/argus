#!/usr/bin/env python3
import json
import os
import sys

def verify_config():
    config_path = "../config/rag-config.json"

    if not os.path.exists(config_path):
        print(f"❌ ERROR: No se encuentra {config_path}")
        print("💡 Ejecuta desde: cd /vagrant/rag/build")
        return False

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_fields = [
            "etcd.host", "etcd.port",
            "rag.host", "rag.port", "rag.model_name", "rag.embedding_dimension"
        ]

        # Verificar campos requeridos
        missing_fields = []
        for field in required_fields:
            keys = field.split('.')
            value = config
            for key in keys:
                if key not in value:
                    missing_fields.append(field)
                    break
                value = value[key]

        if missing_fields:
            print("❌ ERROR: Campos faltantes en configuración:")
            for field in missing_fields:
                print(f"   - {field}")
            return False

        print("✅ Configuración válida: todos los campos requeridos presentes")
        print(f"   RAG: {config['rag']['host']}:{config['rag']['port']}")
        print(f"   etcd: {config['etcd']['host']}:{config['etcd']['port']}")
        return True

    except Exception as e:
        print(f"❌ ERROR leyendo configuración: {e}")
        return False

if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)