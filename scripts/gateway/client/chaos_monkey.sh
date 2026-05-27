#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# ML Defender - Chaos Monkey Traffic Generator
# ══════════════════════════════════════════════════════════════════════════════
# Purpose: High-volume traffic generation for stress testing gateway mode
# Author: Grok4 (xAI) - Battle-tested XDP stress methodology
# Location: /vagrant/scripts/gateway/client/chaos_monkey.sh
# Usage: ./chaos_monkey.sh [instances]
# Default: 5 parallel instances
# ══════════════════════════════════════════════════════════════════════════════

INSTANCES=${1:-5}  # Default 5 instances

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🐒 CHAOS MONKEY - Gateway Stress Test (Grok4 Edition)    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  • Instances: $INSTANCES parallel chaos monkeys"
echo "  • Traffic mix: HTTP, DNS, ICMP"
echo "  • Target: Defender gateway (192.168.100.1)"
echo "  • Press Ctrl+C to stop"
echo ""
echo "══════════════════════════════════════════════════════════════"

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping all chaos monkeys..."
    pkill -P $$ 2>/dev/null
    echo "✅ Cleanup complete"
    exit 0
}

trap cleanup EXIT INT TERM

# Single chaos monkey worker
chaos_worker() {
    local ID=$1
    echo "🐒 Chaos Monkey #$ID starting..."

    while true; do
        # HTTP traffic
        curl -s https://www.cloudflare.com/ips-v4 >/dev/null 2>&1 &
        curl -s https://1.1.1.1/cdn-cgi/trace >/dev/null 2>&1 &

        # ICMP traffic
        ping -c 1 8.8.8.8 >/dev/null 2>&1 &

        # DNS queries
        dig @8.8.8.8 google.com +short >/dev/null 2>&1 &
        dig @1.1.1.1 cloudflare.com +short >/dev/null 2>&1 &

        # HTTP to various endpoints
        curl -s http://example.com >/dev/null 2>&1 &
        curl -s https://httpbin.org/get >/dev/null 2>&1 &

        # Small delay between bursts
        sleep 0.1
    done
}

# Launch chaos monkeys
echo ""
echo "🚀 Launching $INSTANCES chaos monkeys..."
echo ""

PIDS=()
for i in $(seq 1 $INSTANCES); do
    chaos_worker $i &
    PIDS+=($!)
    sleep 0.2
done

echo "══════════════════════════════════════════════════════════════"
echo "✅ All chaos monkeys active!"
echo ""
echo "PIDs: ${PIDS[@]}"
echo ""
echo "Monitor gateway mode:"
echo "  • Dashboard: /vagrant/scripts/gateway/defender/gateway_dashboard.sh"
echo "  • Logs:      tail -f /tmp/sniffer_output.log | grep ifindex=5"
echo ""
echo "Expected behavior:"
echo "  • High packet rate on defender eth3"
echo "  • Multiple ifindex=5 events per second"
echo "  • CPU usage: <50% (target)"
echo "  • Zero kernel drops (target)"
echo ""
echo "Press Ctrl+C to stop all chaos monkeys"
echo "══════════════════════════════════════════════════════════════"

# Wait for user interrupt
wait