He procesado la síntesis del Consejo y genero ahora el **plan de acción ejecutable** para ADR-057 v2, con la corrección del meta-hallazgo adoptado: dos gates independientes.

---

# PLAN DE ACCIÓN EJECUTABLE — ADR-057 Fase 0 v2
## Decisión Vela · Escritura Kuzu · Post-Síntesis Consejo DAY 182

---

## META-HALLAZGO ADOPTADO

**"Bloqueante para Fase 0" se bifurca en dos gates:**

- **GATE A — Commit de schema/ingest** (`ingested_at`, `temporal_anomaly`, `ingest_clock`, `cypher_builder`). Estado: **VERDE**. Nada de Q1–Q10 lo toca. **Sale YA.**

- **GATE B — Sink de producción + afirmación "production-ready"**. Estado: **ROJO**. 5 bloqueantes de consenso. **Ningún merge del sink hasta que la batería B1–B5 pase.**

La dirección D1–D4 (UNWIND batch + 1 writer, Vela no, sharding diferido, single Database) es **INVARIANTE y unánime**. Lo que se gatea es la **implementación del sink**, no la decisión arquitectónica.

---

## GATE A — SALIDA INMEDIATA (Schema / Ingest)

Items que salen del tablero ahora, sin condición:
- ✅ `ingested_at` (timestamp de llegada al sink)
- ✅ `temporal_anomaly` (flag de anomalía temporal)
- ✅ `ingest_clock` (reloj lógico de ingestión)
- ✅ `cypher_builder.hpp` (constructor de Cypher, patch H-1)
- ✅ `IGraphSink` / `IGraphQuery` seams (interfaces abstractas)

**Razón:** son independientes del comportamiento del motor Kuzu en runtime. Cualquier cambio posterior en batch size, flush policy o WAL recovery no invalida estos commits.

---

## GATE B — BATERÍA PRE-MERGE DEL SINK (5 bloqueantes)

Orden de prioridad = riesgo de pérdida de datos / corrupción / ceguera.

---

### B1 · Q7 · RECUPERACIÓN WAL (PRIORIDAD #1)

**Riesgo:** pérdida de datos confirmados tras crash (`kill -9`, OOM, panic).

**Síntesis:** 8/8 bloqueante. Ninguno detectó que el incidente previo fue **auto-infligido** (borramos `.kuzu`, dejamos `.wal` huérfano). Partimos de **"sin evidencia de bug en Kuzu"**, no de "Kuzu roto".

**Acción inmediata:**
1. **ELIMINAR `cleanup_db` del path de producción.** Queda SOLO como utilidad de smoke-test aislado, nunca en runtime del servicio.
2. Implementar `restore_from_wal_smoke_test` (DEBT-LABEL-WAL-001):
    - a) Ingestar riada de N flows con UNWIND batch=1000
    - b) Enviar SIGKILL aleatorio durante ingest (probabilidad 10% por batch)
    - c) **REABRIR base de datos SIN BORRAR NADA** (ni `.kuzu` ni `.wal`)
    - d) Kuzu debe replayar el WAL nativo
    - e) Verificar: `count(flows) == expected`
3. Repetir ≥100 veces para estadística

**Criterio de aceptación (número que zanja):**
- Tasa de pérdida post-SIGKILL: **0%** (ningún commit ackeado perdido)
- Tiempo de recuperación (WAL replay): **≤ 5 s** para ventana de 100k flows
- Si Kuzu falla el test → bug upstream documentado + workaround (no merge)

| Owner | [asignar ingeniero de confiabilidad] |
| Deadline | Día 189 (7 días desde DAY 182) |
| Dependencia | Ninguna (puro test) |

---

### B2 · Q5 · ATOMICIDAD / FLOW ENVENENADO (DoS por batch)

**Riesgo:** UNWIND batch=1000 es UNA tx ACID. 1 fila malformada → rollback total → 999 detecciones legítimas perdidas. Un atacante envía 1 paquete malformado y niega escritura del NDR.

**Síntesis:** 8/8 bloqueante. Conexión con H-1 (`cypher_builder`) — inyección cerrada; vector restante es semántico (tipo, null, constraint).

