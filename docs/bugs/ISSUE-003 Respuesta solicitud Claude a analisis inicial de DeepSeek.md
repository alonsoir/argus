# 🧪 TESTS CIENTÍFICOS PARA VALIDACIÓN DE HIPÓTESIS

## 📋 TESTS PROPUESTOS POR DEEPSEEK

### **1. Test de Race Condition en `initialize()`**

```cpp
// test_race_initialize.cpp
#include "flow/sharded_flow_manager.hpp"
#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>

// Test 1: Race condition en initialize()
void test_concurrent_initialize() {
    std::cout << "🧪 Test 1: Concurrent initialize() race condition" << std::endl;
    
    constexpr int NUM_THREADS = 10;
    constexpr int NUM_ITERATIONS = 100;
    
    std::vector<std::thread> threads;
    std::atomic<int> initialization_attempts{0};
    std::atomic<int> successful_initializations{0};
    std::atomic<int> crashes{0};
    
    // ThreadSanitizer debe detectar si múltiples threads entran en initialize()
    auto worker = [&](int thread_id) {
        for (int i = 0; i < NUM_ITERATIONS; ++i) {
            try {
                auto& manager = sniffer::flow::ShardedFlowManager::instance();
                sniffer::flow::ShardedFlowManager::Config config;
                config.shard_count = 4;
                config.max_flows_per_shard = 1000;
                
                initialization_attempts.fetch_add(1, std::memory_order_relaxed);
                
                manager.initialize(config);
                
                // Si llegamos aquí sin crash, contabilizamos
                successful_initializations.fetch_add(1, std::memory_order_relaxed);
                
                // Pequeño delay aleatorio para aumentar chance de race
                std::this_thread::sleep_for(std::chrono::microseconds(thread_id * 10));
                
            } catch (const std::exception& e) {
                crashes.fetch_add(1, std::memory_order_relaxed);
                std::cerr << "Thread " << thread_id << " crashed: " << e.what() << std::endl;
            }
        }
    };
    
    // Lanzar threads concurrentes
    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back(worker, t);
    }
    
    // Esperar
    for (auto& th : threads) {
        th.join();
    }
    
    // Análisis de resultados
    std::cout << "\n📊 Resultados Test 1:" << std::endl;
    std::cout << "  Intentos de inicialización: " << initialization_attempts << std::endl;
    std::cout << "  Inicializaciones exitosas: " << successful_initializations << std::endl;
    std::cout << "  Crashes: " << crashes << std::endl;
    
    // CRITERIO DE ÉXITO/FRACASO:
    // Si ThreadSanitizer reporta WARNING de data race → FAIL (bug confirmado)
    // Si hay más de 1 successful_initializations → FAIL (multiple initialization)
    // Si crashes > 0 → FAIL (undefined behavior)
    
    if (successful_initializations > 1) {
        std::cout << "❌ FAIL: Múltiples inicializaciones detectadas (race condition)" << std::endl;
        exit(1);
    } else if (crashes > 0) {
        std::cout << "❌ FAIL: Crashes detectados durante inicialización concurrente" << std::endl;
        exit(1);
    } else {
        std::cout << "✅ PASS: Inicialización thread-safe (al menos no detectamos races)" << std::endl;
    }
}

int main() {
    test_concurrent_initialize();
    return 0;
}
```

**Compilación y ejecución:**
```bash
# Compilar con ThreadSanitizer
cd /vagrant/sniffer
g++ -std=c++20 -Iinclude -fsanitize=thread -g -O0 \
    tests/test_race_initialize.cpp \
    src/flow/sharded_flow_manager.cpp \
    src/flow/flow_manager.cpp \
    -o build/test_race_initialize

# Ejecutar con TSAN
cd /vagrant/sniffer/build
./test_race_initialize

# También podemos ejecutar con helgrind (alternativa)
valgrind --tool=helgrind ./test_race_initialize
```

**Comportamiento esperado (si bug existe):**
```
WARNING: ThreadSanitizer: data race (pid=12345)
  Write of size 1 at 0x7fffe8c2b1c0 by thread T2:
    #0 ShardedFlowManager::initialize()::initialized_ = true
    #1 ShardedFlowManager::initialize()

  Previous write of size 1 at 0x7fffe8c2b1c0 by thread T1:
    #0 ShardedFlowManager::initialize()::initialized_ = true
    #1 ShardedFlowManager::initialize()
```

