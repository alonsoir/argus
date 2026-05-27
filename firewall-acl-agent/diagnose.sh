#!/bin/bash
#===----------------------------------------------------------------------===//
# ML Defender - Firewall ACL Agent
# Diagnostic Script - Verify Project Structure
#===----------------------------------------------------------------------===//

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  ML Defender - Firewall ACL Agent Diagnostics         ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

PROJECT_ROOT="/vagrant/firewall-acl-agent"
ERRORS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ((ERRORS++))
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ((ERRORS++))
        return 1
    fi
}

echo "=== Checking Project Structure ==="
echo ""

# Check directories
echo "Directories:"
check_dir "$PROJECT_ROOT"
check_dir "$PROJECT_ROOT/src"
check_dir "$PROJECT_ROOT/src/core"
check_dir "$PROJECT_ROOT/src/api"
check_dir "$PROJECT_ROOT/include"
check_dir "$PROJECT_ROOT/include/firewall"
check_dir "$PROJECT_ROOT/config"
check_dir "$PROJECT_ROOT/tests"
echo ""

# Check header files
echo "Header Files:"
check_file "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"
check_file "$PROJECT_ROOT/include/firewall/iptables_wrapper.hpp"
check_file "$PROJECT_ROOT/include/firewall/batch_processor.hpp"
check_file "$PROJECT_ROOT/include/firewall/zmq_subscriber.hpp"
echo ""

# Check source files
echo "Source Files:"
check_file "$PROJECT_ROOT/src/main.cpp"
check_file "$PROJECT_ROOT/src/core/ipset_wrapper.cpp"
check_file "$PROJECT_ROOT/src/core/iptables_wrapper.cpp"
check_file "$PROJECT_ROOT/src/core/batch_processor.cpp"
check_file "$PROJECT_ROOT/src/api/zmq_subscriber.cpp"
echo ""

# Check configuration
echo "Configuration:"
check_file "$PROJECT_ROOT/config/firewall.json"
check_file "$PROJECT_ROOT/CMakeLists.txt"
echo ""

# Check for IPSetConfig structure
echo "=== Checking IPSetConfig Structure ==="
if check_file "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
    echo "Verifying IPSetConfig field names..."

    if grep -q "std::string setname" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Field 'setname' found"
    else
        echo -e "${RED}✗${NC} Field 'setname' not found (should be 'setname', not 'set_name')"
        ((ERRORS++))
    fi

    if grep -q "std::string typename_" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Field 'typename_' found"
    else
        echo -e "${RED}✗${NC} Field 'typename_' not found (should be 'typename_', not 'set_type')"
        ((ERRORS++))
    fi

    if grep -q "uint32_t hashsize" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Field 'hashsize' found"
    else
        echo -e "${RED}✗${NC} Field 'hashsize' not found (should be 'hashsize', not 'hash_size')"
        ((ERRORS++))
    fi

    if grep -q "uint32_t maxelem" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Field 'maxelem' found"
    else
        echo -e "${RED}✗${NC} Field 'maxelem' not found (should be 'maxelem', not 'max_elements')"
        ((ERRORS++))
    fi
fi
echo ""

# Check for correct method names
echo "=== Checking Method Names ==="
if check_file "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
    if grep -q "bool set_exists" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Method 'set_exists()' found"
    else
        echo -e "${YELLOW}!${NC} Method 'set_exists()' not found (main.cpp expects this)"
        ((ERRORS++))
    fi

    if grep -q "bool create_set" "$PROJECT_ROOT/include/firewall/ipset_wrapper.hpp"; then
        echo -e "${GREEN}✓${NC} Method 'create_set()' found"
    else
        echo -e "${YELLOW}!${NC} Method 'create_set()' not found"
        ((ERRORS++))
    fi
fi
echo ""

# Summary
echo "=== Diagnostic Summary ==="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "You can proceed with compilation:"
    echo "  cd $PROJECT_ROOT/build"
    echo "  cmake .."
    echo "  make -j\$(nproc)"
    exit 0
else
    echo -e "${RED}✗ Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Please fix the issues above before compiling."
    echo "Common fixes:"
    echo "  1. Copy the corrected main.cpp to src/main.cpp"
    echo "  2. Verify IPSetConfig field names in ipset_wrapper.hpp"
    echo "  3. Ensure all required files exist"
    exit 1
fi