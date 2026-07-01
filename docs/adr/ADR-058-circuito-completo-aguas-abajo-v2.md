# ADR-058 — Circuito completo aguas abajo (medallón: adapters → bronce → LZ → Kuzu → dashboard)

- **Estado:** PROPUESTO (v2 — pendiente confirmación del Consejo de las correcciones medidas)
- **Fecha:** DAY 199 (hoy)
- **Revisión:** v2 (DAY 199) — §3.1 reescrita tras revisión adversarial del Consejo (8 modelos).
  Las objeciones se midieron contra `fichero:línea`: tres bloqueantes propuestos cayeron contra
  el binario (window/seq YA materializadas L101/110; `event_id`=bronce col 2; scores YA `DOUBLE`
  en `schema.cypher`); el resto se incorporó. Detalle por edición en §9 (changelog).
- **Rama:** `day196/circuit-adapters-zmq`
- **Supersede / consolida:** `PLAN — Circuito completo aguas abajo (DAY 196 → implementación).md` (consolidado DAY 197, §10 = decisiones cerradas)
- **Relacionado:** ADR-046 v4, ADR-051 (parity gate), ADR-052 (flow_uid identidad multi-nodo), ADR-057 (Kuzu / bitemporalidad)
- **Invariante rector:** medir, no votar. Toda decisión de este ADR está trazada a `fichero:línea` del binario, no a memoria.

---

## 1. Contexto

El circuito aguas abajo materializa el flujo completo desde los adaptadores hasta el
dashboard: `adapters → bronce → Landing Zone (medallón) → grafo Kuzu → dashboard`.
La forma del oro fue ratificada 9/9 por el Consejo en DAY 197. Este ADR la sella y
añade la evidencia medida en el gate de DAY 198 (9 verificaciones contra bytes).

El supuesto operativo de partida es que la inferencia ML está rota/incompleta
(DEBT-RANSOMWARE-ML-HEAD-INERT-001): el circuito se cierra primero por el camino que
**ya existe**, y la re-cualificación de modelos se difiere a post-circuito.

---

## 2. Decisión — Forma del oro (ratificada 9/9, DAY 197)

**Oro-como-ledger + join en Kuzu (write-time).** El ledger es el ÚNICO oro. Kuzu y
cualquier wide-table (incl. matriz de features ML, ADR-040) son **proyecciones
co-iguales reconstruibles**, no oros alternativos. No existe caso para oro-como-join.

Corolarios cerrados (§10 del plan):

1. **`flow_uid` es la PK del grafo**, NO `community_id` (coherencia ADR-052).
2. **`node_id` / `community_id` / `flow_start_window`** son columnas de primera clase
   del oro-ledger (hipótesis del proyecto: contribución por nodo).
3. **Wazuh** → contrato de dominio host **separado** (host↔red), conectado al grafo por
   `agent_id`/IP con método+confianza anotados en la arista (no fusionado en el contrato
   `correlation_v1`). Decisión sube antes del Eslabón 1.
   > NOTA [medido DAY 198]: el nombre `host_domain_v1` del prompt de continuidad **no
   > aparece en ningún doc del repo**. La deuda canónica de integración Wazuh es
   > `DEBT-ARGUSPP-WAZUH-001` (F4, OPEN); el contrato a crear es
   > `DEBT-HOST-DOMAIN-CONTRACT-001` (P1); el diseño host↔red (Translation node /
   > `agent_id` / NAT, anotando método+confianza) vive en `BACKLOG.md:4244,4283`. El
   > nombre del contrato se define al abrir esa deuda, no aquí.
4. **Timestamp se funde en la LZ**, NO en el writer C++.
5. **ZMQ handoff = PUSH/PULL** (at-least-once), no PUB/SUB.
6. **Integridad del oro** [medido DAY 198, plan-doc §10.1, líneas 235/258/312]:
    - **HMAC-SHA256 por-fila** heredado de bronce como **columna** del oro, verificable
      contra clave. Replay del grafo coherente en el tiempo ⟺ filas conservan su HMAC.
    - **Firma del Parquet consolidado como artefacto** — **greenfield, HMAC-SHA256
      coherente con bronce. NO reutiliza el firmador Ed25519** del pipeline
      `scripts/parquet/` (capa RAG-127, contrato distinto). Confundir ambos firmadores
      es exactamente `DEBT-DOCS-MEDALLION-DUALITY-001`: RAG-127/Ed25519 (análisis) vs
      correlación-19/HMAC (grafo). El converter del circuito **no** llama al firmador RAG.

