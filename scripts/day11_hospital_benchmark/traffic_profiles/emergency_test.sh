#!/bin/bash
# traffic_profiles/emergency_test.sh
# Injects a life-critical EHR record DURING high-load (PACS burst)

set -euo pipefail
PROFILE="EMERGENCY"

echo "🚨 EMERGENCY TEST: Injecting 'PENICILINA ALLERGY' during PACS burst"

# Start PACS burst in background
./pacs_burst.sh 8 150 &  # 150MB in 8s

# Wait 1 second into burst, then inject critical EHR
sleep 1

START=$(date +%s%N)
# Send critical alert
echo '{"patient":"John Doe","allergy":"PENICILINA","urgency":"CRITICAL","timestamp":"'"$(date -Iseconds)"'"}' | \
  nc -w1 192.168.100.1 8080 >/dev/null 2>&1
END=$(date +%s%N)

LATENCY_US=$(( (END - START) / 1000 ))
CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print 100-$8}')

printf "%s,%s,5,1,%.1f,%.1f,0.000\n" \
    "$(date -Iseconds)" "$PROFILE" "$LATENCY_US" "$CPU" >> ../perf.log

echo "⏱️  Critical EHR processed in ${LATENCY_US}μs"

# Wait for PACS to finish
wait