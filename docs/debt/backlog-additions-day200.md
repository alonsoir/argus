## 🆕 Entradas DAY 200 — Reconciliación BACKLOG.md ↔ deudas del circuito (ADR-058 §6)

> Origen: TAREA 1 bloqueante pre-Eslabón 0. Medido DAY 199 (grep -c contra el fichero):
> de las ~19 deudas que ADR-058 §6 cita como existentes, solo 2 tenían entrada formal
> en BACKLOG.md (`DEBT-FLOWUID-SEQ-COLLISION-001`, `DEBT-FLOWUID-CANONICAL-ENCODING-001`).
> El resto existía como mención en ADR/plan/actas, no como entrada de backlog. Esta
> sección cierra esa brecha en una sola pasada, fuente canónica decidida antes de
> escribir (ADR-058 + PLAN — Circuito completo aguas abajo, DAY196→197).

---

### DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001 — Rotación de bronce sin follow en el reader
**Severidad:** 🔴 P0 — Eslabón 0
**Estado:** ABIERTO — DAY 199 (medida V3, ADR-058 §4)
**Componente:** `correlation-engine/src/main.cpp` + `ml-detector/src/correlation_writer.cpp`
El writer rota el CSV de bronce por fecha (`correlation_writer.cpp:177`); el reader abre
un handle fijo (`main.cpp:104`) y el modo `--follow` no sigue la rotación
(`main.cpp:125-132`, tail-poll sobre el mismo `ifstream`). Cuando el writer rota a
medianoche al fichero del día siguiente, el reader sigue tailando el de ayer y nunca ve
el nuevo — el circuito verde muere a medianoche. Roja **benigna** (causa conocida, parche
planificado): watcher `inotify`/`IN_CLOSE_WRITE` sobre el directorio (Eslabón 0), no sobre
un handle fijo.
**Test de cierre:** writer rota a las 00:00 (simulado) → el reader detecta el fichero
nuevo sin reinicio → filas post-rotación se materializan en Kuzu sin pérdida ni gap.
**Estimación:** incluida en Eslabón 0 (1 sesión).

---

### DEBT-CONFIG-BRONZE-HARDCODE-001 — bronze_root hardcodeado en zmq_handler
**Severidad:** 🔴 P0 — Eslabón 0
**Estado:** ABIERTO — DAY 199 (medida V3, ADR-058 §4)
**Componente:** `ml-detector/src/zmq_handler.cpp:154` (writer) + `correlation-engine` (reader)
El `base_dir` del bronce está hardcodeado a `/vagrant/logs/correlation/argus` en el
writer; el reader resuelve el path por `--bronze`/`ARGUS_BRONZE_CSV` (argv/env),
sincronizados a mano. El hermano `csv_writer` ya lee `base_dir` de JSON
(`config_loader.cpp:455`, patrón a calcar). Sin fuente única de verdad, el refactor a
ZMQ (Eslabón 6) y cualquier despliegue fuera de Vagrant quedan bloqueados.
**Test de cierre:** `bronze_root` + patrón de naming en JSON; writer y reader derivan el
mismo path de la misma raíz sin literal duplicado; test que cambia `bronze_root` en JSON
y verifica que ambos componentes lo siguen sin recompilar.
**Estimación:** incluida en Eslabón 0 (1 sesión).

---

