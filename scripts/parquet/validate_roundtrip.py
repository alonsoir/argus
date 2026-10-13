#!/usr/bin/env python3
# aRGus NDR — Validacion roundtrip Parquet
# Uso: python3 scripts/parquet/validate_roundtrip.py
# Makefile: make test-parquet (depende de parquet-convert)
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
from schemas import schema_ml_detector, schema_firewall

OUT_DIR = "/vagrant/logs/parquet"
errors  = 0

def check(condition, msg):
    global errors
    if not condition:
        print(f"  FAIL: {msg}")
        errors += 1

# [PARQUET-ALLROWS-D296] DEBT-PARQUET-VALIDATOR-FIRST-ROW-001: TODAS las filas, no solo la [0]
TS_MIN_NS = 1_700_000_000_000_000_000   # 2023-11-14; por debajo = reloj monotonico u otro error (DAY294, DAY296)
TS_FUTURE_MARGIN_NS = 300 * 10**9      # ninguna fila puede venir mas de 300 s del futuro

def check_all_rows(name, col, ms_multiple=False):
    n = len(col)
    nul = col.null_count
    check(nul == 0, f"{name}: {nul} de {n} filas con timestamp_utc_ns nulo")
    a = pc.drop_null(col).to_numpy()
    if len(a) == 0:
        return
    hi = time.time_ns() + TS_FUTURE_MARGIN_NS
    for mask, what in ((a < TS_MIN_NS, f"< {TS_MIN_NS} (reloj monotonico?)"),
                       (a > hi, "del futuro (> ahora + 300 s)")):
        if mask.any():
            i = int(np.argmax(mask))
            check(False, f"{name}: {int(mask.sum())} de {n} filas con timestamp_utc_ns {what}; primera: fila {i} = {int(a[i])}")
    if ms_multiple:
        mask = (a % 1_000_000) != 0
        if mask.any():
            i = int(np.argmax(mask))
            check(False, f"{name}: {int(mask.sum())} de {n} filas no son multiplo de 1_000_000 (ms->ns fallida); primera: fila {i} = {int(a[i])}")

ml_files = sorted(glob.glob(f"{OUT_DIR}/ml-detector/*.parquet"))
check(len(ml_files) > 0, "No Parquet files found in ml-detector/")

for path in ml_files:
    t = pq.read_table(path)
    check(t.schema.equals(schema_ml_detector),
          f"{os.path.basename(path)}: schema mismatch")
    if t.num_rows == 0:
        print(f"  SKIP: {os.path.basename(path)} empty table (CSV vacio)")
        continue
    check_all_rows(os.path.basename(path), t["timestamp_utc_ns"])  # [PARQUET-ALLROWS-D296]

fw_path = f"{OUT_DIR}/firewall/firewall_blocks.parquet"
check(os.path.exists(fw_path), "firewall_blocks.parquet not found")
if os.path.exists(fw_path):
    t = pq.read_table(fw_path)
    check(t.schema.equals(schema_firewall), "firewall: schema mismatch")
    check(t.num_rows > 0, "firewall: empty table")
    check_all_rows("firewall", t["timestamp_utc_ns"], ms_multiple=True)  # [PARQUET-ALLROWS-D296]

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║  aRGus NDR — Parquet Roundtrip Validation               ║")
print("╚══════════════════════════════════════════════════════════╝")
print(f"  ml-detector files validados: {len(ml_files)}")
print(f"  firewall files validados:    1")
if errors == 0:
    print("  ROUNDTRIP PASSED")
else:
    print(f"  {errors} ASSERTION(S) FAILED")
    sys.exit(1)
print()
