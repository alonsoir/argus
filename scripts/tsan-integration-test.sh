#!/bin/bash
set -e

echo "🔥 Starting TSAN Integration Test (300s)"
echo "================================================"

# Absolute paths
TSAN_DIR="/vagrant/tsan-reports/day48"
mkdir -p "$TSAN_DIR"

# Cleanup previous run
pkill -9 -f etcd-server 2>/dev/null || true
pkill -9 -f ml-detector 2>/dev/null || true
sudo pkill -9 -f sniffer 2>/dev/null || true
sleep 2

# Start components with TSAN
echo "🚀 Starting etcd-server..."
cd /vagrant/etcd-server/build-tsan
TSAN_OPTIONS="log_path=$TSAN_DIR/etcd-server-integration history_size=7" \
    nohup ./etcd-server > "$TSAN_DIR/etcd-server-integration.log" 2>&1 &
sleep 3

echo "🚀 Starting ml-detector..."
cd /vagrant/ml-detector/build-tsan
TSAN_OPTIONS="log_path=$TSAN_DIR/ml-detector-integration history_size=7" \
    nohup ./ml-detector --config ../config/ml_detector_config.json > "$TSAN_DIR/ml-detector-integration.log" 2>&1 &
sleep 2

echo "🚀 Starting sniffer..."
cd /vagrant/sniffer/build-tsan
TSAN_OPTIONS="log_path=$TSAN_DIR/sniffer-integration history_size=7" \
    sudo -E nohup ./sniffer -c ../config/sniffer.json > "$TSAN_DIR/sniffer-integration.log" 2>&1 &
sleep 5

# Verify all started
echo "👀 Verifying components started..."
pgrep -f etcd-server > /dev/null || { echo "❌ etcd-server failed to start"; cat "$TSAN_DIR/etcd-server-integration.log"; exit 1; }
pgrep -f ml-detector > /dev/null || { echo "❌ ml-detector failed to start"; cat "$TSAN_DIR/ml-detector-integration.log"; exit 1; }
pgrep -f sniffer > /dev/null || { echo "❌ sniffer failed to start"; cat "$TSAN_DIR/sniffer-integration.log"; exit 1; }
echo "✅ All components running"

# Monitor for 300 seconds
echo "🌊 Monitoring pipeline for 300 seconds..."
for i in {1..30}; do
    sleep 10
    elapsed=$((i * 10))
    echo "  [$elapsed/300s] Checking processes..."
    
    pgrep -f etcd-server > /dev/null || { echo "❌ etcd-server crashed!"; exit 1; }
    pgrep -f ml-detector > /dev/null || { echo "❌ ml-detector crashed!"; exit 1; }
    pgrep -f sniffer > /dev/null || { echo "❌ sniffer crashed!"; exit 1; }
done

echo "✅ Integration test complete - all components stable for 300s"

# Graceful shutdown
echo "🛑 Shutting down components..."
sudo pkill -SIGTERM -f sniffer 2>/dev/null || true
pkill -SIGTERM -f ml-detector 2>/dev/null || true
pkill -SIGTERM -f etcd-server 2>/dev/null || true
sleep 3

# Force kill if needed
sudo pkill -9 -f sniffer 2>/dev/null || true
pkill -9 -f ml-detector 2>/dev/null || true
pkill -9 -f etcd-server 2>/dev/null || true

echo "✅ Shutdown complete"
