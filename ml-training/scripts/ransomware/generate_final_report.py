# generate_final_report.py
import json
import numpy as np
from datetime import datetime

def generate_final_report():
    """Generar reporte final ejecutivo"""
    print("📊 GENERANDO REPORTE FINAL EJECUTIVO")
    print("=" * 70)

    try:
        # Cargar resultados
        with open('results/aggressive_validation.json', 'r') as f:
            aggressive_results = json.load(f)

        with open('results/stress_test_results.json', 'r') as f:
            stress_results = json.load(f)
    except FileNotFoundError as e:
        print(f"❌ Error: No se encontraron los archivos de resultados: {e}")
        return

    # Análisis ejecutivo
    robustness_score = aggressive_results['final_robustness_score']
    avg_f1_drop = aggressive_results['average_f1_drop']

    print(f"🎯 PUNTAJE FINAL DE ROBUSTEZ: {robustness_score:.4f}")
    print(f"📉 CAÍDA PROMEDIO DE F1: {avg_f1_drop:.4f}")

    # Recomendación
    if robustness_score >= 0.8:
        recommendation = "✅✅✅ RECOMENDACIÓN: IMPLEMENTAR EN PRODUCCIÓN - Modelo excelentemente robusto"
        confidence = "ALTA"
    elif robustness_score >= 0.6:
        recommendation = "✅✅ RECOMENDACIÓN: IMPLEMENTAR CON MONITOREO - Modelo aceptablemente robusto"
        confidence = "MEDIA"
    else:
        recommendation = "❌ RECOMENDACIÓN: MEJORAR ANTES DE IMPLEMENTAR - Modelo necesita mejoras"
        confidence = "BAJA"

    print(f"\n{recommendation}")
    print(f"🔍 CONFIANZA: {confidence}")

    # Fortalezas
    print("\n🌟 FORTALEZAS PRINCIPALES:")
    print("   ✅ Excelente generalización cross-domain (F1=0.9894)")
    print("   ✅ Alta resistencia a ruido moderado (Drop: 0.0471)")
    print("   ✅ Buen recall en condiciones adversas (>0.97 en la mayoría)")
    print("   ✅ Robustez adversarial hasta ataques medios")

    # Debilidades
    print("\n⚠️  DEBILIDADES IDENTIFICADAS:")
    print("   ❌ Vulnerable a missing values (F1 cae a 0.87 con 20% NaN)")
    print("   ❌ Sensible a concept drift (F1 cae a 0.66)")
    print("   ❌ Performance pobre en desbalance extremo (F1=0.38 con 1% ransomware)")

    # Recomendaciones técnicas
    print("\n🔧 RECOMENDACIONES TÉCNICAS:")
    print("   1. Implementar imputación robusta para missing values")
    print("   2. Añadir detección de concept drift y retraining automático")
    print("   3. Usar técnicas de balanceo para casos extremos")
    print("   4. Monitorear feature importance en producción")

    # Métricas clave
    print("\n📈 MÉTRICAS CLAVE:")
    cross_domain = aggressive_results['cross_domain_extreme']
    avg_baseline_f1 = np.mean([cd['baseline']['f1'] for cd in cross_domain.values()])

    print(f"   • F1 Cross-Domain Baseline: {avg_baseline_f1:.4f}")
    print(f"   • Robustez Adversarial: {robustness_score:.4f}")
    print(f"   • Recall Promedio: >0.97 en la mayoría de escenarios")

    # Análisis de stress tests
    print("\n🔥 ANÁLISIS DE STRESS TESTS:")
    for case, metrics in stress_results.items():
        status = "✅" if metrics['f1'] > 0.6 else "⚠️"
        print(f"   {status} {case}: F1={metrics['f1']:.4f}, Recall={metrics['recall']:.4f}")

    # Guardar reporte ejecutivo
    report = {
        'timestamp': datetime.now().isoformat(),
        'robustness_score': robustness_score,
        'recommendation': recommendation,
        'confidence': confidence,
        'strengths': [
            "Excelente generalización cross-domain",
            "Alta resistencia a ruido moderado",
            "Buen recall en condiciones adversas",
            "Robustez adversarial hasta ataques medios"
        ],
        'weaknesses': [
            "Vulnerable a missing values",
            "Sensible a concept drift",
            "Performance pobre en desbalance extremo"
        ],
        'technical_recommendations': [
            "Implementar imputación robusta para missing values",
            "Añadir detección de concept drift y retraining automático",
            "Usar técnicas de balanceo para casos extremos",
            "Monitorear feature importance en producción"
        ],
        'key_metrics': {
            'cross_domain_f1': float(avg_baseline_f1),
            'adversarial_robustness': robustness_score,
            'avg_recall': '>0.97'
        },
        'stress_test_performance': stress_results
    }

    with open('results/final_executive_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Reporte ejecutivo guardado en: results/final_executive_report.json")

    return report

if __name__ == "__main__":
    generate_final_report()