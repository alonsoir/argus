# ADR-037 — Static Analysis Security Hardening: safe_path utility

**Status:** PROPOSED — pendiente veredicto Consejo de Sabios  
**Date:** 2026-04-20 (DAY 123)  
**Author:** Alonso Isidoro Roman  
**Reviewer:** Consejo de Sabios (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai)  
**Branch destino:** `feature/adr037-snyk-hardening`  
**Bloqueante para:** ADR-036 (Formal Verification Baseline)  
**Trigger:** Snyk static analysis pass sobre commit `e88e4bf8` (main, DAY 122)

---

## 1. Contexto

Se realizó un análisis estático con Snyk sobre las fuentes C++ de aRGus NDR en el estado
`v0.5.0-preproduction`. El análisis produjo 17 findings de severidad media. No se
identificaron findings críticos.

El presente ADR documenta:
- La clasificación real de los findings por superficie de ataque
- El rechazo razonado de las fixes sugeridas por Snyk
- La solución propia propuesta: `safe_path` utility, header-only, cero dependencias
- El plan de implementación y el gate de cierre

El código Python de entrenamiento (`train_xgboost_level1_v2.py` y similares) queda
**fuera del scope** de este ADR: no forma parte de la superficie binaria monitorizada
por AppArmor/Falco en producción.

---

## 2. Análisis de findings

### 2.1 Clasificación por superficie de ataque

Los 17 findings se agrupan en tres categorías con riesgo real muy distinto:

#### 🔴 Categoría A — Producción (bloqueante para ADR-036)

Binarios que corren bajo AppArmor en producción y reciben paths desde entrada externa
(argv o JSON de configuración).

| ID Snyk | Archivo | Línea | Tipo | Descripción |
|---------|---------|-------|------|-------------|
| F12 | `firewall-acl-agent/src/main.cpp` | 273 | Path Traversal | `config_path` desde argv → `ConfigLoader::load_from_file()` |
| F14a | `firewall-acl-agent/src/core/config_loader.cpp` | 80 | Path Traversal | `std::ifstream file(config_path)` sin sanitizar |
| F13 | `libs/seed-client/src/seed_client.cpp` | 99 | Path Traversal | `seed_path` derivado de JSON → `std::ifstream seed_file` — **material criptográfico** |
| F15a | `libs/seed-client/src/seed_client.cpp` | 93-99 | Path Traversal | Mismo flujo, segunda instancia detectada |
| F14b | `rag-ingester/src/common/config_parser.cpp` | 9 | Path Traversal | `std::ifstream file(config_path)` desde argv |
| F15b | `rag-ingester/src/main.cpp` | 120 | Path Traversal | `ConfigParser::load(config_path)` desde argv |
| F17 | `ml-detector/src/zmq_handler.cpp` | 988 | Integer Overflow | `pages * page_size` — ambos `long`, producto puede desbordar en sistemas con >2TB RAM |

**Nota especial F13/F15a:** `seed_client.cpp` maneja material criptográfico (`seed.bin`).
Cualquier path traversal aquí no es solo una escritura arbitraria — es potencial
exfiltración o corrupción de la seed ChaCha20. Prioridad máxima dentro de esta categoría.

#### 🟡 Categoría B — contrib/ y tools/ (no bloqueante, se cierra en el mismo PR)

Scripts de investigación y entrenamiento. No corren bajo AppArmor. Input controlado
por el investigador en entorno sandbox.

| IDs | Archivos afectados | Tipo |
|-----|--------------------|------|
| F1, F2, F3 | `contrib/ds/pca_pipeline/synthetic_data_generator.cpp` | Path Traversal |
| F4, F5 | `contrib/grok/pca_pipeline/train_pca_pipeline.cpp` | Path Traversal |
| F8 | `contrib/ds/pca_pipeline/train_pca_pipeline.cpp` | Path Traversal |
| F9 | `contrib/grok/pca_pipeline/synthetic_data_generator.cpp` | Path Traversal |
| F10 | (jsonl writer, contrib) | Path Traversal |
| F11 | `contrib/qwen/pca_pipeline/train_pca_pipeline.cpp` | Path Traversal |
| F6 | `tools/generate_synthetic_events.cpp` | Path Traversal |
| F7 | `tools/` (spec_file writer) | Path Traversal |
| contrib overflow | `contrib/glm/pca_pipeline/synthetic_data_generator.cpp` | Integer Overflow |

