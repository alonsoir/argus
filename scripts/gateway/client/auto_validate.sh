#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# ML Defender - Automated Gateway Validation
# ══════════════════════════════════════════════════════════════════════════════
# Purpose: End-to-end automated validation of gateway mode
# Location: /vagrant/scripts/gateway/client/auto_validate.sh
# Usage: ./auto_validate.sh
# ══════════════════════════════════════════════════════════════════════════════

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🤖 AUTOMATED GATEWAY MODE VALIDATION                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will:"
echo "  1. Validate basic connectivity"
echo "  2. Generate test traffic"
echo "  3. Instruct you to validate on defender"
echo ""
read -p "Start automated validation? (y/n): " START

if [ "$START" != "y" ]; then
    echo "Validation cancelled"
    exit 0
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Connectivity Validation
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PHASE 1: Connectivity Validation"
echo "═══════════════════════════════════════════════════════════"

echo "Testing gateway reachability..."
if ping -c 3 192.168.100.1 > /dev/null 2>&1; then
    echo "  ✅ Defender gateway reachable (192.168.100.1)"
else
    echo "  ❌ ERROR: Gateway not reachable"
    echo "     Check defender VM is running: vagrant status defender"
    exit 1
fi

echo "Testing internet connectivity (via gateway)..."
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
    echo "  ✅ Internet reachable (via gateway)"
else
    echo "  ⚠️  WARNING: Internet not reachable"
    echo "     Gateway mode can still be validated with local traffic"
fi

echo "Verifying routing configuration (Qwen test)..."
ROUTE_INFO=$(ip route get 8.8.8.8 from 192.168.100.50 2>/dev/null)
echo "  Route: $ROUTE_INFO"

if echo "$ROUTE_INFO" | grep -q "via 192.168.100.1"; then
    echo "  ✅ Routing correct (via defender gateway)"
else
    echo "  ⚠️  WARNING: Routing may be incorrect"
fi

echo ""
echo "✅ Phase 1 COMPLETE - Connectivity OK"

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Traffic Generation
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PHASE 2: Traffic Generation"
echo "═══════════════════════════════════════════════════════════"

echo "Generating HTTP/HTTPS traffic..."
for i in {1..5}; do
    echo "  Request $i/5..."
    curl -s -I --connect-timeout 2 http://example.com > /dev/null 2>&1
    curl -s -I --connect-timeout 2 https://www.google.com > /dev/null 2>&1
    sleep 0.5
done

echo ""
echo "Generating ICMP traffic..."
ping -c 5 8.8.8.8 > /dev/null 2>&1 &

echo "Generating DNS queries..."
for i in {1..3}; do
    dig @8.8.8.8 google.com +short > /dev/null 2>&1
    sleep 0.3
done

echo ""
echo "Waiting for all traffic to complete..."
wait

echo ""
echo "✅ Phase 2 COMPLETE - Traffic generated"
echo "   • 10 HTTP/HTTPS requests"
echo "   • 5 ICMP pings"
echo "   • 3 DNS queries"

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Validation Instructions
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PHASE 3: Validation on Defender"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "⚠️  IMPORTANT: Now run on defender VM:"
echo ""
echo "   vagrant ssh defender"
echo "   /vagrant/scripts/gateway/defender/validate_gateway.sh"
echo ""
echo "Expected result:"
echo "   ✅ ✅ ✅ GATEWAY MODE VALIDATED ✅ ✅ ✅"
echo "   Events captured on eth3 (ifindex=5)"
echo ""
echo "If validation fails:"
echo "   1. Check sniffer is running:"
echo "      /vagrant/scripts/gateway/defender/start_gateway_test.sh"
echo ""
echo "   2. Check XDP attachment:"
echo "      sudo bpftool net show"
echo ""
echo "   3. Check interface configuration:"
echo "      sudo bpftool map dump name iface_configs"
echo ""
echo "   4. Monitor traffic with tcpdump:"
echo "      sudo tcpdump -i eth3 -c 10"
echo ""
echo "   5. View dashboard:"
echo "      /vagrant/scripts/gateway/defender/gateway_dashboard.sh"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ CLIENT SIDE VALIDATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"