---

## 3. Caminos del medallón y criterio de cierre

Tres caminos (medido DAY 197 — el conector Parquet→Kuzu NO existe ni en prototipo):

- **Camino 0** — `ifstream` bronce → Kuzu. **Ya existe** (`correlation-engine/src/main.cpp`).
- **Flujo A** — bronce → AVRO → Parquet oro. Greenfield.
- **Flujo B** — Parquet → Kuzu. Greenfield (Eslabón 2).

**Criterio de cierre del medallón** = test de equivalencia **Camino-0 ≡ Flujo-A+B**.

### 3.1 Predicado de equivalencia (especificación)

El único output común a ambas ramas es la **proyección Kuzu**. El predicado se define
ahí, no sobre representaciones intermedias. **Medido DAY 198** contra
`schema.cypher` y `cypher_builder.hpp`: el grafo tiene 3 tablas de nodo
(`NetworkFlow` PK=`flow_uid`, `Alert`/`TelemetryEvent` PK=`event_id`) y 3 relaciones
(`ALERT_ABOUT`, `TELEMETRY_ABOUT`, `CORRELATES_FLOW`). Un predicado solo sobre
`flow_uid` sería **demasiado estrecho** (dos grafos pueden coincidir en flujos y diferir
en alerts, scores o aristas). El predicado completo:

El predicado compara solo propiedades **deterministas-de-dato** (derivan del
bronce; idénticas entre ejecuciones). Excluye explícitamente las propiedades
**deterministas-de-ejecución** (derivan del reloj/orden del run; divergen entre
corridas **por diseño, no por bug**). La partición está trazada a `fichero:línea`
(ver «Partición de propiedades» más abajo).

```
EQUIV(Camino0, FlujoA+B) :=
   set(flow_uid)_C0                  == set(flow_uid)_AB         # NetworkFlow (PK, V9)
 ∧ set(event_id)_C0                  == set(event_id)_AB         # Alert ∪ TelemetryEvent
                                                                 #   (event_id = bronce col 2, ver nota)
 ∧ ∀ uid: props_identidad(uid)_C0    == props_identidad(uid)_AB  # node_id, community_id,
                                                                 #   flow_start_window, seq_in_window
                                                                 #   (materializadas L101/110, ver nota)
 ∧ ∀ eid: props_veredicto(eid)_C0    == props_veredicto(eid)_AB  # final_classification, threat_category,
                                                                 #   3 scores double, authoritative_source
                                                                 #   double BIT-EXACTOS por defecto (ver nota)
 ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)
 # EXCLUIDAS (clase determinista-de-ejecución, NO van al predicado):
 #   ingested_at      — wall-clock per-fila (kuzu_graph_sink.hpp:47)
 #   temporal_anomaly — deriva de ingested_at (cypher_builder.hpp:86)
 # hmac_row NO está en este predicado: no vive en la proyección Kuzu (0 hits en
 # schema.cypher). Se verifica aparte como integridad bronce↔oro (ver nota HMAC).
```

**Partición de propiedades (medido DAY 199 contra `cypher_builder.hpp`,
`kuzu_graph_sink.hpp`, `correlation_reader.cpp`, `schema.cypher`):**

| Clase | Propiedades | Traza | En predicado |
|-------|-------------|-------|--------------|
| **D — determinista-de-dato** | `flow_uid`, `event_id`, `node_id`, `community_id`, `flow_start_window`, `seq_in_window`, `final_classification`, `threat_category`, `fast_detector_score`, `ml_detector_score`, `overall_threat_score`, `authoritative_source`, `method`, `confidence` | `cypher_builder.hpp:101-103,110-112`; `event_id`=`correlation_reader.cpp:85` (col 2); aristas=`schema.cypher:71-73` | **SÍ** (`==`, bit-exacto en doubles) |
| **E — determinista-de-ejecución** | `ingested_at`, `temporal_anomaly` | `kuzu_graph_sink.hpp:47` (`ingest_now_ns()` per-fila); `cypher_builder.hpp:86` (`window_to_epoch_nanos(window) > ingested_at_ns + margen`) | **NO** (divergen entre corridas por diseño) |

