cat > /Users/aironman/CLionProjects/test-zeromq-docker/docs/security/SNYK-DAY-128.md << 'EOF'
# Snyk Security Audit — DAY 128

**Tag analizado:** `v0.5.2-hardened`  
**Repositorio:** `alonsoir/argus`  
**Fecha:** 2026-04-24  
**Criterio de triage:** Consejo 8/8 DAY 127

---

## Criterio de clasificación

| Categoría | Acción |
|-----------|--------|
| Código propio + path/overflow/crypto | Fix bloqueante RED→GREEN |
| Código propio + otro HIGH | Fix próximo sprint |
| Third-party no alcanzable | Documentar con justificación |
| Falso positivo demostrable | Cerrar con justificación |

---

## CWE-23 — Relative Path Traversal

### Finding 1 — `libs/seed-client/src/seed_client.cpp:103` — FALSO POSITIVO ✅ CERRADO

```cpp
std::ifstream seed_file(seed_path, std::ios::binary);
```

**Justificación:** El `seed_path` ya ha sido validado por `resolve_seed()` en la línea 98
(4 líneas antes). `resolve_seed()` enforza prefix, lstat(), O_NOFOLLOW, permisos 0400.
Snyk no traza la validación previa. Falso positivo demostrable — ver ADR-037.

---

### Finding 2 — `tools/generate_synthetic_events.cpp:784` — THIRD-PARTY/TOOL ⏳ NO BLOQUEANTE

```cpp
std::ofstream spec_file(spec_path);
```

**Justificación:** `generate_synthetic_events` es una herramienta de desarrollo/lab,
no código de producción del pipeline. No se despliega en entornos críticos.
No alcanzable desde la superficie de ataque real. Documentado, no requiere fix.

---

### Finding 3 — `contrib/ds/pca_pipeline/synthetic_data_generator.cpp:122` — CONTRIB ⏳ NO BLOQUEANTE

```cpp
std::ofstream file(filename, std::ios::binary);
```

**Justificación:** Código en `contrib/` — herramientas de investigación/entrenamiento,
no pipeline de producción. No se despliega en hospitales/municipios. No bloqueante.

---

### Finding 4 — `contrib/ds/pca_pipeline/synthetic_data_generator.cpp:156` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Mismo componente que Finding 3. Ver justificación anterior.

---

### Finding 5 — `contrib/grok/pca_pipeline/train_pca_pipeline.cpp:118` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de entrenamiento. No pipeline de producción.

---

### Finding 6 — `contrib/grok/pca_pipeline/train_pca_pipeline.cpp:24` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de entrenamiento. No pipeline de producción.

---

### Finding 7 — `tools/generate_synthetic_events.cpp:532` — TOOL ⏳ NO BLOQUEANTE

```cpp
std::ifstream config_file(config_path);
```

**Justificación:** config_path viene de argv[3] con default hardcodeado. Herramienta
de lab, no producción. No alcanzable desde superficie de ataque real.

---

### Finding 8 — `libs/seed-client/src/seed_client.cpp:98` — FALSO POSITIVO ✅ CERRADO

```cpp
const int seed_fd = argus::safe_path::resolve_seed(seed_path, keys_dir_);
```

**Justificación:** Esta ES la validación — `resolve_seed()` es precisamente la defensa
contra path traversal. Snyk flagea la llamada sin entender que es la primitiva segura.
Falso positivo documentado en ADR-037.

---

### Finding 9 — `contrib/grok/pca_pipeline/synthetic_data_generator.cpp:74` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de generación sintética. No pipeline de producción.

---

### Finding 10 — `contrib/qwen/pca_pipeline/synthetic_data_generator.cpp:93` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de generación sintética. No pipeline de producción.

---

### Finding 11 — `contrib/ds/pca_pipeline/train_pca_pipeline.cpp:111` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de entrenamiento. No pipeline de producción.

---

### Finding 12 — `contrib/qwen/pca_pipeline/train_pca_pipeline.cpp:24` — CONTRIB ⏳ NO BLOQUEANTE

**Justificación:** Código `contrib/` de entrenamiento. No pipeline de producción.

---

### Finding 13 — `firewall-acl-agent/src/main.cpp:273` — CÓDIGO PROPIO, ANALIZAR 🔍

```cpp
config = ConfigLoader::load_from_file(config_path);
```

**Análisis:** `config_path` viene de argv o config. Verificar si pasa por
`resolve_config()` antes de llegar aquí. Si no → DEBT bloqueante.
**Acción:** Inspeccionar `ConfigLoader::load_from_file()` — si usa `resolve_config()`
internamente, es falso positivo. Si no, añadir validación.
**Estado:** PENDIENTE verificación → ver DEBT-FIREWALL-CONFIG-PATH-001 abajo.

