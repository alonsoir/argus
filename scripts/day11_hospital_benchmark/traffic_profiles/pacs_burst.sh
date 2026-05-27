#!/bin/bash
# traffic_profiles/pacs_burst.sh
# Simulates PACS traffic: 200 MB DICOM bursts (e.g., CT scan)

set -euo pipefail
PROFILE="PACS"
DURATION=${1:-10}
BURST_SIZE=${2:-200}  # MB

echo "🖼️  Starting $PROFILE burst: ${BURST_SIZE}MB over ${DURATION}s"

# Generate synthetic DICOM-like data (no real patient data)
dd if=/dev/urandom of=/tmp/dicom_chunk bs=1M count="$BURST_SIZE" status=none

START=$(date +%s.%N)
# Send via UDP to avoid TCP backpressure (real PACS often uses DICOM over UDP)
pv /tmp/dicom_chunk | nc -u -w30 192.168.100.1 11112 > /dev/null 2>&1 &
PID=$!

# Monitor during transfer
while kill -0 $PID 2>/dev/null; do
    sleep 1
    CUR=$(date +%s.%N)
    ELAPSED=$(echo "$CUR - $START" | bc -l)
    BYTES=$(stat -c%s /tmp/dicom_chunk 2>/dev/null || echo 0)
    RATE=$(echo "scale=2; $BYTES / $ELAPSED / 1000000" | bc -l)  # MB/s
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print 100-$8}')

    # Estimate latency via ICMP (non-intrusive)
    LATENCY=$(ping -c1 -W1 192.168.100.1 | awk -F'=' '/time=/ {print $4}' | cut -d' ' -f1)
    [[ -z "$LATENCY" ]] && LATENCY=0.0

    printf "%s,%s,5,%.0f,%.1f,%.1f,%.3f\n" \
        "$(date -Iseconds)" "$PROFILE" "$RATE" "$LATENCY" "$CPU" "0.0" >> ../perf.log
done

wait $PID
rm -f /tmp/dicom_chunk
echo "✅ $PROFILE burst completed"