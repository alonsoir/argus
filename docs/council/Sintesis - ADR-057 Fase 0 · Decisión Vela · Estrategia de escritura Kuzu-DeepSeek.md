# INFORME DE SÍNTESIS DEFINITIVA — ADR-057 Fase 0
## Del Consejo de Sabios al Ponente · Orquestación: Claude (Anthropic)
**DAY 182** · Tras revisión cruzada de los 8 dictámenes previos

---

## 0. Corrección metodológica

El Consejo reconoce un error de encuadre colectivo en la primera ronda: la pregunta “¿Bloqueante para el merge de Fase 0?” mezclaba **dos gates distintos**. La síntesis clarifica:

- **Gate A – schema e ingest framework** (`ingested_at`, `temporal_anomaly`, `ingest_clock`, `cypher_builder`): listo para commit. Ninguna de las preguntas Q1‑Q9 lo afecta. **Sale ya.**
- **Gate B – sink de producción y afirmación “production‑ready”** (UNWIND batch + 1 writer, D1‑D4): **no está probado.** El smoke midió el mejor caso; la producción es el peor. Se requieren 5 experimentos bloqueantes antes de declarar el sink utilizable en NDR real.

Este informe reemplaza cualquier afirmación anterior de “ninguna pregunta bloquea”. Las decisiones D1‑D4 son la dirección correcta (unanimidad técnica), pero la implementación del sink queda **condicionada a la batería de 5 pruebas**.

---

## 1. Decisiones confirmadas y su estado

| Decisión | Contenido | Estado |
|----------|-----------|--------|
| D1 | Escritura con UNWIND batch + 1 writer único | Dirección correcta, condicionada |
| D2 | Vela NO se adopta | Confirmada |
| D3 | Multi‑writer descartado; sharding diferido | Confirmada, con invariante de seam (véase §4) |
| D4 | Un `Database`, N `Connections`, in‑process único | Confirmada, con guarda de `DatabaseRegistry` |

---

## 2. Batería de 5 pruebas bloqueantes para Gate B

Cada prueba incluye el experimento exacto y el criterio numérico de éxito. No se considerará el sink production‑ready hasta que todas estén superadas.

### B1 · Recuperación del WAL (prioridad #1)
- **Objetivo:** Verificar que tras una muerte súbita (`kill -9`) el WAL nativo de Kuzu recupera todas las transacciones confirmadas.
- **Experimento:**
    1. Iniciar escritura continua de lotes con un marcador único por transacción.
    2. Enviar `SIGKILL` en instante aleatorio durante el commit.
    3. Reabrir la base de datos **sin borrar archivo alguno** (prohibido `cleanup_db` en producción).
    4. Verificar que todas las transacciones cuyo commit fue reconocido están presentes e íntegras.
    5. Repetir ≥100 veces.
- **Criterio:** **0 commits reconocidos perdidos**; tiempo de recuperación ≤5 s para una ventana de 100k operaciones.
- **Deuda asociada:** DEBT‑LABEL‑WAL‑001 → bloqueante.

### B2 · Atomicidad y flujo envenenado
- **Objetivo:** Evitar que una sola fila malformada descarte 999 detecciones válidas.
- **Experimento:**
    1. Insertar en un lote de 1000 una fila que viole el esquema (nodo duplicado, tipo erróneo).
    2. Confirmar que Kuzu realiza rollback total (todos lo asumen, hay que verificarlo).
    3. Implementar bisección recursiva ante fallo: dividir el lote en mitades hasta aislar la fila tóxica, enviarla a `quarantine.log` y confirmar el resto.
    4. Añadir validación previa en el borde (aprovechando `cypher_builder.hpp`) para rechazar tempranamente.
- **Criterio:** **0% de pérdida** de detecciones legítimas; sobrecarga de la bisección ≤10% del throughput.
- **Deuda asociada:** DEBT‑KUZU‑BATCH‑POISON‑001 → bloqueante.

### B3 · Guarda del footgun (DatabaseRegistry)
- **Objetivo:** Hacer imposible abrir dos instancias de `Database` sobre el mismo path dentro del mismo proceso.
- **Experimento:**
    1. Implementar un `DatabaseRegistry` (mapa `path → weak_ptr<Database>`).
    2. Prohibir la construcción directa; solo se obtiene mediante `open()` del registro.
    3. Test unitario: intentar abrir dos veces el mismo path → `EXPECT_THROW`.
    4. Medir el coste de la verificación (debe ser <1 µs).