### DEBT-GOLD-NODE-DIMENSION-001 — node_id/community_id/flow_start_window como columnas de primera clase del oro
**Severidad:** 🔴 P0 — precondición Via Appia (pre-Flujo A)
**Estado:** ABIERTO — DAY 199 · **AMPLIADA DAY 198** (medida V1, ADR-058 §4) — incluye
`flow_start_window` como 4º hash-input materializado, no solo `node_id`/`community_id`.
**Componente:** converter Flujo A (bronce→AVRO→Parquet oro) — greenfield
`node_id` (col 3) y `community_id` (col 4) ya son columnas de primera clase en bronce
[medido]. `flow_start_window` es **100% derivada** hoy: el writer nunca la escribe
(`correlation_writer.cpp:88-89` solo `flow_start_sec`/`flow_start_nano`); el reader la
computa en read-time (`main.cpp:117`, `window_micros(...)`) y es input directo del hash
`flow_uid` (`main.cpp:118`). Sin materializarla en el oro como columna, una fila del
ledger no es re-verificable independientemente: si cambia el bucketing de
`window_micros()`, el `flow_uid` re-derivado deja de coincidir con el que entró al hash
original. Precondición de Via Appia (ledger inmutable auto-contenido), no preferencia.
Sin las tres columnas, el dataset no puede estratificar por nodo — la hipótesis central
del proyecto (¿contribuyen nodos distribuidos a mejores datasets?) queda inmedible.
**Test de cierre:** el converter Flujo A arrastra `node_id`, `community_id` y
`flow_start_window` como columnas Arrow tipadas (no solo como ingredientes internos del
hash); `flow_uid` re-derivado desde las columnas del oro coincide bit a bit con el
`flow_uid` grabado en el mismo registro.
**Estimación:** 1 sesión (diseño esquema) + implementación con Eslabón 1.

---

### DEBT-GOLD-INTEGRITY-HMAC-001 — HMAC por-fila heredado + firma del Parquet consolidado
**Severidad:** 🔴 P0 — Flujo A
**Estado:** ABIERTO — DAY 199 (ADR-058 §2.6, decisión ratificada 9/9)
**Componente:** converter Flujo A (bronce→AVRO→Parquet oro) — greenfield
El HMAC-SHA256 por-fila de bronce (col 18) debe preservarse como **columna** del oro
(no descartarse en el converter), y el Parquet consolidado debe firmarse como artefacto
— **greenfield HMAC-SHA256 coherente con bronce, NO reutiliza el firmador Ed25519** del
pipeline `scripts/parquet/` (capa RAG-127, contrato distinto — confundir ambos firmadores
es exactamente `DEBT-DOCS-MEDALLION-DUALITY-001`). Razón: el replay del grafo es
coherente en el tiempo si y solo si las filas conservan su HMAC original verificable
contra clave.
**Test de cierre:** cada fila del oro conserva su HMAC de bronce, verificable contra la
clave de producción; el Parquet consolidado tiene firma de artefacto verificable
independiente del firmador RAG-127.
**Estimación:** 1 sesión, junto a Eslabón 1.

---

### DEBT-ZMQ-DELIVERY-GUARANTEE-001 — Handoff adapter→engine debe ser PUSH/PULL, no PUB/SUB
**Severidad:** 🔴 P0 — Eslabón 6 (post-circuito verde)
**Estado:** ABIERTO — DAY 199 (ADR-058 §2.5, AdapterSpec v1 §7.1 enmendado)
**Componente:** futuros adapters (Suricata/Zeek/Wazuh) + correlation-engine — greenfield
PUB/SUB es fire-and-forget por diseño (la regla slow-joiner resuelve el arranque, no la
garantía de entrega). AdapterSpec v1 §2 exige at-least-once — incompatible con PUB/SUB
puro para el handoff con garantía. El handoff adapter→engine debe usar **PUSH/PULL**
(encola en el sender hasta HWM); PUB/SUB se reserva para fan-out tolerante a pérdida
(p.ej. firewall-acl-agent en detección tiempo-real, que sí puede perder mensajes).
**Test de cierre:** adapter sintético + engine sobre PUSH/PULL — matar el PULL receptor
durante ráfaga no pierde eventos silenciosamente (se re-entregan al reconectar, dentro
del HWM configurado).
**Estimación:** 1-2 sesiones, con Eslabón 6.

---

