**Respuesta como consejero: Alonso Isidoro Roman (o equivalente en experiencia C++/sistemas distribuidos).** He revisado toda la evidencia, la ADR y las mediciones existentes. Me centro en agujeros no vistos o mal medidos. Todas mis respuestas terminan en invariante/experimento/número verificable.

### Q1 — ¿El ×61 transfiere o es artefacto VM?
**Objeción en una frase:** El ×61 es mayoritariamente parse/plan + overhead de `query()` por fila; fsync en SSD real reduce la brecha pero no la elimina porque el batch UNWIND sigue evitando recompilación y llamadas repetidas.

**Experimento que lo zanja:** En hardware target (N100/RPi5 con SSD NVMe), correr idéntico smoke con `PRAGMA profiling` + timer explícito alrededor de `Database::query()` vs tiempo total de tx. Medir % de tiempo en "compilation" + "execution" para MERGE fila vs UNWIND batch=1000. Invariante: si compilation >30% en MERGE, el speedup estructural se mantiene >×20 incluso con fsync barato.

**Bloqueante para merge Fase 0:** No, pero obliga a incluir el profiling en el smoke de ADR-041 antes de declarar production-ready.

### Q2 — Staleness a bajo caudal.
**Objeción en una frase:** Batch=1000 puro por tamaño crea staleness inaceptable para detección activa (minutos); flush-by-time es obligatorio y debe ser agresivo.

**Experimento/número:** SLO de staleness máximo aceptable para NDR = **500 ms** (tiempo de detección de ataque activo razonable). Política: `flush(size=1000 OR time=200ms)`. Medir en simulación de 3 flows/s: % de eventos consultables <200ms y throughput sostenido. Si throughput cae >15%, bajar a 100ms o hybrid con mini-batches.

**Bloqueante:** Sí para merge Fase 0. Sin flush-by-time medido, UNWIND+1writer no es production-ready.

### Q3 — Reader real vs count(*).
**Objeción en una frase:** La contención medida es irrelevante; traversal 3-hops con filtros por `community_id` + propiedades bajo write riada cambia completamente el p99.

**Experimento:** Reemplazar reader por query representativa:
```cypher
MATCH (f:Flow {community_id: $cid})-[:NEXT*1..3]->(f2)
WHERE f2.timestamp > $ts AND f2.src_ip IN $suspicious
RETURN count(*) AS anomalies
```
Correr concurrente con writer UNWIND. Medir p99 latencia reader y % rechazos writer vs baseline count(*). Invariante: si p99 reader ×>3 o rechazos >5%, conclusión "lectura sana" se invalida.

**Bloqueante:** Sí. El smoke actual es inválido para validar "lectura sana".

### Q4 — Memoria a escala.
**Objeción en una frase:** RSS escala peor que lineal por working set de columnar + índices implícitos; 1M nodos fácilmente >6-8GB sin tiering.

**Experimento:** Sweep: cargar grafo 100k → 500k → 1M nodos (sintético flows hospitalarios) midiendo maxRSS después de checkpoint y tras query traversal pesada. Curva esperada ~6-10 MB por 1k nodos activos. Estrategia tiering: exportar cold edges/nodos (>24h) a Parquet + vista DuckDB externa, mantener solo hot window (últimas 4h) en Kuzu con `COPY ... TO` periódico + delete. Invariante objetivo: RSS <5.5 GB a 1M nodos hot.

**Bloqueante:** Sí para producción real. Diferir sin curva = alto riesgo en RPi5/N100.

### Q5 — Atomicidad y flows envenenados.
**Objeción en una frase:** UNWIND es una sola transacción → rollback total en error (comportamiento estándar ACID).

**Semántica y estrategia:** Rollback total confirmado por diseño Kuzu (una tx write). Estrategia: pre-validación ligera + quarantine. Batch → intentar UNWIND; en error, fallback a retry fila-por-fila con quarantine en buffer separado (o tabla temporal "bad_flows"). Blast radius controlado: <1% pérdida en tráfico hostil. Medir % de batches fallidos y overhead del fallback.

**Bloqueante:** Hardening posterior, pero debe incluirse en smoke antes de merge (test con fila maligna intencional).

### Q6 — Batch sweep.
**Objeción en una frase:** 1000 es arbitrario; tradeoff staleness/aislamiento/throughput requiere sweep explícito.

**Experimento:** Sweep batch ∈ {50, 200, 500, 1000, 5000} con flush híbrido (size OR 200ms). Medir: throughput, p99 staleness, RSS delta, % fallos propagados. Óptimo operativo probable en codo 200-500 (no coincide necesariamente con pico throughput puro).

**Bloqueante:** No, pero obligatorio antes de declarar "production-ready" en ADR-041.

### Q7 — WAL y durabilidad.
**Objeción en una frase:** Borrar WAL en smoke oculta el camino real de recuperación; los datos commiteados pero no checkpointed se pierden si se borra.

**Experimento `restore_from_wal_smoke_test`:** Script: (1) writer UNWIND riada continua, (2) `SIGKILL` aleatorio durante tx, (3) reabrir `Database` misma path, (4) verificar conteo exacto de upserts commiteados pre-kill (usar secuencia o hash traceable). Invariante: 0 pérdida de commiteados tras >100 kills. Si falla, debt WAL se vuelve bloqueante.

**Bloqueante:** Sí para Fase 0. Durabilidad no negociable en infraestructura crítica.

### Q8 — Shardability.
**Objeción en una frase:** Diferir implementación sin hacer write-path shard-aware hoy = reescritura cara después.

**Invariante mínima hoy:** Todo upsert debe llevar `routing_key` explícita (e.g. `community_id` o hash(flow_src)`). Correlador solo asume grafo local por shard. Write API expone `shard_id` opcional. Esto permite fan-out futuro sin cambiar modelo de datos.

**Bloqueante:** Hardening posterior (añadir routing_key ahora es barato).

### Q9 — Footgun Database único.
**Objeción en una frase:** Documentar no previene; singleton + guardia runtime es necesario.

**Implementación fail-closed:** `DatabaseFactory` singleton con `std::once_flag` + verificación `std::filesystem::path` canonical. Constructor lanza `std::logic_error` (o custom) si ya existe para ese path. Test unitario: intentar segundo `Database` y ASSERT_THROW. En C++: mutex + static map<path, weak_ptr>.

**Bloqueante:** Sí para merge Fase 0. Deuda → guardia real.

**Veredicto general:** D1-D4 son dirección correcta (batch + 1 writer), pero Fase 0 requiere Q2 (flush time), Q3 (traversal reader), Q7 (WAL recovery real) y Q9 (guardia) como bloqueantes. Sin ellos, "production-ready" es smoke-tested, no adversarially proven. El resto es hardening posterior medible.

Traigo mediciones o experimentos, no opiniones. Listo para siguiente ronda.

FDO

GROK