**Acción inmediata:**
1. **CONFIRMAR** rollback total de UNWIND (experimento: 1 fila malformada en batch de 1000 → count final = 0). Documentar en acta.
2. Implementar **VALIDACIÓN EN EL BORDE** (antes del UNWIND):
    - a) Schema validation: tipos, rangos, nulls, formatos de IP/MAC
    - b) Foreign-key check: nodos referenciados existen (si aplica)
    - c) Rechazar filas inválidas **ANTES** de construir el batch Cypher
3. Implementar **BISECCIÓN RECURSIVA** (fallback ante fallo inesperado):
    - a) UNWIND batch=N falla → reintentar con N/2
    - b) Recursivo hasta N=1 (aisla fila tóxica)
    - c) Fila tóxica → `quarantine.log` (forense) + commitea el resto
4. Medir overhead de pre-validación + bisección en throughput

**Criterio de aceptación (número que zanja):**
- Pérdida de detecciones legítimas: **0%** (ninguna fila buena se pierde)
- Overhead de validación + bisección: **≤ 10%** de throughput vs batch puro
- Quarantine: **100%** de filas rechazadas logueadas con payload completo

| Owner | [asignar ingeniero de ingest / seguridad] |
| Deadline | Día 189 (7 días) |
| Dependencia | H-1 (`cypher_builder`) ya mergeado |
| Debt nuevo | DEBT-KUZU-BATCH-POISON-001 |

---

### B3 · Q9 · GUARDA DEL FOOTGUN (con reconciliación Q8)

**Riesgo:** 2º `Database` in-process sobre mismo path → dos buffer managers → corrupción silenciosa. Documentación no previene errores a las 3AM.

**Síntesis:** ChatGPT propuso `DatabaseRegistry` (`path→weak_ptr`) en lugar de singleton ciego. Esto **resuelve Q9 Y Q8 simultáneamente**: impone "1 path = 1 Database" pero permite N paths distintos (sharding).

**Acción inmediata:**
1. Implementar `DatabaseRegistry` (thread-safe, path-keyed):
   ```cpp
   std::unordered_map<std::string, std::weak_ptr<kuzu::Database>> registry;
   std::mutex registry_mtx;
   // open(path): si path en registry y vivo → retornar existente
   //             si path en registry y muerto → reconstruir
   //             si path nuevo → crear e insertar
   // 2º open() del MISMO path → throw (no silencioso, no segfault)
   ```
2. Construcción directa de `kuzu::Database` fuera del registry = **IMPOSIBLE**. Usar factory única.
3. Tests:
    - a) Unit: `EXPECT_THROW` en 2ª apertura del mismo path
    - b) Integration: dos threads concurrentes abren mismo path → uno gana, otro falla con mensaje claro
    - c) Stress: 100 threads, 50 paths aleatorios → 0 corrupciones

**Criterio de aceptación (número que zanja):**
- 2º `open()` del mismo path: **excepción con mensaje claro** (no segfault)
- Coste de lookup en registry: **< 1 µs** (no impacta throughput)
- **0%** de posibilidad de doble Database in-process (mecánico, no disciplina)

| Owner | [asignar ingeniero de infraestructura / C++ core] |
| Deadline | Día 189 (7 días) |
| Dependencia | Ninguna |
| Debt rename | DEBT-KUZU-SINGLE-DATABASE-GUARD-001 → DEBT-KUZU-REGISTRY-001 |

---

### B4 · Q2 · STALENESS / FLUSH-BY-TIME (ceguera a bajo caudal)

**Riesgo:** batch=1000 a 3 flows/s tarda ~5.5 min en llenarse. Un ataque lateral (reconnaissance, C2 beacon) se completa antes de ser consultable. Kuzu no tiene flush nativo; es responsabilidad del aplicativo.

**Síntesis:** convergencia del Consejo en SLO staleness p99 — rango 500ms..5s. Centro gravitacional: **1s estándar, 100ms crítico**.

**Acción inmediata:**
1. Implementar `flush(size>=N OR age>=T_ms)` con hilo `Ticker` asíncrono:
    - Ticker despierte cada `T_ms` y fuerce commit si hay datos pendientes
    - No usar timer por batch (inestable); usar `cond_var` + timeout
2. Parametrizar `T_ms` por fuente (no global):
    - Fuentes críticas (hospital, ICS): **T = 100 ms**
    - Fuentes normales: **T = 1000 ms**
    - Bulk/backup: **T = 10000 ms** (o deshabilitado)
3. Smoke de bajo caudal: 1, 3, 10 flows/s durante 10 min
    - Medir staleness e2e (paquete capturado → consultable en Kuzu)
