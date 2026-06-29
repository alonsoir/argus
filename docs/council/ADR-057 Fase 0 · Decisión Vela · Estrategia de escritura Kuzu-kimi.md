# ACTA DE REVISIÓN ADVERSARIAL — RESPUESTAS DEL CONSEJO
## ADR-057 Fase 0 · Decisión Vela · Estrategia de escritura Kuzu

---

### Q1 — ¿El ×61 transfiere o es un artefacto de la VM?

**Objeción:** El ×61 es probablemente **real y estructural**, no un artefacto de VM. El coste dominante en run1 no es `fsync` sino **parse/plan + overhead por-query()**.

**Razonamiento:** Kuzu utiliza WAL para atomicidad y durabilidad, con transacciones serializables y un único writer. En run1 (MERGE fila-a-fila), cada upsert implica parse Cypher → plan query → ejecutar → commit individual. El coste de parse/plan es O(query) y no se amortiza. En run2 (UNWIND batch=1000), se parsea y planifica **una vez** para 1000 filas. El WAL es append-only y secuencial; `fsync` por transacción es ~constante independientemente del número de filas dentro de la tx. El paper de Kuzu confirma: "Transactions are by design serializable as we currently allow one writer transaction in the system" .

**Experimento mínimo:**
1. Instrumentar `connection.query()` con `std::chrono` para descomponer: `[parse_time, plan_time, exec_time, commit_time]`.
2. Ejecutar run2 con batch=1 (UNWIND de 1 fila) vs batch=1000. Si batch=1 se acerca a run1, el ×61 es amortización de parse/plan.
3. Validar ratio run2/run1 en hardware real (RPi5/N100, ADR-041). Si el ratio se mantiene ≥30×, es estructural.

**Métrica de zanjamiento:** Ratio ≥30× en hardware real → estructural confirmado. Ratio <10× → VM artifact dominante.

**¿Bloqueante para Fase 0?** NO. El ×61 es casi seguramente estructural. Pero SÍ bloqueante si el ratio cae <10× en hardware real.

---

### Q2 — Staleness a bajo caudal (el smoke midió el mejor caso)

**Objeción:** El batch fijo de 1000 es una **trampa operativa**. A 3 flows/s, la latencia de detección es ~5.5 minutos — inaceptable para un NDR activo. Se necesita `flush(size OR time)` con SLO por fuente.

**Razonamiento:** El smoke corrió saturado. En régimen de bajo caudal (madrugada hospitalaria), 1000 flows / 3 flows/s = 333s ≈ 5.5 minutos de ceguera. Un ataque lateral silencioso (reconnaissance, C2 beacon) puede completarse en minutos. Kuzu NO tiene configuración nativa de flush interval (a diferencia de Kafka que tiene `log.flush.interval.ms`) . El flush es responsabilidad del aplicativo.

**Experimento mínimo:**
1. Implementar `flush(size=1000 OR time=T_ms)` con `T ∈ {100, 500, 1000, 5000, 10000}`.
2. Medir throughput y staleness p99 ("tiempo desde ingesta hasta consultable") para cada T.
3. Plotear curva throughput vs staleness. El "codo" define el SLO operativo.

**Métrica de zanjamiento:** SLO propuesto: staleness p99 ≤ 2s para fuentes críticas (hospital, ICS), ≤ 10s para fuentes normales. Throughput degradación ≤ 15% respecto a batch puro.

**¿Bloqueante para Fase 0?** **SÍ.** Sin política de flush-by-time, el sistema es ciego a bajo caudal. Merge bloqueado hasta definir `flush_interval_ms` y validar con smoke.

---

### Q3 — El reader del smoke es un juguete

**Objeción:** `count(*)` no toca el grafo. Una **traversal multi-hop** por `community_id` contiende con el writer en el buffer manager y en los índices CSR, invalidando las cifras de contención ×1.16.

