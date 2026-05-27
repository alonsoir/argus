#!/bin/bash
# monitoring/gateway_pulse.sh
# Real-time ASCII dashboard for gateway performance

echo "🏥 ML DEFENDER — HOSPITAL GATEWAY PULSE"
echo "   Press Ctrl+C to stop"
echo

while true; do
    clear
    echo "=== 🚑 EMERGENCY LATENCY (last 5) ==="
    tail -5 ../perf.log | grep EMERGENCY | awk -F, '{printf "→ %7.1f μs (CPU: %4.1f%%)\n", $5, $6}'

    echo -e "\n=== 📊 LIVE TRAFFIC (last 10) ==="
    tail -10 ../perf.log | awk -F, '
        BEGIN { printf "%-10s %-8s %5s %7s %6s %5s\n", "TIME", "PROFILE", "PPS", "LAT(μs)", "CPU%", "LOSS%" }
        {
            gsub("T[0-9:.]+$", "", $1);
            printf "%-10s %-8s %5d %7.1f %6.1f %5.3f\n", $1, $2, $4, $5, $6, $7
        }'

    echo -e "\n=== 📈 SUMMARY (last 60s) ==="
    awk -F, -v now=$(date +%s) '
        BEGIN {
            start = now - 60
            split("EHR,PACS,EMERGENCY", types, ",")
        }
        {
            cmd = "date -d \"" $1 "\" +%s 2>/dev/null"
            cmd | getline ts; close(cmd)
            if (ts >= start) {
                pps[$2] += $4; count[$2]++; lat_sum[$2] += $5
            }
        }
        END {
            for (i in types) {
                t = types[i]
                if (count[t] > 0)
                    printf "%-10s: avg pps=%5.0f | avg lat=%.1fμs\n", t, pps[t]/count[t], lat_sum[t]/count[t]
            }
        }' ../perf.log 2>/dev/null

    echo -e "\n💡 Tip: Run './emergency_test.sh' to simulate critical alert"
    sleep 2
done