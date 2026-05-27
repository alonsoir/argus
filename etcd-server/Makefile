.PHONY: all clean build configure test help

BUILD_DIR := build

all: build

configure:
	@echo "⚙️  Configuring etcd-server..."
	@mkdir -p $(BUILD_DIR)
	@cd $(BUILD_DIR) && cmake .. -DCMAKE_BUILD_TYPE=Release

build: configure
	@echo "🔨 Building etcd-server..."
	@cd $(BUILD_DIR) && $(MAKE) -j$$(nproc)
	@echo "✅ etcd-server compiled successfully!"
	@ls -lh $(BUILD_DIR)/etcd-server

clean:
	@echo "🧹 Cleaning etcd-server build..."
	@rm -rf $(BUILD_DIR)/*

test:
	@echo "🧪 Testing etcd-server..."
	@cd $(BUILD_DIR) && timeout 2s ./etcd-server 2>&1 | head -5 || true

run:
	@echo "🚀 Running etcd-server..."
	@cd $(BUILD_DIR) && ./etcd-server

help:
	@echo "etcd-server Build"
	@echo "Targets:"
	@echo "  make       - Build etcd-server"
	@echo "  make clean - Clean build directory"
	@echo "  make test  - Quick test"
	@echo "  make run   - Run etcd-server"