4. Medir degradación de throughput vs batch puro (sin time-bound)

**Criterio de aceptación (número que zanja):**
- Staleness p99 **≤ 1000 ms** (estándar), **≤ 100 ms** (crítico)
- Degradación throughput vs batch puro: **≤ 15%**
- Sin pérdida de datos (flush forzado commitea todo lo pendiente)

| Owner | [asignar ingeniero de pipeline / ingest] |
| Deadline | Día 189 (7 días) |
| Dependencia | B2 (validación en borde debe estar para no flushear basura) |
| Debt extend | DEBT-KUZU-WRITE-BATCHING-001 (añadir time-flush) |

---

### B5 · Q3 · READER REAL (validar "lectura sana" bajo carga)

**Riesgo:** el smoke usó `count(*)`, que no toca CSR ni vectores de propiedad. Una traversal multi-hop por `community_id` contiende con el writer en el buffer manager e invalida las cifras de contención ×1.16.

**Síntesis:** 8/8 bloqueante. Hasta esto, "lectura sana" va al acta como **provisional**, no como hecho.

**Acción inmediata:**
1. Definir **QUERY CANÓNICA** de correlación NDR (2–3 hops):
   ```cypher
   MATCH (f1:Flow)-[:NEXT_HOP*1..3]->(f2:Flow)
   WHERE f1.community_id = $cid AND f2.dst_ip = $ip
   RETURN f1, f2
   ```
2. Ejecutar query en bucle (reader) mientras writer hace UNWIND batch=1000
3. Medir:
    - a) Latencia p50/p99/p99.9 del reader (vs baseline idle)
    - b) Throughput del writer (¿se degrada con reader activo?)
    - c) Contención en buffer manager (eBPF/perf o métricas internas Kuzu)
4. Baseline: reader solo, sin writer. Comparar ratios.

**Criterio de aceptación (número que zanja):**
- Reader p99 **≤ 2× baseline** bajo carga de escritura (rango Consejo: 2–5×)
- Writer throughput degradación **≤ 20%** con reader activo (rango: 20–50%)
- Si reader p99 > 5× o writer degradación > 50% → reevaluar arquitectura

| Owner | [asignar ingeniero de query / correlación] |
| Deadline | Día 196 (14 días) — puede paralelizarse con B1–B4 |
| Dependencia | B1 (WAL recovery, para no perder datos del smoke) |
| Debt nuevo | DEBT-KUZU-CONCURRENCY-SMOKE-001 (upgrade del smoke actual) |

---

## GUARDAS NOW BARATAS (no esperan a Gate B)

Estas acciones tienen coste ≈cero y mitigan riesgos inmediatamente:

**G1 · Q4 — Capar `bufferPoolSize` en init**
- Acción: en constructor de Database, leer RAM física del host y setear `bufferPoolSize = min(0.7 * RAM, 4GB)` (o configurable vía env var)
- Efecto: convierte "OOM lineal" en "thrashing paginado" — medible, no fatal
- Coste: 1 línea en init. No bloquea, no espera
- Owner: [infraestructura C++]

**G2 · Q8 — Invariante de shard-agnostic (coste cero)**
- Acción: (a) `getRoutingKey()` explícito en el evento (`community_id` ya lo es). (b) Correlador lee tras `IGraphQuery`/`GraphRepository`, NO tras `kuzu::Connection` concreto. (c) `DatabaseRegistry` de B3 ya habilita N paths.
- Efecto: sharding es add-on, no reescritura
- Coste: refactor menor de interfaces (ya parcialmente hecho con `IGraphSink`)
- Owner: [arquitecto / lead]

---

## HARDENING DIFERIDO (ADR-041 / Fase 1)

Items que **NO bloquean Gate B** pero requieren medición antes de producción real:

