# PLAN — Circuito completo aguas abajo (DAY 196 → implementación)

| Campo | Valor |
|---|---|
| **Documento** | Plan de implementación — circuito completo (estado: borrador para Consejo) |
| **Fecha** | 2026-06-26 (DAY 196) |
| **Autores** | Alonso Isidoro Roman + Claude (Anthropic) |
| **Referencia** | ADR-046 v4, ADR-051, ADR-057, AdapterSpec v1, contrato `correlation_v1` |
| **Rama propuesta** | `day196/circuit-adapters-zmq` |
| **Invariante** | medir, no votar · JSON is the law · bronce PRESERVA, gold DECIDE · Via Appia |

> **Convención de estado.** Cada afirmación lleva marca: **[MEDIDO]** (verificado contra fichero esta sesión, con evidencia en Apéndice A), **[POR VERIFICAR]** (requiere comando antes de tocar código — §8), **[DECISIÓN]** (elección de diseño que el Consejo debe ratificar — §10).

---

## 0. Propósito

Completar el **circuito completo aguas abajo** —adapters → zona bronce → Landing Zone (medallón CSV→AVRO→PARQUET) → grafo Kuzu → dashboard de consulta— asumiendo que la inferencia ML está rota o incompleta. El circuito es el **instrumento de medición** que permitirá, *después*, decidir si una mejora de modelo es real antes de confiar en los plugins de ensemble, y sobre el que se construirá el mecanismo MITRE. No se reentrena nada antes de tener el microscopio calibrado: optimizar sin medir es optimizar a ciegas (decisión de DAY 195).

---

## 1. Tesis y criterio de hecho

**Definición de "circuito verde" (E2E, un solo motor):** una fila de aRGus entra por el sniffer, sale enriquecida del `ml-detector`, aterriza en bronce como `correlation_v1` (CSV+HMAC), la LZ la convierte a AVRO→PARQUET hasta gold, Kuzu materializa `:NetworkFlow + :Alert`, y el dashboard la recupera por consulta. Un motor, extremo a extremo. **Eso** es el hito que desbloquea el MITRE.

Orden de trabajo (DAY 195/196): **chapu de FS primero** (que el circuito fluya), verificar flujo aguas abajo, y **solo entonces** migrar a ZMQ PUB/SUB en los adapters. "Medir que fluye" antes de "hacerlo bien".

---

## 2. Topología de componentes y canales

```
[sniffer] --ZMQ--> [ml-detector] --ZMQ--> [firewall-acl-agent --> ipset]   (existente, producción)
                        |
                        | correlation_writer (escribe correlation_v1 a bronce)
                        v
                   [BRONCE *.csv]
                        |
              (HOY: FS-drop / ifstream  ── chapu)
              (PROD: ZMQ PUB/SUB §7.1)
                        v
                [correlation-engine] --> [Kuzu graph]
                        ^
   adapter-suricata ----+
   adapter-zeek --------+
   adapter-wazuh -------+   (host-domain, arista distinta)
   adapter-andres ------+   (stub, contrato negativo)
```

| Canal | Estado | Nota |
|---|---|---|
| sniffer → ml-detector | **[MEDIDO]** existe | ZMQ (`main_libpcap.cpp` connect) |
| ml-detector → firewall-acl-agent | **[MEDIDO]** existe | ZMQ PUB/SUB → batch_processor → ipset |
| ml-detector → bronce | **[MEDIDO]** existe | `correlation_writer.write_record()` |
| bronce → correlation-engine | **[MEDIDO]** existe (chapu) | `ifstream(bronze_path)`, `--bronze`/`ARGUS_BRONZE_CSV` |
| correlation-engine → Kuzu | **[MEDIDO]** existe | `kuzu_graph_sink`, lee bronce CSV **directo** |
| **adapter-argus** | **[MEDIDO]** NO-OP | su función ya la cumple `correlation_writer`; no es proceso nuevo |
| adapter-{suricata,zeek,wazuh,andres} | **[MEDIDO]** NO existen | greenfield |
| LZ medallón (CSV→AVRO→PARQUET) | **[POR VERIFICAR]** no aparece en lo medido | construcción nueva — §8.1 |
| dashboard de consulta | **[POR VERIFICAR]** no medido | greenfield probable |

**Punto crítico (§2):** el `adapter-argus` que aparece en la topología **no es un binario nuevo**. `correlation_writer`, dentro de `ml-detector`, ya es el productor de `correlation_v1` para aRGus. El día de la migración a ZMQ, el "adapter-argus" será el socket PUB que hoy es el `ofstream` — co-ubicado en el dominio del ml-detector, **pero no indistinto de la lógica ML**: el adapter existe para que el engine sea agnóstico al motor de origen; fundirlo con el detector pierde esa propiedad. Co-ubicado sí, indistinto no.

---

## 3. Contratos — separación estricta

Dos contratos en dos capas. **No** son el mismo objeto bajo nombres distintos (esta confusión —`AspectV1`/`AdapterSpec`/`correlation_v1`— fue el origen del desync DAY 194; queda cerrada aquí).

### 3.1 AdapterSpec v1 — contrato de **comportamiento** de ingesta
Normativo (DAY 169, ADR-046 v4 §3.10). Define **cómo se comporta** todo adapter, sea cual sea su payload:
- **at-least-once** (§2): ningún evento se pierde en silencio.
- **dedup idempotente** por `(source_engine, native_event_id)` (§2). Exactly-once explícitamente fuera de alcance.
- `native_event_id` **determinista** en tier golden (§4); ID nativo o hash estable en tier vivo.
- **checkpoint monotónico** persistente entre reinicios (§6).
- **transporte interno SIEMPRE ZeroMQ PUB/SUB** con regla slow-joiner: PUB `bind()` antes que SUB `connect()` (§7.1).

**[DECISIÓN] Enmienda AdapterSpec v1 → v1.1 (pasa por Consejo).** El §3 actual manda emitir un envelope protobuf `SecurityEvent` con campos (`source_engine`, `native_event_id`, `domain`, `severity`, `host_key`, `raw_payload`…) que **no existen en `network_security.proto`** **[MEDIDO]** — el único mensaje es `NetworkSecurityEvent` (línea 569), con otros nombres y anidado. El envelope protobuf era vapor de documento. La salida real al cable es **`correlation_v1` CSV+HMAC, nunca protobuf**. La enmienda reescribe §3 ("el adapter emite filas `correlation_v1`; los §§2/4/6/7.1 se conservan intactos") y abre `DEBT-ADAPTERSPEC-ENVELOPE-001`.

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

El lector (`correlation_reader.parse_and_verify`) **descarta la fila** (devuelve `nullopt`, no lanza) si: nº columnas ≠ 19, HMAC inválido, **o campo numérico ilegible**. **[MEDIDO]** — esto condiciona la regla de centinela (§5).

---

## 4. Tabla de mapeo por motor (resuelta — DAY 169/junio)

Regla general: el adapter **obedece** AdapterSpec v1 y **produce** `correlation_v1`. Cada motor rellena lo que su fichero de salida permite; lo que no puede derivar, va con **centinela** (§5), nunca se omite (rompería el conteo posicional de 19 columnas).

Los tres campos de **federación cross-engine** —`source_sensor`, y la lógica de join— son la clave del diseño:

| Motor | `source_sensor` | Fichero origen | `community_id` | `domain` | Join |
|---|---|---|---|---|---|
| **aRGus** | `argus` | `NetworkSecurityEvent` (protobuf, ya enriquecido) | nativo (`NetworkFeatures.community_id`) | NETWORK | flujo↔flujo por community_id |
| **Suricata** | `suricata` | `eve.json` | nativo (verificar `community-id-seed: 0`) | NETWORK | flujo↔flujo por community_id |
| **Zeek** | `zeek` | `conn.log` | nativo (plugin `corelight/zeek-community-id`) | NETWORK | flujo↔flujo por community_id; staleness ≈5 min (cierre de flujo) |
| **Wazuh** | `wazuh` | `alerts.json` | **ausente** | HOST | **host↔flujo por IP** (cols 7-8), NO por community_id |
| **Andrés** | `andres` | desconocido (stub) | desconocido | ? | contrato negativo: 5 incógnitas pendientes |

