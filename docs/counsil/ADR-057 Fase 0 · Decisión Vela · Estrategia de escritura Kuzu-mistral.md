Aquí tienes un análisis estructurado y **adversarial** para cada pregunta, siguiendo la regla de **"medir, no votar"**. Cada respuesta incluye:
1. **Objeción en una frase** (el agujero).
2. **Experimento o métrica concreta** para validarla.
3. **¿Bloqueante para Fase 0 o hardening posterior?**

---

---

### **Q1 — ¿El ×61 transfiere o es artefacto de la VM?**
**Objeción:** El ×61 podría ser un espejismo de la VM (VirtualBox) y no escalar en hardware real.

**Experimento:**
- Ejecutar el mismo benchmark en **hardware real** (SSD NVMe, sin VM) con:
    - `strace -e trace=fsync` para medir el tiempo de `fsync` en **run1** (MERGE/fila) vs **run2** (UNWIND batch).
    - Comparar el **% del tiempo total** dedicado a `fsync` vs. parse/plan en ambos casos.
- **Métrica objetivo:**
    - Si `fsync` > 70% del tiempo en run1 → El ×61 **se encogerá** en hardware real.
    - Si parse/plan > 70% → El ×61 **es estructural** (transfiere).

**Veredicto:** **Bloqueante para Fase 0**.
*Sin esto, la decisión D1 (UNWIND batch) podría ser inválida en producción.*

---

---

### **Q2 — Staleness a bajo caudal**
**Objeción:** El batch de 1000 introduce **5 minutos de staleness** en escenarios de bajo caudal (ej. 3 flows/s), inaceptable para detección de ataques en tiempo real.

**Experimento:**
- **SLO propuesto:** Staleness máxima = **1 segundo** por fuente (requisito típico en NDR para detección de ataques activos).
- **Política de flush:** `flush_interval_ms = 1000` (1 segundo) **O** `batch_size = 100` (lo que se llene primero).
- **Métrica:**
    - Medir **p99 de staleness** (tiempo desde que un flow llega hasta que es consultable) con:
        - `batch_size ∈ {10, 100, 1000}` y `flush_interval_ms ∈ {100, 1000, 5000}`.
        - Carga: **3 flows/s** (simulando madrugada en hospital).
    - **Objetivo:** Encontrar el par `(batch_size, flush_interval_ms)` que cumpla **p99 staleness ≤ 1s** con el menor impacto en throughput.

**Veredicto:** **Bloqueante para Fase 0**.
*Sin garantía de staleness, el sistema no es production-ready para NDR.*

---

---

### **Q3 — Reader real vs. juguete**
**Objeción:** Las métricas de contención (×1.16, ×11.37) se midieron con `count(*)`, no con queries de correlación multi-hop (el caso de uso real de Kuzu).

**Experimento:**
- **Query representativa:**
  ```cypher
  MATCH (a:Flow)-[:BELONGS_TO]->(c:Community)-[:CONTAINS]->(b:Flow)
  WHERE a.timestamp > datetime() - duration('PT5M')
  RETURN a.id, b.id, c.id
  LIMIT 1000;
  ```
  (Traversal de 2 saltos + filtro temporal, típico en correlación de NDR).
- **Métrica:**
    - Ejecutar el smoke con **1 writer (UNWIND batch=1000)** y **4 readers concurrentes** ejecutando la query anterior.
    - Medir:
        - **Throughput de lecturas** (queries/s).
        - **p99 de latencia de lectura** (con y sin writers activos).
    - **Objetivo:** Comparar la contención con la query real vs. `count(*)`.

**Veredicto:** **Bloqueante para Fase 0**.
*Si la contención explota con queries reales, D1 (UNWIND + 1 writer) podría ser inválida.*

---

---

### **Q4 — Memoria a escala real**
**Objeción:** 822 MB para 100k nodos sugiere que **1M nodos ≈ 8 GB**, lo que reventaría una RPi5 (8 GB) y limitaría el N100.

