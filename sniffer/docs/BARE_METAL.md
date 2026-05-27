# Bare Metal Installation Guide

## C++20 Evolutionary Sniffer - Physical Hardware Deployment

Este documento describe la instalación y configuración del sniffer eBPF en hardware físico para máximo rendimiento.

## Requisitos de Hardware

### Mínimos (Testing/Development)
- **CPU**: Intel/AMD x64 con soporte de virtualización
- **RAM**: 4GB mínimo, 8GB recomendado
- **Disco**: 20GB espacio libre
- **Red**: Una interfaz Ethernet (1Gbps+)

### Recomendados (Production)
- **CPU**: Intel Xeon/AMD EPYC con múltiples cores
- **RAM**: 16GB+ (para ring buffers grandes)
- **Disco**: SSD NVMe para logs
- **Red**: Múltiples interfaces 10Gbps+ con soporte XDP nativo

### Hardware Certificado
```bash
# Verificar soporte XDP en interfaz
ethtool -i <interface> | grep driver
# Drivers con mejor soporte XDP:
# - i40e (Intel XL710)
# - ixgbe (Intel 82599)
# - mlx5_core (Mellanox ConnectX-5/6)
# - virtio_net (VM con soporte XDP)
```

## Requisitos de Sistema Operativo

### Distribuciones Soportadas
- **Ubuntu**: 22.04 LTS, 24.04 LTS
- **Debian**: 12 (Bookworm)
- **RHEL/CentOS**: 9+
- **Fedora**: 38+

### Kernel Requirements
```bash
# Versión mínima del kernel
uname -r
# Mínimo: 5.4+
# Recomendado: 6.1+
# Optimal: 6.8+ (latest eBPF features)

# Verificar opciones eBPF en kernel
grep CONFIG_BPF /boot/config-$(uname -r)
# Debe mostrar:
# CONFIG_BPF=y
# CONFIG_BPF_SYSCALL=y
# CONFIG_BPF_JIT=y
```

## Instalación de Dependencias

### Ubuntu/Debian
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Compilador y herramientas de desarrollo
sudo apt install -y \
    build-essential \
    cmake \
    pkg-config \
    git \
    wget \
    curl

# eBPF toolchain
sudo apt install -y \
    clang \
    llvm \
    libbpf-dev \
    bpftool \
    linux-tools-common \
    linux-tools-generic

# ZeroMQ y dependencias
sudo apt install -y \
    libzmq3-dev \
    libzmq5 \
    libprotobuf-dev \
    protobuf-compiler \
    libjsoncpp-dev

# Herramientas de red
sudo apt install -y \
    iproute2 \
    ethtool \
    tcpdump \
    netstat-nat
```

### RHEL/CentOS/Fedora
```bash
# Habilitar repositorios necesarios
sudo dnf install -y epel-release
sudo dnf config-manager --set-enabled crb  # Para CentOS Stream

# Compilador y herramientas
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y \
    cmake \
    pkg-config \
    git \
    wget \
    curl

# eBPF toolchain
sudo dnf install -y \
    clang \
    llvm \
    libbpf-devel \
    bpftool \
    kernel-devel \
    kernel-headers

# ZeroMQ y dependencias
sudo dnf install -y \
    zeromq-devel \
    protobuf-devel \
    protobuf-compiler \
    jsoncpp-devel

# Herramientas de red
sudo dnf install -y \
    iproute \
    ethtool \
    tcpdump \
    net-tools
```

## Verificación del Sistema

### Script de verificación automática
```bash
#!/bin/bash
# save as: check_sniffer_requirements.sh

echo "=== C++20 Evolutionary Sniffer Requirements Check ==="

# Kernel version
echo -n "Kernel version: "
uname -r
KERNEL_VERSION=$(uname -r | cut -d. -f1-2)
if [[ $(echo "$KERNEL_VERSION >= 5.4" | bc -l) -eq 1 ]]; then
    echo "✅ Kernel version OK"
else
    echo "❌ Kernel too old. Minimum: 5.4"
fi

# eBPF support
echo -n "eBPF JIT: "
if [[ $(sysctl net.core.bpf_jit_enable 2>/dev/null | cut -d= -f2 | tr -d ' ') == "1" ]]; then
    echo "✅ Enabled"
else
    echo "⚠️  Disabled - run: sudo sysctl net.core.bpf_jit_enable=1"