**Mapeo aRGus (F1), rellenando contra bronce:** `native_event_id`←col 2; `event_time`←cols 5-6; `community_id`←col 4; `severity`←derivado de col 16 + col 12; `raw_payload` = la propia línea CSV de bronce; `node_id` (col 3) → metadata. `source_sensor`=`argus`, `domain`=NETWORK constantes; `host_key` n/a (ancla por community_id).

**[DECISIÓN] Wazuh es categoría aparte.** `host_key` **NO es** `community_id`: el primero identifica un host, el segundo un flujo (SHA1 sobre 5-tupla, simétrico — por eso aRGus/Suricata/Zeek que ven el mismo flujo coinciden). Aliasar `host_key`→`community_id` fabricaría un id de flujo falso que no une nada y envenena el espacio donde los motores de flujo sí se unen. El join de Wazuh es `host_key` contra `src_ip`/`dst_ip` (cols 7-8): otra arista del grafo (`:Host —[involucrado_en]→ :NetworkFlow` por IP compartida + ventana temporal). El join community_id↔community_id está **validado** (ADR-051, parity gate `agree=788–1029`).

**Muro estructural Wazuh (diferido, no resolver en el primer eslabón):** `correlation_v1` no tiene columna `host_key`, y el writer omite `write_record` si `community_id == ""` **[MEDIDO]**. Por tanto un evento Wazuh host-domain **hoy nunca se escribe**. Requiere decisión de esquema → `DEBT-CORRELATION-V1-HOSTKEY-001` (extender `correlation_v1` con `host_key`, o contrato host-domain aparte). aRGus/Suricata/Zeek caben tal cual; Wazuh no, y está bien que no.

---

## 5. Regla de centinela (decidida)

"Lo que no aparece" se escribe con centinela, **nunca se omite** (omitir rompe el conteo posicional y `parse_and_verify` descarta la fila entera):

- **Columnas string** (`source_sensor`, `protocol`, `final_classification`, `threat_category`, `authoritative_source`): `UNKNOWN`.
- **Columnas numéricas** (`src_port`/`dst_port` 9-10, `flow_start_sec`/`nano` 5-6, scores 14-16): **`-1`** — `UNKNOWN` en una numérica = "campo numérico ilegible" = fila descartada en silencio.
- El reader / grafo debe interpretar `-1` y `UNKNOWN` como **"no aplica"**, no como basura.

**Ya muerde en Suricata/Zeek, no es teórico:** `fast_detector_score` y `ml_detector_score` (cols 14-15) son scores de aRGus que esos motores no producen → centinela `-1` desde el segundo adapter.

**[DECISIÓN para Consejo]** confirmar `-1` vs `0` para numéricas ausentes (preferencia: `-1`, porque `0` es un score válido y `0` es un puerto-no-puerto ambiguo).

---

## 6. Estrategia de configuración — fuente única de verdad

**Principio (invariante):** las rutas (bronce/plata/oro) y, más adelante, la configuración ZMQ por canal, viven en JSON. **Nunca hardcodeadas.** Hardcode = deuda doble: bloquea el refactor a ZMQ y clava a Vagrant (`/vagrant/...` no existe en producción real).

### 6.1 Estado medido
- `correlation_writer` tiene su `base_dir` **hardcodeado** en `zmq_handler.cpp:154` → `"/vagrant/logs/correlation/argus"`. **[MEDIDO]**
- El hermano `csv_writer` **sí** lee `base_dir` de JSON (`config_loader.cpp:455`, `get_required` sección `csv_writer`). **[MEDIDO]** → el patrón a copiar ya existe en el mismo fichero.
- `correlation-engine` **no tiene JSON de config**: `bronze_path` por `--bronze` (argv) o `ARGUS_BRONZE_CSV` (env). **[MEDIDO]**
- `silver`/`gold` no existen en ningún sitio **[MEDIDO]** — se definirán al construir la LZ.

