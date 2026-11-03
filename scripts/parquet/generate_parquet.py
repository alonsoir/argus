#!/usr/bin/env python3
# aRGus NDR — Generador CSV -> Parquet (solo el CSV del firewall)
# [CSV-WRITER-RETIRE-D310] la mitad ml-detector se retiro con el CsvEventWriter (DAY310)
# Uso: python3 scripts/parquet/generate_parquet.py
# Makefile: make parquet-convert
import sys, os, csv, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyarrow as pa
import pyarrow.parquet as pq
from schemas import schema_firewall, FIREWALL_ACTION

# [FW-CSV-CLAVE-B2-D316] un CSV por clave HMAC: firewall_blocks-<AAAAMMDDTHHMMSSZ>-<huella>.csv (se leen todos, en orden)
FW_CSV_GLOB = "/vagrant/logs/firewall_logs/firewall_blocks-*.csv"
# [PARQUET-SIN-CSV-D316] decisión H1 b de Alonso: sin CSV del firewall se avisa, se borra el Parquet anterior (nunca se
# valida un dato caducado) y se termina bien; validate_roundtrip.py lo dice como SIN DATOS. El firewall solo escribe una
# fila cuando bloquea (DEBT-FW-CSV-SIN-FILAS-EN-GATE-001).
FW_PARQUET = "/vagrant/logs/parquet/firewall/firewall_blocks.parquet"
OUT_DIR     = "/vagrant/logs/parquet"

os.makedirs(f"{OUT_DIR}/firewall",    exist_ok=True)

def convert_firewall():
    out  = f"{OUT_DIR}/firewall/firewall_blocks.parquet"
    rows = {f.name: [] for f in schema_firewall}

    ficheros = sorted(glob.glob(FW_CSV_GLOB))
    if not ficheros:
        return None
    for ruta in ficheros:
        with open(ruta) as f:
            for cols in csv.reader(f):
                if len(cols) < 7:
                    continue
                rows["timestamp_utc_ns"].append(int(cols[0]) * 1_000_000)
                rows["anon_src_host_id"].append(cols[1])
                rows["anon_dst_host_id"].append(cols[2])
                rows["threat_label"].append(cols[3])
                rows["action"].append(FIREWALL_ACTION.get(cols[4], -1))
                rows["confidence"].append(float(cols[5]))
                rows["ed25519_sig"].append(cols[6])

    table = pa.table(rows, schema=schema_firewall)
    pq.write_table(table, out, compression="snappy")
    return table.num_rows, sum(os.path.getsize(r) for r in ficheros), os.path.getsize(out)

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║  aRGus NDR — Parquet Converter                          ║")
print("╚══════════════════════════════════════════════════════════╝")

resultado = convert_firewall()
if resultado is None:
    print(f"  [PARQUET-SIN-CSV] 0 ficheros {FW_CSV_GLOB}: el firewall solo escribe CSV cuando bloquea")
    print("  (ninguna acción de bloqueo desde que hay CSV por clave). No se genera Parquet.")
    if os.path.exists(FW_PARQUET):
        os.remove(FW_PARQUET)
        print(f"  Parquet anterior borrado para no validar datos caducados: {FW_PARQUET}")
    print()
    sys.exit(0)
fw_rows, fw_csv_b, fw_pq_b = resultado
fw_ratio = fw_csv_b / fw_pq_b if fw_pq_b else 0
print(f"  firewall    (all):  {fw_rows:>6} rows  {fw_csv_b:>9,}->{fw_pq_b:>8,} bytes  {fw_ratio:.1f}x")
print()
print(f"  Output: {OUT_DIR}")
print("  ✅ DONE")
print()
