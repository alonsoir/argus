# PROMPT DE CONTINUIDAD — DAY 199 (continúa DAY 198)
# Instrucciones generales para Claude:

1. Piensa antes de codificar  
Expón tus suposiciones. Pregunta cuando no estés seguro. Nunca adivines.

2. Simplicidad primero  
Escribe el código mínimo que resuelva el problema.  
Sin abstracciones que nadie pidió.

3. Cambios quirúrgicos  
No toques código no relacionado con la solicitud.  
Cada línea cambiada debe rastrearse hasta lo que se pidió.

4. Ejecución orientada a metas  
Convierte instrucciones vagas en criterios de éxito verificables  
antes de escribir una sola línea.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (commit de doc no pasa el gate de build).
- **Consejo de Sabios** (8 modelos) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura, NUNCA `open(p,'w')` y `read()` en la misma expresión: trunca a 0) para editar ficheros en macOS · NUNCA `sed -i` en macOS · `vagrant ssh -c` para todo comando del VM · commits/push desde el HOST (el guest Debian no tiene identidad git/GitHub).
- Un día, una batalla.

## DAY 200 — TAREA 1 (bloqueante, antes de Eslabón 0): reconciliar docs/BACKLOG.md con las deudas del circuito. 
Medido DAY 199 (grep -c contra el fichero): de las ~19 deudas que ADR-058 §6 cita como existentes, solo 2 tienen entrada
formal en BACKLOG.md (DEBT-FLOWUID-SEQ-COLLISION-001, DEBT-FLOWUID-CANONICAL-ENCODING-001). 
El resto existe como mención en ADR/plan/actas, no como entrada de backlog. 
Trabajo: (a) 4 deudas nuevas del V3, todas P1 — DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001, 
DEBT-CIRCUIT-PARSER-CROSSLANG-001, DEBT-EVENT-ID-FACTORY-001, y reclasificación P2→P1 + alcance ampliado de
DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001; (b) deudas DAY 196-199 del circuito que faltan — 
al menos DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001, DEBT-CONFIG-BRONZE-HARDCODE-001, DEBT-GOLD-NODE-DIMENSION-001 
(ampliada con flow_start_window), DEBT-GOLD-INTEGRITY-HMAC-001, DEBT-ZMQ-DELIVERY-GUARANTEE-001, 
DEBT-HOST-DOMAIN-CONTRACT-001, DEBT-PARQUET-KUZU-CONNECTOR-001 (ampliada con orden Flujo B), 
DEBT-CIRCUIT-FS-DROP-001, DEBT-PARSE-VERIFY-SENTINEL-001 (degradada P0→P2),
DEBT-ADAPTERSPEC-ENVELOPE-001, DEBT-DOCS-MEDALLION-DUALITY-001, DEBT-JOIN-CONFIDENCE-001; 
(c) resolver drift de ID: ADR-058 cita DEBT-NEO4J-FLOW-KEY-COMPOSITE-001; 
el backlog tiene DEBT-NEO4J-FLOW-KEY-001 (DAY 170). Decidir canónico.
MÉTODO (lección DEDUP, DAY 158, no negociable): una sola pasada, fuente canónica de cada deuda decidida ANTES de escribir 
(preferir la definición más completa del plan del circuito sobre reinventar), script append-only idempotente que aborta 
si el nombre ya existe, gate de cierre grep '^### DEBT\|^## ' docs/BACKLOG.md | sort | uniq -d = 0. NO cat >> a mano. 
Eslabón 0 (config bronce JSON + watcher inotify/IN_CLOSE_WRITE + escritura atómica .tmp→rename, 
cierra DEBT-CONFIG-BRONZE-HARDCODE-001 + DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001) pasa a DAY 201. 

Recordar: la atomicidad es de ROTACIÓN (cambio de día), NO de append.

