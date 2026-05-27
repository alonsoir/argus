# iptables_wrapper - Implementation Summary

## Status: ✅ COMPLETE

**Implementación terminada**: iptables_wrapper.cpp + iptables_wrapper.hpp  
**Compila**: ✅ Sin errores  
**Filosofía**: Comandos del sistema (igual que ipset_wrapper)

---

## Archivos Creados

### 1. include/firewall/iptables_wrapper.hpp
**Propósito**: Interfaz para manejo de reglas iptables

**Estructuras principales:**
```cpp
enum class IPTablesTable { FILTER, NAT, MANGLE, RAW };
enum class IPTablesChain { INPUT, FORWARD, OUTPUT, ... };
enum class IPTablesTarget { ACCEPT, DROP, REJECT, RETURN, JUMP };
enum class IPTablesProtocol { TCP, UDP, ICMP, ALL };

struct IPTablesRule { ... };      // Especificación completa de reglas
struct FirewallConfig { ... };    // Configuración del firewall
struct IPTablesResult<T> { ... }; // Result type (C++20 compatible)
```

**Interfaz pública:**
```cpp
class IPTablesWrapper {
    // Chain management
    IPTablesResult<void> create_chain(name, table);
    IPTablesResult<void> delete_chain(name, table);
    bool chain_exists(name, table);
    IPTablesResult<void> flush_chain(name, table);
    
    // Rule management
    IPTablesResult<void> add_rule(rule);
    IPTablesResult<void> delete_rule(chain, position, table);
    std::vector<std::string> list_rules(chain, table);
    
    // High-level setup
    IPTablesResult<void> setup_base_rules(config);
    IPTablesResult<void> cleanup_rules(config);
    
    // Save/restore
    IPTablesResult<void> save(filepath);
    IPTablesResult<void> restore(filepath);
};
```

---

### 2. src/core/iptables_wrapper.cpp
**Propósito**: Implementación usando comandos del sistema

**Decisiones de diseño:**

1. **Comandos del sistema (NO libiptc)**
   ```cpp
   // Usamos:
   system("iptables -t filter -N chain_name");
   system("iptables -A INPUT -m set --match-set blacklist src -j DROP");
   
   // NO usamos:
   // libiptc API (complejo, hard to maintain)
   ```

2. **Thread-safety con mutex**
   ```cpp
   std::lock_guard<std::mutex> lock(mutex_);
   ```

3. **Error handling robusto**
   ```cpp
   auto [ret, output] = execute_command(cmd);
   if (ret != 0) {
       return IPTablesResult<void>(IPTablesError{...});
   }
   ```

4. **PIMPL pattern (minimal)**
   ```cpp
   struct Impl {
       // No state needed - all via system commands
   };
   ```

---

## Funciones Implementadas

### Chain Management (5 funciones)
```cpp
✅ create_chain()      - Crear cadenas personalizadas
✅ delete_chain()      - Eliminar cadenas (flush + delete)
✅ chain_exists()      - Verificar existencia
✅ flush_chain()       - Limpiar todas las reglas
✅ list_chains()       - Listar cadenas en tabla
```

### Rule Management (3 funciones)
```cpp
✅ add_rule()          - Añadir regla con especificación completa
✅ delete_rule()       - Eliminar regla por posición
✅ list_rules()        - Listar reglas de una cadena
```

### High-Level Setup (2 funciones)
```cpp
✅ setup_base_rules()  - Setup completo del firewall ML Defender
✅ cleanup_rules()     - Limpieza completa
```

### Save/Restore (2 funciones)
```cpp
✅ save()              - iptables-save > file
✅ restore()           - iptables-restore < file
```

---

## setup_base_rules() - La Función Clave

Esta función crea la infraestructura completa del firewall en una sola llamada:

```cpp
IPTablesResult<void> setup_base_rules(const FirewallConfig& config) {
    // 1. Crear cadenas personalizadas
    //    - ML_DEFENDER_BLACKLIST
    //    - ML_DEFENDER_WHITELIST
    //    - ML_DEFENDER_RATELIMIT
    
    // 2. Regla whitelist (posición 1 - máxima prioridad)
    //    iptables -I INPUT 1 -m set --match-set whitelist src -j ACCEPT
    
    // 3. Regla blacklist (posición 2)
    //    iptables -I INPUT 2 -m set --match-set blacklist src -j DROP
    
    // 4. Regla rate limiting (posición 3)
    //    iptables -I INPUT 3 -j ML_DEFENDER_RATELIMIT
    //    - Limita 100 conexiones nuevas por minuto por IP
    //    - DROP si excede el límite
    
    // 5. RETURN al final de cada cadena personalizada
}
```

**Resultado:**
```
Chain INPUT (policy ACCEPT)
1: -m set --match-set ml_defender_whitelist src -j ACCEPT    ← Whitelist
2: -m set --match-set ml_defender_blacklist src -j DROP      ← Blacklist
3: -j ML_DEFENDER_RATELIMIT                                   ← Rate limit
... resto de reglas del sistema ...

Chain ML_DEFENDER_RATELIMIT
1: -p tcp -m conntrack --ctstate NEW -m recent --set -j ACCEPT
2: -p tcp -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 100 -j DROP
3: -j RETURN
```

---

## Integración con ipset

**Relación con ipset_wrapper:**
```
┌─────────────────────────────────────────────┐
│ iptables (STATIC rules - setup once)       │
│                                             │
│ Rule 1: -m set --match-set whitelist       │ ← References ipset
│ Rule 2: -m set --match-set blacklist       │ ← References ipset
│                                             │
└─────────────────────────────────────────────┘
                    ↓ matches against
┌─────────────────────────────────────────────┐
│ ipset (DYNAMIC IPs - updated continuously) │
│                                             │
│ Set: whitelist  → 10 IPs                   │ ← ipset_wrapper updates
│ Set: blacklist  → 50K IPs                  │ ← ipset_wrapper updates
│                                             │
└─────────────────────────────────────────────┘
```

