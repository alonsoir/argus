#!/bin/bash
# monitor_firewall_logs.sh
# Script de monitoreo de logs Day 50 (NO genera tráfico)
# Se usa DURANTE tu stress test real (ml-detector → firewall)

LOG_FILE="/vagrant/logs/firewall-acl-agent/firewall_detailed.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Day 50 - Firewall Log Monitor                        ║"
echo "║  (Para usar DURANTE tu stress test real)              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${YELLOW}⚠ Log file not found:${NC} $LOG_FILE"
    echo ""
    echo "Waiting for firewall to start and create log file..."
    echo "Press Ctrl+C to cancel"
    echo ""

    # Wait for log file to be created
    while [ ! -f "$LOG_FILE" ]; do
        sleep 1
    done

    echo -e "${GREEN}✓ Log file created!${NC}"
    echo ""
fi

# Display mode selection
echo "Select monitoring mode:"
echo ""
echo "  1) All logs (verbose)"
echo "  2) Errors and crashes only"
echo "  3) Batch operations (BATCH + IPSET)"
echo "  4) Performance metrics"
echo "  5) ZMQ pipeline (decrypt, decompress, parse)"
echo "  6) Split view (errors + batch in parallel)"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo -e "${CYAN}=== Showing ALL logs ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        tail -f "$LOG_FILE"
        ;;

    2)
        echo -e "${RED}=== Showing ERRORS and CRASHES only ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        tail -f "$LOG_FILE" | grep --line-buffered -E "(ERROR|CRASH|WARN)"
        ;;

    3)
        echo -e "${MAGENTA}=== Showing BATCH operations ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        tail -f "$LOG_FILE" | grep --line-buffered -E "(BATCH|IPSET)"
        ;;

    4)
        echo -e "${GREEN}=== Showing PERFORMANCE metrics ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        tail -f "$LOG_FILE" | grep --line-buffered -E "(duration_us|ips_per_second|latency|performance)"
        ;;

    5)
        echo -e "${BLUE}=== Showing ZMQ PIPELINE ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        tail -f "$LOG_FILE" | grep --line-buffered -E "(ZMQ|Decrypt|Decompress|Protobuf parsed)"
        ;;

    6)
        echo -e "${YELLOW}=== Split view: Errors (left) + Batch (right) ===${NC}"
        echo "Opening in tmux split..."
        echo ""

        # Check if tmux is available
        if ! command -v tmux &> /dev/null; then
            echo -e "${RED}✗ tmux not installed${NC}"
            echo "Install with: sudo apt-get install tmux"
            exit 1
        fi

        # Create tmux session with split view
        tmux new-session -d -s firewall_monitor
        tmux split-window -h
        tmux select-pane -t 0
        tmux send-keys "tail -f $LOG_FILE | grep --line-buffered -E '(ERROR|CRASH|WARN)'" C-m
        tmux select-pane -t 1
        tmux send-keys "tail -f $LOG_FILE | grep --line-buffered -E '(BATCH|IPSET)'" C-m
        tmux select-pane -t 0
        tmux attach-session -t firewall_monitor
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac