# PLAN — Circuito completo aguas abajo (DAY 196 → implementación)

| Campo | Valor |
|---|---|
| **Documento** | Plan de implementación — circuito completo |
| **Estado** | **Ratificado por el Consejo (9/9 en forma del oro). Enmiendas incorporadas. Listo como commit de apertura de `day196/circuit-adapters-zmq`.** |
| **Fecha base** | 2026-06-26 (DAY 196) · **Consolidado DAY 197** (dictamen del Consejo + correcciones de coherencia) |
| **Autores** | Alonso Isidoro Roman + Claude (Anthropic) |
| **Referencia** | ADR-046 v4, ADR-051, **ADR-052**, ADR-057, AdapterSpec v1, contrato `correlation_v1` |
| **Rama propuesta** | `day196/circuit-adapters-zmq` |
| **Invariante** | medir, no votar · JSON is the law · bronce PRESERVA, gold DECIDE · Via Appia |

> **Convención de estado.** Cada afirmación lleva marca: **[MEDIDO]** (verificado contra fichero, evidencia en Apéndice A), **[POR VERIFICAR]** (requiere comando antes de tocar código — §8), **[DECISIÓN]** (elección de diseño) y **[RATIFICADO]** (cerrado por el Consejo, DAY 197).

---

## Dictamen consolidado del Consejo (DAY 197)

El plan se sometió a los 8 modelos del Consejo (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral). Resumen de lo que cambió respecto al borrador DAY 196:

- **Forma del oro — UNÁNIME 9/9: oro-como-ledger + join en Kuzu.** Reformulación adoptada: el ledger es el **único** oro; Kuzu y cualquier wide-table son **proyecciones co-iguales y reconstruibles**. La excepción "oro-como-join si un consumidor no-Kuzu lo necesita" se disuelve: el wide-table (incluida la matriz de features para reentrenar ML, ADR-040) es **otra proyección tabular** del ledger, no oro. No hay caso en que oro-como-join gane.
- **Rotación → P0** (era P1). Convergencia independiente de 8/8. Reescribe el Eslabón 0.
- **Wazuh → contrato separado `host_domain_v1`**, y la decisión **sube aguas arriba** (antes del Eslabón 1, no en el 5) porque el schema del medallón depende de ella. Topología: **un solo grafo, múltiples sinks de parquet**.
- **`flow_uid` es la PK del grafo, NO `community_id`** (coherencia ADR-052). Corrige los DDL propuestos por el Consejo (Kimi/ChatGPT). `community_id` es propiedad indexada e ingrediente de la PK, no la PK.
- **`node_id` / `community_id` / `flow_start_window` deben ser columnas de primera clase del oro-ledger** — para que el dataset pueda responder la hipótesis del proyecto (contribución por nodo a la calidad del dataset de ensemble). `node_id` y `community_id` **ya son columnas 3 y 4 en bronce** [MEDIDO]; la verificación pendiente es su **propagación al oro** + materializar `flow_start_window`.
- **El conector Parquet→Kuzu NO existe, ni prototipo** [MEDIDO, confirmado DAY 197]. El Eslabón 2 es construcción greenfield, no "re-apuntar". Reordena el plan: el **circuito verde se cierra primero por el Camino 0** (`ifstream` bronce→Kuzu, que ya existe).
- **Timestamp: la fusión va en la LZ, NO en el writer C++** (corrige el borrador). El output del writer ES el contrato bronce sellado; fundir ahí es breaking change.
- **ZMQ PUB/SUB ≠ at-least-once.** Handoff adapter→engine por **PUSH/PULL**; PUB/SUB solo para fan-out tolerante a pérdida. Enmienda AdapterSpec §7.1.
- **Integridad del oro:** HMAC por-fila heredado como columna + firma del Parquet consolidado. Justificación: el replay del grafo es coherente en el tiempo **si y solo si** las filas conservan su HMAC original.
- **Andrés: congelado con razón escrita.** No se toman decisiones arquitectónicas contra un repo sin código (`medir, no votar` aplicado a una dependencia externa). Se reabre cuando haya código estable.

---

## 0. Propósito

Completar el **circuito completo aguas abajo** —adapters → zona bronce → Landing Zone (medallón CSV→AVRO→PARQUET) → grafo Kuzu → dashboard de consulta— asumiendo que la inferencia ML está rota o incompleta. El circuito es el **instrumento de medición** que permitirá, *después*, decidir si una mejora de modelo es real antes de confiar en los plugins de ensemble, y sobre el que se construirá el mecanismo MITRE. No se reentrena nada antes de tener el microscopio calibrado: optimizar sin medir es optimizar a ciegas (decisión de DAY 195).

**Norte de investigación.** El circuito no es un fin: es el instrumento para resolver la hipótesis de si **nodos distribuidos** contribuyen a generar datasets de mayor calidad que capturen el comportamiento de los ataques y sirvan para entrenar modelos de ensemble. Por eso el oro-ledger debe preservar la dimensión por nodo como variable de primera clase (§3.2, §7 Eslabón 1, §10.7): un instrumento ciego a `node_id` mediría bien la pregunta equivocada.

---

## 1. Tesis y criterio de hecho

