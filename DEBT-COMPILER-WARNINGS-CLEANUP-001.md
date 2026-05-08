# DEBT-COMPILER-WARNINGS-CLEANUP-001 — Plan de Actuación

**Rama:** `feature/variant-b-libpcap`  
**Abierta:** DAY 136  
**Iniciada:** DAY 139 (02-05-2026)  
**Prioridad:** P0 BLOQUEANTE — ningún tag posterior sin resolver  
**Referencia EMECAS:** `protocol-EMECAS-output-02-05-2026.md`  
**Total warnings inventariados:** 192

---

## Regla de cierre

Este debt se considera CERRADO cuando:
1. `make test-all` → 8/8 PASSED con `-Werror` activo en todos los componentes del pipeline
2. ODR verification: rebuild limpio con `-flto=thin -Wodr` sin violations
3. Commit con mensaje `fix: DEBT-COMPILER-WARNINGS-CLEANUP-001 — zero warnings pipeline`

---

## Inventario de warnings (02-05-2026)

| ID | Categoría | Flag | Count | Componentes afectados | Riesgo | Estado |
|----|-----------|------|-------|-----------------------|--------|--------|
| W-01 | Unused parameter `flow` | `-Wunused-parameter` | 51 | sniffer | Cosmético | ⬜ PENDIENTE |
| W-02 | Sign conversion `uint32_t → int32_t` | `-Wsign-conversion` | 23 | multiple | Real — UB potencial | ⬜ PENDIENTE |
| W-03 | Sign conversion `int → long unsigned int` | `-Wsign-conversion` | 13 | multiple | Real — UB potencial | ⬜ PENDIENTE |
| W-04 | Unused parameter `args` | `-Wunused-parameter` | 10 | multiple | Cosmético | ⬜ PENDIENTE |
| W-05 | Conversion `uint64_t → float` | `-Wconversion` | 8 | ml-detector | Real — pérdida precisión | ⬜ PENDIENTE |
| W-06 | libtool `-version-info` ignored | (libtool) | 8 | libraries | Externo, no nuestro | ⬜ IGNORAR |
| W-07 | Switch unreachable statement | `-Wswitch-unreachable` | 7 | multiple | Código muerto | ⬜ PENDIENTE |
| W-08 | Sign conversion `unsigned int → int` | `-Wsign-conversion` | 7 | multiple | Real — UB potencial | ⬜ PENDIENTE |
| W-09 | Conversion `uint32_t → float` | `-Wconversion` | 6 | ml-detector | Real — pérdida precisión | ⬜ PENDIENTE |
| W-10 | Conversion `double → float` | `-Wfloat-conversion` | 6 | multiple | Real — pérdida precisión | ⬜ PENDIENTE |
| W-11 | Reorder (miembro inicializado tarde) | `-Wreorder` | 6 | sniffer, ml-detector | **Real — UB silencioso** | ⬜ PENDIENTE |
| W-12 | Reorder (when initialized here) | `-Wreorder` | 6 | sniffer, ml-detector | **Real — UB silencioso** | ⬜ PENDIENTE |
| W-13 | Conversion `vector::size_type → int` | `-Wconversion` | 5 | rag-ingester | Real — pérdida precisión | ⬜ PENDIENTE |
| W-14 | Sign conversion `size_t → int` | `-Wsign-conversion` | 3 | multiple | Real — UB potencial | ⬜ PENDIENTE |
| W-15 | OpenSSL SHA256 deprecated | `-Wdeprecated-declarations` | 3 | crypto-transport | **Real — bloqueante OpenSSL 4** | ⬜ PENDIENTE |
| W-16 | Unused parameter `req` | `-Wunused-parameter` | 2 | multiple | Cosmético | ⬜ PENDIENTE |
| W-17 | Sign conversion `chrono::rep → uint64_t` | `-Wsign-conversion` | 2 | multiple | Real — UB potencial | ⬜ PENDIENTE |
| W-18 | Conversion `vector::size_type → streamsize` | `-Wsign-conversion` | 2 | multiple | Real | ⬜ PENDIENTE |
| W-19 | Conversion `string::size_type → streamsize` | `-Wsign-conversion` | 2 | multiple | Real | ⬜ PENDIENTE |
| W-20 | Unsigned >= 0 always true | `-Wtype-limits` | 2 | multiple | Lógica dudosa | ⬜ PENDIENTE |
| W-21 | Variable set but not used `f2` | `-Wunused-but-set-variable` | 1 | multiple | Cosmético | ⬜ PENDIENTE |
| W-22 | Unused variable `nf` | `-Wunused-variable` | 1 | multiple | Cosmético | ⬜ PENDIENTE |
| W-23 | Unused parameter `index` | `-Wunused-parameter` | 1 | multiple | Cosmético | ⬜ PENDIENTE |

