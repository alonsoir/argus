# 🏗️ ML Defender Build System: Single Source of Truth

**Last Updated:** 2026-02-01 - Day 48 Phase 1

**Authority:** Root `Makefile`

**Philosophy:** [Via Appia Quality] - Evidence-based, deterministic, and lean.

---

## 🎯 The Core Principle

**The root Makefile is the ONLY place where compiler flags (`-O`, `-g`, `-fsanitize`) are defined.**

Individual `CMakeLists.txt` files in component directories (sniffer, ml-detector, etc.) must remain **agnostic** to the build profile. They only handle file organization and dependency linking.

---

## 🛠️ Build Profiles

We have established four distinct profiles to balance performance, debugging, and safety.

### 1. Production (`PROFILE=production`)

* **Flags:** `-O3 -march=native -DNDEBUG -flto`
* **Goal:** Maximum performance and minimum binary size.
* **Result:** ~1.4MB binary (91% reduction).
* **Usage:** `make PROFILE=production all`

### 2. Debug (`PROFILE=debug`)

* **Flags:** `-g -O0 -fno-omit-frame-pointer -DDEBUG`
* **Goal:** Full symbol visibility for GDB/LLDB.
* **Result:** ~17MB binary.
* **Usage:** `make PROFILE=debug all`

### 3. ThreadSanitizer (`PROFILE=tsan`)

* **Flags:** `-fsanitize=thread -g -O1 -DTSAN_ENABLED`
* **Goal:** Detect data races and deadlocks.
* **Requirement:** Requires all linked libraries to be TSAN-compatible.
* **Usage:** `make PROFILE=tsan all`

### 4. AddressSanitizer (`PROFILE=asan`)

* **Flags:** `-fsanitize=address -g -O1 -DASAN_ENABLED`
* **Goal:** Detect memory leaks, buffer overflows, and use-after-free.
* **Usage:** `make PROFILE=asan all`

---

## 📂 Directory Structure

To avoid artifact contamination, each profile uses its own build and binary directory:

```bash
/vagrant/
├── build-production/  # Temporary CMake files for Production
├── build-debug/       # Temporary CMake files for Debug
├── bin-production/    # Final binaries (lean)
└── bin-debug/         # Final binaries (with symbols)

```

---

## 🧪 Validation: How to verify a build?

### Check Binary Size (Production vs Debug)

```bash
ls -lh bin-production/sniffer bin-debug/sniffer
# Expected: 1.4M vs 17M

```

### Check for Sanitizers

```bash
# For TSAN
nm bin-tsan/ml-detector | grep tsan
# For ASAN
nm bin-asan/ml-detector | grep asan

```

---

## ⚠️ Developer Rules (The "Don'ts")

1. **❌ DO NOT** add `set(CMAKE_CXX_FLAGS "-O3")` to any `CMakeLists.txt`.
2. **❌ DO NOT** hardcode `-fsanitize` in component files.
3. **❌ DO NOT** use `docker-compose` for building; the environment is now Vagrant-native.
4. **✅ ALWAYS** use the root Makefile to trigger builds.

---

## Perfiles disponibles
| Perfil | Uso | Flags |
|--------|-----|-------|
| `production` | Despliegue | `-O3 -flto` |
| `debug` | Desarrollo | `-g -O0` |
| `tsan` | Concurrencia | `-fsanitize=thread` |
| `asan` | Memoria | `-fsanitize=address` |

## Uso
```bash
make PROFILE=production all
make PROFILE=tsan test-hardening

# 🚀 **DÍA 48 COMPLETADO - REFACTORIZACIÓN DEL SISTEMA DE CONSTRUCCIÓN**

## 📦 **COMMIT REALIZADO Y PUSHED**

```bash
# Verificación del estado
git status
# On branch feature/build-system-single-source-of-truth
# nothing to commit, working tree clean

# Push exitoso a la rama remota
git push origin feature/build-system-single-source-of-truth
```

---

## 📚 **DOCUMENTACIÓN ACTUALIZADA**

### **1. DAY48_SUMMARY.md** ✅
```markdown
# DÍA 48: REFACTORIZACIÓN DEL SISTEMA DE CONSTRUCCIÓN

## 🎯 OBJETIVO ALCANZADO
Establecer el Makefile raíz como **Single Source of Truth** para el sistema de construcción.

## 🔧 PROBLEMAS RESUELTOS
- **Conflictos de flags**: Eliminados flags hardcodeados en 9 CMakeLists.txt
- **Consistencia**: Configuraciones uniformes en todos los perfiles
- **Dependencias obsoletas**: Eliminadas referencias a Docker/docker-compose
- **Distribución Protobuf**: Corregido para builds con perfiles específicos

## 🏗️ ARQUITECTURA DEL NUEVO SISTEMA

### **Jerarquía de Configuración:**
```
Makefile (raíz) → Flags de compilación → CMake → Binarios
↓
Perfiles:
- production: -O3 -flto -DNDEBUG
- debug: -g -O0 -DDEBUG
- tsan: -fsanitize=thread
- asan: -fsanitize=address
```

