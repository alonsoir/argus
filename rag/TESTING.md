## 🧪 TESTING.md

```markdown
# 🧪 RAG Security System - Testing Guide

## 🎯 Estrategia de Testing

### Niveles de Testing
1. **Unit Tests**: Componentes individuales
2. **Integration Tests**: Interacción entre componentes  
3. **System Tests**: Flujo completo end-to-end
4. **Performance Tests**: Carga y rendimiento

## 🔧 Configuración de Testing

### Dependencias de Testing
```bash
# Instalar frameworks de testing
sudo apt install -y \
    libgtest-dev \
    libgmock-dev \
    lcov \
    gcovr

# Compilar GTest
cd /usr/src/gtest
sudo cmake .
sudo make
sudo cp lib/*.a /usr/lib
```

### Configuración CMake para Testing
```cmake
# En CMakeLists.txt principal
enable_testing()

# Buscar GTest
find_package(GTest REQUIRED)

# Configurar cobertura (opcional)
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --coverage")
endif()
```

## 🧪 Tests Unitarios

### Estructura de Tests
```
tests/
├── unit/               # Tests unitarios
│   ├── test_config_manager.cpp
│   ├── test_whitelist_manager.cpp
│   ├── test_security_context.cpp
│   └── test_llama_integration.cpp
├── integration/        # Tests de integración
│   ├── test_etcd_client.cpp
│   └── test_zmq_communication.cpp
└── fixtures/          # Datos de test
    ├── test_configs/
    └── test_models/
```

### Ejemplo: Test ConfigManager
```cpp
// tests/unit/test_config_manager.cpp
#include <gtest/gtest.h>
#include "rag/config_manager.hpp"

class ConfigManagerTest : public ::testing::Test {
protected:
    void SetUp() override {
        config_manager = std::make_unique<rag::ConfigManager>();
    }
    
    void TearDown() override {
        config_manager.reset();
    }
    
    std::unique_ptr<rag::ConfigManager> config_manager;
};

TEST_F(ConfigManagerTest, LoadValidConfig) {
    EXPECT_TRUE(config_manager->loadConfig("tests/fixtures/valid_config.json"));
}

TEST_F(ConfigManagerTest, LoadInvalidConfig) {
    EXPECT_FALSE(config_manager->loadConfig("tests/fixtures/invalid_config.json"));
}

TEST_F(ConfigManagerTest, GetStringValue) {
    config_manager->loadConfig("tests/fixtures/valid_config.json");
    EXPECT_EQ(config_manager->getString("etcd.endpoints[0]"), "http://localhost:2379");
}
```

### Ejemplo: Test WhitelistManager
```cpp
// tests/unit/test_whitelist_manager.cpp
#include <gtest/gtest.h>
#include "rag/whitelist_manager.hpp"

TEST(WhitelistManagerTest, CommandAllowed) {
    rag::WhitelistManager manager;
    manager.loadFromFile("tests/fixtures/whitelist.json");
    
    EXPECT_TRUE(manager.isCommandAllowed("GET"));
    EXPECT_FALSE(manager.isCommandAllowed("DROP")); // No permitido
}

TEST(WhitelistManagerTest, PatternMatching) {
    rag::WhitelistManager manager;
    manager.loadFromFile("tests/fixtures/whitelist.json");
    
    EXPECT_TRUE(manager.isKeyAllowed("config/database"));
    EXPECT_FALSE(manager.isKeyAllowed("root/password"));
}
```

## 🔄 Tests de Integración

### Test de Comunicación
```cpp
// tests/integration/test_zmq_communication.cpp
#include <gtest/gtest.h>
#include <thread>
#include "rag/security_context.hpp"

class CommunicationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Setup server and client
    }
    
    void TearDown() override {
        // Cleanup
    }
};

TEST_F(CommunicationTest, BasicMessageExchange) {
    rag::SecurityContext context;
    auto response = context.processSecurityRequest("GET /api/data");
    
    EXPECT_FALSE(response.empty());
    EXPECT_NE(response.find("Processed"), std::string::npos);
}
```

### Test de Integración LLM
```cpp
// tests/integration/test_llama_integration.cpp
#include <gtest/gtest.h>
#include "rag/llama_integration.hpp"

TEST(LlamaIntegrationTest, ModelInitialization) {
    rag::LlamaIntegration llama;
    
    // Usar modelo pequeño de test
    EXPECT_TRUE(llama.initialize("tests/fixtures/models/test_model.bin", 512));
}

TEST(LlamaIntegrationTest, QueryProcessing) {
    rag::LlamaIntegration llama;
    llama.initialize("tests/fixtures/models/test_model.bin", 512);
    
    auto response = llama.processQuery("What is security?");
    EXPECT_FALSE(response.empty());
}
```

## 🚀 Tests de Sistema

### Flujo Completo End-to-End
```cpp
// tests/system/test_full_workflow.cpp
#include <gtest/gtest.h>
#include "rag/security_context.hpp"

TEST(FullWorkflowTest, SecurityDecisionPipeline) {
    rag::SecurityContext security;
    security.initialize("config/rag_config.json");
    
    // Consulta permitida
    auto allowed_response = security.processSecurityRequest("GET /api/users");
    EXPECT_NE(allowed_response.find("allowed"), std::string::npos);
    
    // Consulta denegada
    auto denied_response = security.processSecurityRequest("DROP DATABASE");
    EXPECT_NE(denied_response.find("denied"), std::string::npos);
}
```

## 📊 Tests de Performance

### Benchmarking
```cpp
// tests/performance/benchmark_security.cpp
#include <benchmark/benchmark.h>
#include "rag/security_context.hpp"

static void BM_SecurityDecision(benchmark::State& state) {
    rag::SecurityContext security;
    security.initialize("config/rag_config.json");
    
    for (auto _ : state) {
        auto response = security.processSecurityRequest("GET /api/data");
        benchmark::DoNotOptimize(response);
    }
}
BENCHMARK(BM_SecurityDecision);

static void BM_WhitelistCheck(benchmark::State& state) {
    rag::WhitelistManager manager;
    manager.loadFromFile("config/command_whitelist.json");
    
    for (auto _ : state) {
        bool allowed = manager.isCommandAllowed("GET");
        benchmark::DoNotOptimize(allowed);
    }
}
BENCHMARK(BM_WhitelistCheck);
```

## 🧹 Tests de Seguridad

### Validación de Input
```cpp
// tests/security/test_input_validation.cpp
#include <gtest/gtest.h>
#include "rag/security_context.hpp"

TEST(SecurityTest, SQLInjectionAttempt) {
    rag::SecurityContext security;
    security.initialize("config/rag_config.json");
    
    auto response = security.processSecurityRequest("'; DROP TABLE users; --");
    // Debería ser denegado por la whitelist
    EXPECT_NE(response.find("denied"), std::string::npos);
}

TEST(SecurityTest, PathTraversalAttempt) {
    rag::SecurityContext security;
    security.initialize("config/rag_config.json");
    
    auto response = security.processSecurityRequest("GET ../../../etc/passwd");
    // Debería ser denegado por patrones
    EXPECT_NE(response.find("denied"), std::string::npos);
}
```

## 📈 Cobertura de Código

### Generar Reporte de Cobertura
```bash
# Compilar con flags de cobertura
cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j4

# Ejecutar tests con cobertura
make test
# o
ctest --output-on-failure

# Generar reporte
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_report
```

### Métricas de Cobertura Objetivo
- **Líneas**: > 80%
- **Funciones**: > 85%
- **Ramas**: > 75%
- **Componentes Críticos**: > 90%

## 🐛 Debugging de Tests

### Configuración de Debug
```cpp
// tests/debug/test_debug_helpers.cpp
#include <gtest/gtest.h>

// Helper para debug
#define DEBUG_TEST() \
    std::cout << "Test: " << ::testing::UnitTest::GetInstance()->current_test_info()->name() << std::endl;

TEST(DebugTest, WithDebugOutput) {
    DEBUG_TEST();
    std::cout << "Debug information..." << std::endl;
    EXPECT_TRUE(true);
}
```

### Logging de Tests
```bash
# Ejecutar tests con output verbose
./test_whitelist_manager --gtest_verbose=1

# Ejecutar tests específicos
./test_config_manager --gtest_filter="ConfigManagerTest.LoadValidConfig"

# Generar reporte XML para CI
./test_runner --gtest_output=xml:test_results.xml
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
# .github/workflows/test.yml
name: RAG Security Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libgtest-dev libzmq3-dev protobuf-compiler
      - name: Build and test
        run: |
          mkdir build && cd build
          cmake .. -DBUILD_TESTING=ON
          make -j4
          ctest --output-on-failure
```

## 📋 Checklist de Testing

### Pre-commit
- [ ] Todos los tests unitarios pasan
- [ ] No hay regresiones de performance
- [ ] Cobertura de código mantenida
- [ ] Tests de seguridad ejecutados

### Pre-release
- [ ] Tests de integración completos
- [ ] Tests de sistema end-to-end
- [ ] Tests de carga y stress
- [ ] Reporte de cobertura generado

---

*Última actualización: $(date)*  
*Framework: Google Test*  
*Cobertura objetivo: 80%+*
```

## 🎯 Resumen de Documentación Creada

1. **README.md**: Documentación completa del proyecto para desarrolladores
2. **STATUS.md**: Estado actual del desarrollo y próximos pasos  
3. **TESTING.md**: Guía completa de testing y calidad

¡Listo para continuar mañana! ¿Necesitas que ajuste algo en la documentación antes de guardar?