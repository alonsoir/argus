Aquí tienes la **síntesis accionable y priorizada** para avanzar con **ADR-057 v2**, basada en el consenso del Consejo y las correcciones identificadas. Organizado para que puedas **implementar, medir y desbloquear Fase 0** sin ambigüedades.

---

---

---

## **📌 RESUMEN EJECUTIVO (TL;DR para el equipo)**
1. **✅ Gate A (Schema/Ingest):**
    - **YA VERDE.** El commit de schema (`ingested_at`, `temporal_anomaly`, `cypher_builder`) **no está bloqueado** por Q1–Q9.
    - **Acción:** Mergear **inmediatamente** (sin esperar a Gate B).

2. **❌ Gate B (Sink de Producción):**
    - **Bloqueado por 5 experimentos obligatorios** (B1–B5).
    - **No es un debate teórico:** Cada bloqueante tiene un **experimento concreto + métrica numérica** para zanjarlo.
    - **Objetivo:** Validar que **"UNWIND batch + 1 writer" es production-ready** para NDR en infra crítica.

3. **🔧 Guardas NOW (coste bajo, implementar YA):**
    - Capar `bufferPoolSize` en init (Q4).
    - Añadir `getRoutingKey()` explícito en eventos (Q8).
    - Usar `DatabaseRegistry` (no singleton) para Q9 (resuelve Q9 + prepara Q8).

4. **📊 Hardening (Fase 1 / ADR-041):**
    - Q1 (descomposición fsync/parse en N100).
    - Q4 (curva RSS + tiering hot→cold).
    - Q6 (sweep de `batch_size` óptimo).

5. **🆕 Nuevo backlog:**
    - **DEBT-KUZU-BATCH-POISON-001** (bisección recursiva ante fallos en batch).
    - **DEBT-INGEST-BACKPRESSURE-001** (política de cola acotada para floods).

---

---

---

## **🚨 BATERÍA PRE-MERGE DEL SINK (Gate B)**
**Orden de prioridad (de mayor a menor riesgo para producción):**

| ID  | Pregunta | Acción Concreta                                                                                     | Métrica Objetivo                                                                                     | Debt Associated               | ¿Bloqueante? |
|-----|----------|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|--------------------------------|--------------|
| **B1** | Q7 (WAL)       | Eliminar `cleanup_db` del path de producción. Implementar `restore_from_wal_smoke_test`: riada → `kill -9` → reabrir **sin borrar** → replay WAL. | **0 commits ackeados perdidos** tras ≥100 SIGKILLs; recuperación ≤5s para 100k nodos.               | DEBT-LABEL-WAL-001            | ✅ **Sí**      |
| **B2** | Q5 (Poison)   | Confirmar rollback total en UNWIND. Implementar **bisección recursiva** (batch→/2→/2… hasta aislar fila tóxica) + validación en borde ANTES del UNWIND. | **0% pérdida de detecciones legítimas**; overhead ≤10%.                                             | DEBT-KUZU-BATCH-POISON-001    | ✅ **Sí**      |
| **B3** | Q9 (Footgun)  | Implementar `DatabaseRegistry` (map `path→weak_ptr<Database>`). Construcción fuera del registry = imposible; 2º `open()` del mismo path **lanza error**. | Test `EXPECT_THROW` en 2ª apertura del mismo path; coste <1µs.                                      | DEBT-KUZU-SINGLE-DATABASE-GUARD-001 | ✅ **Sí**      |
| **B4** | Q2 (Staleness)| Implementar `flush(size>=N OR age>=T_ms)` con hilo `Ticker` asíncrono. Medir staleness e2e (paquete→consultable). | **SLO p99 staleness ≤1s** (estándar) o ≤100ms (crítico); degradación throughput ≤15%.               | DEBT-KUZU-WRITE-BATCHING-001   | ✅ **Sí**      |
| **B5** | Q3 (Reader)   | Sustituir `count(*)` por **traversal de correlación canónica** (2–3 hops por `community_id`). Remedir contención p50/p99. | **Read p99 ≤5× idle** bajo carga; degradación del writer ≤50%.                                      | DEBT-KUZU-CONCURRENCY-SMOKE-001 | ✅ **Sí**      |

---
**Nota:** Estas 5 acciones **deben completarse y validarse** antes de declarar el sink como production-ready.

---

---

