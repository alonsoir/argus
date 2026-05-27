#!/bin/bash
# compile_with_tsan.sh - Compile ml-detector with ThreadSanitizer
# Day 16 - Race Condition Investigation
# Authors: Alonso + Claude

set -e

PROJECT_ROOT="/vagrant"
DETECTOR_DIR="$PROJECT_ROOT/ml-detector"

echo "🔬 Compiling ml-detector with ThreadSanitizer..."
echo ""

cd "$DETECTOR_DIR"

# Clean previous builds
echo "🧹 Cleaning previous build..."
make clean 2>/dev/null || true

# Compile with TSan flags
echo "🔨 Compiling with -fsanitize=thread..."
echo ""

# TSan requires specific flags:
# -fsanitize=thread: Enable ThreadSanitizer
# -O1: Minimal optimization (TSan doesn't work with -O0 or -O2/-O3)
# -g: Debug symbols for readable stack traces
# -fno-omit-frame-pointer: Better stack traces

export CXXFLAGS="-fsanitize=thread -O1 -g -fno-omit-frame-pointer"
export LDFLAGS="-fsanitize=thread"

# Build ml-detector with TSan
make ml-detector

echo ""
echo "✅ Compilation complete!"
echo ""
echo "📊 Binary info:"
file build/ml-detector
ls -lh build/ml-detector
echo ""

# Verify TSan is linked
echo "🔍 Verifying ThreadSanitizer is linked:"
ldd build/ml-detector | grep tsan || echo "⚠️  Warning: libtsan not found in dependencies"
echo ""

echo "✅ Ready to run with ThreadSanitizer!"
echo ""
echo "Next steps:"
echo "  1. Run: ./run_tsan_test.sh"
echo "  2. Wait for crash or 5 minutes"
echo "  3. Check: tsan_report_*.txt for race condition details"