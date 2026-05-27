.PHONY: all clean build configure proto help

PROTO_DIR := $(shell pwd)/../protobuf
BUILD_DIR := build
PROTO_BUILD_DIR := $(BUILD_DIR)/proto

all: build

# Generate protobuf files if needed
proto:
	@echo "📦 Checking protobuf files..."
	@if [ ! -f "$(PROTO_DIR)/network_security.pb.cc" ] || \
	    [ "$(PROTO_DIR)/network_security.proto" -nt "$(PROTO_DIR)/network_security.pb.cc" ]; then \
		echo "🔨 Regenerating protobuf files..."; \
		cd $(PROTO_DIR) && ./generate.sh; \
	else \
		echo "✅ Protobuf files up to date"; \
	fi

configure: proto
	@echo "⚙️  Configuring sniffer..."
	@mkdir -p $(PROTO_BUILD_DIR)
	@echo "📋 Copying protobuf files to build..."
	@cp $(PROTO_DIR)/network_security.pb.cc $(PROTO_BUILD_DIR)/
	@cp $(PROTO_DIR)/network_security.pb.h $(PROTO_BUILD_DIR)/
	@cd $(BUILD_DIR) && cmake ..

build: configure
	@echo "🔨 Building sniffer..."
	@cd $(BUILD_DIR) && $(MAKE) -j$$(nproc)
	@echo ""
	@echo "✅ Sniffer compiled successfully!"
	@ls -lh $(BUILD_DIR)/sniffer $(BUILD_DIR)/sniffer.bpf.o

clean:
	@echo "🧹 Cleaning build directory..."
	@rm -rf $(BUILD_DIR)/*

distclean: clean
	@echo "🧹 Cleaning protobuf generated files..."
	@rm -f $(PROTO_DIR)/network_security.pb.cc
	@rm -f $(PROTO_DIR)/network_security.pb.h
	@rm -f $(PROTO_DIR)/network_security_pb2.py

help:
	@echo "Sniffer Build System"
	@echo ""
	@echo "Targets:"
	@echo "  make           - Build sniffer (regenerates proto if needed)"
	@echo "  make proto     - Regenerate protobuf files from .proto"
	@echo "  make clean     - Clean build directory"
	@echo "  make distclean - Clean build + generated protobuf files"
	@echo "  make help      - Show this help"
	@echo ""
	@echo "Protobuf schema: $(PROTO_DIR)/network_security.proto"
	@echo "Generated files: $(PROTO_DIR)/network_security.pb.{cc,h}"

.PHONY: proto