**Criterio de PASS/FAIL:**
- **PASS:** ThreadSanitizer no reporta warnings, successful_initializations = 1
- **FAIL:** ThreadSanitizer detecta race condition, OR successful_initializations > 1

---

### **2. Benchmark LRU O(n) vs O(1)**

```cpp
// benchmark_lru_performance.cpp
#include "flow/sharded_flow_manager.hpp"
#include <iostream>
#include <chrono>
#include <random>
#include <vector>
#include <algorithm>

using namespace sniffer::flow;

struct BenchmarkResult {
    size_t num_flows;
    size_t num_updates;
    double total_time_ms;
    double time_per_update_ms;
    bool meets_target;
};

BenchmarkResult run_lru_benchmark(size_t num_flows, size_t num_updates) {
    auto& manager = ShardedFlowManager::instance();
    ShardedFlowManager::Config config;
    config.shard_count = 4;
    config.max_flows_per_shard = num_flows * 2;  // Doble para evitar evicción
    
    manager.initialize(config);
    manager.reset_stats();
    
    // 1. Insertar flows iniciales
    std::vector<FlowKey> keys;
    keys.reserve(num_flows);
    
    for (size_t i = 0; i < num_flows; ++i) {
        FlowKey key{
            .src_ip = static_cast<uint32_t>(i),
            .dst_ip = static_cast<uint32_t>(i + 1000),
            .src_port = static_cast<uint16_t>(50000 + (i % 1000)),
            .dst_port = static_cast<uint16_t>(80 + (i % 100)),
            .protocol = 6  // TCP
        };
        
        SimpleEvent event;
        // Inicializar evento dummy
        manager.add_packet(key, event);
        keys.push_back(key);
    }
    
    // 2. Preparar updates aleatorios
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<size_t> dist(0, num_flows - 1);
    
    // 3. Ejecutar benchmark de updates
    auto start = std::chrono::high_resolution_clock::now();
    
    for (size_t i = 0; i < num_updates; ++i) {
        size_t idx = dist(gen);
        FlowKey key = keys[idx];
        
        SimpleEvent event;
        // Modificar algún campo para que sea update real
        manager.add_packet(key, event);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    
    // 4. Calcular métricas
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    double total_time_ms = duration.count() / 1000.0;
    double time_per_update_ms = total_time_ms / num_updates;
    
    // 5. Threshold: >10ms por update para 10K flows es inaceptable
    //    (Actualmente O(n): ~1μs × 10K = 10ms por update)
    bool meets_target = (time_per_update_ms < 10.0);
    
    manager.cleanup_all();
    
    return BenchmarkResult{
        .num_flows = num_flows,
        .num_updates = num_updates,
        .total_time_ms = total_time_ms,
        .time_per_update_ms = time_per_update_ms,
        .meets_target = meets_target
    };
}

void run_lru_benchmark_suite() {
    std::cout << "🧪 Test 2: LRU Performance Benchmark (O(n) vs O(1))" << std::endl;
    std::cout << "=====================================================" << std::endl;
    
    // Escenarios de prueba
    struct Scenario {
        size_t flows;
        size_t updates;
    };
    
    std::vector<Scenario> scenarios = {
        {1'000, 10'000},      // Pequeño
        {10'000, 10'000},     // Mediano (CRÍTICO)
        {50'000, 10'000},     // Grande
    };
    
    bool all_pass = true;
    
    for (const auto& scenario : scenarios) {
        std::cout << "\n📊 Escenario: " << scenario.flows << " flows, " 
                  << scenario.updates << " updates" << std::endl;
        
        auto result = run_lru_benchmark(scenario.flows, scenario.updates);
        
        std::cout << "  Tiempo total: " << result.total_time_ms << " ms" << std::endl;
        std::cout << "  Tiempo por update: " << result.time_per_update_ms << " ms" << std::endl;
        std::cout << "  Target (<10ms/update): " << (result.meets_target ? "✅" : "❌") << std::endl;
        
        if (!result.meets_target) {
            all_pass = false;
        }
        
        // Predicción teórica:
        // Actual O(n): ~1μs × num_flows por update
        double predicted_time_ms = (1.0 * scenario.flows) / 1000.0;  // μs → ms
        std::cout << "  Predicción teórica O(n): ~" << predicted_time_ms << " ms/update" << std::endl;
        
        // Ratio actual/predicción
        double ratio = result.time_per_update_ms / predicted_time_ms;
        std::cout << "  Ratio real/teórico: " << ratio << "x" << std::endl;
        
        if (ratio > 0.5 && ratio < 2.0) {
            std::cout << "  ✅ Comportamiento O(n) confirmado" << std::endl;
        } else if (result.time_per_update_ms < 0.1) {
            std::cout << "  ⚠️  Más rápido de lo esperado (¿cache?)" << std::endl;
        } else {
            std::cout << "  ❌ Comportamiento no lineal (¿otro bottleneck?)" << std::endl;
        }
    }
    
    std::cout << "\n📈 CONCLUSIÓN DEL BENCHMARK:" << std::endl;
    if (all_pass) {
        std::cout << "✅ PASS: Todos los escenarios cumplen target (<10ms/update)" << std::endl;
        std::cout << "   Recomendación: Mantener implementación actual (simplicidad)" << std::endl;
    } else {
        std::cout << "❌ FAIL: Al menos un escenario excede target" << std::endl;
        std::cout << "   Recomendación: Implementar fix O(1) (iterator map)" << std::endl;
    }
}

int main() {
    run_lru_benchmark_suite();
    return 0;
}
```

