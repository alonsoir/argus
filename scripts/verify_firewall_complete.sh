#!/bin/bash
# ============================================================================
# Verificación EXHAUSTIVA del código de firewall-acl-agent
# ============================================================================
# Este script analiza en detalle qué capacidades tiene firewall actualmente
# y qué necesita para integrar descifrado/descompresión + etcd.
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

FIREWALL_SRC="/vagrant/firewall-acl-agent/src"
FIREWALL_INCLUDE="/vagrant/firewall-acl-agent/include"
FIREWALL_CMAKE="/vagrant/firewall-acl-agent/CMakeLists.txt"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Firewall Code Analysis - Comprehensive Verification      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -d "$FIREWALL_SRC" ]; then
    echo -e "${RED}❌ Firewall source directory not found: $FIREWALL_SRC${NC}"
    exit 1
fi

# ============================================================================
# SECTION 1: CURRENT CAPABILITIES
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "1️⃣  CURRENT CAPABILITIES"
echo "════════════════════════════════════════════════════════════"
echo ""

# 1.1 ZMQ Integration
echo -e "${CYAN}1.1 ZMQ Integration${NC}"
if grep -r "zmq.hpp\|zmq::socket" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ZMQ found${NC}"
    ZMQ_FILES=$(grep -rl "zmq.hpp\|zmq::socket" "$FIREWALL_SRC" | head -3)
    echo "$ZMQ_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ ZMQ NOT found${NC}"
fi
echo ""

# 1.2 Protobuf Parsing
echo -e "${CYAN}1.2 Protobuf Parsing${NC}"
if grep -r "ParseFromArray\|PacketEvent" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Protobuf parsing found${NC}"
    PROTO_FILES=$(grep -rl "ParseFromArray" "$FIREWALL_SRC" | head -3)
    echo "$PROTO_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ Protobuf parsing NOT found${NC}"
fi
echo ""

# 1.3 IPTables/IPSet Integration
echo -e "${CYAN}1.3 IPTables/IPSet Integration${NC}"
if grep -r "ipset\|iptables\|system(" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ IPTables/IPSet integration found${NC}"
    IPTABLES_COUNT=$(grep -r "ipset\|iptables" "$FIREWALL_SRC" | wc -l)
    echo "   Found $IPTABLES_COUNT references"
else
    echo -e "${RED}❌ IPTables/IPSet integration NOT found${NC}"
fi
echo ""

# 1.4 JSON Config Loading
echo -e "${CYAN}1.4 JSON Config Loading${NC}"
if grep -r "nlohmann/json\|json::" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ JSON config loading found${NC}"
    JSON_FILES=$(grep -rl "nlohmann/json" "$FIREWALL_SRC" | head -3)
    echo "$JSON_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ JSON config loading NOT found${NC}"
fi
echo ""

# ============================================================================
# SECTION 2: MISSING CAPABILITIES (CRITICAL)
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "2️⃣  MISSING CAPABILITIES (For Day 23)"
echo "════════════════════════════════════════════════════════════"
echo ""

MISSING_COUNT=0

# 2.1 etcd-client Integration
echo -e "${CYAN}2.1 etcd-client Integration${NC}"
if grep -r "etcd_client\.h\|etcd_client_init" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ etcd-client integration found${NC}"
    ETCD_FILES=$(grep -rl "etcd_client" "$FIREWALL_SRC" | head -3)
    echo "$ETCD_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ etcd-client integration MISSING${NC}"
    echo "   Needed for: Getting crypto tokens from etcd-server"
    echo "   Impact: Cannot get decryption keys"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi
echo ""

# 2.2 ChaCha20-Poly1305 Decryption
echo -e "${CYAN}2.2 ChaCha20-Poly1305 Decryption${NC}"
if grep -r "chacha20\|ChaCha20\|EVP_chacha20" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ChaCha20 decryption found${NC}"
    CHACHA_FILES=$(grep -rl "chacha20" "$FIREWALL_SRC" | head -3)
    echo "$CHACHA_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ ChaCha20 decryption MISSING${NC}"
    echo "   Needed for: Decrypting data from ml-detector"
    echo "   Impact: Cannot read encrypted messages"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi
echo ""

# 2.3 LZ4 Decompression
echo -e "${CYAN}2.3 LZ4 Decompression${NC}"
if grep -r "lz4\.h\|LZ4_decompress" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ LZ4 decompression found${NC}"
    LZ4_FILES=$(grep -rl "lz4\|LZ4" "$FIREWALL_SRC" | head -3)
    echo "$LZ4_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ LZ4 decompression MISSING${NC}"
    echo "   Needed for: Decompressing data from ml-detector"
    echo "   Impact: Cannot read compressed messages"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi
echo ""

# 2.4 Transport Config Reading
echo -e "${CYAN}2.4 Transport Config Reading${NC}"
if grep -r "\"transport\"\|\.transport\[\"compression\"\]" "$FIREWALL_SRC" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Transport config reading found${NC}"
    TRANSPORT_FILES=$(grep -rl "transport" "$FIREWALL_SRC" | head -3)
    echo "$TRANSPORT_FILES" | while read f; do echo "   - $f"; done
else
    echo -e "${RED}❌ Transport config reading MISSING${NC}"
    echo "   Needed for: Reading encryption/compression settings"
    echo "   Impact: Cannot enable/disable features via config"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi
echo ""

