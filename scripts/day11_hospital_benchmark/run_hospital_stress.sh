#!/bin/bash
# run_hospital_stress.sh
# One-command execution of full hospital stress test

cd "$(dirname "$0")" || exit 1

# 1. Pre-flight
echo "🔧 Running pre-flight check..."
./preflight/preflight_check.sh || { echo "❌ Pre-flight failed"; exit 1; }

# 2. Initialize log
echo "timestamp,profile,ifindex,pps,latency_us,cpu_percent,packet_loss_pct" > perf.log

# 3. Run profiles
echo -e "\n💉 EHR Load Test (30s)..."
./traffic_profiles/ehr_load.sh 30 10000

echo -e "\n🖼️  PACS Burst Test (10s)..."
./traffic_profiles/pacs_burst.sh 10 200

echo -e "\n🚨 Emergency Critical Alert Test..."
./traffic_profiles/emergency_test.sh

# 4. Summary
echo -e "\n📊 Validation Summary:"
./analysis/validate_results.sh

# 5. Optional: Start dashboard
echo -e "\n👁️  Start real-time monitoring? (y/N)"
read -r ans
[[ "${ans,,}" == "y" ]] && ./monitoring/gateway_pulse.sh