# ADR-057 — Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla

**Estado:** Provisional / en maduración. Contiene decisiones **FIRMES**, decisiones **RESUELTAS POR MEDICIÓN** (v2, DAY 182) y decisiones **ABIERTAS** que se resuelven por **medición, no por votación**. Revisado por el Consejo de Sabios (1ª vuelta DAY 181, 2ª vuelta DAY 182 sobre el smoke ejecutado).

**Componente:** **`graph-engine`** (componente propio, distinto de `correlation-engine`). Lee la **zona GOLD** del lakehouse gobernado por **Apache Iceberg** (bronce/plata/oro) y es el **único dueño `READ_WRITE`** del/los fichero(s) `.kuzu`: crea, actualiza y sirve lecturas del grafo. No tiene relación con `rag-ingester`/`rag-security`. **Nota de migración:** las clases de grafo (`IGraphSink`, `KuzuGraphSink`, `LoggingGraphSink`, `cypher_builder`, `flow_uid`, `ingest_clock`) viven hoy físicamente en `correlation-engine`; su hogar definitivo es `graph-engine` y habrá que extraerlas (DEBT-GRAPH-ENGINE-EXTRACTION-001).

---

## 0. Revisión — qué cambia respecto a la versión embrionaria

1. Incorpora el **medallion** (Iceberg: bronce/plata/oro) como entorno del grafo; `correlation-engine` alimenta bronce, `graph-engine` lee oro.
2. **Resuelve** §2.1 (in-process vs. servicio) con el modelo de concurrencia real de Kuzu.
3. **Abre tres decisiones medidas:** (D1) un grafo vs. N grafos; (D2) Kuzu original vs. fork de Vela; (D3) motor columnar Arrow/C++ vs. DuckDB para el join silver→gold y el scan de dataset.
4. **Fija la frontera de responsabilidades:** generación de dataset = scan parquet gold; grafo = travesía de grano fino.
5. Reabre el supuesto previo de "DuckDB para el tier frío": ahora es decisión medida, no dada por sentada.
6. **Subordina** D1/D2/D3 al propósito último (§7): el criterio de desempate es qué opción desbloquea antes la generación de datasets para el experimento de aprendizaje ensemble.
7. Añade **§7 (Propósito y condición de validez del experimento)** y **fija D3 dentro de este ADR** (no se extrae a un ADR-058), por la decisión deliberada de cerrar ADRs abiertos antes que abrir nuevos.

### 0.bis — Cambios de la v2 (DAY 182): el smoke B1, ejecutado

El smoke `DEBT-KUZU-CONCURRENCY-SMOKE-001` (adelantado a Fase 0 por arbitraje DAY 181) se **ejecutó y midió**. Sus resultados **cierran D1 y D2** y refinan §2.0/§2.1. Cambios concretos:

- **§2.5 (D1) y §2.6 (D2): de ABIERTA → RESUELTA POR MEDICIÓN.** Un grafo, Kuzu stock, **Vela NO**. Evidencia en §3.0.
- **§2.0/§2.1: reforzadas** con lo medido (lock cross-proceso confirmado; 2º `Database` in-process abre → footgun → guarda barata).
- **Nuevo §3.0** con la tabla de resultados del smoke (run1/run2/run3) y el veredicto.
- **Nuevo §3.1** — Fase 0 del grafo, medida: `ingested_at` + `temporal_anomaly` (verde) + las **tres guardas baratas que protegen el experimento** bajo carga (no "production-readiness").
- **§2.8 (nuevo) — Índice temporal:** Kuzu 0.11.3 **no tiene índice de rango**; la aceleración temporal vive en el tier frío (Parquet/DuckDB), el caliente acepta full-scan + medir. (Reescribe el ítem "índice sobre `ingested_at`" que la 1ª vuelta del Consejo había sugerido.)
- **Nuevo §8 — Endurecimiento DIFERIDO:** el feedback de la 2ª vuelta del Consejo (durabilidad WAL, atomicidad de batch, backpressure, tiering) se aparca con nombre y experimento, **activable si y cuando la hipótesis se corrobore y se decida desplegar** (ver §7). No es camino crítico del experimento.

