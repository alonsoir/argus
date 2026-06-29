**Respuesta como consejero (Grok — C++/sistemas distribuidos).** He incorporado la síntesis completa: alineo con los 5 bloqueantes de consenso, acepto las correcciones (Gate B real, Registry vs singleton, etc.) y aporto precisión C++ + invariantes medibles. Nada de opiniones; todo experimento o número.

### B1 · Q7 — WAL recovery (prioridad #1)
**Objeción en una frase:** El smoke actual contaminó la medición al borrar WAL; la recuperación nativa tras SIGKILL con ficheros intactos sigue sin validar en el write-path batcheado.

**Experimento:** Script de chaos: (1) riada UNWIND continua con `ingest_clock` secuencial traceable, (2) `SIGKILL` uniforme durante tx commit, (3) reabrir `Database` **sin cleanup**, (4) query de verificación de conteo + hash de últimos 500 eventos commiteados. Ejecutar ≥100 kills en N100/SSD.  
**Número:** 0% pérdida de commiteados + recuperación <5 s en ventana 100k. Si falla replay, debt WAL bloquea.

**Bloqueante:** Sí (Gate B). Quita `cleanup_db` de prod inmediatamente.

### B2 · Q5 — Atomicidad / flow envenenado
**Objeción en una frase:** UNWIND = tx única → rollback total confirmado; sin quarantine el blast-radius es inaceptable en tráfico hostil.

**Estrategia + experimento:** Validación semántica ligera pre-UNWIND (usando `cypher_builder` ya parcheado) + bisección recursiva en fallback (batch → mitades hasta fila tóxica → quarantine.log + retry resto). Medir en workload con 0.1-1% filas malignas intencionales.  
**Número:** Pérdida legítima = 0%; overhead del fallback ≤10% en throughput medio.

**Bloqueante:** Sí (Gate B). Debt-KUZU-BATCH-POISON-001.

### B3 · Q9 — Guarda Database (giro Registry)
**Objeción en una frase:** Documentación no es guardia; un singleton ciego mataría sharding futuro.

**Implementación C++ fail-closed:** `DatabaseRegistry` (singleton del registry, no del Database) con `std::unordered_map<std::filesystem::path, std::weak_ptr<kuzu::Database>>` + `std::mutex`. Constructor `open(path)`: canonicaliza path, chequea weak_ptr expirado o lanza `std::runtime_error("Database already open for path")`. Soporta N paths distintos.  
**Número:** Test `EXPECT_THROW` en 2ª apertura mismo path; overhead registro <1 µs (medido con `std::chrono::high_resolution_clock`). Test de sharding futuro: abre 2 paths distintos sin throw.

**Bloqueante:** Sí (Gate B). Resuelve Q9 + habilita Q8 con la misma pieza.

### B4 · Q2 — Staleness / flush-by-time
**Objeción en una frase:** Batch por tamaño puro genera staleness de minutos a bajo caudal; flush híbrido es obligatorio.

**Política:** `flush(size >= 500 OR age >= 1000ms)` con `std::jthread` ticker asíncrono (o `boost::asio` steady_timer).  
**Experimento:** Simulación 1/3/10 flows/s, medir e2e (ingest → visible en traversal) p99 staleness + delta throughput.  
**Número:** p99 staleness ≤1000 ms; degradación throughput ≤15%. Centro de consenso del Consejo. Calibrar SLO exacto en ADR-057 v2.

**Bloqueante:** Sí (Gate B). Debt-KUZU-WRITE-BATCHING-001.

### B5 · Q3 — Reader real de correlación
**Objeción en una frase:** `count(*)` no representa contención real; traversal 2-3 hops bajo riada puede cambiar p99 drásticamente.

**Query representativa:**
```cypher
MATCH (f:Flow {community_id: $cid})-[:NEXT*1..3]->(f2)
WHERE f2.timestamp > $ts AND f.src_ip IN $suspicious
RETURN count(*) AS anomalies, collect(f2.flow_id) LIMIT 100
```
**Experimento:** Correr concurrente con writer UNWIND (mismo smoke mejorado). Medir p99 reader + % rechazos writer vs baseline.  
**Número:** read p99 ≤3-5× idle; degradación writer ≤30%. Fuera de rango → "lectura sana" provisional invalidada.

**Bloqueante:** Sí (Gate B). Debt-KUZU-CONCURRENCY-SMOKE-001.

### Adicional: Q10 — Backpressure (crédito ChatGPT)
**Objeción en una frase:** Asumir producer ≤ writer es frágil; flood DDoS/scan-storm debe acotar memoria.

**Estrategia C++:** Cola bounded (`moodycamel::ConcurrentQueue` o `std::deque` con high-water mark) + política (drop-oldest por `ingest_clock`, spill a Parquet temporal, o block con backpressure al upstream). Cap `bufferPoolSize` + RSS monitoring.  
**Experimento:** Producer 2-5× writer durante 30 min sostenido.  
**Número:** RSS acotada (no crecimiento lineal), pérdida controlada <0.1% eventos críticos. Debt-INGEST-BACKPRESSURE-001 → mínimo hardening fuerte, idealmente Gate B.

### Guardas NOW baratas (no esperan batería)
- **Q4 Memoria:** En `DatabaseRegistry::open` → `db->setConfig("bufferPoolSize", std::min(2GB, 0.6 * hostRAM))`. Evita OOM lineal (Kuzu pagina). Medir thrashing latencia a 1M nodos. Hardening + guarda inmediata.
- **Q8 Sharding:** `getRoutingKey()` explícito (`community_id` hash) + `IGraphQuery` seam. Registry ya lo habilita.

**Veredicto de cierre:** Total alineamiento con síntesis. Gate A sale ya. Gate B (sink production-ready) gated por los 5 B1-B5 + Q10. Dirección D1-D4 sólida y unánime. Hardening Q1/Q6/Q4-curve en ADR-041.

Traigo experimentos medibles, no votos. Listo para implementar los tests y re-medir.

FDO

GROK