---

## **🛡️ GUARDAS NOW (Implementar INMEDIATAMENTE, coste bajo)**
| ID  | Pregunta | Acción                                                                                     | Métrica/Verificación                                                                 |
|-----|----------|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| G1  | Q4       | **Capar `bufferPoolSize`** en init según RAM del host (ej. `min(RAM/2, 4GB)`).              | Confirmar que RSS **no excede el cap** con 1M nodos.                                  |
| G2  | Q8       | Añadir `getRoutingKey()` explícito en el evento (usar `community_id`).                      | Verificar que el correlador usa `IGraphQuery`/`GraphRepository`, no `kuzu::Connection`. |
| G3  | Q9       | Usar `DatabaseRegistry` (no singleton) para permitir N paths distintos (prepara sharding). | Test: 2 paths distintos → 2 `Database` permitidos; mismo path → error.                |

---
**Objetivo:** Estas guardas **eliminan riesgos críticos** con cambios mínimos y **no bloquean el desarrollo** de B1–B5.

---

---

---

## **📈 HARDENING (Fase 1 / ADR-041)**
**No bloquean Fase 0, pero son críticos para escalar en hardware real (N100/RPi5).**

| ID  | Pregunta | Acción                                                                                     | Métrica Objetiva                                                                                     |
|-----|----------|--------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| H1  | Q1       | Ejecutar benchmark en **N100** (SSD real) con `strace -e trace=fsync` para aislar coste de `fsync` vs. parse/plan. | Si `Δ_fsync > 0.85` → ×61 se encoge en metal (predicción: ~×13); si <0.30 → estructural. |
| H2  | Q4       | Medir **curva RSS vs. nodos** (100k, 500k, 1M, 2M) con `bufferPoolSize` capado.               | Verificar **degradación de latencia por thrashing** (no OOM).                                         |
| H3  | Q6       | **Sweep de `batch_size`**: `{1, 10, 100, 300, 500, 1000, 2500, 5000, 10000}`.               | Encontrar codo donde **Δthroughput <5%** (predicción: ~300–500).                                     |
| H4  | Q8       | Validar que `getRoutingKey()` + `IGraphQuery` permiten **sharding futuro sin reescritura**. | Test: Correlación multi-hop sobre 2 shards → mismos resultados que grafo único.           |

---

---

---
## **🆕 NUEVO BACKLOG (Deudas técnicas identificadas por el Consejo)**
| ID                     | Descripción                                                                                     | Prioridad | Acción Inicial                                                                 |
|------------------------|-------------------------------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------|
| DEBT-KUZU-BATCH-POISON-001 | Implementar bisección recursiva + quarantine ante fallos en batch.                              | Alta      | Diseñar algoritmo de bisección y validación en borde.                          |
| DEBT-INGEST-BACKPRESSURE-001 | Política de **cola acotada** para floods (ej. drop-oldest si producer > writer).                | Alta      | Definir umbrales de cola y métricas de pérdida de eventos.                     |
| DEBT-KUZU-CONCURRENCY-SMOKE-001 | Actualizar smoke para incluir **traversal de correlación real** (no `count(*)`).               | Media     | Implementar query canónica y medir contención.                                |

---

---
---
## **📅 PLAN DE ACCIÓN INMEDIATO (Próximos 15 días)**
### **🔥 Sprint 0: Desbloqueo de Gate B (5 días)**
1. **Día 1–2:**
    - Implementar **B1 (WAL recovery)** y **B3 (`DatabaseRegistry`)**.
    - Validar con `restore_from_wal_smoke_test` (100 SIGKILLs).
2. **Día 3–4:**
    - Implementar **B2 (bisección + validación en borde)** y **B4 (flush-by-time)**.
    - Medir staleness p99 con `flush_interval_ms = 1000`.
3. **Día 5:**
    - Implementar **B5 (reader real)** y validar contención con traversal canónica.
    - **Revisión de Gate B:** Si todos los B1–B5 pasan, el sink es **production-ready para Fase 0**.

### **🛡️ Sprint 1: Guardas NOW (Paralelo, 3 días)**
- Implementar **G1 (capar `bufferPoolSize`)**.
- Añadir **G2 (`getRoutingKey()`)** y **G3 (`DatabaseRegistry`)**.

