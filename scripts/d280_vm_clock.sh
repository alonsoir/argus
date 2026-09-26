#!/usr/bin/env bash
# DAY280 — desfase de reloj de cada VM contra el host (Mac).
# offset = hora_VM - hora_host; el ssh mete incertidumbre = (host_despues - host_antes)
set -uo pipefail
now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
for vm in "$@"; do
  t0=$(now)
  v=$(vagrant ssh "$vm" -c 'date +%s.%N' 2>/dev/null | tr -d '\r')
  t1=$(now)
  python3 - "$vm" "$t0" "$v" "$t1" <<'PY'
import sys
vm,t0,v,t1=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
mid=(t0+t1)/2
print(f"{vm:10s} offset_vs_host={v-mid:+8.2f} s  (incertidumbre ±{(t1-t0)/2:.2f} s)")
PY
done
