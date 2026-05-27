#!/usr/bin/env python3
"""
Performance Metrics Plotter (macOS-compatible)
Genera gráficas con manejo explícito de decimales
"""

import sys
import locale
from pathlib import Path

# Forzar locale para punto decimal
locale.setlocale(locale.LC_NUMERIC, 'C')

try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # No GUI
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except ImportError as e:
    PLOTTING_AVAILABLE = False
    MISSING_MODULE = str(e).split("'")[1] if "'" in str(e) else "pandas/matplotlib"

def plot_cpu_usage(df, output_path):
    """Genera gráfica de uso de CPU"""
    fig, ax = plt.subplots(figsize=(14, 6))

    # Convert to numeric, coercing errors (like 'us.') to NaN
    sniffer_cpu = pd.to_numeric(df['sniffer_cpu'], errors='coerce')
    detector_cpu = pd.to_numeric(df['detector_cpu'], errors='coerce')
    system_cpu = pd.to_numeric(df['system_cpu'], errors='coerce')

    # Plot (NaN values will be skipped automatically)
    ax.plot(df.index, sniffer_cpu, label='Sniffer', linewidth=2, color='#1f77b4')
    ax.plot(df.index, detector_cpu, label='ml-detector', linewidth=2, color='#ff7f0e')
    ax.plot(df.index, system_cpu, label='System Total',
            linewidth=1, alpha=0.5, linestyle='--', color='#2ca02c')

    ax.set_title('CPU Usage Over Time', fontsize=16, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Usage (%)', fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # Set reasonable Y limits based on data (ignoring NaN)
    y_max = max(detector_cpu.max(), system_cpu.max()) * 1.2
    ax.set_ylim(-1, y_max)

    plt.tight_layout()
    plt.savefig(f'{output_path}/cpu_usage.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Generated: {output_path}/cpu_usage.png")

def plot_memory_usage(df, output_path):
    """Genera gráfica de uso de memoria"""
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(df.index, df['sniffer_rss'].astype(float), label='Sniffer RSS', linewidth=2, color='#1f77b4')
    ax.plot(df.index, df['detector_rss'].astype(float), label='ml-detector RSS', linewidth=2, color='#ff7f0e')

    ax.set_title('Memory Usage Over Time (RSS)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Memory (MB)', fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # Set reasonable Y limits
    y_max = df['detector_rss'].max() * 1.2
    ax.set_ylim(-5, y_max)

    plt.tight_layout()
    plt.savefig(f'{output_path}/memory_usage.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Generated: {output_path}/memory_usage.png")

def print_text_summary(cpu_df, mem_df):
    """Imprime resumen en texto"""
    print("\n" + "="*80)
    print("  PERFORMANCE SUMMARY")
    print("="*80)

    # Convert to numeric, coercing errors to NaN
    sniffer_cpu = pd.to_numeric(cpu_df['sniffer_cpu'], errors='coerce')
    detector_cpu = pd.to_numeric(cpu_df['detector_cpu'], errors='coerce')
    system_cpu = pd.to_numeric(cpu_df['system_cpu'], errors='coerce')
    sniffer_rss = pd.to_numeric(mem_df['sniffer_rss'], errors='coerce')
    detector_rss = pd.to_numeric(mem_df['detector_rss'], errors='coerce')

    print("\n📊 CPU USAGE:")
    print(f"  Sniffer:     avg={sniffer_cpu.mean():.1f}%  max={sniffer_cpu.max():.1f}%")
    print(f"  ml-detector: avg={detector_cpu.mean():.1f}%  max={detector_cpu.max():.1f}%")
    print(f"  System:      avg={system_cpu.mean():.1f}%  max={system_cpu.max():.1f}%")

    print("\n💾 MEMORY USAGE (RSS):")
    print(f"  Sniffer:     avg={sniffer_rss.mean():.1f}MB  max={sniffer_rss.max():.1f}MB")
    print(f"  ml-detector: avg={detector_rss.mean():.1f}MB  max={detector_rss.max():.1f}MB")

    print("\n📈 SAMPLES:")
    print(f"  Total samples: {len(cpu_df)}")
    print(f"  Duration: ~{len(cpu_df)*5/60:.0f} minutes")
    print("="*80 + "\n")

def main():
    if not PLOTTING_AVAILABLE:
        print(f"⚠️  Módulo '{MISSING_MODULE}' no disponible")
        print(f"   Instalar con: pip3 install pandas matplotlib")
        sys.exit(1)

    # Determinar directorio de métricas
    if len(sys.argv) >= 2:
        metrics_dir = Path(sys.argv[1])
    else:
        metrics_dir = Path('./performance_metrics')

    if not metrics_dir.exists():
        print(f"❌ Directorio no encontrado: {metrics_dir}")
        sys.exit(1)

    # Buscar archivos CSV más recientes
    cpu_files = sorted(metrics_dir.glob('cpu_*.csv'), reverse=True)
    mem_files = sorted(metrics_dir.glob('memory_*.csv'), reverse=True)

    if not cpu_files or not mem_files:
        print(f"❌ No se encontraron archivos de métricas en {metrics_dir}")
        sys.exit(1)

    print(f"📊 Procesando métricas de: {metrics_dir}")
    print(f"   CPU data: {cpu_files[0].name}")
    print(f"   Memory data: {mem_files[0].name}")
    print()

    # Cargar datos con manejo explícito de tipos
    try:
        # Leer CSV forzando punto decimal
        cpu_df = pd.read_csv(
            cpu_files[0],
            parse_dates=['timestamp'],
            index_col='timestamp',
            decimal='.',  # Forzar punto decimal
            thousands=None  # No usar separador de miles
        )

        mem_df = pd.read_csv(
            mem_files[0],
            parse_dates=['timestamp'],
            index_col='timestamp',
            decimal='.',
            thousands=None
        )

        # Verificar que los datos son numéricos
        print("🔍 Verificando datos cargados:")
        print(f"   CPU columns: {cpu_df.columns.tolist()}")
        print(f"   CPU dtypes: {cpu_df.dtypes.tolist()}")
        print(f"   Sample values - sniffer_cpu: {cpu_df['sniffer_cpu'].iloc[0]}")
        print(f"   Sample values - detector_mem: {cpu_df['detector_mem_mb'].iloc[0]}")
        print()

    except Exception as e:
        print(f"❌ Error leyendo CSVs: {e}")
        print("   Verifica que los CSVs tengan formato correcto")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Generar gráficas
    try:
        plot_cpu_usage(cpu_df, metrics_dir)
        plot_memory_usage(mem_df, metrics_dir)
        print_text_summary(cpu_df, mem_df)
        print(f"\n✅ Análisis completado")
        print(f"📁 Gráficas guardadas en: {metrics_dir}")
    except Exception as e:
        print(f"❌ Error generando gráficas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()