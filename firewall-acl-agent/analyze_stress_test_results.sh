#!/bin/bash
# analyze_stress_test_results.sh
# Análisis de logs DESPUÉS de ejecutar tu stress test real

LOG_FILE="/vagrant/logs/firewall-acl-agent/firewall_detailed.log"

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Day 50 - Stress Test Results Analyzer                ║"
echo "║  (Post-mortem analysis)                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    exit 1
fi

echo "Analyzing: $LOG_FILE"
echo "File size: $(du -h "$LOG_FILE" | cut -f1)"
echo "Last modified: $(stat -c %y "$LOG_FILE" 2>/dev/null || stat -f %Sm "$LOG_FILE" 2>/dev/null)"
echo ""

echo "════════════════════════════════════════════════════════"
echo "Event Counters"
echo "════════════════════════════════════════════════════════"

# ZMQ Events
ZMQ_RECV=$(grep -c "ZMQ message received" "$LOG_FILE" || echo 0)
echo "ZMQ messages received:     $ZMQ_RECV"

# Protobuf Parsing
PROTOBUF_PARSED=$(grep -c "Protobuf parsed" "$LOG_FILE" || echo 0)
echo "Protobuf parsed:           $PROTOBUF_PARSED"

# Detections processed
DETECTIONS=$(grep -c "Processing detection\|Processing threat event" "$LOG_FILE" || echo 0)
echo "Detections processed:      $DETECTIONS"

# Batch operations
BATCH_ADDS=$(grep -c "Added IP to pending batch\|Added IP directly to batch" "$LOG_FILE" || echo 0)
echo "IPs added to batches:      $BATCH_ADDS"

BATCH_DEDUP=$(grep -c "IP deduplicated" "$LOG_FILE" || echo 0)
echo "IPs deduplicated:          $BATCH_DEDUP"

BATCH_FLUSH=$(grep -c "Starting batch flush" "$LOG_FILE" || echo 0)
echo "Batches flushed:           $BATCH_FLUSH"

# IPSet operations
IPSET_SUCCESS=$(grep -c "Batch flush successful" "$LOG_FILE" || echo 0)
echo "IPSet batch successes:     $IPSET_SUCCESS"

IPSET_FAILED=$(grep -c "Batch flush failed" "$LOG_FILE" || echo 0)
echo "IPSet batch failures:      $IPSET_FAILED"

echo ""
echo "════════════════════════════════════════════════════════"
echo "Error Analysis"
echo "════════════════════════════════════════════════════════"

ERRORS=$(grep -c "ERROR" "$LOG_FILE" || echo 0)
echo "Total errors:              $ERRORS"

WARNINGS=$(grep -c "WARN" "$LOG_FILE" || echo 0)
echo "Total warnings:            $WARNINGS"

CRASHES=$(grep -c "CRASH" "$LOG_FILE" || echo 0)
echo "Crashes detected:          $CRASHES"

if [ "$CRASHES" -gt 0 ]; then
    echo ""
    echo "⚠️  CRASH DETECTED - Last crash details:"
    echo "────────────────────────────────────────────────────────"
    grep -A 20 "=== CRASH DETECTED ===" "$LOG_FILE" | tail -n 20
fi

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "Sample errors (last 5):"
    echo "────────────────────────────────────────────────────────"
    grep "ERROR" "$LOG_FILE" | tail -n 5
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "Performance Metrics"
echo "════════════════════════════════════════════════════════"

# Extract flush latencies
if grep -q "duration_us" "$LOG_FILE"; then
    echo "Batch flush latencies (μs):"

    # Get all flush durations
    DURATIONS=$(grep "Batch flush successful" "$LOG_FILE" | grep -oP 'duration_us=\K[0-9]+' || echo "")

    if [ -n "$DURATIONS" ]; then
        # Calculate min, max, avg
        MIN=$(echo "$DURATIONS" | sort -n | head -1)
        MAX=$(echo "$DURATIONS" | sort -n | tail -1)
        AVG=$(echo "$DURATIONS" | awk '{sum+=$1; count++} END {if(count>0) print int(sum/count); else print 0}')
        COUNT=$(echo "$DURATIONS" | wc -l)

        echo "  Min:   $MIN μs"
        echo "  Max:   $MAX μs"
        echo "  Avg:   $AVG μs"
        echo "  Count: $COUNT flushes"
    else
        echo "  No latency data found"
    fi