- **Criterio:** **Fallo controlado garantizado**, no dependiente de disciplina manual.
- **Deuda asociada:** DEBT‑KUZU‑SINGLE‑DATABASE‑GUARD‑001 → bloqueante.
- **Nota:** Este diseño (registry en lugar de singleton ciego) permite múltiples paths distintos y es compatible con sharding futuro (Q8).

### B4 · Staleness a bajo caudal (flush‑by‑time)
- **Objetivo:** Garantizar que un flujo de eventos lento no produzca latencias de detección inaceptables.
- **Experimento:**
    1. Alimentar el sink con caudales realistas de red tranquila: 1, 3 y 10 flows/s.
    2. Implementar política de descarga: `flush(size ≥ N OR age ≥ T_ms)` con un hilo `Ticker` asíncrono.
    3. Medir staleness extremo‑a‑extremo (desde ingreso del paquete hasta visibilidad en consulta) en p99.
- **Criterio:**
    - SLO de staleness p99: **≤1 s** para caudal bajo estándar; ≤100 ms para eventos críticos.
    - Degradación del throughput en saturación ≤15%.
- **Deuda asociada:** DEBT‑KUZU‑WRITE‑BATCHING‑001 (extendida) → bloqueante.

### B5 · Lector de correlación real
- **Objetivo:** Validar que la contención no hace inviable la lectura analítica bajo carga de escritura real.
- **Experimento:**
    1. Sustituir el `count(*)` actual por una consulta de correlación canónica: 3 saltos por `community_id` partiendo de un nodo sospechoso.
    2. Ejecutarla concurrentemente con la riada de upserts, replicando run2 y run3.
    3. Medir latencia p50/p99 de la consulta y el impacto en el throughput de escritura.
- **Criterio:**
    - Latencia p99 de lectura bajo carga ≤3× la latencia en reposo.
    - Degradación del writer ≤30%.
- **Deuda asociada:** DEBT‑KUZU‑CONCURRENCY‑SMOKE‑001 → bloqueante.

---

## 3. Guardas baratas de aplicación inmediata (no esperan a la batería)

- **Acotar `bufferPoolSize`** en la inicialización de Kuzu según la RAM disponible del host. Convierte Q4 (memoria a escala) en un riesgo de rendimiento, no de estabilidad.
- **Hacer explícita la clave de routing** (`getRoutingKey()`) en los eventos de ingesta, y que el correlador dependa de `IGraphQuery`/`GraphRepository`, no de una conexión concreta. Esto preserva la capacidad de sharding futuro sin coste ahora (Q8).

---

## 4. Cuestiones diferidas a hardening (ADR-041 / Fase 1)

- **Q1 (×61):** Descomponer coste fsync vs parse en hardware real (N100/NVMe). La dirección D1 es invariante; solo calibrará el multiplicador exacto.
- **Q4 (curva RSS):** Con el pool de buffer capado, medir latencia de consulta real bajo thrashing con 1M nodos y planificar tiering hot‑cold.
- **Q6 (tamaño de lote óptimo):** Barrido fino `batch ∈ {10, 50, 100, 300, 500, 1000, …}` midiendo simultáneamente throughput, staleness, RSS y radio de fallo; fijar el valor de producción basado en el frente de Pareto que cumpla todos los SLO.
- **Q10 (backpressure):** Formalizar y probar el mecanismo de control de cola ante sobrecarga sostenida (DEBT‑INGEST‑BACKPRESSURE‑001).

---

## 5. Veredicto final del Consejo

La propuesta técnica D1–D4 es sólida, unánime y debe ser registrada como la dirección del sistema. Sin embargo, el **sink de producción no se considera validado** hasta que se complete la batería de cinco pruebas bloqueantes descritas en §2.

Se insta al ponente a:
1. **Merge inmediato** de los cambios de schema e ingest framework (Gate A).
2. **Inicio de la batería bloqueante** en una rama paralela, priorizando la recuperación del WAL (B1) y la atomicidad ante flujos envenenados (B2).
3. **Aplicación de las guardas baratas** (registro de bases de datos, acotación del pool de buffer, seam de routing) en el tronco principal antes de cualquier despliegue.

La documentación complementaria (ADR‑057 v2) reflejará este desglose y las deudas técnicas listadas.

> *Medir no es solo un experimento; es la única defensa contra la extrapolación sin datos.* — Consejo de Sabios, DAY 182
> 
> FDO
> 
> DEEPSEEK