**Definición de "circuito verde" (E2E, un solo motor):** una fila de aRGus entra por el sniffer, sale enriquecida del ml-detector, aterriza en bronce como `correlation_v1` (CSV+HMAC), y se materializa en Kuzu como `:NetworkFlow` + `:Alert`, recuperable por consulta del dashboard. Un motor, extremo a extremo.

**[RATIFICADO] El circuito verde no se mide en bronce, se mide en Kuzu.** `correlation_reader.parse_and_verify` **descarta la fila en silencio** (devuelve `nullopt`) si el HMAC o el conteo de columnas fallan [MEDIDO]. Por tanto "el CSV existe en bronce" NO prueba que el circuito fluye: el writer puede escribir basura y el reader tirarla sin ruido. El criterio de hecho es un **test E2E automático** que: (1) inyecta un evento sintético (`community_id=TEST-xxx`), (2) verifica HMAC válido en bronce, (3) verifica materialización con `MATCH (f:NetworkFlow {community_id:"TEST-xxx"}) RETURN f`, (4) **falla el pipeline si cualquier paso cae**. Eso es el hito que desbloquea el MITRE.

**[RATIFICADO] El primer circuito verde se cierra por el Camino 0 (`ifstream` directo), no por el medallón.** El conector Parquet→Kuzu no existe (§8.4). Se separa "¿fluye el circuito?" de "¿funciona el medallón?": un bug en el conector nuevo no debe contaminar la medición de si el circuito fluye. Ver §7 (tres caminos) y la secuencia de eslabones.

Orden de trabajo (DAY 195/196): **chapu de FS primero** (que el circuito fluya), verificar flujo aguas abajo, y **solo entonces** migrar a ZMQ en los adapters. "Medir que fluye" antes de "hacerlo bien".

---

## 2. Topología de componentes y canales

```
[sniffer] --ZMQ--> [ml-detector] --ZMQ--> [firewall-acl-agent --> ipset]   (existente, producción)
                        |
                        | correlation_writer (escribe correlation_v1 a bronce)
                        v
                   [BRONCE *.csv]
                        |
         ┌── Camino 0 (HOY, ya existe): ifstream bronce→Kuzu directo ──┐
         │                                                            v
         │                                                      [Kuzu graph]
         │                                                            ^
         └── Flujo A (greenfield): bronce→LZ→AVRO→PARQUET (oro-ledger) │
                                          │                            │
                                          └── Flujo B (greenfield): ───┘
                                              conector PARQUET→Kuzu (NO existe)

   adapter-suricata ----+
   adapter-zeek --------+--> [correlation-engine] (handoff PUSH/PULL, §7.1 enmendado)
   adapter-wazuh -------+    (host-domain → host_domain_v1, sink aparte)
   adapter-andres ------+    (congelado, contrato negativo)
```

| Canal | Estado | Nota |
|---|---|---|
| sniffer → ml-detector | **[MEDIDO]** existe | ZMQ (`main_libpcap.cpp` connect) |
| ml-detector → firewall-acl-agent | **[MEDIDO]** existe | ZMQ PUB/SUB → batch_processor → ipset |
| ml-detector → bronce | **[MEDIDO]** existe | `correlation_writer.write_record()` |
| bronce → correlation-engine (**Camino 0**) | **[MEDIDO]** existe (chapu) | `ifstream(bronze_path)`, `--bronze`/`ARGUS_BRONZE_CSV` |
| correlation-engine → Kuzu (**Camino 0**) | **[MEDIDO]** existe | `kuzu_graph_sink`, lee bronce CSV **directo** |
| **adapter-argus** | **[MEDIDO]** NO-OP | su función ya la cumple `correlation_writer`; no es proceso nuevo |
| adapter-{suricata,zeek,wazuh,andres} | **[MEDIDO]** NO existen | greenfield |
| LZ medallón (**Flujo A**) | **[MEDIDO]** greenfield | construcción nueva — §8.1 |
| conector PARQUET→Kuzu (**Flujo B**) | **[MEDIDO]** NO existe, ni prototipo | greenfield — §8.4 |
| dashboard de consulta | **[POR VERIFICAR]** no medido | greenfield probable |

**Punto crítico (§2):** el adapter-argus **no es un binario nuevo**. `correlation_writer`, dentro de ml-detector, ya es el productor de `correlation_v1` para aRGus. El día de la migración a ZMQ, el "adapter-argus" será el socket de envío que hoy es el `ofstream` — co-ubicado en el dominio del ml-detector, **pero no indistinto de la lógica ML**: el adapter existe para que el engine sea agnóstico al motor de origen; fundirlo con el detector pierde esa propiedad. Co-ubicado sí, indistinto no.

---

## 3. Contratos — separación estricta

Dos contratos en dos capas. **No** son el mismo objeto bajo nombres distintos (esta confusión —AspectV1/AdapterSpec/correlation_v1— fue el origen del desync DAY 194; queda cerrada).

### 3.1 AdapterSpec v1 — contrato de **comportamiento** de ingesta
Normativo (DAY 169, ADR-046 v4 §3.10). Define **cómo se comporta** todo adapter, sea cual sea su payload:

- **at-least-once** (§2): ningún evento se pierde en silencio.
- **dedup idempotente** por `(source_engine, native_event_id)` (§2). Exactly-once explícitamente fuera de alcance.
- `native_event_id` **determinista** en tier golden (§4); ID nativo o hash estable en tier vivo.
- **checkpoint monotónico** persistente entre reinicios (§6).

