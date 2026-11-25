#!/usr/bin/env python3
# aRGus NDR — Validacion roundtrip Parquet (solo el del firewall)
# [CSV-WRITER-RETIRE-D310] la mitad ml-detector se retiro con el CsvEventWriter (DAY310)
# Uso: python3 scripts/parquet/validate_roundtrip.py
# Makefile: make test-parquet (depende de parquet-convert)
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import pyarrow.parquet as pq
from schemas import schema_firewall
from filas_ts import fallos_ts  # [PARQUET-SIN-NUMPY-D337] sin numpy, solo pyarrow.compute

OUT_DIR = "/vagrant/logs/parquet"
errors  = 0

def check(condition, msg):
    global errors
    if not condition:
        print(f"  FAIL: {msg}")
        errors += 1

# [PARQUET-ALLROWS-D296] DEBT-PARQUET-VALIDATOR-FIRST-ROW-001: TODAS las filas, no solo la [0].
# [PARQUET-SIN-NUMPY-D337] La comprobación (con TS_MIN_NS y TS_FUTURE_MARGIN_NS) está en filas_ts.py, solo con
# pyarrow.compute; sus tests, en test_filas_ts.py (make test-parquet los corre antes que esto).
def check_all_rows(name, col, ms_multiple=False):
    for msg in fallos_ts(name, col, time.time_ns(), ms_multiple):
        check(False, msg)

fw_path = f"{OUT_DIR}/firewall/firewall_blocks.parquet"
# [PARQUET-SIN-CSV-D316] decisión H1 b de Alonso: sin ningún CSV del firewall no hay nada que validar y se dice así (rc 0).
# Si hay CSV y falta el Parquet, es un fallo.
FW_CSV_GLOB = "/vagrant/logs/firewall_logs/firewall_blocks-*.csv"
if not os.path.exists(fw_path) and not glob.glob(FW_CSV_GLOB):
    print()
    print("  [PARQUET-SIN-DATOS] firewall: 0 ficheros firewall_blocks-*.csv, nada que validar (no es un PASSED).")
    print("  El firewall solo escribe CSV cuando bloquea: DEBT-FW-CSV-SIN-FILAS-EN-GATE-001.")
    print()
    sys.exit(0)
check(os.path.exists(fw_path), "firewall_blocks.parquet not found (hay CSV del firewall)")
if os.path.exists(fw_path):
    t = pq.read_table(fw_path)
    check(t.schema.equals(schema_firewall), "firewall: schema mismatch")
    check(t.num_rows > 0, "firewall: empty table")
    check_all_rows("firewall", t["timestamp_utc_ns"], ms_multiple=True)  # [PARQUET-ALLROWS-D296]

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║  aRGus NDR — Parquet Roundtrip Validation               ║")
print("╚══════════════════════════════════════════════════════════╝")
print(f"  firewall files validados:    1")
if errors == 0:
    print("  ROUNDTRIP PASSED")
else:
    print(f"  {errors} ASSERTION(S) FAILED")
    sys.exit(1)
print()