Razón de la exclusión: la equivalencia de dos **caminos** debe definirse sobre lo que
deriva del **dato**, no sobre cuándo corrió cada camino. `ingested_at` se sella con
`CLOCK_REALTIME` a la entrada del sink (per-fila); dos ejecuciones producen relojes
distintos. `temporal_anomaly` es un `bool` que **parece** determinista-de-dato (deriva
de `window`) pero su fórmula toca `ingested_at` (`cypher_builder.hpp:86`), luego hereda
el no-determinismo para flujos cuya window cae cerca del instante de ingestión. Incluir
cualquiera de las dos en el predicado lo haría fallar entre Camino 0 y Flujo A+B **sin
que exista bug alguno en el converter**. La verificación correcta de `temporal_anomaly`
no es equivalencia-entre-caminos sino un **test unitario de la fórmula** (mismo `window`
+ mismo `ingested_at` fijo ⇒ mismo bool); se traza en
`DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P2).

**Nota — `event_id` y window/seq son datos del bronce, no generados aguas abajo
(medido DAY 199):** objeción del Consejo (varios modelos): «`event_id` podría ser UUID
v4 → los sets nunca coinciden» y «Camino 0 no escribe `flow_start_window`/`seq_in_window`
→ el predicado falla por construcción». **Ambas caen contra el binario.**
`event_id` se lee como **columna 2 del bronce** (`correlation_reader.cpp:85`:
`r.event_id = f[2]`; struct `correlation_record.hpp:14` lo marca `// 2`): viaja como
dato, igual que `flow_uid`; ambos caminos leen el mismo `f[2]` → mismo set por
construcción. (Matiz: `ingest_clock.hpp:6` indica que el wall-clock compone el
`event_id` en el **productor**, aguas arriba del bronce; irrelevante para la
equivalencia, que empieza una vez el valor ya está escrito en bronce.)
`flow_start_window` y `seq_in_window` **sí se materializan** como propiedades del nodo
en Camino 0 (`cypher_builder.hpp:101,110`: `ON CREATE SET f.flow_start_window=...,
f.seq_in_window=...`): no se computan-y-tiran, se computan en read-time **y** se
escriben. El predicado `props_identidad ==` se sostiene porque ambos caminos las emiten.

**Nota — igualdad de los scores: BIT-EXACTA por defecto (medido DAY 198):** los 3
`double` (cols 14-16) se comparan **bit a bit**, no con tolerancia. Justificación medida,
no supuesta: ambos caminos parten del **mismo** double — el de `parse_double` sobre el
**mismo bronce CSV** (Camino 0 y Flujo A leen el mismo texto; la degradación texto→double,
si la hay, es idéntica en ambos y se cancela en el predicado). El único tramo donde
difieren es AVRO→Parquet→conector, y ese tramo es **lossless por tipo**: AVRO `double` y
el tipo físico `DOUBLE` de Parquet son ambos IEEE 754 binary64 — la misma representación
que un `double` de C++. Un round-trip double→AVRO→Parquet→double **preserva los bits**
salvo que el converter (a) trunque a `float32`, (b) recompute el score en oro en vez de
copiarlo, o (c) reformatee vía texto intermedio. Esos tres son **exactamente los bugs que
el test debe cazar** — una ε los enmascararía. (El path de logging ya fuerza
`precision(17)` + `locale::classic()` en `cypher_builder.hpp:151`: el único punto de
pérdida real es texto, y ahí ya está cubierto.)

> **Cláusula de escape de ε (condicionada a medición, no a priori):** ε se introduce
> **solo si** la medición sobre el Flujo-A real exhibe no-bit-exactitud **con causa
> entendida y benigna** (p.ej. una cuantización inevitable y documentada del converter).
> Entonces ε se **deriva de esa cuantización medida** — no es un número a ojo — y se
> documenta la fuente. Hasta entonces el criterio es `==`. Esto honra "medir, no votar":
> no ratificamos hoy una tolerancia para una pérdida no medida que el análisis de tipos
> predice **inexistente**.