**Distinción que esta v2 fija explícitamente, para que no se vuelva a confundir:** el eje de este ADR (§7) es *¿aguanta el andamiaje la carga de la prueba y nos deja medir si el ensemble + el grafo hacen ver más a aRGus?* — NO *¿es el sink production-ready para un NDR hospitalario desplegado?*. La 2ª vuelta del Consejo respondió, con razón, a la pregunta tal como se le formuló (production-readiness) y marcó cinco bloqueantes. **En el eje real del experimento, casi ninguno bloquea:** la durabilidad tras crash, el DoS por envenenamiento o el staleness en ataque activo son propiedades de un servidor *desplegado*, no de la ruta crítica hacia el *resultado científico*, que se publica salga como salga (corroborada con estos datos, o no corroborada con estos otros). Lo único del feedback que sí entra ahora es lo que impide que **el banco de pruebas falsee la medición** (§3.1).

---

## 1. Contexto

El recorrido del dato, tal como queda establecido:

`correlation-engine` recibe los ficheros-contrato **aspectv1** de cada componente → los deposita en la **LZ bronze** (Apache Iceberg). Promoción por fases consolidadas: CSV (bronze) → **Avro** al consolidar → **Parquet** en **silver** al consolidar → **parquets con join** en **gold** (join de aRGus+Suricata+Zeek por `community_id`; posibles joins adicionales por `trace_id` / `flow_id`). El grafo se construye **desde gold**, y lo construye `graph-engine` (componente propio).

De aquí emergen **dos superficies de lectura distintas**, con cargas distintas:
- **Columnar** (lakehouse): generación de datasets, agregados, consultas a frío.
- **Travesía** (grafo): correlación de grano fino.

**Casos de uso conocidos:** (a) generación de datasets que juntan todas las señales de telemetría; (b) retro-hunt de IOC; (c) **otros aún desconocidos**. El conjunto de consultas es incompleto y va a crecer.

**Principio rector bajo incertidumbre de queries:** *modelar el dominio, no la consulta.* Las consultas son volátiles; el dominio de telemetría (flujo, host, sensor, señal, cadena causal) es estable.

**Perfil de carga:** se prevén **muchas más actualizaciones que lecturas** (escrituras dominantes). Solicitar la generación de un dataset es una solicitud de **lectura**. **Confirmado por medición (DAY 182):** bajo perfil write-heavy realista (~100:1), el cuello de escritura de Kuzu es el overhead por-`query()`, no el fsync ni el escritor único (§3.0).

**Contingencia de upstream:** Kuzu fue **archivado por upstream (oct-2025)**, v0.11.3 release final (pin SHA256). Mitigado por `DEBT-KUZU-UPSTREAM-ARCHIVED-001` (P2) + la abstracción `IGraphSink` (backend intercambiable) + plan B fork `Vela-Engineering/kuzu`. **El catálogo de plantillas (§2.3) es la frontera de portabilidad** — no acumular Cypher nativo fuera de él.

---

## 2. Decisión

### 2.0 Modelo de concurrencia de Kuzu — FIRME (restricción de entorno, MEDIDA DAY 182)

- Kuzu es embebido; el **lock es por fichero** de base de datos. **Varios `.kuzu` distintos conviven**, cada uno en `READ_WRITE`, sin conflicto mutuo; un mismo proceso puede sostener N objetos `Database` apuntando a N ficheros **distintos**.
- **Por cada fichero:** exactamente **un proceso** puede ser su dueño en `READ_WRITE`. Dentro de ese proceso, **múltiples `Connection`** sacadas del único `Database` compartido emiten lecturas **y** escrituras concurrentes de forma segura (cada sentencia va envuelta en transacción). **Esta es la garantía firme que satisface la *conditio sine qua non*** (R/W concurrente).
- **MEDIDO (smoke [B], DAY 182):** un **segundo proceso** que abra el mismo fichero **es rechazado por lock** (exit=2, confirmado). PERO un **segundo `Database` in-process sobre el mismo path ABRE** sin error — Kuzu **no se autoprotege in-process**: dos buffer managers sobre los mismos datos = corrupción silenciosa. Es un **footgun**, no una protección. → guarda propia obligatoria (§3.1, `DatabaseRegistry`).
- **MEDIDO (smoke, escritura):** Kuzu permite **una sola write-tx en todo el sistema** — confirmado por el propio motor: *"Cannot start a new write transaction... Only one write transaction at a time is allowed."* Es invariante de software de Kuzu, **no artefacto de VM**.
- **Consecuencia:** cualquier proceso que no sea el dueño debe llegar al grafo **a través del dueño** (fachada IPC, p. ej. el patrón ZMQ ya existente), nunca abriendo el fichero.