else
    echo "No performance data available"
fi

# Extract throughput
if grep -q "ips_per_second" "$LOG_FILE"; then
    echo ""
    echo "Throughput (IPs/sec):"

    THROUGHPUT=$(grep "ips_per_second" "$LOG_FILE" | grep -oP 'ips_per_second=\K[0-9.]+' | tail -n 5)

    if [ -n "$THROUGHPUT" ]; then
        echo "$THROUGHPUT" | awk '{printf "  %s IPs/sec\n", $1}'
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "System State Dumps"
echo "════════════════════════════════════════════════════════"

STATE_DUMPS=$(grep -c "System State Dump" "$LOG_FILE" || echo 0)
echo "State dumps recorded:      $STATE_DUMPS"

if [ "$STATE_DUMPS" -gt 0 ]; then
    echo ""
    echo "Last state dump:"
    echo "────────────────────────────────────────────────────────"
    grep "System State Dump" "$LOG_FILE" | tail -n 1
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "Success Rates"
echo "════════════════════════════════════════════════════════"

if [ "$BATCH_FLUSH" -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($IPSET_SUCCESS / $BATCH_FLUSH) * 100}")
    echo "Batch flush success rate:  $SUCCESS_RATE%"
fi

if [ "$ZMQ_RECV" -gt 0 ]; then
    PARSE_RATE=$(awk "BEGIN {printf \"%.1f\", ($PROTOBUF_PARSED / $ZMQ_RECV) * 100}")
    echo "Protobuf parse rate:       $PARSE_RATE%"
fi

if [ "$BATCH_ADDS" -gt 0 ]; then
    DEDUP_RATE=$(awk "BEGIN {printf \"%.1f\", ($BATCH_DEDUP / ($BATCH_ADDS + $BATCH_DEDUP)) * 100}")
    echo "Deduplication rate:        $DEDUP_RATE%"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "Timeline Analysis"
echo "════════════════════════════════════════════════════════"

FIRST_EVENT=$(grep "Firewall ACL Agent starting\|Observability initialized" "$LOG_FILE" | head -1 | grep -oP '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "Unknown")
LAST_EVENT=$(grep "BATCH\|IPSET\|ERROR" "$LOG_FILE" | tail -1 | grep -oP '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "Unknown")

echo "First event:               $FIRST_EVENT"
echo "Last event:                $LAST_EVENT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "Recommendations"
echo "════════════════════════════════════════════════════════"

if [ "$CRASHES" -gt 0 ]; then
    echo "⚠️  CRITICAL: Crashes detected - review backtrace above"
fi

if [ "$IPSET_FAILED" -gt 0 ]; then
    echo "⚠️  WARNING: IPSet failures detected - check permissions/ipset config"
fi

if [ "$ERRORS" -gt 10 ]; then
    echo "⚠️  WARNING: High error count - review error messages"
fi

if [ "$BATCH_FLUSH" -eq 0 ]; then
    echo "⚠️  INFO: No batches flushed - check if events are arriving"
fi

if [ "$CRASHES" -eq 0 ] && [ "$ERRORS" -eq 0 ] && [ "$BATCH_FLUSH" -gt 0 ]; then
    echo "✅ SUCCESS: No crashes or errors detected"
    echo "✅ SUCCESS: Batches processed successfully"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "Analysis complete!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "For detailed investigation:"
echo "  grep ERROR $LOG_FILE"
echo "  grep CRASH $LOG_FILE"
echo "  grep 'Batch flush' $LOG_FILE"
echo ""