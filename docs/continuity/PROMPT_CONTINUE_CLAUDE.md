# Prompt de continuidad — DAY 184 (aRGus NDR)

Soy Alonso, investigador solo en Badajoz construyendo **aRGus NDR** (C++20, NDR open-source
embebido para hospitales/infraestructura crítica), con Dr. Andrés Caro Lindo (UEx/INCIBE).
Sesiones de madrugada. **Consejo de Sabios** (8 modelos) como revisión adversarial.
Principios: **"medir, no votar"**, **Via Appia Quality**, honestidad científica por encima de todo.

Repo: `/Users/aironman/CLionProjects/test-zeromq-docker`.
Branch: `feature/day183-kuzu-sink-unwind-flush` (creada en DAY 183 desde main tras el merge
del PR#100). **Invariante de build:** SIEMPRE `make <target>` desde el host macOS; NUNCA
`cmake` directo ni `vagrant ssh -c` envolviendo un `make`. **EMECAS** = `vagrant destroy -f &&
vagrant up && make bootstrap && make test-all`. **Kuzu** v0.11.3, embebido tras `IGraphSink`,
BD en `/tmp` guest-nativo (vboxsf rompe el mmap).

---

## QUÉ PASÓ EN DAY 183 (cerrado; commit tras este prompt)

**La BASE del path parametrizado (ADR-057) está PROBADA en BD real, no afirmada.** Cerramos
el punto 2 del camino crítico en su parte fundacional.

- **`cypher_builder.hpp` refactorizado**: `make_bindings()` = fuente única de valores
  derivados (`window`, `temporal_anomaly`), Kuzu-free (lo incluye `LoggingGraphSink`).
  Dos plantillas `kAlert/kTelemetryCypherTemplate` (Cypher NO parametriza labels → 2, no 1).
  `build_cypher` (logging) rebasado sobre `make_bindings` → salida byte-idéntica a DAY 180.
- **`test_cypher_prepared.cpp`** (nuevo, GTest, en `correlation-engine-test` → gate permanente
  en test-components/test-all/EMECAS). 6/6 verde. Zanjado por medición:
    - **VERIFY-1**: UINT64 (sentinela `0xFEDCBA98...` > 2⁶³) y UINT32 round-trip íntegro.
      Sin colapso a INT64.
    - **VERIFY-2**: API real de Kuzu 0.11.3 = `execute(PreparedStatement*, pair<string,Args>...)`.
      **El overload con `unordered_map` NO existe.** Claves `std::string`.
    - **VERIFY-3**: `$flow_uid` reusado coincide en `MERGE(f)` y `e.flow_uid`.
    - **H-1**: `node_id="a'b\c"` vuelve byte-idéntico → inyección Cypher cerrada
      ESTRUCTURALMENTE por el param tipado, no por `esc()`. Lo prometido en ADR-057.

**DOS LECCIONES caras que NO se pierden (las pagamos hoy):**
1. **Bind = variádico de 14 pares por fila**, claves `std::string`. El `bind_params`-devuelve-map
   que esbocé NO aplica. El binder de producción es una función que hace `execute(prep, par1..par14)`.
2. **Ciclo de vida Kuzu**: los `QueryResult` y `PreparedStatement` sostienen refs al BufferManager
   de la `Database`. DEBEN morir ANTES que `conn`/`db`. **Nunca `db.reset()` con un `QueryResult`
   vivo** = el SIGSEGV de hoy (`BufferManager::unpin` sobre FileHandle liberado).

`kuzu_graph_sink.{hpp,cpp}` SIGUE INTACTO — la base se probó aislada. Mañana se cablea.

---

## QUÉ HACER EN DAY 184 — "TODO LO DEMÁS" (camino crítico, en orden)

Recordatorio del eje (punto 3): el objetivo NO es la mejor implementación del grafo, es
**torturar el pipeline** a 33 Mb/s y luego x86 RAW sin perder ni corromper datos. Lo de hoy es
el suelo que protege esa medición.

0. **EMECAS verde de partida** en la rama antes de tocar código (señal limpia).
1. **Cablear el `KuzuGraphSink` real** (esto es el resto del punto 2):
    - Ctor: `prepare()` las DOS plantillas una vez (miembros `prep_alert_`/`prep_telemetry_`,
      forward-decl `PreparedStatement`). Fail-closed si una no prepara.
    - **Binder de producción**: función que hace `conn_->execute(prep.get(), par1..par14)` por
      fila (variádico, claves `std::string`). NO map.
    - **`write()`**: sella `ingest_now_ns()` a la ENTRADA (first_seen, per-fila) y empuja
      `{record, flow_uid, ts}` al acumulador. Devuelve true=aceptado. Flush inline si `size≥N` o
      `now−last_flush≥T`.
    - **`flush()`**: `BEGIN TRANSACTION` → bucle `execute` por fila → `COMMIT` (1 checkpoint por
      batch = la amortización). Fallo → `ROLLBACK`, buffer SE QUEDA (reintento, nunca drop
      silencioso), surface del fallo. Limpia buffer solo en éxito.
      **Orden de vida**: cada `QueryResult` del execute muere dentro del bucle, antes de cerrar nada.
    - **Cambio de contrato `flush()→estado`** (hoy es `void` → oculta fallo de durabilidad).
      Afecta también a `LoggingGraphSink`.
    - Acumulador síncrono mono-hilo = acotado + backpressure POR CONSTRUCCIÓN (el flush inline
      en el mismo hilo frena al productor). NO hay `IngestQueue` async todavía: eso es decisión
      MEDIDA del punto 3, solo si UNWIND/execute-loop síncrono se mide corto en x86 RAW.
    - **Caveat T-en-idle**: el trigger de tiempo no dispara si `write()` deja de llamarse.
      No muerde para reproducir throughput; sí cuando T sea SLA de staleness (→ writer en su
      hilo con tick, frontera del async). Apuntado, diferido.
2. **Decisión a medir, no asumir**: ¿el `execute`-por-fila-en-1-tx alcanza los 10–12k ups/s del
   smoke (UNWIND batch)? Si sí → cerrado. Si corto → recién ahí spike de UNWIND con `LIST<STRUCT>`
   param (sin verificar que 0.11.3 lo soporte).
3. **Diseñar la tortura E2E**: pcap-relay MITRE → correlation-engine → bronce Iceberg → silver →
   gold (join `community_id`) → graph-engine (Kuzu flood). Medir: ¿se pierden filas?, ¿grafo stale?,
   ¿RSS acotada? (pool capado **y** acumulador acotado: dos regiones distintas).
4. **MITRE disjunto (ADR-040)**: A–M (experiencia) vs N–Z (evaluación). Mejora sobre N–Z = publicable.

---

## FRENTES ABIERTOS (no perder)

- **D3 (Arrow vs DuckDB)** sigue abierta. B2 (banco promoción/join silver→gold). ADR-057 §2.7/§3.2.
- **event_id replay-stable (Frente C)**: 8 respuestas del Consejo sin sintetizar.
  `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1): ¿el path de PRODUCCIÓN heredó el reloj inyectado?
- **Extracción graph-engine** (`DEBT-GRAPH-ENGINE-EXTRACTION-001`) cuando se materialice Iceberg.
- **Calibrar margen `temporal_anomaly`** (2s placeholder, `kTemporalMarginNs` en cypher_builder.hpp).
- **Endurecimiento diferido (ADR-057 §8)**: WAL durabilidad, poison/atomicidad, backpressure
  sostenido, reader traversal, memoria a escala, fsync en x86 RAW, shardability. Post-corroboración.
  Insight: los cinco "bloqueantes" son UN problema = cola hacia el writer único = `IngestQueue`.
- **`audit-taint` semgrep en cuarentena** (`DEBT-SEMGREP-CPP-HANG-001`).
- **Higiene BACKLOG**: 7 cabeceras duplicadas preexistentes (no urgente). Pendiente: entrada
  DAY 183 en ADR-057/BACKLOG documentando la base parametrizada + las dos lecciones Kuzu.

---

## EL EJE QUE NO SE NEGOCIA

¿Pueden los modelos ensemble aprender de la experiencia acumulada de los nodos distribuidos y
mejorar con ella? **Se publica salga como salga.** Corroborada → hallazgo. Camino seco → también
hallazgo. **Pase lo que pase, entregamos datasets de valor al equipo de Andrés.** Si el diseño solo
pudiera confirmar, no sería medición.

paper arXiv:2604.04952 · BACKLOG-FEDER-001: sin deadline duro (22-sep-2026 era ritmo); gate real
= datasets de valor científico a Andrés.