### DEBT-HOST-DOMAIN-CONTRACT-001 — Contrato host_domain_v1 (Wazuh) separado de correlation_v1
**Severidad:** 🟡 P1 — pre-Eslabón 1 (bloquea el esquema del medallón)
**Estado:** ABIERTO — DAY 199 (ADR-058 §2.3, decisión ratificada: 6/8 separado)
**Componente:** adapter-wazuh (greenfield) + sink `:Host` en Kuzu
Wazuh no tiene flujo (`community_id` ausente estructuralmente) — extender
`correlation_v1` con una col `host_key` crearía un schema con dos columnas de identidad
mutuamente excluyentes (antipatrón). Contrato `host_domain_v1` separado, con su propia
zona bronce/LZ y sink `:Host`, unido al grafo `:NetworkFlow` por arista
`(:Host)-[:INVOLVES_IP]->(:NetworkFlow)` vía IP + ventana temporal (no fusionado en
`correlation_v1`). Nota DAY198: el nombre `host_domain_v1` reemplaza cualquier mención
histórica de "host_domain_v1" suelta en prompts de continuidad; el nombre del contrato
formal se fija al abrir esta deuda. La deuda de integración Wazuh en sí (agente + manager)
es canónicamente `DEBT-ARGUSPP-WAZUH-001` (F4, ya abierta) — esta deuda es el **contrato
de dominio**, no el despliegue del agente.
**Test de cierre:** `host_domain_v1` documentado (columnas, centinelas, join); sink `:Host`
+ arista `INVOLVES_IP` con método+confianza anotados; un solo grafo con múltiples sinks
  de parquet verificado en Kuzu.
  **Estimación:** 1-2 sesiones, antes del Eslabón 1.

---

### DEBT-PARQUET-KUZU-CONNECTOR-001 — Conector PARQUET→Kuzu (Flujo B) no existe
**Severidad:** 🟡 P1 — Eslabón 2
**Estado:** ABIERTO — DAY 199 · **AMPLIADA DAY 198** con orden de escritura del Flujo B
(medido §8.4/DAY197: no existe ni prototipo)
**Componente:** conector nuevo Parquet oro → Kuzu — greenfield
No es "re-apuntar" `kuzu_graph_sink` (que hoy lee bronce-CSV directo, Camino 0): es un
componente nuevo. **Orden de escritura del Flujo B (ampliación DAY198):** el conector
debe respetar el mismo orden causal que Camino 0 al aplicar `MERGE` — leer el Parquet
oro en orden de `ingested_at` creciente (no en orden arbitrario de partición/fichero),
para que la semántica `ON CREATE SET` sin `ON MATCH SET` (§ADR-058 V7) produzca el mismo
grafo que Camino 0 ante colisiones de `flow_uid`. Un orden de lectura distinto al orden
de escritura original invalidaría el test de equivalencia §3.1 aunque el contenido de las
filas sea idéntico.
**Test de cierre:** test de equivalencia Camino-0 ≡ Flujo-A+B (predicado ADR-058 §3.1)
sobre un evento sintético — grafo idéntico en ambos caminos, incluyendo el caso de
colisión de `flow_uid` con orden de llegada invertido; benchmark de ingesta (1M filas)
como gate de salida production-ready (no bloquea el circuito verde de un motor).
**Estimación:** 2-3 sesiones, Eslabón 2.

---

### DEBT-CIRCUIT-FS-DROP-001 — Handoff por fichero (ifstream) es interino
**Severidad:** 🟡 P1 — post-circuito verde
**Estado:** ABIERTO — DAY 199 (ADR-058 §2.5)
**Componente:** `correlation-engine/src/main.cpp` (Camino 0)
El Camino 0 lee bronce vía `ifstream` directo sobre fichero — válido para cerrar el
circuito verde de un motor (medible, simple), pero es un patrón de transporte interino.
Producción migra a ZMQ (Eslabón 6, `DEBT-ZMQ-DELIVERY-GUARANTEE-001`). Esta deuda marca
el compromiso explícito de no dejar el FS-drop como transporte permanente aunque
"funcione" — coherente con la regla de rama del plan (el ADR es commit de apertura del
mismo PR que la implementación).
**Test de cierre:** documentado el criterio de migración (cuándo el FS-drop deja de ser
aceptable — volumen, multi-nodo); Eslabón 6 lo sustituye sin romper el test de
equivalencia §3.1.
**Estimación:** 0.5 sesión (doc) + Eslabón 6 para el cierre real.