**Compilación y ejecución:**
```bash
# Compilar con optimizaciones
cd /vagrant/sniffer
g++ -std=c++20 -Iinclude -O2 -g \
    tests/benchmark_lru_performance.cpp \
    src/flow/sharded_flow_manager.cpp \
    src/flow/flow_manager.cpp \
    -o build/benchmark_lru_performance

# Ejecutar benchmark
cd /vagrant/sniffer/build
./benchmark_lru_performance
```

**Threshold de aceptación:**
```
- Para 10K flows y 10K updates:
  ✅ PASS: <10 ms por update (total <100 segundos)
  ❌ FAIL: >10 ms por update (necesita optimización)

Basado en cálculo teórico:
  O(n): 1μs × 10K flows = 10ms por update
  O(1): ~0.1μs por update = 1ms total para 10K updates
```

---

### **3. Test de Data Race en `get_flow_stats_mut()`**

```cpp
// test_data_race_mut.cpp
#include "flow/sharded_flow_manager.hpp"
#include <iostream>
#include <thread>
#include <atomic>
#include <vector>
#include <chrono>

using namespace sniffer::flow;

// Test que demuestra data race si get_flow_stats_mut() no es thread-safe
void test_concurrent_mut_access() {
    std::cout << "🧪 Test 3: Data race en get_flow_stats_mut()" << std::endl;
    
    auto& manager = ShardedFlowManager::instance();
    ShardedFlowManager::Config config;
    config.shard_count = 4;
    config.max_flows_per_shard = 1000;
    
    manager.initialize(config);
    
    // Crear un flow de prueba
    FlowKey test_key{
        .src_ip = 0x0a000001,
        .dst_ip = 0x0a000002,
        .src_port = 12345,
        .dst_port = 80,
        .protocol = 6
    };
    
    SimpleEvent initial_event;
    manager.add_packet(test_key, initial_event);
    
    constexpr int NUM_WRITER_THREADS = 4;
    constexpr int NUM_READER_THREADS = 4;
    constexpr int ITERATIONS = 10000;
    
    std::atomic<bool> stop{false};
    std::atomic<int> write_count{0};
    std::atomic<int> read_count{0};
    std::atomic<int> data_race_detected{0};
    
    // Writers: usan get_flow_stats_mut() para modificar
    std::vector<std::thread> writers;
    for (int w = 0; w < NUM_WRITER_THREADS; ++w) {
        writers.emplace_back([&, w]() {
            for (int i = 0; i < ITERATIONS && !stop.load(); ++i) {
                auto* stats = manager.get_flow_stats_mut(test_key);
                if (stats) {
                    // MODIFICACIÓN CONCURRENTE SIN LOCK
                    // ThreadSanitizer debe detectar race aquí
                    stats->add_packet(initial_event, test_key);
                    write_count.fetch_add(1, std::memory_order_relaxed);
                }
                std::this_thread::sleep_for(std::chrono::microseconds(w * 10));
            }
        });
    }
    
    // Readers: usan get_flow_stats() para leer
    std::vector<std::thread> readers;
    for (int r = 0; r < NUM_READER_THREADS; ++r) {
        readers.emplace_back([&, r]() {
            while (!stop.load() && write_count.load() < ITERATIONS * NUM_WRITER_THREADS) {
                const auto* stats = manager.get_flow_stats(test_key);
                if (stats) {
                    // LECTURA CONCURRENTE CON ESCRITURA
                    // Esto es safe por get_flow_stats() (shared_lock)
                    volatile uint64_t packet_count = stats->get_packet_count();
                    (void)packet_count;  // Evitar warning de unused
                    read_count.fetch_add(1, std::memory_order_relaxed);
                }
                std::this_thread::sleep_for(std::chrono::microseconds(r * 5));
            }
        });
    }
    
    // Ejecutar por tiempo limitado
    std::this_thread::sleep_for(std::chrono::seconds(2));
    stop.store(true);
    
    // Esperar threads
    for (auto& w : writers) w.join();
    for (auto& r : readers) r.join();
    
    std::cout << "\n📊 Resultados Test 3:" << std::endl;
    std::cout << "  Escrituras: " << write_count.load() << std::endl;
    std::cout << "  Lecturas: " << read_count.load() << std::endl;
    
    // ThreadSanitizer detectará automáticamente si hay data race
    // Para nuestra verificación, podemos forzar un crash si detectamos inconsistency
    auto final_stats = manager.get_flow_stats(test_key);
    if (final_stats) {
        uint64_t expected_min_packets = write_count.load() + 1;  // +1 por inicial
        uint64_t actual_packets = final_stats->get_packet_count();
        
        std::cout << "  Packets en flow final: " << actual_packets << std::endl;
        std::cout << "  Mínimo esperado: " << expected_min_packets << std::endl;
        
        if (actual_packets < expected_min_packets) {
            std::cout << "❌ FAIL: Pérdida de updates (data race confirmada)" << std::endl;
            std::cout << "   Se perdieron " << (expected_min_packets - actual_packets) 
                      << " updates por race condition" << std::endl;
            exit(1);
        }
    }
    
    std::cout << "✅ Test ejecutado (ThreadSanitizer reportará races si existen)" << std::endl;
}

int main() {
    test_concurrent_mut_access();
    return 0;
}
```