### **📊 Sprint 2: Hardening (Fase 1, 7 días)**
- Ejecutar **H1 (Q1 en N100)** y **H3 (sweep de batch_size)**.
- Documentar resultados en **ADR-041**.

---
---
## **📝 ACTUALIZACIÓN DE ADR-057 v2**
### **Cambios clave:**
1. **Separar Gate A (Schema) y Gate B (Sink):**
    - Gate A: **Mergeable YA**.
    - Gate B: **Bloqueado por B1–B5**.
2. **Añadir sección "Batería Pre-Merge del Sink":**
    - Listar B1–B5 con acciones, métricas y deudas asociadas.
3. **Añadir "Guardas NOW":**
    - G1–G3 con justificación de bajo coste.
4. **Añadir "Nuevo Backlog":**
    - DEBT-KUZU-BATCH-POISON-001 y DEBT-INGEST-BACKPRESSURE-001.
5. **Clarificar invariantes para sharding (Q8):**
    - `getRoutingKey()` + `IGraphQuery` como **requisitos mínimos** para futuros shards.

---
---
## **⚠️ RIESGOS RESIDUALES (A monitorear)**
| Riesgo                          | Mitigación                                                                                     | Responsable       |
|---------------------------------|------------------------------------------------------------------------------------------------|-------------------|
| Overhead de bisección (B2) >10% | Optimizar validación en borde (ej. usar rust-cypher o precompilar queries).                   | Equipo de backend |
| Thrashing en N100 (H2)          | Tiering hot→cold (Parquet/DuckDB) si RSS > 6GB.                                                | Equipo de infra   |
| Floods sin backpressure (Q10)   | Implementar DEBT-INGEST-BACKPRESSURE-001 en Sprint 2.                                           | Equipo de ingest  |

---
---
---
## **🎯 MÉTRICAS CLAVE PARA DASHBOARD**
| Métrica                          | Objetivo                     | Fuente               |
|----------------------------------|------------------------------|----------------------|
| % commits perdidos tras SIGKILL  | **0%**                       | B1 (WAL recovery)    |
| p99 staleness                    | **≤1s**                      | B4 (flush-by-time)   |
| Read p99 bajo carga              | **≤5× idle**                 | B5 (reader real)     |
| Overhead bisección               | **≤10%**                     | B2 (poison)          |
| RSS con 1M nodos                 | **≤ bufferPoolSize cap**     | G1 (Q4)              |
| Throughput vs. batch_size        | **Codo en ~300–500**         | H3 (Q6)              |

---
---
## **💬 PREGUNTAS ABIERTAS PARA EL CONSEJO**
1. **B4 (Staleness):**
    - ¿Aceptamos **1s como SLO estándar** para NDR, o necesitamos **100ms en modo crítico**?
    - *Propuesta:* Definir **2 modos de operación** (estándar/crítico) con SLOs distintos.

2. **H3 (Batch Size):**
    - ¿Priorizamos **throughput máximo** (batch ~1000) o **seguridad operativa** (batch ~300–500)?
    - *Propuesta:* Usar **batch=500** como default (equilibrio entre throughput y staleness/blast radius).

3. **Q10 (Backpressure):**
    - ¿Qué política de cola adoptamos para floods? Opciones:
        - **Drop oldest** (pérdida de datos viejos).
        - **Block producer** (backpressure a fuente).
        - **Spill a disco** (persistencia temporal).
    - *Propuesta:* **Drop oldest** (simplicidad) + métrica de eventos descartados.

---
---
## **📌 CONCLUSIÓN**
- **Gate A (Schema): ✅ Merge YA.**
- **Gate B (Sink): ❌ Bloqueado por B1–B5.**
    - **Prioridad absoluta:** B1 (WAL) y B2 (Poison) → **Riesgo de pérdida de datos**.
    - **Segunda prioridad:** B3 (Footgun), B4 (Staleness), B5 (Reader).
- **Guardas NOW (G1–G3): Implementar en paralelo.**
- **Hardening (H1–H4): Fase 1 (ADR-041).**

**Próximos pasos:**
1. **Asignar responsables** para cada B1–B5 y G1–G3.
2. **Crear tickets** en el backlog con las métricas objetivo.
3. **Reunión de revisión en 5 días** para validar B1–B5.

---
**¿Qué experimento o métrica añadirías para reducir el riesgo residual en B1–B5?**

FDO

MISTRAL