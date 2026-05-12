#!/usr/bin/env python3
# aRGus NDR — Validacion roundtrip Parquet
# Uso: python3 scripts/parquet/validate_roundtrip.py
# Makefile: make test-parquet (depende de parquet-convert)
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyarrow.parquet as pq
from schemas import schema_ml_detector, schema_firewall

OUT_DIR = "/vagrant/logs/parquet"
errors  = 0

def check(condition, msg):
    global errors
    if not condition:
        print(f"  FAIL: {msg}")
        errors += 1

ml_files = sorted(glob.glob(f"{OUT_DIR}/ml-detector/*.parquet"))
check(len(ml_files) > 0, "No Parquet files found in ml-detector/")

for path in ml_files:
    t = pq.read_table(path)
    check(t.schema.equals(schema_ml_detector),
          f"{os.path.basename(path)}: schema mismatch")
    if t.num_rows == 0:
        print(f"  SKIP: {os.path.basename(path)} empty table (CSV vacio)")
        continue
    ts = t["timestamp_utc_ns"][0].as_py()
    check(ts > 1_700_000_000_000_000_000,
          f"{os.path.basename(path)}: timestamp out of range ({ts})")

fw_path = f"{OUT_DIR}/firewall/firewall_blocks.parquet"
check(os.path.exists(fw_path), "firewall_blocks.parquet not found")
if os.path.exists(fw_path):
    t = pq.read_table(fw_path)
    check(t.schema.equals(schema_firewall), "firewall: schema mismatch")
    check(t.num_rows > 0, "firewall: empty table")
    ts = t["timestamp_utc_ns"][0].as_py()
    check(ts > 1_700_000_000_000_000_000,
          f"firewall: timestamp out of range ({ts})")
    check(ts % 1_000_000 == 0,
          f"firewall: timestamp no es multiplo de 1_000_000 (ms->ns fallida)")

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
