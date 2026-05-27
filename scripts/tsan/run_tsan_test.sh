#!/bin/bash
# run_tsan_test.sh - Run ml-detector with ThreadSanitizer
# Day 16 - Race Condition Investigation
# Authors: Alonso + Claude

set -e

PROJECT_ROOT="/vagrant"
DETECTOR_DIR="$PROJECT_ROOT/ml-detector"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TSAN_LOG="$PROJECT_ROOT/tsan_report_${TIMESTAMP}.txt"

echo "🔬 Running ml-detector with ThreadSanitizer"
echo "============================================"
echo ""
echo "📁 TSan report will be saved to: $TSAN_LOG"
echo ""

# ThreadSanitizer environment variables
export TSAN_OPTIONS="log_path=$TSAN_LOG second_deadlock_stack=1 history_size=7"

# Clean previous logs
rm -rf "$LOG_DIR/rag/artifacts/$(date +%Y-%m-%d)" 2>/dev/null || true
rm -f "$LOG_DIR/rag/events/$(date +%Y-%m-%d).jsonl" 2>/dev/null || true

echo "🚀 Starting ml-detector..."
echo ""
echo "⏱️  Test will run for 5 minutes or until crash"
echo "   Press Ctrl+C to stop early"
echo ""

cd "$DETECTOR_DIR"

# Start timer
START_TIME=$(date +%s)

# Run detector (TSan will print races to stderr)
./build/ml-detector config/ml_detector_config.json 2>&1 | tee -a "$TSAN_LOG" &
DETECTOR_PID=$!

echo "🔍 ml-detector PID: $DETECTOR_PID"
echo ""

# Monitor for 5 minutes or until crash
MAX_RUNTIME=300  # 5 minutes
ELAPSED=0

while kill -0 $DETECTOR_PID 2>/dev/null; do
    sleep 1
    ELAPSED=$(($(date +%s) - START_TIME))

    # Print progress every 10 seconds
    if [ $((ELAPSED % 10)) -eq 0 ]; then
        printf "\r⏱️  Runtime: %02d:%02d / 05:00" $((ELAPSED/60)) $((ELAPSED%60))
    fi

    # Stop after 5 minutes
    if [ $ELAPSED -ge $MAX_RUNTIME ]; then
        echo ""
        echo ""
        echo "⏰ 5 minutes reached - stopping test"
        kill $DETECTOR_PID 2>/dev/null || true
        sleep 2
        break
    fi
done

# Wait for process to finish
wait $DETECTOR_PID 2>/dev/null || true

FINAL_ELAPSED=$(($(date +%s) - START_TIME))

echo ""
echo ""
echo "============================================"
echo "📊 Test Complete"
echo "============================================"
echo "⏱️  Total runtime: $(($FINAL_ELAPSED / 60))m $(($FINAL_ELAPSED % 60))s"
echo ""

# Check if TSan found any races
if [ -f "$TSAN_LOG" ]; then
    RACE_COUNT=$(grep -c "WARNING: ThreadSanitizer: data race" "$TSAN_LOG" 2>/dev/null || echo "0")

    if [ "$RACE_COUNT" -gt 0 ]; then
        echo "🚨 ThreadSanitizer detected $RACE_COUNT race condition(s)!"
        echo ""
        echo "📄 Full report: $TSAN_LOG"
        echo ""
        echo "🔍 Quick summary:"
        grep -A 5 "WARNING: ThreadSanitizer" "$TSAN_LOG" | head -30
        echo ""
        echo "..."
        echo ""
        echo "✅ Success! We've captured the race conditions."
        echo "   Next step: Analyze the report and apply the fix."
    else
        echo "✅ No race conditions detected"
        echo "   (Test may have been too short or detector crashed before TSan could report)"
    fi
else
    echo "⚠️  TSan report file not found: $TSAN_LOG"
fi

echo ""
echo "📁 Check artifacts:"
echo "   ls -lh $LOG_DIR/rag/artifacts/$(date +%Y-%m-%d)/ | wc -l"
echo ""
echo "🎯 Next: Review $TSAN_LOG for race details"