### 2.1 Ubicación: in-process, un único proceso dueño — FIRME

El componente de grafo (**`graph-engine`**) es el **único dueño `READ_WRITE`** del/los fichero(s) de grafo. Lee eventos de la zona GOLD de Iceberg y atiende las consultas de grano fino. El invariante operativo es **"un solo proceso es dueño del `.kuzu`"**, no "un solo usuario": varios administradores son válidos siempre que hablen con ese proceso, no que abran el fichero. **Reforzado DAY 182:** "un solo proceso dueño" es correcto NO porque el lock impida un 2º `Database` in-process (no lo impide — es un footgun), sino porque cross-proceso está bloqueado **y** in-process es un footgun. La guarda lo hace imposible por construcción (§3.1).

### 2.2 Frontera de responsabilidades — FIRME

- **Generación de dataset = scan columnar sobre parquet gold**, *no* travesía de grafo. No lee siquiera de Kuzu: lee el tier columnar. Esto descarga al grafo de la exportación masiva.
- El **grafo** queda reservado para lo que solo el grafo hace: **travesías de correlación de grano fino** (retro-hunt y las que vengan).

### 2.3 Interfaz de consulta: plantillas parametrizadas, sin LLM al inicio — FIRME *(heredado)*

Path 2: plantillas Cypher parametrizadas; nada de NL→Cypher libre. El LLM, cuando se añada, mapea NL→(intención, parámetros) contra plantillas pre-validadas. El catálogo de preguntas SOC *es* la biblioteca de plantillas. La capa NL es azúcar intercambiable, diferida (ADR propio, DEBT-NL-BENCHMARK-001). **El catálogo es además la frontera de portabilidad ante el upstream archivado.**

### 2.4 Bitemporalidad — FIRME *(heredado, implementado Fase 0 DAY 182)*

`event_time` vs. `knowledge_time`. Los flujos nunca se reescriben; los indicadores se **anotan** sobre ellos con `knowledge_time`. Habilita forense reproducible e informes "a fecha de". Implementación Fase 0 en §3.1: `ingested_at` (provenance/first_seen, NO reproducibilidad — wall clock deliberado, distinto del `bpf_ktime` envenenable del sensor) + `temporal_anomaly` (unilateral: futuro-datación = firma de clock-injection).

### 2.5 Topología: un grafo vs. N grafos — ✅ RESUELTA POR MEDICIÓN (D1, smoke B1, DAY 182)

**Veredicto: UN GRAFO.** El smoke confirmó las dos mitades del razonamiento original:
- La amplificación de escritura de N grafos por eje (`community_id`/`trace_id`/`flow_id`) duele justo donde las escrituras dominan, y fragmenta las consultas cross-eje futuras. Modelo correcto: **un grafo, ejes como tipos de arista/nodo**.
- El único beneficio de fragmentar —paralelismo de escritura— **no existe en Kuzu stock**: el smoke (run3, 4 writers) midió **373.000 rechazos** por la única write-tx del sistema, con solo +37% de throughput y la contención de lectura p99 disparándose a ×11.37. Multi-writer **no escala**.

**Si la medición justificara fragmentar, el eje correcto sigue siendo el TEMPORAL** (sharding del tier caliente), nunca el de correlación (rompe la entidad). Diferido a §8 con invariante de shardability preservada barata (la routing key `community_id` ya existe; `IGraphSink`/`IGraphQuery` son el seam).

