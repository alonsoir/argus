#!/bin/bash
# analysis/validate_results.sh
# Validates against medical-grade success criteria

PERF_LOG="../perf.log"
PASS=0; FAIL=0

check() {
    local condition="$1"
    local description="$2"
    if eval "$condition"; then
        ((PASS++))
        echo "✅ $description"
    else
        ((FAIL++))
        echo "❌ $description"
    fi
}

echo "🔍 Validating Day 11 Results against Medical Criteria"

# 1. Zero false positives in EHR
FP_EHR=$(grep -c "FP_DETECTED.*EHR" "$PERF_LOG" 2>/dev/null || echo 0)
check "[[ $FP_EHR -eq 0 ]]" "Zero false positives in EHR traffic"

# 2. Critical EHR latency < 50ms
EMERG_LAT=$(awk -F, '$2=="EMERGENCY" {print $5}' "$PERF_LOG" | sort -n | tail -1)
check "[[ $EMERG_LAT -lt 50000 ]]" "Emergency EHR latency < 50ms (actual: ${EMERG_LAT}μs)"

# 3. PACS p99 latency < 150μs
PACS_P99=$(awk -F, '$2=="PACS" {lat[NR]=$5} END {n=asort(lat); print (n>0) ? lat[int(0.99*n)] : 0}' "$PERF_LOG")
check "[[ $PACS_P99 -lt 150 ]]" "PACS p99 latency < 150μs (actual: ${PACS_P99}μs)"

# 4. CPU < 40% during peak
CPU_PEAK=$(awk -F, '{if($6 > max) max=$6} END {print max+0}' "$PERF_LOG")
check "[[ $CPU_PEAK -lt 40 ]]" "Peak CPU < 40% (actual: ${CPU_PEAK}%)"

echo -e "\n🎯 Medical Validation: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && echo "🌟 HOSPITAL-READY ✅" || echo "⚠️ Requires adjustment"