---

### DEBT-PARSE-VERIFY-SENTINEL-001 — Centinela -1 en campos numéricos: doc + vigilancia
**Severidad:** 🟢 P2 — **degradada de P0** (medida V2, ADR-058 §4, DAY 198)
**Estado:** ABIERTO — DAY 199
**Componente:** `correlation-engine/src/correlation_reader.cpp` (`parse_and_verify`)
Medido extremo a extremo: el proto no puede transportar `-1` en puertos (`uint32`,
`network_security.proto:105-106`); ICMP usa `0` (`test_community_id.cpp:62`), no `-1`;
el writer copia el puerto directo sin remapeo (`correlation_writer.cpp:91-92`); el
reader acepta `"0"` con `from_chars`. **No hay descarte silencioso de filas ICMP** — el
centinela `-1` temido no existe en `src_port`/`dst_port`. Se degrada de P0 a P2 porque el
riesgo real es residual: `flow_start_sec`/`flow_start_nano` **sí** son signed
(`int64_t`/`int32_t`) y un `-1` ahí sobrevive como valor sin marca de centinela,
propagándose al hash vía `window_micros(-1,-1)` — riesgo semántico, no de pérdida de fila.
El comentario de `correlation_reader.hpp:12` colapsa "campo numérico ilegible" sin
distinguir corrupto de centinela — trampa documental para un campo unsigned futuro con
centinela `-1`.
**Test de cierre:** documentar que el contrato usa `0` para puerto-ausente y la asimetría
signed(sec/nano)/unsigned(puertos); vigilancia explícita si se añade un campo unsigned
futuro con semántica de centinela negativo.
**Estimación:** 0.5 sesión (doc).

---

### DEBT-ADAPTERSPEC-ENVELOPE-001 — Enmienda AdapterSpec v1 → v1.1 (envelope + transporte)
**Severidad:** 🟢 P2 — doc, pasa por Consejo
**Estado:** ABIERTO — DAY 199 (ADR-058 §2.5, PLAN §3.1)
**Componente:** `docs/engineering_decisions/` — AdapterSpec v1
Dos correcciones documentales sobre el AdapterSpec v1 (DAY 169, ADR-046 v4 §3.10): (1)
el envelope protobuf `SecurityEvent` referenciado en §3 **no existe**
(`network_security.proto` solo tiene `NetworkSecurityEvent`) — el adapter emite filas
`correlation_v1` (CSV+HMAC), nunca protobuf; (2) el transporte interno NO es siempre
PUB/SUB — §7.1 se enmienda para el handoff adapter→engine (ver
`DEBT-ZMQ-DELIVERY-GUARANTEE-001`). El frame ZMQ, cuando llegue el Eslabón 6, transporta
los bytes del CSV firmado, no un protobuf reensamblado.
**Test de cierre:** documento AdapterSpec v1.1 redactado y subido al Consejo para
ratificación; §§2/4/6 conservados sin cambio.
**Estimación:** 0.5 sesión (doc) + ratificación Consejo.

---

