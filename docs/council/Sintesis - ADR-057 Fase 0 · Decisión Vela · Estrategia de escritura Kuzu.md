# SÍNTESIS DEL CONSEJO — ADR-057 Fase 0 · Decisión Vela · Escritura Kuzu
## DAY 182 · 8 consejeros (ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen, Claude)
## Orquestación de síntesis: Claude

---

## 0. El meta-hallazgo (léelo antes que nada)

**El Consejo rechazó, casi por unanimidad, la afirmación "ninguna pregunta bloquea Fase 0".** 7 de 8 marcaron entre 4 y 7 preguntas como BLOQUEANTES. La mía fue la voz discrepante ("nada bloquea el merge de schema").

No es que ellos tengan razón y yo no, ni al revés: **la pregunta del paquete estaba mal escrita y nosotros la escribimos.** "Bloqueante para el merge de Fase 0" mezcló dos cosas distintas, y el Consejo, ante la ambigüedad, leyó la grande:

- **Gate A — commit de schema/ingest** (`ingested_at`, `temporal_anomaly`, `ingest_clock`, `cypher_builder`). Ya verde en EMECAS. **Nada de Q1–Q9 lo toca.** Aquí mi lectura era correcta.
- **Gate B — el sink de producción + la afirmación "production-ready"** (UNWIND batch + 1 writer = D1–D4). **Aquí viven todos los bloqueantes.** Aquí el Consejo tiene razón y yo me quedé corto.

**Adopto la corrección:** ADR-057 v2 puede *registrar* la dirección D1–D4 (es sólida y unánime) pero debe marcar la implementación del sink como **GATED por una batería de 5 bloqueantes**, no como "hecho". El smoke midió el mejor caso; la producción es el peor.

---

## 1. Matriz de veredictos (quién atacó qué)

`B`=bloqueante · `H`=hardening · `C`=condicional · `N`=no bloquea · `—`=no lo planteó

| Q | ChatGPT | DeepSeek | Gemini | Grok | Kimi | Mistral | Qwen | Claude | **Síntesis** |
|---|---|---|---|---|---|---|---|---|---|
| Q1 ×61 | B | B* | H | H | N | B | B | H | **CONTESTADA** (4B/4H) |
| Q2 staleness | B | B | B | B | B | B | B | B* | **BLOQUEANTE** (8/8) |
| Q3 reader | B | B | B | B | B | B | B | B* | **BLOQUEANTE** (8/8) |
| Q4 memoria | B | B | H | B | C | H | C | H* | **CONTESTADA** (lean H con cap) |
| Q5 poison | B | B | B | B | B | B | B | B | **BLOQUEANTE** (8/8) |
| Q6 batch=1000 | B | C | H | H | N | B | H | N | **CONTESTADA** (lean H) |
| Q7 WAL | B | B | B | B | B | B | B | B | **BLOQUEANTE** (8/8) |
| Q8 sharding | H | B | H | H | H | H | C | N | **DIFERIDA + invariante** |
| Q9 footgun | B | B | B | B | B | B | B | B | **BLOQUEANTE** (8/8) |
| Q10 backpressure | **B** | — | — | — | — | — | — | — | **NUEVA** (solo ChatGPT) |

`*` = el matiz de Claude (no "B de Fase 0" sino "B del sink/afirmación").

---

## 2. Los 5 bloqueantes de consenso → batería pre-merge del sink

Estos cinco son la condición para declarar el sink production-ready. 8/8 (o 7/8) de acuerdo. Cada uno con el experimento y el número que el propio Consejo convergió:

### B1 · Q7 — Recuperación del WAL (prioridad #1)
- **Acción:** quitar `cleanup_db` del path de producción (queda SOLO en el smoke-como-herramienta). Implementar `restore_from_wal_smoke_test`: riada → `kill -9` a media tx → reabrir **sin borrar nada** → Kuzu debe replayar el WAL nativo.
- **Número:** 0 commits ackeados perdidos tras **≥100** SIGKILLs; recuperación ≤5 s para ventana de 100k.
- **Debt:** DEBT-LABEL-WAL-001 → bloqueante.
- **Nota mía que sostengo:** el `unordered_map::at` del incidente fue **auto-infligido** (borramos `.kuzu`, dejamos `.wal` huérfano), NO prueba de fallo de recuperación de Kuzu. Ninguno de los otros 7 lo detectó — todos tomaron el incidente como evidencia de un bug que no está demostrado. El test real (ambos ficheros intactos) dirá la verdad; partimos de "sin evidencia de fallo", no de "Kuzu roto".

### B2 · Q5 — Atomicidad / flow envenenado
- **Acción:** confirmar rollback total de UNWIND (todos lo dan por ACID estricto); implementar **bisección recursiva** ante fallo (batch→/2→/2…→aísla la fila tóxica→`quarantine.log`→commitea el resto) + **validación en el borde** ANTES del UNWIND.
- **Número:** 0% pérdida de detecciones legítimas; overhead ≤10%.
- **Conexión:** la validación en el borde enlaza con tu patch **H-1** (`cypher_builder.hpp`) ya hecho — la inyección está cerrada; el vector restante es semántico.
- **Debt:** DEBT-KUZU-BATCH-POISON-001 (nuevo) → bloqueante.