# ============================================================================
# SECTION 3: CMAKE ANALYSIS
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "3️⃣  CMAKE CONFIGURATION"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ -f "$FIREWALL_CMAKE" ]; then
    echo -e "${GREEN}✅ CMakeLists.txt found${NC}"
    echo ""

    # Check for required libraries
    echo -e "${CYAN}3.1 Linked Libraries${NC}"

    if grep "etcd_client" "$FIREWALL_CMAKE" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ etcd_client library linked${NC}"
    else
        echo -e "${RED}❌ etcd_client library NOT linked${NC}"
        echo "   Must add: find_library(ETCD_CLIENT_LIB etcd_client ...)"
    fi

    if grep "lz4" "$FIREWALL_CMAKE" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ LZ4 library linked${NC}"
    else
        echo -e "${RED}❌ LZ4 library NOT linked${NC}"
        echo "   Must add: target_link_libraries(... lz4)"
    fi

    if grep "ssl\|crypto" "$FIREWALL_CMAKE" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OpenSSL libraries linked${NC}"
    else
        echo -e "${RED}❌ OpenSSL libraries NOT linked${NC}"
        echo "   Must add: target_link_libraries(... ssl crypto)"
    fi

    echo ""

    # Check for include directories
    echo -e "${CYAN}3.2 Include Directories${NC}"

    if grep "etcd-client/include" "$FIREWALL_CMAKE" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ etcd-client includes configured${NC}"
    else
        echo -e "${RED}❌ etcd-client includes NOT configured${NC}"
        echo "   Must add: target_include_directories(... ../etcd-client/include)"
    fi
else
    echo -e "${RED}❌ CMakeLists.txt NOT found${NC}"
fi
echo ""

# ============================================================================
# SECTION 4: FILE STRUCTURE
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "4️⃣  FILE STRUCTURE"
echo "════════════════════════════════════════════════════════════"
echo ""

echo -e "${CYAN}Source files:${NC}"
if [ -d "$FIREWALL_SRC" ]; then
    ls -1 "$FIREWALL_SRC"/*.cpp 2>/dev/null | while read f; do
        filename=$(basename "$f")
        lines=$(wc -l < "$f")
        echo "   $filename ($lines lines)"
    done
else
    echo "   (No .cpp files found)"
fi
echo ""

echo -e "${CYAN}Header files:${NC}"
if [ -d "$FIREWALL_INCLUDE" ]; then
    ls -1 "$FIREWALL_INCLUDE"/*.h 2>/dev/null | while read f; do
        filename=$(basename "$f")
        echo "   $filename"
    done
elif ls "$FIREWALL_SRC"/*.h 2>/dev/null | grep -q .; then
    ls -1 "$FIREWALL_SRC"/*.h | while read f; do
        filename=$(basename "$f")
        echo "   $filename"
    done
else
    echo "   (No .h files found)"
fi
echo ""

# ============================================================================
# SECTION 5: SUMMARY & RECOMMENDATIONS
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "5️⃣  SUMMARY & RECOMMENDATIONS"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ $MISSING_COUNT -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Firewall HAS all required capabilities                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Update firewall.json with 'transport' section"
    echo "  2. Verify etcd settings in config"
    echo "  3. Test: make firewall && make run-lab-dev-day23"
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ Firewall MISSING $MISSING_COUNT critical capabilities           ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Required modifications:${NC}"
    echo ""

    if ! grep -r "etcd_client" "$FIREWALL_SRC" > /dev/null 2>&1; then
        echo "  1️⃣  Add etcd-client integration:"
        echo "     - #include \"etcd_client.h\" in main.cpp"
        echo "     - Call etcd_client_init() on startup"
        echo "     - Call etcd_client_get_token() to get crypto keys"
        echo "     - Link library in CMakeLists.txt"
        echo ""
    fi

    if ! grep -r "chacha20\|ChaCha20" "$FIREWALL_SRC" > /dev/null 2>&1; then
        echo "  2️⃣  Add ChaCha20-Poly1305 decryption:"
        echo "     - #include <openssl/evp.h>"
        echo "     - Implement decrypt_chacha20_poly1305() function"
        echo "     - Use in ZMQ receive loop"
        echo "     - Link OpenSSL in CMakeLists.txt"
        echo ""
    fi

    if ! grep -r "lz4\|LZ4" "$FIREWALL_SRC" > /dev/null 2>&1; then
        echo "  3️⃣  Add LZ4 decompression:"
        echo "     - #include <lz4.h>"
        echo "     - Implement decompress_lz4() function"
        echo "     - Use after decryption, before protobuf parse"
        echo "     - Link LZ4 in CMakeLists.txt"
        echo ""
    fi

    if ! grep -r "\"transport\"" "$FIREWALL_SRC" > /dev/null 2>&1; then
        echo "  4️⃣  Add transport config reading:"
        echo "     - Read config[\"transport\"][\"encryption\"][\"enabled\"]"
        echo "     - Read config[\"transport\"][\"compression\"][\"enabled\"]"
        echo "     - Use flags to enable/disable features"
        echo ""
    fi

    echo -e "${YELLOW}Estimated time: 30-60 minutes${NC}"
    echo ""
    echo "📚 See detailed guide in: FIREWALL_INTEGRATION_GUIDE.md"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

exit $([ $MISSING_COUNT -eq 0 ] && echo 0 || echo 1)