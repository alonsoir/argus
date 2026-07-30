# -*- mode: ruby -*-
# vi: set ft=ruby :

# ══════════════════════════════════════════════════════════════════════════════
# ML DEFENDER LABORATORY - MULTI-VM CONFIGURATION (Vagrantfile)
# ══════════════════════════════════════════════════════════════════════════════
#
# ARCHITECTURE:
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  ML Defender Complete Pipeline Laboratory                               │
# │                                                                          │
# │  ┌─────────────────────────┐         ┌──────────────────────────────┐   │
# │  │  DEFENDER VM            │         │  CLIENT VM                   │   │
# │  │  (Full ML Pipeline)     │         │  (Traffic Generator)         │   │
# │  │                         │         │                              │   │
# │  │  • eBPF/XDP Sniffer     │◄────────│  • Attack simulation         │   │
# │  │  • ML Detector          │   LAN   │  • Gateway testing           │   │
# │  │  • Firewall ACL Agent   │  eth2   │  • PCAP dataset replay       │   │
# │  │  • RAG Security System  │         │  • Performance benchmarks    │   │
# │  │  • FAISS Ingestion      │         │                              │   │
# │  │                         │         │                              │   │
# │  │  eth1: 192.168.56.20    │         │  eth1: 192.168.100.50        │   │
# │  │  eth2: 192.168.100.1    │         │  Gateway: 192.168.100.1      │   │
# │  └─────────────────────────┘         └──────────────────────────────┘   │
# └──────────────────────────────────────────────────────────────────────────┘
#
# PHASE 2A: FAISS Ingestion Support
#   • FAISS v1.8.0 (CPU-only, shared library)
#   • ONNX Runtime v1.17.1
#   • Cron restart every 72h (memory leak mitigation)
#
# DAY 95: Cryptographic Provisioning
#   • tools/provision.sh genera keypairs Ed25519 + seeds ChaCha20
#   • /etc/ml-defender/{component}/ — AppArmor-compatible (ADR-019)
#   • run: "once" — las claves persisten entre reinicios de VM
#   • Re-provisionar manualmente: make provision
#
# USAGE:
#   Development (defender only):   vagrant up defender
#   Gateway testing (both VMs):    vagrant up defender client
#   Full demo:                     vagrant up
#
# CONTROL:
#   autostart: false → Client VM disabled by default
#   autostart: true  → Client VM starts automatically
#
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# ADAPTER_TOOLCHAIN — toolchain C++ para compilar los <sensor>-adapter DENTRO
# de cada VM de sensor. DEBT-VM-SENSOR-NO-TOOLCHAIN-001.
# Paquetes = los instalados a mano en `suricata` DAY 226 (make suricata-adapter-test 2/2).
# Verifica POR INVOCACIÓN, no por `test -f` (lección DAY 224/225: comprobar el
# resultado, no la presencia del fichero). set -e → un fallo tumba el vagrant up.
# ══════════════════════════════════════════════════════════════════════════════
ADAPTER_TOOLCHAIN = <<-'ADAPTER_TOOLCHAIN_SHELL'
  set -e
  export DEBIAN_FRONTEND=noninteractive
  echo "🔧 ADAPTER_TOOLCHAIN — instalando toolchain C++ de adapters..."

  apt-get update -qq
  apt-get install -y build-essential cmake pkg-config \
    libsodium-dev nlohmann-json3-dev libssl-dev

  echo "── verificando toolchain (por invocación, no test -f) ──"
  cmake --version | head -1
  g++ --version   | head -1
  pkg-config --modversion libsodium
  echo '#include <nlohmann/json.hpp>' | g++ -x c++ -std=c++20 -fsyntax-only - \
    && echo "✅ nlohmann/json.hpp compila"
  echo '#include <openssl/hmac.h>'    | g++ -x c++ -fsyntax-only - \
    && echo "✅ openssl/hmac.h compila"
  echo "✅ ADAPTER_TOOLCHAIN verificado"
ADAPTER_TOOLCHAIN_SHELL

# WAZUH_AGENT_INSTALL — instala el agente Wazuh por dpkg del .deb cacheado en /vagrant.
# dpkg NO necesita repo/apt/DNS/gnupg (a diferencia de la via apt). El nombre del agente
# llega por env AGENT_NAME (fijado en cada provision). Version clavada = la del manager.
WAZUH_AGENT_INSTALL = <<-'WAZUH_AGENT_INSTALL_SHELL'
  set -e
  MANAGER_IP="192.168.100.12"
  DEB="/vagrant/provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb"
  echo "🛡️  WAZUH_AGENT_INSTALL — agente '${AGENT_NAME}' -> manager ${MANAGER_IP}"
  if /var/ossec/bin/wazuh-control info >/dev/null 2>&1; then
    echo "✅ agente ya instalado, nada que hacer"; exit 0
  fi
  if [ ! -f "$DEB" ]; then
    echo "❌ no encuentro el .deb en $DEB"
    echo "   cachealo antes del up:  mkdir -p provisioning/wazuh && cp logs/wazuh-agent_4.14.7-1_amd64.deb provisioning/wazuh/"
    exit 1
  fi
  WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" dpkg -i "$DEB"
  systemctl daemon-reload
  systemctl enable --now wazuh-agent
  echo "✅ WAZUH_AGENT_INSTALL — '${AGENT_NAME}' instalado y arrancado"
WAZUH_AGENT_INSTALL_SHELL