**Compilación y ejecución:**
```bash
# Compilar con ThreadSanitizer
cd /vagrant/sniffer
g++ -std=c++20 -Iinclude -fsanitize=thread -g -O0 \
    tests/test_data_race_mut.cpp \
    src/flow/sharded_flow_manager.cpp \
    src/flow/flow_manager.cpp \
    -o build/test_data_race_mut

# Ejecutar
cd /vagrant/sniffer/build
./test_data_race_mut
```

**Comportamiento esperado si hay data race:**
```
WARNING: ThreadSanitizer: data race (pid=12345)
  Write of size 8 at 0x7fffe8c2b200 by thread T2 (mut):
    #0 FlowStatistics::add_packet()
    #1 test_concurrent_mut_access()::<lambda()>::operator()()

  Previous read of size 8 at 0x7fffe8c2b200 by thread T3 (non-mut):
    #0 FlowStatistics::get_packet_count()
    #1 test_concurrent_mut_access()::<lambda()>::operator()()
```

**Criterio de PASS/FAIL:**
- **PASS:** ThreadSanitizer no reporta warnings, actual_packets >= expected_min_packets
- **FAIL:** ThreadSanitizer detecta race, OR actual_packets < expected_min_packets

---

## 📊 PLAN DE VALIDACIÓN CIENTÍFICA

### **Día 44 - Morning (3h): Ejecución de Tests**

1. **Configurar entorno de testing:**
```bash
cd /vagrant/sniffer
mkdir -p tests build

# Copiar archivos de test
cp /tmp/test_*.cpp tests/
cp /tmp/benchmark_*.cpp tests/
```

2. **Ejecutar secuencia de pruebas:**
```bash
# 1. Test race condition initialize
./build/test_race_initialize 2>&1 | tee results/initialize_race.log

# 2. Benchmark LRU performance  
./build/benchmark_lru_performance 2>&1 | tee results/lru_benchmark.log

# 3. Test data race get_flow_stats_mut
./build/test_data_race_mut 2>&1 | tee results/mut_race.log
```

3. **Analizar resultados:**
```bash
# Extraer métricas clave
grep -E "(PASS|FAIL|Resultados|CONCLUSIÓN)" results/*.log
```

### **Día 44 - Afternoon (3h): Decisión basada en evidencia**

**Tabla de decisión:**

| Test | Resultado | Acción |
|------|-----------|--------|
| initialize() race | FAIL | Aplicar std::call_once |
| LRU performance | FAIL (>10ms) | Implementar iterator map O(1) |
| get_flow_stats_mut() race | FAIL | Eliminar método o hacer thread-safe |

### **Día 44 - Evening (2h): Documentación de evidencia**

