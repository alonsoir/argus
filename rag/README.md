# 📝 Generando Documentación para el Componente RAG

## 📋 README.md

```markdown
# 🛡️ RAG Security System

Sistema de seguridad basado en RAG (Retrieval-Augmented Generation) que implementa control de acceso mediante lista blanca y integración con modelos de lenguaje.

## 🎯 Arquitectura

```
RAG Security System
├── 🤖 LLM Integration (llama.cpp)
├── 📋 Whitelist Parser & Manager
├── 🔄 etcd Client (Distributed Config)
├── ⚙️ Config Manager (JSON-based)
├── 🔐 Security Context
└── 🎯 Command Validator
```

## 🚀 Características

- **Lista Blanca de Comandos**: Control granular de operaciones permitidas
- **Integración LLM**: Procesamiento de consultas naturales usando llama.cpp
- **Configuración Centralizada**: Gestión via JSON con validación
- **Distributed Coordination**: Comunicación con etcd para estado compartido
- **Auditoría**: Logging completo de decisiones de seguridad

## 📦 Dependencias

### Core
- **C++20**: Estándar moderno de C++
- **ZeroMQ**: Comunicación entre componentes
- **Protobuf**: Serialización de mensajes
- **nlohmann/json**: Procesamiento de JSON

### IA/ML
- **llama.cpp**: Inferencia de modelos de lenguaje
- **Modelos GGML**: Modelos cuantizados optimizados

### Distributed Systems
- **etcd-cpp-api**: Cliente para etcd (distributed key-value store)

## 🏗️ Estructura del Proyecto

```
rag/
├── include/rag/           # Headers públicos
│   ├── security_context.hpp
│   ├── config_manager.hpp
│   ├── whitelist_manager.hpp
│   ├── llama_integration.hpp
│   └── etcd_client.hpp
├── src/                   # Implementaciones
├── config/               # Configuración
│   ├── rag_config.json
│   └── command_whitelist.json
├── tests/               # Tests unitarios
└── build/              # Build artifacts
```

## ⚙️ Configuración

### Configuración Principal (`config/rag_config.json`)

```json
{
  "etcd": {
    "endpoints": ["http://localhost:2379"],
    "timeout": 5000,
    "retry_attempts": 3
  },
  "llama": {
    "model_path": "models/llama/ggml-model-q4_0.bin",
    "context_size": 2048,
    "temperature": 0.7
  },
  "security": {
    "whitelist_file": "config/command_whitelist.json",
    "max_query_length": 1000,
    "enable_audit_log": true
  }
}
```

### Lista Blanca (`config/command_whitelist.json`)

```json
{
  "allowed_commands": [
    "GET", "SET", "DELETE", "WATCH", "PUT", "LIST", "STATUS"
  ],
  "allowed_patterns": [
    "^[a-zA-Z0-9_./-]+$",
    "^config/", "^security/", "^ml-detector/"
  ],
  "restricted_keys": [
    "root", "admin", "password", "secret"
  ]
}
```

## 🔧 Compilación

### Prerrequisitos

```bash
# En Debian/Ubuntu
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    pkg-config \
    libzmq3-dev \
    protobuf-compiler \
    libprotobuf-dev \
    nlohmann-json3-dev
```

### Compilar

```bash
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### Ejecutar

```bash
./rag-security
```

## 🔄 Integración con el Ecosistema

### Comunicación via ZeroMQ
- **Puerto**: 5555 (configurable)
- **Protocolo**: Protobuf serialization
- **Mensajes**: `network_security.proto`

### Coordinación via etcd
- **Keyspace**: `/rag/security/`
- **Watch**: Cambios en configuración en tiempo real
- **Service Discovery**: Registro automático de instancias

## 🧪 Testing

```bash
# Ejecutar tests unitarios
cd build
ctest --verbose

# O compilar y ejecutar tests específicos
make test_whitelist_manager
./test_whitelist_manager
```

## 📊 Monitoreo

### Métricas
- Tasa de consultas procesadas
- Tiempos de respuesta del LLM
- Decisiones de seguridad (allow/deny)
- Uso de recursos

### Logs
- Auditoría de decisiones
- Errores del sistema
- Cambios de configuración

## 🤝 Contribución

1. Fork el proyecto
2. Crea una feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Distribuido bajo la Licencia MIT. Ver `LICENSE` para más información.

## 🆘 Soporte

- 📧 Email: equipo@proyecto.com
- 💬 Slack: #rag-security
- 🐛 Issues: GitHub Issues
```