### **Validación de Perfiles:**
| Perfil | Tamaño | Optimización | Sanitizer | Status |
|--------|--------|--------------|-----------|--------|
| production | 1.4M | -O3 -flto | None | ✅ |
| debug | 17M | -O0 | None | ✅ |
| tsan | 23M | -O1 | ThreadSanitizer v2 | ✅ |
| asan | ~25M | -O1 | AddressSanitizer | ✅ |

## 📊 MÉTRICAS DE CALIDAD

### **Eficiencia de Tamaño:**
- **Reducción del 91%** en producción vs debug
- **Compresión LTO**: Optimización de enlace completo
- **Flags consistentes**: Mismo set en todos los componentes

### **Validación Sanitizadores:**
- **TSAN**: ThreadSanitizer activo y funcional
- **ASAN**: AddressSanitizer listo para pruebas
- **Aislamiento**: Build directories separados por perfil

## 🛠️ COMPONENTES REFACTORIZADOS (9/9)
1. ✅ ml-detector
2. ✅ sniffer
3. ✅ rag-ingester
4. ✅ common-rag-ingester
5. ✅ firewall-acl-agent
6. ✅ etcd-server
7. ✅ tools
8. ✅ crypto-transport
9. ✅ etcd-client

## 🧪 PRUEBAS REALIZADAS
```bash
# Builds exitosos en todos los perfiles
make PROFILE=production all
make PROFILE=debug all
make PROFILE=tsan all
make PROFILE=asan all

# Clean operations específicas
make clean-production
make clean-tsan
```

## 🔄 FLUJO DE TRABAJO HABILITADO
```bash
# Desarrollo diario
make PROFILE=debug sniffer
make PROFILE=debug test

# Testing de concurrencia
make PROFILE=tsan all
./build-tsan/tests/concurrency_test

# Producción
make PROFILE=production all
strip build-production/bin/*
```

## 🎨 CALIDAD VIA APPIA
- ✅ **Basado en evidencia**: Tamaños medidos, sanitizadores validados
- ✅ **Refactorización sistemática**: Patrón idéntico en 9 archivos
- ✅ **Fundamentos sólidos**: Sistema de construcción predecible
- ✅ **Multiplataforma**: Testeado en macOS → Vagrant → Ubuntu 22.04

## 📈 IMPACTO EN EL PIPELINE ML-DEFENDER
```
ANTES:
├── Flags inconsistentes
├── Builds no reproducibles
├── Sanitizadores conflictivos
└── Docker dependencies

AHORA:
├── Single Source of Truth ✅
├── 4 perfiles validados ✅
├── Builds aislados por perfil ✅
└── Preparado para producción ✅
```

## 🚀 PRÓXIMOS PASOS
1. **Day 49 Mañana**: Documentación final + integración CI
2. **Day 49 Tarde**: Opcional - stress test de contratos
3. **Day 50+**: Hardening de producción

---

**STATUS: DÍA 48 COMPLETADO EXITOSAMENTE** 🎉
```

### **2. BUILD_SYSTEM.md** ✅
```markdown
# SISTEMA DE CONSTRUCCIÓN - DOCUMENTACIÓN TÉCNICA

## 📋 VISIÓN GENERAL
El sistema de construcción ha sido refactorizado para tener **una única fuente de verdad**: el Makefile raíz. Todos los flags de compilación y configuraciones de perfil se definen ahora en el Makefile y se propagan a CMake.

## 🎭 PERFILES SOPORTADOS

### **1. Production (`PROFILE=production`)**
```makefile
CXXFLAGS = -O3 -march=native -DNDEBUG -flto
```
- **Propósito**: Builds de producción, tamaño optimizado
- **Uso**: Releases, deployments, benchmarks
- **Directorio**: `build-production/`

### **2. Debug (`PROFILE=debug`)**
```makefile
CXXFLAGS = -g -O0 -fno-omit-frame-pointer -DDEBUG
```
- **Propósito**: Desarrollo, debugging con símbolos completos
- **Uso**: Desarrollo diario, troubleshooting
- **Directorio**: `build-debug/`

### **3. TSAN (`PROFILE=tsan`)**
```makefile
CXXFLAGS = -fsanitize=thread -g -O1 -DTSAN_ENABLED
```
- **Propósito**: Detección de race conditions y problemas de concurrencia
- **Uso**: Testing de thread-safety, validación concurrente
- **Directorio**: `build-tsan/`

### **4. ASAN (`PROFILE=asan`)**
```makefile
CXXFLAGS = -fsanitize=address -g -O1 -DASAN_ENABLED
```
- **Propósito**: Detección de memory leaks y buffer overflows
- **Uso**: Validación de seguridad de memoria
- **Directorio**: `build-asan/`

## 🛠️ USO PRÁCTICO