**[RATIFICADO] Enmienda AdapterSpec v1 → v1.1 (`DEBT-ADAPTERSPEC-ENVELOPE-001`).** Dos correcciones:

1. **El envelope protobuf `SecurityEvent` (§3) no existe.** `network_security.proto` solo tiene `NetworkSecurityEvent` (L569) [MEDIDO]. La salida real al cable es **`correlation_v1` CSV+HMAC, nunca protobuf**. §3 se reescribe: "el adapter emite filas `correlation_v1`; los §§2/4/6/7.1 se conservan".
2. **El transporte interno NO es siempre PUB/SUB.** §7.1 se enmienda: el **handoff adapter→engine usa PUSH/PULL** (encola en el sender hasta HWM → compatible con at-least-once); PUB/SUB se reserva para **fan-out tolerante a pérdida** (p.ej. firewall-acl-agent, que sí puede perder mensajes en detección tiempo-real). Razón: PUB/SUB es fire-and-forget por diseño; la regla slow-joiner resuelve el arranque, no la garantía de entrega. AdapterSpec §2 ("ningún evento se pierde en silencio") es **incompatible** con PUB/SUB puro para el handoff con garantía.
3. **Cuando llegue el Eslabón 6, el frame ZMQ transporta los bytes del CSV firmado, no un protobuf reensamblado.** Razón: solo aRGus podría intentar mantener un contrato protobuf; por coherencia, **todos** los adapters transportan los bytes del `correlation_v1` CSV+HMAC. Esto preserva `parse_and_verify` intacto: el envelope ZMQ es solo framing; el cuerpo sigue siendo CSV+HMAC.

Regla slow-joiner conservada para todo socket: PUB `bind()` antes que SUB `connect()` (§7.1).

### 3.2 correlation_v1 — contrato de **dato**
19 columnas CSV posicional, sin header, HMAC-SHA256 sobre cols 0-17 en col 18. Zona bronce. **[MEDIDO]**

```
0 schema_version   1 source_sensor    2 event_id        3 node_id
4 community_id      5 flow_start_sec   6 flow_start_nano 7 src_ip
8 dst_ip            9 src_port        10 dst_port       11 protocol
12 final_classification 13 threat_category 14 fast_detector_score
15 ml_detector_score 16 overall_threat_score 17 authoritative_source
18 HMAC-SHA256(cols 0-17)
```

**[MEDIDO] `node_id` (col 3) y `community_id` (col 4) son columnas de primera clase del contrato bronce.** No están "diluidos" dentro de `flow_uid`: están explícitos. Esto resuelve a nivel bronce la preocupación de §10.7. El riesgo de dilución vive **un paso más abajo**, en el converter Flujo A (CSV→Arrow→Parquet oro): debe arrastrar cols 3 y 4 como columnas Arrow de primera clase, no usarlas solo para computar `flow_uid` y descartarlas. **Verificación de mañana** (§8.5).

El lector (`correlation_reader.parse_and_verify`) **descarta la fila** (devuelve `nullopt`, no lanza) si: nº columnas ≠ 19, HMAC inválido, **o campo numérico ilegible** [MEDIDO] — esto condiciona la regla de centinela (§5) y exige la verificación de §8.6.

**`flow_uid` (ADR-052):** `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`. Es la **identidad canónica del flujo** y la **PK del nodo `:NetworkFlow` en Kuzu** (§7 Eslabón 2). `community_id` NO es la PK: colisiona entre nodos distintos del despliegue multi-nodo (mismo flujo visto en dos nodos comparte `community_id` pero son observaciones distintas). `community_id` es propiedad indexada para el join cross-sensor **dentro** de un nodo (validado ADR-051). `flow_start_window` se deriva de cols 5-6; **no es columna hoy** → ver §10.7 / §8.5.

---

## 4. Tabla de mapeo por motor (resuelta)

Regla general: el adapter **obedece** AdapterSpec v1 y **produce** `correlation_v1` (motores de red) o `host_domain_v1` (motores de host). Cada motor rellena lo que su fichero de salida permite; lo que no puede derivar, va con **centinela** (§5), nunca se omite (rompería el conteo posicional).

| Motor | `source_sensor` | Fichero origen | `community_id` | `domain` | Join | Contrato |
|---|---|---|---|---|---|---|
| **aRGus** | `argus` | `NetworkSecurityEvent` (protobuf, ya enriquecido) | nativo | NETWORK | flujo↔flujo por `community_id` | `correlation_v1` |
| **Suricata** | `suricata` | `eve.json` | nativo (verificar `community-id-seed: 0`) | NETWORK | flujo↔flujo por `community_id` | `correlation_v1` |
| **Zeek** | `zeek` | `conn.log` | nativo (plugin `corelight/zeek-community-id`) | NETWORK | flujo↔flujo; staleness ≈5 min | `correlation_v1` |
| **Wazuh** | `wazuh` | `alerts.json` | **ausente** | HOST | **host↔flujo por IP** (en grafo) | **`host_domain_v1`** (separado) |
| **Andrés** | `andres` | desconocido | desconocido | ? | congelado | — |

**Mapeo aRGus (F1):** `native_event_id`←col 2; `event_time`←cols 5-6; `community_id`←col 4; `node_id`←col 3; `severity`←derivado de col 16 + col 12; `raw_payload` = la propia línea CSV de bronce. `source_sensor=argus`, `domain=NETWORK` constantes.

