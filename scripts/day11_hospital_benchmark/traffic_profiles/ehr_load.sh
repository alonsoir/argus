#!/bin/bash
# traffic_profiles/ehr_load.sh
# Simulates Electronic Health Record queries: 50-byte JSON, high frequency

set -euo pipefail
PROFILE="EHR"
DURATION=${1:-30}  # seconds
RATE=${2:-10000}   # requests/sec
TARGET="192.168.100.1:8080"

echo "💉 Starting $PROFILE load: $RATE req/s for $DURATION seconds"

# Warm-up
echo '{"op":"ping","id":0}' | nc -w1 "$TARGET" >/dev/null 2>&1

# Generate load with wrk2 (uniform arrival, avoids burst artifacts)
wrk2 -c100 -t4 -R"$RATE" -d"${DURATION}s" -s ./ehr.lua "http://$TARGET" 2>&1 | \
  awk -v profile="$PROFILE" -v ifindex=5 '
    /Requests/sec/ { rps = $2 }
    /Latency/ && /99%/ { p99 = $2 }
    /Latency/ && /50%/ { p50 = $2 }
    END {
        if (rps && p99 && p50) {
            cpu = "'$(top -bn1 | grep "Cpu(s)" | awk '{print 100-$8}')'"
            printf "%s,%s,%d,%.0f,%.1f,%.1f,%.3f\n", strftime("%Y-%m-%dT%H:%M:%S"), profile, ifindex, rps, p99, cpu, 0.0
        }
    }' >> ../perf.log