**Razonamiento:** Kuzu usa almacenamiento columnar CSR (Compressed Sparse Row) para edges . `count(*)` es un scan de metadatos; no toca estructuras CSR ni vectores de propiedades. Una traversal real requiere random access en índices de nodo, traversal CSR multi-hop, e intersección de conjuntos en memoria. El writer batcheado modifica CSR (append edges), invalidando cachés y forzando re-lectura de páginas del buffer manager.

**Experimento mínimo:**
1. Query representativa de correlación NDR:
   ```cypher
   MATCH (f1:Flow)-[:NEXT_HOP*1..3]->(f2:Flow)
   WHERE f1.community_id = $cid AND f2.dst_ip = $ip
   RETURN f1, f2
   ```
2. Ejecutar en bucle (reader) mientras el writer hace UNWIND batch=1000. Medir latencia p50/p99/p99.9 del reader y throughput del writer.
3. Comparar contra baseline (reader solo).

**Métrica de zanjamiento:** Reader p99 ≤ 2× baseline con writer activo. Writer throughput degradación ≤ 20% con reader activo.

**¿Bloqueante para Fase 0?** **SÍ.** Sin validar con traversal real, las cifras de contención son literatura fantástica. Merge bloqueado hasta smoke con query representativa.

---

### Q4 — A escala real, el cuello es la MEMORIA

**Objeción:** 822 MB para 100k nodos proyecta ~8 GB para 1M nodos, excediendo RPi5 y apretando N100. El cuello vinculante no es throughput sino **working set**, y Kuzu 0.11.3 carece de índice de rango para tiering.

**Razonamiento:** Proyección lineal: 822 MB / 100k × 1M = 8.22 GB. RPi5 (8 GB total) → OOM garantizado con Kuzu + OS + ZeroMQ + ML detector. Kuzu asigna ~80% de memoria física al buffer pool por defecto . Sin tiering hot→cold, el grafo crece indefinidamente. Kuzu escala a cientos de millones de nodos en benchmarks académicos (LDBC SF100: ~280M nodos, 1.7B edges) , pero eso es con hardware de servidor, no RPi5.

**Experimento mínimo:**
1. Medir RSS vs |nodes| para |nodes| ∈ {100k, 250k, 500k, 750k, 1M} con distribución power-law (realista para redes).
2. Plotear curva RSS = f(|nodes|).
3. Estrategia de tiering: Hot (Kuzu, últimas N horas) → Warm (Parquet/DuckDB) → Cold (S3/minio). PoC de exportación periódica.

**Métrica de zanjamiento:** RSS(1M nodes) ≤ 6 GB (margen para N100 con 16 GB). Query con rango de timestamp en 1M nodes: p99 ≤ 500ms. Overhead de tiering ≤ 5%.

**¿Bloqueante para Fase 0?** **PARCIALMENTE.** La curva RSS vs nodos es bloqueante (define viabilidad RPi5). El tiering es hardening posterior (ADR-041).

---

### Q5 — Atomicidad: un flow envenenado tira 1000 detecciones

**Objeción:** UNWIND batch es **UNA transacción ACID con rollback total**. Un flow malformado revienta las 999 detecciones legítimas del batch, transformando aislamiento en **amplificación de pérdida**.

**Razonamiento:** Kuzu implementa transacciones ACID: "updates are atomic and provide all-or-nothing behavior" . UNWIND de 1000 filas = UNA transacción. Si falla CUALQUIER fila (constraint violation, tipo incorrecto, null inesperado), toda la transacción se revierte. Un NDR ingiere tráfico HOSTIL por definición. Un atacante puede enviar un paquete malformado para causar DoS de detección. La escritura por fila (run1) aísla fallos: 1 fila mala = 1 fila perdida. El batch convierte 1 fila mala en 1000 filas perdidas.

**Experimento mínimo:**
1. Crear UNWIND batch=1000 con 1 fila malformada. Verificar rollback TOTAL.
2. Implementar estrategia de quarantine:
    - **Pre-validación:** schema validation antes de UNWIND.
    - **Fallback binario:** si UNWIND falla, reintentar con batch/2, recursivamente hasta batch=1.
    - **Dead letter queue:** filas rechazadas a quarantine forense.
