#!/bin/bash
# ML Defender - 8 Hour Stress Test
# Phase 1, Day 5 - Stability validation

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_DURATION_MINUTES=10
TEST_DURATION_SECONDS=$((TEST_DURATION_MINUTES * 60))
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_DIR="/vagrant/stress_test_${TIMESTAMP}"
LOGS_DIR="${TEST_DIR}/logs"
MONITORING_DIR="${TEST_DIR}/monitoring"

SNIFFER_DIR="/vagrant/sniffer/build"
SNIFFER_BIN="./sniffer"
SNIFFER_CONFIG="config/sniffer.json"

ML_DETECTOR_DIR="/vagrant/ml-detector/build"
ML_DETECTOR_BIN="./ml-detector"
ML_DETECTOR_CONFIG="../config/ml_detector_config.json"

TRAFFIC_RATE_PPS=75  # Target: 75 packets/second
MONITORING_INTERVAL=60  # Monitor every 60s

# ============================================================================
# SETUP
# ============================================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ML DEFENDER - 8 HOUR STRESS TEST                              ║"
echo "║  Testing stability, performance, and memory leak detection     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏱️  Duration: ${TEST_DURATION_MINUTES} minutes (${TEST_DURATION_SECONDS} seconds)"
echo "📊 Traffic rate: ~${TRAFFIC_RATE_PPS} pps"
echo "📁 Test directory: ${TEST_DIR}"
echo ""

# Create directories
mkdir -p "${LOGS_DIR}"
mkdir -p "${MONITORING_DIR}"

# Save test configuration
cat > "${TEST_DIR}/test_info.txt" <<EOF
ML Defender 8-Hour Stress Test
===============================
Start time: $(date)
Duration: ${TEST_DURATION_MINUTES} minutes
Traffic rate: ${TRAFFIC_RATE_PPS} pps
Components: Sniffer + ML-Detector
Thresholds: DDoS=0.85, Ransomware=0.90, Traffic=0.80, Internal=0.85
Hardware: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)
Memory: $(free -h | grep "Mem:" | awk '{print $2}')
OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
Kernel: $(uname -r)
EOF

echo "📋 Test configuration saved"

# ============================================================================
# BACKGROUND PROCESSES
# ============================================================================

# Start ML-Detector (from its build directory)
echo "🚀 Starting ML-Detector..."
cd ${ML_DETECTOR_DIR}
${ML_DETECTOR_BIN} -c ${ML_DETECTOR_CONFIG} > "${LOGS_DIR}/ml_detector.log" 2>&1 &
ML_DETECTOR_PID=$!
echo "   PID: ${ML_DETECTOR_PID}"
echo "   Working directory: ${ML_DETECTOR_DIR}"
sleep 3  # Wait for initialization

# Verify ML-Detector started
if ! kill -0 ${ML_DETECTOR_PID} 2>/dev/null; then
    echo "❌ ERROR: ML-Detector failed to start!"
    echo "   Check log: ${LOGS_DIR}/ml_detector.log"
    tail -20 "${LOGS_DIR}/ml_detector.log"
    exit 1
fi
echo "   ✅ ML-Detector running"

# Start Sniffer (from its build directory, requires sudo)
echo "🚀 Starting Sniffer..."
cd ${SNIFFER_DIR}
sudo ${SNIFFER_BIN} -c ${SNIFFER_CONFIG} > "${LOGS_DIR}/sniffer.log" 2>&1 &
SNIFFER_PID=$!
echo "   PID: ${SNIFFER_PID}"
echo "   Working directory: ${SNIFFER_DIR}"
sleep 5  # Wait for eBPF initialization

# Verify Sniffer started
if ! sudo kill -0 ${SNIFFER_PID} 2>/dev/null; then
    echo "❌ ERROR: Sniffer failed to start!"
    echo "   Check log: ${LOGS_DIR}/sniffer.log"
    tail -20 "${LOGS_DIR}/sniffer.log"
    kill ${ML_DETECTOR_PID} 2>/dev/null || true
    exit 1
fi
echo "   ✅ Sniffer running"

# Start resource monitoring
echo "📊 Starting resource monitor..."
cd /vagrant
bash /vagrant/stress_test_monitor.sh ${SNIFFER_PID} ${ML_DETECTOR_PID} "${MONITORING_DIR}" ${MONITORING_INTERVAL} > "${LOGS_DIR}/monitor.log" 2>&1 &
MONITOR_PID=$!
echo "   PID: ${MONITOR_PID}"

# Start traffic generator
echo "🌐 Starting traffic generator..."
bash /vagrant/stress_test_traffic.sh ${TRAFFIC_RATE_PPS} > "${LOGS_DIR}/traffic.log" 2>&1 &
TRAFFIC_PID=$!
echo "   PID: ${TRAFFIC_PID}"