### B3 · Q9 — Guarda del footgun (con un giro que reconcilia Q8)
- **Acción:** **`DatabaseRegistry` (path→`weak_ptr<Database>`)**, no un singleton ciego. Construcción fuera del registry = imposible; 2º `open()` del MISMO path lanza.
- **Número:** test `EXPECT_THROW` en 2ª apertura del mismo path; coste <1 µs.
- **Insight de síntesis (lo vio ChatGPT, lo elevo):** un singleton puro asume *un* path para siempre → **mataría el sharding de Q8**. Un registry `path→weak_ptr` impone "1 path = 1 Database" PERO permite N paths distintos → **la guarda de Q9 y la shardability de Q8 se resuelven con la MISMA pieza.** No uses singleton.
- **Debt:** DEBT-KUZU-SINGLE-DATABASE-GUARD-001 → bloqueante.

### B4 · Q2 — Staleness / flush-by-time
- **Acción:** `flush(size>=N OR age>=T_ms)` con hilo `Ticker` asíncrono. Medir staleness e2e (paquete→consultable) p99 a **1/3/10 flows/s**.
- **Número (convergencia del Consejo):** SLO staleness p99 — propuestas 500 ms (Grok) … 1 s (ChatGPT/Mistral/Qwen/Gemini) … 2–5 s (Kimi/Qwen). **Centro: `flush_interval_ms = 1000` estándar, 100 ms crítico.** Degradación throughput ≤15%. Calibra el SLO en ADR-057.
- **Debt:** DEBT-KUZU-WRITE-BATCHING-001 (extendido con time-flush) → bloqueante.

### B5 · Q3 — Reader real (no `count(*)`)
- **Acción:** sustituir `count(*)` por UNA traversal de correlación canónica (2–3 hops por `community_id`); remedir contención p50/p99 **y** si el lector pesado frena al writer.
- **Número (rango del Consejo):** read p99 ≤ **2–5×** idle bajo carga; degradación del writer ≤ **20–50%**. Fuera de eso, "lectura sana" (D4) cae.
- **Honestidad:** hasta esto, "la lectura se mantiene sana" va al acta como **provisional**, no como hecho.
- **Debt:** upgrade del smoke (DEBT-KUZU-CONCURRENCY-SMOKE-001).

---

## 3. Las 3 contestadas → un experimento zanja cada una

### Q1 — ¿×61 estructural o artefacto de VM? (4B / 4H)
- **Mi aporte cuantitativo (único en el Consejo):** de tus dos runs, `coste(n)=P+S+n·E` → **E ≈ 88 µs/fila** (ejecución real), **P+S ≈ 5.93 ms** (fijo amortizable). El ×61 es *enteramente* amortizar ese fijo.
- **Lo que mi math NO separa:** P (parse/plan) de S (fsync). Ahí el Consejo tiene razón: falta el experimento.
- **Experimento convergente:** tmpfs vs disco aísla S (Gemini: `Delta_fsync=(T_disco−T_tmpfs)/T_disco`); prepared-statement aísla P. Correr en N100.
- **Número:** si `Delta_fsync>0.85` → fsync domina → el ×61 se encoge en metal real (mi apuesta: ~×13) **pero batching sigue ganando** (amortiza parse/plan). Si <0.30 → estructural (Kimi).
- **Veredicto de síntesis:** **calibración, NO gate de merge.** La *dirección* D1 es invariante al hardware; el *multiplicador* exacto es Fase 1/ADR-041.

### Q4 — Memoria a escala (lean Hardening, con guarda NOW)
- **El humo del Consejo:** "1M nodos = 8 GB lineal → OOM → bloqueante" lo afirmaron ChatGPT/DeepSeek/Grok/Mistral/Qwen **por extrapolación lineal, sin medir**. Es, irónicamente, **un voto, no una medida** — justo lo que la regla prohíbe.
- **La refutación (yo + Gemini explícito + Kimi parcial):** Kuzu es GDB **en disco con buffer manager configurable**. Los 822 MB son el pool por defecto, no f(nodos). Capando `bufferPoolSize`, **RSS NO puede exceder el cap** (Kuzu pagina a disco). No hay OOM lineal.
- **Acción NOW (barata, Gemini la llama "pre-requisito"):** capar `bufferPoolSize` en init según RAM del host. Eso convierte Q4 en hardening.
- **Experimento real:** a `bufferPoolSize` FIJO (p.ej. 2 GB), correr 1M nodos → confirmar que NO hay OOM y medir la **degradación de latencia por thrashing** (ese es el riesgo real, no el RSS). Curva tamaño-en-disco vs nodos para planificar retención.
- **Veredicto de síntesis:** **hardening + guarda NOW (capar el pool).** El tiering hot→cold (Parquet/DuckDB) → ADR-041.