3. Medir overhead en throughput.

**Métrica de zanjamiento:** Con quarantine + fallback: throughput degradación ≤ 10%. Tasa de pérdida de detecciones legítimas: 0%.

**¿Bloqueante para Fase 0?** **SÍ.** Sin estrategia de quarantine, un atacante puede DoSear el NDR con un único paquete malformado. Merge bloqueado hasta implementar pre-validación o fallback.

---

### Q6 — 1000 es un número mágico

**Objeción:** 1000 es arbitrario. El óptimo operativo no coincide con el óptimo de throughput porque tradea staleness, RSS y blast-radius de fallo. **No hay sweep que lo justifique.**

**Razonamiento:** Batch size afecta throughput (↑), staleness (↑), RSS (↑), y blast radius de fallo (↑). 1000 puede ser óptimo para throughput puro pero sub-óptimo para el sistema completo. Necesario barrido sistemático.

**Experimento mínimo:**
1. Sweep de batch_size ∈ {1, 10, 50, 100, 500, 1000, 5000, 10000}.
2. Para cada batch_size, medir: throughput, staleness p99, RSS máximo, tiempo de rollback.
3. Plotear Pareto frontier: throughput vs staleness vs RSS.
4. Seleccionar batch_size en la rodilla de la curva, no en el máximo de throughput.

**Métrica de zanjamiento:** Batch óptimo operativo = punto donde ∂(throughput)/∂(batch) < 5% Y staleness p99 ≤ SLO definido en Q2.

**¿Bloqueante para Fase 0?** NO. 1000 es razonable como punto de partida. Pero el sweep es deuda técnica crítica (DEBT-BATCH-SWEEP-001) para ADR-041.

---

### Q7 — Borrar el WAL es lo contrario de lo que necesita producción

**Objeción:** `cleanup_db` borrando el WAL es un **agujero de durabilidad**: el WAL contiene datos commiteados no checkpointed; borrarlo = pérdida de datos confirmados. El smoke no valida recuperación post-SIGKILL.

**Razonamiento:** WAL garantiza durabilidad: cambios se loguean antes de aplicarse a data files . En Kuzu: "Kůzu uses write ahead logging to achieve atomicity and durability" . `cleanup_db` que borra WAL = destrucción de datos commiteados no checkpointed. El smoke validó que el camino de crash EXISTE, no que la RECUPERACIÓN funcione.

**Experimento mínimo:**
1. Implementar `wal_crash_recovery_test`:
    - Ingestar 10k flows con UNWIND batch=1000.
    - Enviar SIGKILL aleatorio durante ingest (10% probabilidad por batch).
    - Reabrir DB, contar flows. Assert: count == expected.
2. Repetir 100 veces.
3. Medir tiempo de recuperación (WAL replay).

**Métrica de zanjamiento:** Tasa de pérdida post-SIGKILL: 0%. Tiempo de recuperación WAL: ≤ 5s para ventana de 100k flows.

**¿Bloqueante para Fase 0?** **SÍ.** Sin test de recuperación WAL post-SIGKILL, no hay garantía de durabilidad. Merge bloqueado hasta `restore_from_wal_smoke_test` pase.

---

### Q8 — Diferir sharding ¿es diferir, o es cerrar la puerta?

**Objeción:** Si el write path de hoy asume grafo único y correlación cross-shard imposible, "diferir sharding" es en realidad **"imposibilitarlo sin reescritura completa"**.

**Razonamiento:** Sharding de grafos requiere routing key explícita, correlación cross-shard, y consistencia de referencias (IDs globales vs locales). Si hoy el modelo asume IDs autoincrementales locales y queries sin hint de shard, sharding posterior requiere migración de IDs (imposible sin downtime) y reescritura de todas las queries.