#### 🟢 Categoría C — Falsos positivos documentados

| IDs | Archivos | Análisis |
|-----|---------|---------|
| F15-inotify, F16 | `rag-ingester/src/csv_dir_watcher.cpp:168`, `csv_file_watcher.cpp:112` | `n` procede de `read()` acotado por `BUF_SIZE = 4096`. `ptr < buf + n` no puede desbordar. Snyk no traza el origen de `n` hasta su acotación. **FP documentado, no se toca el código.** |

---

## 3. Rechazo de las fixes sugeridas por Snyk

Snyk propone tres alternativas externas para todos los path traversal:

| Librería sugerida | Peso estimado | Mantenimiento | Problema |
|-------------------|--------------|---------------|---------|
| `aws_fopen` (aws-c-compression) | SDK AWS completo | AWS (activo) | Dependencia masiva. Introduce superficie de ataque >= a la que pretende cerrar. |
| `QUtil::safe_fopen` (qpdf) | ~500KB | qpdf team | Librería PDF. Semánticamente incorrecta para un NDR. |
| `utility::filesystem::FOpen` (Open3D) | ~50MB build | Intel ISL | Librería 3D. Absolutamente fuera de contexto. |

**Veredicto:** Las tres propuestas violan el principio de minimización de superficie de
control del pipeline. Introducen dependencias externas de tamaño y propósito
desproporcionados para resolver un problema que C++20 resuelve nativamente con
`std::filesystem::weakly_canonical` en ~10 líneas.

**Decisión de diseño:** implementación propia en `contrib/safe-path/`.

---

## 4. Solución propuesta: `safe_path` utility

### 4.1 Estructura

```
contrib/safe-path/
  include/
    safe_path/
      safe_path.hpp       ← header-only, cero dependencias externas
  tests/
    test_safe_path.cpp    ← Google Test, gate de cierre
  CMakeLists.txt
  README.md
```

### 4.2 Implementación propuesta

```cpp
// contrib/safe-path/include/safe_path/safe_path.hpp
#pragma once

#include <filesystem>
#include <stdexcept>
#include <string>

namespace argus::safe_path {

/**
 * Resuelve y valida un path de entrada contra un prefijo permitido.
 *
 * Usa std::filesystem::weakly_canonical para resolver symlinks y
 * componentes ".." sin requerir que el path exista previamente.
 * Lanza std::runtime_error si el path resuelto no tiene el prefijo
 * esperado — previene path traversal (CWE-23).
 *
 * @param path           Path de entrada (puede venir de argv o config JSON)
 * @param allowed_prefix Prefijo canónico permitido (ej. "/etc/ml-defender/")
 * @returns              String del path canónico validado
 * @throws std::runtime_error si el path no está bajo allowed_prefix
 */
[[nodiscard]] inline std::string resolve(
    const std::string& path,
    const std::string& allowed_prefix)
{
    namespace fs = std::filesystem;
    const auto canonical = fs::weakly_canonical(fs::path(path)).string();
    if (canonical.rfind(allowed_prefix, 0) != 0) {
        throw std::runtime_error(
            "[safe_path] Path traversal rejected: '" + path +
            "' resolves to '" + canonical +
            "' outside allowed prefix '" + allowed_prefix + "'");
    }
    return canonical;
}

/**
 * Variante para paths de escritura: adicionalmente verifica que el
 * directorio padre exista y sea escribible por el proceso actual.
 *
 * @throws std::runtime_error si el directorio padre no existe o no es escribible
 */
[[nodiscard]] inline std::string resolve_writable(
    const std::string& path,
    const std::string& allowed_prefix)
{
    const auto resolved = resolve(path, allowed_prefix);
    namespace fs = std::filesystem;
    const auto parent = fs::path(resolved).parent_path();
    if (!fs::is_directory(parent)) {
        throw std::runtime_error(
            "[safe_path] Parent directory does not exist: " + parent.string());
    }
    return resolved;
}

} // namespace argus::safe_path
```

### 4.3 Uso en producción

**Antes (vulnerable):**
```cpp
std::ifstream seed_file(seed_path, std::ios::binary);
```

**Después (seguro):**
```cpp
#include <safe_path/safe_path.hpp>

const auto safe = argus::safe_path::resolve(seed_path, "/etc/ml-defender/keys/");
std::ifstream seed_file(safe, std::ios::binary);
```

**Antes (vulnerable):**
```cpp
std::ifstream file(config_path);
```

