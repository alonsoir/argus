#!/bin/bash
#===----------------------------------------------------------------------===//
# ML Defender - Firewall ACL Agent
# Script para aplicar correcciones a main.cpp
#===----------------------------------------------------------------------===//

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/vagrant/firewall-acl-agent"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ML Defender - Aplicar Correcciones a main.cpp       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que existe el proyecto
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}ERROR: No se encuentra el proyecto en $PROJECT_ROOT${NC}"
    exit 1
fi

# Verificar que existe el main.cpp corregido
# Buscar en varias ubicaciones posibles
MAIN_CPP_SOURCE=""
if [ -f "$SCRIPT_DIR/main.cpp" ]; then
    MAIN_CPP_SOURCE="$SCRIPT_DIR/main.cpp"
elif [ -f "./main.cpp" ]; then
    MAIN_CPP_SOURCE="./main.cpp"
elif [ -f "../main.cpp" ]; then
    MAIN_CPP_SOURCE="../main.cpp"
fi

if [ -z "$MAIN_CPP_SOURCE" ]; then
    echo -e "${RED}ERROR: No se encuentra main.cpp corregido${NC}"
    echo "Buscado en:"
    echo "  - $SCRIPT_DIR/main.cpp"
    echo "  - ./main.cpp"
    echo "  - ../main.cpp"
    echo ""
    echo "Por favor, ejecuta este script desde el directorio donde descargaste los archivos."
    exit 1
fi

echo "Usando: $MAIN_CPP_SOURCE"

# Hacer backup del main.cpp original (si existe)
if [ -f "$PROJECT_ROOT/src/main.cpp" ]; then
    BACKUP_FILE="$PROJECT_ROOT/src/main.cpp.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}[1/3]${NC} Creando backup del main.cpp original..."
    cp "$PROJECT_ROOT/src/main.cpp" "$BACKUP_FILE"
    echo -e "      ${GREEN}✓${NC} Backup guardado: $BACKUP_FILE"
else
    echo -e "${YELLOW}[1/3]${NC} No hay main.cpp previo, no se requiere backup"
fi

# Copiar el main.cpp corregido
echo -e "${YELLOW}[2/3]${NC} Copiando main.cpp corregido..."
cp "$MAIN_CPP_SOURCE" "$PROJECT_ROOT/src/main.cpp"
echo -e "      ${GREEN}✓${NC} main.cpp actualizado"

# Verificar que se copió correctamente
if [ -f "$PROJECT_ROOT/src/main.cpp" ]; then
    LINES=$(wc -l < "$PROJECT_ROOT/src/main.cpp")
    echo -e "${YELLOW}[3/3]${NC} Verificando archivo..."
    echo -e "      ${GREEN}✓${NC} Archivo instalado correctamente ($LINES líneas)"
else
    echo -e "${RED}ERROR: No se pudo copiar el archivo${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✓ Correcciones Aplicadas Exitosamente      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Cambios aplicados:"
echo "  • Estructuras de configuración agregadas (BatchConfig, ZMQConfig, etc.)"
echo "  • Nombres de campos corregidos (name, type, hashsize, maxelem)"
echo "  • Conversión de strings a enums implementada"
echo "  • Métodos de API corregidos (set_exists, create_set)"
echo ""

echo "Próximos pasos:"
echo ""
echo -e "${BLUE}1. Compilar el proyecto:${NC}"
echo "   cd $PROJECT_ROOT/build"
echo "   cmake .."
echo "   make -j\$(nproc)"
echo ""
echo -e "${BLUE}2. Probar la configuración:${NC}"
echo "   sudo ./firewall-acl-agent --test-config -c ../config/firewall.json"
echo ""
echo -e "${BLUE}3. Ejecutar el agente:${NC}"
echo "   sudo ./firewall-acl-agent -c ../config/firewall.json"
echo ""

echo -e "${GREEN}Listo para compilar!${NC}"
echo ""