# DISEÑO — Eslabón 1, Flujo A (bronce → AVRO → Parquet oro)

- **Estado:** ✅ RATIFICADO — Consejo de Sabios (9/9: Claude, ChatGPT, DeepSeek, Gemini,
  GLM, Grok, Kimi, Mistral, Qwen), DAY 205
- **Fecha:** DAY 205 (borrador) → DAY 205 (ratificación)
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

**RATIFICADO — versión pinneada: `libarrow-dev=24.0.0-1` / `libparquet-dev=24.0.0-1`.**
(Consejo 9/9, ver §6 changelog). Instalar en `provision.sh`:
```bash
apt-get install -y -V libarrow-dev=24.0.0-1 libparquet-dev=24.0.0-1
apt-mark hold libarrow-dev libparquet-dev
```
**Regla de proceso permanente** (adoptada de la propuesta de ChatGPT, Consejo DAY 205):
el proyecto pinnea la primera versión de Arrow que supera la batería completa de
validación reproducible (compila, tests verdes, Parquet bit-idéntico, sin regresión de
rendimiento). Toda actualización posterior de Arrow requiere revalidación completa del
circuito y regeneración de la evidencia experimental — nunca se actualiza "porque sí".

**Nota de reversibilidad** (Kimi, DAY 205): Arrow 24.0.0 escribe Parquet format 2.6,
backward-compatible con lectores 12.x+. Un downgrade futuro de la librería, si hiciera
falta, no invalida los ficheros ya escritos — no es one-way door.

**Estado de `defender` al DAY 205:** `libavro-dev` y `apache-arrow-apt-source`
instalados a mano en la sesión de exploración — **no reproducible** desde
`Vagrantfile`/`provision.sh` actuales todavía. Un `vagrant destroy` limpio no los
traerá de vuelta hasta que se cablee la provisión con los pines de arriba.

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

## 5. Ratificación del Consejo — DAY 205

**Q1 — Versión Arrow/Parquet:** `24.0.0-1`, pinneada explícita + `apt-mark hold`. Ver §1.
Voto: 8/9 directo a `24.0.0-1`; Claude (voto inicial `18.1.0-1`) cambió su voto tras
constatar que Arrow no tiene modelo LTS (a diferencia de Kuzu, que sí tenía riesgo real
de discontinuidad) y que nadie aportó evidencia de CVEs sin parchear que justificaran
una versión anterior. Regla de proceso adoptada (ChatGPT): pinnear la primera versión
que supera la batería de validación reproducible; revalidar antes de cualquier upgrade.

**Q2 — Puertos en AVRO (cols 9-10):** `int` signed 32-bit + campo `doc` documentando la
asimetría con `uint32_t` del proto. **Unanimidad 9/9.** Sin deuda nueva. Redacción
adoptada (Kimi):
```json
{
  "name": "src_port",
  "type": "int",
  "doc": "Unsigned uint32_t del proto. Rango válido: 0-65535. Valores >= 2^31 son reservados para extensión futura."
}
```
Análogo para `dst_port`.

**Q3 — ADR vs. documento de apoyo:** Documento de apoyo, referenciado desde ADR-058.
**8/9** — único disidente: Grok (proponía ADR-059, argumentando impacto en deudas
P0/P1). Mayoría considera que *impactar* deudas no equivale a *decidir* arquitectura
nueva — este documento vive en containment bajo ADR-058, no en paridad con él. Ruta de
archivo: `docs/design/eslabon-1-flujo-a-avro-parquet/eslabon-1-flujo-a-avro-parquet.md`,
referenciado desde ADR-058 §9
(changelog) o sección de referencias.

**Correcciones de hecho registradas durante la deliberación:** Mistral describió la
serie 24.x de Arrow como "LTS" — inexacto, ninguna rama de Arrow tiene ese estatus
(confirmado independientemente por DeepSeek, GLM, Qwen, Grok). No cambia la conclusión
(24.0.0-1 sigue siendo la versión correcta) pero se deja registrado por higiene
epistémica.

## 6. Preguntas abiertas nuevas (no bloqueantes, quedan para más adelante)

1. **Política de compatibilidad `correlation_gold_v1` → `v2`** (aportada por ChatGPT,
   no estaba en el alcance original). Sin resolver ahora — decidir cuándo se plantee
   la primera necesidad real de evolución de esquema, no antes.
2. **Interfaces `BronzeReader`/`GoldWriter`** (aportada por ChatGPT) para desacoplar el
   algoritmo del converter del formato concreto (AVRO/Parquet), coherente con el patrón
   ya usado en el proyecto (`ICryptoProvider`, `IGraphSink`). Recomendado como
   refinamiento de implementación, no bloqueante de esta ratificación.

---

*Documento de apoyo a ADR-058 v3 — RATIFICADO por el Consejo de Sabios (9/9), DAY 205 — Via Appia Quality.*