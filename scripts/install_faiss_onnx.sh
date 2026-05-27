#!/bin/bash
# ML Defender - FAISS and ONNX Runtime Installation Script
# Via Appia Quality: Foundation first 🏛️

set -e

echo "🔍 Installing FAISS and ONNX Runtime dependencies..."

# Update package list
apt-get update

# Install BLAS/LAPACK for FAISS
echo "📦 Installing BLAS/LAPACK..."
apt-get install -y libblas-dev liblapack-dev

# Install ONNX Runtime dependencies
echo "📦 Installing ONNX Runtime dependencies..."
apt-get install -y libgomp1

# Build FAISS from source (CPU version only)
if [ ! -d "/usr/local/include/faiss" ]; then
    echo "🏗️  Building FAISS from source..."
    cd /tmp

    # Clone FAISS repository
    if [ ! -d "faiss" ]; then
        git clone https://github.com/facebookresearch/faiss.git
    fi

    cd faiss

    # Create build directory
    mkdir -p build && cd build

    # Configure CMake
    cmake .. \
        -DFAISS_ENABLE_GPU=OFF \
        -DFAISS_ENABLE_PYTHON=OFF \
        -DBUILD_TESTING=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local

    # Build with all available cores
    make -j$(nproc)

    # Install
    make install

    # Update library cache
    ldconfig

    echo "✅ FAISS installed successfully"
else
    echo "✅ FAISS already installed"
fi

# Install ONNX Runtime (CPU version)
if [ ! -f "/usr/local/lib/libonnxruntime.so" ]; then
    echo "🧠 Installing ONNX Runtime..."
    cd /tmp

    # Download ONNX Runtime
    ONNX_VERSION="1.16.3"
    ONNX_FILE="onnxruntime-linux-x64-${ONNX_VERSION}.tgz"

    if [ ! -f "${ONNX_FILE}" ]; then
        wget "https://github.com/microsoft/onnxruntime/releases/download/v${ONNX_VERSION}/${ONNX_FILE}"
    fi

    # Extract
    tar -xzf "${ONNX_FILE}"

    # Install headers and libraries
    cd "onnxruntime-linux-x64-${ONNX_VERSION}"
    cp -r include/* /usr/local/include/
    cp -r lib/* /usr/local/lib/

    # Update library cache
    ldconfig

    echo "✅ ONNX Runtime installed successfully"
else
    echo "✅ ONNX Runtime already installed"
fi

# Verify installations
echo ""
echo "🔍 Verifying installations..."
echo "================================"

if [ -d "/usr/local/include/faiss" ]; then
    echo "  ✅ FAISS headers: /usr/local/include/faiss"
else
    echo "  ❌ FAISS headers not found"
fi

if [ -f "/usr/local/lib/libfaiss.so" ]; then
    echo "  ✅ FAISS library: /usr/local/lib/libfaiss.so"
else
    echo "  ❌ FAISS library not found"
fi

if [ -f "/usr/local/include/onnxruntime/core/session/onnxruntime_cxx_api.h" ]; then
    echo "  ✅ ONNX Runtime headers: /usr/local/include/onnxruntime"
else
    echo "  ❌ ONNX Runtime headers not found"
fi

if [ -f "/usr/local/lib/libonnxruntime.so" ]; then
    echo "  ✅ ONNX Runtime library: /usr/local/lib/libonnxruntime.so"
else
    echo "  ❌ ONNX Runtime library not found"
fi

echo "================================"
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Create test programs to verify FAISS integration"
echo "  2. Create test programs to verify ONNX Runtime integration"
echo "  3. Start implementing ChunkCoordinator"