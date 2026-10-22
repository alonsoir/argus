#!/bin/bash
# ML Defender - Library Verification Script (CORRECTED)
# Verifica FAISS y ONNX Runtime considerando ubicaciones reales

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ML Defender - Library Verification                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ════════════════════════════════════════════════════════════════════
# FAISS Verification
# ════════════════════════════════════════════════════════════════════

echo "🔍 FAISS Verification:"
echo "────────────────────────────────────────────────────────────"

FAISS_OK=true

# Check shared library (.so)
if [ -f /usr/local/lib/libfaiss.so ]; then
    SIZE=$(ls -lh /usr/local/lib/libfaiss.so | awk '{print $5}')
    echo "  ✅ Shared library: /usr/local/lib/libfaiss.so ($SIZE)"
else
    echo "  ❌ Shared library NOT found: /usr/local/lib/libfaiss.so"
    FAISS_OK=false
fi

# Check static library (.a) - optional but good to have
if [ -f /usr/local/lib/libfaiss.a ]; then
    SIZE=$(ls -lh /usr/local/lib/libfaiss.a | awk '{print $5}')
    echo "  ✅ Static library: /usr/local/lib/libfaiss.a ($SIZE)"
fi

# Check headers
if [ -d /usr/local/include/faiss ]; then
    HEADER_COUNT=$(find /usr/local/include/faiss -name "*.h" | wc -l)
    echo "  ✅ Headers: /usr/local/include/faiss/ ($HEADER_COUNT files)"
else
    echo "  ❌ Headers NOT found: /usr/local/include/faiss/"
    FAISS_OK=false
fi

# Check CMake config
if [ -f /usr/local/share/faiss/faiss-config.cmake ]; then
    echo "  ✅ CMake config: /usr/local/share/faiss/faiss-config.cmake"
fi

# Check ldconfig
if sudo ldconfig -p 2>/dev/null | grep -q faiss; then
    echo "  ✅ In ldconfig cache:"
    sudo ldconfig -p | grep faiss | sed 's/^/      /'
else
    echo "  ⚠️  Not in ldconfig cache (run: sudo ldconfig)"
fi

echo ""

# ════════════════════════════════════════════════════════════════════
# ONNX Runtime Verification
# ════════════════════════════════════════════════════════════════════

echo "🔍 ONNX Runtime Verification:"
echo "────────────────────────────────────────────────────────────"

ONNX_OK=true

# Check library (.so)
if [ -f /usr/local/lib/libonnxruntime.so ]; then
    SIZE=$(ls -lh /usr/local/lib/libonnxruntime.so | awk '{print $5}')
    VERSION=$(ls -l /usr/local/lib/libonnxruntime.so.* 2>/dev/null | head -1 | awk '{print $9}')
    echo "  ✅ Library: /usr/local/lib/libonnxruntime.so ($SIZE)"
    if [ -n "$VERSION" ]; then
        echo "     Version: $(basename $VERSION)"
    fi
else
    echo "  ❌ Library NOT found: /usr/local/lib/libonnxruntime.so"
    ONNX_OK=false
fi

# Check headers (loose files, not in subdirectory)
ONNX_HEADERS=$(ls /usr/local/include/onnxruntime*.h 2>/dev/null | wc -l)
if [ "$ONNX_HEADERS" -gt 0 ]; then
    echo "  ✅ Headers: /usr/local/include/onnxruntime*.h ($ONNX_HEADERS files)"
    ls /usr/local/include/onnxruntime*.h | sed 's/^/      /' | head -5
    if [ "$ONNX_HEADERS" -gt 5 ]; then
        echo "      ... and $((ONNX_HEADERS - 5)) more"
    fi
else
    echo "  ❌ Headers NOT found: /usr/local/include/onnxruntime*.h"
    ONNX_OK=false
fi

# Check ldconfig
if sudo ldconfig -p 2>/dev/null | grep -q onnxruntime; then
    echo "  ✅ In ldconfig cache:"
    sudo ldconfig -p | grep onnxruntime | sed 's/^/      /'