### 2.6 Motor de grafo: Kuzu original vs. fork de Vela — ✅ RESUELTA POR MEDICIÓN (D2, smoke B1, DAY 182)

**Veredicto: KUZU ORIGINAL (stock). Vela NO.** El lean a priori era Vela (multi-writer in-process). La medición lo revierte:
- El cuello **NO era la serialización del escritor único**. Era el **overhead por-`query()`** (parse/plan + fsync por llamada). La palanca real es **batchear sentencias con `UNWIND`** (una `query()` = N upserts), que da **×55–61** y vive en Kuzu stock.
- Lo único que Vela añadiría —writers paralelos— es exactamente lo que run3 demostró que **no escala** (single write-tx). Por tanto Vela no aporta sobre el problema medido.
- **Reconsiderar Vela solo si** un sink con UNWIND batch + 1 writer se mide corto en hardware real (x86 RAW / N100 / RPi5, ADR-041) — y entonces como decisión del Consejo con revisión de seguridad (fork de comunidad, supply-chain; nótese que el upstream de Kuzu también está archivado).

`DEBT-KUZU-UPSTREAM-ARCHIVED-001` (P2) sigue vigente como contingencia; este veredicto NO la cierra, solo decide que el salto a Vela no está justificado hoy por rendimiento.

### 2.7 Motor columnar de promoción/consulta: Arrow/C++ vs. DuckDB — ABIERTA (D3, sin tocar)

**El smoke de Kuzu NO toca esta decisión.** D3 sigue ABIERTA y se resuelve con **B2** (banco de promoción/join, §3). El lean (capita fina C++/Arrow si se mantiene fina; DuckDB si igualar su robustez convierte la capita en medio motor) permanece sin cambios. *Nota: se mantiene dentro del ADR-057, no se extrae a ADR-058.*

### 2.8 Índice temporal del tier caliente — FIRME (MEDIDO/VERIFICADO DAY 182)

Kuzu 0.11.3 **no ofrece índice secundario ni de rango** (solo PK-hash, FTS sobre STRING, HNSW sobre vectores — verificado). Por tanto **no existe "índice sobre `ingested_at`"** en el tier caliente. Consecuencia de diseño:
- La **aceleración de consultas por rango temporal vive en el tier FRÍO** (Parquet/DuckDB, predicate pushdown).
- El **tier caliente (Kuzu) acepta full-scan temporal + medir**; si el full-scan se mide caro a escala real, la respuesta es **tiering hot→cold más agresivo** (§8), no un índice que el motor no tiene.
- Los campos crudos (`flow_start_window`, `ingested_at`) se conservan para que un cálculo bitemporal a futuro (bilateral/pasado) se haga en runtime sin cerrar puertas.

---

## 3. Experimentos que resuelven las decisiones abiertas (el instrumento)

El smoke test deja de ser una comprobación de corrección y se convierte en el **instrumento que decide la arquitectura**.

**Criterio de desempate (ver §7):** si B1 o B2 no arrojan un ganador nítido, gana la opción que **antes desbloquee la generación de datasets** para el experimento de aprendizaje. Velocidad hacia el experimento por encima de elegancia arquitectónica.

### 3.0 — B1 EJECUTADO (resuelve D1 + D2) · DAY 182

Banco de contención escritura/lectura con perfil write-heavy realista (i9 / VirtualBox, `/tmp` nativo del guest — NO vboxsf, que rompe el `mmap` de Kuzu —, 5 s, grafo inicial 100k nodos vía UNWIND, upsert flood ~100:1):

| run | estrategia | upserts/s | por-upsert p50 | maxRSS | veredicto |
|-----|-----------|-----------|----------------|--------|-----------|
| 1 | MERGE/fila (sink actual) | 164–229 | ~6.0 ms | 632 MB | overhead por-`query()` |
| 2 | UNWIND batch=1000, 1 writer | 10.000–12.200 | ~78–94 µs | 664–682 MB | **×55–61 más rápido** |
| 3 | UNWIND batch=1000, 4 writers | 13.800–16.000 | ~82–97 µs | 821 MB | 373k rechazos write-tx, no escala |