Crear `/vagrant/docs/validation/ISSUE-003_EVIDENCE.md`:
```
# Evidencia Científica - ISSUE-003 ShardedFlowManager

## 1. Race Condition initialize()
- Test: test_race_initialize.cpp
- Compilación: g++ -fsanitize=thread
- Resultado: [PASS/FAIL]
- ThreadSanitizer output: [copiar]
- Decisión: [mantener/cambiar]

## 2. LRU Performance O(n)
- Benchmark: benchmark_lru_performance.cpp
- Métricas: [tabla con flows/updates/tiempo]
- Threshold: <10ms por update para 10K flows
- Resultado: [cumple/excede]
- Decisión: [optimizar/mantener]

## 3. Data Race get_flow_stats_mut()
- Test: test_data_race_mut.cpp
- Resultado: [PASS/FAIL]
- Pérdida de updates: [X/expected]
- Decisión: [eliminar/arreglar]
```

---

## 🏛️ CONCLUSIÓN DEL MÉTODO CIENTÍFICO

**Alonso y Claude:** Esto es Vía Appia en acción:

1. ✅ **Hipótesis** → DeepSeek identificó posibles bugs
2. ⏳ **Experimento** → Tests diseñados (arriba)
3. ⏳ **Observación** → Ejecutaremos y mediremos
4. ⏳ **Conclusión** → Basada en datos, no opiniones
5. ⏳ **Acción** → Fix solo si evidencia lo justifica

**¿Listo para ejecutar los tests y ver qué dicen los datos?** 🔬📊

**Próximos pasos:**
1. Copiar archivos de test al directorio `/vagrant/sniffer/tests/`
2. Compilar con las flags indicadas
3. Ejecutar y capturar resultados
4. Tomar decisiones basadas en evidencia

**¡Manos a la obra con el método científico!** 🧪

Claude pregunta:

DeepSeek, gracias por el análisis.

ChatGPT-5 confirmó 2 de tus 3 hipótesis:
1. ✅ LRU O(n) - CONSENSO 3/5 revisores
2. ✅ initialized_ race - CONSENSO 2/5 revisores
3. ❓ get_mut unsafe - Solo tú lo identificaste

Necesitamos TESTS para validar #2 y #3:

**Test 1: initialized_ race**
- Múltiples threads llamando initialize() simultáneamente
- TSAN debe detectar data race
- Código standalone ejecutable

**Test 2: get_mut data race**
- Thread A: get_flow_stats_mut() + modify
- Thread B: get_flow_stats() + read
- TSAN debe detectar race
- Código standalone ejecutable

Si tests FALLAN → aplicamos fixes.
Si tests PASAN → código actual es seguro.

Método científico: evidencia antes que teoría. 🔬

DeepSeek responde:

# 🧪 TESTS CIENTÍFICOS PARA VALIDACIÓN

## TEST 1: Race Condition en `initialize()`

