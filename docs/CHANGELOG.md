# Changelog

Todos los cambios notables del proyecto están documentados aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [Day 53 - HMAC Infrastructure] - 2026-02-10

### ✨ **Added - HMAC Log Integrity System (Phases 1-2)**

#### **🔐 FASE 1: etcd-server SecretsManager**
- **HMAC Key Generation**: SHA256-based keys (32 bytes random + salt)
- **Key Rotation**: Timestamp-based rotation con historical tracking
- **Key Management**:
  - `generate_hmac_key()`: Nueva key generation
  - `rotate_hmac_key()`: Safe rotation con backup
  - `get_hmac_key()`: Retrieval by timestamp
  - `list_hmac_keys()`: Audit trail
- **HTTP Endpoints**:
```
  GET  /secrets/keys              → List all HMAC keys
  GET  /secrets/{secret_name}     → Get specific secret
  POST /secrets/rotate/{component} → Rotate component key
```
- **Testing**: 12 unit tests + 4 integration tests (100% pass)

#### **🛡️ FASE 2: etcd-client HMAC Utilities**
- **5 Core Methods**:
```cpp
  get_hmac_key(component, timestamp)   → Key retrieval
  compute_hmac_sha256(data, key)       → HMAC generation
  validate_hmac_sha256(data, hmac, key)→ HMAC verification
  bytes_to_hex(bytes)                  → Hex encoding
  hex_to_bytes(hex)                    → Hex decoding
```
- **OpenSSL Integration**: HMAC_SHA256 implementation
- **Universal Availability**: All components (ml-detector, sniffer, rag-ingester) inherit HMAC via etcd-client
- **Testing**: 12 unit tests + 4 integration tests (100% pass)

### 🔧 **Technical Details**

#### **Architecture Pattern**
```
etcd-server (SecretsManager)
    ↓ HTTP API
etcd-client (HMAC utilities)
    ↓ Link-time inheritance
ml-detector, sniffer, rag-ingester (Ready for HMAC)
```

#### **Files Modified/Created** (16 total)
```
etcd-server/
├── include/etcd_server/secrets_manager.hpp        # New class
├── src/secrets_manager.cpp                        # New implementation
├── src/http_server.cpp                            # 3 new endpoints
├── tests/test_secrets_manager.cpp                 # 12 unit tests
├── tests/test_secrets_manager_integration.cpp     # 4 integration tests
└── CMakeLists.txt                                 # OpenSSL linking

etcd-client/
├── include/etcd_client/etcd_client.hpp            # 5 new methods
├── src/etcd_client.cpp                            # HMAC implementation
├── tests/test_etcd_client_hmac.cpp                # 12 unit tests
├── tests/test_etcd_client_hmac_integration.cpp    # 4 integration tests
└── CMakeLists.txt                                 # OpenSSL linking
```

### 🧪 **Testing Summary**

**Total Tests**: 32 (24 unit + 8 integration)  
**Pass Rate**: 100%

#### **SecretsManager Tests**
- [x] Key generation randomness
- [x] Key rotation without data loss
- [x] Key retrieval by timestamp
- [x] Historical key tracking
- [x] HTTP endpoint functionality
- [x] Concurrent access safety

#### **etcd-client HMAC Tests**
- [x] HMAC computation correctness
- [x] HMAC validation (valid/invalid cases)
- [x] Hex encoding/decoding roundtrip
- [x] Key retrieval from etcd-server
- [x] Error handling (missing keys, invalid hex)
- [x] Thread safety

### 📊 **Performance Characteristics**

- **Key Generation**: ~1ms (includes RAND_bytes + etcd store)
- **HMAC Computation**: ~0.05ms (SHA256 hash)
- **Key Retrieval**: ~2ms (HTTP GET from etcd-server)
- **Memory Overhead**: +64 bytes per HMAC tag (SHA256)

### 🗺️ **Next Steps (FASE 3)**

- [ ] rag-ingester EventLoader HMAC integration
- [ ] ml-detector log signing (optional P2)
- [ ] Audit trail visualization (P3)

---

## [v4.0.0-rag-llama-integration] - 2025-11-20

### 🎉 **MAJOR RELEASE: ML Defender Platform Complete**

**Estado:** Phase 1 Completa - Sistema RAG + 4 Detectores ML Operativos  
**Arquitectura:** KISS con WhiteListManager como router central

### ✨ **Added**

#### **🧠 RAG Security System con LLAMA Real**
- **TinyLlama-1.1B Integration**: Modelo real funcionando (`/vagrant/rag/models/tinyllama-1.1b-chat-v1.0.Q4_0.gguf`)
- **Arquitectura KISS**:
    - `WhiteListManager`: Router central + comunicación etcd
    - `RagCommandManager`: Lógica RAG + validación
    - `LlamaIntegration`: Integración real con llama.cpp
    - `ConfigManager`: Persistencia JSON automática