### 6.2 Antídoto al desync: matching **estructural**, no por literales duplicados
N+1 JSON con paths literales que "deben coincidir" y nada que lo obligue = desync DAY 194 reencarnado. El antídoto es **un único `bronze_root`** y derivación por convención:

- `bronze_root` definido **una vez** (p.ej. `/vagrant/logs/correlation`).
- Cada motor escribe en `bronze_root/<source_sensor>/<date>.csv` (el sufijo por motor ya está en el path actual: `.../correlation/argus`).
- El engine consume `bronze_root/*/<date>.csv` derivando del mismo root. "Machear" pasa de "copio el literal y rezo" a "todos derivan de la misma raíz".

### 6.3 Fase chapu (ahora, mínimo cambio)
1. Sacar el hardcode de `zmq_handler.cpp:154` a `ml_detector_config.json` (clave `bronze_root` o `correlation_writer.base_dir`), leído en `config_loader.cpp` **calcando** el patrón `csv_writer` (3 líneas: clave JSON + `get_required` + uso).
2. El engine **no necesita JSON nuevo todavía**: el script de arranque (provisioning Vagrant) lee ese mismo JSON y pasa `--bronze {bronze_root}/argus/{hoy}.csv`. Fuente de verdad = un único JSON; matching **garantizado por derivación**.

### 6.4 Fase producción (Ansible/Jinja2 — visión)
El generador Ansible/Jinja2 produce **todos** los contratos JSON desde plantilla única → coherencia cross-componente garantizada por **generación**, no por copia manual. Cada componente expone en su contrato JSON sus rutas y (más adelante, en el mismo JSON) su parte ZMQ del canal que le toca. El generador es el lugar donde se correlaciona la coherencia de los rutas y endpoints entre componentes distribuidos. La maquinaria ZMQ ya existe y está probada (sniffer→ml-detector→firewall); la migración FS-drop→ZMQ en los adapters es patrón conocido, no investigación.

---

## 7. Plan de implementación por eslabones

> Secuencia estricta: cada eslabón se valida verde antes del siguiente. Un motor (aRGus) E2E antes de añadir adapters reales.

- **Eslabón 0 — Config bronce a JSON.** Sacar hardcode `zmq_handler.cpp:154` → `bronze_root` en `ml_detector_config.json`; arranque del engine deriva `--bronze` del mismo JSON. Verificar que writer y reader **resuelven al mismo path** (§8.2). *Adapter-argus = no-op.*
- **Eslabón 1 — Landing Zone / medallón.** **[MEDIDO: medallón de correlación = greenfield].** El converter `scripts/parquet/` existente NO sirve a este circuito (es RAG-127/Ed25519, capa distinta — ver §8.1 y `DEBT-DOCS-MEDALLION-DUALITY-001`); se construye **al lado**, reutilizando sus *patrones*, no su código. Arquitectura **por componente**:
    - **Zonas LZ independientes por motor** (`LZ-argus`, `LZ-suricata`, `LZ-zeek`, `LZ-wazuh`), cada una con su `{bronce, plata}`. Pipelines arrow/c++ paralelos: un motor lento (Zeek, cierre de flujo ≈5 min) no bloquea el avance de otro. Coherente con *staleness por fuente, no global* (ADR-051 / ADR-057).
    - **Flujo por zona:** `component-date.csv` (bronce-CSV `correlation_v1`) → `component-date.avro` (bronce-AVRO) → `component-date.parquet` (plata-PARQUET).
    - **Oro: zona ÚNICA compartida, NO por componente** (el join es cross-component por definición — ver §10.2). Forma del oro pendiente de decisión de Consejo (oro-como-join arrow vs oro-como-ledger + join en Kuzu).
    - **Herencia de `scripts/parquet/` (patrones, no código):** (a) centinela→null: `-1`/`UNKNOWN` en CSV → `null` Arrow tipado (precedente `SENTINEL=-9999.0`→`None`, DAY 148); (b) esqueleto `validate_roundtrip` **+ verificación HMAC** (el existente valida Ed25519, otra cadena); (c) tipos `pa.dictionary(int32, utf8)` para `source_sensor`/`protocol`/`final_classification`/`threat_category` (baja cardinalidad).
    - **Lección timestamp (de `DEBT-PARQUET-TIMESTAMP-NS-001`):** funde `flow_start_sec`+`flow_start_nano` (cols 5-6) a `timestamp_utc_ns` **en el origen (writer C++)**, no con un workaround `x1_000_000` en el converter. Un arreglo de unidades en la capa de conversión es deuda heredada.
    - Definir `silver_root`/`gold_root` en JSON (no existen aún, **[MEDIDO]**).