**Experimento mínimo:**
1. Definir routing key: `shard_key = hash(src_ip) % N_shards`.
2. Asegurar que TODOS los nodos Flow tienen `shard_key` como propiedad.
3. Implementar correlador con interfaz abstracta:
   ```cpp
   class Correlator {
     virtual QueryResult correlate(const Flow& flow) = 0;
     // single-shard hoy, multi-shard mañana
   };
   ```
4. Verificar 0 queries hardcodean asunción de grafo único.

**Métrica de zanjamiento:** 100% de nodos/edges tienen `shard_key` explícita. 0 queries asumen unicidad global.

**¿Bloqueante para Fase 0?** NO como implementación, **SÍ como diseño**. Merge NO bloqueado, pero se requiere ADR-058 (shard-agnostic design contract) como deliverable paralelo.

---

### Q9 — El footgun ¿está prevenido o solo anotado?

**Objeción:** `DEBT-KUZU-SINGLE-DATABASE-GUARD-001` es documentación, no guarda. Abrir un 2º `Database` in-process debe ser **IMPOSIBLE mecánicamente**, no improbable por disciplina.

**Razonamiento:** Kuzu permite "one writer transaction in the system" y dos Database sobre mismo path = corrupción. Documentación no previene errores en producción a las 3 AM con deploy apresurado. Patrón fail-closed: el sistema debe hacer IMPOSIBLE el estado inseguro.

**Experimento mínimo:**
1. Implementar singleton thread-safe con verificación de path:
   ```cpp
   class KuzuDatabaseManager {
     static std::mutex mtx;
     static std::shared_ptr<kuzu::Database> instance;
     static std::string current_path;
   public:
     static std::shared_ptr<kuzu::Database> open(const std::string& path) {
       std::lock_guard<std::mutex> lock(mtx);
       if (instance && current_path != path) {
         throw std::runtime_error("Database already open at different path");
       }
       // ... crear o retornar existente
     }
   };
   ```
2. Test unitario: 2º intento de `open()` lanza excepción controlada.
3. Test de integración: dos threads concurrentes intentan abrir DB simultáneamente → uno gana, otro falla con error claro.

**Métrica de zanjamiento:** Test pasa: 2º open() lanza excepción con mensaje claro. 0% posibilidad de corrupción por doble Database.

**¿Bloqueante para Fase 0?** **SÍ.** Sin guarda mecánica, el footgun es inevitable en producción. Merge bloqueado hasta singleton + test.

---

## RESUMEN DE BLOQUEOS PARA MERGE FASE 0

| Pregunta | Bloqueante | Razón |
|----------|-----------|-------|
| Q1 | NO | ×61 probablemente estructural; validar en HW real |
| Q2 | **SÍ** | Sin flush-by-time, ceguera a bajo caudal |
| Q3 | **SÍ** | Sin traversal real, contención es literatura |
| Q4 | PARCIAL | Curva RSS vs nodos define viabilidad RPi5 |
| Q5 | **SÍ** | Sin quarantine, DoS por paquete malformado |
| Q6 | NO | Sweep es deuda técnica crítica para ADR-041 |
| Q7 | **SÍ** | Sin test SIGKILL→recover, no hay durabilidad |
| Q8 | NO (diseño) | Requiere ADR-058 contract shard-agnostic |
| Q9 | **SÍ** | Sin singleton mecánico, footgun inevitable |

### Condiciones de merge Fase 0:
1. ✅ Implementar `flush(size OR time)` con SLO definido (Q2)
2. ✅ Smoke con traversal multi-hop representativo (Q3)
3. ✅ Estrategia quarantine + fallback batch (Q5)
4. ✅ `wal_crash_recovery_test` post-SIGKILL (Q7)
5. ✅ Singleton Database con test de doble-apertura (Q9)
6. ⏳ Curva RSS 100k/500k/1M (Q4) — puede ser ADR-041 si no bloquea RPi5

> *"La documentación es un voto; el smoke es una medida."* — DAY 182
> 
> FDO
> 
> KIMI