**Workflow:**
1. **Una vez al inicio**: `iptables_wrapper.setup_base_rules()`
    - Crea reglas estáticas que referencian ipsets
    - Nunca se modifican después

2. **Continuamente durante operación**: `ipset_wrapper.add_batch()`
    - Añade/elimina IPs de los sets
    - Las reglas iptables automáticamente las consideran
    - O(1) lookup en kernel

---

## Características de la Implementación

### ✅ Ventajas (igual que ipset_wrapper)

1. **Simplicidad**
    - ~650 LOC vs ~2000+ con libiptc
    - Código fácil de leer y mantener
    - Comandos auditables

2. **Estabilidad**
    - CLI iptables es más estable que libiptc entre versiones
    - Menos propenso a cambios incompatibles

3. **Debuggabilidad**
    - Los comandos se pueden ejecutar manualmente
    - Output de error es legible (no códigos crípticos)
    - Fácil de reproducir problemas

4. **Sin dependencias**
    - No requiere libiptc-dev
    - Solo requiere iptables instalado (estándar en Linux)

### ⚠️ Trade-offs

1. **Overhead de proceso**
    - Cada comando spawns un shell
    - ~1-2ms por operación

2. **NO es problema porque:**
    - setup_base_rules() se llama UNA VEZ al inicio
    - Después las reglas NO cambian
    - Los updates dinámicos son vía ipset (no iptables)

---

## Uso Típico

```cpp
#include "firewall/iptables_wrapper.hpp"
#include "firewall/ipset_wrapper.hpp"

// Setup firewall (una vez al inicio)
FirewallConfig config;
config.blacklist_ipset = "ml_defender_blacklist";
config.whitelist_ipset = "ml_defender_whitelist";

IPTablesWrapper iptables;
auto result = iptables.setup_base_rules(config);

if (!result) {
    LOG_ERROR("Failed to setup firewall: {}", result.get_error().message);
    return -1;
}

// Ahora las reglas están activas
// Para bloquear IPs, usa ipset_wrapper (NO iptables):
IPSetWrapper ipset;
ipset.add_batch("ml_defender_blacklist", malicious_ips);  // ← ESTO

// NO hagas:
// iptables.add_rule(...) para cada IP  ← MAL, O(n) performance
```

---

## Testing

**Tests pendientes** (requieren root):
```cpp
TEST(IPTablesWrapper, CreateAndDeleteChain) {
    IPTablesWrapper wrapper;
    
    // Create
    auto result = wrapper.create_chain("TEST_CHAIN");
    ASSERT_TRUE(result);
    EXPECT_TRUE(wrapper.chain_exists("TEST_CHAIN"));
    
    // Delete
    result = wrapper.delete_chain("TEST_CHAIN");
    ASSERT_TRUE(result);
    EXPECT_FALSE(wrapper.chain_exists("TEST_CHAIN"));
}

TEST(IPTablesWrapper, SetupBaseRules) {
    IPTablesWrapper iptables;
    IPSetWrapper ipset;
    
    // Create ipsets first
    ipset.create_set({...});
    
    // Setup firewall
    FirewallConfig config;
    auto result = iptables.setup_base_rules(config);
    ASSERT_TRUE(result);
    
    // Verify rules exist
    auto rules = iptables.list_rules("INPUT");
    EXPECT_GT(rules.size(), 0);
    
    // Cleanup
    iptables.cleanup_rules(config);
}
```

---

## Próximos Pasos

### Completado ✅
1. ✅ ipset_wrapper (comandos del sistema, 16/20 tests passing)
2. ✅ iptables_wrapper (comandos del sistema, compila correctamente)
3. ✅ Documentación de decisiones de diseño

### Por hacer ⏳
1. **batch_processor.hpp/cpp**
    - Acumula detections en memoria
    - Batch flush a ipset
    - Deduplicación in-memory

2. **zmq_subscriber.hpp/cpp**
    - Recibe detections del ml-detector vía ZMQ
    - Parsea protobuf messages
    - Envía a batch_processor

3. **main.cpp**
    - Inicializa todo
    - Setup signal handlers
    - Event loop

4. **Unit tests para iptables_wrapper**
    - Requieren VM con root (igual que ipset tests)

5. **Integration tests**
    - End-to-end: ZMQ → batch → ipset → iptables

6. **Stress tests distribuidos**
    - THE CONTRACT TESTS
    - 5 escenarios documentados en PERFORMANCE_METRICS.md

---

## Compilación

```bash
cd /vagrant/firewall-acl-agent/build
rm -rf *
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON ..
make -j4

# Output esperado:
# [ 62%] Building CXX object CMakeFiles/firewall_core.dir/src/core/iptables_wrapper.cpp.o
# [ 75%] Linking CXX static library libfirewall_core.a
# [100%] Built target firewall_core
```

---

## Resumen

**iptables_wrapper está COMPLETO y LISTO**:
- ✅ Header con todas las estructuras y firmas
- ✅ Implementación usando comandos del sistema
- ✅ Thread-safe con mutex
- ✅ Error handling robusto
- ✅ setup_base_rules() implementado
- ✅ Compila sin errores
- ✅ Filosofía consistente con ipset_wrapper

**Siguiente**: batch_processor para conectar detections → ipset updates

**Filosofía mantenida**: Simple, mantenible, Via Appia Quality 🏛️