fi

# Required tools
TOOLS=("clang" "bpftool" "cmake" "protoc")
for tool in "${TOOLS[@]}"; do
    if command -v $tool >/dev/null 2>&1; then
        echo "✅ $tool: $(which $tool)"
    else
        echo "❌ $tool: Not found"
    fi
done

# Library checks
LIBS=("zmq" "protobuf" "jsoncpp")
for lib in "${LIBS[@]}"; do
    if pkg-config --exists $lib 2>/dev/null || pkg-config --exists lib$lib 2>/dev/null; then
        echo "✅ $lib: Available"
    else
        echo "❌ $lib: Not found"
    fi
done

# Network interfaces with XDP support
echo "Network interfaces:"
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v lo); do
    if ethtool -i $iface 2>/dev/null | grep -q "driver"; then
        driver=$(ethtool -i $iface | grep driver | cut -d: -f2 | tr -d ' ')
        echo "  ✅ $iface ($driver)"
    fi
done

echo "=== End Requirements Check ==="
```

## Configuración del Sistema

### Optimizaciones de kernel para eBPF
```bash
# /etc/sysctl.d/99-ebpf-sniffer.conf
net.core.bpf_jit_enable = 1
net.core.bpf_jit_harden = 0
net.core.bpf_jit_kallsyms = 1
net.core.netdev_max_backlog = 5000
net.core.netdev_budget = 600

# Ring buffer optimizations
kernel.perf_event_max_stack = 127
kernel.perf_event_max_contexts_per_stack = 8

# Apply changes
sudo sysctl -p /etc/sysctl.d/99-ebpf-sniffer.conf
```

### Configuración de memoria para eBPF
```bash
# Aumentar límites de memoria para maps eBPF
echo '* soft memlock unlimited' | sudo tee -a /etc/security/limits.conf
echo '* hard memlock unlimited' | sudo tee -a /etc/security/limits.conf

# Para systemd services
sudo mkdir -p /etc/systemd/system.conf.d/
echo '[Manager]' | sudo tee /etc/systemd/system.conf.d/memlock.conf
echo 'DefaultLimitMEMLOCK=infinity' | sudo tee -a /etc/systemd/system.conf.d/memlock.conf
```

## Compilación e Instalación

### Clonar y compilar
```bash
# Clonar repositorio
git clone <repository-url>
cd sniffer

# Crear directorio de build
mkdir build && cd build

# Configurar con CMake
cmake .. -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_CXX_STANDARD=20

# Compilar
make -j$(nproc)

# Verificar compilación exitosa
ls -la sniffer
```

### Instalación del binario
```bash
# Instalar binario del sistema
sudo cp sniffer /usr/local/bin/
sudo chmod +x /usr/local/bin/sniffer

# Instalar programa eBPF
sudo mkdir -p /usr/local/lib/sniffer/
sudo cp sniffer.bpf.o /usr/local/lib/sniffer/

# Crear directorio de configuración
sudo mkdir -p /etc/sniffer/
sudo cp ../config/sniffer.json /etc/sniffer/
```

## Configuración

### Archivo de configuración básico
```json
{
  "component": {
    "name": "evolutionary_sniffer",
    "version": "3.1.0"
  },
  "node_id": "bare_metal_001",
  "cluster_name": "production_cluster",
  "capture": {
    "interface": "eth0"
  },
  "network": {
    "output_socket": {
      "address": "127.0.0.1",
      "port": 5571,
      "socket_type": "PUSH"
    }
  },
  "features": {
    "extraction_enabled": true,
    "kernel_feature_count": 25,
    "user_feature_count": 58
  }
}
```

### Service systemd
```ini
# /etc/systemd/system/evolutionary-sniffer.service
[Unit]
Description=C++20 Evolutionary Sniffer
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/local/bin/sniffer --config=/etc/sniffer/sniffer.json
Restart=always
RestartSec=5
LimitMEMLOCK=infinity

# eBPF capabilities
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_NET_ADMIN CAP_DAC_OVERRIDE
AmbientCapabilities=CAP_SYS_ADMIN CAP_NET_ADMIN CAP_DAC_OVERRIDE

[Install]
WantedBy=multi-user.target
```

### Habilitar servicio
```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicio
sudo systemctl enable evolutionary-sniffer

# Iniciar servicio
sudo systemctl start evolutionary-sniffer

