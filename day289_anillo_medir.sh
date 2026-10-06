#!/usr/bin/env bash
# DAY289 paso 0 del anillo: delta del mapa stats + perf y top por hilos del sniffer durante una corrida.
# Uso: day289_anillo_medir.sh TAG SEGUNDOS  (lanzar tcpreplay en el client JUSTO después de arrancarlo)
# PID del sniffer: SNIFFER_PID=... o pgrep -x sniffer.
set -eu
export LC_ALL=C
TAG=${1:?tag}; SEG=${2:?segundos}
D=/vagrant/logs/lab/day289/anillo
mkdir -p "$D"
PID=${SNIFFER_PID:-$(pgrep -x sniffer || true)}
N=$(printf '%s\n' "$PID" | grep -c . || true)
if [ "$N" -ne 1 ]; then
  echo "PARAR: se esperaba 1 PID de sniffer y hay $N ($PID). Candidatos:"; pgrep -a sniffer || true; exit 1
fi
echo "sniffer PID=$PID tag=$TAG ventana=${SEG}s — lanza ya el tcpreplay"
sudo bpftool map dump name stats -j > "$D/stats_antes_$TAG.json"
top -b -H -d 1 -n "$SEG" -p "$PID" > "$D/top_$TAG.txt" &
TOP=$!
sudo perf record -F 99 -e cpu-clock --call-graph dwarf -p "$PID" -o "/tmp/perf_$TAG.data" -- sleep "$SEG" \
  > "$D/perf_record_$TAG.txt" 2>&1
wait "$TOP" || true
sudo bpftool map dump name stats -j > "$D/stats_despues_$TAG.json"

echo "== delta del mapa stats =="
python3 - "$D/stats_antes_$TAG.json" "$D/stats_despues_$TAG.json" <<'PY' | tee "$D/stats_delta_$TAG.txt"
import json, sys
NOM = {0: "EVENTS", 1: "RESERVE_FAIL", 2: "FILTER_DISCARD", 3: "FRAG_SKIPPED"}
def num(x):
    if isinstance(x, list):
        return int.from_bytes(bytes(int(b, 16) for b in x), "little")
    return int(x)
def leer(p):
    out = {}
    for e in json.load(open(p)):
        f = e.get("formatted", e)
        if "values" in f:
            v = sum(num(c["value"]) for c in f["values"])
        else:
            v = num(f["value"])
        out[num(f["key"])] = v
    return out
a, b = leer(sys.argv[1]), leer(sys.argv[2])
for k in sorted(b):
    print(f"{NOM.get(k, k):15s} antes={a.get(k, 0):>12d} despues={b[k]:>12d} delta={b[k] - a.get(k, 0):>10d}")
ev, rf = b.get(0, 0) - a.get(0, 0), b.get(1, 0) - a.get(1, 0)
if ev + rf:
    print(f"fraccion RESERVE_FAIL = {100 * rf / (ev + rf):.2f}% de (EVENTS+RESERVE_FAIL)")
PY

echo "== perf: top símbolos (>=1 %) =="
sudo perf report -i "/tmp/perf_$TAG.data" --stdio --no-children --sort comm,dso,sym --percent-limit 1 \
  > "$D/perf_report_$TAG.txt" 2>&1 || true
grep -E '^ +[0-9]' "$D/perf_report_$TAG.txt" | head -30 || true
echo "== perf: reparto por hilo =="
sudo perf report -i "/tmp/perf_$TAG.data" --stdio --no-children --sort tid --percent-limit 1 \
  > "$D/perf_hilos_$TAG.txt" 2>&1 || true
grep -E '^ +[0-9]' "$D/perf_hilos_$TAG.txt" | head -20 || true
echo "== top -H: %CPU medio por hilo (los 8 más altos) =="
awk -v P="$PID" '$1 ~ /^[0-9]+$/ && NF >= 12 {c[$1" "$12]+=$9; n[$1" "$12]++}
  END {for (k in c) printf "%6.1f %s\n", c[k]/n[k], k}' "$D/top_$TAG.txt" | sort -rn | head -8
echo "== ZMQ-DROP en logs =="
grep -c 'ZMQ-DROP' /vagrant/logs/lab/sniffer.log || true
grep -c 'ZMQ-DROP' /vagrant/logs/lab/ml-detector.log || true
grep 'ZMQ-DROP' /vagrant/logs/lab/ml-detector.log | tail -3 || true
