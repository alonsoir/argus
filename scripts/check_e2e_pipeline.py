#!/usr/bin/env python3
"""
check_e2e_pipeline.py — DAY 159
Parsea logs del pipeline aRGus NDR y verifica integridad E2E.

Modo snapshot: guarda contadores antes de inyectar, verifica incremento después.
Uso:
  python3 check_e2e_pipeline.py snapshot   # guarda estado actual
  python3 check_e2e_pipeline.py check      # verifica incremento vs snapshot
  python3 check_e2e_pipeline.py check-abs  # verifica valores absolutos (sin snapshot)
"""
import re
import sys
import json
from pathlib import Path

LOG_DIR     = Path("/vagrant/logs/lab")
SNAPSHOT_F  = Path("/tmp/argus_e2e_snapshot.json")

def parse_ml_detector_last(log_path):
    pattern = re.compile(
        r"Stats: received=(\d+), processed=(\d+), sent=(\d+), attacks=(\d+), "
        r"errors=\(deser:(\d+), feat:(\d+), inf:(\d+)\)"
    )
    last = None
    with open(log_path) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                last = {
                    "received":  int(m.group(1)),
                    "processed": int(m.group(2)),
                    "sent":      int(m.group(3)),
                    "err_deser": int(m.group(5)),
                }
    return last

def parse_firewall_last(log_path):
    fields = ["events_processed", "events_dropped", "crypto_errors", "decompression_errors"]
    last = None
    with open(log_path) as f:
        for line in f:
            if "System State Dump" not in line:
                continue
            row = {}
            for field in fields:
                m = re.search(rf"{field}=(\d+)", line)
                if m:
                    row[field] = int(m.group(1))
            if len(row) == len(fields):
                last = row
    return last

