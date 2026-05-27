# 🔧 CONFIGURACIÓN DE RED - ML DEFENDER

## 🌐 **ESTADO ACTUAL DE INTERFACES**

### **Interfaces Configuradas y Operativas:**

```bash
# Verificar estado actual
ip -4 -br addr show

# Esperado:
# eth0: 10.0.2.15/24     (NAT - Internet)
# eth1: 192.168.56.20/24 (Host-only - Laboratorio)
# eth2: 192.168.1.134/24 (Bridged - LAN Real) 🎯
```

### **Verificación de Captura en eth2:**

```bash
# Test rápido de captura en eth2 (tráfico real)
sudo tcpdump -i eth2 -c 10 -n -v

# Verificar servicios ML Defender
sudo ss -tulpn | grep -E ':(5555|2379|2380|3000|5571)'
```

---

## 🚀 **CONFIGURACIÓN SNIFFER eBPF PARA ETH2**

### **1. Actualizar Configuración del Sniffer:**

```bash
# Editar configuración para usar eth2
sudo nano /ruta/a/ml-defender/sniffer/config/sniffer.json
```

**Configuración Actualizada:**
```json
{
  "interface": "eth2",
  "port": 5555,
  "promiscuous": true,
  "buffer_size_mb": 64,
  "max_packets_per_second": 100000,
  "feature_extraction": {
    "enabled": true,
    "num_features": 40,
    "normalization": "minmax"
  }
}
```

### **2. Script de Prueba Rápida para eth2:**

```bash
#!/bin/bash
# scripts/test_sniffer_eth2.sh

echo "🔧 Configurando Sniffer eBPF para eth2..."

# Parar servicios previos
sudo pkill -f sniffer
sudo pkill -f ml-detector

# Verificar que eth2 está activa
echo "📡 Verificando interfaz eth2..."
ip link show eth2
if [ $? -ne 0 ]; then
    echo "❌ eth2 no encontrada. Interfaces disponibles:"
    ip -br link show
    exit 1
fi

# Configurar eth2 en modo promiscuo
echo "🔍 Activando modo promiscuo en eth2..."
sudo ip link set eth2 promisc on

# Verificar tráfico en eth2
echo "📊 Capturando tráfico de prueba en eth2..."
sudo timeout 5s tcpdump -i eth2 -c 20 -n | tee /tmp/eth2_traffic.log

# Iniciar sniffer en eth2
echo "🚀 Iniciando sniffer eBPF en eth2..."
cd /ruta/a/ml-defender/sniffer
sudo ./build/cpp_sniffer --config config/sniffer.json --interface eth2 &

# Esperar inicialización
sleep 3

# Verificar que el sniffer está capturando
echo "🔎 Verificando captura del sniffer..."
sudo ss -tulpn | grep 5555

# Generar tráfico de prueba ZeroMQ
echo "🎯 Generando tráfico ZeroMQ de prueba..."
cd /ruta/a/ml-defender/ml-detector
python3 scripts/generate_test_traffic.py --interface eth2 --count 50

# Monitorear logs del sniffer
echo "📝 Monitoreando logs del sniffer..."
sudo tail -f /var/log/ml-defender/sniffer.log | head -20

echo "✅ Configuración eth2 completada"
```

### **3. Inicio Rápido de Servicios:**

```bash
#!/bin/bash
# scripts/start_services_eth2.sh

echo "🚀 Iniciando ML Defender en eth2..."

# 1. Iniciar etcd (si se usa)
echo "📦 Iniciando etcd..."
sudo systemctl start etcd || echo "⚠️  etcd no disponible, continuando..."

# 2. Iniciar ml-detector
echo "🤖 Iniciando ml-detector..."
cd /ruta/a/ml-defender/ml-detector
sudo ./build/ml_detector --config config/ml_detector.json &

# 3. Iniciar sniffer en eth2
echo "📡 Iniciando sniffer en eth2..."
cd /ruta/a/ml-defender/sniffer
sudo ./build/cpp_sniffer --interface eth2 --port 5555 --promiscuous &

# 4. Iniciar RAG system (opcional)
echo "🧠 Iniciando sistema RAG..."
cd /ruta/a/ml-defender/rag-system
sudo python3 rag_command_manager.py &

# Verificación
echo "🔍 Verificando servicios..."
sleep 3
sudo ss -tulpn | grep -E ':(5555|2379|2380)'

echo "✅ ML Defender operativo en eth2"
```

---

## 🎯 **GENERACIÓN DE TRÁFICO DE PRUEBA**

### **Script de Tráfico Realista:**

```python
#!/usr/bin/env python3
# scripts/generate_realistic_traffic.py

import time
import socket
import random
from threading import Thread

def generate_ddos_traffic(interface_ip="192.168.1.134", count=100):
    """Genera tráfico similar a DDoS para testing"""
    print(f"🎯 Generando {count} paquetes DDoS de prueba...")
    
    for i in range(count):
        try:
            # Simular diferentes tipos de tráfico
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Tráfico UDP flood
                sock.sendto(b"X" * random.randint(50, 1500), 
                           (interface_ip, random.randint(1000, 65000)))
                
            # Pequeña pausa aleatoria
            time.sleep(random.uniform(0.001, 0.1))
            
        except Exception as e:
            print(f"❌ Error en paquete {i}: {e}")
    
    print(f"✅ Generados {count} paquetes de prueba")

def generate_normal_traffic(interface_ip="192.168.1.134", count=50):
    """Genera tráfico normal para testing"""
    print(f"🎯 Generando {count} paquetes normales...")
    
    for i in range(count):
        try:
            # Tráfico HTTP normal
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.connect((interface_ip, 80))
                sock.send(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
                
            time.sleep(0.1)
            
        except:
            # Fallo esperado (puerto 80 probablemente cerrado)
            pass
    
    print(f"✅ Generados {count} paquetes normales")

if __name__ == "__main__":
    # Generar mezcla de tráfico
    Thread(target=generate_ddos_traffic, args=("192.168.1.134", 50)).start()
    Thread(target=generate_normal_traffic, args=("192.168.1.134", 30)).start()
```