> **Guarda de comparación: una sola regla canónica para los bordes IEEE 754
> (medido DAY 199, P2).** Pasar de `≈ε` a `==` aflora dos bordes que con ε quedaban
> ocultos (igual de rotos, pero invisibles). **No pueden tratarse con la misma
> primitiva** — y este es el error que hay que evitar:
> - **NaN:** `NaN != NaN`. Un `==` crudo falla aunque ambos lados sean NaN.
> - **Cero con signo:** `-0.0` y `+0.0` son **bit-distintos** (`0x8000…0` vs `0x0`) pero
>   numéricamente iguales. Un `==` crudo los iguala (oculta divergencia de bits); un
>   `memcmp` crudo de 8 bytes los **separa** (falsa divergencia). Por eso `memcmp` solo
>   —como se proponía— es incorrecto: rompe el caso `-0.0`.
>
> **Regla única:** comparar sobre el **patrón de bits canonicalizado**, donde
> canonicalización = { todo NaN → un único patrón quiet `0x7ff8000000000000`;
> `-0.0` → `+0.0` }. Sobre ese patrón, `==` bit a bit. Una sola regla coherente para
> los tres casos (finitos, NaN, ceros). Ambos caminos deben canonicalizar **antes** de
> comparar; el converter Flujo A aplica la misma canonicalización. (Apunte medido: la
> serialización a AVRO/Parquet puede mutar el *payload*/signo del NaN —signaling→quiet—,
> por eso la canonicalización a un patrón único es necesaria, no opcional.)
> No bloquea el cierre del predicado.

**Nota — robustez a colisión `flow_uid` (medido DAY 198):** el sink usa **MERGE** en
ambos paths (`cypher_builder.hpp:100,154`), con **solo `ON CREATE SET`, sin
`ON MATCH SET`** (8 ocurrencias CREATE, 0 MATCH). Consecuencia: ante dos flujos que
hashean al mismo `flow_uid` (colisión por `seq_in_window=0`,
`DEBT-FLOWUID-SEQ-COLLISION-001`), el segundo hace MATCH puro y sus propiedades se
**descartan de forma idéntica en ambos caminos**. Por tanto la **equivalencia se
sostiene** ante colisión — Camino 0 y Flujo A+B producen el mismo grafo, **bajo una
precondición medida** (ver abajo). La colisión es deuda de **fidelidad** (se pierde un
flujo real, P2), NO de **equivalencia** (ambos caminos pierden el mismo). El medallón
**no queda bloqueado** por ella.

> **Precondición de la robustez (objeción del Consejo, aceptada): orden de inserción
> determinista.** El argumento «ambos descartan idénticamente» solo se sostiene si, ante
> colisión `flow_uid`, **el mismo flujo gana el `ON CREATE SET` en ambos caminos** — y eso
> depende del **orden de inserción**. Camino 0 es `ifstream` secuencial (orden = líneas
> del bronce). Flujo B (Parquet→Kuzu, greenfield) podría insertar en paralelo/bulk, en cuyo
> caso ganaría un flujo distinto y el predicado rompería **por carrera de arquitectura, no
> por bug del converter**. **Decreto:** el Flujo B inserta en orden determinista por
> `(flow_start_window, seq_in_window)` antes del sink Kuzu; el test de equivalencia asume y
> verifica esta precondición. Sin orden determinista, el predicado mide la convergencia del
> sink bajo un orden concreto, no la equivalencia de los caminos.
Relacionado: `DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` (PK compuesta `(flow_uid, seq)` aún no
implementada — el schema usa PK simple). Sobre `DEBT-FLOWUID-CANONICAL-ENCODING-001`
**[medido DAY 198, `flow_uid.hpp`]: resuelta de facto.** El encoding
(`encode_flow_input`) es canónico, self-describing e inyectivo por construcción:
length-prefix `uint16` BE antes de cada string variable (sin separador → imposible
colisión de encoding entre `node_id`/`community_id`), `window` y `seq` como enteros
**big-endian de ancho fijo** (`put_be64`/`put_be32`, no string decimal → sin ambigüedad
cross-language), tag de versión `"argus-flowuid-v1"` (16B) prefijado al input (el
esquema se versiona dentro del hash), BLAKE2b-256 sin truncado (`static_assert`
digest_size=32). **Vectores congelados verificados byte-idénticos C++ ↔
`hashlib.blake2b`** — la paridad cross-language ya existe. Consecuencia para el
predicado: `set(flow_uid)_C0 == set(flow_uid)_AB` **no puede fallar por encoding**; solo
por colisión `seq` (neutralizada por MERGE para equivalencia) o por bug del converter
(que es lo que el test debe cazar). Acción residual: el converter Flujo A **reusa**
`encode_flow_input` (o, si es Python, los vectores golden congelados), no reimplementa.

**Nota — HMAC: integridad bronce↔oro, NO cláusula del predicado (medido DAY 199):**
objeción del Consejo (DeepSeek), **aceptada**. El predicado V1 incluía
`∀ fila: hmac_row preservado`, pero `hmac` tiene **0 ocurrencias en `schema.cypher`**: el
grafo Kuzu **no almacena HMAC**, ni por Camino 0 ni por Flujo A+B. Una cláusula sobre la
proyección Kuzu que referencia un campo ausente de Kuzu es **inverificable** donde estaba.
Corrección: `hmac_row` **sale del predicado de equivalencia** (§3.1) y se reubica como
**control de integridad bronce↔oro-ledger** — se verifica que cada fila del oro conserva el
HMAC heredado del bronce (§2 corolario 6), de forma independiente al test
Camino-0 ≡ Flujo-A+B. La definición del mecanismo (clave, alcance por-fila vs por-artefacto)
vive en `DEBT-GOLD-INTEGRITY-HMAC-001` (P0).

### 3.2 Cláusula de caducidad (atada a 10.8)

El predicado §3.1 es **válido mientras el join sea determinista** (hoy: parámetros en
JSON → propiedad mantenida). Al activar `DEBT-JOIN-CONFIDENCE-001` (join adaptativo /
no-determinista), dos caminos pueden tomar decisiones de join distintas y la
equivalencia rompe **por diseño, no por bug**. En ese momento el predicado debe
revisarse (probablemente relajarse a equivalencia sobre el subconjunto determinista +
banda de tolerancia en el join confidence).

---

## 4. Evidencia medida — Gate DAY 198 (9/9 contra bytes)

> Cada fila está trazada al binario. Ninguna afirmación se apoya en memoria.

### V1 — Propagación de `flow_start_window` al oro  ✓ (decisión: MATERIALIZAR)

- **Medido (reader):** `correlation-engine/src/main.cpp:117` computa
  `window = window_micros(flow_start_sec, flow_start_nano)` en **read-time**. La window
  es input del hash (`compute_flow_uid(node_id, community_id, window)`, `main.cpp:118`),
  no una columna.
- **Medido (writer):** `ml-detector/src/correlation_writer.cpp:88-89` escribe
  `flow_start_sec = ts.seconds()` y `flow_start_nano = ts.nanos()` por separado;
  **nunca** un `flow_start_window`. Confirmado por ambos extremos: la window es 100%
  derivada, no existe en el contrato.
- **Decisión:** materializar `flow_start_window` como **columna hash-input del oro**,
  junto a `node_id` (col 3) y `community_id` (col 4). Sin esto, una fila del ledger no
  es re-verificable independientemente: el día que cambie el bucketing de
  `window_micros()`, el `flow_uid` re-derivado deja de coincidir con el que entró al
  hash. Es **precondición de Via Appia**, no preferencia. Greenfield puro (nada que
  migrar — no existe en ningún extremo).
- **Deuda:** `DEBT-GOLD-NODE-DIMENSION-001` se amplía para incluir `flow_start_window`
  como 4º hash-input materializado.

### V2 — Centinela `-1` en campos numéricos  ✓ (veredicto: FANTASMA en puertos)

Cadena medida extremo a extremo:

- **Proto:** `protobuf/network_security.proto:105-106` → `uint32 source_port`,
  `uint32 destination_port`. Estructuralmente **no puede transportar `-1`**.
- **Sniffer:** `ring_consumer.cpp:874-875` y `main_libpcap.cpp:130-137` asignan el
  puerto vía `ntohs()` (→ `uint16`) o campo unsigned. ICMP usa puerto **`0`**
  (`test_community_id.cpp:62`: `compute_community_id(..., 0, 0, 1)`), no `-1`.
- **Writer:** `correlation_writer.cpp:91-92` copia `nf.source_port()` directo al Row,
  sin remapeo. `"0"` se serializa tal cual.
- **Reader:** `correlation_reader.cpp` `parse_num<uint32_t>` con `std::from_chars`
  acepta `"0"`. Fila **sobrevive**.

**Conclusión:** no hay descarte silencioso de filas ICMP. El centinela `-1` que se
temía no existe en `src_port`/`dst_port`. **NO se cambian los tipos** (`uint32_t` se
mantiene): cambiarlos a signed introduciría divergencia con el proto y una rama de
centinela que ningún productor alimenta.

**Riesgo residual (P2):** `flow_start_sec` (`int64_t`) y `flow_start_nano` (`int32_t`)
**sí** son signed (`correlation_record.hpp:14-15`). Un `-1` ahí sobrevive como valor y
se propagaría al hash vía `window_micros(-1,-1)` sin marca de centinela. Riesgo
**semántico**, no de pérdida de fila.

**Trampa documental (P2):** el comentario de `correlation_reader.hpp:12` colapsa
"campo numérico ilegible" sin distinguir corrupto de centinela. Inocuo hoy (no hay
centinela en los unsigned); trampa para un campo unsigned futuro con centinela `-1`.

- **Deuda:** `DEBT-PARSE-VERIFY-SENTINEL-001` **degradada P0 → P2**. Acción: documentar
  que el contrato usa `0` para puerto-ausente; documentar la asimetría
  signed(sec/nano)/unsigned(puertos); vigilar campos unsigned futuros.

### V3 — Writer/reader resuelven al mismo path  ✓ (roja BENIGNA)

- **Writer:** `correlation_writer.cpp:177` →
  `return config_.base_dir + "/" + date + ".csv"` (rota por fecha).
- **Reader:** `main.cpp:60-68,104` abre un **único path fijo** (`--bronze` o
  `ARGUS_BRONZE_CSV`) con un solo `ifstream in(bronze_path)`.
- **Rotation-follow roto (medido):** `main.cpp:125-132` hace `in.clear(); drain()`
  sobre el **mismo** handle. Cuando el writer rota a medianoche al fichero del día
  siguiente, el reader sigue tailando el de ayer y **nunca ve el nuevo**.
- **Veredicto:** roja con causa conocida y **parche ya planificado** (Eslabón 0:
  watcher `inotify`/`IN_CLOSE_WRITE`). No bloquea el ADR; lo justifica.
- **Deudas P0 confirmadas:** `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`,
  `DEBT-CONFIG-BRONZE-HARDCODE-001` (fuentes de config divergentes: writer = JSON
  `base_dir`, reader = env/arg; sincronizados a mano).

### V4 — Precondición day194  ✓ (satisfecha)

- **Medido:** `remotes/origin/day194/ransomware-provenance-desync` existe; **PR #107
  mergeado** (commit `77a3de9c`), con DAY194/195 dentro (provenance audit + desync
  dirimido + lab firetest spec). El trabajo está integrado.
- La precondición del plan ("confirmar que day194 está cerrada") apuntaba al nombre
  **local** (inexistente); la rama real es remota y ya mergeada. **No hay bloqueo.**
- **Limpieza opcional (no bloqueante):** borrar la rama remota efímera post-merge.

### V5 — Puerto ICMP en sniffer  ✓ (sin centinela negativo)

Cubierto en V2: ICMP usa `0` (`test_community_id.cpp:62`), no `-1`.

### V6 — Writer no remapea el puerto  ✓ (`0` atraviesa limpio)

Cubierto en V2: `correlation_writer.cpp:91-92` copia directa sin transformar.

### V7 — Verbo de escritura al grafo  ✓ (MERGE, equivalencia robusta a colisión)

- **Medido:** `cypher_builder.hpp:100-114` (path producción, prepared `$param`) y
  `:154-179` (path logging, interpolado) usan **MERGE** sobre `NetworkFlow {flow_uid}` y
  `Alert/TelemetryEvent {event_id}`. Solo `ON CREATE SET`, **cero `ON MATCH SET`**.
- **Consecuencia para §3.1:** colisión `flow_uid` → segundo flujo descartado idéntico en
  ambos caminos → equivalencia robusta (ver nota §3.1). Fidelidad P2, no bloqueante.

### V8 — Interpolación de Cypher (línea 154)  ✓ (logging aislado, ADR-057 intacto)

- **Medido:** la interpolación de string `{flow_uid:'" << fuid << "'}` vive **solo** en
  `build_cypher()`, que alimenta `logger_->info("[CYPHER] {}", ...)`
  (`logging_graph_sink.cpp:27`) — **no toca BD**. Producción (`KuzuGraphSink`) usa
  exclusivamente prepared statements parametrizados (`kuzu_graph_sink.cpp:90-96`).
- `cypher_builder.hpp:46` documenta el invariante: producción y logging comparten
  `make_bindings()` → no pueden divergir. `:122` marca el `esc()` como defensa del log,
  NO como frontera de seguridad. **No hay regresión de ADR-057** (Cypher injection).

### V9 — Encoding canónico de `flow_uid`  ✓ (resuelta de facto)

- **Medido (`flow_uid.hpp`):** `encode_flow_input` es canónico e inyectivo:
  length-prefix `uint16` BE por string (sin separador), `window`/`seq` como enteros BE
  de ancho fijo (`put_be64`/`put_be32`), tag de versión `"argus-flowuid-v1"` (16B)
  prefijado, BLAKE2b-256 sin truncado (`static_assert` digest_size=32).
- **Paridad cross-language ya congelada:** vectores verificados byte-idénticos contra
  `hashlib.blake2b(digest_size=32)`. El converter Flujo A no puede divergir si reusa el
  encoding. → `set(flow_uid)` no falla por encoding; `DEBT-FLOWUID-CANONICAL-ENCODING-001`
  resuelta de facto (acción residual: no-duplicación, ver §3.1).

---

## 5. Eslabón 0 (primera implementación, mismo PR que este ADR)

Config bronce a JSON (`bronze_root` + patrón naming, calcado de `csv_writer`
`config_loader.cpp:455`) + watcher `inotify`/`IN_CLOSE_WRITE` + escritura atómica
`.tmp` → rename + cierre por tiempo absoluto.

Cierra: `DEBT-CONFIG-BRONZE-HARDCODE-001` + `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`
(ambas P0).

---

## 6. Deudas (estado post-gate DAY 198)

> Nombres verificados contra `grep -rhoE 'DEBT-[A-Z0-9-]+' docs/ | sort -u` (DAY 198):
> todos existen literalmente en el repo. No hay nombre inventado de memoria.

**P0:**
- `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (medida V3 — Eslabón 0)
- `DEBT-CONFIG-BRONZE-HARDCODE-001` (medida V3 — Eslabón 0)
- `DEBT-GOLD-NODE-DIMENSION-001` (ampliada V1 — incluye `flow_start_window`)
- `DEBT-GOLD-INTEGRITY-HMAC-001`
- `DEBT-ZMQ-DELIVERY-GUARANTEE-001`

**P1:**
- `DEBT-HOST-DOMAIN-CONTRACT-001` (pre-Eslabón 1; contrato Wazuh host↔red por definir)
- `DEBT-PARQUET-KUZU-CONNECTOR-001` (greenfield, Eslabón 2)
- `DEBT-CIRCUIT-FS-DROP-001`

**P2:**
- `DEBT-PARSE-VERIFY-SENTINEL-001` (**degradada de P0** — medida V2; doc + vigilancia)
- `DEBT-ADAPTERSPEC-ENVELOPE-001`
- `DEBT-DOCS-MEDALLION-DUALITY-001` (firma del oro HMAC ≠ Ed25519 RAG — ver §2 corolario 6)
- `DEBT-JOIN-CONFIDENCE-001` (gobierna la cláusula de caducidad §3.2)
- `DEBT-FLOWUID-SEQ-COLLISION-001` (medida V7 — `seq_in_window=0`; fidelidad, no
  equivalencia; no bloquea el medallón)
- `DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` (PK compuesta `(flow_uid, seq)` no implementada;
  el schema usa PK simple `flow_uid`)
- `DEBT-FLOWUID-CANONICAL-ENCODING-001` (**resuelta de facto** — medida DAY 198;
  encoding inyectivo length-prefixed + BE + tag versión, paridad C++/Python congelada;
  acción residual: converter Flujo A reusa `encode_flow_input`, no reimplementa)
- `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (**nueva DAY 199** — medida; `temporal_anomaly`
  excluida del predicado §3.1 por derivar de `ingested_at` (`cypher_builder.hpp:86`). Su
  verificación es un test unitario de la fórmula —mismo `window` + `ingested_at` fijo ⇒ mismo
  bool—, no equivalencia-entre-caminos. El converter Flujo A debe portar la fórmula 1:1.)

**P3:**
- higiene `backups/`/`.backup` → `git rm --cached` / `.gitignore`
- limpieza rama remota `day194/...` efímera (V4)

---

## 7. Consecuencias

- El medallón se cierra primero por Camino 0 (existe), con el test de equivalencia
  §3.1 como gate de aceptación de Flujo A+B.
- El contrato de 19 columnas **no se modifica** (V2 lo dejó intacto: los tipos son
  correctos extremo a extremo).
- `flow_start_window` se añade al oro como columna nueva (V1) — no toca el contrato
  bronce, solo el converter Flujo A y el esquema del oro-ledger.
- El ADR entra en el mismo PR que el Eslabón 0 (commit de doc no pasa gate de build,
  va con la implementación) — coherente con la regla de rama del plan.

---

## 8. Estado de ratificación

**Bit-exacto por defecto: RATIFICADO** (ronda DAY 199, Consejo 8 modelos). La sub-decisión
abierta en la v1 — `==` bit-exacto en los 3 scores double con ε degradada a cláusula de
escape condicionada a medición — se sometió al Consejo y **no fue objetada de fondo** (voto
explícito a favor; el resto refinó los bordes, no la decisión). Queda cerrada.