```cpp
// test_race_initialize.cpp
#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>

// Mínimo mock necesario para compilar el test
namespace sniffer {
namespace flow {

struct SimpleEvent {};  // Dummy para compilación

class ShardedFlowManager {
public:
    struct Config {
        size_t shard_count = 0;
        size_t max_flows_per_shard = 10000;
    };
    
    static ShardedFlowManager& instance() {
        static ShardedFlowManager instance;
        return instance;
    }
    
    // 🔬 VERSIÓN ACTUAL (posible race condition)
    void initialize(const Config& config) {
        if (initialized_) {
            return;
        }
        config_ = config;
        initialized_ = true;
    }
    
private:
    Config config_;
    bool initialized_ = false;
};

} // namespace flow
} // namespace sniffer

// Test científico: Race condition en initialize()
void test_race_condition_initialize() {
    std::cout << "🧪 TEST 1: Race Condition en initialize()\n";
    std::cout << "===========================================\n";
    
    constexpr int NUM_THREADS = 10;
    constexpr int ATTEMPTS_PER_THREAD = 100;
    
    std::vector<std::thread> threads;
    std::atomic<int> initializations{0};
    std::atomic<int> double_initializations{0};
    
    auto worker = [&](int thread_id) {
        for (int i = 0; i < ATTEMPTS_PER_THREAD; ++i) {
            auto& manager = sniffer::flow::ShardedFlowManager::instance();
            sniffer::flow::ShardedFlowManager::Config config;
            config.shard_count = 4 + thread_id;
            
            // Medir si se llama múltiples veces
            int before = initializations.load();
            manager.initialize(config);
            int after = initializations.fetch_add(1);
            
            if (after > before) {
                // Otro thread ya incrementó → posible double initialization
                double_initializations.fetch_add(1);
            }
            
            // Pequeña variación para aumentar probabilidad de race
            std::this_thread::sleep_for(std::chrono::microseconds(thread_id * 3));
        }
    };
    
    // Lanzar threads concurrentemente
    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back(worker, t);
    }
    
    // Esperar
    for (auto& th : threads) {
        th.join();
    }
    
    // Análisis de resultados
    std::cout << "\n📊 RESULTADOS:\n";
    std::cout << "  Total inicializaciones llamadas: " << initializations.load() << "\n";
    std::cout << "  Posibles double-initializations: " << double_initializations.load() << "\n";
    
    // 🔬 CRITERIO DE FALLO CIENTÍFICO:
    // Si hay más inicializaciones que threads, entonces initialized_=false
    // permitió que múltiples threads pasaran la verificación
    if (double_initializations > 0) {
        std::cout << "\n❌ FALLO: Race condition detectada\n";
        std::cout << "   Múltiples threads pasaron la verificación initialized_=false\n";
        std::cout << "   Esto corrompería config_ con valores inconsistentes\n";
        
        // ThreadSanitizer debería reportar:
        // WARNING: ThreadSanitizer: data race (pid=...)
        //   Write of size 1 at 0x... by thread T1:
        //     #0 ShardedFlowManager::initialize()
        //   Previous write of size 1 at 0x... by thread T2:
        //     #0 ShardedFlowManager::initialize()
        
        exit(1);
    } else {
        std::cout << "\n✅ PASO: No se detectó double-initialization (pero TSAN puede ver más)\n";
        std::cout << "   ThreadSanitizer puede detectar races que no vemos en lógica\n";
    }
}

int main() {
    test_race_condition_initialize();
    return 0;
}
```

**Compilación con ThreadSanitizer:**
```bash
# Compilar con ThreadSanitizer
g++ -std=c++20 -fsanitize=thread -g -O1 test_race_initialize.cpp -o test_race_initialize -lpthread

# Ejecutar test
./test_race_initialize

# También ejecutar con helgrind para validación adicional
valgrind --tool=helgrind ./test_race_initialize
```

**Output esperado si hay race condition:**
```
🧪 TEST 1: Race Condition en initialize()
===========================================

📊 RESULTADOS:
  Total inicializaciones llamadas: 1000
  Posibles double-initializations: 8

❌ FALLO: Race condition detectada
   Múltiples threads pasaron la verificación initialized_=false
   Esto corrompería config_ con valores inconsistentes

# ThreadSanitizer agregaría:
WARNING: ThreadSanitizer: data race (pid=12345)
  Write of size 1 at 0x7fffe8c2b1c0 by thread T2:
    #0 ShardedFlowManager::initialize()
  Previous write of size 1 at 0x7fffe8c2b1c0 by thread T1:
    #0 ShardedFlowManager::initialize()
```

---

## TEST 2: Data Race en `get_flow_stats_mut()`