**Descomposición (de los dos primeros runs):** `coste(n) = P + S + n·E` → **E ≈ 88 µs/fila** (ejecución real del MERGE, irreducible), **P+S ≈ 5.93 ms** (parse/plan + commit/fsync, fijo, amortizable). El ×55–61 es *enteramente* amortizar ese coste fijo de 1-por-fila a 1-por-1000.

**Hallazgos de operación medidos (cada uno contradijo doc o supuesto):**
1. **Lock:** la doc decía que un 2º `Database` sobre el mismo path falla. MEDIDO: cross-proceso sí falla (exit=2); **in-process abre** (footgun, dos buffer managers → corrupción). El "un Database, N Connections" es correcto por ser cross-proceso-bloqueado **y** in-process-footgun, no por el lock.
2. **Cuello = overhead por-`query()`, no fsync solo ni single-writer.** UNWIND+single-MERGE >> MERGE-por-fila (el procesamiento estático domina).
3. **Crash (Ctrl-C/SIGKILL) deja WAL huérfano.** Incidente del propio smoke: borrar el `.kuzu` y dejar el `.wal` huérfano → reapertura lanza `unordered_map::at`. **Corrección honesta:** fue auto-infligido (inconsistencia artificial), NO prueba de fallo de recuperación de Kuzu. El smoke se auto-sana con `cleanup_db` (limpia `.wal`/`.lock`/sidecars al arrancar). La recuperación real tras crash queda sin validar → §8 (no bloquea el experimento).

**Veredicto B1:** un grafo (D1), Kuzu stock (D2), Vela NO. El sink de `graph-engine` debe escribir con **UNWIND batch + 1 writer**.

> *La documentación es un voto; el smoke es una medida.* — DAY 182

### 3.1 — Fase 0 del grafo (MEDIDA / IMPLEMENTADA) + guardas que protegen el experimento

**Verde y aplicado (EMECAS DAY 182):**
- `ingested_at` (epoch-ns wall clock = first_seen, `ON CREATE SET`) en las 3 tablas de nodo (`NetworkFlow`, `Alert`, `TelemetryEvent`).
- `temporal_anomaly` (BOOLEAN, **unilateral**: TRUE si `flow_start_window > ingested_at + margen`) solo en `NetworkFlow`. Margen `kTemporalMarginNs = 2s` PLACEHOLDER a calibrar. Raw fields conservados para un cómputo bilateral/pasado a futuro.
- `build_cypher()` toma `ingested_at_ns` por parámetro (función libre, determinista y testeable con valor fijo — sin DI). `cypher_builder` es la única fuente de Cypher, `locale::classic()` siempre. Cierra la frontera de inyección Cypher (H-1).
- `make test-components` ahora corre `correlation-engine-test` PRIMERO (cerró `DEBT-CE-TESTS-UNGATED-001`: los tests de Kuzu+H-1 no gateaban merges desde DAY 180).

**Tres guardas baratas que protegen LA MEDICIÓN (no production-readiness), necesarias para que el banco aguante la tortura de datos a 33 Mb/s (Vagrant) y más en x86 RAW sin perder ni corromper datos del experimento:**

1. **Sink con UNWIND batch + flush-by-(size OR time) + 1 writer.** El throughput (×55–61) viene del batch; el flush-by-time evita cegarse en valles de caudal (un flow no debe quedar sin commitear indefinidamente si el batch no se llena). Sin esto, la riada o satura (pierde) o el grafo va stale. Es condición de que el experimento **mida lo que entra**.
2. **`DatabaseRegistry` (path→`weak_ptr<Database>`).** Hace **imposible** abrir un 2º `Database` sobre el mismo path (lanza). Protege los runs de una corrupción auto-infligida (el footgun de §2.0). Barato (~10 líneas + test). *Bonus:* habilita N paths distintos → no cierra la puerta al sharding temporal de §8 (un singleton ciego sí la cerraría).
3. **Capar `bufferPoolSize` en init** según la RAM asignada a Vagrant (y al x86 RAW). Evita que Kuzu coja RAM por defecto y compita con el resto del pipeline durante la tortura. El RSS queda acotado por el cap (Kuzu pagina a disco) — **no es el OOM lineal que se temió**; el riesgo real a escala es la latencia de paginación, que se mide aparte (§8).

