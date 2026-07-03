# DISEÑO — Eslabón 1, Flujo A (bronce → AVRO → Parquet oro)

- **Estado:** BORRADOR — para ratificación del Consejo de Sabios antes de implementar
- **Fecha:** DAY 205
- **Autores:** Alonso Isidoro Roman + Claude (Anthropic)
- **Relacionado:** ADR-058 v3 (contrato de Flujo A, §3.1, §4-V1, §6), `docs/adr/ADR-058-circuito-completo-aguas-abajo-v3.md`
- **Invariante rector:** medir, no votar. Toda decisión de este documento está trazada a
  verificación real (versión de paquete instalada, header confirmado) o a la deuda del
  ADR-058 que resuelve — no a supuesto.
- **Alcance:** este documento diseña **solo** el primer salto del medallón
  (`CSV bronce → AVRO bronce → Parquet oro`, hoy terminal porque aRGus es la única
  fuente). La unificación cross-sensor (Suricata/Zeek/Wazuh vía `community_id`) es un
  salto posterior, ya trazado como `BACKLOG-CIRCUIT-ARROW-MEDALLION-001`, y no se diseña
  aquí — cuando existan más fuentes, este Parquet pasa a jugar el papel de "plata de
  aRGus", no de oro final.

---

## 1. Decisión de lenguaje y librerías (medido, no votado)

**Todo el converter es C++20. Cero Python en el camino crítico del circuito.**