Vagrant.configure("2") do |config|

  # ════════════════════════════════════════════════════════════════════════════
  # DEFENDER VM - Full ML Pipeline (Primary)
  # ════════════════════════════════════════════════════════════════════════════
  config.vm.define "defender", primary: true do |defender|
    defender.vm.provision "shell", name: "wazuh-agent", env: {"AGENT_NAME" => "defender"}, inline: WAZUH_AGENT_INSTALL
    defender.vm.box = "debian/bookworm64"
    defender.vm.box_version = "12.20240905.1"

    defender.vm.provider "virtualbox" do |vb|
      vb.name = "ml-defender-gateway-lab"
      vb.memory = "8192"
      vb.cpus = 6

      # Network optimizations - Simple virtio (stable, proven)
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]  # NAT
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]  # WAN (eth1)
      vb.customize ["modifyvm", :id, "--nictype3", "virtio"]  # Gateway (eth2)

      # Promiscuous mode para captura de paquetes
      vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]  # eth1 (WAN)
      vb.customize ["modifyvm", :id, "--nicpromisc3", "allow-all"]  # eth2 (Gateway)

      # General optimizations
      vb.customize ["modifyvm", :id, "--ioapic", "on"]
      vb.customize ["modifyvm", :id, "--audio", "none"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
      vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    end

    # ════════════════════════════════════════════════════════════════════════
    # RED - Configuración Dual-NIC para Testing (STABLE)
    # ════════════════════════════════════════════════════════════════════════
    # eth0: NAT (Vagrant management)
    # eth1: 192.168.56.20 (WAN-facing, host-only) - Host-based IDS
    # eth2: 192.168.100.1 (LAN-facing, internal) - Gateway mode

    defender.vm.network "private_network", ip: "192.168.56.20"  # eth1: WAN-facing
    defender.vm.network "private_network", ip: "192.168.100.1",
      virtualbox__intnet: "ml_defender_gateway_lan"  # eth2: Gateway LAN

    defender.vm.network "forwarded_port", guest: 5571, host: 5571
    defender.vm.network "forwarded_port", guest: 5572, host: 5572
    defender.vm.network "forwarded_port", guest: 2379, host: 2379
    defender.vm.network "forwarded_port", guest: 8080, host: 8080  # Jenkins
    defender.vm.network "forwarded_port", guest: 8200, host: 8200  # Vault

    defender.vm.synced_folder ".", "/vagrant", type: "virtualbox",
        mount_options: ["dmode=775,fmode=775,exec"]

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: Configuración de Red DUAL-NIC + Modo Promiscuo
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", run: "always", inline: <<-SHELL
      echo "🔧 Configurando interfaces de red para Dual-NIC testing..."

      # 1. Instalar herramientas de red
      apt-get update -qq
      apt-get install -y ethtool tcpdump iptables nftables iproute2

      # 2. Configurar IP forwarding para gateway mode
      echo "🌐 Activando IP forwarding para gateway mode..."
      sysctl -w net.ipv4.ip_forward=1
      sysctl -w net.ipv6.conf.all.forwarding=1
      if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
        echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
      fi

      # 3. CRITICAL: Disable rp_filter (prevents routing issues)
      echo "🔧 Disabling rp_filter..."
      sysctl -w net.ipv4.conf.all.rp_filter=0
      sysctl -w net.ipv4.conf.eth1.rp_filter=0
      sysctl -w net.ipv4.conf.eth2.rp_filter=0
      if ! grep -q "net.ipv4.conf.all.rp_filter" /etc/sysctl.conf; then
        echo "net.ipv4.conf.all.rp_filter=0" >> /etc/sysctl.conf
        echo "net.ipv4.conf.eth1.rp_filter=0" >> /etc/sysctl.conf
        echo "net.ipv4.conf.eth2.rp_filter=0" >> /etc/sysctl.conf
      fi

      # 4. Configure NAT for gateway mode
      echo "🔥 Configuring NAT/MASQUERADE..."
      iptables -t nat -F POSTROUTING
      iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
      iptables -A FORWARD -i eth2 -o eth1 -j ACCEPT
      iptables -A FORWARD -i eth1 -o eth2 -m state --state RELATED,ESTABLISHED -j ACCEPT

      # 5. Detectar interfaz gateway automáticamente
      GATEWAY_IFACE=$(ip -o addr show | grep "192.168.100.1" | awk '{print $2}')
      if [ -z "$GATEWAY_IFACE" ]; then
        echo "⚠️  Gateway interface not found, defaulting to eth2"
        GATEWAY_IFACE="eth2"
      fi

      echo "═══════════════════════════════════════════════════════════"
      echo "🎯 CONFIGURACIÓN DUAL-NIC ML DEFENDER"
      echo "═══════════════════════════════════════════════════════════"
      echo "eth0: NAT (Vagrant management)"
      echo "eth1: 192.168.56.20 (WAN-facing, host-only) - Host-Based IDS"
      echo "eth2: 192.168.100.1 (LAN-facing, internal) - Gateway Mode"
      echo "IP Forwarding: $(sysctl net.ipv4.ip_forward | cut -d= -f2)"
      echo "rp_filter: $(sysctl net.ipv4.conf.all.rp_filter | cut -d= -f2)"
      echo "Gateway Interface: $GATEWAY_IFACE"
      echo "═══════════════════════════════════════════════════════════"

      # 6. Configurar modo promiscuo en interfaces de captura
      echo "🔍 Configurando eth1 (WAN-facing, host-based)..."
      if ip link show eth1 >/dev/null 2>&1; then
        ip link set eth1 up
        ip link set eth1 promisc on
        ethtool -K eth1 gro off tso off gso off 2>/dev/null || true

        if ip link show eth1 | grep -q PROMISC; then
          echo "✅ eth1: Modo promiscuo ACTIVO (Host-Based IDS)"
        else
          echo "❌ eth1: Modo promiscuo INACTIVO"
        fi
      fi

      echo "🔍 Configurando $GATEWAY_IFACE (LAN-facing, gateway mode)..."
      if ip link show $GATEWAY_IFACE >/dev/null 2>&1; then
        ip link set $GATEWAY_IFACE up
        ip link set $GATEWAY_IFACE promisc on
        ethtool -K $GATEWAY_IFACE gro off tso off gso off 2>/dev/null || true

        if ip link show $GATEWAY_IFACE | grep -q PROMISC; then
          echo "✅ $GATEWAY_IFACE: Modo promiscuo ACTIVO (Gateway Mode)"
        else
          echo "❌ $GATEWAY_IFACE: Modo promiscuo INACTIVO"
        fi
      else
        echo "⚠️  $GATEWAY_IFACE no encontrada"
      fi

      # 7. Verificación final
      echo ""
      echo "═══════════════════════════════════════════════════════════"
      echo "✅ CONFIGURACIÓN DE RED COMPLETADA"
      echo "═══════════════════════════════════════════════════════════"
      echo "Interfaces disponibles:"
      ip addr show | grep -E '^[0-9]+:|inet ' | grep -v '127.0.0.1'
      echo ""
      echo "═══════════════════════════════════════════════════════════"
      echo ""
    SHELL

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: ALL Dependencies
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "all-dependencies", inline: <<-DEPENDENCIES_EOF
      export DEBIAN_FRONTEND=noninteractive
      set -x

      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║  Installing ALL dependencies - Phase 2A (FAISS)           ║"
      echo "╚════════════════════════════════════════════════════════════╝"

      # Core system packages
      apt-get update
      apt-get install -y build-essential git wget curl vim jq make rsync locales libc-bin file tmux xxd

      apt-get install -y chrony
      systemctl enable chrony

      # eBPF toolchain
      apt-get install -y clang llvm bpftool linux-headers-amd64 libpcap-dev

      # CRITICAL: libbpf 1.4.6 (FIX PERMANENTE)
      CURRENT_LIBBPF_VERSION=$(PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}" pkg-config --modversion libbpf 2>/dev/null || echo "0.0.0")
      if [ "$(printf '%s\n' "1.2.0" "$CURRENT_LIBBPF_VERSION" | sort -V | head -n1)" != "1.2.0" ]; then
        echo "🔧 Upgrading libbpf to 1.4.6..."
        apt-get install -y libelf-dev zlib1g-dev pkg-config
        cd /tmp && rm -rf libbpf
        git clone --depth 1 --branch v1.4.6 https://github.com/libbpf/libbpf.git
        cd libbpf/src
        make -j$(nproc) BUILD_STATIC_ONLY=y
        make install install_headers
        ldconfig

        if ! grep -q "PKG_CONFIG_PATH.*usr/lib64/pkgconfig" /etc/environment 2>/dev/null; then
          echo 'PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"' >> /etc/environment
        fi

        cat > /etc/profile.d/libbpf.sh << 'LIBBPF_PROFILE'
export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"
LIBBPF_PROFILE
        chmod +x /etc/profile.d/libbpf.sh
        export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"
        export LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"
        echo "/usr/lib64" > /etc/ld.so.conf.d/libbpf.conf
        ldconfig
        cd /tmp && rm -rf libbpf
      fi

      # Networking libraries
      apt-get install -y libjsoncpp-dev libcurl4-openssl-dev libzmq3-dev

      # Protobuf
      apt-get install -y protobuf-compiler libprotobuf-dev libprotobuf32

      # Compression
      apt-get install -y liblz4-dev libzstd-dev

      # ML Detector
      apt-get install -y pkg-config libspdlog-dev nlohmann-json3-dev

      # Firewall
      apt-get install -y iptables ipset libxtables-dev
      # AppArmor
      apt-get install -y apparmor-utils apparmor-profiles

      # RAG dependencies
      apt-get install -y libboost-all-dev libtool autoconf automake libgrpc-dev libgrpc++-dev \
        protobuf-compiler-grpc libc-ares-dev libre2-dev libabsl-dev libbenchmark-dev \
        libgtest-dev libssl-dev libcpprest-dev cmake

      # Python
      apt-get install -y python3 python3-pip python3-venv python3-dev

      # Testing tools (para gateway testing)
      apt-get install -y hping3 nmap tcpreplay netcat-openbsd iperf3 net-tools dnsutils

      # CMake 3.25+
      CMAKE_VERSION=$(cmake --version 2>/dev/null | head -1 | awk '{print $3}')
      if [ -z "$CMAKE_VERSION" ] || [ "$(printf '%s\n' "3.20" "$CMAKE_VERSION" | sort -V | head -n1)" != "3.20" ]; then
        cd /tmp
        wget -q https://github.com/Kitware/CMake/releases/download/v3.25.0/cmake-3.25.0-linux-x86_64.sh
        sh cmake-3.25.0-linux-x86_64.sh --prefix=/usr/local --skip-license
        rm cmake-3.25.0-linux-x86_64.sh
      fi

      # libsodium 1.0.19 (requerido por crypto-transport HKDF-SHA256 — ADR-013)
      # Debian bookworm provee 1.0.18 — crypto_kdf_hkdf_sha256_* requiere 1.0.19+
      if [ "$(pkg-config --modversion libsodium 2>/dev/null)" != "1.0.19" ]; then
        echo "🔐 Installing libsodium 1.0.19 from source..."
        cd /tmp && rm -rf libsodium-stable libsodium-1.0.19.tar.gz
        curl -fsSL https://github.com/jedisct1/libsodium/releases/download/1.0.19-RELEASE/libsodium-1.0.19.tar.gz \
          -o libsodium-1.0.19.tar.gz
        tar xzf libsodium-1.0.19.tar.gz
        cd libsodium-stable
        ./configure --prefix=/usr/local
        make -j4
        make install
        ldconfig
        echo "✅ libsodium $(pkg-config --modversion libsodium) installed"
      else
        echo "✅ libsodium 1.0.19 already installed"
      fi
      # ONNX Runtime v1.17.1
      if [ ! -f /usr/local/lib/libonnxruntime.so ]; then
        echo "🧠 Installing ONNX Runtime v1.17.1..."
        cd /tmp
        wget -q https://github.com/microsoft/onnxruntime/releases/download/v1.17.1/onnxruntime-linux-x64-1.17.1.tgz
        tar -xzf onnxruntime-linux-x64-1.17.1.tgz
        cp -r onnxruntime-linux-x64-1.17.1/include/* /usr/local/include/
        cp -r onnxruntime-linux-x64-1.17.1/lib/* /usr/local/lib/
        ldconfig

        echo "🔗 Creating /usr/local/lib64 symlinks for ONNX Runtime..."
        mkdir -p /usr/local/lib64
        ln -sf /usr/local/lib/libonnxruntime.so* /usr/local/lib64/
        ln -sf /usr/local/lib/libonnxruntime_providers_shared.so /usr/local/lib64/

        rm -rf onnxruntime-linux-*
        echo "✅ ONNX Runtime installed with lib64 symlinks"
      else
        echo "✅ ONNX Runtime already installed"
        if [ ! -d /usr/local/lib64 ]; then
          echo "🔗 Creating missing /usr/local/lib64 symlinks..."
          mkdir -p /usr/local/lib64
          ln -sf /usr/local/lib/libonnxruntime.so* /usr/local/lib64/
          ln -sf /usr/local/lib/libonnxruntime_providers_shared.so /usr/local/lib64/ 2>/dev/null || true
          echo "✅ lib64 symlinks created"
        fi
      fi

      # FAISS v1.8.0 (CPU-only, shared library) - Phase 2A
      if [ ! -f /usr/local/lib/libfaiss.so ]; then
        echo "🔍 Installing FAISS v1.8.0 (CPU-only, shared library)..."
        apt-get install -y libblas-dev liblapack-dev
        cd /tmp && rm -rf faiss
        git clone --depth 1 --branch v1.8.0 https://github.com/facebookresearch/faiss.git
        cd faiss
        mkdir -p build && cd build
        cmake .. \
          -DFAISS_ENABLE_GPU=OFF \
          -DFAISS_ENABLE_PYTHON=OFF \
          -DBUILD_TESTING=OFF \
          -DBUILD_SHARED_LIBS=ON \
          -DCMAKE_BUILD_TYPE=Release \
          -DCMAKE_INSTALL_PREFIX=/usr/local
        make -j$(nproc)
        make install
        ldconfig
        cd /tmp && rm -rf faiss
        echo "✅ FAISS installed successfully"
      else
        echo "✅ FAISS already installed"
      fi
      # XGBoost 3.2.0 (C API + Python) - ADR-026 Track 1
      if [ ! -f /usr/local/lib/libxgboost.so ]; then
        echo "🔍 Installing XGBoost 3.2.0..."
        pip3 install xgboost==3.2.0 --break-system-packages --timeout=300 || {
          echo "⚠️  PyPI inaccesible — fallback apt (versión no garantizada)"
          # TODO: verificar qué versión provee apt en Debian bookworm
          # apt show python3-xgboost — pendiente DEBT-XGBOOST-APT-001
          # Versión apt != 3.2.0 → resultados no reproducibles científicamente
          apt-get install -y python3-xgboost || true
          echo "❗ WARNING: xgboost $(python3 -c 'import xgboost; print(xgboost.__version__)' 2>/dev/null || echo 'not available')"
          echo "❗ Para reproducibilidad científica, usar xgboost==3.2.0"
        }
        # Headers C++ — desde pip (fallback si GitHub no accesible, DEBT-XGBOOST-HEADERS-001)
        mkdir -p /usr/local/include/xgboost
        XGB_INC=$(python3 -c "import xgboost,os; print(os.path.join(os.path.dirname(xgboost.__file__),'include'))" 2>/dev/null || echo "")
        if [ -d "$XGB_INC/xgboost" ]; then
          cp "$XGB_INC/xgboost/"*.h /usr/local/include/xgboost/ || true
        else
          curl -fsSL https://raw.githubusercontent.com/dmlc/xgboost/v3.2.0/include/xgboost/c_api.h \
            -o /usr/local/include/xgboost/c_api.h || true
          curl -fsSL https://raw.githubusercontent.com/dmlc/xgboost/v3.2.0/include/xgboost/base.h \
            -o /usr/local/include/xgboost/base.h || true
        fi
        # Librería compartida al path estándar
        XGBOOST_SO=$(python3 -c "import xgboost.core; print(xgboost.core.find_lib_path()[0])" 2>/dev/null)
        if [ -n "$XGBOOST_SO" ]; then
          cp "$XGBOOST_SO" /usr/local/lib/libxgboost.so
          ldconfig
          echo "✅ XGBoost installed: $(python3 -c 'import xgboost; print(xgboost.__version__)')"
          # libgomp bundled en xgboost wheel — symlink para dlopen desde plugins C++
          ln -sf /usr/local/lib/python3.11/dist-packages/xgboost.libs/libgomp-e985bcbb.so.1.0.0 /usr/local/lib/libgomp-e985bcbb.so.1.0.0
          ldconfig
        else
          echo "❌ libxgboost.so not found after pip + apt"
          exit 1
        fi
      else
        echo "✅ XGBoost already installed"
      fi

      # Dependencias Python para entrenamiento ML (ADR-026, train_xgboost_level1_v2.py)
      pip3 install pandas scikit-learn --break-system-packages --timeout=300 || {
        echo "⚠️  pandas/scikit-learn pip failed — intentando apt fallback"
        apt-get install -y python3-pandas python3-sklearn || true
      }
      # Directorio de plugins ML Defender
      mkdir -p /usr/lib/ml-defender/plugins

      # plugin_xgboost (ADR-026 Track 1) — build + deploy
      if [ ! -f /usr/lib/ml-defender/plugins/libplugin_xgboost.so ]; then
        echo "🔌 Building plugin_xgboost..."
        cd /vagrant/plugins/xgboost
        rm -rf build && mkdir -p build && cd build
        cmake -DCMAKE_BUILD_TYPE=Release .. && make -j4
        cp libplugin_xgboost.so /usr/lib/ml-defender/plugins/
        echo "✅ plugin_xgboost deployed"
      else
        echo "✅ plugin_xgboost already deployed"
      fi

      # plugin_test_message — build gestionado por make pipeline-build (requiere plugin-loader instalado)
      # NO buildear aquí: plugin-loader headers no disponibles en este punto del provisioning

      # etcd-cpp-api
      if [ ! -f /usr/local/lib/libetcd-cpp-api.so ] && [ ! -f /usr/local/lib/libetcd-cpp-api.a ]; then
        cd /tmp && rm -rf etcd-cpp-apiv3
        git clone https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git
        cd etcd-cpp-apiv3 && git checkout v0.15.3
        mkdir build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=/usr/local
        make -j4 && make install
        ldconfig
      fi

      # cpp-httplib
      if [ ! -f /usr/local/include/httplib.h ]; then
        cd /tmp && rm -rf cpp-httplib
        git clone https://github.com/yhirose/cpp-httplib.git
        mkdir -p /usr/local/include
        cp cpp-httplib/httplib.h /usr/local/include/
      fi

      # Crypto++
      if [ ! -f /usr/include/cryptopp/cryptlib.h ] && [ ! -f /usr/local/include/cryptopp/cryptlib.h ]; then
        apt-get install -y libcrypto++-dev libcrypto++-doc libcrypto++-utils || {
          cd /tmp
          wget https://www.cryptopp.com/cryptopp870.zip
          unzip cryptopp870.zip -d cryptopp
          cd cryptopp && make -j4 && make install
        }
      fi

      # llama.cpp
      if [ ! -f /vagrant/third_party/llama.cpp/build/src/libllama.a ]; then
        cd /vagrant/third_party/llama.cpp
        mkdir -p build && cd build
        cmake .. -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON \
          -DLLAMA_NATIVE=OFF -DLLAMA_NO_ACCELERATE=ON -DLLAMA_METAL=OFF -DCMAKE_BUILD_TYPE=Release
        cmake --build . --target all -- -j4
      fi

      # Download LLM model
      mkdir -p /vagrant/rag/models
      cd /vagrant/rag/models
      if [ ! -f "tinyllama-1.1b-chat-v1.0.Q4_0.gguf" ]; then
        wget -q --show-progress --continue --timeout=120 --tries=3 \
          "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf" || \
        curl -L -C - --progress-bar \
          "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf" \
          -o tinyllama-1.1b-chat-v1.0.Q4_0.gguf
      fi

      # Sudoers
      mkdir -p /etc/sudoers.d
      cat > /etc/sudoers.d/ml-defender << 'EOF'
vagrant ALL=(ALL) NOPASSWD: /vagrant/sniffer/build/sniffer
vagrant ALL=(ALL) NOPASSWD: /vagrant/firewall-acl-agent/build/firewall-acl-agent
vagrant ALL=(ALL) NOPASSWD: /usr/sbin/iptables
vagrant ALL=(ALL) NOPASSWD: /usr/sbin/ipset
vagrant ALL=(ALL) NOPASSWD: /usr/bin/pkill
vagrant ALL=(ALL) NOPASSWD: /bin/kill
vagrant ALL=(ALL) NOPASSWD: /usr/bin/killall
vagrant ALL=(ALL) NOPASSWD: /vagrant/tools/provision.sh
EOF
      chmod 0440 /etc/sudoers.d/ml-defender

      # System config
      sed -i '/es_ES.UTF-8/s/^# //g' /etc/locale.gen
      locale-gen es_ES.UTF-8
      update-locale LANG=es_ES.UTF-8 LC_ALL=es_ES.UTF-8

      if [ -f /proc/sys/net/core/bpf_jit_enable ]; then
        echo 1 > /proc/sys/net/core/bpf_jit_enable
        mountpoint -q /sys/fs/bpf || mount -t bpf none /sys/fs/bpf
        grep -q "/sys/fs/bpf" /etc/fstab || echo "none /sys/fs/bpf bpf defaults 0 0" >> /etc/fstab
      fi

      # Directory structure
      mkdir -p /vagrant/ml-detector/models/production/{level1,level2,level3}
      mkdir -p /vagrant/ml-training/outputs/onnx
      mkdir -p /vagrant/firewall-acl-agent/build/logs
      mkdir -p /vagrant/rag/build/logs
      mkdir -p /vagrant/logs/lab
      mkdir -p /var/log/ml-defender
      chown -R vagrant:vagrant /var/log/ml-defender
      chmod 755 /var/log/ml-defender

      # Protobuf generation
      if [ -f /vagrant/protobuf/generate.sh ] && [ ! -f /vagrant/protobuf/network_security.pb.cc ]; then
        cd /vagrant/protobuf && ./generate.sh
      fi

      if [ -f /vagrant/protobuf/network_security.pb.cc ]; then
        mkdir -p /vagrant/firewall-acl-agent/proto
        cp /vagrant/protobuf/network_security.pb.cc /vagrant/firewall-acl-agent/proto/
        cp /vagrant/protobuf/network_security.pb.h /vagrant/firewall-acl-agent/proto/
      fi

      # Build components
      if [ ! -f /vagrant/firewall-acl-agent/build/firewall-acl-agent ]; then
        mkdir -p /vagrant/firewall-acl-agent/build
        cd /vagrant/firewall-acl-agent/build
        cmake .. && make -j4
      fi

      # Bash aliases
      if ! grep -q "FAISS Ingestion aliases" /home/vagrant/.bashrc; then
        cat >> /home/vagrant/.bashrc << 'BASHRC_EOF'
# ML Defender aliases
alias build-sniffer='cd /vagrant/sniffer && make'
alias build-detector='cd /vagrant/ml-detector/build && rm -rf * && cmake .. && make -j4'
alias build-firewall='cd /vagrant/firewall-acl-agent/build && rm -rf * && cmake .. && make -j4'
alias build-rag='cd /vagrant/rag/build && rm -rf * && cmake .. && make -j4'
alias proto-regen='cd /vagrant/protobuf && ./generate.sh && cp network_security.pb.* /vagrant/firewall-acl-agent/proto/'
alias run-firewall='cd /vagrant/firewall-acl-agent/build && sudo ./firewall-acl-agent -c ../config/firewall.json'
alias run-detector='cd /vagrant/ml-detector/build && ./ml-detector -c ../config/ml_detector_config.json'
alias run-sniffer='cd /vagrant/sniffer/build && sudo ./sniffer -c ../config/sniffer.json'
alias run-rag='cd /vagrant/rag/build && ./rag-security -c ../config/rag_config.json'
alias run-lab='cd /vagrant && bash scripts/run_lab_dev.sh'
alias kill-lab='sudo pkill -9 firewall-acl-agent; pkill -9 ml-detector; sudo pkill -9 sniffer; pkill -9 rag-security'
alias status-lab='pgrep -a firewall-acl-agent; pgrep -a ml-detector; pgrep -a sniffer; pgrep -a rag-security'
alias logs-firewall='tail -f /vagrant/firewall-acl-agent/build/logs/*.log 2>/dev/null'
alias logs-detector='tail -f /vagrant/ml-detector/build/logs/*.log 2>/dev/null'
alias logs-sniffer='tail -f /vagrant/logs/lab/sniffer.log 2>/dev/null'
alias logs-rag='tail -f /vagrant/rag/build/logs/*.log 2>/dev/null'
alias logs-lab='cd /vagrant && bash scripts/monitor_lab.sh'

# Gateway testing aliases
alias test-gateway='/vagrant/scripts/gateway/defender/validate_gateway.sh'
alias start-gateway='/vagrant/scripts/gateway/defender/start_gateway_test.sh'
alias gateway-dash='/vagrant/scripts/gateway/defender/gateway_dashboard.sh'

# FAISS Ingestion aliases (Phase 2A)
alias explore-logs='/vagrant/scripts/explore_rag_logs.sh'
alias verify-faiss='ls -lh /usr/local/lib/libfaiss.so && ls -d /usr/local/include/faiss'
alias verify-onnx='ls -lh /usr/local/lib/libonnxruntime.so && find /usr/local/include -name "onnxruntime*.h"'

# Provisioning aliases (DAY 95)
alias provision-status='sudo bash /vagrant/tools/provision.sh status'
alias provision-verify='sudo bash /vagrant/tools/provision.sh verify'

export PROJECT_ROOT="/vagrant"
export MODELS_DIR="/vagrant/ml-detector/models/production"

cat << 'WELCOME'
╔════════════════════════════════════════════════════════════╗
║  ML Defender - Network Security Pipeline                   ║
║  Development Environment - PHASE 2A (FAISS)                ║
╚════════════════════════════════════════════════════════════╝
🎯 Dual-NIC Configuration:
   eth1: 192.168.56.20 (WAN-facing, host-based IDS)
   eth2: 192.168.100.1 (LAN-facing, gateway mode)
🔐 Cryptographic Provisioning (DAY 95):
   provision-status  # Estado de claves
   provision-verify  # Verificar integridad
🔍 FAISS Ingestion Ready:
   explore-logs     # Explore available RAG logs
   verify-faiss     # Verify FAISS installation
   verify-onnx      # Verify ONNX Runtime
🚀 Gateway Testing:
   start-gateway    # Start sniffer in gateway mode
   test-gateway     # Validate gateway capture
   gateway-dash     # Live monitoring dashboard
WELCOME
BASHRC_EOF
      fi

      echo "✅ PROVISIONING COMPLETED SUCCESSFULLY!"
      # Falco .deb — descargado en dev VM → dist/vendor/ para instalar offline en hardened VM (ADR-030 BSR)
      # dist/vendor/ es la fuente de verdad. CHECKSUMS generado aquí y committeado. .deb gitignored.
      mkdir -p /vagrant/dist/vendor
      if ls /vagrant/dist/vendor/falco_*.deb 1>/dev/null 2>&1; then
        echo "✅ Falco .deb ya presente en /vagrant/dist/vendor/"
      else
        echo "📦 Descargando Falco .deb → dist/vendor/..."
        curl -fsSL https://falco.org/repo/falcosecurity-packages.asc | \
          gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] https://download.falco.org/packages/deb stable main" | \
          tee /etc/apt/sources.list.d/falcosecurity.list
        apt-get update -qq
        cd /vagrant/dist/vendor && apt-get download falco
        echo "✅ Falco .deb descargado en /vagrant/dist/vendor/"
      fi
      sha256sum /vagrant/dist/vendor/falco_*.deb > /vagrant/dist/vendor/CHECKSUMS
      echo "✅ dist/vendor/CHECKSUMS actualizado"


      # ── Ansible + Jinja2 (DEBT-VAULT-PROVISION-PROD-001) ─────────────────
      # Ansible: controller de orquestacion (solo en dev, no en prod — ADR-039)
      if ! command -v ansible &>/dev/null; then
        echo "📦 Instalando Ansible + Jinja2..."
        apt-get install -y ansible
        pip3 install jinja2 --break-system-packages --quiet
        echo "✅ Ansible $(ansible --version | head -1) instalado"
        echo "✅ Jinja2 $(python3 -c 'import jinja2; print(jinja2.__version__)')"
      else
        echo "✅ Ansible ya instalado: $(ansible --version | head -1)"
      fi

      # ── Auditoría de seguridad: cppcheck + semgrep (make audit, DAY 181) ──
      # Dev-only (ADR-039): análisis estático/taint, no van a prod. cppcheck por
      # apt; semgrep por pip con --break-system-packages (convención del guest
      # desechable, igual que xgboost/pandas/jinja2). Provisión, NO runtime:
      # contrib/audit/audit.mk solo VERIFICA presencia (separación build/runtime).
      if ! command -v cppcheck &>/dev/null; then
        echo "🔬 Instalando cppcheck (análisis estático C++)..."
        apt-get install -y cppcheck
        echo "✅ cppcheck $(cppcheck --version)"
      else
        echo "✅ cppcheck ya instalado: $(cppcheck --version)"
      fi

      if ! command -v semgrep &>/dev/null; then
        echo "🛡️  Instalando semgrep (taint H-1/H-2)..."
        pip3 install semgrep --break-system-packages --quiet
        echo "✅ semgrep $(semgrep --version 2>/dev/null | head -1)"
      else
        echo "✅ semgrep ya instalado: $(semgrep --version 2>/dev/null | head -1)"
      fi

      # ── HashiCorp Vault (DEBT-CRYPTO-MATERIAL-STORAGE-001) ─────────────────
      # Fix DAY 160: repo hashicorp OK con dearmor directo
      if ! command -v vault &>/dev/null; then
        echo "📦 Instalando HashiCorp Vault..."
        wget -O - https://apt.releases.hashicorp.com/gpg 2>/dev/null | \
          gpg --dearmor | \
          tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" | \
          tee /etc/apt/sources.list.d/hashicorp.list
        apt-get update -qq
        apt-get install -y vault
        echo "✅ Vault $(vault version | head -1) instalado"
      else
        echo "✅ Vault ya instalado: $(vault version | head -1)"
      fi

      # ── Java 21 via SDKMAN (requerido por Jenkins 2.555+) ──────────────────
      # Fix DAY 160: Java 21 no está en repos Bookworm — SDKMAN + Temurin
      # Jenkins 2.555.2 requiere Java 21 mínimo (Java 17 falla silenciosamente)
      if [ ! -f /root/.sdkman/candidates/java/21.0.7-tem/bin/java ]; then
        echo "📦 Instalando prereqs SDKMAN (unzip, zip)..."
        apt-get install -y unzip zip 2>&1 | tail -1
        echo "📦 Instalando SDKMAN..."
        curl -s https://get.sdkman.io | bash
        echo "📦 Instalando Java 21.0.7 Temurin via SDKMAN..."
        source /root/.sdkman/bin/sdkman-init.sh
        sdk install java 21.0.7-tem < /dev/null
        echo "✅ Java 21 Temurin instalado"
      else
        echo "✅ Java 21 Temurin ya instalado"
      fi

      # ── Jenkins (DEBT-VAULT-PROVISION-PROD-001) ───────────────────────────
      # Fix DAY 160: key via keyserver (jenkins.io-2023.key rotada — NO usar)
      # Fix DAY 160: Jenkins 2.555+ requiere Java 21 — JAVA_HOME en defaults
      # Fix DAY 160: Jenkins como root en dev (Java 21 en /root/.sdkman)
      if ! command -v jenkins &>/dev/null && [ ! -f /etc/init.d/jenkins ]; then
        echo "📦 Instalando Jenkins 2.555+..."
        gpg --keyserver keyserver.ubuntu.com --recv-keys 7198F4B714ABFC68 2>/dev/null
        gpg --export 7198F4B714ABFC68 \
          | tee /usr/share/keyrings/jenkins-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" \
          | tee /etc/apt/sources.list.d/jenkins.list
        apt-get update -qq
        apt-get install -y jenkins
        echo "JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem" >> /etc/default/jenkins
        echo "JAVA=/root/.sdkman/candidates/java/21.0.7-tem/bin/java" >> /etc/default/jenkins
        sed -i 's/^JENKINS_USER=.*/JENKINS_USER=root/' /etc/default/jenkins
        sed -i 's/^JENKINS_GROUP=.*/JENKINS_GROUP=root/' /etc/default/jenkins
        mkdir -p /etc/systemd/system/jenkins.service.d
        printf '[Service]\nUser=root\nGroup=root\nEnvironment="JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem"\nEnvironment="PATH=/root/.sdkman/candidates/java/21.0.7-tem/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n' \
          > /etc/systemd/system/jenkins.service.d/java21.conf
        systemctl daemon-reload
        systemctl enable jenkins
        systemctl start jenkins
        echo "✅ Jenkins instalado (puerto 8080)"
        echo "⚠️  Password inicial: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
      else
        echo "✅ Jenkins ya instalado — asegurando arranque..."
        systemctl start jenkins 2>/dev/null || true
      fi

      # Vault autostart movido a vault-enterprise-bootstrap (run: always) — DAY 163

      # ── Kuzu v0.11.3 embebido (backend IGraphSink — DAY 180) ──────────────
            # ⚠️  Upstream ARCHIVADO (10-oct-2025): v0.11.3 = release final, sin parches
            #     futuros. Mitigado por abstracción IGraphSink. Plan B: fork
            #     Vela-Engineering/kuzu. Ver nota BACKLOG DAY 180.
            # C++ client = libkuzu.so + kuzu.hpp (NO hay .deb upstream). Pin URL+SHA256.
            # DB = fichero único .kuzu desde v0.11.0 (no directorio).
            if [ ! -f /usr/local/lib/libkuzu.so ]; then
              echo "🗃️  Installing Kuzu v0.11.3 (embedded graph backend)..."
              KUZU_URL="https://github.com/kuzudb/kuzu/releases/download/v0.11.3/libkuzu-linux-x86_64.tar.gz"
              KUZU_SHA256="e99f9671ebfacf4d6208aa4b94490016e4ac9be242deed1fea78afb31c058ebd"   # ← pega aquí el sha256sum tras la 1ª descarga

              cd /tmp && rm -rf kuzu-install && mkdir kuzu-install && cd kuzu-install
              curl -fsSL "$KUZU_URL" -o libkuzu.tar.gz

              GOT=$(sha256sum libkuzu.tar.gz | awk '{print $1}')
              if [ "$KUZU_SHA256" = "PENDIENTE_PINEAR" ]; then
                echo "⚠️  SHA256 sin pinear. Descargado: $GOT"
                echo "    → Pégalo en KUZU_SHA256 y re-provisiona para fijar el pin."
              elif [ "$GOT" != "$KUZU_SHA256" ]; then
                echo "❌ SHA256 mismatch Kuzu: esperado $KUZU_SHA256, obtenido $GOT"; exit 1
              else
                echo "✅ SHA256 Kuzu verificado"
              fi

              tar xzf libkuzu.tar.gz
              KUZU_SO=$(find . -name 'libkuzu.so*' | head -1)
              KUZU_HPP=$(find . -name 'kuzu.hpp' | head -1)
              KUZU_H=$(find . -name 'kuzu.h' | head -1)
              if [ -z "$KUZU_SO" ] || [ -z "$KUZU_HPP" ]; then
                echo "❌ Artefactos Kuzu no hallados en el tarball (so/hpp)"; exit 1
              fi
              cp "$KUZU_SO" /usr/local/lib/libkuzu.so
              cp "$KUZU_HPP" /usr/local/include/
              [ -n "$KUZU_H" ] && cp "$KUZU_H" /usr/local/include/
              ldconfig
              cd /tmp && rm -rf kuzu-install
              echo "✅ Kuzu instalado: $(ls -la /usr/local/lib/libkuzu.so)"
            else
              echo "✅ Kuzu ya instalado"
            fi
            # ── libavro-c 1.11.1 (I/O AVRO, zona bronce del circuito) ─────────────
                  # DEBT-CIRCUIT-PARSER-CROSSLANG-001 cerrada por diseño: I/O AVRO en API C
                  # wrapeada desde C++20, mismo patrón que OpenSSL en CorrelationWriter.
                  # Ver docs/design/eslabon-1-flujo-a-avro-parquet.md (ratificado Consejo DAY 205).
                  if [ ! -f /usr/include/avro.h ]; then
                    echo "📦 Instalando libavro-dev (I/O AVRO bronce, Eslabón 1)..."
                    apt-get install -y --no-install-recommends libavro-dev
                    echo "✅ avro-c $(dpkg -s libavro-dev | grep '^Version' | awk '{print $2}') instalado"
                  else
                    echo "✅ libavro-dev ya instalado"
                  fi

                  # ── Apache Arrow / Parquet 24.0.0-1 (zona oro, escritura Parquet) ─────
                  # Versión pinneada explícita — regla de proceso ratificada Consejo DAY 205:
                  # "se pinnea la primera versión que supera la batería de validación
                  # reproducible; toda actualización posterior exige revalidación completa".
                  # Smoke test verde (12/12) en defender DAY 205 contra esta versión exacta.
                  ARROW_PIN="24.0.0-1"
                  if [ ! -f /etc/apt/sources.list.d/apache-arrow.sources ] && \
                     ! dpkg -l apache-arrow-apt-source >/dev/null 2>&1; then
                    echo "📦 Añadiendo repo oficial Apache Arrow (Bookworm)..."
                    wget -q https://apache.jfrog.io/artifactory/arrow/debian/apache-arrow-apt-source-latest-bookworm.deb \
                      -O /tmp/arrow-apt.deb
                    apt-get install -y /tmp/arrow-apt.deb
                    rm -f /tmp/arrow-apt.deb
                    apt-get update -qq
                    echo "✅ Repo apache-arrow-apt-source añadido"
                  else
                    echo "✅ Repo apache-arrow-apt-source ya presente"
                  fi

                  INSTALLED_ARROW=$(dpkg -s libarrow-dev 2>/dev/null | grep '^Version' | awk '{print $2}' || echo "none")
                  if [ "$INSTALLED_ARROW" != "$ARROW_PIN" ]; then
                    echo "📦 Instalando libarrow-dev=${ARROW_PIN} libparquet-dev=${ARROW_PIN} (pinneado)..."
                    apt-get install -y -V "libarrow-dev=${ARROW_PIN}" "libparquet-dev=${ARROW_PIN}"
                    apt-mark hold libarrow-dev libparquet-dev
                    echo "✅ Arrow/Parquet ${ARROW_PIN} instalado y bloqueado (apt-mark hold)"
                  else
                    echo "✅ libarrow-dev ${ARROW_PIN} ya instalado y pinneado"
                    apt-mark hold libarrow-dev libparquet-dev >/dev/null 2>&1 || true
                  fi
    DEPENDENCIES_EOF

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: directorio de runtime del grafo Kuzu (DAY 180)
    # ════════════════════════════════════════════════════════════════════════
    # SITUACIÓN TEMPORAL — leer antes de tocar:
    #   · La landing zone bronce/plata/oro NO se crea aquí. Su destino real es
    #     Apache Iceberg, que gestionará sus propias rutas y política de tablas.
    #     Crear /var/lib/argus/{bronze,silver,gold} ahora sería trabajo que
    #     Iceberg deshará. Paso a paso: hoy solo el grafo necesita hogar.
    #   · El grafo es propiedad EXCLUSIVA de Kuzu (por ahora): fichero único .kuzu.
    #   · NO puede vivir en /vagrant: es mount vboxsf y Kuzu mapea con mmap (rompe).
    #     Por eso fs LOCAL del guest: /opt/argus/graph.
    #   · Esta carpeta debe ser vigilada por Falco (ADR-030 BSR): reglas TEMPORALES
    #     en falco/rules.d/argus_graph.yaml (revisar/retirar al migrar a Iceberg).
    #   · Owner = vagrant (el correlation-engine corre como vagrant en dev). El
    #     usuario de producción está por decidir (componentes de las Raspberry).
    defender.vm.provision "shell", name: "configure-argus-graph-dir", run: "always",
      inline: <<-ARGUS_GRAPH
      echo "🗂️  Preparando runtime del grafo Kuzu (/opt/argus/graph)..."
      mkdir -p /opt/argus/graph
      chown -R vagrant:vagrant /opt/argus
      chmod 750 /opt/argus/graph
      echo "✅ /opt/argus/graph listo ($(stat -c '%U:%G %a' /opt/argus/graph))"
    ARGUS_GRAPH

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: Auto-configure sniffer.json
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "configure-sniffer", run: "always", inline: <<-SNIFFER_CONFIG
      echo "🔧 Auto-configuring sniffer.json for current network topology..."

      GATEWAY_IFACE=$(ip -o addr show | grep "192.168.100.1" | awk '{print $2}')
      if [ -z "$GATEWAY_IFACE" ]; then
        echo "⚠️  Gateway interface not found, defaulting to eth2"
        GATEWAY_IFACE="eth2"
      fi
      echo "✅ Gateway interface detected: $GATEWAY_IFACE"

      if [ -f /vagrant/sniffer/config/sniffer.json ]; then
        cp /vagrant/sniffer/config/sniffer.json /vagrant/sniffer/config/sniffer.json.auto.backup
        sed -i "s/\\"interface\\": \\"eth[0-9]\\"/\\"interface\\": \\"$GATEWAY_IFACE\\"/g" /vagrant/sniffer/config/sniffer.json
        echo "✅ sniffer.json updated with gateway interface: $GATEWAY_IFACE"
      else
        echo "⚠️  sniffer.json not found at /vagrant/sniffer/config/sniffer.json"
      fi

      echo "═══════════════════════════════════════════════════════════"
      echo "🎯 SNIFFER AUTO-CONFIGURATION COMPLETE"
      echo "═══════════════════════════════════════════════════════════"
      echo "WAN interface:     eth1 (192.168.56.20)"
      echo "Gateway interface: $GATEWAY_IFACE (192.168.100.1)"
      echo "═══════════════════════════════════════════════════════════"
    SNIFFER_CONFIG

    defender.vm.provision "shell", name: "ntp-sync", run: "always", inline: <<-NTP_SYNC
      echo "⏱️  NTP sync check (ADR-046 P0)..."

      # Forzar sync inmediato (especialmente útil tras vagrant up en frío)
      chronyc makestep 1.0 3 2>/dev/null || true
      sleep 2

      # Verificar offset
      OFFSET=$(chronyc tracking 2>/dev/null \
        | grep "System time" \
        | awk '{print $4}' \
        | sed 's/-//')

      if [ -z "$OFFSET" ]; then
        echo "⚠️  chronyc tracking no disponible — chrony no sincronizado aún"
        echo "   Continuando (gate P0 en runtime del correlation-engine)"
      else
        # Comparar con threshold 1.0s usando awk (bash no maneja floats)
        OVER=$(awk "BEGIN {print ($OFFSET > 1.0) ? 1 : 0}")
        if [ "$OVER" = "1" ]; then
          echo "❌ NTP offset ${OFFSET}s > 1.0s — WARN (gate bloqueará correlation-engine)"
        else
          echo "✅ NTP offset ${OFFSET}s < 1.0s — OK"
        fi
      fi

      chronyc tracking | grep -E "Reference ID|System time|Stratum" || true
    NTP_SYNC

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: Cron restart every 72h (memory leak mitigation)
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "configure-cron-restart", run: "once", inline: <<-CRON
      echo "⏰ Configurando cron para restart automático cada 72h..."
      CRON_ENTRY="0 3 */3 * * /vagrant/scripts/restart_ml_defender.sh"
      if ! crontab -u vagrant -l 2>/dev/null | grep -q "restart_ml_defender"; then
        (crontab -u vagrant -l 2>/dev/null; echo "# ML Defender restart every 72h (memory leak mitigation)") | crontab -u vagrant -
        (crontab -u vagrant -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -u vagrant -
        echo "✅ Cron configurado: Restart cada 3 días a las 3:00 AM"
      else
        echo "✅ Cron ya configurado"
      fi
      crontab -u vagrant -l
    CRON

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: SQLite.db necessary for RAG and RAG-INGESTER (Day 40)
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "configure-sqlite-day40", run: "once", inline: <<-SQLITE
      echo "📁 Day 40: Creating shared indices directory..."
      mkdir -p /vagrant/shared/indices
      chown -R vagrant:vagrant /vagrant/shared/indices
      chmod 755 /vagrant/shared/indices
      echo "✅ Shared indices directory ready: /vagrant/shared/indices"

      if ! dpkg -l | grep -q libsqlite3-dev; then
        echo "📦 Installing SQLite3 development headers + CLI..."
        apt-get install -y libsqlite3-dev sqlite3
        echo "✅ SQLite3 dev + CLI installed"
      else
        echo "✅ SQLite3 dev already installed"
        apt-get install -y sqlite3
      fi
    SQLITE

    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: Cryptographic Identity (DAY 95)
    # tools/provision.sh genera keypairs Ed25519 + seeds ChaCha20
    # para los 6 componentes del pipeline.
    #
    # run: "once" — las claves persisten entre reinicios de VM.
    # Para re-provisionar manualmente: make provision
    # Para re-provisionar un componente: make provision-reprovision COMPONENT=sniffer
    #
    # ADR refs: ADR-013 (seed distribution), ADR-019 (OS hardening)
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "cryptographic-provisioning", run: "once", inline: <<-CRYPTO_PROVISION
      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║  🔐 Cryptographic Provisioning (DAY 95 — PHASE 1)         ║"
      echo "╚════════════════════════════════════════════════════════════╝"

      if [ ! -f /vagrant/tools/provision.sh ]; then
        echo "❌ tools/provision.sh no encontrado en /vagrant/tools/"
        echo "   Asegúrate de que el repositorio está montado correctamente."
        exit 1
      fi

      chmod +x /vagrant/tools/provision.sh
      bash /vagrant/tools/provision.sh full

      echo "✅ Cryptographic provisioning completed"
      echo "   Keys at: /etc/ml-defender/"
      echo "   Verify:  sudo bash /vagrant/tools/provision.sh status"

      echo "📦 Installing systemd units (TEST-PROVISION-1 Check 5)..."
      if [ -f /vagrant/etcd-server/config/install-systemd-units.sh ]; then
        bash /vagrant/etcd-server/config/install-systemd-units.sh
        echo "✅ systemd units installed"
      else
        echo "⚠️  install-systemd-units.sh not found — skipping"
      fi
    CRYPTO_PROVISION

    # ════════════════════════════════════════════════════════════════════════
    # Enterprise Crypto Bootstrap — Modelo B (efímero por diseño)
    # run: "always" — cada vagrant up genera nuevo keypair enterprise
    # vendor.key NUNCA persiste en disco — solo en Vault dev (inmem)
    # BACKLOG-CRYPTO-VENDOR-KEY-001 (DAY 163)
    # ════════════════════════════════════════════════════════════════════════
    defender.vm.provision "shell", name: "vault-enterprise-bootstrap", run: "always", inline: <<-VAULT_ENTERPRISE
      set -e
      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║  🔐 Enterprise Crypto Bootstrap — Modelo B (efímero)      ║"
      echo "║  Nuevo keypair → Vault → nuevo token (cada vagrant up)    ║"
      echo "╚════════════════════════════════════════════════════════════╝"

      export VAULT_ADDR=http://127.0.0.1:8200
      export VAULT_TOKEN=argus-dev-token

      # ── 1. Vault dev ──────────────────────────────────────────────────
      if ! pgrep -x vault > /dev/null; then
        echo "🔐 Arrancando Vault dev mode..."
        nohup vault server -dev \
          -dev-root-token-id=argus-dev-token \
          -dev-listen-address=0.0.0.0:8200 \
          > /tmp/vault-dev.log 2>&1 &
        sleep 3
        echo "✅ Vault dev OK"
      else
        echo "✅ Vault ya corriendo (pid: $(pgrep -x vault))"
      fi

      # secret/argus/crypto: siempre recrear (Vault dev es inmem)
      vault kv put secret/argus/crypto \
        seed=argus-dev-seed-32bytes-placeholder \
        provider=vault_crypto > /dev/null
      echo "✅ secret/argus/crypto recreado"

      # ── 2. Python cryptography (si no está) ───────────────────────────
      python3 -c "import cryptography" 2>/dev/null || \
        pip3 install cryptography --break-system-packages --quiet

      # ── 3. Generar nuevo keypair Ed25519 enterprise ────────────────────
      echo "🔑 Generando nuevo keypair enterprise (Modelo B)..."
      rm -f /tmp/argus_vendor.key /tmp/argus_vendor.pub /tmp/argus_enterprise.token

      python3 /vagrant/enterprise/scripts/generate_token.py \
        --gen-keypair \
        --privkey /tmp/argus_vendor.key \
        --pubkey  /tmp/argus_vendor.pub

      if [ ! -f /tmp/argus_vendor.key ] || [ ! -f /tmp/argus_vendor.pub ]; then
        echo "❌ generate_token.py --gen-keypair no generó los ficheros esperados"
        exit 1
      fi
      echo "✅ Keypair generado en /tmp"

      # ── 4. Extraer pubkey hex (32 bytes Ed25519 raw) ──────────────────
      PUBKEY_HEX=$(openssl pkey -in /tmp/argus_vendor.pub -pubin -outform DER \
        | tail -c 32 | od -A n -t x1 | tr -d ' \n')

      if [ -z "$PUBKEY_HEX" ] || [ ${#PUBKEY_HEX} -ne 64 ]; then
        echo "❌ Pubkey hex inválido: '$PUBKEY_HEX' (longitud: ${#PUBKEY_HEX})"
        exit 1
      fi
      echo "✅ Pubkey hex: $PUBKEY_HEX"

      # ── 5. Subir a Vault ──────────────────────────────────────────────
      vault kv put secret/argus/enterprise/vendor-key \
        key=$(base64 -w0 /tmp/argus_vendor.key)
      vault kv put secret/argus/enterprise/vendor-pubkey \
        hex=$PUBKEY_HEX
      echo "✅ Vault: vendor-key + vendor-pubkey almacenados"

      # ── 6. Generar token enterprise (365 días) ────────────────────────
      python3 /vagrant/enterprise/scripts/generate_token.py \
        --privkey     /tmp/argus_vendor.key \
        --pubkey      /tmp/argus_vendor.pub \
        --instance-id argus-dev \
        --features    vault_crypto \
        --days        365 \
        --out         /tmp/argus_enterprise.token

      if [ ! -f /tmp/argus_enterprise.token ]; then
        echo "❌ Token no generado"
        exit 1
      fi
      echo "✅ Token enterprise generado"

      # ── 7. Instalar artefactos en /vagrant/enterprise/ ────────────────
      cp /tmp/argus_vendor.pub       /vagrant/enterprise/enterprise_vendor.pub
      cp /tmp/argus_enterprise.token /vagrant/enterprise/enterprise.token
      echo "✅ enterprise_vendor.pub + enterprise.token actualizados"

      # ── 8. Token en Vault (etcd-server lo consulta en runtime) ────────
      vault kv put secret/argus/enterprise/token \
        value=@/tmp/argus_enterprise.token
      echo "✅ Vault: enterprise.token almacenado"

      # ── 9. Limpiar /tmp ───────────────────────────────────────────────
      rm -f /tmp/argus_vendor.key /tmp/argus_vendor.pub /tmp/argus_enterprise.token
      echo "✅ /tmp limpiado — vendor.key nunca persiste en disco"

      echo ""
      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║  ✅ Enterprise crypto bootstrap completado                 ║"
      echo "╚════════════════════════════════════════════════════════════╝"
      echo "   Pubkey hex : $PUBKEY_HEX"
      echo "   Token      : /vagrant/enterprise/enterprise.token"
      echo "   Vault      : secret/argus/enterprise/{vendor-key,vendor-pubkey,token}"
      echo "   vendor.key : solo en Vault (nunca en disco)"
    VAULT_ENTERPRISE

  end  # End defender VM

  # ════════════════════════════════════════════════════════════════════════════
  # CLIENT VM - Traffic Generator & Gateway Testing
  # ════════════════════════════════════════════════════════════════════════════

  config.vm.define "client", autostart: false do |client|
    client.vm.provision "shell", name: "wazuh-agent", env: {"AGENT_NAME" => "client"}, inline: WAZUH_AGENT_INSTALL
    client.vm.box = "debian/bookworm64"
    client.vm.box_version = "12.20240905.1"
    client.vm.hostname = "ml-client"

    client.vm.provider "virtualbox" do |vb|
      vb.name = "ml-defender-client"
      vb.memory = "1024"
      vb.cpus = 2
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
    end

    # Network: LAN only (connects to defender eth2)
    client.vm.network "private_network",
      ip: "192.168.100.50",
      virtualbox__intnet: "ml_defender_gateway_lan"

    client.vm.provision "shell", name: "client-setup", run: "always", inline: <<-CLIENT
          export DEBIAN_FRONTEND=noninteractive
          # NO set -e (regla de provisioning): un repo externo caído no debe tumbar el up
          echo "=== ML CLIENT — Traffic Generator + MITRE Attack Tools ==="
          apt-get update -qq || true
          apt-get install -y --no-install-recommends \
          curl wget iproute2 net-tools dnsutils \
          tcpdump tcpreplay netcat-openbsd \
          iputils-ping procps chrony \
          nmap hydra sqlmap \
          python3 python3-pip git \
          || { echo "FATAL: herramientas base no instaladas"; exit 1; }

          # Atomic Red Team (ground truth reproducible — DEBT-ARGUSPP-MITRE-001)
          if [ ! -d /opt/atomic-red-team ]; then
            git clone --depth 1 \
              https://github.com/redcanaryco/atomic-red-team.git \
              /opt/atomic-red-team || \
              echo "⚠️  atomic-red-team clone failed — red team offline mode"
          fi

          # NTP sync — community_id requiere timestamps coherentes
          systemctl enable chrony
          systemctl start chrony
          chronyc makestep 1.0 3 2>/dev/null || true

          # Routing hacia defender
          ip route del default 2>/dev/null || true
          ip route add default via 192.168.100.1 dev eth1

          chattr -i /etc/resolv.conf 2>/dev/null || true
          echo "nameserver 8.8.8.8" > /etc/resolv.conf
          echo "nameserver 1.1.1.1" >> /etc/resolv.conf
          chattr +i /etc/resolv.conf 2>/dev/null || true

          echo "=== CLIENT READY ==="
          echo "   IP      : 192.168.100.50"
          echo "   Gateway : 192.168.100.1 (defender eth2)"
          echo "   Tools   : nmap hydra sqlmap tcpreplay atomic-red-team"
        CLIENT

  end  # End client VM

# ════════════════════════════════════════════════════════════════════════════
  # SURICATA VM — IDS signatures (ADR-048 F2)
  # ════════════════════════════════════════════════════════════════════════════
  config.vm.define "suricata", autostart: false do |suricata|
    suricata.vm.provision "shell", name: "wazuh-agent", env: {"AGENT_NAME" => "suricata"}, inline: WAZUH_AGENT_INSTALL
    suricata.vm.box         = "debian/bookworm64"
    suricata.vm.box_version = "12.20240905.1"
    suricata.vm.hostname    = "argus-suricata"

    suricata.vm.provider "virtualbox" do |vb|
      vb.name   = "argus-suricata"
      vb.memory = "2048"
      vb.cpus   = 2
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
      vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
      vb.customize ["modifyvm", :id, "--ioapic", "on"]
      vb.customize ["modifyvm", :id, "--audio", "none"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
    end

    suricata.vm.network "private_network",
      ip: "192.168.100.10",
      virtualbox__intnet: "ml_defender_gateway_lan"

    suricata.vm.synced_folder ".", "/vagrant", type: "virtualbox",
      mount_options: ["dmode=775,fmode=775,exec"]

    suricata.vm.provision "shell", name: "install-suricata", inline: <<-SHELL
      export DEBIAN_FRONTEND=noninteractive
      echo "=== Installing Suricata + ET Open rules (ADR-048 F2) ==="

      apt-get update -qq
      apt-get install -y curl gnupg2 chrony net-tools procps python3 jq tcpreplay

      systemctl enable chrony
      systemctl start chrony
      chronyc makestep 1.0 3 2>/dev/null || true

      # DNS fix DESPUES de chrony — chattr bloquea sobreescritura
      echo "nameserver 8.8.8.8" > /etc/resolv.conf
      echo "nameserver 1.1.1.1" >> /etc/resolv.conf
      chattr +i /etc/resolv.conf

      # bookworm-backports para libhtp2 >= 0.5.50 (Suricata 7.x)
      echo "deb http://deb.debian.org/debian bookworm-backports main" \
        > /etc/apt/sources.list.d/backports.list
      apt-get update -qq
      apt-get install -y -t bookworm-backports libhtp2 || { echo "❌ libhtp2 failed"; exit 1; }
      apt-get install -y suricata suricata-update || { echo "❌ suricata install failed"; exit 1; }

      suricata --build-info | grep -i "version" || true

      suricata-update --no-reload || true
      echo "Rules: $(find /var/lib/suricata/rules -name '*.rules' 2>/dev/null | head -1)"

      sed -i 's/- interface: eth0/- interface: eth1/' /etc/suricata/suricata.yaml
      ip link set eth1 promisc on || true
      echo 'ip link set eth1 promisc on' >> /etc/rc.local
      chmod +x /etc/rc.local

      # community-id: yes — DEBT-ARGUSPP-COMMUNITY-ID-001
      sed -i '/community-id:/s/false/yes/' /etc/suricata/suricata.yaml
      # community-id-seed=0 explicito — paridad con aRGus y Zeek (FIX DAY170).
      # No depender del default de fabrica; garantizar la clave del join cross-tool.
      sed -i 's/^\([[:space:]]*\)community-id-seed:[[:space:]]*[0-9]*/\1community-id-seed: 0/' /etc/suricata/suricata.yaml

      mkdir -p /var/log/suricata
      chown -R suricata:suricata /var/log/suricata 2>/dev/null || true

      echo "=== Suricata ready ==="
      suricata --build-info | grep -iE "version|AF_PACKET|PCAP" || true
      echo "community-id: $(grep 'community-id' /etc/suricata/suricata.yaml | head -1)"
      ip link show eth1 | grep -i promisc || echo "⚠️  eth1 promisc no activo aun"
    SHELL

    suricata.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN

  end  # End suricata VM

  # ════════════════════════════════════════════════════════════════════════════
  # ZEEK VM — protocol analysis / observability layer (ADR-048 F3)
  # ════════════════════════════════════════════════════════════════════════════
  config.vm.define "zeek", autostart: false do |zeek|
    zeek.vm.provision "shell", name: "wazuh-agent", env: {"AGENT_NAME" => "zeek"}, inline: WAZUH_AGENT_INSTALL
    zeek.vm.box         = "debian/bookworm64"
    zeek.vm.box_version = "12.20240905.1"
    zeek.vm.hostname    = "argus-zeek"

    zeek.vm.provider "virtualbox" do |vb|
      vb.name   = "argus-zeek"
      vb.memory = "2048"
      vb.cpus   = 2
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
      vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
      vb.customize ["modifyvm", :id, "--ioapic", "on"]
      vb.customize ["modifyvm", :id, "--audio", "none"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
    end

    zeek.vm.network "private_network",
      ip: "192.168.100.11",
      virtualbox__intnet: "ml_defender_gateway_lan"

    zeek.vm.synced_folder ".", "/vagrant", type: "virtualbox",
      mount_options: ["dmode=775,fmode=775,exec"]

    zeek.vm.provision "shell", name: "install-zeek", inline: <<-SHELL
      export DEBIAN_FRONTEND=noninteractive
      echo "=== Installing Zeek (ADR-048 F3) ==="

      apt-get update -qq
      apt-get install -y curl gnupg2 chrony net-tools procps

      systemctl enable chrony
      systemctl start chrony
      chronyc makestep 1.0 3 2>/dev/null || true

      # DNS fix DESPUES de chrony
      echo "nameserver 8.8.8.8" > /etc/resolv.conf
      echo "nameserver 1.1.1.1" >> /etc/resolv.conf
      chattr +i /etc/resolv.conf

      # Zeek repo oficial OpenSUSE
      echo 'deb http://download.opensuse.org/repositories/security:/zeek/Debian_12/ /' \
        > /etc/apt/sources.list.d/zeek.list
      curl -fsSL https://download.opensuse.org/repositories/security:/zeek/Debian_12/Release.key \
        | gpg --dearmor > /etc/apt/trusted.gpg.d/zeek.gpg
      apt-get update -qq
      apt-get install -y zeek || { echo "❌ zeek install failed"; exit 1; }

      echo 'export PATH=/opt/zeek/bin:$PATH' >> /etc/profile.d/zeek.sh
      chmod +x /etc/profile.d/zeek.sh
      export PATH=/opt/zeek/bin:$PATH

      sed -i 's/interface=eth0/interface=eth1/' /opt/zeek/etc/node.cfg
      ip link set eth1 promisc on || true
      echo 'ip link set eth1 promisc on' >> /etc/rc.local
      chmod +x /etc/rc.local

      # community-id — DEBT-ARGUSPP-COMMUNITY-ID-001 + DEBT-ZEEK-COMMUNITY-ID-PROVISION-001
      # FIX DAY170: (1) ZeekControl carga site/local.zeek, NO etc/local.zeek (bug previo).
      #             (2) policy correcto = community-id-logging (no community-id-v1).
      #             (3) seed=0 explicito -> paridad con aRGus y Suricata (verificado: 1:IN7uq...).
      ZEEK_SITE="$(/opt/zeek/bin/zeek-config --site_dir 2>/dev/null || echo /opt/zeek/share/zeek/site)"
      SITE_LOCAL="${ZEEK_SITE}/local.zeek"
      mkdir -p "$ZEEK_SITE"
      touch "$SITE_LOCAL"
      # Guardas separadas por linea: el paquete Zeek puede traer el @load (comentado o no)
      # y una edicion manual previa pudo dejar el @load sin el seed. Idempotente por linea.
      if ! grep -qE '^[[:space:]]*@load policy/protocols/conn/community-id-logging' "$SITE_LOCAL"; then
        printf '\\n@load policy/protocols/conn/community-id-logging\\n' >> "$SITE_LOCAL"
      fi
      if ! grep -qE '^[[:space:]]*redef CommunityID::seed' "$SITE_LOCAL"; then
        printf 'redef CommunityID::seed = 0;\\n' >> "$SITE_LOCAL"
      fi

      mkdir -p /var/log/zeek
      ln -sf /opt/zeek/logs/current /var/log/zeek/current 2>/dev/null || true

      echo "=== Zeek ready ==="
      /opt/zeek/bin/zeek --version || true
      echo "community-id: $(grep -h community-id "$SITE_LOCAL" 2>/dev/null || echo NO-CONFIGURADO)"
      ip link show eth1 | grep -i promisc || echo "⚠️  eth1 promisc no activo aun"
    SHELL

    zeek.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN

  end  # End zeek VM

  # ════════════════════════════════════════════════════════════════════════════
  # WAZUH VM — host-based events / HIDS (ADR-048 F4)
  # ════════════════════════════════════════════════════════════════════════════
  config.vm.define "wazuh", autostart: false do |wazuh|
    wazuh.vm.box         = "debian/bookworm64"
    wazuh.vm.box_version = "12.20240905.1"
    wazuh.vm.hostname    = "argus-wazuh"

    wazuh.vm.provider "virtualbox" do |vb|
      vb.name   = "argus-wazuh"
      vb.memory = "4096"
      vb.cpus   = 2
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
      vb.customize ["modifyvm", :id, "--ioapic", "on"]
      vb.customize ["modifyvm", :id, "--audio", "none"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
    end

    wazuh.vm.network "private_network",
      ip: "192.168.100.12",
      virtualbox__intnet: "ml_defender_gateway_lan"

    wazuh.vm.synced_folder ".", "/vagrant", type: "virtualbox",
      mount_options: ["dmode=775,fmode=775,exec"]

    wazuh.vm.provision "shell", name: "install-wazuh", inline: <<-SHELL
      export DEBIAN_FRONTEND=noninteractive
      echo "=== Installing Wazuh manager (ADR-048 F4) ==="

      apt-get update -qq
      apt-get install -y curl gnupg2 chrony net-tools procps

      systemctl enable chrony
      systemctl start chrony
      chronyc makestep 1.0 3 2>/dev/null || true

      # DNS fix DESPUES de chrony
      echo "nameserver 8.8.8.8" > /etc/resolv.conf
      echo "nameserver 1.1.1.1" >> /etc/resolv.conf
      chattr +i /etc/resolv.conf

      curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
        | gpg --dearmor > /usr/share/keyrings/wazuh.gpg
      echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
        > /etc/apt/sources.list.d/wazuh.list
      apt-get update -qq
      apt-get install -y wazuh-manager || { echo "❌ wazuh-manager install failed"; exit 1; }

      systemctl daemon-reload
      systemctl enable wazuh-manager
      systemctl start wazuh-manager || true

      echo "=== Wazuh manager ready ==="
      /var/ossec/bin/wazuh-control status | head -5 || true
    SHELL

    wazuh.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN

  end  # End wazuh VM

end  # End Vagrant configuration