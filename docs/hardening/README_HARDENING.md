# 🛡️ ML Defender - Hardening Phase Guide

**Status**: Flags preparados, **DESACTIVADOS** por defecto  
**Activar cuando**: Papers enviados + features completas + inicio de fase fixing  
**Última actualización**: Day 11, Dec 7, 2025

---

## 📋 Estado Actual

### ✅ Preparado (No Activo)

| Componente | Archivo | Flags Añadidos | Estado |
|------------|---------|----------------|--------|
| **sniffer** | `Makefile` | Basic + Sanitizers | ❌ Comentados |
| **ml-detector** | `CMakeLists.txt` | Options condicionales | ❌ OFF |
| **firewall-acl-agent** | `CMakeLists.txt` | Options condicionales | ❌ OFF |
| **rag-security** | `CMakeLists.txt` | Options condicionales | ❌ OFF |

**Comportamiento actual**: Compilación normal, sin overhead, desarrollo rápido

---

## 🔧 Cómo Activar (Fase Hardening)

### Paso 1: Verificar Prerequisitos

```bash
# Confirmar que estamos en fase hardening
# ✅ Papers enviados a revisión
# ✅ Todas las features implementadas
# ✅ Pipeline funcional end-to-end
# ✅ Listos para fixing exhaustivo
```

### Paso 2: Activar en Sniffer (Makefile)

```bash
cd /vagrant/sniffer

# Editar Makefile
vim Makefile

# Descomentar esta línea (cerca del inicio):
# HARDENING_ENABLED = 1

# Recompilar
make clean
make -j6

# Verificar flags activos
make -n | grep "stack-protector"
# Deberías ver: -fstack-protector-strong
```

### Paso 3: Activar en CMake Components

```bash
# ml-detector
cd /vagrant/ml-detector/build
rm -rf *
cmake -DENABLE_HARDENING=ON ..
make -j6

# firewall-acl-agent
cd /vagrant/firewall-acl-agent/build
rm -rf *
cmake -DENABLE_HARDENING=ON ..
make -j6

# rag-security
cd /vagrant/rag/build
rm -rf *
cmake -DENABLE_HARDENING=ON ..
make -j6
```

---

## 🧪 Testing con Sanitizers

**IMPORTANTE**: Usar UN sanitizer a la vez. No combinar.

### AddressSanitizer (Memory Errors)

**Detecta**:
- Buffer overflows
- Use-after-free
- Double-free
- Memory leaks

```bash
# Sniffer (Makefile)
cd /vagrant/sniffer
# En Makefile, descomentar:
# SANITIZER = address
# CXXFLAGS += -fsanitize=address -fno-omit-frame-pointer
make clean && make -j6

# ml-detector (CMake)
cd /vagrant/ml-detector/build
rm -rf *
cmake -DENABLE_HARDENING=ON -DSANITIZER=address ..
make -j6

# Ejecutar tests
sudo ./sniffer -c config/sniffer.json
# Si hay memory errors, ASan imprimirá stack trace
```

**Ejemplo output de error**:
```
=================================================================
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...
    #0 0x... in parse_packet /vagrant/sniffer/src/parser.cpp:123
    #1 0x... in main /vagrant/sniffer/src/main.cpp:456
```

### ThreadSanitizer (Race Conditions)

**Detecta**:
- Data races
- Thread safety issues
- Lock order inversions

```bash
# ml-detector (tiene threads)
cd /vagrant/ml-detector/build
rm -rf *
cmake -DENABLE_HARDENING=ON -DSANITIZER=thread ..
make -j6

./ml-detector -c ../config/ml_detector_config.json

# TSan imprimirá si hay races
```

**Ejemplo output de error**:
```
==================
WARNING: ThreadSanitizer: data race (pid=12345)
  Write of size 4 at 0x... by thread T1:
    #0 detector_thread /vagrant/ml-detector/src/detector.cpp:234
  Previous read of size 4 at 0x... by main thread:
    #0 main_loop /vagrant/ml-detector/src/main.cpp:567
```

### UndefinedBehaviorSanitizer (UB)

**Detecta**:
- Integer overflow/underflow
- Division by zero
- Null pointer dereference
- Misaligned access

```bash
cd /vagrant/sniffer
# Descomentar en Makefile:
# SANITIZER = undefined
make clean && make -j6

sudo ./sniffer -c config/sniffer.json
```

**Ejemplo output de error**:
```
runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
    /vagrant/sniffer/src/features.cpp:89:12
```

### MemorySanitizer (Uninitialized Reads)

**Detecta**:
- Uninitialized memory reads
- Use of uninitialized variables

```bash
cd /vagrant/ml-detector/build
rm -rf *
cmake -DENABLE_HARDENING=ON -DSANITIZER=memory ..
make -j6

./ml-detector -c ../config/ml_detector_config.json
```

---

## 📊 Performance Impact