Justificación: `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (ADR-058 §6, P1) existe *solo* porque
dos runtimes de lenguajes distintos podrían parsear el mismo texto con reglas de
redondeo distintas (`std::from_chars` correct-rounding vs `strtod`/`float()` de Python,
no garantizado en todos los bordes). Con un único binario C++20 que reusa
`parse_double` del propio proyecto, esa precondición desaparece — la deuda queda
**cerrada por diseño**, no mitigada.

Verificado DAY 205 contra `defender` (medido, no supuesto):

| Componente | Paquete | Origen | Estado |
|---|---|---|---|
| I/O AVRO | `libavro-dev` 1.11.1-1 | repo oficial Debian Bookworm (`apt-cache search avro`) | Instalado y headers confirmados (`/usr/include/avro.h` + `/usr/include/avro/*.h`, `libavro.so`) |
| Construcción de tablas + escritura Parquet | `libarrow-dev` / `libparquet-dev` 24.0.0-1 | repo oficial Apache Arrow (`apache-arrow-apt-source`, mismo patrón que HashiCorp/Jenkins en `sources.list.d/`) | Candidato confirmado vía `apt-cache policy`, 24 versiones disponibles en el índice — no instalado aún en `provision.sh` |

**Separación de responsabilidades (decisión de diseño):** no se le pide a Arrow C++ que
lea/escriba AVRO (soporte históricamente incompleto/incierto en `libarrow`). En su
lugar:

- **`avro-c`** (API C, `extern "C"`) hace todo el I/O de AVRO — mismo patrón ya usado en
  el proyecto para OpenSSL (`EVP`/`HMAC` en `CorrelationWriter`): librería C wrapeada
  desde C++20, auditable, sin binding intermedio de terceros.
- **Arrow C++ / Parquet** entra solo dentro del converter, construyendo `arrow::Table`
  en memoria a partir de las filas que `avro-c` ya deserializó, y escribiendo el
  Parquet — su competencia core, sin ambigüedad de soporte.

**Pendiente antes de tocar `provision.sh` (no implementar todavía — solo diseño):**
1. Fijar versión exacta de Arrow/Parquet (`=24.0.0-1` o la que ratifique el Consejo),
   pinneada explícitamente — mismo criterio que el pin SHA256 de Kuzu
   (`DEBT-KUZU-UPSTREAM-ARCHIVED-001`). Nunca `apt-get install` sin versión, para que
   un `vagrant destroy && up` futuro no traiga drift de versión sin control.
2. El estado actual de `defender` (con `libavro-dev` y `apache-arrow-apt-source`
   instalados a mano en esta sesión de exploración) **no es reproducible** desde
   `Vagrantfile`/`provision.sh` actuales — es exploración, no compromiso. Un
   `vagrant destroy` limpio no los traerá de vuelta hasta que se cablee la provisión.

---

## 2. Esquema AVRO — `correlation_gold_v1`

Dos bloques. El bloque bronce se **copia**, nunca se recalcula (cierra
`DEBT-EVENT-ID-FACTORY-001` y la mitad de `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001`
por construcción). El bloque oro se materializa en el converter.

### 2.1 Bloque bronce (cols 0-18, contrato `correlation_v1`, `ml-detector/include/correlation_writer.hpp`)

| # | campo | tipo AVRO | nota |
|---|---|---|---|
| 0 | schema_version | string | |
| 1 | source_sensor | string | |
| 2 | event_id | string | copiado verbatim del bronce — nunca regenerado en el converter (`DEBT-EVENT-ID-FACTORY-001`) |
| 3 | node_id | string | ya columna de 1ª clase en bronce (medido, `correlation_writer.cpp:84`) |
| 4 | community_id | string | ya columna de 1ª clase |
| 5 | flow_start_sec | long | signed (`int64_t`, `correlation_record.hpp:14`) |
| 6 | flow_start_nano | int | signed (`int32_t`) |
| 7 | src_ip | string | |
| 8 | dst_ip | string | |
| 9 | src_port | int | `uint32_t` en el proto; AVRO no tiene unsigned nativo — documentar rango en el esquema |
| 10 | dst_port | int | ídem |
| 11 | protocol | string | |
| 12 | final_classification | string | |
| 13 | threat_category | string | |
| 14 | fast_detector_score | double | canonicalizado (NaN→quiet `0x7ff8000000000000`, `-0.0`→`+0.0`) **una sola vez, en la escritura** (ADR-058 §3.1, "punto único de canonicalización") |
| 15 | ml_detector_score | double | ídem |
| 16 | overall_threat_score | double | ídem |
| 17 | authoritative_source | string | símbolo `DetectorSource_Name()` |
| 18 | hmac_row | string (hex) | **preservado como columna**, no se descarta — cierra `DEBT-GOLD-INTEGRITY-HMAC-001` |

### 2.2 Bloque oro (materializado por el converter — no viene del bronce)

| # | campo | tipo AVRO | por qué |
|---|---|---|---|
| 19 | flow_start_window | long | hoy 100% derivada en read-time (`window_micros()`, `correlation-engine/src/main.cpp:117`), nunca escrita en Parquet — `DEBT-GOLD-NODE-DIMENSION-001` exige materializarla para que el ledger sea auto-verificable sin depender de que `window_micros()` no cambie de bucketing |
| 20 | seq_in_window | int | hoy fijo a 0 (`DEBT-FLOWUID-SEQ-COLLISION-001`); se materializa igual, aunque su valor no varíe todavía |
| 21 | flow_uid | string (base64) | recomputado en el converter con `encode_flow_input` (mismo encoding canónico ya congelado y verificado byte-a-byte contra `hashlib.blake2b`, `flow_uid.hpp`) desde 3+4+19[+20] — permite verificar re-derivación bit a bit contra la propiedad ya materializada en Kuzu (`cypher_builder.hpp:101,110`) |
| 22 | ingested_at | long (`timestamp-micros`, logical type) | clase **E** — determinista-de-ejecución (`kuzu_graph_sink.hpp:47`). Se **preserva** desde el bronce/WAL, nunca se recalcula al reprocesar; jerarquía de fuentes: el WAL prevalece en replay, el campo Kuzu es vista del estado actual (`DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`, parte b) |
| 23 | temporal_anomaly | boolean | clase **E**, fórmula portada 1:1 desde `cypher_builder.hpp:86`, evaluada sobre el `ingested_at` correcto — nunca el del reproceso (`DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`, parte a) |

**Relación con el predicado de equivalencia §3.1 (ADR-058):**
- Cols 0-18 + 19-21 son clase **D** (determinista-de-dato) → entran en `EQUIV(Camino0, FlujoA+B)`, comparación `==` bit-exacta en los doubles (14-16), tras canonicalización.
- Cols 22-23 son clase **E** → quedan explícitamente **fuera** del predicado, por diseño, no por omisión.

---

## 3. Partición de directorio

**Por fecha únicamente** (`date=YYYY-MM-DD/`, heredado del rotado de segmentos del
bronce, DAY 203). **Sin** partición secundaria por `node_id` todavía.

Motivo: el propio ADR-058 §8 declina explícitamente el gold-plating especulativo (SLA,
particiones anticipadas sin dato de volumen real) hasta que el número de nodos e
instalaciones lo justifique — coherente con "medir, no votar" y con la regla de "una
batalla" del proyecto. Si la hipótesis central del proyecto (contribución por nodo a la
calidad del corpus) madura, particionar por `node_id` es un cambio de layout de
directorio, no de esquema — no bloquea el diseño actual.

---

## 4. Deudas del ADR-058 que este diseño satisface o deja explícitamente abiertas

| Deuda | Efecto de este diseño |
|---|---|
| `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (P1) | **Cerrada por diseño** — sin runtime Python, no hay frontera de lenguaje que cruzar |
| `DEBT-GOLD-NODE-DIMENSION-001` (P0) | Satisfecha — cols 19-21 materializan `flow_start_window`/`seq_in_window`/`flow_uid` en el oro |
| `DEBT-GOLD-INTEGRITY-HMAC-001` (P0) | Satisfecha para HMAC por-fila (col 18 preservada). **Pendiente de diseño aparte:** firma del Parquet consolidado como artefacto (greenfield HMAC-SHA256, no reutiliza el firmador Ed25519 de `scripts/parquet/` — `DEBT-DOCS-MEDALLION-DUALITY-001`) |
| `DEBT-EVENT-ID-FACTORY-001` (P1) | Satisfecha por regla de diseño — `event_id` se copia, nunca se regenera |
| `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001` (P1) | Parcialmente satisfecha — el esquema fuerza copia bit-exacta de scores; la re-validación con scores no-triviales sigue pendiente de que `DEBT-RANSOMWARE-ML-HEAD-INERT-001` se cierre |
| `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P1) | Cubierta por cols 22-23 y la regla de jerarquía de fuentes (WAL prevalece en replay) — implementación aún pendiente |
| `DEBT-PARQUET-KUZU-CONNECTOR-001` (P1, Flujo B) | **Fuera de alcance de este documento** — este diseño cubre bronce→AVRO→Parquet oro (Flujo A), no el conector Parquet→Kuzu |

---

## 5. Preguntas abiertas para el Consejo

1. **Versión exacta de Arrow/Parquet a pinnear.** Candidato: `24.0.0-1` (última en el
   índice al DAY 205). ¿Alguna razón para fijar una LTS anterior en vez de la más
   reciente?
2. **Formato del rango unsigned de puertos en AVRO (cols 9-10).** AVRO `int` es signed
   de 32 bits; el proto usa `uint32_t`. Los valores reales de puerto (`0-65535`) caben
   sin overflow, pero conviene decidir si se documenta la asimetría en el propio
   `.avsc` (comentario/doc field) o si se abre una nota de deuda menor.
3. **¿Este documento se formaliza como ADR numerado, o queda como documento de diseño
   de apoyo referenciado desde ADR-058?** (Nota de proceso: evitar colisión de
   numeración — verificar contra el backlog completo antes de asignar número, lección
   de DAY 175/199.)

---

*Documento de apoyo a ADR-058 v3 — Via Appia Quality.*