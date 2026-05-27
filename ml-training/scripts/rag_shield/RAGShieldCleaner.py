#!/usr/bin/env python3
"""
RAG Shield Cleaner - Limpieza simple del proyecto
"""

import os
import shutil
import glob

def clean_project():
    """Limpia el proyecto moviendo archivos antiguos a carpeta archive"""

    print("🧹 LIMPIANDO PROYECTO RAG SHIELD")
    print("=" * 50)

    # Archivos esenciales que NO mover
    keep_files = [
        "RagSecurityShield.py",
        "rag_security_ultimate_model_20251121_134436.pkl",
        "rag_shield_ultimate_dataset_20251121_134125.json",
        "UltimateRAGShieldTrainer.py",
        "RAGShieldUltimateDataset.py",
        "RAGShieldCleaner.py"  # Este script
    ]

    # Crear directorio archive si no existe
    archive_dir = "archive_old_models"
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"📁 Creando directorio: {archive_dir}")

    # Contadores
    moved_count = 0
    keep_count = 0

    print("\n📋 MANTENIENDO ARCHIVOS ESENCIALES:")
    for file in keep_files:
        if os.path.exists(file):
            print(f"✅ {file}")
            keep_count += 1

    print(f"\n📦 MOVIENDO ARCHIVOS ANTIGUOS:")
    print("-" * 40)

    # Mover todos los .pkl excepto el esencial
    pkl_files = glob.glob("*.pkl")
    for pkl_file in pkl_files:
        if pkl_file not in keep_files:
            try:
                shutil.move(pkl_file, os.path.join(archive_dir, pkl_file))
                print(f"📦 {pkl_file}")
                moved_count += 1
            except Exception as e:
                print(f"⚠️  Error moviendo {pkl_file}: {e}")

    # Mover todos los .json excepto el esencial
    json_files = glob.glob("*.json")
    for json_file in json_files:
        if json_file not in keep_files:
            try:
                shutil.move(json_file, os.path.join(archive_dir, json_file))
                print(f"📦 {json_file}")
                moved_count += 1
            except Exception as e:
                print(f"⚠️  Error moviendo {json_file}: {e}")

    # Mover scripts antiguos
    old_scripts = [
        "SecureRAGShieldGenerator.py", "SecureRAGShieldTrainer.py", "SecureRAGShieldBalanced.py",
        "SecureRAGShieldClassifier.py", "SecureRAGShieldValidator.py", "SecureRagShieldFineTuning.py",
        "RAGShieldFoundation.py", "RAGShieldBalancedFinal.py", "RAGShieldOptimalFinal.py",
        "RAGShieldExpandedFoundation.py", "RAGShieldDatasetFixer.py", "RAGShieldFinalValidator.py",
        "RAGShieldUltimateValidator.py", "AdaptiveRAGShield.py", "FoundationRAGShieldTrainer.py",
        "ExpandedRAGShieldTrainer.py", "RagSecurityClassifierEnhanced.py"
    ]

    for script in old_scripts:
        if os.path.exists(script) and script not in keep_files:
            try:
                shutil.move(script, os.path.join(archive_dir, script))
                print(f"📦 {script}")
                moved_count += 1
            except Exception as e:
                print(f"⚠️  Error moviendo {script}: {e}")

    # Mover imágenes
    image_files = glob.glob("*.png")
    for image in image_files:
        try:
            shutil.move(image, os.path.join(archive_dir, image))
            print(f"📦 {image}")
            moved_count += 1
        except Exception as e:
            print(f"⚠️  Error moviendo {image}: {e}")

    print(f"\n📊 RESUMEN:")
    print(f"   - Archivos mantenidos: {keep_count}")
    print(f"   - Archivos movidos: {moved_count}")
    print(f"   - Directorio archive: {archive_dir}/")

    return keep_count, moved_count

def show_current_files():
    """Muestra los archivos actuales"""
    print(f"\n📁 ESTRUCTURA ACTUAL:")
    print("-" * 30)

    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    dirs = [d for d in os.listdir('.') if os.path.isdir(d)]

    print("📄 Archivos:")
    for file in sorted(files):
        print(f"   {file}")

    print("\n📁 Directorios:")
    for dir in sorted(dirs):
        print(f"   {dir}/")

def main():
    """Función principal"""
    print("🎯 LIMPIEZA RÁPIDA - RAG SHIELD")
    print("=" * 40)

    try:
        # Mostrar archivos antes
        print("📋 ARCHIVOS ANTES DE LIMPIEZA:")
        show_current_files()

        # Ejecutar limpieza
        keep_count, moved_count = clean_project()

        # Mostrar archivos después
        print(f"\n🎉 LIMPIEZA COMPLETADA!")
        print("=" * 30)
        print(f"✅ Mantenidos: {keep_count} archivos")
        print(f"📦 Movidos: {moved_count} archivos a archive_old_models/")

        print(f"\n📋 ARCHIVOS DESPUÉS DE LIMPIEZA:")
        show_current_files()

        print(f"\n🚀 PARA PRODUCCIÓN:")
        print("   RagSecurityShield.py + rag_security_ultimate_model_*.pkl")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()