---

## 🔍 **MONITOREO Y VERIFICACIÓN**

### **Script de Monitoreo en Tiempo Real:**

```bash
#!/bin/bash
# scripts/monitor_eth2.sh

echo "📊 Monitoreo ML Defender - eth2"
echo "================================"

while true; do
    clear
    echo "$(date) - ML Defender Status"
    echo "--------------------------------"
    
    # 1. Verificar interfaz
    echo "🔍 Interfaz eth2:"
    ip -4 -br addr show eth2
    
    # 2. Verificar servicios
    echo "🛠️ Servicios activos:"
    sudo ss -tulpn | grep -E ':(5555|2379|2380)' | sort
    
    # 3. Verificar procesos
    echo "🤖 Procesos ML Defender:"
    pgrep -af "sniffer\|ml_detector" || echo "❌ No hay procesos activos"
    
    # 4. Estadísticas de red
    echo "📈 Estadísticas eth2:"
    cat /sys/class/net/eth2/statistics/rx_packets | xargs echo "  Paquetes recibidos:"
    cat /sys/class/net/eth2/statistics/tx_packets | xargs echo "  Paquetes enviados:"
    
    # 5. Uso de recursos
    echo "💾 Uso de recursos:"
    ps aux --sort=-%cpu | head -5 | awk '{print $2, $3, $4, $11}'
    
    sleep 5
done
```

### **Verificación de Captura eBPF:**

```bash
#!/bin/bash
# scripts/verify_ebpf_capture.sh

echo "🔍 Verificando captura eBPF en eth2..."

# 1. Verificar que eBPF está cargado
echo "📦 Módulos eBPF cargados:"
sudo bpftool prog list | grep -i sniffer || echo "❌ No se encontraron programas eBPF"

# 2. Verificar mapas eBPF
echo "🗺️ Mapas eBPF:"
sudo bpftool map list | head -10

# 3. Verificar tráfico capturado
echo "📊 Tráfico en eth2:"
sudo ethtool -S eth2 | grep -E "packets|bytes" | head -5

# 4. Verificar colas XDP
echo "📨 Colas XDP:"
sudo ip link show dev eth2 | grep xdp

echo "✅ Verificación completada"
```

---

## 🛠️ **SOLUCIÓN DE PROBLEMAS COMUNES**

### **Problema: eth2 no detecta tráfico**
```bash
# Solución: Verificar configuración de red
sudo ip link set eth2 up
sudo ip addr show dev eth2
sudo ethtool eth2

# Verificar que está en modo promiscuo
sudo ip link set eth2 promisc on
```

### **Problema: Sniffer no inicia**
```bash
# Verificar permisos eBPF
sudo sysctl kernel.unprivileged_bpf_disabled
sudo sysctl -w kernel.unprivileged_bpf_disabled=0

# Verificar que el puerto 5555 está libre
sudo lsof -i :5555

# Reiniciar servicios
sudo pkill -f sniffer
sudo pkill -f ml_detector
./scripts/start_services_eth2.sh
```

### **Problema: No hay tráfico en eth2**
```bash
# Generar tráfico artificial
ping -I eth2 192.168.1.1 &
./scripts/generate_realistic_traffic.py

# Verificar con tcpdump
sudo tcpdump -i eth2 -c 10 -n -v
```

---

## 📋 **CHECKLIST DE IMPLEMENTACIÓN**

### **Pre-Implementación:**
- [ ] Verificar que eth2 tiene IP 192.168.1.134/24
- [ ] Confirmar que eth2 está `UP` y `RUNNING`
- [ ] Activar modo promiscuo: `sudo ip link set eth2 promisc on`
- [ ] Verificar tráfico con `tcpdump -i eth2 -c 5`

### **Implementación:**
- [ ] Actualizar `sniffer.json` con interfaz "eth2"
- [ ] Compilar sniffer: `cd sniffer && make clean && make`
- [ ] Ejecutar `scripts/test_sniffer_eth2.sh`
- [ ] Verificar captura con `scripts/monitor_eth2.sh`

### **Post-Implementación:**
- [ ] Generar tráfico de prueba
- [ ] Verificar logs del sniffer
- [ ] Confirmar procesamiento ML
- [ ] Validar alertas y detecciones

---

## 🎯 **PRÓXIMOS PASOS INMEDIATOS**

1. **Ejecutar configuración eth2:**
   ```bash
   chmod +x scripts/test_sniffer_eth2.sh
   ./scripts/test_sniffer_eth2.sh
   ```

2. **Monitorear resultados:**
   ```bash
   ./scripts/monitor_eth2.sh
   ```

3. **Validar captura real:**
    - Esperar tráfico de red natural
    - Generar tráfico artificial adicional
    - Verificar procesamiento ML

4. **Optimizar configuración:**
    - Ajustar parámetros eBPF según rendimiento
    - Fine-tune detecciones ML
    - Configurar alertas y logging

---

**¿Listo para proceder con la configuración de eth2?** 🚀

Ejecuta:
```bash
./scripts/test_sniffer_eth2.sh
```

Y luego monitorea con:
```bash
./scripts/monitor_eth2.sh
```