else
    echo "  ⚠️  Not in ldconfig cache (run: sudo ldconfig)"
fi

echo ""

# ════════════════════════════════════════════════════════════════════
# Compilation Test
# ════════════════════════════════════════════════════════════════════

echo "🧪 Compilation Test:"
echo "────────────────────────────────────────────────────────────"

# Test FAISS
if [ "$FAISS_OK" == "true" ]; then
    echo "  Testing FAISS compilation..."
    cat > /tmp/test_faiss.cpp << 'EOF'
#include <faiss/IndexFlat.h>
#include <iostream>
int main() {
    faiss::IndexFlatL2 index(64);
    std::cout << "FAISS OK" << std::endl;
    return 0;
}
EOF

    if g++ -std=c++17 /tmp/test_faiss.cpp -o /tmp/test_faiss \
        -I/usr/local/include -L/usr/local/lib -lfaiss -lblas 2>/dev/null; then
        echo "  ✅ FAISS compilation successful"
        if /tmp/test_faiss 2>/dev/null; then
            echo "  ✅ FAISS execution successful"
        else
            echo "  ⚠️  FAISS compiled but execution failed"
        fi
        rm -f /tmp/test_faiss
    else
        echo "  ❌ FAISS compilation failed"
    fi
    rm -f /tmp/test_faiss.cpp
else
    echo "  ⏭️  FAISS not ready for testing"
fi

# Test ONNX Runtime
if [ "$ONNX_OK" == "true" ]; then
    echo "  Testing ONNX Runtime compilation..."
    cat > /tmp/test_onnx.cpp << 'EOF'
#include <onnxruntime_cxx_api.h>
#include <iostream>
int main() {
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "test");
    std::cout << "ONNX Runtime OK" << std::endl;
    return 0;
}
EOF

    if g++ -std=c++17 /tmp/test_onnx.cpp -o /tmp/test_onnx \
        -I/usr/local/include -L/usr/local/lib -lonnxruntime 2>/dev/null; then
        echo "  ✅ ONNX Runtime compilation successful"
        if LD_LIBRARY_PATH=/usr/local/lib /tmp/test_onnx 2>/dev/null; then
            echo "  ✅ ONNX Runtime execution successful"
        else
            echo "  ⚠️  ONNX Runtime compiled but execution failed"
        fi
        rm -f /tmp/test_onnx
    else
        echo "  ❌ ONNX Runtime compilation failed"
    fi
    rm -f /tmp/test_onnx.cpp
else
    echo "  ⏭️  ONNX Runtime not ready for testing"
fi

echo ""

# ════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════"
echo "📊 SUMMARY"
echo "═══════════════════════════════════════════════════════════"

if [ "$FAISS_OK" == "true" ]; then
    echo "  ✅ FAISS: Ready for use"
else
    echo "  ❌ FAISS: NOT ready - run install_faiss_shared.sh"
fi

if [ "$ONNX_OK" == "true" ]; then
    echo "  ✅ ONNX Runtime: Ready for use"
else
    echo "  ❌ ONNX Runtime: NOT ready - check installation"
fi

echo "═══════════════════════════════════════════════════════════"

if [ "$FAISS_OK" == "true" ] && [ "$ONNX_OK" == "true" ]; then
    echo ""
    echo "✅ All libraries ready for Phase 2A development!"
    echo ""
    echo "Next steps:"
    echo "  1. Update CMakeLists.txt to link FAISS"
    echo "  2. Start implementing ChunkCoordinator"
    exit 0
else
    echo ""
    echo "⚠️  Some libraries need attention"
    echo ""
    echo "To fix:"
    if [ "$FAISS_OK" != "true" ]; then
        echo "  - Run: sudo /vagrant/scripts/install_faiss_shared.sh"
    fi
    if [ "$ONNX_OK" != "true" ]; then
        echo "  - Check ONNX Runtime installation"
    fi
    exit 1
fi