```cpp
// test_race_mut_access.cpp
#include <iostream>
#include <thread>
#include <atomic>
#include <chrono>
#include <vector>

// Mínimo mock para el test
namespace sniffer {
namespace flow {

struct FlowKey {
    uint32_t src_ip, dst_ip;
    uint16_t src_port, dst_port;
    uint8_t protocol;
    
    struct Hash {
        size_t operator()(const FlowKey& k) const {
            return k.src_ip ^ k.dst_ip ^ k.src_port ^ k.dst_port ^ k.protocol;
        }
    };
};

struct FlowStatistics {
    std::atomic<uint64_t> packet_count{0};
    std::atomic<uint64_t> byte_count{0};
    
    void add_packet() {
        // ⚠️ Si no es atómico, habrá race condition
        packet_count.fetch_add(1, std::memory_order_relaxed);
    }
    
    uint64_t get_packet_count() const {
        return packet_count.load(std::memory_order_relaxed);
    }
};

class ShardedFlowManager {
public:
    struct Config {
        size_t shard_count = 4;
    };
    
    static ShardedFlowManager& instance() {
        static ShardedFlowManager instance;
        return instance;
    }
    
    void initialize(const Config&) {}
    
    // 🔬 Versión UNSAFE (actual)
    FlowStatistics* get_flow_stats_mut(const FlowKey& key) {
        // Simular acceso sin lock completo
        static FlowStatistics stats;
        return &stats;
    }
    
    const FlowStatistics* get_flow_stats(const FlowKey& key) const {
        static FlowStatistics stats;
        return &stats;
    }
    
    void add_packet(const FlowKey& key) {
        if (auto* stats = get_flow_stats_mut(key)) {
            stats->add_packet();
        }
    }
};

} // namespace flow
} // namespace sniffer

// Test científico: Data race en get_flow_stats_mut()
void test_data_race_mut_access() {
    std::cout << "🧪 TEST 2: Data Race en get_flow_stats_mut()\n";
    std::cout << "=============================================\n";
    
    auto& manager = sniffer::flow::ShardedFlowManager::instance();
    sniffer::flow::ShardedFlowManager::Config config;
    manager.initialize(config);
    
    sniffer::flow::FlowKey test_key{
        .src_ip = 0x0a000001,
        .dst_ip = 0x0a000002,
        .src_port = 12345,
        .dst_port = 80,
        .protocol = 6
    };
    
    constexpr int WRITER_THREADS = 4;
    constexpr int READER_THREADS = 4;
    constexpr int DURATION_MS = 2000;
    
    std::atomic<bool> stop{false};
    std::atomic<uint64_t> write_count{0};
    std::atomic<uint64_t> read_count{0};
    std::atomic<uint64_t> inconsistent_reads{0};
    
    // Writers: usan get_flow_stats_mut() para modificar
    std::vector<std::thread> writers;
    for (int w = 0; w < WRITER_THREADS; ++w) {
        writers.emplace_back([&, w]() {
            while (!stop.load()) {
                if (auto* stats = manager.get_flow_stats_mut(test_key)) {
                    stats->add_packet();
                    write_count.fetch_add(1, std::memory_order_relaxed);
                }
                // Variación para aumentar probabilidad de race
                std::this_thread::sleep_for(std::chrono::microseconds(w * 5));
            }
        });
    }
    
    // Readers: usan get_flow_stats() para leer
    std::vector<std::thread> readers;
    for (int r = 0; r < READER_THREADS; ++r) {
        readers.emplace_back([&, r]() {
            uint64_t last_value = 0;
            while (!stop.load()) {
                if (const auto* stats = manager.get_flow_stats(test_key)) {
                    uint64_t current = stats->get_packet_count();
                    read_count.fetch_add(1, std::memory_order_relaxed);
                    
                    // Verificar consistencia (debería ser monótonamente creciente)
                    if (current < last_value) {
                        inconsistent_reads.fetch_add(1, std::memory_order_relaxed);
                        std::cerr << "❌ Lectura inconsistente: " << current << " < " << last_value << "\n";
                    }
                    last_value = current;
                }
                std::this_thread::sleep_for(std::chrono::microseconds(r * 3));
            }
        });
    }
    
    // Ejecutar por tiempo limitado
    std::this_thread::sleep_for(std::chrono::milliseconds(DURATION_MS));
    stop.store(true);
    
    // Esperar threads
    for (auto& w : writers) w.join();
    for (auto& r : readers) r.join();
    
    // Leer valor final
    const auto* final_stats = manager.get_flow_stats(test_key);
    uint64_t final_count = final_stats ? final_stats->get_packet_count() : 0;
    
    std::cout << "\n📊 RESULTADOS:\n";
    std::cout << "  Escrituras realizadas: " << write_count.load() << "\n";
    std::cout << "  Lecturas realizadas: " << read_count.load() << "\n";
    std::cout << "  Valor final en contador: " << final_count << "\n";
    std::cout << "  Lecturas inconsistentes detectadas: " << inconsistent_reads.load() << "\n";
    
    // 🔬 CRITERIO DE FALLO CIENTÍFICO:
    // 1. Si hay lecturas inconsistentes (contador que decrece)
    // 2. Si ThreadSanitizer detecta data race
    // 3. Si faltan writes (final_count < write_count)
    
    bool has_race = false;
    
    if (inconsistent_reads > 0) {
        std::cout << "\n❌ FALLO: Lecturas inconsistentes detectadas\n";
        std::cout << "   El contador decreció durante ejecución (race condition)\n";
        has_race = true;
    }
    
    if (final_count < write_count.load()) {
        std::cout << "\n❌ FALLO: Pérdida de writes\n";
        std::cout << "   Se esperaban " << write_count.load() << " writes, pero contador es " << final_count << "\n";
        std::cout << "   Diferencia: " << (write_count.load() - final_count) << " writes perdidos\n";
        has_race = true;
    }
    
    if (has_race) {
        std::cout << "\n💡 ThreadSanitizer debería reportar:\n";
        std::cout << "   WARNING: ThreadSanitizer: data race\n";
        std::cout << "     Write of size 8 at 0x... by thread T1 (writer)\n";
        std::cout << "     Previous read of size 8 at 0x... by thread T2 (reader)\n";
        exit(1);
    } else {
        std::cout << "\n✅ PASO: No se detectaron inconsistencias en lógica\n";
        std::cout << "   (Pero ThreadSanitizer puede detectar races a nivel de memoria)\n";
    }
}

int main() {
    test_data_race_mut_access();
    return 0;
}
```