**Después (seguro):**
```cpp
const auto safe = argus::safe_path::resolve(config_path, "/etc/ml-defender/");
std::ifstream file(safe);
```

### 4.4 Prefijos permitidos por componente

| Componente | Prefijo read | Prefijo write |
|-----------|-------------|--------------|
| `seed-client` | `/etc/ml-defender/keys/` | — (solo lectura) |
| `firewall-acl-agent` config | `/etc/ml-defender/` | — |
| `rag-ingester` config | `/etc/ml-defender/` | — |
| `tools/` output | `/vagrant/` o `/shared/` | `/vagrant/` o `/shared/` |
| `contrib/` output | `/shared/` | `/shared/` |

---

## 5. Fix del Integer Overflow F17

```cpp
// zmq_handler.cpp:988 — ANTES
long pages = 0;
long page_size = sysconf(_SC_PAGESIZE);
current_memory_mb_.store((pages * page_size) / (1024.0 * 1024.0));

// DESPUÉS — cast explícito a int64_t antes de multiplicar
long pages = 0;
long page_size = sysconf(_SC_PAGESIZE);
const auto mem_bytes = static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
current_memory_mb_.store(static_cast<double>(mem_bytes) / (1024.0 * 1024.0));
```

El overflow en `contrib/glm/` (`samples * dimensions`) se corrige igual:
```cpp
data.reserve(static_cast<size_t>(config.samples) * static_cast<size_t>(config.dimensions));
```

---

## 6. Tests de cierre

`test_safe_path.cpp` debe cubrir como mínimo:

1. Path normal dentro del prefijo → resuelve correctamente
2. Path con `../..` que escapa el prefijo → lanza `std::runtime_error`
3. Path con symlink que apunta fuera del prefijo → rechazado
4. Path vacío → rechazado
5. Prefijo con trailing slash vs sin él → consistente en ambos casos
6. `resolve_writable` con directorio padre inexistente → lanza error

Gate: **todos los tests PASSED** + segunda pasada Snyk con **0 findings en código de producción**.

---

## 7. Plan de implementación

```
PASO 1 — crear contrib/safe-path/ (header + CMakeLists + tests)
PASO 2 — aplicar safe_path::resolve() en los 5 findings de producción:
          seed-client, firewall-acl-agent, rag-ingester
PASO 3 — fix F17 integer overflow en zmq_handler.cpp
PASO 4 — aplicar safe_path::resolve() en contrib/ y tools/ (Categoría B)
PASO 5 — make test-all VERDE
PASO 6 — segunda pasada Snyk → 0 findings producción
PASO 7 — documentar FP inotify en este ADR
PASO 8 — merge a main, tag v0.5.1-hardened
```

---

## 8. Deudas técnicas generadas

Ninguna nueva. Este ADR cierra deuda existente.

La nueva `contrib/safe-path/` pasa a ser superficie mantenida del proyecto.
Cualquier nuevo uso de `std::ifstream`/`std::ofstream` con input externo en código
de producción **debe** usar `argus::safe_path::resolve()`. Se añade como regla
permanente al checklist de code review.

---

## 9. Preguntas al Consejo

1. **¿`weakly_canonical` es suficiente o se prefiere `canonical`?**
   `canonical` requiere que el path exista; `weakly_canonical` funciona también con
   paths de escritura a ficheros aún no creados. ¿Hay objeción a `weakly_canonical`
   para los casos de escritura?

2. **¿La granularidad de prefijos por componente es correcta?**
   ¿Se debe usar un prefijo único `/etc/ml-defender/` para todos los componentes de
   producción, o la separación por componente (`/keys/`, etc.) es preferible?

3. **¿Contrib/ y tools/ merecen el mismo `safe_path` o un nivel de restricción menor?**
   Propuesta: mismo header, pero con prefijo `/shared/` o `/vagrant/` según entorno.
   ¿Consenso?

4. **¿Se acepta el veredicto de FP sobre los findings inotify (F15/F16)?**
   La acotación de `n` por `BUF_SIZE = 4096` hace imposible el overflow. ¿Alguien
   ve un vector de ataque que invalide este análisis?

---

## 10. Decisión requerida

**Veredicto solicitado: Sí/No + comentarios sobre cada pregunta**

Gate de merge: 7/7 o mayoría simple con ningún voto en contra explícito sobre
la decisión de no usar librerías externas.

---

*"Via Appia Quality — la superficie mínima es la superficie más segura."*