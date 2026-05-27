#!/usr/bin/env python3
"""
Fix CPU CSV with specific known structure
Structure: timestamp, sniffer_cpu, sniffer_mem (split), detector_cpu, detector_mem (split), system_cpu (split), system_mem (split)
"""

from pathlib import Path

def fix_cpu_csv(csv_file):
    """Fix CPU CSV with known 12-field to 7-field structure"""

    print(f"🔧 Arreglando {csv_file.name}...")

    with open(csv_file, 'r') as f:
        lines = f.readlines()

    if not lines:
        print("   ❌ Archivo vacío")
        return False

    # Keep header as-is
    header = lines[0].strip()
    fixed_lines = [header + '\n']

    errors = 0

    for line_num, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue

        parts = line.split(',')

        # If already 7 fields, keep as-is
        if len(parts) == 7:
            fixed_lines.append(line + '\n')
            continue

        # If not 11 fields, we can't fix it
        if len(parts) != 11:
            print(f"   ⚠️  Line {line_num}: Expected 11 fields, got {len(parts)}")
            errors += 1
            if errors > 10:
                print(f"   ❌ Demasiados errores, abortando")
                return False
            continue

        # Parse 11-field structure into 7 fields
        try:
            timestamp = parts[0]
            sniffer_cpu = parts[1]  # Already decimal format (0.0)
            sniffer_mem = f"{parts[2]}.{parts[3]}"  # Merge 4,5625 → 4.5625
            detector_cpu = parts[4]  # Already decimal format (6.6)
            detector_mem = f"{parts[5]}.{parts[6]}"  # Merge 139,281 → 139.281
            system_cpu = f"{parts[7]}.{parts[8]}"  # Merge 25,0 → 25.0
            system_mem = f"{parts[9]}.{parts[10]}"  # Merge 7,3 → 7.3

            fixed_line = f"{timestamp},{sniffer_cpu},{sniffer_mem},{detector_cpu},{detector_mem},{system_cpu},{system_mem}\n"
            fixed_lines.append(fixed_line)

        except Exception as e:
            print(f"   ⚠️  Line {line_num}: Error parsing: {e}")
            errors += 1
            continue

    # Write fixed file
    with open(csv_file, 'w') as f:
        f.writelines(fixed_lines)

    print(f"   ✅ Arreglado: {len(fixed_lines)-1} líneas, {errors} errores")
    return True

def main():
    metrics_dir = Path("performance_metrics")
    cpu_file = metrics_dir / "cpu_20251026_085315.csv"

    if not cpu_file.exists():
        print(f"❌ Archivo no encontrado: {cpu_file}")
        return

    # First, restore from backup
    backup = cpu_file.with_suffix('.csv.bak')
    if backup.exists():
        print("📦 Restaurando desde backup...")
        import shutil
        shutil.copy(backup, cpu_file)
        print("   ✅ Restaurado\n")

    # Fix
    if fix_cpu_csv(cpu_file):
        print("\n" + "="*80)
        print("✅ CPU CSV arreglado")
        print("="*80)
        print("\nPrimeras 5 líneas:")
        print("-"*80)

        with open(cpu_file) as f:
            for i, line in enumerate(f):
                if i < 5:
                    print(line.rstrip())
                else:
                    break

        print("-"*80)

        # Verify with pandas
        try:
            import pandas as pd
            df = pd.read_csv(cpu_file)
            print(f"\n📊 Verificación con pandas:")
            print(f"   Filas: {len(df)}")
            print(f"   Columnas: {df.columns.tolist()}")
            print(f"\n   Sniffer CPU: avg={df['sniffer_cpu'].mean():.1f}% max={df['sniffer_cpu'].max():.1f}%")
            print(f"   Sniffer MEM: avg={df['sniffer_mem_mb'].mean():.1f}MB max={df['sniffer_mem_mb'].max():.1f}MB")
            print(f"   Detector CPU: avg={df['detector_cpu'].mean():.1f}% max={df['detector_cpu'].max():.1f}%")
            print(f"   Detector MEM: avg={df['detector_mem_mb'].mean():.1f}MB max={df['detector_mem_mb'].max():.1f}MB")
            print(f"\n   ✅ Pandas puede leer el archivo correctamente")
        except Exception as e:
            print(f"\n   ⚠️  Error verificando con pandas: {e}")

if __name__ == '__main__':
    main()