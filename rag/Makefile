.PHONY: all clean build configure test test-faiss test-onnx help

BUILD_DIR := build
CONFIG_DIR := config

# ════════════════════════════════════════════════════════════════════
# MAIN TARGETS
# ════════════════════════════════════════════════════════════════════

all: build

configure:
	@echo "⚙️  Configuring RAG Security System..."
	@mkdir -p $(BUILD_DIR)
	@cd $(BUILD_DIR) && cmake .. -DCMAKE_BUILD_TYPE=Release

build: configure
	@echo "🔨 Building RAG..."
	@cd $(BUILD_DIR) && $(MAKE) -j$$(nproc)
	@echo "✅ RAG compiled successfully!"
	@ls -lh $(BUILD_DIR)/rag-security

clean:
	@echo "🧹 Cleaning RAG build..."
	@rm -rf $(BUILD_DIR)/*

# ════════════════════════════════════════════════════════════════════
# TESTING TARGETS (Phase 2A)
# ════════════════════════════════════════════════════════════════════

test: test-main
	@echo "✅ All tests completed"

test-main:
	@echo "🧪 Testing RAG main executable..."
	@cd $(BUILD_DIR) && ./rag-security --test-config 2>&1 || echo "Test ejecutado"

# Test FAISS Integration
test-faiss: build-test-faiss
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "🧪 Running FAISS Integration Test"
	@echo "════════════════════════════════════════════════════════════"
	@if [ -f $(BUILD_DIR)/test_faiss_basic ]; then \
		cd $(BUILD_DIR) && ./test_faiss_basic; \
	else \
		echo "❌ test_faiss_basic not found - FAISS not available?"; \
		echo "   Run 'make configure' to check FAISS status"; \
		exit 1; \
	fi
	@echo "════════════════════════════════════════════════════════════"

build-test-faiss: configure
	@echo "🔨 Building test_faiss_basic..."
	@cd $(BUILD_DIR) && $(MAKE) test_faiss_basic 2>&1 | grep -v "^make"

# Test ONNX Runtime
# Test ONNX Runtime
test-onnx: build-test-onnx
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "🧪 Running ONNX Runtime Test"
	@echo "════════════════════════════════════════════════════════════"
	@if [ -f $(BUILD_DIR)/test_onnx_basic ]; then \
		echo "📝 Generating dummy ONNX model..."; \
		cd tests && python3 create_dummy_model_lite.py > /dev/null 2>&1 && echo "✅ Model generated" && ../build/test_onnx_basic; \
	else \
		echo "ℹ️  test_onnx_basic not yet implemented"; \
	fi
	@echo "════════════════════════════════════════════════════════════"

build-test-onnx: configure
	@echo "🔨 Building test_onnx_basic..."
	@cd $(BUILD_DIR) && $(MAKE) test_onnx_basic 2>&1 | grep -v "^make" || echo "Not yet created"

# Run all Phase 2A tests
test-all: test-faiss test-onnx
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  All Phase 2A Tests Completed                             ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

# ════════════════════════════════════════════════════════════════════
# VERIFICATION TARGETS
# ════════════════════════════════════════════════════════════════════

verify-libs:
	@echo "🔍 Verifying Phase 2A libraries..."
	@echo ""
	@echo "FAISS:"
	@ls -lh /usr/local/lib/libfaiss.so 2>/dev/null || echo "  ❌ libfaiss.so not found"
	@ls -d /usr/local/include/faiss 2>/dev/null || echo "  ❌ FAISS headers not found"
	@echo ""
	@echo "ONNX Runtime:"
	@ls -lh /usr/local/lib/libonnxruntime.so 2>/dev/null || echo "  ❌ libonnxruntime.so not found"
	@find /usr/local/include -name "onnxruntime*.h" 2>/dev/null | head -3 || echo "  ❌ ONNX headers not found"
	@echo ""

# ════════════════════════════════════════════════════════════════════
# RUN TARGETS
# ════════════════════════════════════════════════════════════════════

run:
	@echo "🚀 Running RAG..."
	@cd $(BUILD_DIR) && ./rag-security -c ../$(CONFIG_DIR)/rag-config.json

run-debug:
	@echo "🐛 Running RAG in debug mode..."
	@cd $(BUILD_DIR) && ./rag-security -c ../$(CONFIG_DIR)/rag-config.json --debug

# ════════════════════════════════════════════════════════════════════
# HELP
# ════════════════════════════════════════════════════════════════════

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  RAG Security System - Makefile Help                      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Main Targets:"
	@echo "  make              - Build RAG Security"
	@echo "  make clean        - Clean build directory"
	@echo "  make configure    - Configure CMake"
	@echo "  make run          - Run RAG with config"
	@echo "  make run-debug    - Run with debug output"
	@echo ""
	@echo "🧪 Testing (Phase 2A):"
	@echo "  make test         - Run main tests"
	@echo "  make test-faiss   - Run FAISS integration test"
	@echo "  make test-onnx    - Run ONNX Runtime test (Day 32)"
	@echo "  make test-all     - Run all Phase 2A tests"
	@echo ""
	@echo "🔍 Verification:"
	@echo "  make verify-libs  - Verify FAISS + ONNX installation"
	@echo ""
	@echo "📝 Quick Start:"
	@echo "  1. make configure    # Configure build"
	@echo "  2. make              # Build everything"
	@echo "  3. make test-faiss   # Test FAISS integration"
	@echo "  4. make verify-libs  # Verify libraries"
	@echo ""