---

## Orden de ataque (prioridad por riesgo real)

### FASE 1 — UB silencioso (atacar primero)
**Objetivo:** Eliminar comportamiento indefinido silencioso antes de añadir `-Werror`

- [ ] **TAREA-01:** `-Wreorder` — `RingBufferConsumer`, `DualNICManager`, `ZMQHandler`  
  Reordenar declaraciones de miembros en headers para que coincidan con el orden del constructor  
  _Estimación: 30 min | 12 instancias_

### FASE 2 — API deprecated (bloquea futuro)
- [ ] **TAREA-02:** `-Wdeprecated-declarations` OpenSSL SHA256  
  Migrar `SHA256_Init/Update/Final` → `EVP_DigestInit_ex/Update/Final_ex`  
  _Estimación: 1h | 3 instancias en crypto-transport_

### FASE 3 — Conversiones de signo y precisión
- [ ] **TAREA-03:** `-Wsign-conversion` sistemático (52 instancias)  
  Auditar cada cast: añadir `static_cast` explícito o corregir tipo en origen  
  _Estimación: 2-3h_

- [ ] **TAREA-04:** `-Wconversion` / `-Wfloat-conversion` (20 instancias)  
  `static_cast<float>()` explícito donde la pérdida de precisión es aceptada  
  _Estimación: 1h_

- [ ] **TAREA-05:** `-Wtype-limits` unsigned >= 0 (2 instancias)  
  Eliminar comparación sin sentido o cambiar tipo  
  _Estimación: 15 min_

### FASE 4 — Código muerto
- [ ] **TAREA-06:** `-Wswitch-unreachable` (7 instancias)  
  Eliminar `return`/`break` antes de código inalcanzable  
  _Estimación: 30 min_

### FASE 5 — ODR verification (requiere LTO)
- [ ] **TAREA-07:** Rebuild con `-flto=thin -Wodr`  
  Verificar que no hay ODR violations ocultas entre `sniffer` y `ml-detector`  
  Diagnóstico: `nm -C` en ambos binarios + linker con LTO activo  
  _Estimación: 1h_

### FASE 6 — Activar `-Werror` en CMakeLists
- [ ] **TAREA-08:** Añadir `-Werror` a todos los `CMakeLists.txt` del pipeline  
  Hacer la limpieza permanente — cualquier warning futuro rompe la build  
  _Estimación: 30 min_

### FASE 7 — Cosmético (último)
- [ ] **TAREA-09:** `-Wunused-parameter` (64 instancias)  
  Añadir `[[maybe_unused]]` o `(void)param;` donde el parámetro es requerido por firma  
  _Estimación: 1-2h_

---

## Log de progreso

| Fecha | DAY | Tarea | Resultado | Commit |
|-------|-----|-------|-----------|--------|
| 02-05-2026 | 139 | Inventario completo (192 warnings categorizados) | ✅ | — |

---

## Notas técnicas

**Por qué `-Wreorder` es UB:**  
El estándar C++ garantiza que los miembros se inicializan en el **orden de declaración en la clase**, no en el orden del constructor initializer list. Si el initializer list usa un orden diferente, el compilador lo ejecuta en orden de declaración igualmente — pero el código parece que hace otra cosa. Si un miembro depende de otro, el resultado es UB silencioso.

**Por qué OpenSSL SHA256 deprecated es bloqueante:**  
`SHA256_Init/Update/Final` son la API de bajo nivel de OpenSSL. Marcadas deprecated en OpenSSL 3.0, eliminación planificada en OpenSSL 4.x. La API de reemplazo es `EVP_DigestInit_ex2` (OpenSSL 3.0+). Los hospitales con Debian 12+ ya tienen OpenSSL 3.x — la deprecation es real ahora.

**ODR y LTO:**  
Las ODR violations no generan warnings con compilación normal. Requieren Link-Time Optimization (`-flto`) que permite al linker ver todas las translation units simultáneamente. La flag `-Wodr` activa el warning específico. Sin esto, una ODR violation es UB silencioso que puede manifestarse como crashes intermitentes en producción.

**Libtool warnings (W-06):**  
`'-version-info/-version-number' is ignored for convenience libraries` — este warning lo genera libtool al compilar `.a` (static) en lugar de `.so` (shared). No es código nuestro. Ignorar.