### DEBT-DOCS-MEDALLION-DUALITY-001 — Dualidad de pipelines PARQUET (RAG-127 vs correlación)
**Severidad:** 🟢 P2 — doc
**Estado:** ABIERTO — DAY 199 (medida §8.1, ADR-058 §2.6)
**Componente:** `scripts/parquet/` (RAG-127, Ed25519) vs converter Flujo A (correlación-19, HMAC) — documentación
El único pipeline Parquet real hoy es `scripts/parquet/` — lee el CSV de 127 columnas
del RAG, firma Ed25519, **no** lee `correlation_v1`. Es una capa distinta (RAG-127,
análisis) del medallón de correlación (grafo, greenfield). Riesgo: confundir ambos
firmadores (Ed25519 vs HMAC-SHA256 del oro del circuito) o asumir que uno sustituye al
otro. Documentar la dualidad con warnings explícitos evita que un futuro cambio en uno
rompa el otro por asunción errónea de equivalencia.
**Test de cierre:** nota en `docs/` que distingue explícitamente ambos pipelines Parquet,
sus firmadores y sus contratos de entrada; referenciada desde ADR-058 y desde
`scripts/parquet/README` si existe.
**Estimación:** 0.5 sesión (doc).

---

### DEBT-JOIN-CONFIDENCE-001 — Ventana de join adaptativa vs reconstruibilidad del ledger
**Severidad:** 🟢 P2 — pre-join adaptativo (gobierna la cláusula de caducidad ADR-058 §3.2)
**Estado:** ABIERTO — DAY 199 (PLAN §10.8, ADR-058 §3.2)
**Componente:** correlation-engine (parámetros de ventana de join) — diseño diferido
Hoy los parámetros de ventana de join son deterministas y configurables en JSON — la
propiedad "Kuzu reconstruible desde el ledger" se mantiene. Si la ventana se vuelve
**adaptativa** (join no-determinista), dos caminos pueden tomar decisiones de join
distintas y el predicado de equivalencia ADR-058 §3.1 rompe **por diseño, no por bug**.
Este es exactamente el gatillo de la cláusula de caducidad del ADR-058: el predicado es
válido mientras el join sea determinista. Decisión diferida para el DDL: grabar el
contexto-de-decisión-de-join por época en el schema del ledger, o diferir hasta que el
join adaptativo exista realmente.
**Test de cierre:** ningún test de cierre hasta que se active un join adaptativo real;
la deuda existe para que esa activación no ocurra sin revisar primero el predicado de
equivalencia y el schema del ledger.
**Estimación:** diferida — sin sesión asignada hasta activación de join adaptativo.

---

### DEBT-NEO4J-FLOW-KEY-COMPOSITE-001 — PK compuesta (flow_uid, seq) no implementada
**Severidad:** 🟢 P2 — fidelidad, no bloqueante de equivalencia
**Estado:** ABIERTO — DAY 199 (medida V7, ADR-058 §6) · **resuelve drift de ID con
`DEBT-NEO4J-FLOW-KEY-001`** (ver nota de canonicidad abajo)
**Componente:** `correlation-engine/schema/schema.cypher` (PK simple `flow_uid`)
El schema actual usa `flow_uid` como PK simple. Ante colisión de `flow_uid` (por
`seq_in_window=0` fijo, `DEBT-FLOWUID-SEQ-COLLISION-001`), el `MERGE` con solo
`ON CREATE SET` (sin `ON MATCH SET`) descarta el segundo flujo colisionado de forma
**idéntica en Camino 0 y Flujo A+B** — la equivalencia §3.1 se sostiene ante la colisión.
Es deuda de **fidelidad** (se pierde un flujo real), NO de equivalencia (ambos caminos
pierden el mismo). Una PK compuesta `(flow_uid, seq)` resolvería la colisión pero no es
prerequisito del cierre del medallón.
**Nota de canonicidad (drift de ID, DAY199):** `ADR-058` §6 cita
`DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` como la deuda viva de PK compuesta. El backlog tenía
únicamente `DEBT-NEO4J-FLOW-KEY-001` (DAY170), que es un objeto **distinto**: la decisión
de diseño original de usar `flow_uid = hash(node_id‖community_id‖flow_start_window)`
como identidad del nodo-flujo, ratificada y cerrada por ADR-052 v3.2 (DAY173) e
implementada en `schema.cypher` (PK simple `flow_uid`). **Decisión: dos IDs distintos,
ambos canónicos.** `DEBT-NEO4J-FLOW-KEY-001` se marca CLOSED (superseded by ADR-052 v3.2,
implementada); `DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` es la entrada nueva y correcta para el
trabajo de PK compuesta pendiente, exactamente como la cita ADR-058.
**Test de cierre:** dos flujos con `flow_uid` colisionado y `seq` distinto →
distinguibles en Kuzu vía PK compuesta; sin regresión del test de equivalencia §3.1.
**Estimación:** 1 sesión, post-medallón (no bloqueante).