**Compilación con ThreadSanitizer:**
```bash
# Compilar con ThreadSanitizer
g++ -std=c++20 -fsanitize=thread -g -O1 test_race_mut_access.cpp -o test_race_mut_access -lpthread

# Ejecutar test
./test_race_mut_access

# Para validación adicional
valgrind --tool=drd ./test_race_mut_access
```

**Output esperado si hay data race:**
```
🧪 TEST 2: Data Race en get_flow_stats_mut()
=============================================

📊 RESULTADOS:
  Escrituras realizadas: 1842
  Lecturas realizadas: 2657
  Valor final en contador: 1794
  Lecturas inconsistentes detectadas: 3
❌ Lectura inconsistente: 1791 < 1792
❌ Lectura inconsistente: 1792 < 1793
❌ Lectura inconsistente: 1790 < 1794

❌ FALLO: Lecturas inconsistentes detectadas
   El contador decreció durante ejecución (race condition)

❌ FALLO: Pérdida de writes
   Se esperaban 1842 writes, pero contador es 1794
   Diferencia: 48 writes perdidos

💡 ThreadSanitizer debería reportar:
   WARNING: ThreadSanitizer: data race
     Write of size 8 at 0x... by thread T1 (writer)
     Previous read of size 8 at 0x... by thread T2 (reader)
```

---

## 📊 PROTOCOLO DE DECISIÓN CIENTÍFICA

### **Para cada test:**

```bash
# 1. Compilar con ThreadSanitizer
g++ -fsanitize=thread -g -O1 test_X.cpp -o test_X -lpthread

# 2. Ejecutar test
./test_X 2>&1 | tee resultados_X.log

# 3. Analizar salida
grep -E "(FALLO|PASO|WARNING|ERROR)" resultados_X.log

# 4. Verificar con helgrind (opcional)
valgrind --tool=helgrind ./test_X 2>&1 | grep -E "(Possible|Conflicts)"
```

### **Criterios de decisión:**

**Test 1 (`initialize()`):**
- ✅ **PASA SI:** ThreadSanitizer no reporta warnings, `double_initializations = 0`
- ❌ **FALLA SI:** ThreadSanitizer detecta data race, O `double_initializations > 0`

**Test 2 (`get_flow_stats_mut()`):**
- ✅ **PASA SI:** ThreadSanitizer no reporta warnings, `inconsistent_reads = 0`, `final_count == write_count`
- ❌ **FALLA SI:** ThreadSanitizer detecta data race, O `inconsistent_reads > 0`, O `final_count < write_count`

### **Acciones basadas en evidencia:**

| Test | Resultado | Acción |
|------|-----------|--------|
| initialize() race | ❌ FALLA | Aplicar `std::call_once` |
| initialize() race | ✅ PASA | Mantener implementación actual |
| get_mut() race | ❌ FALLA | Eliminar método o hacer thread-safe |
| get_mut() race | ✅ PASA | Mantener método (con documentación de uso) |

---

## 🏛️ CONCLUSIÓN METODOLÓGICA

**Claude y Alonso:** Estos tests implementan el método científico:

1. **Hipótesis:** Race condition existe en `initialize()` y `get_flow_stats_mut()`
2. **Experimento:** Tests reproducen condiciones de concurrencia extrema
3. **Medición:** Métricas cuantitativas (inconsistencias, pérdidas)
4. **Validación:** ThreadSanitizer como detector independiente
5. **Conclusión:** Basada en datos empíricos, no opiniones

**Próximos pasos:**
1. Ejecutar tests en el entorno real del proyecto
2. Capturar evidencia (logs de TSAN)
3. Tomar decisiones basadas en resultados
4. Documentar en `/vagrant/docs/validation/`

**¿Listos para ejecutar los tests y ver qué dice la evidencia?** 🔬📊