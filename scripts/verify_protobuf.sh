#!/bin/bash
# verify_protobuf.sh — canónica = verdad, descubrimiento dinámico de copias.
# Cualquier */proto/network_security.pb.{cc,h} bajo /vagrant debe igualar la
# canónica. Ausente = OK (no compilado). Presente-pero-distinto = DRIFT.
echo "🔍 Verificando consistencia protobuf (canónica = verdad)..."
echo "========================================"

CANONICAL_DIR="/vagrant/protobuf"
declare -a FILES=("network_security.pb.cc" "network_security.pb.h")
ERRORS=0

for FILE in "${FILES[@]}"; do
    if [ ! -f "$CANONICAL_DIR/$FILE" ]; then
        echo "❌ Canónica ausente: $CANONICAL_DIR/$FILE — corre 'make proto' primero"
        ERRORS=$((ERRORS + 1))
    fi
done
[ $ERRORS -gt 0 ] && { echo "❌ Falta la fuente canónica."; exit 1; }

for FILE in "${FILES[@]}"; do
    echo ""
    echo "📄 $FILE"
    REF=$(sha256sum "$CANONICAL_DIR/$FILE" | cut -d ' ' -f1)
    echo "   📌 $CANONICAL_DIR: $REF"
    while IFS= read -r COPY; do
        CUR=$(sha256sum "$COPY" | cut -d ' ' -f1)
        if [ "$CUR" == "$REF" ]; then
            echo "   ✅ $COPY"
        else
            echo "   ❌ $COPY: $CUR (DRIFT vs canónica)"
            ERRORS=$((ERRORS + 1))
        fi
    done < <(find /vagrant -type f -path "*/proto/$FILE" ! -path "$CANONICAL_DIR/*" 2>/dev/null)
done

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ Todas las copias coinciden con la canónica. Protobuf unificado correcto."
    exit 0
else
    echo "❌ $ERRORS discrepancia(s). Revisar consistencia protobuf."
    exit 1
fi