**Experimento:**
- **Curva RSS vs. nodos:**
    - Medir **maxRSS** para grafos de **100k, 500k, 1M, 2M nodos** (con el mismo schema y densidad de aristas).
    - **Métrica:** Ajustar una regresión lineal/logarítmica para predecir el **working set a 10M nodos** (escala real en hospitales grandes).
- **Estrategia de tiering:**
    - Proponer un **umbral de memoria** (ej. 6 GB) para activar el tiering:
        - **Hot:** Nodos/aristas accesados en las últimas **24h** (en Kuzu).
        - **Cold:** Resto, almacenado en **Parquet + DuckDB** (solo lectura, sin Kuzu).
    - **Métrica:** Medir el **% de queries que tocan el tier cold** y el **overhead de migración** (hot ↔ cold).

**Veredicto:** **Hardening posterior (pero crítico para ADR-041)**.
*No bloquea Fase 0, pero sin esto, el sistema no escala en hardware real.*

---

---

### **Q5 — Atomicidad: fallo en batch**
**Objeción:** Un `UNWIND` de 1000 filas es **una transacción atómica**: un flow malformado revienta las 999 buenas.

**Experimento:**
- **Semántica de Kuzu:**
    - Crear un batch con **1 fila válida + 1 fila inválida** (ej. `INSERT` con `NULL` en campo NOT NULL).
    - Verificar si:
        1. **Rollback total:** Ninguna fila se inserta.
        2. **Rollback parcial:** Solo la fila válida se inserta.
    - **Métrica:** Documentar el comportamiento exacto (consultar código fuente de Kuzu o test empírico).
- **Estrategia de quarantine:**
    - Si es **rollback total**, implementar:
        - **Pre-validación:** Filtrar filas malformadas **antes** del `UNWIND`.
        - **Chunking:** Dividir el batch en chunks de **100 filas** (tradeoff: throughput vs. blast radius).
    - **Métrica:** Medir el **% de filas descartadas** y el **overhead de pre-validación**.

**Veredicto:** **Bloqueante para Fase 0**.
*Sin esto, un ataque deliberado podría paralizar el sistema.*

---

---
### **Q6 — Tamaño de batch óptimo**
**Objeción:** `batch_size = 1000` es arbitrario. El óptimo depende de **throughput, staleness, RSS y blast radius**.

**Experimento:**
- **Sweep de batch_size:**
    - Ejecutar el smoke con `batch_size ∈ {1, 10, 100, 1000, 10000}` y `flush_interval_ms = 1000` (para Q2).
    - **Métricas:**
        - **Throughput** (upserts/s).
        - **p99 staleness** (con carga de 3 flows/s).
        - **maxRSS** (memoria).
        - **Blast radius:** % de filas perdidas en caso de fallo (simular con Q5).
    - **Objetivo:** Encontrar el **codo de la curva** (punto donde aumentar `batch_size` ya no mejora throughput pero empeora staleness/memoria).

**Veredicto:** **Bloqueante para Fase 0**.
*Sin esto, el batch_size podría ser subóptimo o peligroso.*

---

---
### **Q7 — Recuperación del WAL**
**Objeción:** Borrar el WAL (`cleanup_db`) **no es recuperación**. El WAL contiene datos commiteados no checkpointed.

**Experimento:**
- **Test de durabilidad:**
    1. Ejecutar el smoke con `batch_size=1000` y **matar el proceso con `SIGKILL`** cada 5 segundos (simulando crash).
    2. Reiniciar Kuzu y ejecutar:
       ```bash
       kuzu --restore-from-wal /path/to/db
       ```
    3. **Métrica:**
        - Verificar que **todos los upserts commiteados antes del SIGKILL** están presentes en la DB recuperada.
        - Medir el **tiempo de recuperación** (debe ser < 10s para producción).
- **Invariante:** El test debe cubrir:
    - Crash **durante** un `UNWIND` (transacción abierta).
    - Crash **entre** batches (transacción cerrada).