## Estado al cierre de DAY 198
- **GATE DEL CIRCUITO CERRADO 9/9 CONTRA BYTES.** Las 9 verificaciones medidas, cero apoyo en memoria:
    1. `flow_start_window` es **derivada** (writer escribe sec+nano `correlation_writer.cpp:88-89`; reader computa window en read-time `main.cpp:117`). Decisión: **materializar en oro como columna hash-input** (precondición Via Appia). `DEBT-GOLD-NODE-DIMENSION-001` ampliada.
    2. Centinela `-1`: **FANTASMA en puertos**. Proto `uint32` e2e (`network_security.proto:105-106`), sniffer usa `0` para ICMP (`test_community_id.cpp:62`), writer copia directa (`correlation_writer.cpp:91-92`), reader `from_chars` acepta `0`. `DEBT-PARSE-VERIFY-SENTINEL-001` **degradada P0→P2**. Riesgo residual: `flow_start_sec`/`nano` son signed (`int64/int32`), `-1` sobrevive como valor (semántico, P2).
    3. Writer rota por fecha (`correlation_writer.cpp:177`), reader abre handle fijo (`main.cpp:104`), `--follow` no sigue rotación (`main.cpp:125-132`) → **roja BENIGNA**, Eslabón 0 parchea. P0: `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`, `DEBT-CONFIG-BRONZE-HARDCODE-001`.
    4. day194: PR #107 mergeado (`77a3de9c`), no-bloqueo.
       5-6. Sniffer/writer puerto sin centinela negativo.
    7. Verbo Cypher = **MERGE** ambos paths (`cypher_builder.hpp:100,154`), solo `ON CREATE SET`, cero `ON MATCH` → equivalencia robusta a colisión `flow_uid` (segundo flujo descartado idéntico en ambos caminos). Colisión = fidelidad P2, NO equivalencia.
    8. Interpolación L154 vive solo en `build_cypher()`/logging (`logging_graph_sink.cpp:27`), no toca BD; producción usa prepared `$param` → **ADR-057 intacto**.
    9. Encoding `flow_uid` **canónico** (`flow_uid.hpp`): BLAKE2b-256 sin truncado, length-prefix `uint16` BE por string, window/seq enteros BE de ancho fijo, tag `"argus-flowuid-v1"` (16B), **paridad C++↔`hashlib.blake2b` congelada**. `DEBT-FLOWUID-CANONICAL-ENCODING-001` **resuelta de facto**.
- **ADR-058 commiteado en `day196`** (commit `47d0a8d6`, 315 líneas, LF puro). Fichero: `docs/adr/ADR-058-circuito-completo-aguas-abajo.md`. Pendiente: **push de `day196` + PR del circuito + subir al Consejo para ratificación 9/9**.
- **HIGIENE DOCUMENTAL MERGEADA** (PR `88ee842d` → main): 49 renames `(100%)`, `docs/adr` canónico `ADR-NNN[-vN]-slug.md`, `docs/debt`+`docs/backlog` consolidados, `docs/debts` eliminado, historia git preservada. `day196` ya trae la higiene vía fast-forward (`ddc9f754..68031662`). Rama `day198/docs-adr-naming-hygiene` borrable.

## Decisión VIVA para el Consejo
Una sola, consciente (no hueco): **tolerancia ε en los 3 scores double** (cols 14-16) del predicado de equivalencia §3.1 del ADR-058. El path de producción usa binding nativo (sin pérdida); el Flujo A+B serializa double→Parquet→double (no bit-exacto). El predicado compara con ε, no bit-a-bit. No medible hasta que exista el Flujo A. El Consejo lo ratifica como criterio del test de equivalencia.

