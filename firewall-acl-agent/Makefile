.PHONY: all clean build test install run

BUILD_DIR := build

all: build

$(BUILD_DIR):
	@echo "📦 Creating build directory..."
	@mkdir -p $(BUILD_DIR)

build: $(BUILD_DIR)
	@echo "🔨 Building Firewall ACL Agent..."
	@cd $(BUILD_DIR) && cmake .. && $(MAKE) -j$(shell nproc)
	@echo "✅ Build complete: $(BUILD_DIR)/firewall-agent"

clean:
	@echo "🧹 Cleaning build directory..."
	@rm -rf $(BUILD_DIR)
	@echo "✅ Clean complete"

test: build
	@echo "🧪 Running tests..."
	@cd $(BUILD_DIR) && ctest --output-on-failure

install: build
	@echo "📦 Installing firewall-agent..."
	@cd $(BUILD_DIR) && sudo $(MAKE) install

run: build
	@echo "🚀 Running firewall-agent..."
	@cd $(BUILD_DIR) && sudo ./firewall-agent -c config/firewall.json

help:
	@echo "ML Defender - Firewall ACL Agent"
	@echo ""
	@echo "Available targets:"
	@echo "  make all      - Build firewall-agent (default)"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make test     - Run unit tests"
	@echo "  make install  - Install to system"
	@echo "  make run      - Build and run"
