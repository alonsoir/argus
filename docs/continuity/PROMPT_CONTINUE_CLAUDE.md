# Prompt de continuidad — DAY 183 (aRGus NDR)

Soy Alonso, investigador solo en Badajoz construyendo **aRGus NDR** (C++20, NDR open-source
embebido para hospitales/infraestructura crítica), colaborando con Dr. Andrés Caro Lindo
(UEx/INCIBE). Trabajo en sesiones de madrugada. Uso el **Consejo de Sabios** (8 modelos:
Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) como revisión adversarial.
Principios: **"medir, no votar"**, **Via Appia Quality** (construir para durar), honestidad
científica por encima de todo.

Repo: `/Users/aironman/CLionProjects/test-zeromq-docker`. Branch:
`feature/day170-community-id-protobuf`. **Invariante de build:** SIEMPRE `make <target>` desde
el host macOS; el Makefile hace `vagrant ssh -c` internamente; NUNCA `cmake` directo (riesgo
`.pb.h` rancio) ni `vagrant ssh -c` envolviendo un `make` (el binario vagrant no está en el
guest). **EMECAS** = `vagrant destroy -f && vagrant up && make bootstrap && make test-all`.
**Kuzu** v0.11.3 (upstream archivado oct-2025, pin SHA256), embebido tras `IGraphSink`,
BD en `/tmp` guest-nativo (vboxsf rompe el mmap de Kuzu).

---

## QUÉ PASÓ EN DAY 182 (lo que cierro hoy)

**El smoke `DEBT-KUZU-CONCURRENCY-SMOKE-001` se EJECUTÓ y MIDIÓ. D1 y D2 quedan RESUELTAS POR
MEDICIÓN.** Esto es B1 del ADR-057 ejecutado, no "production-readiness".

- **D1 = UN GRAFO** (no N grafos por eje). run3 (4 writers) = 373k rechazos por la única
  write-tx del sistema, +37% throughput, lectura p99 ×11.37. Multi-writer NO escala. Sharding
  futuro —si lo hubiera— TEMPORAL, nunca semántico.
- **D2 = KUZU STOCK, VELA NO.** El cuello era el overhead por-`query()` (parse/plan+fsync por
  llamada), no el escritor único. **UNWIND batch (1 query = N upserts) → ×55–61** (164–229
  ups/s con MERGE-por-fila → 10.000–12.200 con UNWIND batch=1000). Vela solo añade writers
  paralelos = exactamente lo que no escala. Reconsiderar Vela SOLO si UNWIND+1writer se mide
  corto en hardware real.
- **Descomposición:** `coste(n)=P+S+n·E`, E≈88µs/fila (MERGE irreducible), P+S≈5.93ms (fijo,
  amortizable). El ×55–61 es amortizar el coste fijo de 1-por-fila a 1-por-1000.
- **Lock:** cross-proceso rechazado (exit=2 ✅); in-process 2º Database ABRE (footgun →
  corrupción) → `DatabaseRegistry` obligatorio.
- **Corrección honesta mía (la cacé yo, no los otros 7):** el `unordered_map::at` al reabrir
  tras crash fue AUTO-INFLIGIDO (borré el `.kuzu` y dejé el `.wal` huérfano = inconsistencia
  artificial). NO es prueba de que Kuzu no recupere. La recuperación real sigue sin validar
  (diferida).

**Fase 0 del grafo VERDE (EMECAS):** `ingested_at` (first_seen, wall clock deliberado, distinto
del bpf_ktime envenenable) + `temporal_anomaly` unilateral (futuro-datación = firma de
clock-injection, margen 2s PLACEHOLDER a calibrar) + `build_cypher(ingested_at_ns)` (función
libre, testeable, `locale::classic()`, cierra inyección Cypher H-1). Tres guardas que protegen
LA MEDICIÓN: sink UNWIND-batch + flush-by-(size|time), `DatabaseRegistry`, `bufferPoolSize`
capado. `DEBT-CE-TESTS-UNGATED-001` cerrada (test-components corre correlation-engine-test 1º).

**Decisión arquitectónica importante:** `correlation-engine` y `graph-engine` son DOS
componentes, separados por **Apache Iceberg** (gobierna LZ bronce/plata/oro). correlation-engine
alimenta bronce; graph-engine lee GOLD y es dueño del `.kuzu`. Las clases de grafo viven hoy en
correlation-engine pero hay que extraerlas → `DEBT-GRAPH-ENGINE-EXTRACTION-001`.

**Entregables DAY 182 (en /mnt/user-data/outputs/ de la sesión y a aplicar al repo):**
1. `ADR-057-v2.md` → reemplaza `docs/adr/ADR-057: ...V2.md`. D1+D2 resueltas, §3.0 con tabla
   run1/2/3, §3.1 Fase 0, §2.8 sin índice de rango, §8 endurecimiento diferido, componente
   renombrado graph-engine.
