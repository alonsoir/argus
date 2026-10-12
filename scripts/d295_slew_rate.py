#!/usr/bin/env python3
"""DAY295: ritmo de MONOTONIC y REALTIME frente a MONOTONIC_RAW durante N segundos (ppm)."""
import sys
import time

n = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
c = (time.CLOCK_REALTIME, time.CLOCK_MONOTONIC, time.CLOCK_MONOTONIC_RAW)
a = [time.clock_gettime_ns(k) for k in c]
time.sleep(n)
b = [time.clock_gettime_ns(k) for k in c]
raw = b[2] - a[2]
print(f"intervalo_raw={raw / 1e9:.3f} s")
print(f"ppm_monotonic_vs_raw={((b[1] - a[1]) / raw - 1) * 1e6:.1f}")
print(f"ppm_realtime_vs_raw={((b[0] - a[0]) / raw - 1) * 1e6:.1f}")