### Q6 — batch=1000 mágico (lean Hardening)
- **Mi predicción analítica:** overhead fijo amortizado = (5.93 ms)/batch vs 88 µs/fila de ejecución. Codo donde el overhead cae bajo ~20%: **batch ≈ 300–500**, no 1000. A 10000 no compras throughput y empeoras staleness/blast-radius.
- **Experimento convergente:** sweep `batch∈{1,10,100,300,500,1000,2500,5000,10000}` midiendo a la vez throughput + staleness p99 + RSS + blast-radius. Codo donde Δthroughput<5%.
- **Veredicto de síntesis:** **hardening; correr ANTES de fijar la constante del sink.** Predicción: bajará de 1000 a ~300–500 por seguridad operativa (Q2/Q5).

---

## 4. Q8 — Sharding: diferida CON invariante (barata hoy)

- **La adjudicación más fina la dio Qwen:** sharding solo se "cierra" si la invariante de routing NO se mantiene hoy. **Pero `community_id` YA es tu clave de correlación primaria (ADR-046)** → la invariante de routing **ya existe**. Eso baja Q8 de "peligro" a "diferible barato".
- **Acción NOW (≈coste cero):** (a) `getRoutingKey()` explícito en el evento (Gemini); (b) el correlador lee tras `IGraphQuery`/`GraphRepository`, NO tras `kuzu::Connection` concreto (espejo de tu `IGraphSink`). El `DatabaseRegistry` de B3 ya habilita N paths.
- **Veredicto:** difiere la implementación; **NO difieras el seam.** No bloquea.

---

## 5. Q10 — Backpressure (el hueco que solo vio ChatGPT)

- **La objeción:** el ADR asume implícito `producer_rate ≤ writer_rate`. ¿Qué pasa con 50k eventos/s entrando 20 min y el writer absorbiendo 10k/s? Cola infinita → OOM. El smoke corrió saturado pero **nunca probó sobrecarga sostenida con cola acotada.**
- **Por qué importa para NDR:** un flood (scan storm, DDoS) es exactamente cuando NO puedes quedarte ciego ni reventar por memoria. "Throughput alto sin backpressure es estable solo mientras todo va bien; los sistemas críticos se diseñan para cuando no va bien."
- **Experimento:** producer = 2× writer durante 30 min; medir RSS, profundidad de cola, pérdida de eventos, staleness. **Invariante:** RSS acotada + política de backpressure explícita (drop-oldest / block-producer / spill-a-disco), no crecimiento infinito.
- **Debt:** DEBT-INGEST-BACKPRESSURE-001 (nuevo, **crédito ChatGPT**). Probable bloqueante de producción; mínimo, debt con nombre y experimento.

---

## 6. Ledger honesto (quién corrigió a quién)

**El Consejo nos corrigió:**
- El gate real es el sink/afirmación production-ready, no solo el schema (7/8). Mi "nada bloquea" estaba demasiado estrecho.
- **Q9 registry > singleton** (ChatGPT) — mejor que mi "lanzar en 2ª construcción", y además reconcilia con Q8.
- **Q10 backpressure** (ChatGPT) — hueco real que yo no vi.

**Nosotros corregimos al Consejo:**
- **Q7:** el WAL huérfano fue auto-infligido; no hay evidencia de bug de recuperación de Kuzu. Ninguno de los 7 lo vio.
- **Q4:** "1M=8 GB lineal" es extrapolación sin medir; `bufferPoolSize` lo acota. Gemini lo confirma de forma independiente; el resto votó.
- **Q1:** la descomposición `E≈88 µs, P+S≈5.93 ms` la calculé solo yo desde tus dos runs; recoloca Q1 de "bloqueante" a "calibración".

**Lo que NADIE discute:** D1 (UNWIND batch) y D2 (Vela no) son la dirección correcta — unánime. El commit de schema/ingest sale ya.

---

## 7. Plan de cierre → ADR-057 v2 + acta

**Sale ya (Gate A):** commit de schema/ingest (independiente, verde).

**Batería pre-merge del sink (Gate B), por orden de prioridad:**
1. **B1 Q7** WAL recovery (durabilidad — #1, y upstream archivado = sin red).
2. **B2 Q5** bisección + validación en borde (DoS por envenenamiento).
3. **B3 Q9** `DatabaseRegistry` (corrupción; reconcilia Q8).
4. **B4 Q2** flush-by-time (ceguera a bajo caudal).
5. **B5 Q3** reader de correlación real (validar "lectura sana").

**Guardas NOW baratas (no esperan a la batería):**
- Capar `bufferPoolSize` en init (Q4).
- `getRoutingKey()` + `IGraphQuery` seam (Q8).

**Hardening medible (ADR-041 / Fase 1):**
- Q1 descomposición fsync/parse en N100 · Q4 curva RSS+tiering · Q6 sweep de batch.

**Nuevo en backlog:** DEBT-KUZU-BATCH-POISON-001, DEBT-INGEST-BACKPRESSURE-001; renombrar el gate de Q4 a "cap pool NOW + curva luego".

> *La documentación es un voto; el smoke es una medida. Y cuando ocho consejeros votan que algo es lineal sin medirlo, eso también es un voto.* — Síntesis DAY 182
> 
> FDO
> 
> Alonso y Claude.