- **Sistema de Validación Robusta**:
    - `BaseValidator`: Clase base heredable para validación
    - `RagValidator`: Reglas específicas para comandos RAG
- **Comandos Interactivos Completos**:
  ```bash
  SECURITY_SYSTEM> rag show_config
  SECURITY_SYSTEM> rag ask_llm "¿Qué es un firewall en seguridad informática?"
  SECURITY_SYSTEM> rag update_setting port 9090
  SECURITY_SYSTEM> rag show_capabilities
  SECURITY_SYSTEM> exit
  ```

#### **⚡ 4 Detectores ML C++20 Embebidos (Sub-microsegundo)**
- **DDoS Detector**: 0.24μs latency (417x mejor que objetivo)
- **Ransomware Detector**: 1.06μs latency (94x mejor que objetivo)
- **Traffic Classifier**: 0.37μs latency (270x mejor que objetivo)
- **Internal Threat Detector**: 0.33μs latency (303x mejor que objetivo)

#### **🏗️ Arquitectura KISS Consolidada**
```
WhiteListManager (Router Central + Etcd)
    ├── cpp_sniffer (eBPF/XDP + 40 features)
    ├── ml-detector (4 modelos C++20 embebidos)
    └── RagCommandManager (RAG + LLAMA real)
         ├── RagValidator (Reglas específicas)
         ├── ConfigManager (JSON Persistencia) 
         └── LlamaIntegration (TinyLlama-1.1B REAL)
```

### 🔧 **Fixed**

#### **🐛 KV Cache Inconsistency Workaround**
- **Problema**: `inconsistent sequence positions (X=213, Y=0)`
- **Solución**: Limpieza manual del cache KV entre consultas
- **Implementación**:
  ```cpp
  void clear_kv_cache() {
      llama_batch batch = llama_batch_init(1, 0, 1);
      batch.n_tokens = 0;  // Batch vacío
      llama_decode(ctx, batch);  // Resetea estado interno
      llama_batch_free(batch);
  }
  ```

#### **🔄 Sistema de Configuración Robusto**
- **JSON Single Source of Truth**: Todos los thresholds desde `sniffer.json`
- **Validación Automática**: Range checking y fallbacks
- **Persistencia**: Configuración sobrevive reinicios

### 📊 **Performance Validated**

#### **Estabilidad del Sistema**
- ✅ **17h prueba de estabilidad**: Memoria estable (+1 MB growth)
- ✅ **35,387 eventos procesados**: Zero crashes
- ✅ **4 detectores ML**: Funcionando en producción
- ✅ **Sistema RAG**: Consultas reales operativas

#### **Rendimiento ML Detectores**
```
| Detector          | Latency | Throughput  | vs Target |
|-------------------|---------|-------------|-----------|
| DDoS              | 0.24μs  | ~4.1M/sec   | 417x mejor |
| Ransomware        | 1.06μs  | 944K/sec    | 94x mejor  |
| Traffic           | 0.37μs  | ~2.7M/sec   | 270x mejor |
| Internal          | 0.33μs  | ~3.0M/sec   | 303x mejor |
```

### 🧪 **Testing**

#### **Pruebas RAG System**
- [x] Múltiples consultas secuenciales
- [x] Consultas de seguridad complejas
- [x] Actualización configuración en caliente
- [x] Integración con comandos existentes

#### **Pruebas ML Detectors**
- [x] Rendimiento con tráfico real
- [x] Precisión en escenarios de ataque
- [x] Consumo recursos Raspberry Pi
- [x] Integración end-to-end con sniffer

### 📝 **Technical Details**

#### **Archivos Modificados/Creados**
```
rag/
├── src/
│   ├── main.cpp                          # Inicialización centralizada
│   ├── whitelist_manager.cpp            # Router + comunicación etcd
│   ├── rag_command_manager.cpp          # Lógica RAG + validación
│   ├── llama_integration_real.cpp       # Integración LLAMA real
│   ├── base_validator.cpp               # Validación centralizada
│   ├── rag_validator.cpp                # Reglas específicas RAG
│   └── config_manager.cpp               # Persistencia JSON
├── include/
│   └── rag/
│       ├── whitelist_manager.hpp
│       ├── rag_command_manager.hpp
│       ├── llama_integration.hpp
│       ├── base_validator.hpp
│       └── config_manager.hpp
└── config/
    └── system_config.json               # Configuración del sistema
```

#### **Dependencias Nuevas**
- **llama.cpp**: Integración con modelo TinyLlama-1.1B
- **etcd-cpp-apiv3**: Comunicación distribuida (preparada)
- **nlohmann_json**: Manejo de configuración JSON