- **Eslabón 2 — Conector Kuzu sobre oro.** `kuzu_graph_sink` ya existe; hoy lee bronce-CSV **directo** (`ifstream`). Re-apuntar a oro-PARQUET según decisión §10.2. Si oro-como-ledger: community_id se materializa como `:NetworkFlow` compartido y cada sensor cuelga su `:Detection` (el join **es** el grafo); Wazuh entra como `:Host` por IP, arista aparte.
- **Eslabón 3 — Dashboard de consulta.** Cypher primero; NL-only admin después.
- **Validación E2E (un motor).** Circuito verde con aRGus extremo a extremo. **Hito que desbloquea MITRE.**
- **Eslabón 4 — Adapters de flujo.** Suricata, luego Zeek (caben en `correlation_v1` tal cual). Centinela `-1` en scores aRGus-only.
- **Eslabón 5 — Wazuh.** Resolver `DEBT-CORRELATION-V1-HOSTKEY-001` (decisión de esquema) antes de implementar. Andrés queda stub (contrato negativo).
- **Eslabón 6 — Migración a ZMQ PUB/SUB.** Sustituir FS-drop por el contrato §7.1 en todos los adapters (`DEBT-CIRCUIT-FS-DROP-001`). Patrón conocido.

---

## 8. Verificaciones pendientes antes de teclear (medir, no votar)

### 8.1 ¿Existe ya algún medallón? — **RESUELTO [MEDIDO]**
El grep `avro|parquet|arrow|iceberg|silver|gold|landing.?zone` devolvió **un solo pipeline real**: `scripts/parquet/` (`generate_parquet.py` + `schemas/{ml_detector,firewall}.py` + `validate_roundtrip.py`). Caracterizado:
- Lee el **CSV de 127 columnas del RAG** (`/vagrant/logs/ml-detector/events`, exige `len(cols) >= 127`) y el CSV de firewall — **NO** lee `correlation_v1` bronce.
- Dos tablas (`ml_detector`, `firewall`), **parquet plano sin zonas** (sin bronce/plata/oro en el código), **sin `community_id`**, **sin join**. Firma **Ed25519**, no el HMAC-SHA256 de `correlation_v1`.
- Es la capa de serialización del **RAG-127**, ratificada DAY 148, marcada "secreto industrial". **Capa distinta del circuito de correlación.**

**Conclusión:** el medallón de correlación (`correlation_v1`→AVRO→PARQUET→Kuzu, join por community_id) es **greenfield**. Se reutilizan patrones (centinela→null, roundtrip, tipos dictionary, lección timestamp-ns), no código. → `DEBT-DOCS-MEDALLION-DUALITY-001`.

**[POR VERIFICAR]** ¿el converter RAG-127 está en uso en producción, o es infraestructura preparatoria parada? El propio `firewall.py` deja la pista: *"Revisar rag-security si en algún momento consume Parquet directamente"* — sugiere que el RAG aún consume CSV y el parquet espera consumidor. Targets `make parquet-convert`/`make test-parquet` existen, pero un target no prueba ejecución en el flujo real. No bloquea el Eslabón 1; relevante solo para no romper algo vivo.