---

### DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001 — Igualdad bit-exacta de scores double en el predicado de equivalencia
**Severidad:** 🟡 P1 — nueva V3 (medición DAY 199, ADR-058 §3.1/§8)
**Estado:** ABIERTO — DAY 199
**Componente:** converter Flujo A (bronce→AVRO→Parquet oro) — cols 14-16 (scores double)
El predicado de equivalencia ADR-058 §3.1 compara los 3 scores double (fast/ml/overall)
**bit a bit por defecto**, no con tolerancia ε. Justificación medida: ambos caminos
parten del mismo `double` producido por `parse_double` sobre el mismo bronce CSV; AVRO
`double` y Parquet `DOUBLE` son ambos IEEE 754 binary64 — un round-trip
double→AVRO→Parquet→double preserva los bits salvo que el converter (a) trunque a
`float32`, (b) **recompute el score en oro en vez de copiarlo**, o (c) reformatee vía
texto intermedio. Esta deuda formaliza la guarda explícita: el converter Flujo A debe
**copiar** los bytes del score, nunca re-evaluar/normalizar/recalcular el valor — un
converter que "limpia" o "normaliza" el score en la capa oro rompería la equivalencia
de forma silenciosa e indetectable sin este test. Incluye la guarda NaN (patrón de bits,
no `==`, porque `NaN != NaN` bajo IEEE 754) — relevante mientras
`DEBT-RANSOMWARE-ML-HEAD-INERT-001` deja scores ML sin inicializar/inertes.
**Test de cierre:** test de equivalencia sobre vector con scores conocidos (incluyendo
NaN sintético) → Camino 0 y Flujo A+B producen bytes idénticos en cols 14-16;
test negativo — un converter que recomputa/trunca el score falla el test.
**Estimación:** 1 sesión, con Eslabón 1/2.

---

### DEBT-CIRCUIT-PARSER-CROSSLANG-001 — Paridad de parsing cross-language en el converter Flujo A
**Severidad:** 🟡 P1 — nueva V3 (medición DAY 199, ADR-058 §3.1/§9)
**Estado:** ABIERTO — DAY 199
**Componente:** converter Flujo A (probable Python/pyarrow) vs `correlation_reader.cpp` (`parse_and_verify`)
El encoding canónico de `flow_uid` (`flow_uid.hpp`, `encode_flow_input`) ya tiene paridad
cross-language congelada y verificada byte a byte contra `hashlib.blake2b` — pero eso
cubre solo el **hash**, no el **parseo** del CSV bronce que lo alimenta. Si el converter
Flujo A reimplementa el parseo de `correlation_v1` (19 columnas, centinela `-1`,
verificación HMAC) en vez de reusar/replicar exactamente la lógica de
`parse_and_verify`, dos filas pueden divergir en qué se considera "descartable" —
p.ej. un campo numérico "ilegible" para un parser Python (`ValueError` en distinto punto
que `std::from_chars`) puede aceptar o rechazar una fila que el reader C++ trataría
distinto. Esta deuda exige que el converter **reuse** el encoding (`flow_uid.hpp` o los
vectores golden congelados) y **replique exactamente** las reglas de descarte de
`parse_and_verify` (nº columnas ≠19, HMAC inválido, centinela `-1`/`UNKNOWN`), no las
reimplemente de memoria.
**Test de cierre:** batería de vectores de bronce (válidos, HMAC inválido, columnas de
menos, centinela en cada posición numérica) parseados por ambos lados → mismo veredicto
(aceptar/descartar) en C++ y en el converter Flujo A, byte a byte donde aplique.
**Estimación:** 1 sesión, con Eslabón 1.