**Estas tres son las únicas piezas del feedback de la 2ª vuelta del Consejo que entran en el camino crítico del experimento.** El resto se difiere (§8).

### 3.2 — B2 PENDIENTE (resuelve D3)

Banco de promoción/join (Arrow/C++ vs. DuckDB) sobre el join aRGus+Suricata+Zeek por `community_id`. Tres ejes: rendimiento, comportamiento bajo presión de memoria (spill), coste de mantenimiento medible (líneas de C++ crítico). **Sin ejecutar.** Avro fuera del cuadrilátero.

---

## 4. Consecuencias

- (+) R/W concurrente **garantizado** in-process; la *conditio sine qua non* queda satisfecha y **medida**.
- (+) D1 y D2 **resueltas con datos** (un grafo, Kuzu stock), no con votos ni elegancia.
- (+) Separación nítida de superficies de lectura: columnar (masivo/dataset/frío) vs. travesía (grano fino).
- (+) Diseño **robusto ante consultas futuras desconocidas** (grafo modelado por dominio).
- (+) El sink batcheado da ×55–61 — el andamiaje puede tragar la tortura de datos del experimento.
- (−) Potencialmente **tres motores** en el stack (Kuzu, Arrow, quizá DuckDB): mantenimiento + deuda de versiones.
- (−) D3 **diferida** hasta B2 — cierre no alcanzado por diseño (*medir, no votar*).
- (−) Endurecimiento de producción (durabilidad WAL, atomicidad, backpressure, tiering) **diferido a §8**: el andamiaje del experimento no es un despliegue hospitalario, y no debe pagar ese coste hasta que la hipótesis lo justifique.
- (−) Upstream Kuzu archivado: contingencia viva (`DEBT-KUZU-UPSTREAM-ARCHIVED-001`).

---

## 5. Alternativas consideradas

- **Particionar el grafo por eje de correlación** → descartado por medición (D1, §2.5); rompe la entidad y triplica la escritura; el paralelismo que justificaría fragmentar no escala en Kuzu (run3).
- **Fork de Vela (multi-writer)** → descartado por medición hoy (D2, §2.6); revisable solo si UNWIND+1writer se mide corto en hardware real.
- **Índice sobre `ingested_at` en Kuzu** → imposible (Kuzu 0.11.3 no tiene índice de rango, §2.8); la aceleración temporal vive en el tier frío.
- **Exponer Cypher crudo / NL→Cypher libre con LLM** → descartado *(heredado)*.
- **Sin bitemporalidad** → insuficiente para forense reproducible *(heredado)*.
- **DuckDB dado por sentado para el tier frío** → reabierto: decisión medida (D3, B2).

---

## 6. Pendiente antes del cierre del ADR

- [x] Ejecutar **B1** (D1+D2) — HECHO DAY 182, resultados en §3.0.
- [ ] Ejecutar **B2** (D3, Arrow vs DuckDB) — traer números.
- [ ] Decidir el **nombre** del componente (`graph-engine` provisional; candidatos `graph-sentinel`/`graph-warden`).
- [ ] **Extraer las clases de grafo de `correlation-engine` a `graph-engine`** (DEBT-GRAPH-ENGINE-EXTRACTION-001).
- [ ] Calibrar el **margen de `temporal_anomaly`** (2s placeholder) con dato real.
- [ ] Definir la **partición disjunta de escenarios MITRE** (entrenar A–M / evaluar N–Z) antes del experimento de aprendizaje (§7).
- [ ] *(heredado)* Catálogo inicial de plantillas (§2.3); dependencia con `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001`.

---

## 7. Propósito: esta capa es andamiaje, no fin