### 8.2 ¿Writer y reader resuelven al mismo path?
```bash
# clave real que lee el writer + cómo arranca hoy el engine
grep -nE 'base_dir|bronze|ARGUS_BRONZE_CSV|--bronze' \
  ml-detector/src/config_loader.cpp ml-detector/src/zmq_handler.cpp \
  correlation-engine/src/main.cpp 2>/dev/null
# qué dice el JSON viejo del ml-detector
grep -nE 'base_dir|correlation|bronze|csv_writer' ml-detector/config/ml_detector_config.json
```
Si el writer rota a fichero **datado** y el engine sigue **un solo** fichero → bug de medianoche (§9, `ROTATION-FOLLOW`).

### 8.3 ¿De qué lee Kuzu hoy?
Confirmado parcialmente: `correlation-engine/src/main.cpp` → `ifstream(bronze_path)` → `parse_and_verify` → `flow_uid` → `IGraphSink`. Verificar que no hay una segunda ruta de ingesta antes de re-apuntar al medallón.

---

## 9. Deudas a abrir (ticket antes de implementar)

| ID | Descripción | Prioridad |
|---|---|---|
| `DEBT-CIRCUIT-FS-DROP-001` | Handoff adapter→engine por fichero (`ifstream`) es interino; contrato de producción es ZMQ PUB/SUB §7.1 | P1 (post-circuito verde) |
| `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` | Writer rota a `<date>.csv` diario; engine sigue un solo fichero → corte mudo a medianoche. Decidir: engine vigila **directorio** vs lanzador recalcula datado | P1 |
| `DEBT-ADAPTERSPEC-ENVELOPE-001` | Enmienda AdapterSpec v1 §3 → v1.1: envelope protobuf `SecurityEvent` inexistente; salida real = `correlation_v1` CSV+HMAC | P2 (doc, pasa por Consejo) |
| `DEBT-CORRELATION-V1-HOSTKEY-001` | Wazuh host-domain no cabe en `correlation_v1` (sin `host_key`, regla `community_id==""` lo descarta). Decisión de esquema | P2 (pre-Wazuh) |
| `DEBT-CONFIG-BRONZE-HARDCODE-001` | `bronze base_dir` hardcodeado en `zmq_handler.cpp:154` (clava a Vagrant + bloquea ZMQ). Mover a JSON | P1 (Eslabón 0) |
| `DEBT-DOCS-MEDALLION-DUALITY-001` | Existen DOS pipelines PARQUET: RAG-127/Ed25519 (`scripts/parquet/`, capa análisis) vs correlación-19/HMAC (medallón nuevo, capa grafo). Documentar la dualidad para que nadie los confunda | P2 (doc) |
| Higiene | `firewall-acl-agent/backups/day23-*` y `.backup` ensucian árbol y greps → `git rm --cached` / `.gitignore` | P3 |

---

## 10. Preguntas abiertas para el Consejo

1. **A vs B (formato de salida del adapter).** Decidido en sesión: **B** — cada motor escribe `correlation_v1` a bronce (bronce PRESERVA, una fila por motor distinguida por `source_sensor`), correlación diferida a gold (gold DECIDE). No hay envelope protobuf intermedio (no existe). **Ratificar.**
2. **Forma del oro: join en arrow vs join en Kuzu.** El medallón de correlación es greenfield (§8.1), así que la pregunta no es "¿sustituye o se intercala?" sino **dónde vive el join cross-component**:
    - **Oro-como-join (arrow funde):** un parquet único ya correlacionado por community_id (aRGus+Suri+Zeek); Kuzu ingiere un fichero + deltas. El oro *contiene* el join.
    - **Oro-como-ledger (Kuzu une):** oro = parquet curado, una observación por fila, todas portando community_id, **sin fundir**; Kuzu hace el join al materializar el grafo. El oro *cura*, no funde.
    - **Lean (a ratificar):** oro-como-ledger + join en Kuzu. Razones: (1) Via Appia — oro es el ledger inmutable durable, Kuzu es proyección reconstruible; (2) el paper exige dataset materializado reproducible (ADR-046 §3.11) — oro es ese artefacto; (3) unir-por-clave-en-relaciones es para lo que Kuzu existe — community_id quiere ser `:NetworkFlow` compartido con aristas, no una columna de un wide-table aplanado; pre-fundir en arrow obliga a unir dos veces. Oro-como-join se reserva solo si un consumidor **no-Kuzu** necesita el wide-table (analítica batch / retro-hunt fuera del grafo).
    - En ambas variantes: Wazuh/Andrés viven en parquet aparte, sin tocar, conectados por IP no por community_id.