# Verificar estado
sudo systemctl status evolutionary-sniffer
```

## Verificación de Funcionamiento

### Tests básicos
```bash
# Verificar que el programa eBPF se carga
sudo bpftool prog show

# Verificar attachment XDP
sudo bpftool net show

# Ver estadísticas del sniffer
sudo systemctl status evolutionary-sniffer

# Ver logs en tiempo real
sudo journalctl -u evolutionary-sniffer -f
```

### Prueba de captura manual
```bash
# Ejecutar manualmente para testing
sudo /usr/local/bin/sniffer --config=/etc/sniffer/sniffer.json --verbose

# En otra terminal, generar tráfico de prueba
ping -c 10 8.8.8.8
```

## Performance Tuning

### CPU affinity
```bash
# Asignar sniffer a CPUs específicos
sudo systemctl edit evolutionary-sniffer

# Agregar:
[Service]
ExecStart=
ExecStart=taskset -c 0,1 /usr/local/bin/sniffer --config=/etc/sniffer/sniffer.json
```

### Optimizaciones de red
```bash
# Aumentar ring buffer de la interfaz
sudo ethtool -G eth0 rx 4096 tx 4096

# Deshabilitar offloading para mejor captura
sudo ethtool -K eth0 gro off lro off tso off gso off

# Configurar RSS para distribución de carga
sudo ethtool -X eth0 equal 4
```

## Troubleshooting

### Problemas comunes

#### Error: "Failed to load eBPF program"
```bash
# Verificar permisos
ls -la sniffer.bpf.o
sudo chmod 644 sniffer.bpf.o

# Verificar kernel headers
ls /lib/modules/$(uname -r)/build/
```

#### Error: "Permission denied" para XDP attach
```bash
# Verificar capabilities
sudo getcap /usr/local/bin/sniffer

# Si es necesario, agregar capabilities
sudo setcap 'cap_sys_admin,cap_net_admin+eip' /usr/local/bin/sniffer
```

#### Alto uso de CPU
```bash
# Verificar JIT compilation
sudo sysctl net.core.bpf_jit_enable
# Debe ser 1

# Optimizar ring buffer size en config
# Reducir timeout de polling
```

### Logs y debugging
```bash
# Logs del sistema
sudo dmesg | grep -i bpf
sudo journalctl -u evolutionary-sniffer --no-pager

# Debug eBPF
sudo bpftool prog tracelog

# Estadísticas de red
cat /proc/net/dev
ss -tuln | grep 5571
```

## Monitoreo de Producción

### Métricas clave
```bash
# Script de monitoreo básico
#!/bin/bash
# monitor_sniffer.sh

echo "=== Sniffer Health Check ==="
echo "Service Status: $(systemctl is-active evolutionary-sniffer)"
echo "eBPF Programs: $(sudo bpftool prog show type xdp | wc -l)"
echo "Memory Usage: $(ps aux | grep sniffer | awk '{print $4}')%"
echo "Network Stats:"
cat /proc/net/dev | grep eth0 | awk '{print "RX: " $2 " TX: " $10}'
```

### Alerting básico
```bash
# /etc/cron.d/sniffer-health
# Check every minute
* * * * * root /usr/local/bin/monitor_sniffer.sh | logger -t sniffer-monitor
```

## Actualizaciones

### Procedimiento de actualización
```bash
# Parar servicio
sudo systemctl stop evolutionary-sniffer

# Backup configuración
sudo cp /etc/sniffer/sniffer.json /etc/sniffer/sniffer.json.backup_20251119

# Compilar nueva versión
git pull
cd build && make clean && make -j$(nproc)

# Instalar nueva versión
sudo cp sniffer /usr/local/bin/
sudo cp sniffer.bpf.o /usr/local/lib/sniffer/

# Reiniciar servicio
sudo systemctl start evolutionary-sniffer
sudo systemctl status evolutionary-sniffer
```

## Desinstalación

```bash
# Parar y deshabilitar servicio
sudo systemctl stop evolutionary-sniffer
sudo systemctl disable evolutionary-sniffer

# Eliminar archivos
sudo rm -f /usr/local/bin/sniffer
sudo rm -rf /usr/local/lib/sniffer/
sudo rm -rf /etc/sniffer/
sudo rm -f /etc/systemd/system/evolutionary-sniffer.service

# Reload systemd
sudo systemctl daemon-reload
```