---

### Finding 14 — `rag-ingester/src/main.cpp:120` — CÓDIGO PROPIO, ANALIZAR 🔍

```cpp
auto config = rag_ingester::ConfigParser::load(config_path);
```

**Análisis:** Igual que Finding 13. `ConfigParser::load()` ya tiene tests de traversal
(test_config_parser_traversal — PASSED en DAY 128). Verificar si usa `resolve_config()`.
**Estado:** PENDIENTE verificación → probable falso positivo dado que test pasa.

---

## CWE-190 — Integer Overflow

### Finding 15 — `rag-ingester/src/csv_dir_watcher.cpp:171` — FALSO POSITIVO ✅ CERRADO

```cpp
while (ptr < buf + n) {
```

**Justificación:** Documentado como F15 en el propio código con comentario explícito:
"SAFE: n <= BUF_SIZE = 4096 garantizado por POSIX read(). ptr < buf + n nunca desborda.
Snyk no traza acotación de read() → BUF_SIZE." Falso positivo ya documentado ADR-037.

---

### Finding 16 — `rag-ingester/src/csv_file_watcher.cpp:112` — FALSO POSITIVO ✅ CERRADO

```cpp
ev = reinterpret_cast<const inotify_event*>(buf + i);
```

**Justificación:** Patrón estándar inotify POSIX. `i` está acotado por el tamaño del
buffer. Snyk no traza la acotación del loop inotify. Falso positivo.

---

### Finding 17 — `contrib/glm/pca_pipeline/synthetic_data_generator.cpp:63` — CONTRIB ⏳ NO BLOQUEANTE

```cpp
data.reserve(config.samples * config.dimensions);
```

**Justificación:** Código `contrib/` de generación sintética. Potencial overflow real
si config.samples * config.dimensions supera SIZE_MAX, pero no es código de producción.
Documentado para cuando este código sea promovido a producción.

---

## CWE-78 — OS Command Injection

### Finding 18 — `firewall-acl-agent/src/core/iptables_wrapper.cpp:625` — CÓDIGO PROPIO HIGH 🔴

```cpp
execute_command(cmd);
```

**Análisis:** `IPTablesWrapper::cleanup_rules()` fue identificado por Snyk en DAY 115
(23 vulnerabilidades C++ medium). Este es el más crítico — command injection en
iptables wrapper. `cmd` podría contener input no sanitizado.

**Acción:** Fix bloqueante RED→GREEN en próximo sprint.
**Deuda:** DEBT-IPTABLES-INJECTION-001 — ver sección deudas nuevas.

---

## Resumen de clasificación

| # | Fichero | CWE | Clasificación | Acción |
|---|---------|-----|---------------|--------|
| 1 | seed_client.cpp:103 | CWE-23 | Falso positivo | Cerrado |
| 2 | generate_synthetic_events.cpp:784 | CWE-23 | Tool/no prod | No bloqueante |
| 3-6 | contrib/ds,grok/... | CWE-23 | Contrib/no prod | No bloqueante |
| 7 | generate_synthetic_events.cpp:532 | CWE-23 | Tool/no prod | No bloqueante |
| 8 | seed_client.cpp:98 | CWE-23 | Falso positivo | Cerrado |
| 9-12 | contrib/grok,qwen,ds/... | CWE-23 | Contrib/no prod | No bloqueante |
| 13 | firewall-acl-agent/main.cpp:273 | CWE-23 | Pendiente verificación | DEBT-FIREWALL-CONFIG-PATH-001 |
| 14 | rag-ingester/main.cpp:120 | CWE-23 | Probable falso positivo | Verificar |
| 15 | csv_dir_watcher.cpp:171 | CWE-190 | Falso positivo doc. | Cerrado (F15/ADR-037) |
| 16 | csv_file_watcher.cpp:112 | CWE-190 | Falso positivo | Cerrado |
| 17 | contrib/glm/... | CWE-190 | Contrib/no prod | No bloqueante |
| 18 | iptables_wrapper.cpp:625 | CWE-78 | Código propio HIGH | DEBT-IPTABLES-INJECTION-001 |

---

## Deudas nuevas generadas
DEBT-IPTABLES-INJECTION-001   CWE-78, HIGH — execute_command() en iptables_wrapper
Fix bloqueante RED→GREEN, próximo sprint
DEBT-FIREWALL-CONFIG-PATH-001 CWE-23 — verificar resolve_config() en ConfigLoader
Probable falso positivo, verificar en próximo sprint
