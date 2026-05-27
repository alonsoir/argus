#!/bin/bash
# preflight/preflight_check.sh
# Hospital Network Pre-flight Check – ML Defender Day 11
# Ensures environment is ready for medical-grade benchmarking

set -euo pipefail
LOG="preflight.log"
echo "$(date -Iseconds) 🏥 Starting pre-flight check" | tee -a "$LOG"

PASS=0; FAIL=0

check() {
    local condition="$1"
    local description="$2"
    local result
    if eval "$condition"; then
        ((PASS++))
        echo "✅ $description" | tee -a "$LOG"
    else
        ((FAIL++))
        echo "❌ $description" | tee -a "$LOG"
    fi
}

# 1. Core networking
check "[[ $(sysctl -n net.ipv4.ip_forward 2>/dev/null) == 1 ]]" "IP forwarding enabled"
check "[[ $(sysctl -n net.ipv4.conf.all.rp_filter 2>/dev/null) == 0 ]]" "rp_filter=0 (all interfaces)"
check "[[ $(sysctl -n net.ipv4.conf.eth1.rp_filter 2>/dev/null) == 0 ]]" "rp_filter=0 (eth1/WAN)"
check "[[ $(sysctl -n net.ipv4.conf.eth3.rp_filter 2>/dev/null) == 0 ]]" "rp_filter=0 (eth3/LAN)"

# 2. XDP state
check "$(bpftool net 2>/dev/null | grep -q 'eth3.*generic' && echo 1)" "XDP attached to eth3 (gateway)"
check "$(bpftool net 2>/dev/null | grep -q 'eth1.*generic' && echo 1)" "XDP attached to eth1 (host-based)"
check "[[ -n \"\$(bpftool map list 2>/dev/null | grep ring_buf)\" ]]" "Ring buffer map exists"

# 3. Services
check "[[ -n \"\$(pgrep -f 'sniffer.*--dual-nic')\" ]]" "ML Defender sniffer running"

# 4. Traffic generation capability
check "[[ -x /usr/bin/tcpreplay ]]" "tcpreplay installed"
check "[[ -x /usr/bin/wrk2 ]]" "wrk2 installed (for EHR load)"

echo -e "\n📊 $(date -Iseconds): $PASS passed, $FAIL failed" | tee -a "$LOG"

if [[ $FAIL -eq 0 ]]; then
    touch preflight_ok
    echo "🌟 Pre-flight successful. Ready for hospital stress test." | tee -a "$LOG"
    exit 0
else
    echo "⚠️  Pre-flight failed. Fix issues before proceeding." | tee -a "$LOG"
    exit 1
fi