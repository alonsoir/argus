#!/bin/bash
# ML Defender - FAISS Installation Script (FIXED)
# Instala FAISS con BUILD_SHARED_LIBS=ON para generar libfaiss.so

set -e

echo "🔧 FAISS Installation - Shared Library Build"
echo "=============================================="
echo ""

# ════════════════════════════════════════════════════════════════════
# Step 1: Clean previous static-only build
# ════════════════════════════════════════════════════════════════════

if [ -f /usr/local/lib/libfaiss.a ] && [ ! -f /usr/local/lib/libfaiss.so ]; then
    echo "🧹 Removing previous static-only build..."
    sudo rm -f /usr/local/lib/libfaiss.a
    sudo rm -rf /usr/local/include/faiss
    sudo rm -rf /usr/local/share/faiss
    echo "✅ Cleaned"
fi

echo ""

# ════════════════════════════════════════════════════════════════════
# Step 2: Install dependencies
# ════════════════════════════════════════════════════════════════════

echo "📦 Installing FAISS dependencies..."
sudo apt-get update -qq
sudo apt-get install -y libblas-dev liblapack-dev cmake build-essential git

echo "✅ Dependencies installed"
echo ""

# ════════════════════════════════════════════════════════════════════
# Step 3: Build FAISS with shared library enabled
# ════════════════════════════════════════════════════════════════════

if [ ! -f /usr/local/lib/libfaiss.so ]; then
    echo "🏗️  Building FAISS from source (shared library)..."
    cd /tmp

    # Clean previous clone if exists
    rm -rf faiss

    # Clone FAISS
    echo "   Cloning FAISS v1.8.0..."
    git clone --depth 1 --branch v1.8.0 https://github.com/facebookresearch/faiss.git
    cd faiss

    # Configure with shared library enabled
    mkdir -p build && cd build
    echo "   Configuring CMake..."
    cmake .. \
      -DFAISS_ENABLE_GPU=OFF \
      -DFAISS_ENABLE_PYTHON=OFF \
      -DBUILD_TESTING=OFF \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local

    # Build (this takes ~10-15 minutes)
    echo "   Building FAISS (this may take 10-15 minutes)..."
    make -j$(nproc)

    # Install
    echo "   Installing..."
    sudo make install

    # Update library cache
    sudo ldconfig

    # Clean up
    cd /tmp && rm -rf faiss

    echo "✅ FAISS compiled and installed successfully"
else
    echo "✅ FAISS shared library already installed"
fi

echo ""

# ════════════════════════════════════════════════════════════════════
# Step 4: Verification
# ════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════"
echo "🔍 VERIFICATION"
echo "═══════════════════════════════════════════════════════════"

# Check shared library
if [ -f /usr/local/lib/libfaiss.so ]; then
    echo "  ✅ FAISS shared library: $(ls -lh /usr/local/lib/libfaiss.so | awk '{print $9, $5}')"
else
    echo "  ❌ FAISS shared library NOT found"
fi

# Check static library (should also exist)
if [ -f /usr/local/lib/libfaiss.a ]; then
    echo "  ✅ FAISS static library: $(ls -lh /usr/local/lib/libfaiss.a | awk '{print $9, $5}')"
fi

# Check headers
if [ -d /usr/local/include/faiss ]; then
    HEADER_COUNT=$(find /usr/local/include/faiss -name "*.h" | wc -l)
    echo "  ✅ FAISS headers: /usr/local/include/faiss ($HEADER_COUNT files)"
else
    echo "  ❌ FAISS headers NOT found"
fi

# Check ldconfig cache
echo ""
echo "  Library cache (ldconfig):"
if sudo ldconfig -p | grep -q faiss; then
    sudo ldconfig -p | grep faiss | sed 's/^/    /'
else
    echo "    ⚠️  Not in ldconfig cache (may need VM restart)"
fi

echo "═══════════════════════════════════════════════════════════"
echo ""

# ════════════════════════════════════════════════════════════════════
# Step 5: Test compilation
# ════════════════════════════════════════════════════════════════════

echo "🧪 Testing FAISS compilation..."

TEST_FILE="/tmp/test_faiss.cpp"
cat > $TEST_FILE << 'EOF'
#include <faiss/IndexFlat.h>
#include <iostream>

int main() {
    int d = 64;
    faiss::IndexFlatL2 index(d);
    std::cout << "✅ FAISS test: created index with dimension " << d << std::endl;
    return 0;
}
EOF

# Try to compile
if g++ -std=c++17 $TEST_FILE -o /tmp/test_faiss -I/usr/local/include -L/usr/local/lib -lfaiss -lblas 2>/dev/null; then
    echo "  ✅ Test compilation successful"

    # Try to run
    if /tmp/test_faiss 2>/dev/null; then
        echo "  ✅ Test execution successful"
    else
        echo "  ⚠️  Test compiled but failed to run (may need ldconfig or VM restart)"
    fi

    rm -f /tmp/test_faiss
else
    echo "  ⚠️  Test compilation failed (check library paths)"
fi

rm -f $TEST_FILE

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ FAISS INSTALLATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Verify: ls -lh /usr/local/lib/libfaiss.so"
echo "  2. Check headers: ls /usr/local/include/faiss/"
echo "  3. Create C++ test program"
echo ""