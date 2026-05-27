#!/usr/bin/env python3
"""
Auto-configuración para entrenamiento según RAM disponible
ml-training/scripts/check_system_config.py
"""

import sys
import json
from pathlib import Path

def get_memory_info():
    """Obtener información de memoria del sistema"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'used_gb': mem.used / (1024**3),
            'percent': mem.percent
        }
    except ImportError:
        print("⚠️  psutil no instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
        import psutil
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'used_gb': mem.used / (1024**3),
            'percent': mem.percent
        }

def recommend_config(mem_info):
    """Recomendar configuración según memoria disponible"""
    total_gb = mem_info['total_gb']
    available_gb = mem_info['available_gb']
    
    configs = []
    
    # Configuración conservadora (70% de memoria disponible)
    if available_gb >= 5:
        configs.append({
            'name': 'Large (Recomendado)',
            'sample_size': 800000,
            'estimated_memory_mb': 1200,
            'estimated_time_min': '15-20',
            'expected_accuracy': '98%+',
            'description': 'Dataset grande, excelentes métricas'
        })
    
    if available_gb >= 3:
        configs.append({
            'name': 'Medium (Recomendado)',
            'sample_size': 400000,
            'estimated_memory_mb': 600,
            'estimated_time_min': '8-12',
            'expected_accuracy': '97-98%',
            'description': 'Buen balance performance/tiempo'
        })
    
    if available_gb >= 2:
        configs.append({
            'name': 'Small',
            'sample_size': 200000,
            'estimated_memory_mb': 300,
            'estimated_time_min': '3-5',
            'expected_accuracy': '96-97%',
            'description': 'Rápido, métricas aceptables'
        })
    
    configs.append({
        'name': 'Tiny (Pruebas)',
        'sample_size': 50000,
        'estimated_memory_mb': 100,
        'estimated_time_min': '1-2',
        'expected_accuracy': '94-95%',
        'description': 'Solo para pruebas rápidas'
    })
    
    return configs

def check_dependencies():
    """Verificar dependencias instaladas"""
    deps = {
        'pandas': False,
        'numpy': False,
        'sklearn': False,
        'matplotlib': False,
        'seaborn': False,
        'joblib': False,
        'imblearn': False,
        'psutil': False
    }
    
    for dep in deps:
        try:
            if dep == 'sklearn':
                __import__('sklearn')
            elif dep == 'imblearn':
                __import__('imblearn')
            else:
                __import__(dep)
            deps[dep] = True
        except ImportError:
            pass
    
    return deps

def check_dataset():
    """Verificar que el dataset existe"""
    dataset_path = Path("datasets/CIC-DDoS-2019")
    
    if not dataset_path.exists():
        return {
            'exists': False,
            'files': 0,
            'message': f"Dataset no encontrado en: {dataset_path.absolute()}"
        }
    
    csv_files = list(dataset_path.rglob("*.csv"))
    
    return {
        'exists': True,
        'files': len(csv_files),
        'message': f"✅ {len(csv_files)} archivos CSV encontrados"
    }

def main():
    print("=" * 80)
    print("🔍 SYSTEM CONFIGURATION CHECK")
    print("=" * 80)
    
    # 1. Memoria
    print("\n📊 MEMORIA")
    print("-" * 80)
    mem_info = get_memory_info()
    print(f"  Total:     {mem_info['total_gb']:.2f} GB")
    print(f"  Usada:     {mem_info['used_gb']:.2f} GB ({mem_info['percent']:.1f}%)")
    print(f"  Disponible: {mem_info['available_gb']:.2f} GB")
    
    # 2. Configuraciones recomendadas
    print("\n🎯 CONFIGURACIONES RECOMENDADAS")
    print("-" * 80)
    configs = recommend_config(mem_info)
    
    for i, config in enumerate(configs, 1):
        print(f"\n{i}. {config['name']}")
        print(f"   Sample size: {config['sample_size']:,} flows")
        print(f"   Memoria estimada: ~{config['estimated_memory_mb']} MB")
        print(f"   Tiempo estimado: {config['estimated_time_min']} min")
        print(f"   Accuracy esperada: {config['expected_accuracy']}")
        print(f"   → {config['description']}")
    
    # 3. Dependencias
    print("\n📦 DEPENDENCIAS")
    print("-" * 80)
    deps = check_dependencies()
    
    all_installed = all(deps.values())
    
    for dep, installed in deps.items():
        status = "✅" if installed else "❌"
        print(f"  {status} {dep}")
    
    if not all_installed:
        print("\n⚠️  Faltan dependencias. Instalar con:")
        missing = [dep for dep, inst in deps.items() if not inst]
        if 'imblearn' in missing:
            print("  pip install imbalanced-learn")
            missing.remove('imblearn')
        if missing:
            print(f"  pip install {' '.join(missing)}")
    
    # 4. Dataset
    print("\n📂 DATASET")
    print("-" * 80)
    dataset_info = check_dataset()
    
    if dataset_info['exists']:
        print(f"  {dataset_info['message']}")
    else:
        print(f"  ❌ {dataset_info['message']}")
        print("  Descargar de: https://www.unb.ca/cic/datasets/ddos-2019.html")
    
    # 5. Recomendación final
    print("\n" + "=" * 80)
    print("💡 RECOMENDACIÓN")
    print("=" * 80)
    
    if not all_installed:
        print("\n❌ Instala las dependencias faltantes primero")
        return 1
    
    if not dataset_info['exists']:
        print("\n❌ Descarga el dataset CIC-DDoS-2019 primero")
        return 1
    
    # Recomendar la mejor config
    recommended = configs[0] if configs else None
    
    if recommended:
        print(f"\n✅ Configuración recomendada: {recommended['name']}")
        print(f"\nEdita train_level2_ddos_binary_optimized.py línea 30:")
        print(f"\n  SAMPLE_SIZE = {recommended['sample_size']}  # {recommended['description']}")
        print(f"\nY ejecuta:")
        print(f"  python scripts/train_level2_ddos_binary_optimized.py")
    else:
        print("\n⚠️  RAM insuficiente (<2GB disponible)")
        print("  Opciones:")
        print("  1. Aumentar RAM de la VM (editar Vagrantfile)")
        print("  2. Cerrar otros procesos")
        print("  3. Entrenar en el host macOS")
    
    # Guardar config recomendada en JSON
    if recommended:
        config_file = Path("outputs/recommended_config.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump({
                'memory_info': mem_info,
                'recommended_config': recommended,
                'all_configs': configs
            }, f, indent=2)
        
        print(f"\n📝 Config guardada en: {config_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
