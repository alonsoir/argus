# ML Detector Tricapa - C++20

Sistema de detección de amenazas en tiempo real basado en Machine Learning con arquitectura tricapa.

## 🎯 Características

- **Arquitectura Tricapa**:
    - 🥇 Nivel 1: Detección general de ataques (RF, 23 features)
    - 🥈 Nivel 2: Clasificación especializada (DDOS/Ransomware, 82 features)
    - 🥉 Nivel 3: Detección de anomalías (Internal/Web, 4 features)

- **Performance Objetivo**:
    - Latencia < 5ms por clasificación
    - IPC con Unix sockets (< 0.5ms overhead)
    - Zero-copy donde sea posible
    - Throughput: 10-50k eventos/seg por quinteto

- **Tecnologías**:
    - C++20 (gcc 10+, clang 11+)
    - ONNX Runtime para inferencia ML
    - ZeroMQ para IPC (patrón PULL/PUB)
    - Protobuf para serialización (compartido desde raíz)
    - nlohmann/json para configuración
    - spdlog para logging estructurado

## 🏗️ Arquitectura

### Quinteto Distribuido

El ml-detector es parte de un quinteto especializado co-localizado:
sniffer-ebpf ──→ ml-detector ──→ geoip-enricher ──→ scheduler ──→ firewall-agent
(eth2)          (tricapa)         (coords)         (decisión)     (ACL batch)
[XDP/eBPF]      [ONNX RT]        [MaxMind]        [Redis]        [nftables]

### Flujo de Decisión Tricapa

Evento Protobuf (83 features)
↓
🥇 Nivel 1: ¿Ataque? (23 features, RF)
├─→ NO  → 🥉 Nivel 3: Anomalía? (4 features)
│         ├─→ NO  → LOG + FIN ✅
│         └─→ SÍ  → ANOMALY → Scheduler
│
└─→ SÍ  → 🥈 Nivel 2: ¿Tipo? (82 features, RF)
├─→ DDOS       → Scheduler
├─→ RANSOMWARE → Scheduler
└─→ UNKNOWN    → Scheduler

## 📁 Estructura

ml-detector/
├── src/                    # Implementación C++20
├── include/                # Headers
├── models/                 # Modelos ML (ONNX)
│   ├── production/
│   ├── metadata/
│   └── scripts/
├── config/                 # Configuración JSON
├── tests/                  # Tests
├── docker/                 # Contenedorización
└── docs/                   # Documentación

**Nota**: El directorio `protobuf/` está en la raíz del proyecto (compartido).

## 🚀 Build

La idea será crear un paquete debian como hicimos para el sniffer.
### Requisitos Compilación
```bash
    sudo apt-get install -y build-essential cmake pkg-config \
        libzmq3-dev libprotobuf-dev protobuf-compiler \
        liblz4-dev nlohmann-json3-dev libspdlog-dev
    
    mkdir build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc)
```

### 📊 Uso
```bash
  ./ml-detector --config ../config/ml_detector_config.json
```

### 🔧 Configuración
Ver config/ml_detector.json para opciones completas.

📖 Documentación

Arquitectura
Conversión de Modelos
Deployment

### 🧪 Laboratorio

Host: OSX
VM: Vagrant corriendo Debian 11 + Kernel 6.1.x, ejecutando docker-compose.
RAM: 4-8GB
CPU: 2-4 cores

### 🤝 Contribución
Proyecto de investigación para paper en arXiv.
Coautores: Alonso Isidoro Román, Claude (Anthropic), ChatGPT (OpenAI), Grok (xAI), Parallels.ai
📝 Licencia
MIT License type

### 🚀 Roadmap

Estructura inicial del proyecto
Conversión de modelos joblib → ONNX
Implementación del clasificador tricapa
Tests completos
Benchmarks
Paper en arXiv

Status: 🚧 En desarrollo activo