## Acciones DAY 199 (en orden)
1. **[push pendiente]** `git push -u origin day196/circuit-adapters-zmq` (desde el host). Abrir PR del circuito. Subir ADR-058 al Consejo.
2. **→ Eslabón 0 (primera implementación real del circuito):** config bronce a JSON (`bronze_root` + patrón naming, calcado de `csv_writer` `config_loader.cpp:455`) + watcher `inotify`/`IN_CLOSE_WRITE` + escritura atómica `.tmp`→rename + cierre por tiempo absoluto. Cierra `DEBT-CONFIG-BRONZE-HARDCODE-001` + `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (ambas P0). El ADR-058 es el commit de apertura del mismo PR.
3. Tras Eslabón 0 verde → **Eslabón 1** (Flujo A: bronce→AVRO→Parquet oro, greenfield) con `flow_start_window` materializada + HMAC-SHA256 por-fila heredado + firma Parquet **greenfield HMAC, NO el Ed25519 de RAG-127** (`DEBT-DOCS-MEDALLION-DUALITY-001`).

## Criterio de cierre del medallón (del ADR-058 §3.1)
Test de equivalencia **Camino-0 ≡ Flujo-A+B** sobre la proyección Kuzu. Predicado ancho:
`set(flow_uid)` (NetworkFlow) ∧ `set(event_id)` (Alert∪TelemetryEvent) ∧ props_identidad (node_id, community_id, window, seq) ∧ props_veredicto ≈ε (cols 12-17, scores con tolerancia) ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} ∧ hmac_row preservado. **Cláusula de caducidad:** válido mientras el join sea determinista (10.8 / `DEBT-JOIN-CONFIDENCE-001`).

## Deudas abiertas (prioridad)
- **P0:** `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`, `DEBT-CONFIG-BRONZE-HARDCODE-001` (ambas → Eslabón 0), `DEBT-GOLD-NODE-DIMENSION-001` (incl. `flow_start_window`), `DEBT-GOLD-INTEGRITY-HMAC-001`, `DEBT-ZMQ-DELIVERY-GUARANTEE-001`
- **P1:** `DEBT-HOST-DOMAIN-CONTRACT-001` (pre-Eslabón 1; Wazuh host↔red, deuda canónica `DEBT-ARGUSPP-WAZUH-001` F4; el nombre `host_domain_v1` NO existe en repo), `DEBT-PARQUET-KUZU-CONNECTOR-001` (greenfield Eslabón 2), `DEBT-CIRCUIT-FS-DROP-001`
- **P2:** `DEBT-PARSE-VERIFY-SENTINEL-001` (degradada de P0; doc + vigilancia campos unsigned futuros), `DEBT-FLOWUID-SEQ-COLLISION-001` (seq=0; fidelidad, no equivalencia), `DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` (PK compuesta `(flow_uid,seq)` no implementada), `DEBT-ADAPTERSPEC-ENVELOPE-001`, `DEBT-DOCS-MEDALLION-DUALITY-001`, `DEBT-JOIN-CONFIDENCE-001`
- **resueltas DAY 198:** `DEBT-FLOWUID-CANONICAL-ENCODING-001` (de facto, encoding inyectivo + paridad congelada)
- **P3:** higiene `backups/`/`.backup` + `.DS_Store` → `.gitignore` / `git rm --cached`

## Punteros (paths POST-higiene — nombres canónicos)
- `docs/adr/ADR-058-circuito-completo-aguas-abajo.md` (commit `47d0a8d6`, en `day196`)
- `docs/council/PLAN — Circuito completo aguas abajo (DAY 196 → implementación).md` (plan-doc consolidado DAY 197; `council/` NO normalizado, fuera de alcance de la higiene)
- `docs/adr/ADR-052-v3.2-multi-node-flow-identity-host-net-correlation.md` (flow_uid identidad multi-nodo)
- `docs/adr/ADR-057-capa-consulta-grafo-kuzu-bitemporalidad-nl-v2.md` (Kuzu/bitemporalidad)
- `docs/adr/ADR-051-v2.2-final-seed-parity-gate-correlation-health.md` (parity gate)
- `correlation-engine/include/correlation_engine/flow_uid.hpp` (encoding canónico, `compute_flow_uid`, `window_micros`)
- `correlation-engine/include/correlation_engine/cypher_builder.hpp` (MERGE, ON CREATE SET; prod=`$param`, logging=interpolado)
- `correlation-engine/include/correlation_engine/correlation_record.hpp` (struct 19 cols; sec=int64, nano=int32, src/dst_port=uint32)
- `correlation-engine/src/correlation_reader.cpp:67` (`parse_and_verify`; from_chars + parse_double; descarta nullopt)
- `correlation-engine/src/main.cpp` (Camino 0: ifstream→parse_and_verify→flow_uid→IGraphSink; `--follow` tail-poll roto en rotación)
- `correlation-engine/schema/schema.cypher` (NetworkFlow PK=flow_uid simple; Alert/TelemetryEvent PK=event_id; veredicto desnormalizado cols 12-17)
- `ml-detector/src/config_loader.cpp:455` (patrón csv_writer a calcar para bronze config JSON)
- `scripts/parquet/` (RAG-127, Ed25519, capa DISTINTA — no tocar para el circuito)

## Rama
`day196/circuit-adapters-zmq` (al día con main vía fast-forward, trae la higiene). ADR-058 commiteado (`47d0a8d6`). Pendiente push. El Eslabón 0 va en el mismo PR que el ADR (commit de doc no pasa gate, va con la implementación). day194 cerrada (PR #107). Backup del ADR-058 en `~/adr058-backup.md` (host, 315 líneas) por si acaso.