**[RATIFICADO] Wazuh: contrato `host_domain_v1` separado, NO se extiende `correlation_v1`.** (6 modelos a favor de separado, 2 a favor de v2/col-20; voto de Claude rompe hacia separado.) Argumento decisivo: `correlation_v1` tiene `community_id` como clave estructural y Wazuh **no tiene flujo**. Meter `host_key` como col 20 crea una fila donde `community_id` va vacío y `host_key` lleno — un mismo schema con **dos columnas de identidad mutuamente excluyentes**, que es el antipatrón. El coste de "dos pipelines" es real pero menor: los dos dominios **se unen en Kuzu de todos modos** (donde viven los joins), vía arista `(:Host)-[:INVOLVES_IP]->(:NetworkFlow)` por IP + ventana temporal. `host_domain_v1` tiene su propia zona bronce, su propia LZ y su propio sink a `:Host`.

**Topología de grafo (cae de la decisión Wazuh):** **un solo grafo, múltiples sinks de parquet.** `:NetworkFlow` alimentado por `correlation_v1`; `:Host` por `host_domain_v1`; relacionados por IP+ventana en Cypher. No hay grafos federados.

**La decisión sube aguas arriba:** `DEBT-CORRELATION-V1-HOSTKEY-001` (renombrado `DEBT-HOST-DOMAIN-CONTRACT-001`) se resuelve **antes del Eslabón 1**, porque la estructura del parquet plata depende de si hay o no `host_key`. Sube de P2 a **P1**.

---

## 5. Regla de centinela (decidida)

"Lo que no aparece" se escribe con centinela, **nunca se omite**:

- **Columnas string** (`source_sensor`, `protocol`, `final_classification`, `threat_category`, `authoritative_source`): `UNKNOWN`.
- **Columnas numéricas** (`src_port`/`dst_port` 9-10, `flow_start_sec`/`nano` 5-6, scores 14-16): **`-1`** — `UNKNOWN` en una numérica = "campo numérico ilegible" = fila descartada en silencio.
- **Temporales:** par **`(-1, -1)`** para `(flow_start_sec, flow_start_nano)`. El grafo interpreta el par como `null` temporal, **no** como `1969-12-31` (un `-1` en epoch-seconds es 1969; sin esta regla habría "flujos detectados" en plena Guerra Fría).
- El reader / grafo lee `-1` y `UNKNOWN` como **"no aplica"**, no como basura.

**Ya muerde en Suricata/Zeek:** `fast_detector_score` y `ml_detector_score` (cols 14-15) son scores de aRGus que esos motores no producen → centinela `-1` desde el segundo adapter.

**[RATIFICADO] `-1` para numéricas ausentes** (no `0`: `0` es score válido y puerto-0 ambiguo).

**[POR VERIFICAR — P0, §8.6] `parse_and_verify` debe aceptar `-1` en TODAS las columnas numéricas (5-6, 9-10, 14-16) sin descartar la fila.** Si el reader actual rechaza negativos en puertos o timestamps como "ilegibles", el segundo adapter que use centinela **rompe el circuito en silencio**. Verificar antes del Eslabón 1.

---

## 6. Estrategia de configuración e ingesta — fuente única de verdad

**Principio (invariante):** rutas (bronce/plata/oro) y, más adelante, configuración ZMQ por canal, viven en JSON. **Nunca hardcodeadas.** Hardcode = deuda doble: bloquea el refactor a ZMQ y clava a Vagrant.

### 6.1 Estado medido
- `correlation_writer` tiene su `base_dir` **hardcodeado** en `zmq_handler.cpp:154` → `/vagrant/logs/correlation/argus` [MEDIDO].
- El hermano `csv_writer` **sí** lee `base_dir` de JSON (`config_loader.cpp:455`) [MEDIDO] → patrón a copiar, mismo fichero.
- `correlation-engine` **no tiene JSON de config**: `bronze_path` por `--bronze` (argv) o `ARGUS_BRONZE_CSV` (env) [MEDIDO].
- `silver`/`gold` no existen en ningún sitio [MEDIDO] — se definen al construir la LZ.

### 6.2 Antídoto al desync: matching **estructural**, no por literales duplicados
- `bronze_root` definido **una vez** (p.ej. `/vagrant/logs/correlation`).
- Cada motor escribe en `bronze_root/<source_sensor>/<fichero>.csv`.
- El engine consume `bronze_root/*/...` derivando del mismo root. "Machear" pasa de "copio el literal y rezo" a "todos derivan de la misma raíz".
- **El JSON del Eslabón 0 lleva también el patrón de naming de ficheros**, para que el engine derive qué ficheros vigilar sin ambigüedad (si no, cerrar el hardcode reabre la duplicación que la propia regla prohíbe).

### 6.3 [RATIFICADO] Ingesta: un solo mecanismo, dos regímenes por config
El engine **vigila el directorio** con `inotify` + filtro **`IN_CLOSE_WRITE`** (solo notifica cuando el writer **cierra** el fichero → nunca se lee un fichero a medio escribir). Fallback a poll si `inotify` no disponible.

**Una sola ruta de watcher**, no dos. El régimen lo fija la configuración JSON, no el mecanismo:

- **Modo forense (por defecto):** ventana de rotación amplia (p.ej. 5 min) + `K` alto. "Mirar por una ventana del pasado". Parámetros poco agresivos.
- **Modo cuasi-tiempo-real:** ventana corta + `K` bajo (→1). Parámetros agresivos. Dependiente de CPU/RAM.

**Contrato de rotación del writer:**
- Un fichero CSV se cierra por **tiempo absoluto desde su apertura**, NO desde la última fila escrita. Si un sensor enmudece a las 23:58, su fichero se cierra igual al cumplir la ventana — si no, un sensor mudo deja un fichero abierto para siempre y el consolidador nunca lo ve (reabriría ROTATION-FOLLOW por la puerta de atrás).
- Escritura atómica: el writer escribe `.<fichero>.csv.tmp` y renombra al cerrar, o append atómico por línea.
- El consolidador AVRO agrupa los últimos `K` ficheros CSV (configurable) por zona.

**[RATIFICADO] SLO de staleness del oro (determinista, configurable):**
```
staleness_máx = ventana_rotación_csv + (K × ventana_rotación_csv)
```
Ej. forense (5 min, K=3) ≈ 20 min worst-case evento→grafo. Los tres parámetros temporales (ventana de join Kuzu, ventana de rotación CSV, batch `K`) son **deterministas y configurables vía contrato JSON**. El admin decide el régimen; se entrega uno por defecto (forense) y se documentan recomendaciones por hardware.

**Nota de correctitud:** la rotación por tiempo puede partir un flujo lento (Zeek ≈5 min) entre dos CSV, pero el join en Kuzu reúne las filas por `community_id` aunque vengan de ficheros distintos → **no rompe correctitud, solo añade latencia** (acotada por el SLO de arriba). El número seguro para cada régimen se infiere por **stress-test sobre el hardware objetivo** (procesar CSV de muchas líneas es de milisegundos; el factor limitante en cuasi-realtime es CPU/RAM). El stress-test **es** el experimento: se guarda como artefacto reproducible.

### 6.4 Fase producción (Ansible/Jinja2 — visión)
El generador Ansible/Jinja2 produce **todos** los contratos JSON desde plantilla única → coherencia cross-componente por **generación**, no por copia. En el mundo real, el generador conoce el hardware del target y aplica los **números seguros** inferidos por los stress-tests previos (mismo patrón que ya se usa para `vendor.key`→Vault y pubkey desde env var en Jenkins). Es el lugar donde se correlaciona la coherencia de rutas, endpoints ZMQ y parámetros de ingesta entre componentes distribuidos.

---

## 7. Plan de implementación por eslabones

> Secuencia estricta: cada eslabón verde antes del siguiente. Un motor (aRGus) E2E antes de añadir adapters reales.

**Tres caminos (no confundir):**
- **Camino 0** (ya existe): bronce CSV →`ifstream`→ Kuzu directo. Cierra el **circuito verde de un motor**. Mide *"¿fluye?"*.
- **Flujo A** (greenfield): bronce CSV → LZ → AVRO → Parquet **oro-ledger**. Mide *"¿el medallón preserva?"*.
- **Flujo B** (greenfield): Parquet oro → **conector nuevo** → Kuzu. Mide *"¿el medallón alimenta el grafo igual que el Camino 0?"*.

---

