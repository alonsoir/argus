# Firewall Integration Guide - Day 23 (Decryption + Decompression)

## 🎯 Filosofía: "Despacio y Bien"

**Objetivo**: Integrar capacidades de descifrado y descompresión en firewall sin romper lo que funciona.

**Timeline**: Hoy (verificación) + Mañana (implementación) + Cuando sea (testing)

**Principio Via Appia**: "Predecible, robusto, y bien documentado."

---

## 📅 Plan de Trabajo (2 Días)

### **DÍA 1 (HOY)**: Verificación y Preparación (1-2 horas)

✅ **Fase 1.1**: Análisis del código actual (15 min)
- Ejecutar script de verificación
- Identificar qué tiene y qué falta
- Listar archivos a modificar

✅ **Fase 1.2**: Backup y preparación (10 min)
- Backup de firewall.json
- Backup de CMakeLists.txt
- Backup de src/*.cpp
- Crear rama git (opcional pero recomendado)

✅ **Fase 1.3**: Revisión de dependencias (15 min)
- Verificar etcd-client compilado
- Verificar LZ4 instalado en VM
- Verificar OpenSSL disponible
- Documentar versiones

✅ **Fase 1.4**: Plan detallado (30 min)
- Revisar esta guía completa
- Identificar secciones de código a modificar
- Preparar snippets de código
- Decidir orden de cambios

---

### **DÍA 2 (MAÑANA)**: Implementación Incremental (2-4 horas)

🔧 **Fase 2.1**: CMakeLists.txt (15 min)
- Añadir etcd-client library
- Añadir LZ4 library
- Añadir OpenSSL libraries
- Añadir include directories
- Test: cmake clean build

🔧 **Fase 2.2**: Headers y estructuras (15 min)
- Añadir #include statements
- Definir estructuras de config
- Añadir variables globales (si necesario)
- Test: Compile check (no link)

🔧 **Fase 2.3**: Inicialización (30 min)
- Leer config["transport"]
- Inicializar etcd-client
- Verificar configuración al startup
- Test: Startup sin errores

🔧 **Fase 2.4**: Funciones helper (45 min)
- Implementar decrypt_chacha20_poly1305()
- Implementar decompress_lz4()
- Añadir error handling
- Test: Unit tests si es posible

🔧 **Fase 2.5**: Integración en loop ZMQ (30 min)
- Modificar zmq_recv() flow
- Añadir decrypt → decompress → parse
- Añadir logging
- Test: Compile completo

🔧 **Fase 2.6**: Cleanup y refinamiento (30 min)
- Añadir etcd_client_cleanup()
- Mejorar error messages
- Añadir métricas
- Code review

---

### **DÍA 3+ (CUANDO SEA)**: Testing y Validación

🧪 **Fase 3.1**: Testing unitario (30 min)
- Firewall solo (sin pipeline)
- Con datos de prueba
- Verificar logs

🧪 **Fase 3.2**: Testing integrado (30 min)
- Pipeline completo
- Con etcd-server
- Verificar end-to-end

🧪 **Fase 3.3**: Stress test (cuando esté listo)
- make test-day23-stress
- Monitoring
- Análisis de resultados

---

## 🔧 FASE 2.1: CMakeLists.txt Modifications

### Backup Actual

```bash
cp /vagrant/firewall-acl-agent/CMakeLists.txt /vagrant/firewall-acl-agent/CMakeLists.txt.backup
```

### Cambios Necesarios

```cmake
cmake_minimum_required(VERSION 3.10)
project(../firewall-acl-agent)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================================================
# DEPENDENCIES
# ============================================================================

# Find required packages
find_package(../protobuf REQUIRED)
find_package(spdlog REQUIRED)
find_package(nlohmann_json 3.2.0 REQUIRED)

# ZMQ (system or custom)
find_library(ZMQ_LIB zmq REQUIRED)

# LZ4 (for decompression) - NEW
find_library(LZ4_LIB lz4 REQUIRED)

# OpenSSL (for ChaCha20-Poly1305) - NEW
find_package(OpenSSL REQUIRED)

# etcd-client (custom) - NEW
find_library(ETCD_CLIENT_LIB etcd_client
        PATHS ${CMAKE_SOURCE_DIR}/../etcd-client/build
        NO_DEFAULT_PATH
        REQUIRED
)

message(STATUS "Found etcd_client: ${ETCD_CLIENT_LIB}")
message(STATUS "Found LZ4: ${LZ4_LIB}")
message(STATUS "Found OpenSSL: ${OPENSSL_LIBRARIES}")

# ============================================================================
# INCLUDE DIRECTORIES
# ============================================================================

include_directories(
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/../proto
        ${CMAKE_SOURCE_DIR}/../etcd-client/include  # NEW
        ${PROTOBUF_INCLUDE_DIRS}
        ${OPENSSL_INCLUDE_DIR}                       # NEW
)

# ============================================================================
# SOURCE FILES
# ============================================================================

set(SOURCES
        src/main.cpp
        src/firewall_agent.cpp  # si existe
        # ... otros archivos ...
)

# Protobuf generated files
set(PROTO_SRCS
        ${CMAKE_SOURCE_DIR}/../proto/packet.pb.cc
)

# ============================================================================
# EXECUTABLE
# ============================================================================

add_executable(firewall-acl-agent
        ${SOURCES}
        ${PROTO_SRCS}
)

# ============================================================================
# LINKING
# ============================================================================

target_link_libraries(firewall-acl-agent
        ${PROTOBUF_LIBRARIES}
        ${ZMQ_LIB}
        spdlog::spdlog
        nlohmann_json::nlohmann_json
        ${ETCD_CLIENT_LIB}      # NEW
        ${LZ4_LIB}              # NEW
        ${OPENSSL_LIBRARIES}    # NEW (ssl + crypto)
        pthread
)

# ============================================================================
# COMPILE OPTIONS
# ============================================================================

target_compile_options(firewall-acl-agent PRIVATE
        -Wall
        -Wextra
        -O2
        -g
)

# For etcd-client to find shared library at runtime
set_target_properties(firewall-acl-agent PROPERTIES
        BUILD_RPATH "${CMAKE_SOURCE_DIR}/../etcd-client/build"
        INSTALL_RPATH "${CMAKE_SOURCE_DIR}/../etcd-client/build"
)
```

### Verificación Post-Modificación

```bash
vagrant ssh
cd /vagrant/firewall-acl-agent/build
rm -rf *
cmake ..

# Debe mostrar:
# -- Found etcd_client: /vagrant/etcd-client/build/libetcd_client.so
# -- Found LZ4: /usr/lib/x86_64-linux-gnu/liblz4.so
# -- Found OpenSSL: /usr/lib/x86_64-linux-gnu/libssl.so;/usr/lib/x86_64-linux-gnu/libcrypto.so
```

---

## 🔧 FASE 2.2: Headers y Estructuras

### main.cpp (o archivo principal) - Headers Section

```cpp
// Standard includes
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <csignal>
#include <thread>
#include <chrono>
#include <cstring>

// Third-party includes
#include <zmq.hpp>
#include <spdlog/spdlog.h>
#include <nlohmann/json.hpp>

// Protobuf
#include "packet.pb.h"

// NEW: Crypto/Compression includes
#include "etcd_client.h"
#include <lz4.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

using json = nlohmann::json;
```

### Estructuras de Configuración

```cpp
// Transport configuration structure
struct TransportConfig {
    bool compression_enabled = false;
    bool decompression_only = true;
    std::string compression_algorithm = "lz4";
    
    bool encryption_enabled = false;
    bool decryption_only = true;
    bool etcd_token_required = true;
    std::string encryption_algorithm = "chacha20-poly1305";
    std::string fallback_mode = "compressed_only";
};

// etcd configuration structure (extend existing if present)
struct EtcdConfig {
    bool enabled = false;
    std::vector<std::string> endpoints;
    int connection_timeout_ms = 5000;
    std::string crypto_token_path = "/crypto/firewall/tokens";
    std::string config_sync_path = "/config/firewall";
    int heartbeat_interval_seconds = 30;
    // ... existing fields ...
};

// Global variables (if needed)
static TransportConfig g_transport_config;
static EtcdConfig g_etcd_config;
static bool g_running = true;
```

---

## 🔧 FASE 2.3: Inicialización

### Load Configuration

```cpp
void load_transport_config(const json& config) {
    if (config.contains("transport")) {
        auto transport = config["transport"];
        
        if (transport.contains("compression")) {
            g_transport_config.compression_enabled = 
                transport["compression"].value("enabled", false);
            g_transport_config.decompression_only = 
                transport["compression"].value("decompression_only", true);
            g_transport_config.compression_algorithm = 
                transport["compression"].value("algorithm", "lz4");
        }
        
        if (transport.contains("encryption")) {
            g_transport_config.encryption_enabled = 
                transport["encryption"].value("enabled", false);
            g_transport_config.decryption_only = 
                transport["encryption"].value("decryption_only", true);
            g_transport_config.etcd_token_required = 
                transport["encryption"].value("etcd_token_required", true);
            g_transport_config.encryption_algorithm = 
                transport["encryption"].value("algorithm", "chacha20-poly1305");
        }
        
        spdlog::info("Transport config loaded:");
        spdlog::info("  Compression: {}", g_transport_config.compression_enabled);
        spdlog::info("  Encryption: {}", g_transport_config.encryption_enabled);
    }
}

void load_etcd_config(const json& config) {
    if (config.contains("etcd")) {
        auto etcd = config["etcd"];
        
        g_etcd_config.enabled = etcd.value("enabled", false);
        g_etcd_config.endpoints = etcd.value("endpoints", std::vector<std::string>{"localhost:2379"});
        g_etcd_config.connection_timeout_ms = etcd.value("connection_timeout_ms", 5000);
        g_etcd_config.crypto_token_path = etcd.value("crypto_token_path", "/crypto/firewall/tokens");
        // ... load other fields ...
        
        spdlog::info("etcd config loaded:");
        spdlog::info("  Enabled: {}", g_etcd_config.enabled);
        spdlog::info("  Endpoints: {}", g_etcd_config.endpoints[0]);
        spdlog::info("  Crypto token path: {}", g_etcd_config.crypto_token_path);
    }
}
```

### Initialize etcd-client

```cpp
void initialize_etcd_client() {
    if (!g_etcd_config.enabled) {
        spdlog::warn("etcd is disabled in config");
        return;
    }
    
    try {
        int result = etcd_client_init(
            g_etcd_config.config_sync_path.c_str(),
            "firewall-01",  // component_id
            g_etcd_config.endpoints[0].c_str()
        );
        
        if (result == 0) {
            spdlog::info("✅ etcd-client initialized successfully");
        } else {
            spdlog::error("❌ etcd-client initialization failed: {}", result);
            throw std::runtime_error("etcd-client init failed");
        }
    } catch (const std::exception& e) {
        spdlog::error("Exception initializing etcd-client: {}", e.what());
        throw;
    }
}
```

### Main Function Initialization

```cpp
int main(int argc, char* argv[]) {
    // Existing initialization...
    spdlog::set_level(spdlog::level::info);
    
    // Load config
    std::ifstream config_file("config/firewall.json");
    json config;
    config_file >> config;
    
    // Load transport config (NEW)
    load_transport_config(config);
    
    // Load etcd config (NEW)
    load_etcd_config(config);
    
    // Initialize etcd-client (NEW)
    if (g_etcd_config.enabled) {
        initialize_etcd_client();
    }
    
    // Continue with existing initialization...
    // ZMQ setup, IPSet setup, etc.
    
    // ... rest of main ...
}
```

---

## 🔧 FASE 2.4: Helper Functions

### Decryption Function

```cpp
std::vector<uint8_t> decrypt_chacha20_poly1305(
    const std::vector<uint8_t>& encrypted_data,
    const std::string& key_hex
) {
    spdlog::debug("Decrypting {} bytes with ChaCha20-Poly1305", encrypted_data.size());
    
    // Validate input
    if (encrypted_data.size() < 12 + 16) {  // nonce(12) + tag(16)
        spdlog::error("Encrypted data too small: {} bytes", encrypted_data.size());
        throw std::runtime_error("Invalid encrypted data size");
    }
    
    // Extract nonce (first 12 bytes)
    std::vector<uint8_t> nonce(encrypted_data.begin(), encrypted_data.begin() + 12);
    
    // Extract ciphertext + tag (rest)
    std::vector<uint8_t> ciphertext_and_tag(
        encrypted_data.begin() + 12,
        encrypted_data.end()
    );
    
    // Convert hex key to bytes
    std::vector<uint8_t> key;
    key.reserve(key_hex.length() / 2);
    for (size_t i = 0; i < key_hex.length(); i += 2) {
        std::string byte_str = key_hex.substr(i, 2);
        key.push_back(static_cast<uint8_t>(std::stoi(byte_str, nullptr, 16)));
    }
    
    // Prepare output buffer
    std::vector<uint8_t> plaintext(ciphertext_and_tag.size() - 16);  // -16 for tag
    
    // Create decryption context
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        throw std::runtime_error("Failed to create EVP context");
    }
    
    try {
        // Initialize decryption
        if (EVP_DecryptInit_ex(ctx, EVP_chacha20_poly1305(), nullptr, key.data(), nonce.data()) != 1) {
            throw std::runtime_error("EVP_DecryptInit_ex failed");
        }
        
        // Decrypt
        int len = 0;
        if (EVP_DecryptUpdate(ctx, plaintext.data(), &len, 
                              ciphertext_and_tag.data(), ciphertext_and_tag.size() - 16) != 1) {
            throw std::runtime_error("EVP_DecryptUpdate failed");
        }
        
        // Set expected tag
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_TAG, 16,
                                const_cast<uint8_t*>(ciphertext_and_tag.data() + ciphertext_and_tag.size() - 16)) != 1) {
            throw std::runtime_error("EVP_CIPHER_CTX_ctrl failed");
        }
        
        // Finalize (verifies tag)
        int final_len = 0;
        if (EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &final_len) != 1) {
            throw std::runtime_error("Decryption failed - authentication tag mismatch");
        }
        
        plaintext.resize(len + final_len);
        
        EVP_CIPHER_CTX_free(ctx);
        
        spdlog::debug("✅ Decrypted successfully: {} bytes", plaintext.size());
        return plaintext;
        
    } catch (...) {
        EVP_CIPHER_CTX_free(ctx);
        throw;
    }
}
```

### Decompression Function

```cpp
std::vector<uint8_t> decompress_lz4(const std::vector<uint8_t>& compressed_data) {
    spdlog::debug("Decompressing {} bytes with LZ4", compressed_data.size());
    
    // Validate input
    if (compressed_data.size() < 4) {
        spdlog::error("Compressed data too small: {} bytes", compressed_data.size());
        throw std::runtime_error("Invalid compressed data size");
    }
    
    // Extract decompressed size (first 4 bytes, little-endian)
    uint32_t decompressed_size;
    std::memcpy(&decompressed_size, compressed_data.data(), sizeof(uint32_t));
    
    spdlog::debug("Expected decompressed size: {} bytes", decompressed_size);
    
    // Validate decompressed size
    if (decompressed_size == 0 || decompressed_size > 10 * 1024 * 1024) {  // 10MB limit
        spdlog::error("Invalid decompressed size: {}", decompressed_size);
        throw std::runtime_error("Invalid decompressed size");
    }
    
    // Prepare output buffer
    std::vector<uint8_t> decompressed(decompressed_size);
    
    // Decompress (skip first 4 bytes which contain the size)
    int result = LZ4_decompress_safe(
        reinterpret_cast<const char*>(compressed_data.data() + 4),
        reinterpret_cast<char*>(decompressed.data()),
        compressed_data.size() - 4,
        decompressed_size
    );
    
    if (result < 0) {
        spdlog::error("LZ4 decompression failed: error code {}", result);
        throw std::runtime_error("LZ4 decompression failed");
    }
    
    if (static_cast<uint32_t>(result) != decompressed_size) {
        spdlog::warn("Decompressed size mismatch: expected {}, got {}", decompressed_size, result);
    }
    
    spdlog::debug("✅ Decompressed successfully: {} bytes", result);
    return decompressed;
}
```

### Get Crypto Token from etcd

```cpp
std::string get_crypto_token_from_etcd(const std::string& sender_component) {
    if (!g_etcd_config.enabled) {
        throw std::runtime_error("etcd is disabled, cannot get crypto token");
    }
    
    // Build token path: /crypto/firewall/tokens/ml-detector
    std::string token_path = g_etcd_config.crypto_token_path + "/" + sender_component;
    
    spdlog::debug("Retrieving crypto token from etcd: {}", token_path);
    
    try {
        char token_buffer[1024] = {0};
        int result = etcd_client_get_token(token_path.c_str(), token_buffer, sizeof(token_buffer));
        
        if (result != 0) {
            spdlog::error("Failed to get token from etcd: error {}", result);
            throw std::runtime_error("etcd_client_get_token failed");
        }
        
        std::string token(token_buffer);
        
        if (token.empty()) {
            spdlog::error("Retrieved empty token from etcd");
            throw std::runtime_error("Empty crypto token");
        }
        
        spdlog::debug("✅ Retrieved crypto token: {} chars", token.length());
        return token;
        
    } catch (const std::exception& e) {
        spdlog::error("Exception getting crypto token: {}", e.what());
        throw;
    }
}
```

---

## 🔧 FASE 2.5: Integración en Loop ZMQ

### Modified ZMQ Receive Loop

```cpp
void zmq_receive_loop(zmq::socket_t& socket) {
    spdlog::info("Starting ZMQ receive loop");
    spdlog::info("  Encryption: {}", g_transport_config.encryption_enabled ? "ON" : "OFF");
    spdlog::info("  Compression: {}", g_transport_config.compression_enabled ? "ON" : "OFF");
    
    // Cache crypto token (refresh periodically in production)
    std::string crypto_token;
    if (g_transport_config.encryption_enabled && g_transport_config.etcd_token_required) {
        try {
            crypto_token = get_crypto_token_from_etcd("ml-detector");
            spdlog::info("✅ Crypto token cached for decryption");
        } catch (const std::exception& e) {
            spdlog::error("Failed to get crypto token: {}", e.what());
            if (g_transport_config.fallback_mode != "compressed_only") {
                throw;
            }
            spdlog::warn("Continuing in compressed_only fallback mode");
            g_transport_config.encryption_enabled = false;
        }
    }
    
    while (g_running) {
        try {
            zmq::message_t message;
            
            // Receive message (with timeout)
            auto result = socket.recv(message, zmq::recv_flags::none);
            if (!result) {
                continue;  // Timeout or no message
            }
            
            spdlog::debug("Received ZMQ message: {} bytes", message.size());
            
            // Copy to vector for processing
            std::vector<uint8_t> data(
                static_cast<uint8_t*>(message.data()),
                static_cast<uint8_t*>(message.data()) + message.size()
            );
            
            // STEP 1: Decrypt if enabled
            if (g_transport_config.encryption_enabled) {
                try {
                    auto start = std::chrono::high_resolution_clock::now();
                    
                    data = decrypt_chacha20_poly1305(data, crypto_token);
                    
                    auto end = std::chrono::high_resolution_clock::now();
                    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
                    
                    spdlog::debug("✅ Decrypted: {} µs", duration.count());
                    
                } catch (const std::exception& e) {
                    spdlog::error("❌ Decryption failed: {}", e.what());
                    continue;  // Skip this message
                }
            }
            
            // STEP 2: Decompress if enabled
            if (g_transport_config.compression_enabled) {
                try {
                    auto start = std::chrono::high_resolution_clock::now();
                    
                    data = decompress_lz4(data);
                    
                    auto end = std::chrono::high_resolution_clock::now();
                    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
                    
                    spdlog::debug("✅ Decompressed: {} µs", duration.count());
                    
                } catch (const std::exception& e) {
                    spdlog::error("❌ Decompression failed: {}", e.what());
                    continue;  // Skip this message
                }
            }
            
            // STEP 3: Parse Protobuf (now data is plaintext)
            PacketEvent event;
            if (!event.ParseFromArray(data.data(), data.size())) {
                spdlog::error("❌ Failed to parse protobuf ({} bytes)", data.size());
                continue;
            }
            
            spdlog::debug("✅ Parsed PacketEvent: src={}, dst={}, threat_level={}",
                         event.src_ip(), event.dst_ip(), event.threat_level());
            
            // STEP 4: Process firewall action (existing code)
            process_firewall_action(event);
            
        } catch (const zmq::error_t& e) {
            if (e.num() == EINTR) {
                spdlog::info("ZMQ interrupted, shutting down");
                break;
            }
            spdlog::error("ZMQ error: {}", e.what());
        } catch (const std::exception& e) {
            spdlog::error("Unexpected error in receive loop: {}", e.what());
        }
    }
    
    spdlog::info("ZMQ receive loop exited");
}
```

---

## 🔧 FASE 2.6: Cleanup y Refinamiento

### Cleanup Function

```cpp
void cleanup() {
    spdlog::info("Cleaning up...");
    
    // Cleanup etcd-client
    if (g_etcd_config.enabled) {
        spdlog::info("Cleaning up etcd-client");
        etcd_client_cleanup();
    }
    
    // Existing cleanup code...
    // (ZMQ context, IPSet cleanup, etc.)
    
    spdlog::info("Cleanup complete");
}
```

### Signal Handler

```cpp
void signal_handler(int signal) {
    if (signal == SIGINT || signal == SIGTERM) {
        spdlog::info("Received signal {}, shutting down gracefully", signal);
        g_running = false;
    }
}

int main(int argc, char* argv[]) {
    // Install signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    // ... rest of main ...
    
    // Before exit
    cleanup();
    
    return 0;
}
```

---

## ✅ Checklist Completo de Implementación

### CMakeLists.txt
- [ ] find_library(ETCD_CLIENT_LIB ...)
- [ ] find_library(LZ4_LIB ...)
- [ ] find_package(OpenSSL REQUIRED)
- [ ] target_link_libraries(... etcd_client lz4 ssl crypto)
- [ ] target_include_directories(... etcd-client/include)
- [ ] set_target_properties(... BUILD_RPATH ...)

### Headers
- [ ] #include "etcd_client.h"
- [ ] #include <lz4.h>
- [ ] #include <openssl/evp.h>

### Config Loading
- [ ] load_transport_config()
- [ ] load_etcd_config()
- [ ] Log configuration at startup

### Initialization
- [ ] initialize_etcd_client()
- [ ] Error handling if etcd unavailable

### Helper Functions
- [ ] decrypt_chacha20_poly1305()
- [ ] decompress_lz4()
- [ ] get_crypto_token_from_etcd()
- [ ] Error handling in all functions

### ZMQ Loop
- [ ] Cache crypto token before loop
- [ ] Decrypt if encryption_enabled
- [ ] Decompress if compression_enabled
- [ ] Parse protobuf
- [ ] Process firewall action
- [ ] Timing metrics (optional)

### Cleanup
- [ ] etcd_client_cleanup()
- [ ] Existing cleanup code preserved

### Config File
- [ ] Backup original firewall.json
- [ ] Apply new integrated config
- [ ] Verify JSON syntax

---

## 🧪 Plan de Testing

### Test 1: Compilación
```bash
cd /vagrant/firewall-acl-agent/build
rm -rf *
cmake ..
make
# Debe compilar sin errores
```

### Test 2: Startup Sin Pipeline
```bash
./firewall-acl-agent
# Debe:
# - Inicializar etcd-client
# - Cargar config transport
# - No crashear
# Ctrl+C para salir
```

### Test 3: Con etcd-server Solo
```bash
# Terminal 1: etcd-server
make etcd-server-start

# Terminal 2: firewall
make run-firewall

# Debe:
# - Conectar a etcd
# - Registrar heartbeat
# - Esperar mensajes ZMQ
```

### Test 4: Pipeline Completo
```bash
make run-lab-dev-day23
make status-lab-day23

# Verificar logs:
tail -f /vagrant/logs/lab/firewall-agent.log

# Buscar:
# ✅ "Received ZMQ message"
# ✅ "Decrypted: X µs"
# ✅ "Decompressed: X µs"
# ✅ "Parsed PacketEvent"
```

---

## 🐛 Troubleshooting

### Error: "undefined reference to etcd_client_init"
```bash
# Verificar linkage
ldd /vagrant/firewall-acl-agent/build/firewall-acl-agent | grep etcd
# Debe mostrar: libetcd_client.so => /vagrant/etcd-client/build/...

# Si no aparece, revisar CMakeLists.txt
grep etcd_client /vagrant/firewall-acl-agent/CMakeLists.txt
```

### Error: "Failed to get token from etcd"
```bash
# Verificar etcd-server running
curl http://localhost:2379/version

# Verificar token existe
vagrant ssh -c "etcdctl get /crypto/firewall/tokens/ml-detector"
```

### Error: "Decryption failed - authentication tag mismatch"
```bash
# Verificar que ml-detector y firewall usan MISMO token
# Check ml-detector token:
vagrant ssh -c "etcdctl get /crypto/ml-detector/tokens/firewall"
# Check firewall token:
vagrant ssh -c "etcdctl get /crypto/firewall/tokens/ml-detector"
# Deben ser el mismo valor
```

### Error: "LZ4 decompression failed"
```bash
# Verificar datos están comprimidos
# Añadir log hex dump (debug):
spdlog::debug("First 16 bytes: {:02x}", fmt::join(data.begin(), data.begin()+16, " "));
```

---

## 📊 Métricas de Éxito

### Compilación
- ✅ cmake success
- ✅ make success
- ✅ No warnings críticos

### Startup
- ✅ Config cargado correctamente
- ✅ etcd-client inicializado
- ✅ Crypto token obtenido

### Runtime
- ✅ Mensajes ZMQ recibidos
- ✅ Descifrado exitoso (si enabled)
- ✅ Descompresión exitosa (si enabled)
- ✅ Protobuf parseado
- ✅ Reglas firewall aplicadas

### Performance
- ✅ Descifrado < 100 µs
- ✅ Descompresión < 50 µs
- ✅ Procesamiento total < 1 ms

---

## 🎯 Siguiente Sesión (Mañana)

**Objetivo**: Implementar FASE 2.1 a 2.6

**Preparación**:
1. Leer esta guía completamente
2. Tener editor abierto con firewall source
3. Tener terminal con VM conectada
4. Tener backup de archivos críticos

**Primera tarea**: CMakeLists.txt (15 minutos)

**Si hay problemas**: Parar, documentar, y continuar al día siguiente. Sin prisa. Via Appia Quality. 🏛️

---

¡Tranquilo, paso a paso, lo dejamos fino catalino! 😊