| Configuration | CPU Overhead | Memory Overhead | Use Case |
|---------------|--------------|-----------------|----------|
| **No hardening** | 0% | 0% | Development (actual) |
| **Basic flags** | ~5% | ~0% | Production candidate |
| **+ ASan** | ~100% | ~200% | Memory debugging |
| **+ TSan** | ~500-1500% | ~900% | Thread debugging |
| **+ UBSan** | ~20% | ~0% | UB detection |
| **+ MSan** | ~200% | ~100% | Uninitialized reads |

**Recomendación**: En fase hardening, ejecutar con CADA sanitizer separadamente.

---

## 🔍 Testing Workflow (Fase Hardening)

### Week 1: Basic Security

```bash
# Día 1-2: Compilar con ENABLE_HARDENING=ON
# - Corregir warnings de compilación
# - Todos los componentes limpios

# Día 3-4: Ejecutar test suite completo
# - Gateway mode validation
# - Host-based mode validation
# - PCAP replay (CTU-13, tcpreplay)
# - Stress tests (chaos_monkey)

# Día 5: Documentar baseline
# - Performance metrics con hardening básico
# - Comparar vs sin hardening
```

### Week 2: AddressSanitizer

```bash
# Día 1-2: Compilar con ASan
# - Sniffer, detector, firewall, rag
# - Ejecutar test suite

# Día 3-4: Reproducir y corregir issues
# - Stack traces de ASan
# - Memory leaks report
# - Corregir uno por uno

# Día 5: Re-validar con ASan limpio
# - 0 errores, 0 leaks
```

### Week 3: ThreadSanitizer

```bash
# Día 1-2: Compilar con TSan
# - Solo componentes con threads (ml-detector)
# - Ejecutar stress tests

# Día 3-4: Corregir data races
# - Añadir mutexes donde necesario
# - Verificar lock ordering

# Día 5: Re-validar con TSan limpio
```

### Week 4: UBSan + MSan

```bash
# Día 1-2: UndefinedBehaviorSanitizer
# - Compilar, ejecutar, corregir

# Día 3-4: MemorySanitizer
# - Compilar, ejecutar, corregir

# Día 5: Full re-test con todos los sanitizers
# - Uno por uno, todos limpios
# - Documentar en VALIDATION_HARDENING.md
```

---

## 📝 Checklist de Hardening Completo

```markdown
### Preparación
- [ ] Papers enviados a revisión
- [ ] Todas las features implementadas
- [ ] Tests end-to-end pasando
- [ ] Backups de código actual

### Basic Security
- [ ] Sniffer compilado con HARDENING_ENABLED=1
- [ ] ml-detector con -DENABLE_HARDENING=ON
- [ ] firewall con -DENABLE_HARDENING=ON
- [ ] rag con -DENABLE_HARDENING=ON
- [ ] 0 compiler warnings
- [ ] Performance baseline documentado

### AddressSanitizer
- [ ] Sniffer con ASan: 0 errores, 0 leaks
- [ ] ml-detector con ASan: 0 errores, 0 leaks
- [ ] firewall con ASan: 0 errores, 0 leaks
- [ ] rag con ASan: 0 errores, 0 leaks
- [ ] Stress tests passed (1 hour runtime)

### ThreadSanitizer
- [ ] ml-detector con TSan: 0 data races
- [ ] Stress tests passed (1 hour runtime)

### UndefinedBehaviorSanitizer
- [ ] Todos los componentes: 0 UB detected
- [ ] Edge cases tested (div by zero, overflow, etc)

### MemorySanitizer
- [ ] Todos los componentes: 0 uninitialized reads
- [ ] Full pipeline tested

### Production Ready
- [ ] Todos los sanitizers limpios
- [ ] Performance impact aceptable (<10% con basic flags)
- [ ] Security audit documentado
- [ ] VALIDATION_HARDENING.md completo
- [ ] Code review final (multi-agent)
```

---

## 🚨 Known Issues Registry

**Documentar aquí los issues encontrados durante hardening**:

```markdown
### Issue #1: [Título]
- **Componente**: sniffer/ml-detector/firewall/rag
- **Sanitizer**: ASan/TSan/UBSan/MSan
- **Severidad**: Critical/High/Medium/Low
- **Descripción**: [Stack trace o descripción]
- **Fix**: [Qué se hizo para corregir]
- **Commit**: [SHA del commit con fix]
- **Validado**: [Fecha]

### Issue #2: ...
```

---

## 📚 Referencias

- [AddressSanitizer](https://github.com/google/sanitizers/wiki/AddressSanitizer)
- [ThreadSanitizer](https://github.com/google/sanitizers/wiki/ThreadSanitizerCppManual)
- [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)
- [MemorySanitizer](https://github.com/google/sanitizers/wiki/MemorySanitizer)

---

## 🙏 Multi-Agent Review (Fase Hardening)

**Cuando activemos hardening, solicitar review de**:
- **Grok4**: Kernel/eBPF memory safety
- **DeepSeek**: Automated testing infrastructure
- **Qwen**: Production deployment concerns
- **Claude**: Code review + documentation

**Filosofía**: Via Appia Quality - Build to last, fix thoroughly

---

**Preparado por**: Claude + Alonso  
**Estado**: Flags preparados, esperando fase hardening  
**Próxima revisión**: Post-papers, pre-production