### 🚀 **Usage**

```bash
# Iniciar sistema RAG Security
cd /vagrant/rag/build && ./rag-security

# Comandos de ejemplo
SECURITY_SYSTEM> rag ask_llm "¿Cómo funciona un firewall de aplicaciones?"
SECURITY_SYSTEM> rag ask_llm "Explica cómo detectar un ataque DDoS"
SECURITY_SYSTEM> rag show_config
SECURITY_SYSTEM> rag update_setting max_tokens 256
```

---

## [v3.2.1-hybrid-filters] - 2025-10-25

### ✨ Added

- **FD-based BPF Map Access**: Implementado acceso directo a BPF filter maps mediante File Descriptors
- **Hybrid Filtering System**: Sistema de filtrado completo kernel/userspace

### 🔧 Fixed

- **BPF Map Accessibility**: Solucionado error "No such file or directory (errno: 2)"
- **EbpfLoader Constructor**: Corregido orden de inicialización de miembros

---

## [v3.2.0] - 2025-10-20

### ✨ Added

- **Enhanced Configuration System**: Soporte completo para filtros híbridos en JSON
- **BPFMapManager Module**: Nueva clase para gestión centralizada de BPF maps

---

## [v3.1.0] - 2025-10-19

### 🔧 Fixed

- **Build System Overhaul**: Build reproducible 100% desde cero
- **Dependencies Resolution**: Todas las dependencias en una sola fase

---

## [v1.0.0-stable-pipeline] - 2025-10-15

### ✨ Initial Release

- **Sniffer eBPF v3.1**: XDP program con AF_XDP socket
- **ML Detector v1.0**: Level 1 inference (RandomForest)
- **Pipeline**: Protobuf schema v3.1.0, ZMQ communication

---

## 🐛 **Known Issues**

### **Active**

#### **P0 - KV Cache Inconsistency**
- **Estado**: Workaround implementado, solución definitiva pendiente
- **Impacto**: Consultas múltiples requieren limpieza manual del cache
- **Plan**: Investigar alternativas en Phase 2

#### **P1 - SMB Diversity Counter Retorna 0**
- **Estado**: Pendiente para Phase 2
- **Impacto**: Falso negativo en detección lateral movement

### **Resolved**

- ~~**BPF map pinning dependency**~~ → Fixed in v3.2.1
- ~~**Build failures desde cero**~~ → Fixed in v3.1.0
- ~~**Protobuf generation manual**~~ → Fixed in v3.1.0

---

## 🗺️ **Roadmap Actualizado**

### **Phase 1: ✅ COMPLETADO (20 Nov 2025)**
- ✅ 4 Detectores ML C++20 embebidos (sub-microsegundo)
- ✅ Sistema RAG con LLAMA real integrado
- ✅ Arquitectura KISS consolidada
- ✅ 17h prueba de estabilidad (+1MB memoria)

### **Phase 2: 🔄 EN PROGRESO (Nov-Dic 2025)**
- 🔄 Estabilización RAG System (KV Cache fix)
- 🔄 firewall-acl-agent development
- 🔄 Integración etcd coordinator
- 🔄 Resolución ISSUE-003: SMB diversity counter

### **Phase 3: 📋 PLANIFICADO (Ene-Feb 2026)**
- 📋 Base de datos vectorial RAG
- 📋 Dashboard Grafana/Prometheus
- 📋 Hardening de seguridad
- 📋 Preparación deployment Raspberry Pi

### **Phase 4: 🎯 FUTURO (Mar 2026+)**
- 🎯 Auto-tuning de parámetros ML
- 🎯 Model versioning y A/B testing
- 🎯 Distributed deployment
- 🎯 Physical device manufacturing

---

## 👥 **Contributors**

### **Equipo Central**
- **Alonso** (@alonsoir) - Líder de Investigación & Arquitecto
- **Claude** (Anthropic) - Arquitecto Principal & Investigador
- **DeepSeek** - Ingeniero de Sistemas & ML
- **Qwen** - Ingeniero de Sistemas & ML
- **GLM** - Ingeniero de Sistemas & ML
- **Parallel.ai** - Ingeniero de Sistemas & ML
- 
### **Colaboradores IA**
- **TinyLlama Project** - Modelo LLM de código abierto
- **llama.cpp** - Biblioteca de integración LLM

---

## 📄 **License**

MIT License - See [LICENSE](LICENSE) file for details

---

<div align="center">

**🏥 ML Defender - Protegiendo Infraestructuras Críticas con ML Embebido e IA**

*Última actualización: Noviembre 20, 2025*  
**¡Phase 1 Completa! Sistema RAG + 4 Detectores ML Operativos 🎉**

</div>