### **Comandos Esenciales:**
```bash
# Build específico de componente con perfil
make PROFILE=production sniffer
make PROFILE=debug ml-detector
make PROFILE=tsan firewall-acl-agent

# Build completo con perfil
make PROFILE=production all
make PROFILE=tsan all

# Limpieza específica por perfil
make clean-production
make clean-tsan

# Limpieza completa (todos los perfiles)
make clean
```

### **Ejemplos de Workflow:**
```bash
# Desarrollo normal
make PROFILE=debug all
./build-debug/bin/sniffer --config config.yaml

# Testing de concurrencia
make PROFILE=tsan all
./build-tsan/tests/concurrency_test --gtest_repeat=10

# Preparación para producción
make PROFILE=production all
strip build-production/bin/*
ls -lh build-production/bin/
```

## 📁 ESTRUCTURA DE DIRECTORIOS
```
ml-defender/
├── Makefile                    # Single Source of Truth
├── CMakeLists.txt             # Configuración raíz CMake
├── build-production/          # Builds de producción
│   ├── bin/
│   ├── lib/
│   └── tests/
├── build-debug/               # Builds de debug
├── build-tsan/                # Builds con ThreadSanitizer
├── build-asan/                # Builds con AddressSanitizer
└── [componentes]/
    └── CMakeLists.txt         # Sin flags hardcodeados
```

## 🔧 INTEGRACIÓN CMAKE

### **Antes (Problema):**
```cmake
# En cada CMakeLists.txt (9 archivos)
set(CMAKE_CXX_FLAGS "-O2 -g -Wall -Wextra -fsanitize=address")
# ↑ Conflictos con Makefile, inconsistencia entre componentes
```

### **Después (Solución):**
```cmake
# Ningún flag hardcodeado en CMakeLists.txt
add_executable(ml-detector src/main.cpp)
target_link_libraries(ml-detector ${LIBRARIES})
# ↑ Flags inyectados por Makefile según perfil
```

## 🧪 VALIDACIÓN Y VERIFICACIÓN

### **Verificación de Perfiles:**
```bash
# Verificar que los sanitizadores estén activos
make PROFILE=tsan ml-detector
ldd build-tsan/bin/ml-detector | grep tsan
# Debe mostrar: libtsan.so

# Verificar optimizaciones
make PROFILE=production ml-detector
objdump -d build-production/bin/ml-detector | head -20
# Debe mostrar instrucciones optimizadas
```

### **Métricas de Validación:**
```bash
# Tamaños esperados por perfil (aproximados)
du -h build-*/bin/ml-detector | sort -h
# 1.4M   build-production/bin/ml-detector
# 17M    build-debug/bin/ml-detector
# 23M    build-tsan/bin/ml-detector
# 25M    build-asan/bin/ml-detector
```

## 🐛 TROUBLESHOOTING

### **Problema: Flags no se aplican**
```bash
# Síntoma: Los bins tienen tamaño similar en todos los perfiles
# Solución:
make clean  # Limpiar todos los builds
make PROFILE=production all  # Rebuild completo
```

### **Problema: Protobuf missing**
```bash
# Síntoma: Error "pb.h: No such file"
# Solución: El Makefile ahora copia automáticamente
# Los archivos generados van a build-PROFILE/protobuf/
```

### **Problema: Dependencias cruzadas**
```bash
# Síntoma: Componentes linkean con versión incorrecta
# Solución: Cada perfil tiene su propio directorio de build
# No hay contaminación entre perfiles
```

## 🚀 MANTENIMIENTO Y EXTENSIÓN

### **Agregar nuevo componente:**
1. Crear `nuevo-componente/CMakeLists.txt` sin flags
2. Agregar target al Makefile raíz
3. El sistema de perfiles se aplica automáticamente

### **Agregar nuevo perfil:**
1. Agregar definición en Makefile:
```makefile
PROFILE_NUEVO_CXX := -flags-especificos
```
2. Agregar reglas de clean:
```makefile
clean-nuevo:
	rm -rf build-nuevo
```
3. Actualizar documentación

## 📊 COMPARACIÓN ANTES/DESPUÉS

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Fuente de verdad** | 9 CMakeLists.txt + Makefile | Solo Makefile |
| **Consistencia** | Conflictos frecuentes | Perfectamente consistente |
| **Reproducibilidad** | Dependía del último editado | Determinista por perfil |
| **Mantenimiento** | Cambiar flags en 10 lugares | Cambiar en 1 lugar |
| **Testing** | Manual por componente | Automático por perfil |

---

## 🎯 BUENAS PRÁCTICAS

### **Para Desarrolladores:**
```bash
# Usar debug para desarrollo diario
make PROFILE=debug all
./build-debug/bin/componente

# Usar tsan antes de commits importantes
make PROFILE=tsan all
./build-tsan/tests/*

# Usar production para benchmarks
make PROFILE=production all
./build-production/bin/componente --benchmark
```

### **Para CI/CD:**
```bash
# Pipeline típico
make PROFILE=debug all && make test
make PROFILE=tsan all && make test
make PROFILE=production all
# Build final: build-production/
```

