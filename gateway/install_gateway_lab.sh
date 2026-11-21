#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# ML Defender - Install Gateway Laboratory Files
# ══════════════════════════════════════════════════════════════════════════════
# Purpose: Copy all gateway testing files to correct locations
# Usage: ./install_gateway_lab.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ML Defender - Gateway Laboratory Installation            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Source directory (where files were downloaded/created)
SRC_DIR="/mnt/user-data/outputs"
DEST_DIR="/vagrant"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$DEST_DIR/scripts/gateway/defender"
mkdir -p "$DEST_DIR/scripts/gateway/client"
mkdir -p "$DEST_DIR/scripts/gateway/shared"

# Backup existing Vagrantfile
if [ -f "$DEST_DIR/Vagrantfile" ]; then
    echo "💾 Backing up existing Vagrantfile..."
    cp "$DEST_DIR/Vagrantfile" "$DEST_DIR/Vagrantfile.backup.$(date +%Y%m%d-%H%M%S)"
fi

# Copy Vagrantfile
echo "📄 Installing Vagrantfile.multi-vm..."
if [ -f "$SRC_DIR/Vagrantfile.multi-vm" ]; then
    cp "$SRC_DIR/Vagrantfile.multi-vm" "$DEST_DIR/Vagrantfile.multi-vm"
    echo "   ✅ Vagrantfile.multi-vm installed"
else
    echo "   ❌ Vagrantfile.multi-vm not found in $SRC_DIR"
fi

# Copy defender scripts
echo "📄 Installing defender scripts..."
for script in start_gateway_test.sh validate_gateway.sh gateway_dashboard.sh; do
    if [ -f "$SRC_DIR/$script" ]; then
        cp "$SRC_DIR/$script" "$DEST_DIR/scripts/gateway/defender/"
        chmod +x "$DEST_DIR/scripts/gateway/defender/$script"
        echo "   ✅ $script installed"
    else
        echo "   ❌ $script not found"
    fi
done

# Copy client scripts
echo "📄 Installing client scripts..."
for script in generate_traffic.sh chaos_monkey.sh auto_validate.sh; do
    if [ -f "$SRC_DIR/$script" ]; then
        cp "$SRC_DIR/$script" "$DEST_DIR/scripts/gateway/client/"
        chmod +x "$DEST_DIR/scripts/gateway/client/$script"
        echo "   ✅ $script installed"
    else
        echo "   ❌ $script not found"
    fi
done

# Copy shared config
echo "📄 Installing shared configuration..."
if [ -f "$SRC_DIR/config_gateway.json" ]; then
    cp "$SRC_DIR/config_gateway.json" "$DEST_DIR/scripts/gateway/shared/"
    echo "   ✅ config_gateway.json installed"
else
    echo "   ❌ config_gateway.json not found"
fi

# Copy documentation
echo "📄 Installing documentation..."
if [ -f "$SRC_DIR/README_GATEWAY.md" ]; then
    cp "$SRC_DIR/README_GATEWAY.md" "$DEST_DIR/"
    echo "   ✅ README_GATEWAY.md installed"
else
    echo "   ❌ README_GATEWAY.md not found"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Installation Complete                                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 Files installed:"
echo "   /vagrant/Vagrantfile.multi-vm"
echo "   /vagrant/scripts/gateway/defender/*.sh (3 files)"
echo "   /vagrant/scripts/gateway/client/*.sh (3 files)"
echo "   /vagrant/scripts/gateway/shared/config_gateway.json"
echo "   /vagrant/README_GATEWAY.md"
echo ""
echo "🚀 Next steps:"
echo ""
echo "   1. Review README:"
echo "      cat /vagrant/README_GATEWAY.md"
echo ""
echo "   2. Use multi-VM Vagrantfile:"
echo "      cd /vagrant"
echo "      mv Vagrantfile Vagrantfile.backup.single-vm"
echo "      mv Vagrantfile.multi-vm Vagrantfile"
echo ""
echo "   3. Start gateway testing:"
echo "      vagrant up defender client"
echo ""
echo "   4. Follow validation workflow in README_GATEWAY.md"
echo ""
echo "════════════════════════════════════════════════════════════"