| ID | Item | Experimento | Debt |
|---|---|---|---|
| H1 | Q1 — Descomposición ×61 | tmpfs vs disco aísla S; prepared-statement aísla P. Correr en N100. Métrica: `Delta_fsync = (T_disco − T_tmpfs) / T_disco`. >0.85 → fsync domina; <0.30 → estructural. | DEBT-KUZU-PERF-CALIBRATION-001 |
| H2 | Q4 — Curva RSS + tiering | A `bufferPoolSize` FIJO (2 GB), correr 1M nodos. Confirmar NO OOM. Medir degradación latencia por thrashing. Curva tamaño-en-disco vs nodos. Estrategia: Hot (Kuzu) → Warm (Parquet/DuckDB) → Cold (S3/minio). | DEBT-KUZU-MEMORY-TIERING-001 |
| H3 | Q6 — Sweep batch size | Sweep batch ∈ {1, 10, 100, 300, 500, 1000, 2500, 5000, 10000} midiendo throughput + staleness p99 + RSS + blast-radius. Predicción: codo en 300–500. | DEBT-BATCH-SWEEP-001 |
| H4 | Q10 — Backpressure | Producer = 2× writer durante 30 min. Medir RSS, profundidad de cola, pérdida, staleness. Política explícita: drop-oldest / block-producer / spill-a-disco. | DEBT-INGEST-BACKPRESSURE-001 |

---

## LEDGER DE CORRECCIONES ADOPTADAS

**El Consejo nos corrigió:**
- ✅ Gate real = sink/afirmación production-ready, no solo schema (7/8 acertaron)
- ✅ Q9: `DatabaseRegistry` (`path→weak_ptr`) > singleton ciego (ChatGPT). Reconcilia Q8.
- ✅ Q10: backpressure es hueco real (ChatGPT solo lo vio)

**Nosotros corregimos al Consejo:**
- ✅ Q7: WAL huérfano fue auto-infligido; ninguno de los 7 lo detectó
- ✅ Q4: "1M=8GB lineal" es extrapolación sin medir; `bufferPoolSize` lo acota
- ✅ Q1: descomposición E≈88 µs, P+S≈5.93 ms calculada desde las dos runs. Recoloca Q1 de "bloqueante" a "calibración"

---

## TIMELINE VISUAL

```
DAY 182  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  Gate A SALE YA (schema/ingest) — sin condición                  │
         │  G1 (cap pool) y G2 (shard seam) — hoy, coste cero               │
DAY 183  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  B1 (WAL), B2 (poison), B3 (registry), B4 (flush) — INICIO      │
DAY 189  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  DEADLINE B1–B4 (7 días)                                         │
         │  Si alguno falla → NO merge del sink. Replanificar.              │
DAY 190  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  B5 (reader real) — INICIO (paralelo si recursos)                │
DAY 196  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  DEADLINE B5 (14 días desde DAY 182)                             │
         │  Si B5 falla → "lectura sana" cae; reevaluar D4.                 │
DAY 197+ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         │  Gate B CERRADO → merge del sink production-ready                │
         │  H1–H4 en ADR-041 (Fase 1) — hardening medible                  │
```

---

## CHECKLIST DE MERGE DEL SINK (Gate B)

- [ ] B1: `restore_from_wal_smoke_test` pasa (100 SIGKILLs, 0% pérdida, ≤5s recovery)
- [ ] B2: bisección + validación en borde pasa (0% pérdida legítima, ≤10% overhead)
- [ ] B3: `DatabaseRegistry` test pasa (2º `open()` lanza, <1µs lookup, 0 corrupción)
- [ ] B4: flush-by-time smoke pasa (staleness p99 ≤1s, degradación ≤15%)
- [ ] B5: reader real smoke pasa (reader p99 ≤2× idle, writer degradación ≤20%)
- [ ] G1: `bufferPoolSize` capado en init (configurable, ≤70% RAM)
- [ ] G2: `getRoutingKey()` + `IGraphQuery` seam (shard-agnostic)

**Si cualquier □ es NO → Gate B permanece CERRADO. No hay excepciones.**

---

## NOTAS PARA SIGUIENTES INSTANCIAS

1. **La pregunta "bloqueante para Fase 0" debe especificar SIEMPRE el gate:** "bloqueante para commit de schema" vs "bloqueante para merge del sink". La ambigüedad generó 7 vs 1 en la primera ronda.

2. **"Extrapolación lineal sin medir" es un voto, no una medida.** La regla de la sesión aplica también a las objeciones del Consejo.

3. **El ledger honesto debe publicarse en cada acta.** La corrección mutua es señal de salud, no de debilidad.

4. **Q10 (backpressure) demuestra que 8 cabezas no ven todo.** Mantener la regla: *"no quiero consenso, quiero el agujero que los demás no vieron."*

---

> *"La documentación es un voto; el smoke es una medida. Y cuando ocho consejeros votan que algo es lineal sin medirlo, eso también es un voto."* — Síntesis DAY 182

FDO · KIMI