def print_header(title):
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print(f"║  🔍 {title:<54}║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check-abs"

    ml_log = LOG_DIR / "ml-detector.log"
    fw_log = LOG_DIR / "firewall-agent.log"

    ml_stats = parse_ml_detector_last(ml_log) if ml_log.exists() else None
    fw_stats = parse_firewall_last(fw_log)     if fw_log.exists() else None

    # ── SNAPSHOT ─────────────────────────────────────────────────────────────
    if mode == "snapshot":
        print_header("aRGus NDR — E2E Snapshot (DAY 159)")
        snap = {
            "ml_detector": ml_stats or {},
            "firewall":    fw_stats or {},
        }
        SNAPSHOT_F.write_text(json.dumps(snap, indent=2))
        print(f"✅ Snapshot guardado en {SNAPSHOT_F}")
        print(f"   ml-detector: {ml_stats}")
        print(f"   firewall:    {fw_stats}")
        sys.exit(0)

    # ── CHECK solo firewall (ml-detector parado intencionalmente) ───────────
    if mode == "check-firewall":
        print_header("aRGus NDR — E2E Check firewall (delta vs snapshot)")
        if not SNAPSHOT_F.exists():
            print("❌ No hay snapshot")
            sys.exit(1)
        snap = json.loads(SNAPSHOT_F.read_text())
        fw_before = snap.get("firewall", {})
        failures = []

        fw_proc_before = fw_before.get("events_processed", 0)
        fw_proc_after  = (fw_stats or {}).get("events_processed", 0)
        fw_delta = fw_proc_after - fw_proc_before
        print(f"firewall: events_processed {fw_proc_before} → {fw_proc_after} (delta={fw_delta})")
        if fw_delta <= 0:
            failures.append(f"firewall: ZERO new events processed (delta={fw_delta})")
        if (fw_stats or {}).get("events_dropped", 0) > fw_before.get("events_dropped", 0):
            failures.append("firewall: events_dropped aumentó")
        if (fw_stats or {}).get("crypto_errors", 0) > 0:
            failures.append(f"firewall: crypto_errors={fw_stats['crypto_errors']}")
        if (fw_stats or {}).get("decompression_errors", 0) > 0:
            failures.append(f"firewall: decompression_errors={fw_stats['decompression_errors']}")

        print()
        print("════════════════════════════════════════════════════════════")
        if failures:
            print("❌ E2E CHECK FAILED:")
            for f in failures:
                print(f"   • {f}")
            sys.exit(1)
        else:
            print("✅ E2E CHECK PASSED — firewall saludable")
        sys.exit(0)

    # ── CHECK con delta ───────────────────────────────────────────────────────
    if mode == "check":
        print_header("aRGus NDR — E2E Check (delta vs snapshot)")
        if not SNAPSHOT_F.exists():
            print("❌ No hay snapshot — ejecuta primero: python3 check_e2e_pipeline.py snapshot")
            sys.exit(1)
        snap = json.loads(SNAPSHOT_F.read_text())
        ml_before = snap.get("ml_detector", {})
        fw_before  = snap.get("firewall", {})

        failures = []

        # ml-detector: received debe haber aumentado
        ml_recv_before = ml_before.get("received", 0)
        ml_recv_after  = (ml_stats or {}).get("received", 0)
        ml_delta = ml_recv_after - ml_recv_before
        # Si los contadores bajaron, ml-detector se reinició — usar valor absoluto
        if ml_delta < 0:
            print(f"ml-detector: reinicio detectado ({ml_recv_before} → {ml_recv_after}) — usando absoluto")
            ml_delta = ml_recv_after
        print(f"ml-detector: received {ml_recv_before} → {ml_recv_after} (delta={ml_delta})")
        if ml_delta <= 0:
            failures.append(f"ml-detector: ZERO new events received (delta={ml_delta})")
        if (ml_stats or {}).get("err_deser", 0) > 0:
            failures.append(f"ml-detector: deserialization errors={ml_stats['err_deser']}")

        # firewall: events_processed debe haber aumentado
        fw_proc_before = fw_before.get("events_processed", 0)
        fw_proc_after  = (fw_stats or {}).get("events_processed", 0)
        fw_delta = fw_proc_after - fw_proc_before
        # Si los contadores bajaron, firewall se reinició — usar valor absoluto
        if fw_delta < 0:
            print(f"firewall: reinicio detectado ({fw_proc_before} → {fw_proc_after}) — usando absoluto")
            fw_delta = fw_proc_after
        print(f"firewall:    events_processed {fw_proc_before} → {fw_proc_after} (delta={fw_delta})")
        if fw_delta <= 0:
            failures.append(f"firewall: ZERO new events processed (delta={fw_delta})")
        if (fw_stats or {}).get("events_dropped", 0) > (fw_before.get("events_dropped", 0)):
            failures.append("firewall: events_dropped aumentó")
        if (fw_stats or {}).get("crypto_errors", 0) > 0:
            failures.append(f"firewall: crypto_errors={fw_stats['crypto_errors']}")
        if (fw_stats or {}).get("decompression_errors", 0) > 0:
            failures.append(f"firewall: decompression_errors={fw_stats['decompression_errors']}")

        print()
        print("════════════════════════════════════════════════════════════")
        if failures:
            print("❌ E2E CHECK FAILED:")
            for f in failures:
                print(f"   • {f}")
            sys.exit(1)
        else:
            print("✅ E2E CHECK PASSED — pipeline saludable")
        sys.exit(0)

    # ── CHECK absoluto (sin snapshot) ────────────────────────────────────────
    print_header("aRGus NDR — E2E Check absoluto (DAY 159)")
    failures = []

    print("ml-detector (último stat):")
    if ml_stats:
        for k, v in ml_stats.items():
            print(f"  {k}={v}")
        if ml_stats["received"] == 0:
            failures.append("ml-detector: ZERO events received")
        if ml_stats["err_deser"] > 0:
            failures.append(f"ml-detector: err_deser={ml_stats['err_deser']}")
    else:
        failures.append("ml-detector: log no encontrado o sin stats")
    print()

    print("firewall (último stat):")
    if fw_stats:
        for k, v in fw_stats.items():
            print(f"  {k}={v}")
        if fw_stats["events_processed"] == 0:
            failures.append("firewall: ZERO events processed")
        if fw_stats["events_dropped"] > 0:
            failures.append(f"firewall: events_dropped={fw_stats['events_dropped']}")
        if fw_stats["crypto_errors"] > 0:
            failures.append(f"firewall: crypto_errors={fw_stats['crypto_errors']}")
        if fw_stats["decompression_errors"] > 0:
            failures.append(f"firewall: decompression_errors={fw_stats['decompression_errors']}")
    else:
        failures.append("firewall: log no encontrado o sin stats")
    print()

    print("════════════════════════════════════════════════════════════")
    if failures:
        print("❌ E2E CHECK FAILED:")
        for f in failures:
            print(f"   • {f}")
        sys.exit(1)
    else:
        print("✅ E2E CHECK PASSED — pipeline saludable")
    sys.exit(0)

if __name__ == "__main__":
    main()