2. `BACKLOG-day182-bloque.md` → pegar al inicio de las entradas DAY de `docs/BACKLOG.md`.
   Paraguas CONCURRENCY-SMOKE con 8 sub-ejes diferidos + GRAPH-ENGINE-EXTRACTION +
   CE-TESTS-UNGATED cerrada. (Asumí dedup; verificar con
   `grep '^## ' docs/BACKLOG.md | sort | uniq -d` — debe salir vacío.)
3. `README-day182-edits.md` → 3 str_replace (fecha, tabla DAY-STATUS, hitos+milestone).
4. Este prompt.
5. LinkedIn post (inglés) — pendiente de tu OK sobre el ángulo.

---

## QUÉ HACER EN DAY 183 (el camino crítico, en orden)

**El objetivo NO es la mejor implementación del grafo. Es torturar el pipeline.** A 33 Mb/s
(techo de la NIC virtual de Vagrant) y luego más en un **servidor x86 RAW** en la misma red,
fuera de Vagrant. El andamiaje tiene que tragar esa riada sin perder ni corromper datos del
experimento. Eso es lo que las 3 guardas de Fase 0 protegen.

1. **Aplicar los 5 entregables al repo** (ADR-057 v2, BACKLOG, README, commit). EMECAS verde
   antes de seguir.
2. **Cablear el sink real con UNWIND batch + flush-by-(size|time)** en el camino vivo
   (hoy el smoke lo probó aislado; falta que el `KuzuGraphSink` de producción lo use). Esta es
   la pieza que convierte el ×55–61 medido en throughput real del pipeline.
3. **Diseñar la tortura E2E:** pcap-relay MITRE → correlation-engine → bronce Iceberg →
   silver → gold (join por `community_id`) → graph-engine (Kuzu COPY+upsert flood). Medir:
   ¿se pierden filas?, ¿el grafo va stale?, ¿RSS acotada por el pool?
4. **MITRE disjunto (no negociable, ADR-040):** escenarios A–M (experiencia/entrenamiento) vs
   N–Z (evaluación, no vistos). Mejora sobre N–Z = publicable; solo sobre A–M = overfitting.

---

## FRENTES ABIERTOS (no perder)

- **D3 (Arrow vs DuckDB) SIGUE ABIERTA.** El smoke de Kuzu NO la toca. Se resuelve con B2
  (banco de promoción/join silver→gold + scan dataset). Sin ejecutar. ADR-057 §2.7/§3.2.
- **event_id replay-stable (Frente C):** 8 respuestas del Consejo desde DAY 180, veredicto SIN
  sintetizar. `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1). Verificar si el path de PRODUCCIÓN
  heredó el reloj inyectado del build de cross-check.
- **Extracción graph-engine** (`DEBT-GRAPH-ENGINE-EXTRACTION-001`) cuando se materialice Iceberg.
- **Calibrar margen `temporal_anomaly`** (2s placeholder) con dato real.
- **Endurecimiento diferido (ADR-057 §8, bajo el paraguas CONCURRENCY-SMOKE):** durabilidad WAL
  (Q7), poison/atomicidad (Q5), backpressure sostenido (Q10), reader real traversal (Q3),
  memoria a escala+tiering (Q4), batch sweep (Q6), decomposición fsync en x86 RAW (Q1),
  shardability (Q8). TODO esto es post-corroboración / pre-despliegue. NO es camino crítico del
  experimento. Insight: los cinco "bloqueantes" del Consejo son UN problema — gestionar una cola
  hacia un único consumidor de tasa fija (el writer único de Kuzu) = subsistema `IngestQueue`.
- **`audit-taint` semgrep en cuarentena** (`DEBT-SEMGREP-CPP-HANG-001`).

---

## EL EJE QUE NO SE NEGOCIA (recordatorio para mí mismo)

La hipótesis fundamental: ¿pueden los modelos ensemble (árboles) aprender de la experiencia
acumulada que han visto los nodos distribuidos y mejorar con ella? **El resultado se publica
salga como salga.** Corroborada con estos datos → hallazgo. Camino seco con estos otros datos →
también hallazgo (lo escribimos en el paper, buscamos otra hipótesis en el futuro). **Pase lo
que pase, entregamos datasets de valor al equipo de Andrés.** La decisión de publicar una cosa
u otra NO depende de tener la mejor implementación del grafo. Si el diseño solo pudiera
confirmar, no sería medición, sería búsqueda de confirmación.

paper arXiv:2604.04952 · BACKLOG-FEDER-001: sin deadline duro (22-sep-2026 era ritmo); gate real
= demostrar datasets de valor científico a Andrés.