Toda esta capa —medallion, join en gold, grafo, motor columnar— **no es el fin, es andamiaje.** Existe para habilitar **la pregunta fundamental del proyecto**: ¿pueden los modelos ensemble (árboles) aprender de la experiencia acumulada que han visto los nodos distribuidos y mejorar con ella? Demostrar esa mejora es lo más importante.

Como **no existe todavía una red distribuida real**, la hipótesis se somete a prueba por sustitución: ejecutar **tests MITRE lo más variados posibles** que ataquen al **pipeline completo** al máximo de caudal disponible (33 Mb/s en Vagrant; mayor en el servidor x86 RAW conectado a la misma red, fuera de Vagrant), producir datasets, y medir si el ensemble mejora al incorporar la experiencia previa.

**El andamiaje debe aguantar la tortura.** El pipeline tiene que tragar la carga máxima de la tarjeta de red sin perder ni corromper datos del experimento — de ahí las tres guardas de §3.1 (UNWIND batch para throughput, flush-by-time para no cegarse, `bufferPoolSize` capado para no competir por RAM). Esto NO es "production-ready para hospital": es "el banco de pruebas no falsea la medición".

**Subordinación de decisiones.** D1, D2 y D3 son **instrumentales**. Cuando B1/B2 no den un ganador nítido, el criterio de desempate es **qué opción desbloquea antes la generación de datasets** — no qué arquitectura es más elegante. Una opción 90% tan buena que permita generar datasets esta semana gana a una óptima que llegue el mes que viene. El desarrollo no se puede eternizar: necesitamos ver resultados.

**Condición de validez del experimento (no negociable).** Los escenarios MITRE que generan el dataset de "experiencia previa" deben ser **disjuntos** de los que evalúan la mejora. Se entrena con la experiencia de los escenarios **A–M** y se mide la mejora contra escenarios **N–Z no vistos**:
- Mejora sobre **N–Z** → aprendizaje sobre experiencia (resultado publicable).
- Mejora solo sobre **A–M** → memorización / overfitting al banco (no publicable). Esta partición *es* el experimento. Walk-forward + golden set inmutable conforme a **ADR-040**.

**Honestidad científica (*medir, no votar*).** El experimento debe poder decir **que no**. Un resultado **nulo o negativo** con datos disjuntos también es un hallazgo, y se publica: indicaría que la hipótesis necesita más señal, más nodos o un dataset más rico antes de sostenerse. Pase lo que pase —hipótesis corroborada con estos datos, o camino seco con estos otros— **se entregan datasets de valor al equipo de Andrés (UEx/INCIBE)**, y la decisión de publicar una cosa u otra **no depende de tener la mejor implementación posible del grafo.** Si el diseño solo pudiera confirmar, no sería medición.

---

## 8. Endurecimiento DIFERIDO (no es camino crítico del experimento)

Recoge el feedback de la **2ª vuelta del Consejo (DAY 182)** que es real para un **despliegue de producción** pero **NO** para el andamiaje del experimento. Todo aquí queda con nombre y experimento, **activable si y cuando la hipótesis se corrobore y se decida desplegar en infraestructura real** (RPi5/N100/x86). Encuadrado bajo `DEBT-KUZU-CONCURRENCY-SMOKE-001` en el BACKLOG (paraguas único, para que este hilo resurja con la noticia — buena o seca — sobre la hipótesis ensemble).

