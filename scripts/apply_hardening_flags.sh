#!/bin/bash
# apply_hardening_flags.sh
# Script para aplicar flags de hardening a todos los componentes
#
# USO:
#   ./apply_hardening_flags.sh --help
#   ./apply_hardening_flags.sh --dry-run
#   ./apply_hardening_flags.sh --apply

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/vagrant"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    cat << EOF
🛡️ ML Defender - Hardening Flags Application Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --help          Show this help message
    --dry-run       Show what would be changed (no modifications)
    --apply         Apply patches to Makefiles and CMakeLists.txt
    --status        Check current hardening status

DESCRIPTION:
    Este script añade flags de hardening (desactivados por defecto) a:
    - sniffer/Makefile
    - ml-detector/CMakeLists.txt
    - firewall-acl-agent/CMakeLists.txt
    - rag-security/CMakeLists.txt

IMPORTANT:
    Los flags estarán DESACTIVADOS por defecto.
    Para activarlos, ver README_HARDENING.md

EXAMPLES:
    # Ver qué cambiaría (sin modificar)
    $0 --dry-run

    # Aplicar patches
    $0 --apply

    # Ver estado actual
    $0 --status

EOF
}

check_status() {
    echo -e "${BLUE}Checking hardening status...${NC}"
    echo ""

    # Sniffer
    if grep -q "HARDENING_ENABLED" "$PROJECT_ROOT/sniffer/Makefile" 2>/dev/null; then
        if grep -q "^HARDENING_ENABLED = 1" "$PROJECT_ROOT/sniffer/Makefile" 2>/dev/null; then
            echo -e "sniffer/Makefile: ${GREEN}✅ Hardening ACTIVE${NC}"
        else
            echo -e "sniffer/Makefile: ${YELLOW}⚙️ Prepared (INACTIVE)${NC}"
        fi
    else
        echo -e "sniffer/Makefile: ${RED}❌ Not prepared${NC}"
    fi

    # ml-detector
    if grep -q "ENABLE_HARDENING" "$PROJECT_ROOT/ml-detector/CMakeLists.txt" 2>/dev/null; then
        echo -e "ml-detector/CMakeLists.txt: ${YELLOW}⚙️ Prepared (OFF by default)${NC}"
    else
        echo -e "ml-detector/CMakeLists.txt: ${RED}❌ Not prepared${NC}"
    fi

    # firewall
    if grep -q "ENABLE_HARDENING" "$PROJECT_ROOT/firewall-acl-agent/CMakeLists.txt" 2>/dev/null; then
        echo -e "firewall/CMakeLists.txt: ${YELLOW}⚙️ Prepared (OFF by default)${NC}"
    else
        echo -e "firewall/CMakeLists.txt: ${RED}❌ Not prepared${NC}"
    fi

    # rag
    if grep -q "ENABLE_HARDENING" "$PROJECT_ROOT/rag/CMakeLists.txt" 2>/dev/null; then
        echo -e "rag/CMakeLists.txt: ${YELLOW}⚙️ Prepared (OFF by default)${NC}"
    else
        echo -e "rag/CMakeLists.txt: ${RED}❌ Not prepared${NC}"
    fi
}

dry_run() {
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
    echo ""
    echo "Would add hardening flags to:"
    echo "  - sniffer/Makefile"
    echo "  - ml-detector/CMakeLists.txt"
    echo "  - firewall-acl-agent/CMakeLists.txt"
    echo "  - rag-security/CMakeLists.txt"
    echo ""
    echo "All flags would be DISABLED by default."
    echo "See README_HARDENING.md for activation instructions."
}

apply_patches() {
    echo -e "${GREEN}Applying hardening flags...${NC}"
    echo ""

    # Backup originals
    echo "Creating backups..."
    cp "$PROJECT_ROOT/sniffer/Makefile" "$PROJECT_ROOT/sniffer/Makefile.pre-hardening" 2>/dev/null || true

    echo -e "${YELLOW}⚠️ MANUAL STEP REQUIRED:${NC}"
    echo ""
    echo "Los patches están en:"
    echo "  - /vagrant/docs/hardening/Makefile_hardening.patch"
    echo "  - /vagrant/docs/hardening/CMakeLists_hardening.patch"
    echo ""
    echo "Aplicar manualmente copiando las secciones a cada archivo."
    echo "Ver README_HARDENING.md para instrucciones completas."
    echo ""
    echo -e "${GREEN}Reason for manual application:${NC}"
    echo "Cada componente tiene estructura diferente, mejor copiar secciones"
    echo "relevantes que intentar patch automático que podría romper cosas."
}

# Main
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --status)
        check_status
        exit 0
        ;;
    --dry-run)
        dry_run
        exit 0
        ;;
    --apply)
        apply_patches
        exit 0
        ;;
    *)
        echo -e "${RED}Error: Unknown option '${1:-}'${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac