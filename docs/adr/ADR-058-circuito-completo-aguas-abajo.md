# ADR-058 — Circuito completo aguas abajo (medallón: adapters → bronce → LZ → Kuzu → dashboard)

- **Estado:** PROPUESTO (pendiente ratificación final del Consejo)
- **Fecha:** DAY 198
- **Rama:** `day196/circuit-adapters-zmq`
- **Supersede / consolida:** `PLAN — Circuito completo aguas abajo (DAY 196 → implementación).md` (consolidado DAY 197, §10 = decisiones cerradas)
- **Relacionado:** ADR-046 v4, ADR-051 (parity gate), ADR-052 (flow_uid identidad multi-nodo), ADR-057 (Kuzu / bitemporalidad)
- **Invariante rector:** medir, no votar. Toda decisión de este ADR está trazada a `fichero:línea` del binario, no a memoria.

---

## 1. Contexto

El circuito aguas abajo materializa el flujo completo desde los adaptadores hasta el
dashboard: `adapters → bronce → Landing Zone (medallón) → grafo Kuzu → dashboard`.
La forma del oro fue ratificada 9/9 por el Consejo en DAY 197. Este ADR la sella y
añade la evidencia medida en el gate de DAY 198 (6 verificaciones contra bytes).

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

```
EQUIV(Camino0, FlujoA+B) :=
   set(flow_uid)_C0                  == set(flow_uid)_AB         # NetworkFlow
 ∧ set(event_id)_C0                  == set(event_id)_AB         # Alert ∪ TelemetryEvent
 ∧ ∀ uid: props_identidad(uid)_C0    == props_identidad(uid)_AB  # node_id, community_id,
                                                                 #   flow_start_window, seq_in_window
 ∧ ∀ eid: props_veredicto(eid)_C0    ≈ε props_veredicto(eid)_AB  # cols 12-17; los 3 scores
                                                                 #   double con tolerancia ε (ver nota)
 ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)
 ∧ ∀ fila: hmac_row preservado de bronce
```

**Nota — tolerancia ε en los scores (medido DAY 198):** el path de producción
(`KuzuGraphSink`, prepared statements) pasa los `double` (cols 14-16) como **binding
nativo, sin serializar a texto** → sin pérdida. Pero el roundtrip del **Flujo A+B**
serializa el double a Parquet y de vuelta. La igualdad de los 3 scores debe compararse
**con tolerancia ε** (no bit-exacta), o la equivalencia falla por redondeo Parquet, no
por bug lógico. (El path de logging ya fuerza `precision(17)` + `locale::classic()` en
`cypher_builder.hpp:151` — el equipo conoce el riesgo de precisión/locale.)

**Nota — robustez a colisión `flow_uid` (medido DAY 198):** el sink usa **MERGE** en
ambos paths (`cypher_builder.hpp:100,154`), con **solo `ON CREATE SET`, sin
`ON MATCH SET`** (8 ocurrencias CREATE, 0 MATCH). Consecuencia: ante dos flujos que
hashean al mismo `flow_uid` (colisión por `seq_in_window=0`,
`DEBT-FLOWUID-SEQ-COLLISION-001`), el segundo hace MATCH puro y sus propiedades se
**descartan de forma idéntica en ambos caminos**. Por tanto la **equivalencia se
sostiene** ante colisión — Camino 0 y Flujo A+B producen el mismo grafo. La colisión es
deuda de **fidelidad** (se pierde un flujo real, P2), NO de **equivalencia** (ambos
caminos pierden el mismo). El predicado §3.1 es robusto a la colisión; el medallón **no
queda bloqueado** por ella.
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
- `DEBT-DOCS-MEDALLION-DUALITY-001` (firma del oro HMAC ≠ Ed25519 RAG — ver §2.6)
- `DEBT-JOIN-CONFIDENCE-001` (gobierna la cláusula de caducidad §3.2)
- `DEBT-FLOWUID-SEQ-COLLISION-001` (medida V7 — `seq_in_window=0`; fidelidad, no
  equivalencia; no bloquea el medallón)
- `DEBT-NEO4J-FLOW-KEY-COMPOSITE-001` (PK compuesta `(flow_uid, seq)` no implementada;
  el schema usa PK simple `flow_uid`)
- `DEBT-FLOWUID-CANONICAL-ENCODING-001` (**resuelta de facto** — medida DAY 198;
  encoding inyectivo length-prefixed + BE + tag versión, paridad C++/Python congelada;
  acción residual: converter Flujo A reusa `encode_flow_input`, no reimplementa)

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

## 8. Pendiente de ratificación

Decisión VIVA para el Consejo: **ninguna abierta.** 10.8 diferida con ticket
(`DEBT-JOIN-CONFIDENCE-001`). El plan está listo para cerrar como ADR.