**Veredicto:** **Bloqueante para Fase 0**.
*Sin esto, el sistema pierde datos en producción.*

---
---
### **Q8 — Shardability futura**
**Objeción:** Diferir sharding sin prepararlo **hoy** podría hacerla imposible después.

**Experimento:**
- **Invariantes mínimas para sharding:**
    1. **Routing key explícita:**
        - Cada `Flow` debe tener un campo `shard_key` (ej. `hash(community_id) % N_SHARDS`).
        - **Test:** Insertar 10k flows con `shard_key` y verificar que se distribuyen uniformemente.
    2. **Correlador agnóstico:**
        - Las queries de correlación **no pueden asumir grafo único** (ej. usar `UNION ALL` para cruzar shards).
        - **Test:** Ejecutar una query de correlación multi-hop **sobre 2 shards** y verificar que devuelve los mismos resultados que en un grafo único.
- **Métrica:**
    - **Overhead de routing:** Tiempo añadido por calcular `shard_key` vs. grafo único.
    - **Complexidad de queries:** Líneas de código añadidas para soportar sharding.

**Veredicto:** **Hardening posterior (pero crítico para ADR-041)**.
*No bloquea Fase 0, pero sin esto, sharding será una reescritura.*

---
---
### **Q9 — Footgun de 2º Database**
**Objeción:** `DEBT-KUZU-SINGLE-DATABASE-GUARD-001` solo **documenta** el footgun; no lo previene.

**Experimento:**
- **Implementación fail-closed:**
    - Crear un **singleton global** para `Database` con:
      ```cpp
      class DatabaseGuard {
      public:
          DatabaseGuard() {
              if (instance_ != nullptr) {
                  throw std::runtime_error("Multiple Database instances detected");
              }
              instance_ = this;
          }
          ~DatabaseGuard() { instance_ = nullptr; }
      private:
          static inline DatabaseGuard* instance_ = nullptr;
      };
      ```
        - **Test:** Intentar crear un 2º `Database` en el mismo proceso y verificar que **falla con error controlado**.
    - **Métrica:** Tiempo añadido por la verificación (debe ser < 1μs).

**Veredicto:** **Bloqueante para Fase 0**.
*Sin esto, un error humano puede corromper la DB en producción.*

---
---
---
### **Resumen de bloqueantes para Fase 0**
| Pregunta | ¿Bloqueante? | Razón |
|----------|-------------|-------|
| Q1       | ✅ Sí        | El ×61 podría no transferir a hardware real. |
| Q2       | ✅ Sí        | Staleness inaceptable para NDR. |
| Q3       | ✅ Sí        | Contención no medida con queries reales. |
| Q5       | ✅ Sí        | Atomicidad no validada; riesgo de pérdida masiva de datos. |
| Q6       | ✅ Sí        | Batch size no optimizado; riesgo de staleness/memoria. |
| Q7       | ✅ Sí        | Durabilidad no probada; pérdida de datos en crash. |
| Q9       | ✅ Sí        | Footgun no prevenido; corrupción de datos. |
| Q4       | ❌ No        | Memoria es crítico, pero se puede diferir a ADR-041. |
| Q8       | ❌ No        | Sharding se puede preparar después, pero con invariantes hoy. |

---
### **Recomendación final**
**Fase 0 NO puede mergearse hasta resolver Q1, Q2, Q3, Q5, Q6, Q7 y Q9.**
- **Prioridad 1:** Q7 (durabilidad) y Q5 (atomicidad) → **Riesgo de pérdida de datos**.
- **Prioridad 2:** Q1, Q2, Q3 → **Riesgo de rendimiento inaceptable en producción**.
- **Prioridad 3:** Q6 y Q9 → **Riesgo de inestabilidad o corrupción**.

**El smoke actual solo probó el mejor caso. La producción es el peor caso.**

---
**¿Qué experimento o métrica añadirías para desmontar alguna de estas objeciones?**

FDO

MISTRAL