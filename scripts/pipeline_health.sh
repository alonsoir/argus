#!/usr/bin/env bash
# ML Defender — Pipeline Health Monitor
# Muestra qué componentes están activos vs idle
# Uso: bash scripts/pipeline_health.sh

COMPONENTS=(
    "etcd-server:etcd-server/build-debug/etcd-server"
    "rag-security:rag/build/rag-security"
    "rag-ingester:rag-ingester/build-debug/rag-ingester"
    "ml-detector:ml-detector/build-debug/ml-detector"
    "sniffer:sniffer/build-debug/sniffer"
    "firewall:firewall-acl-agent/build-debug/firewall-acl-agent"
)

LOG_DIR="/vagrant/logs/lab"
IDLE_THRESHOLD_SECS=30  # Si el log no creció en N segundos → IDLE

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      ML Defender — Pipeline Health Monitor                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Vagrant VM status (no levantar nada, solo consultar)
echo "  🖥  VM Status:"
DEFENDER_STATUS=$(vagrant status defender 2>/dev/null | grep "defender" | awk '{print $2}')
CLIENT_STATUS=$(vagrant status client 2>/dev/null | grep "client" | awk '{print $2}')
echo "    defender: ${DEFENDER_STATUS:-unknown}"
echo "    client:   ${CLIENT_STATUS:-unknown}"
echo ""

# Componentes del pipeline
echo "  📦 Pipeline Components:"
printf "    %-22s %-10s %-10s %-10s\n" "Component" "Status" "PID" "Log Activity"
printf "    %-22s %-10s %-10s %-10s\n" "---------" "------" "---" "------------"

for entry in "${COMPONENTS[@]}"; do
    name="${entry%%:*}"
    pattern="${entry##*:}"
    binary=$(basename "$pattern")

    # Buscar PID del proceso real (no el grep ni el sudo)
    pid=$(vagrant ssh defender -c "ps xa | grep '$binary' | grep -v grep" 2>/dev/null | awk '{print $1}' | tail -1)

    if [ -z "$pid" ]; then
        printf "    %-22s %-10s %-10s %-10s\n" "$name" "❌ DOWN" "-" "-"
        continue
    fi

    # Log activity: tiempo desde última modificación
    logfile=""
    case "$name" in
        etcd-server)    logfile="$LOG_DIR/etcd-server.log" ;;
        rag-security)   logfile="$LOG_DIR/rag-security.log" ;;
        rag-ingester)   logfile="$LOG_DIR/rag-ingester.log" ;;
        ml-detector)    logfile="$LOG_DIR/ml-detector.log" ;;
        sniffer)        logfile="$LOG_DIR/sniffer.log" ;;
        firewall)       logfile="$LOG_DIR/firewall-agent.log" ;;
    esac

    if [ -f "$logfile" ]; then
        # Segundos desde última modificación
        now=$(date +%s)
        last_mod=$(stat -c %Y "$logfile" 2>/dev/null || stat -f %m "$logfile" 2>/dev/null)
        delta=$((now - last_mod))

        if [ "$delta" -lt "$IDLE_THRESHOLD_SECS" ]; then
            activity="🟢 ACTIVE (${delta}s ago)"
        else
            activity="🟡 IDLE (${delta}s ago)"
        fi
    else
        activity="❓ no log"
    fi

    printf "    %-22s %-10s %-10s %s\n" "$name" "✅ UP" "$pid" "$activity"
done

echo ""

# ML-Detector stats rápido
echo "  📊 ML-Detector last stats:"
vagrant ssh -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1" 2>/dev/null \
    | sed 's/.*📊 Stats:/   /' || echo "    (no disponible)"

echo ""

# Client VM warning si ya está up
if [ "$CLIENT_STATUS" = "running" ]; then
    echo "  ⚠️  VM 'client' ya está RUNNING — no ejecutar 'vagrant up client'"
else
    echo "  ℹ️  VM 'client' está $CLIENT_STATUS — ejecutar 'vagrant up client' para replay"
fi

echo ""
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""