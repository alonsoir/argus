#!/bin/bash
# verify_day50_integration.sh
# Verifica que la integración Day 50 está completa

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Day 50 Integration Verification                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

FIREWALL_DIR="/vagrant/firewall-acl-agent"
ERRORS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    local file=$1
    local search_string=$2
    local description=$3

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ MISSING${NC} $description"
        echo "  File not found: $file"
        ((ERRORS++))
        return 1
    fi

    if [ -n "$search_string" ]; then
        if grep -q "$search_string" "$file" 2>/dev/null; then
            echo -e "${GREEN}✓ OK${NC} $description"
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} $description"
            echo "  File exists but missing expected content: '$search_string'"
            ((ERRORS++))
            return 1
        fi
    else
        echo -e "${GREEN}✓ OK${NC} $description"
        return 0
    fi
}

echo "════════════════════════════════════════════════════════"
echo "1. Verificando Headers de Observabilidad"
echo "════════════════════════════════════════════════════════"

check_file \
    "$FIREWALL_DIR/include/firewall_observability_logger.hpp" \
    "class ObservabilityLogger" \
    "firewall_observability_logger.hpp"

check_file \
    "$FIREWALL_DIR/include/crash_diagnostics.hpp" \
    "struct SystemState" \
    "crash_diagnostics.hpp"

echo ""
echo "════════════════════════════════════════════════════════"
echo "2. Verificando main.cpp Refactorizado"
echo "════════════════════════════════════════════════════════"

check_file \
    "$FIREWALL_DIR/src/main.cpp" \
    "firewall_observability_logger.hpp" \
    "main.cpp includes observability header"

check_file \
    "$FIREWALL_DIR/src/main.cpp" \
    "FIREWALL_LOG_INFO" \
    "main.cpp uses observability macros"

check_file \
    "$FIREWALL_DIR/src/main.cpp" \
    "install_crash_handlers" \
    "main.cpp installs crash handlers"

# Check for etcd bug fix (absolute path default)
if grep -q 'config_path = "/vagrant/config/firewall.json"' "$FIREWALL_DIR/src/main.cpp" 2>/dev/null; then
    echo -e "${GREEN}✓ OK${NC} main.cpp has etcd bug fix (absolute path)"
else
    echo -e "${YELLOW}⚠ WARNING${NC} main.cpp may still have relative path (check line ~170)"
    ((ERRORS++))
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "3. Verificando zmq_subscriber.cpp Refactorizado"
echo "════════════════════════════════════════════════════════"

check_file \
    "$FIREWALL_DIR/src/api/zmq_subscriber.cpp" \
    "firewall_observability_logger.hpp" \
    "zmq_subscriber.cpp includes observability header"

check_file \
    "$FIREWALL_DIR/src/api/zmq_subscriber.cpp" \
    "TRACK_OPERATION" \
    "zmq_subscriber.cpp uses operation tracking"

check_file \
    "$FIREWALL_DIR/src/api/zmq_subscriber.cpp" \
    "INCREMENT_COUNTER" \
    "zmq_subscriber.cpp updates global counters"

echo ""
echo "════════════════════════════════════════════════════════"
echo "4. Verificando batch_processor.cpp Refactorizado"
echo "════════════════════════════════════════════════════════"

check_file \
    "$FIREWALL_DIR/src/core/batch_processor.cpp" \
    "firewall_observability_logger.hpp" \
    "batch_processor.cpp includes observability header"

check_file \
    "$FIREWALL_DIR/src/core/batch_processor.cpp" \
    "FIREWALL_LOG_BATCH" \
    "batch_processor.cpp uses batch logging"

check_file \
    "$FIREWALL_DIR/src/core/batch_processor.cpp" \
    "FIREWALL_LOG_IPSET" \
    "batch_processor.cpp logs ipset operations"

echo ""
echo "════════════════════════════════════════════════════════"
echo "5. Verificando CMakeLists.txt"
echo "════════════════════════════════════════════════════════"

check_file \
    "$FIREWALL_DIR/CMakeLists.txt" \
    "Day 50" \
    "CMakeLists.txt updated for Day 50"

check_file \
    "$FIREWALL_DIR/CMakeLists.txt" \
    "backtrace" \
    "CMakeLists.txt searches for backtrace library"

echo ""
echo "════════════════════════════════════════════════════════"
echo "6. Verificando Estructura de Logs"
echo "════════════════════════════════════════════════════════"

LOG_DIR="/vagrant/logs/firewall-acl-agent"

if [ -d "$LOG_DIR" ]; then
    echo -e "${GREEN}✓ OK${NC} Log directory exists: $LOG_DIR"
else
    echo -e "${YELLOW}⚠ WARNING${NC} Log directory missing (will be created at runtime)"
    echo "  Creating directory..."
    mkdir -p "$LOG_DIR" 2>/dev/null && echo -e "${GREEN}✓ Created${NC}" || echo -e "${RED}✗ Failed${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "7. Prueba de Compilación"
echo "════════════════════════════════════════════════════════"

cd "$FIREWALL_DIR"

if [ -f "Makefile" ]; then
    echo "Intentando compilar (esto puede tardar)..."
    if make clean >/dev/null 2>&1 && make -j$(nproc) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC} Compilation successful"

        # Check if binary exists
        if [ -f "firewall-acl-agent" ]; then
            echo -e "${GREEN}✓ OK${NC} Binary created: firewall-acl-agent"

            # Check binary size (should be reasonable)
            BINARY_SIZE=$(stat -f%z "firewall-acl-agent" 2>/dev/null || stat -c%s "firewall-acl-agent" 2>/dev/null)
            echo "  Binary size: $(numfmt --to=iec $BINARY_SIZE 2>/dev/null || echo "$BINARY_SIZE bytes")"
        else
            echo -e "${RED}✗ FAILED${NC} Binary not created"
            ((ERRORS++))
        fi
    else
        echo -e "${RED}✗ FAILED${NC} Compilation failed"
        echo "  Run 'make' manually to see errors"
        ((ERRORS++))
    fi
else
    echo -e "${YELLOW}⚠ WARNING${NC} No Makefile found, skipping compilation test"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "8. Verificando Dependencias del Sistema"
echo "════════════════════════════════════════════════════════"

# Check for backtrace library
if ldconfig -p 2>/dev/null | grep -q libbacktrace; then
    echo -e "${GREEN}✓ OK${NC} libbacktrace found in system"
else
    echo -e "${YELLOW}⚠ INFO${NC} libbacktrace not found (will use execinfo.h fallback)"
fi

# Check for required libraries
for lib in libzmq libprotobuf jsoncpp; do
    if ldconfig -p 2>/dev/null | grep -q "$lib"; then
        echo -e "${GREEN}✓ OK${NC} $lib found"
    else
        echo -e "${RED}✗ MISSING${NC} $lib not found"
        ((ERRORS++))
    fi
done

echo ""
echo "════════════════════════════════════════════════════════"
echo "Resumen de Verificación"
echo "════════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ SUCCESS${NC} All Day 50 components verified!"
    echo ""
    echo "Next steps:"
    echo "  1. Run firewall: ./firewall-acl-agent --config /vagrant/config/firewall.json --verbose"
    echo "  2. Monitor logs: tail -f /vagrant/logs/firewall-acl-agent/firewall_detailed.log"
    echo "  3. Run YOUR stress test (ml-detector with encryption)"
    echo ""
    exit 0
else
    echo -e "${RED}✗ FAILED${NC} Found $ERRORS issue(s)"
    echo ""
    echo "Please fix the issues above before running the firewall."
    echo ""
    exit 1
fi