| Eje | Qué falta | Experimento que lo zanja | Por qué NO bloquea el experimento |
|-----|-----------|--------------------------|------------------------------------|
| **Durabilidad WAL (Q7)** | Recuperación real tras crash sin validar (el smoke borra el WAL; producción debe recuperarlo). | `restore_from_wal_smoke_test`: SIGKILL a media riada con AMBOS ficheros intactos → reabrir sin limpiar → 0 commits ackeados perdidos (≥100 iter). Ligado a `DEBT-LABEL-WAL-001`. | Un crash del banco se reinicia y se relanza la tanda; no falsea la métrica de mejora del ensemble. (Upstream archivado: si la recuperación falla, lo posees tú.) |
| **Atomicidad / poison (Q5)** | UNWIND = 1 tx → una fila maligna tira el batch. | Validación tipada en el borde (enlaza H-1) + bisección-retry + quarantine. Confirmar rollback total. | El tráfico del experimento es MITRE controlado, no hostil-adversarial-de-ingesta; el envenenamiento es amenaza de despliegue. |
| **Backpressure sostenido (Q10)** | Cola productor→writer único sin política bajo sobrecarga sostenida. | Productor = 2× writer durante 30 min → RSS acotada + política explícita (degradar resolución antes que cegar). | A 33 Mb/s (y x86 RAW acotado) con flush-by-size+time el sink absorbe; la sobrecarga sostenida con drop silencioso es escenario de despliegue bajo flood. |
| **Reader real (Q3)** | Contención medida con `count(*)`, no con traversal de correlación. | Sustituir por traversal 2–3 hop por `community_id`; medir p99 lectura + degradación del writer + RSS (acopla con memoria). | La "lectura sana" es claim de producción; el experimento escribe mucho y lee poco/offline (datasets = scan columnar, no traversal). Anotar como *provisional* hasta medir. |
| **Memoria a escala (Q4)** | Curva RSS vs nodos con `bufferPoolSize` fijo; tiering hot→cold. | A pool fijo (p.ej. 2 GB), cargar 100k/500k/1M → confirmar RSS acotado por pool (no OOM lineal) + medir latencia por thrashing en almacenamiento lento. Tiering Parquet/DuckDB. | Target del experimento = servidor grande (Vagrant con RAM asignada, luego x86 RAW); el OOM en RPi5 es problema de despliegue embebido. La guarda de §3.1 (capar pool) ya evita que compita por RAM. |
| **Batch sweep (Q6)** | `batch=1000` sin barrido. | Sweep `{1,10,100,300,500,1000,...}` con flush-by-time activo; codo donde Δthroughput<5%. Predicción analítica: ~300–500. | 1000 funciona y da ×55–61; el ajuste fino es optimización, no condición de medir. |
| **Decomposición fsync/parse (Q1)** | P+S≈5.93ms sin separar fsync de parse/plan; medido en VM. | tmpfs vs disco (aísla fsync) + prepared-stmt (aísla parse/plan), en x86 RAW. | La dirección (UNWIND gana, Vela no) es invariante al hardware; solo cambia la magnitud del ×. Calibración para ADR-041, no gate. |
| **Shardability (Q8)** | Preservar que el sharding temporal futuro no exija reescritura. | Mantener routing key explícita (`community_id` ya existe) + `IGraphQuery` espejo de `IGraphSink`. | Es invariante barata, ya casi satisfecha; no hay que implementar sharding, solo no cerrarle la puerta. |

**Insight de síntesis (no perder):** los cinco "bloqueantes de producción" del Consejo (flush, poison, backpressure, guard, reader) **no son cinco problemas, son uno**: gestionar una **cola hacia un único consumidor de tasa fija** (el writer único de Kuzu). En despliegue, eso es el subsistema `IngestQueue` de `graph-engine`. En el experimento, basta la versión mínima de §3.1.

---

## Fuentes (concurrencia, forks, índices — verificadas DAY 181–182)

- Kuzu — *Connections & Concurrency* (doc oficial): un `Database` `READ_WRITE` por fichero, conexiones múltiples concurrentes, patrón servidor para multi-proceso.
- Kuzu — issue #3295 / #3872: el segundo PROCESO falla por lock incluso en `READ_ONLY` mientras hay escritor.
- Kuzu — paper / docs: "one writer transaction in the system" (serializable por diseño). Confirmado en runtime DAY 182 (mensaje de error literal).
- Kuzu — UNWIND + MERGE batch (tutorial/docs): patrón set-based; principio general (Neptune/Neo4j) "una cláusula MERGE por nodo es ineficiente, UNWIND+single-MERGE es lo óptimo".
- Kuzu — índices: PK-hash + FTS (STRING) + HNSW (vectores); **sin índice secundario/de rango** en 0.11.3.
- `Vela-Engineering/kuzu`: fork con multi-writer in-process; mantenimiento activo tras el archivado del upstream. (No elimina el lock multi-proceso.)