---

### DEBT-EVENT-ID-FACTORY-001 — Origen y preservación de event_id en el predicado de equivalencia
**Severidad:** 🟡 P1 — nueva V3 (medición DAY 199, ADR-058 §3.1)
**Estado:** ABIERTO — DAY 199
**Componente:** `ml-detector/src/correlation_writer.cpp` (col 2, event_id) + converter Flujo A
El predicado ADR-058 §3.1 exige `set(event_id)_C0 == set(event_id)_AB` para
`Alert ∪ TelemetryEvent`. No hay evidencia medida de que `event_id` (col 2 del contrato
bronce) sea tratado hoy como valor **opaco a preservar** por el converter Flujo A, ni de
cuál es su regla de generación en origen (¿UUID del writer? ¿derivado?). Si el converter
Flujo A regenera o reasigna `event_id` (en vez de propagar verbatim el de bronce), el
predicado de equivalencia falla estructuralmente sin que sea un bug de datos — sería un
bug de contrato no detectado hasta el test E2E. Esta deuda formaliza: (1) documentar el
origen/generación real de `event_id` en el writer; (2) garantizar que el converter Flujo A
lo copia verbatim, nunca lo deriva de nuevo.
**Test de cierre:** origen de `event_id` documentado; test de equivalencia con múltiples
`Alert`/`TelemetryEvent` → mismo conjunto de `event_id` en Camino 0 y Flujo A+B, sin
colisiones ni reasignación.
**Estimación:** 0.5 sesión (investigación) + 0.5 sesión (test), con Eslabón 1/2.

---

### DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001 — Paridad del flag temporal_anomaly entre caminos
**Severidad:** 🟡 P1 — **reclasificada de P2** + alcance ampliado (medición DAY 199, ADR-057 §Fase0/DAY181)
**Estado:** ABIERTO — DAY 199
**Componente:** `graph-engine` (Camino 0, `ingested_at`/`temporal_anomaly`) + converter Flujo A
El flag `temporal_anomaly` (Fase 0 del grafo, DAY 182 — `ingested_at > flow_start_window
+ margen` → futuro-datación, señal de clock-injection, enmienda del Consejo DAY 181)
se calcula hoy en el path de escritura de Camino 0 (`build_cypher(ingested_at_ns)`). El
Flujo A/B no tiene definido cómo preserva o recalcula `ingested_at` a través de
AVRO→Parquet: si el converter usa el timestamp de **procesamiento del batch** en vez del
`ingested_at` original de bronce, el flag `temporal_anomaly` puede divergir entre caminos
para el mismo evento — rompiendo silenciosamente la sub-cláusula `props_veredicto` del
predicado §3.1 (el flag es parte del veredicto, cols 12-17 conceptualmente extendidas).
**Reclasificación:** pasa de P2 (guarda de Fase 0, aislada) a **P1** porque afecta
directamente la equivalencia formal del medallón, no solo la calidad del dato en Camino 0.
**Alcance ampliado:** cubre también el caso de replay (el Consejo DAY181 ya señaló que
`ingested_at` "reflejaría el tiempo del replay" si no se preserva la jerarquía de fuentes
— WAL prevalece en replay, campo Kuzu es vista del estado actual).
**Test de cierre:** evento sintético con `flow_start_window` futuro-datado → mismo valor
de `temporal_anomaly` en Camino 0 y Flujo A+B; test de replay → `ingested_at` preservado
desde bronce, no reescrito con el tiempo de reproceso.
**Estimación:** 1 sesión, con Eslabón 1/2 — depende de decisión de jerarquía de fuentes
(WAL vs Kuzu, aún abierta bajo `DEBT-LABEL-WAL-001`).