- **Eslabón 0 — Config + watcher + escritura atómica.** Sacar hardcode `zmq_handler.cpp:154` → `bronze_root` + patrón de naming en `ml_detector_config.json` (calcando `csv_writer`, §6.3). Implementar `inotify`/`IN_CLOSE_WRITE` en el engine + escritura atómica `.tmp`→rename en el writer + cierre por tiempo absoluto. Verificar writer/reader al mismo path (§8.2) y `-1` aceptado por `parse_and_verify` (§8.6). Aplicar regla `bronze_root + <source_sensor>` (no literal duplicado). *Resuelve `DEBT-CONFIG-BRONZE-HARDCODE-001` + `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (P0).*

- **Validación E2E (un motor) — vía Camino 0.** Circuito verde con aRGus extremo a extremo por el `ifstream` que ya existe, medido en Kuzu (no en bronce). Test automático §1. **Hito que desbloquea MITRE.** *No depende del medallón.*

- **Eslabón 1 — Landing Zone / medallón (Flujo A).** **[MEDIDO: greenfield].** El converter `scripts/parquet/` NO sirve (RAG-127/Ed25519, capa distinta — §8.1, `DEBT-DOCS-MEDALLION-DUALITY-001`); se construye **al lado**, reutilizando *patrones*, no código. Arquitectura **por componente**:
    - Zonas LZ independientes por motor (`LZ-argus`, `LZ-suricata`, `LZ-zeek`, `LZ-wazuh`), cada una con `{bronce, plata}`. Pipelines arrow/c++ paralelos: un motor lento no bloquea a otro (staleness por fuente, ADR-051/057).
    - Flujo por zona: `component-<fichero>.csv` → `.avro` → `.parquet` (plata).
    - **Oro: zona ÚNICA compartida** (el join es cross-component — §10.2).
    - **[RATIFICADO] El oro-ledger lleva como columnas de primera clase:** `node_id`, `community_id`, `flow_start_window` (las tres dimensiones por las que el experimento corta los datos — §10.7), + `flow_uid` derivado, + **HMAC por-fila heredado de bronce** (columna) — verificable contra clave. Además el Parquet consolidado se **firma como artefacto**. Razón: replay del grafo coherente en el tiempo ⟺ filas conservan su HMAC original. *`DEBT-GOLD-INTEGRITY-HMAC-001`, `DEBT-GOLD-NODE-DIMENSION-001`.*
    - **[CORRECCIÓN] Timestamp: la fusión `flow_start_sec`+`flow_start_nano` → `timestamp_utc_ns` va en la LZ (CSV→Arrow), NO en el writer C++.** El output del writer ES el contrato bronce sellado de 19 columnas que ya lee `parse_and_verify`; fundir ahí es breaking change + migración del histórico. El "origen" para Arrow es la LZ, una capa aguas abajo. El writer no toca su contrato.
    - Herencia de patrones de `scripts/parquet/`: centinela→null (`-1`/`UNKNOWN`→null Arrow tipado, precedente DAY 148); esqueleto `validate_roundtrip` **+ verificación HMAC** (el existente valida Ed25519); tipos `pa.dictionary(int32, utf8)` para columnas de baja cardinalidad.
    - Definir `silver_root`/`gold_root` en JSON.

- **Eslabón 2 — Conector PARQUET→Kuzu (Flujo B, greenfield).** **[MEDIDO: NO existe, ni prototipo.]** No es "re-apuntar"; es construcción nueva. `kuzu_graph_sink` hoy lee bronce-CSV directo (Camino 0); el conector Parquet es otro componente.
    - DDL: `:NetworkFlow` con **`flow_uid` como PRIMARY KEY** (NO `community_id`); `community_id`, `node_id`, `flow_start_window` como propiedades indexadas. Cada sensor cuelga su `:Detection`/`:Alert`. `:Host` (de `host_domain_v1`) por IP, arista aparte.
    - **[RATIFICADO] Criterio de cierre = test de equivalencia:** el grafo que produce el **Camino 0** y el que produce **Flujo A+B** deben ser **idénticos** para el mismo evento sintético de entrada (mismo `:NetworkFlow`, mismas propiedades). Sin equivalencia, "el medallón funciona" significa "arranca", no "produce la misma verdad". Es el principio de los golden vectors aplicado al circuito.
    - **Benchmark de ingesta** (1M filas, throughput Kuzu) como **gate de salida para declarar Eslabón 2 production-ready** — NO bloquea el circuito verde de un motor (que ya cerró por Camino 0). Si <10K eventos/s, evaluar buffer intermedio. *`DEBT-PARQUET-KUZU-CONNECTOR-001`.*

- **Eslabón 3 — Dashboard de consulta.** Cypher primero; NL-only admin después.

- **Eslabón 4 — Adapters de flujo.** Suricata, luego Zeek (caben en `correlation_v1`). Centinela `-1` en scores aRGus-only.

- **Eslabón 5 — Wazuh (host_domain_v1).** El contrato ya está diseñado y ratificado **antes del Eslabón 1** (§4); aquí se implementa el adapter + sink `:Host`. Andrés permanece congelado.

- **Eslabón 6 — Migración a transporte ZMQ.** Sustituir FS-drop por **PUSH/PULL** (handoff adapter→engine, garantía hasta HWM), reservando PUB/SUB para fan-out tolerante a pérdida (§3.1). El frame transporta bytes del CSV firmado (no protobuf). `DEBT-CIRCUIT-FS-DROP-001` deja de ser "migración trivial": es cambio de patrón de transporte con decisión de garantía de entrega.

---

## 8. Verificaciones pendientes antes de teclear (medir, no votar)

### 8.1 ¿Existe ya algún medallón? — **RESUELTO [MEDIDO]**
El grep devolvió **un solo pipeline real**: `scripts/parquet/`. Lee el CSV de 127 columnas del RAG (exige `len(cols) >= 127`) — **NO** lee `correlation_v1`. Parquet plano sin zonas, sin `community_id`, sin join. Firma Ed25519, no HMAC-SHA256. Es la capa RAG-127, **distinta** del circuito de correlación. → el medallón de correlación es **greenfield**; se reutilizan patrones, no código (`DEBT-DOCS-MEDALLION-DUALITY-001`).

**[POR VERIFICAR — no bloquea] §8.1b** ¿el converter RAG-127 está en uso o parado? `firewall.py` deja la pista: *"Revisar rag-security si en algún momento consume Parquet directamente"* — sugiere que el RAG aún consume CSV y el parquet espera consumidor. Relevante solo para no romper algo vivo.

### 8.2 ¿Writer y reader resuelven al mismo path?
```bash
grep -nE 'base_dir|bronze|ARGUS_BRONZE_CSV|--bronze' \
  ml-detector/src/config_loader.cpp ml-detector/src/zmq_handler.cpp \
  correlation-engine/src/main.cpp 2>/dev/null
