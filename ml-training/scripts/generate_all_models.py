# /vagrant/ml-training/scripts/generate_all_models.py
import os
import subprocess
import sys

def generate_all_models():
    """Generar todos los headers C++ para ml-detector"""
    print("🚀 GENERANDO TODOS LOS MODELOS ML...")

    scripts = [
        # Modelo, Script, Descripción
        ("ddos_detection", "generate_ddos_inline.py", "🛡️ DDoS Detection"),
        ("external_traffic", "generate_traffic_cpp_forest.py", "🌐 External Traffic"),
        ("internal_traffic", "generate_internal_inline.py", "🏠 Internal Traffic"),
        ("ransomware", "extract_full_forest.py", "💰 Ransomware")
    ]

    for model_dir, script_name, description in scripts:
        script_path = os.path.join(model_dir, script_name)
        print(f"\n{description}")
        print("=" * 50)

        if os.path.exists(script_path):
            print(f"📁 Ejecutando: {script_path}")
            try:
                # Cambiar al directorio del modelo
                original_dir = os.getcwd()
                os.chdir(model_dir)

                # Ejecutar script
                result = subprocess.run([sys.executable, script_name],
                                        capture_output=True, text=True)

                if result.returncode == 0:
                    print("✅ GENERACIÓN EXITOSA")
                    if result.stdout:
                        print(f"   Output: {result.stdout.strip()}")
                else:
                    print(f"❌ ERROR en ejecución:")
                    print(f"   {result.stderr.strip()}")

                # Volver al directorio original
                os.chdir(original_dir)

            except Exception as e:
                print(f"❌ ERROR: {e}")
        else:
            print(f"⚠️  Script no encontrado: {script_path}")
            print("   Creando script básico...")
            create_basic_generator(model_dir, script_name)

    print("\n🎉 GENERACIÓN COMPLETADA")
    verify_headers()

def create_basic_generator(model_dir, script_name):
    """Crear un script generador básico si no existe"""
    # Implementación para crear script básico
    pass

def verify_headers():
    """Verificar que todos los headers se generaron"""
    print("\n🔍 VERIFICANDO HEADERS GENERADOS...")

    headers = [
        "/vagrant/ml-detector/src/ddos_trees_inline.hpp",
        "/vagrant/ml-detector/src/traffic_trees_inline.hpp",
        "/vagrant/ml-detector/src/internal_trees_inline.hpp",
        "/vagrant/ml-detector/src/forest_trees_inline.hpp"
    ]

    for header in headers:
        if os.path.exists(header):
            print(f"✅ {os.path.basename(header)}")
        else:
            print(f"❌ {os.path.basename(header)} - FALTANTE")

if __name__ == "__main__":
    generate_all_models()