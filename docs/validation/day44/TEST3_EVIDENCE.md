# TEST #3: Data Race en get_flow_stats_mut()

## Hipótesis (DeepSeek)

`get_flow_stats_mut()` permite acceso mutable sin garantías thread-safety, causando data races cuando múltiples threads modifican/leen el mismo flow.

## Test Original (código original)

### Configuración:
- 4 writer threads llamando `get_flow_stats_mut()` + `add_packet()`
- 4 reader threads llamando `get_flow_stats()` 
- Mismo FlowKey accedido concurrentemente

### Resultados:
```
Escrituras: 14,928
Lecturas: 72,670
❌ ThreadSanitizer: reported 42 warnings
```

### TSAN Output (sample):
```
WARNING: ThreadSanitizer: data race (pid=2022)
  Read of size 8 at 0x7b4400000028 by thread T2:
    #0 FlowStatistics::add_packet() include/flow_manager.hpp:85
    
  Previous write of size 8 at 0x7b4400000028 by thread T1:
    #0 FlowStatistics::add_packet() include/flow_manager.hpp:94
```

**Campos en race:** `spkts`, `dpkts`, `sbytes`, `dbytes` (líneas 85, 88, 94, 95)

---

## Root Cause Identificado

### Problema 1: get_flow_stats_mut()
```cpp
FlowStatistics* get_flow_stats_mut(const FlowKey& key) {
    std::unique_lock lock(*shard.mutex);
    auto it = shard.flows->find(key);
    return (it != end) ? &it->second.stats : nullptr;
}  // ← Lock liberado AQUÍ

// Usuario modifica fuera del lock:
auto* stats = manager.get_flow_stats_mut(key);
stats->add_packet(event);  // ← SIN PROTECCIÓN
```

### Problema 2: get_flow_stats()
```cpp
const FlowStatistics* get_flow_stats(const FlowKey& key) const {
    std::shared_lock lock(*shard.mutex);
    return &it->second.stats;
}  // ← Lock liberado AQUÍ

// Usuario lee fuera del lock:
const auto* stats = manager.get_flow_stats(key);
uint64_t packets = stats->spkts;  // ← RACE si otro thread escribe
```

**Conclusión:** Ambos métodos devuelven punteros que se usan **fuera del lock** → data race inevitable.

---

## FIX #3: API Thread-Safe por Diseño

### Cambios Implementados:

**1. ELIMINADOS métodos unsafe:**
```cpp
// REMOVED:
FlowStatistics* get_flow_stats_mut(const FlowKey& key);
const FlowStatistics* get_flow_stats(const FlowKey& key) const;
```

**2. NUEVO: get_flow_stats_copy()**
```cpp
std::optional<FlowStatistics> get_flow_stats_copy(const FlowKey& key) const {
    std::unique_lock lock(*shard.mutex);
    
    auto it = shard.flows->find(key);
    if (it != shard.flows->end()) {
        // Copia manual de todos los campos DENTRO del lock
        FlowStatistics copy;
        copy.spkts = it->second.stats.spkts;
        copy.dpkts = it->second.stats.dpkts;
        // ... (todos los campos)
        return std::make_optional(std::move(copy));
    }
    return std::nullopt;
}
```

**3. NUEVO: with_flow_stats() [template]**
```cpp
template<typename Func>
void with_flow_stats(const FlowKey& key, Func&& func) const {
    std::unique_lock lock(*shard.mutex);
    auto it = shard.flows->find(key);
    if (it != shard.flows->end()) {
        func(it->second.stats);  // Callback ejecuta DENTRO del lock
    }
}
```

**4. Cambio mutex:**
```cpp
// ANTES: std::shared_mutex (readers-writers)
// DESPUÉS: std::mutex (exclusive lock siempre)
```

---

## Validación Post-Fix

### Test con FIX #3:
```
Escrituras: 11,229 (add_packet)
Lecturas: 3,272 (get_flow_stats_copy)
✅ ThreadSanitizer: CLEAN (0 warnings)
```

### Verificación:
```bash
grep "ThreadSanitizer" results/test3_final_fix.log
# Output: (vacío)
```

**Resultado:** ✅ **TSAN CLEAN - NO DATA RACES**

---

## Comparativa ANTES vs DESPUÉS

| Aspecto | Original | FIX #3 |
|---------|----------|--------|
| Data races | 42 | 0 |
| API unsafe | 2 métodos | 0 |
| Retorna punteros | Sí | No |
| Copia en lock | No | Sí |
| Thread-safety | ❌ | ✅ |

---

## Análisis Arquitectural

### ¿Por qué falló shared_mutex?

El problema NO era `shared_mutex` vs `mutex`, sino **devolver punteros**:
```
Lock protege:     ✅ Acceso al map
Lock NO protege:  ❌ Uso del puntero retornado
```

### Lección aprendida:

**"Never return pointers to data protected by locks unless the lock is held for the entire lifetime of the pointer use."**

**Soluciones thread-safe:**
1. Retornar copia (get_flow_stats_copy)
2. Callback dentro del lock (with_flow_stats)
3. RAII guard que mantiene lock (complejo, no implementado)

---

## Conclusión TEST #3

✅ **HIPÓTESIS VALIDADA:** `get_flow_stats_mut()` causaba data races  
✅ **FIX IMPLEMENTADO:** API rediseñada sin punteros expuestos  
✅ **TSAN CLEAN:** 0 warnings con 11K writes + 3K reads concurrentes  

**Status:** ✅ **TEST #3 PASSED**

---

**Arquitectura Via Appia:** Código thread-safe by design, preparado para décadas 🏛️