grep -nE 'base_dir|correlation|bronze|csv_writer' ml-detector/config/ml_detector_config.json
```

### 8.3 ¿De qué lee Kuzu hoy?
Confirmado: `correlation-engine/src/main.cpp` → `ifstream(bronze_path)` → `parse_and_verify` → `flow_uid` → `IGraphSink`. Verificar que no hay segunda ruta de ingesta antes de tocar nada.

### 8.4 ¿Existe conector PARQUET→Kuzu? — **RESUELTO [MEDIDO, DAY 197]: NO, ni prototipo.**
Confirma que el Eslabón 2 es greenfield y que el circuito verde debe cerrar por Camino 0.

### 8.5 [P0 — mañana] ¿`node_id`/`community_id`/`flow_start_window` propagan al oro como columnas de primera clase?
`node_id` (col 3) y `community_id` (col 4) **ya son columnas en bronce** [MEDIDO §3.2]. Verificar que el converter Flujo A las arrastra a Arrow/Parquet **como columnas**, no solo como ingredientes de `flow_uid`. `flow_start_window` no es columna hoy: decidir si se materializa explícita en oro (recomendado: sí, pin de la función de ventana) o se re-deriva de cols 5-6. **Bloquea el schema del oro** (añadir columna a un ledger ya poblado = re-firmar + re-consolidar histórico).
```bash
grep -nE 'node_id|community_id|flow_start_window|flow_start_sec|flow_start_nano' \
  ml-detector/include/correlation_writer.hpp