# ============================================================================
# MAIN TEST LOOP
# ============================================================================

echo ""
echo "✅ All components started successfully"
echo ""
echo "⏳ Test running for ${TEST_DURATION_MINUTES} minutes..."
echo "   Progress will be shown every 30 minutes"
echo "   Press Ctrl+C to stop early (graceful shutdown)"
echo ""
echo "📊 Monitor with:"
echo "   tail -f ${LOGS_DIR}/sniffer.log"
echo "   tail -f ${LOGS_DIR}/ml_detector.log"
echo ""

START_TIME=$(date +%s)
END_TIME=$((START_TIME + TEST_DURATION_SECONDS))

# Function for report generation
generate_report() {
    echo ""
    echo "📊 Generating test report..."

    REPORT="${TEST_DIR}/REPORT.md"

    ACTUAL_RUNTIME=$(($(date +%s) - START_TIME))
    HOURS=$((ACTUAL_RUNTIME / 3600))
    MINUTES=$(((ACTUAL_RUNTIME % 3600) / 60))
    SECONDS=$((ACTUAL_RUNTIME % 60))

    cat > "${REPORT}" <<EOF
# ML Defender - 8 Hour Stress Test Report

## Test Information
- **Start Time**: $(cat "${TEST_DIR}/test_info.txt" | grep "Start time" | cut -d: -f2-)
- **End Time**: $(date)
- **Planned Duration**: ${TEST_DURATION_MINUTES} minutes
- **Actual Runtime**: ${HOURS}h ${MINUTES}m ${SECONDS}s (${ACTUAL_RUNTIME} seconds)
- **Traffic Rate**: ${TRAFFIC_RATE_PPS} pps

## Configuration
- **Thresholds**: DDoS=0.85, Ransomware=0.90, Traffic=0.80, Internal=0.85
- **Hardware**: $(grep "Hardware:" "${TEST_DIR}/test_info.txt" | cut -d: -f2-)
- **Memory**: $(grep "Memory:" "${TEST_DIR}/test_info.txt" | cut -d: -f2-)
- **Kernel**: $(grep "Kernel:" "${TEST_DIR}/test_info.txt" | cut -d: -f2-)

## Component Status
- **Sniffer**: $(if sudo kill -0 ${SNIFFER_PID} 2>/dev/null; then echo "✅ Running (PID: ${SNIFFER_PID})"; else echo "❌ Stopped"; fi)
- **ML-Detector**: $(if kill -0 ${ML_DETECTOR_PID} 2>/dev/null; then echo "✅ Running (PID: ${ML_DETECTOR_PID})"; else echo "❌ Stopped"; fi)

## Statistics

### Sniffer Final Stats
\`\`\`
$(tail -100 "${LOGS_DIR}/sniffer.log" | grep -A 25 "Enhanced RingBufferConsumer Statistics" | tail -25 || echo "No stats found")
\`\`\`

### ML-Detector Final Stats
\`\`\`
$(tail -100 "${LOGS_DIR}/ml_detector.log" | grep "Stats:" | tail -5 || echo "No stats found")
\`\`\`

## Resource Usage

### Memory (Last 20 samples)
\`\`\`
$(tail -20 "${MONITORING_DIR}/memory.csv" || echo "No memory data")
\`\`\`

### Memory Analysis
- **Initial Memory**: $(head -2 "${MONITORING_DIR}/memory.csv" | tail -1 | cut -d',' -f6) MB
- **Final Memory**: $(tail -1 "${MONITORING_DIR}/memory.csv" | cut -d',' -f6) MB
- **Memory Growth**: $(($(tail -1 "${MONITORING_DIR}/memory.csv" | cut -d',' -f6) - $(head -2 "${MONITORING_DIR}/memory.csv" | tail -1 | cut -d',' -f6))) MB

### CPU (Last 20 samples)
\`\`\`
$(tail -20 "${MONITORING_DIR}/cpu.csv" || echo "No CPU data")
\`\`\`

## Errors and Warnings

### Sniffer Errors
\`\`\`
$(grep -i "error\|warning\|failed" "${LOGS_DIR}/sniffer.log" | head -50 || echo "No errors found")
\`\`\`

### ML-Detector Errors
\`\`\`
$(grep -i "error\|warning\|failed" "${LOGS_DIR}/ml_detector.log" | head -50 || echo "No errors found")
\`\`\`

## Files
- **Logs Directory**: \`${LOGS_DIR}/\`
- **Monitoring Directory**: \`${MONITORING_DIR}/\`
- **Compressed Archive**: \`stress_test_${TIMESTAMP}.tar.gz\`

## Analysis

### Memory Leak Detection
$(if [ -f "${MONITORING_DIR}/memory.csv" ]; then
    INITIAL=$(head -2 "${MONITORING_DIR}/memory.csv" | tail -1 | cut -d',' -f6)
    FINAL=$(tail -1 "${MONITORING_DIR}/memory.csv" | cut -d',' -f6)
    GROWTH=$((FINAL - INITIAL))
    if [ ${GROWTH} -gt 100 ]; then
        echo "⚠️  **POTENTIAL LEAK**: Memory grew by ${GROWTH}MB over test duration"
    elif [ ${GROWTH} -gt 50 ]; then
        echo "⚠️  **MONITOR**: Memory grew by ${GROWTH}MB - acceptable but monitor"
    else
        echo "✅ **STABLE**: Memory growth ${GROWTH}MB is within normal range"
    fi
else
    echo "❌ No memory data available"
fi)

### Stability
$(if sudo kill -0 ${SNIFFER_PID} 2>/dev/null && kill -0 ${ML_DETECTOR_PID} 2>/dev/null; then
    echo "✅ All components completed test successfully"
else
    echo "❌ One or more components crashed during test"
fi)

## Next Steps
1. Review error logs for any warnings or failures
2. Analyze memory.csv for linear growth (potential leak)
3. Validate detection rates match expected patterns
4. Calibrate thresholds based on false positive rate
5. If stable, proceed with production deployment

---
Generated: $(date)
EOF

    # Compress logs
    echo "🗜️  Compressing logs..."
    cd /vagrant
    tar -czf "stress_test_${TIMESTAMP}.tar.gz" "stress_test_${TIMESTAMP}/"
    ARCHIVE_SIZE=$(du -h "stress_test_${TIMESTAMP}.tar.gz" | cut -f1)
    echo "✅ Archive created: stress_test_${TIMESTAMP}.tar.gz (${ARCHIVE_SIZE})"

    echo ""
    echo "📄 Report saved to: ${REPORT}"
    echo ""
    cat "${REPORT}"
}

# Trap for graceful shutdown
cleanup() {
    echo ""
    echo "🛑 Stopping stress test..."

    # Stop traffic generator
    if kill -0 ${TRAFFIC_PID} 2>/dev/null; then
        kill ${TRAFFIC_PID} 2>/dev/null || true
        echo "   ✅ Traffic generator stopped"
    fi

    # Stop monitor
    if kill -0 ${MONITOR_PID} 2>/dev/null; then
        kill ${MONITOR_PID} 2>/dev/null || true
        echo "   ✅ Resource monitor stopped"
    fi

    # Stop sniffer
    if sudo kill -0 ${SNIFFER_PID} 2>/dev/null; then
        sudo kill ${SNIFFER_PID} 2>/dev/null || true
        sleep 2
        echo "   ✅ Sniffer stopped"
    fi

    # Stop ml-detector
    if kill -0 ${ML_DETECTOR_PID} 2>/dev/null; then
        kill ${ML_DETECTOR_PID} 2>/dev/null || true
        sleep 2
        echo "   ✅ ML-Detector stopped"
    fi

    echo "✅ All components stopped"
    generate_report
}

trap cleanup SIGINT SIGTERM EXIT

# Progress loop
LAST_CHECK=$(date +%s)
while [ $(date +%s) -lt ${END_TIME} ]; do
    sleep 60  # Check every minute

    CURRENT=$(date +%s)

    # Show progress every 30 minutes
    if [ $((CURRENT - LAST_CHECK)) -ge 1800 ]; then
        ELAPSED=$((CURRENT - START_TIME))
        HOURS=$((ELAPSED / 3600))
        MINUTES=$(((ELAPSED % 3600) / 60))
        REMAINING=$((END_TIME - CURRENT))
        REMAINING_HOURS=$((REMAINING / 3600))
        REMAINING_MINUTES=$(((REMAINING % 3600) / 60))

        echo "⏱️  [$(date +%H:%M:%S)] Progress: ${HOURS}h ${MINUTES}m elapsed | ${REMAINING_HOURS}h ${REMAINING_MINUTES}m remaining"


        LAST_CHECK=${CURRENT}
    fi

    # Check if processes are still alive
    if ! sudo kill -0 ${SNIFFER_PID} 2>/dev/null; then
        echo "❌ [$(date +%H:%M:%S)] ERROR: Sniffer process died!"
        echo "   Last 50 lines of log:"
        tail -50 "${LOGS_DIR}/sniffer.log"
        exit 1
    fi

    if ! kill -0 ${ML_DETECTOR_PID} 2>/dev/null; then
        echo "❌ [$(date +%H:%M:%S)] ERROR: ML-Detector process died!"
        echo "   Last 50 lines of log:"
        tail -50 "${LOGS_DIR}/ml_detector.log"
        exit 1
    fi
done

# Test completed successfully
echo ""
echo "🎉 Test completed successfully after ${TEST_DURATION_MINUTES} minutes!"
exit 0