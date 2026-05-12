#!/usr/bin/env python3
# aRGus NDR — Generador CSV -> Parquet
# Uso: python3 scripts/parquet/generate_parquet.py
# Makefile: make parquet-convert
import sys, os, csv, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyarrow as pa
import pyarrow.parquet as pq
from schemas import (
    schema_ml_detector, ML_DETECTOR_CLASSIFICATION, ML_DETECTOR_ACTION, SENTINEL,
    schema_firewall, FIREWALL_ACTION,
)

ML_CSV_DIR  = "/vagrant/logs/ml-detector/events"

PROTOCOL_MAP = {"TCP": 6, "UDP": 17, "ICMP": 1, "OTHER": 255}
FW_CSV_PATH = "/vagrant/logs/firewall_logs/firewall_blocks.csv"
OUT_DIR     = "/vagrant/logs/parquet"

os.makedirs(f"{OUT_DIR}/ml-detector", exist_ok=True)
os.makedirs(f"{OUT_DIR}/firewall",    exist_ok=True)

def convert_ml_day(csv_path):
    date = os.path.basename(csv_path).replace(".csv", "")
    out  = f"{OUT_DIR}/ml-detector/{date}.parquet"
    rows = {f.name: [] for f in schema_ml_detector}

    with open(csv_path) as f:
        for cols in csv.reader(f):
            if len(cols) < 127:
                continue
            rows["timestamp_utc_ns"].append(int(cols[0]))
            rows["flow_id"].append(cols[1])
            rows["anon_src_host_id"].append(cols[2] if cols[2] else None)
            rows["anon_dst_host_id"].append(cols[3] if cols[3] else None)
            rows["src_port"].append(int(cols[4])  if cols[4]  else None)
            rows["dst_port"].append(int(cols[5])  if cols[5]  else None)
            rows["protocol"].append(PROTOCOL_MAP.get(cols[6], int(cols[6]) if cols[6].isdigit() else None))
            rows["classification"].append(ML_DETECTOR_CLASSIFICATION.get(cols[7], -1))
            rows["confidence"].append(float(cols[8])  if cols[8]  else None)
            rows["threat_label"].append(cols[9]   if cols[9]  else None)
            rows["threat_score"].append(float(cols[10]) if cols[10] else None)
            v_a = float(cols[11]) if cols[11] else None
            v_b = float(cols[12]) if cols[12] else None
            rows["score_a"].append(None if v_a == SENTINEL else v_a)
            rows["score_b"].append(None if v_b == SENTINEL else v_b)
            rows["action"].append(ML_DETECTOR_ACTION.get(cols[13], -1))
            rows["ed25519_sig"].append(cols[-1])

    table = pa.table(rows, schema=schema_ml_detector)
    pq.write_table(table, out, compression="snappy")
    csv_b = os.path.getsize(csv_path)
    pq_b  = os.path.getsize(out)
    return date, table.num_rows, csv_b, pq_b

def convert_firewall():
    out  = f"{OUT_DIR}/firewall/firewall_blocks.parquet"
    rows = {f.name: [] for f in schema_firewall}

    with open(FW_CSV_PATH) as f:
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
    return table.num_rows, os.path.getsize(FW_CSV_PATH), os.path.getsize(out)

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║  aRGus NDR — Parquet Converter                          ║")
print("╚══════════════════════════════════════════════════════════╝")

total_rows = 0
for csv_path in sorted(glob.glob(f"{ML_CSV_DIR}/*.csv")):
    date, n, csv_b, pq_b = convert_ml_day(csv_path)
    ratio = csv_b / pq_b if pq_b else 0
    marker = "  (empty CSV)" if n == 0 else ""
    print(f"  ml-detector {date}: {n:>6} rows  {csv_b:>9,}->{pq_b:>8,} bytes  {ratio:.1f}x{marker}")
    total_rows += n

fw_rows, fw_csv_b, fw_pq_b = convert_firewall()
fw_ratio = fw_csv_b / fw_pq_b if fw_pq_b else 0
print(f"  firewall    (all):  {fw_rows:>6} rows  {fw_csv_b:>9,}->{fw_pq_b:>8,} bytes  {fw_ratio:.1f}x")
print()
print(f"  TOTAL ml-detector rows: {total_rows:,}")
print(f"  Output: {OUT_DIR}")
print("  ✅ DONE")
print()