3. **Centinela numérico — [precedente, casi cerrado].** `-1`/`UNKNOWN` en CSV bronce → `null` tipado en parquet. El proyecto ya decidió esta semántica (DAY 148: `SENTINEL=-9999.0`→`None`). No es `-1` *vs* `null`: es `-1` en CSV (texto, sin null) → `null` Arrow (tipado). Confirmar el valor centinela CSV (`-1` propuesto; `0` ambiguo para score/puerto) y que reader C++ y grafo lo lean como "no aplica".
4. **Rotación/follow.** Engine vigila directorio (sigue el fichero más nuevo) vs lanzador recalcula datado.
5. **Wazuh.** Extender `correlation_v1` con `host_key` (rompe el sellado de 19 columnas → ¿`correlation_v2`?) vs contrato host-domain separado con su propio sink.
6. **Andrés.** Mantener stub con contrato negativo (5 incógnitas: naturaleza, transporte, presencia de community_id, clave de join, staleness SLO) hasta que haya repo/datos.

---

## Apéndice A — Evidencia medida esta sesión

- `network_security.proto`: único mensaje envelope-candidato = `NetworkSecurityEvent` (L569); **no existe** `SecurityEvent`.
- `correlation_writer.{hpp,cpp}`: `write_record(NetworkSecurityEvent)`; `get_file_path = base_dir + "/" + date + ".csv"`; `base_dir` hardcodeado `"/vagrant/logs/correlation/argus"` en `zmq_handler.cpp:154`; rotación diaria con `create_directories`.
- `csv_writer`: `base_dir` desde JSON (`config_loader.cpp:455`).
- `correlation-engine/src/main.cpp`: `--bronze`/`ARGUS_BRONZE_CSV`; `ifstream(bronze_path)`; pipeline `parse_and_verify → flow_uid → IGraphSink`; tiene `kuzu_graph_sink`, `cypher_builder`, `correlation_reader`. Sin AVRO/PARQUET/Arrow/silver/gold en lo medido.
- `firewall-acl-agent/zmq_subscriber.hpp`: consumidor real del PUB del ml-detector → `batch_processor` → ipset.
- `scripts/parquet/`: pipeline RAG-127→PARQUET. `generate_parquet.py` lee `/vagrant/logs/ml-detector/events` (CSV 127 cols) y `firewall_blocks.csv`; escribe `OUT_DIR/{ml-detector,firewall}/*.parquet` plano. `schemas/{ml_detector,firewall}.py`: Arrow, firma Ed25519, `SENTINEL=-9999.0`→null, `pa.dictionary`, sin `community_id`. `validate_roundtrip.py`: `schema.equals` + rango timestamp. `DEBT-PARQUET-TIMESTAMP-NS-001` documentada en `firewall.py` (ms→ns workaround `x1_000_000`). Capa RAG, distinta del circuito de correlación.
- AdapterSpec v1: documento normativo en `docs/engineering_decisions/`; §7.1 transporte interno ZMQ PUB/SUB.

---

*EMECAS++ aplica antes de cualquier merge. Este plan es documentación; el commit de documentación no pasa el gate de build, pero los commits de implementación de cada eslabón sí.*