```

### 8.6 [P0 — mañana] ¿`parse_and_verify` acepta `-1` en todas las columnas numéricas?
Verificar cols 5-6, 9-10, 14-16. Si rechaza negativos como "ilegibles", el segundo centinela rompe el circuito en silencio. Bloquea Eslabón 1.

---

## 9. Deudas a abrir (ticket antes de implementar)

| ID | Descripción | Prioridad |
|---|---|---|
| `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` | Rotación: writer cierra por tiempo absoluto, engine vigila directorio (`inotify`/`IN_CLOSE_WRITE`), cierre atómico. Sin esto el "circuito verde" muere a medianoche | **P0** (Eslabón 0) |
| `DEBT-CONFIG-BRONZE-HARDCODE-001` | `bronze base_dir` hardcodeado en `zmq_handler.cpp:154` (clava a Vagrant + bloquea ZMQ). Mover a JSON + patrón de naming | **P0** (Eslabón 0) |
| `DEBT-GOLD-NODE-DIMENSION-001` | `node_id`/`community_id`/`flow_start_window` como columnas de primera clase del oro (verificar propagación al converter Flujo A). Sin esto el dataset es ciego a la hipótesis del proyecto | **P0** (pre-Flujo A) |
| `DEBT-PARSE-VERIFY-SENTINEL-001` | Verificar `parse_and_verify` acepta `-1` en numéricas (5-6, 9-10, 14-16) | **P0** (pre-Eslabón 1) |
| `DEBT-HOST-DOMAIN-CONTRACT-001` | Wazuh: diseñar/ratificar contrato `host_domain_v1` separado (era `DEBT-CORRELATION-V1-HOSTKEY-001`). Sube aguas arriba: bloquea schema del medallón | **P1** (pre-Eslabón 1) |
| `DEBT-PARQUET-KUZU-CONNECTOR-001` | Conector PARQUET→Kuzu (Flujo B) no existe, ni prototipo. Greenfield + test de equivalencia Camino-0 ≡ A+B + benchmark | P1 (Eslabón 2) |
| `DEBT-GOLD-INTEGRITY-HMAC-001` | HMAC por-fila heredado como columna del oro + firma del Parquet consolidado (replay coherente en el tiempo) | P1 (Flujo A) |
| `DEBT-ZMQ-DELIVERY-GUARANTEE-001` | Handoff adapter→engine: PUSH/PULL (no PUB/SUB) para at-least-once; PUB/SUB solo fan-out tolerante a pérdida. Enmienda AdapterSpec §7.1 | P1 (Eslabón 6) |
| `DEBT-CIRCUIT-FS-DROP-001` | Handoff por fichero (`ifstream`) es interino; producción = ZMQ §7.1 enmendado | P1 (post-circuito verde) |
| `DEBT-ADAPTERSPEC-ENVELOPE-001` | Enmienda AdapterSpec v1 §3 → v1.1: envelope protobuf inexistente; transporte = bytes CSV firmados; PUSH/PULL para handoff | P2 (doc, pasa por Consejo) |
| `DEBT-DOCS-MEDALLION-DUALITY-001` | Dos pipelines PARQUET: RAG-127/Ed25519 (análisis) vs correlación-19/HMAC (grafo). Documentar la dualidad con warnings | P2 (doc) |
| `DEBT-JOIN-CONFIDENCE-001` | Ventana temporal de join adaptativa (GLM5-Turbo): si adapta, los parámetros deben grabarse en el ledger por época para que "Kuzu reconstruible" sea verdad (§10.8). Hoy: parámetros deterministas en JSON | P2 (pre-join adaptativo) |
| Higiene | `firewall-acl-agent/backups/day23-*` y `.backup` ensucian árbol y greps → `git rm --cached` / `.gitignore` | P3 |

---

## 10. Decisiones del Consejo (cerradas DAY 197)

**10.1 A vs B (formato de salida).** **[RATIFICADO] B** — cada motor de red escribe `correlation_v1` a bronce (bronce PRESERVA, una fila por motor por `source_sensor`); correlación diferida a Kuzu (gold DECIDE). No hay envelope protobuf. El frame ZMQ (Eslabón 6) transporta bytes del CSV firmado.

**10.2 Forma del oro.** **[RATIFICADO 9/9] Oro-como-ledger + join en Kuzu.** Reformulación: el ledger es el **único** oro; Kuzu y cualquier wide-table son proyecciones co-iguales reconstruibles. La matriz de features para reentrenar ML (ADR-040) es una **proyección tabular** del ledger, no oro — por eso no hay caso para oro-como-join. Razones: (1) Via Appia — oro = ledger inmutable durable, Kuzu = proyección reconstruible y **verificable** (HMAC heredado); (2) paper reproducible (ADR-046 §3.11); (3) unir-por-clave-en-relaciones es para lo que Kuzu existe. El join se materializa **en write-time** (ingesta), no en query-time. Wazuh/Andrés viven en parquet aparte, conectados por IP en el grafo.

**10.3 Centinela numérico.** **[RATIFICADO] `-1`** en CSV → `null` Arrow tipado; par `(-1,-1)` para temporales. Verificar `parse_and_verify` (§8.6).

**10.4 Rotación/follow.** **[RATIFICADO]** Engine vigila directorio con `inotify`/`IN_CLOSE_WRITE` (una sola ruta); régimen forense vs cuasi-realtime por config JSON; cierre por tiempo absoluto desde apertura; SLO de staleness determinista (§6.3). ROTATION-FOLLOW → **P0**.

**10.5 Wazuh.** **[RATIFICADO]** Contrato `host_domain_v1` separado; un solo grafo con múltiples sinks; decisión sube antes del Eslabón 1 (§4).

**10.6 Andrés.** **[RATIFICADO] Congelado con razón escrita:** repo entregado **sin código**. No se toman decisiones arquitectónicas contra una dependencia externa inestable (`medir, no votar`: no se mide contra un fichero que no existe; podría cambiar a diario). Se reabre cuando haya código estable, analizando entonces qué se necesita. Distinto de "borrar": queda constancia documentada del *porqué* para que nadie lo reabra sin saber que ya se decidió.

**10.7 [NUEVA — coherencia con el norte de investigación] Dimensión por nodo en el oro.** `node_id`, `community_id`, `flow_start_window` como columnas de primera clase del oro-ledger, no solo ingredientes de `flow_uid`. Sin ellas el dataset no puede estratificar por nodo y la hipótesis ("¿contribuyen nodos distribuidos a mejores datasets?") es inmedible (el hash no se invierte). `node_id`/`community_id` ya son columnas 3-4 en bronce [MEDIDO]; verificar propagación al oro (§8.5).

**10.8 [ABIERTA — diferida con ticket] Parámetros de join en el ledger.** Si la ventana de join se vuelve **adaptativa** (`DEBT-JOIN-CONFIDENCE-001`), "Kuzu reconstruible desde el ledger" solo es verdad si los parámetros de join por época son deterministas **o** están grabados en el ledger. Hoy son deterministas y configurables en JSON (§6.3) → la propiedad se mantiene. Decisión para el DDL: grabar el contexto-de-decisión-de-join por época en el schema del ledger, o diferir hasta que el join adaptativo exista. *No dejar implícito.*

**10.9 [NUEVA] `flow_uid` PK, no `community_id`.** Coherencia ADR-052. `community_id` colisiona multi-nodo; es propiedad indexada e ingrediente de la PK, no la PK. Corrige los DDL propuestos por el Consejo.

---

## Apéndice A — Evidencia medida

- `network_security.proto`: único envelope-candidato = `NetworkSecurityEvent` (L569); **no existe** `SecurityEvent`.
- `correlation_writer.{hpp,cpp}`: `write_record(NetworkSecurityEvent)`; `get_file_path = base_dir + "/" + date + ".csv"`; `base_dir` hardcodeado `"/vagrant/logs/correlation/argus"` en `zmq_handler.cpp:154`; rotación diaria con `create_directories`.
- `correlation_v1`: 19 columnas; `node_id`=col 3, `community_id`=col 4 (**de primera clase en bronce**); HMAC cols 0-17 en col 18.
- `csv_writer`: `base_dir` desde JSON (`config_loader.cpp:455`).
- `correlation-engine/src/main.cpp`: `--bronze`/`ARGUS_BRONZE_CSV`; `ifstream(bronze_path)`; `parse_and_verify` → `flow_uid` → `IGraphSink`; tiene `kuzu_graph_sink`, `cypher_builder`, `correlation_reader`. **Sin AVRO/PARQUET/Arrow/silver/gold** en lo medido.
- **Conector PARQUET→Kuzu: no existe, ni prototipo [MEDIDO DAY 197].**
- `firewall-acl-agent/zmq_subscriber.hpp`: consumidor real del PUB del ml-detector → `batch_processor` → ipset.
- `scripts/parquet/`: pipeline RAG-127→PARQUET. Lee CSV 127 cols + firewall; parquet plano; firma Ed25519; `SENTINEL=-9999.0`→null; `pa.dictionary`; sin `community_id`. `DEBT-PARQUET-TIMESTAMP-NS-001` documentada (`x1_000_000`). Capa RAG, distinta del circuito de correlación.
- `AdapterSpec v1`: documento normativo en `docs/engineering_decisions/`.

---

*EMECAS++ aplica antes de cualquier merge. Este plan es documentación; el commit de documentación no pasa el gate de build, pero los commits de implementación de cada eslabón sí. Subir como commit de apertura de `day196/circuit-adapters-zmq` (cerrar antes `day194/ransomware-provenance-desync` si sigue abierta).*