**Lo que esta v2 lleva al Consejo NO es re-litigación, sino confirmación de las correcciones
medidas.** La revisión adversarial de la v1 produjo objeciones de calidad. Cada una se
**midió contra `fichero:línea`**, no se debatió:

- **Cayeron contra el binario** (la medición refuta la objeción):
  - «window/seq no las escribe Camino 0» → **falso**: `cypher_builder.hpp:101,110` las
    materializa (`ON CREATE SET`).
  - «`event_id` indefinido / posible UUID v4» → **falso**: es bronce col 2
    (`correlation_reader.cpp:85`).
  - «el schema podría declarar FLOAT en los scores» → **falso**: `schema.cypher:42-44,62-64`
    son `DOUBLE`; refuerza bit-exacto.
- **Incorporadas a §3.1** (la medición confirma la objeción):
  - `hmac_row` sale del predicado → integridad bronce↔oro (0 hits de `hmac` en
    `schema.cypher`). [DeepSeek]
  - **Partición D/E**: `ingested_at` (`kuzu_graph_sink.hpp:47`) y `temporal_anomaly`
    (`cypher_builder.hpp:86`) excluidas por deterministas-de-ejecución. [hallazgo de la
    medición; ningún modelo lo vio, tampoco la v1]
  - NaN + `-0.0`: una sola regla canónica (canonicalizar, no `memcmp` crudo ni `==` crudo).
  - MERGE robusto a colisión **bajo precondición** de orden de inserción determinista.
    [Gemini/Kimi/Qwen]
- **Diferidas como deuda trazada** (fuera del alcance de este ADR, no gold-plating dentro):
  oro-ledger como multiset bajo at-least-once; HMAC scope full-row vs columnas-grafo;
  `inotify` + NFS/contenedor → fallback polling. Punteros en §6 y backlog.

Petición concreta al Consejo: **confirmar** que las correcciones de §3.1 reflejan
fielmente lo medido. No se reabre la forma del oro (ratificada DAY 197) ni bit-exacto
(ratificado DAY 199). 10.8 diferida con ticket (`DEBT-JOIN-CONFIDENCE-001`). Con esta
confirmación, el plan cierra como ADR.

---

## 9. Changelog v1 → v2 (DAY 199)

Trazabilidad de cada cambio respecto a la v1 presentada al Consejo. El original v1 se
conserva intacto; esta v2 es un fichero separado.

| # | §  | Cambio | Origen | Veredicto medido |
|---|----|--------|--------|------------------|
| 1 | 1  | "6 verificaciones" → "9" | A3 (Claude) | fósil de versión previa |
| 2 | 3.1| Predicado particionado D/E; `ingested_at`+`temporal_anomaly` EXCLUIDAS | medición DAY 199 | `kuzu_graph_sink.hpp:47`, `cypher_builder.hpp:86` |
| 3 | 3.1| `hmac_row` fuera del predicado → integridad bronce↔oro | DeepSeek | 0 hits `hmac` en `schema.cypher` |
| 4 | 3.1| Nota: `event_id`=bronce col 2; window/seq YA materializadas | GLM/Kimi (refutadas) | `correlation_reader.cpp:85`, `cypher_builder.hpp:101,110` |
| 5 | 3.1| Guarda canónica única NaN + `-0.0` (no `memcmp` crudo) | Claude/Gemini/DeepSeek/Qwen | IEEE 754 |
| 6 | 3.1| MERGE robusto **bajo** orden de inserción determinista | Gemini/Kimi/Qwen | `cypher_builder.hpp` MERGE/ON CREATE |
| 7 | 6  | Nueva `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P2) | hallazgo medición | `cypher_builder.hpp:86` |
| 8 | 6  | Ref `§2.6` → `§2 corolario 6` | A4 (Claude) | higiene interna |
| 9 | 8  | Cierre: "confirmar lo medido", no re-litigar; bit-exacto RATIFICADO | árbitro | — |

> Nota de scope: objeciones de gold-plating del lote (backpressure/HWM, schema evolution,
> SLA del test, key management, RBAC, retention, rollback, timezone, hash-grafo-completo)
> se declinan en este ADR por violar "una batalla" / ya cubiertas por deuda existente.
> No son defectos del circuito; son trabajo post-FEDER o de otra capa.