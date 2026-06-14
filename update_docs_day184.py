#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_docs_day184.py — Actualiza docs/BACKLOG.md y README.md con el trabajo del DAY 184.

Diseño (Via Appia / lección DEBT-DOCS-BACKLOG-DEDUP-001):
  * IDEMPOTENTE: si los marcadores DAY 184 ya existen, no reinserta (sale limpio).
    Correrlo dos veces no duplica nada.
  * DEFENSIVO: hace backup `<fichero>.bak.<timestamp>` antes de tocar cada fichero.
  * POR ANCLA, NO POR APPEND CIEGO: inserta usando cadenas-ancla exactas, nunca `cat >>`.
  * VERIFICABLE: al final corre un chequeo de duplicados acotado a MIS marcadores
    (cada uno debe aparecer exactamente una vez). Con --audit imprime además todos
    los headings `##`/`###` repetidos del fichero entero, para inspección manual.

Uso:
    python3 update_docs_day184.py                      # usa ./docs/BACKLOG.md y ./README.md
    python3 update_docs_day184.py --dry-run            # no escribe; muestra qué haría
    python3 update_docs_day184.py --audit              # tras editar, lista headings duplicados
    python3 update_docs_day184.py --backlog PATH --readme PATH   # rutas explícitas

Salida: exit 0 si todo OK (incluido "ya estaba aplicado"); exit 1 si algún ancla no
        se encuentra (el fichero no se modifica en ese caso).
"""

import argparse
import datetime as _dt
import os
import re
import sys

# ──────────────────────────────────────────────────────────────────────────────
# CONTENIDO A INSERTAR
# ──────────────────────────────────────────────────────────────────────────────

# --- README: bloque DAY-STATUS completo (entre los marcadores HTML) -------------
README_DAY_STATUS = """<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 184 |
| Tag | v1.0.0-day166 |
| Branch | feature/day183-kuzu-sink-unwind-flush |
| EMECAS++ OSS | \u2705 verde \u2014 test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | \u2705 VERDE \u2014 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| Frente A \u2014 Backend Kuzu | \u2705 `KuzuGraphSink` real detr\u00e1s de `IGraphSink` \u00b7 Kuzu v0.11.3 (upstream archivado, pin SHA256) \u00b7 BD en `/tmp` guest-nativo (vboxsf rompe mmap) |
| flush()\u2192FlushResult | \u2705 DAY 184 \u2014 contrato POD `[[nodiscard]]` sobre el TIPO; ning\u00fan sink puede descartar en silencio el fallo de durabilidad bajo -Werror (cierre estructural, mismo esp\u00edritu que H-1) |
| KuzuGraphSink batch | \u2705 DAY 184 \u2014 write() acumula, flush() ejecuta el batch en UNA transacci\u00f3n (BEGIN/execute(prepared)/COMMIT, ROLLBACK+retenci\u00f3n en fallo). Cierra H-1 en el path EJECUTADO de Kuzu |
| VERIFY-3 | \u2705 DAY 184 \u2014 test gemelo COMMIT(2 nodos)/ROLLBACK(0): el batch va en 1 transacci\u00f3n. Baseline test_kuzu_graph_sink 0.48s\u21920.86s (contabilizado) |
| Kuzu 0.11.3 API | \u2705 DAY 184 \u2014 verificada contra header vendorizado: control transaccional por string, execute(prepared) vari\u00e1dico, Value sin ctor desde string_view (materializar a std::string) |
| Frente C \u2014 event_id replay-stable | \U0001f7e1 diagnosticado + escalado al Consejo \u00b7 DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (P1) |
| Consejo de Sabios | \u2705 DAY 184 \u2014 8/8 revisaron las 5 decisiones del banco de tortura: aprobadas con condiciones de validez (tmpfs, fuzzer protobuf, nodo-estrella, librer\u00eda pura, HMAC por env) |
| Arquitectura | \u2705 ADR-046 v4 \u00b7 ADR-052 v3.2 \u00b7 ADR-051 v2.2 \u00b7 ADR-055 v1 \u00b7 \U0001f7e2 ADR-057 v2 (D1+D2 resueltas; D3 abierta) \u00b7 \u23f3 ADR-050/053/054 |
| Pr\u00f3ximo hito (DAY 185) | Extraer `libcorrelation_v1` (Opci\u00f3n B) + injector adversarial a /dev/shm + primera tortura (rows-in vs nodos materializados, RSS acotado, staleness) |
| Gate UEx/INCIBE | Datasets de valor cient\u00edfico (no deadline duro) \u2014 se entregan salga corroborada o seca la hip\u00f3tesis ensemble |
<!-- /DAY-STATUS -->"""

# --- README: bloque "Hitos DAY 184" (se inserta ANTES de "### Hitos DAY 182") ---
README_HITOS_184 = """### Hitos DAY 184 \U0001f389 \u2014 flush()\u2192FlushResult + batch transaccional + Consejo del banco de tortura
- **`IGraphSink::flush()` deja de devolver `void` \u2192 `FlushResult`** (POD `{bool ok; uint64_t rows_flushed; uint64_t rows_pending; explicit operator bool}`). `[[nodiscard]]` sobre el TIPO, no sobre cada m\u00e9todo \u2192 ning\u00fan sink presente o futuro puede descartar en silencio el fallo de durabilidad bajo `-Werror`. Cierre **estructural** (mismo esp\u00edritu que H-1, cerrado por par\u00e1metro tipado y no por `esc()`). `main.cpp`: flush fallido \u2192 `EXIT_FAILURE` (el harness E2E no lee \"ok\" sobre datos perdidos). 8 touchpoints de `IGraphSink` revisados por grep, cero fuga a otros componentes. Commit `4e221ede`.
- **`KuzuGraphSink` cableado en batch.** `write()` acumula (copia `CorrelationRecord` + `flow_uid` materializado + `ingested_at` sellado a la entrada). `flush()` ejecuta el batch en UNA transacci\u00f3n: `BEGIN`/loop `execute(prepared)`/`COMMIT`; `ROLLBACK` + buffer retenido en fallo (retry, nunca descarte silencioso). **Cierra H-1 en el path EJECUTADO de Kuzu** \u2014 el sink ya no corre `query(string interpolado)`, corre `execute(prepared, params)`. Orden de miembros `db_\u2192conn_\u2192prep_*\u2192accumulator_` resuelve lifetimes por RAII. Destructor grita si el buffer no est\u00e1 vac\u00edo. Commit `112b9df1`.
- **VERIFY-3 \u2014 test de agrupaci\u00f3n transaccional.** Dos tests gemelos: mismas N filas, solo cambia `COMMIT` vs `ROLLBACK`. COMMIT \u2192 2 nodos durables; ROLLBACK \u2192 0. Prueba que `BEGIN/COMMIT` por string envuelve los `execute(prepared)` en UNA transacci\u00f3n = 1 checkpoint por batch (la premisa que `flush()` amortiza, ahora medida). Baseline `test_kuzu_graph_sink` 0.48s\u21920.86s (batch + aperturas extra de BD, contabilizado). 6/6 verde.
- **API Kuzu 0.11.3 verificada contra el header vendorizado** (`/usr/local/include/kuzu.hpp`, NO de memoria): (1) NO hay m\u00e9todo de transacci\u00f3n tipado \u2014 el control es por string `query(\"BEGIN TRANSACTION\"/\"COMMIT\"/\"ROLLBACK\")`, cada uno devuelve `QueryResult`, se comprueba `isSuccess()`; (2) `execute(PreparedStatement*, pair<string,Args>...)` vari\u00e1dico, claves `std::string`; (3) `common::Value` SIN ctor desde `string_view`, todos los ctors `explicit` \u2192 materializar cada campo de texto a `std::string` (`string_view::data()` no termina en nul); (4) el header documenta el SIGSEGV de DAY 183 (`preventTransactionRollbackOnDestruction`: rollback en destrucci\u00f3n sobre Database cerrada = SEGFAULT).
- **Consejo de Sabios (8/8) \u2014 revisi\u00f3n del banco de tortura del DAY 185.** Las 5 decisiones (medir-primero, Opci\u00f3n B, extraer librer\u00eda, injector-a-fichero, HMAC=correctitud) **aprobadas con condiciones de validez**. Se\u00f1al incorporada: CSV bronce en `/dev/shm` (tmpfs, no disco \u2014 a\u00edsla I/O de la contenci\u00f3n con los COMMIT de Kuzu); test de equivalencia sobre fuzzer de protobuf (1M iteraciones, no caso \u00fanico); injector adversarial += nodo-estrella/alta cardinalidad + l\u00ednea truncada + duplicado exacto con contador + out-of-order causal; `libcorrelation_v1` PURA (struct + serializaci\u00f3n, cero I/O); HMAC por env var compartida, nunca hardcode, nunca `--skip-hmac`. Ruido rechazado: `--skip-hmac` (puerta trasera), clave HMAC hardcodeada (segunda fuente de verdad), \"SQL injection\" en payload (categor\u00eda err\u00f3nea \u2014 Kuzu es Cypher, ya cubierto por H-1).

"""

# --- BACKLOG: secci\u00f3n "Entradas DAY 184" (se inserta ANTES de "## 🆕 Entradas DAY 182") ---
BACKLOG_ENTRADAS_184 = """## \U0001f195 Entradas DAY 184 \u2014 flush()\u2192FlushResult + batch transaccional Kuzu + Consejo banco de tortura

> Origen: sesi\u00f3n DAY 184 (branch `feature/day183-kuzu-sink-unwind-flush`). Endurecimiento del
> sink de durabilidad que protege LA MEDICI\u00d3N (no production-readiness) + s\u00edntesis del Consejo
> (8/8) sobre las 5 decisiones del banco de tortura del DAY 185. Todo lo de hoy es \"suelo que
> protege la medici\u00f3n\": que el camino bronce\u2192Kuzu trague la tortura sin perder/corromper filas.

### \u2705 CERRADO DAY 184 \u2014 contrato de durabilidad del sink

- **flush()\u2192FlushResult (commit `4e221ede`).** `IGraphSink::flush()` deja de devolver `void`
  (ocultaba el fallo de durabilidad) y devuelve un POD `[[nodiscard]] FlushResult
  {bool ok; uint64_t rows_flushed; uint64_t rows_pending; explicit operator bool}`. El
  `[[nodiscard]]` est\u00e1 sobre el TIPO, no sobre cada m\u00e9todo \u2192 ning\u00fan sink presente o futuro
  puede descartar el fallo bajo `-Werror` (cierre estructural, mismo esp\u00edritu que H-1: tipado,
  no `esc()`). `main.cpp:134` \u2192 flush fallido = `EXIT_FAILURE`. 8 touchpoints de `IGraphSink`
  revisados por grep, cero fuga a ml-detector/firewall/etc.
- **KuzuGraphSink batch (commit `112b9df1`).** `write()` acumula (copia `CorrelationRecord` +
  `flow_uid` materializado + `ingested_at` sellado a la entrada v\u00eda `ingest_now_ns()`).
  `flush()` ejecuta el batch en UNA transacci\u00f3n (`BEGIN`/loop `execute(prepared)`/`COMMIT`,
  `ROLLBACK`+buffer retenido en fallo \u2014 retry, nunca descarte). **Cierra H-1 en el path
  EJECUTADO de Kuzu** (el sink corre `execute(prepared, params)`, no `query(string)`).
  Orden de miembros `db_\u2192conn_\u2192prep_*\u2192accumulator_` resuelve lifetimes por RAII; el destructor
  grita si el buffer no est\u00e1 vac\u00edo (durabilidad violada).
- **VERIFY-3 (test-only, commit separado).** Dos tests gemelos en `test_kuzu_graph_sink.cpp`:
  mismas N filas, solo cambia COMMIT vs ROLLBACK. COMMIT\u21922 nodos durables, ROLLBACK\u21920. Prueba
  que `BEGIN/COMMIT` por string envuelve los `execute(prepared)` en 1 transacci\u00f3n = 1 checkpoint
  por batch (la premisa que `flush()` amortiza, ahora medida). Baseline 0.48s\u21920.86s
  (contabilizado). 6/6 verde.
- **3 lecciones del header Kuzu 0.11.3** (verificadas contra `/usr/local/include/kuzu.hpp`, no de
  memoria): control transaccional por string (no m\u00e9todo tipado); `execute(prepared, pair<string,
  Args>...)` vari\u00e1dico; `common::Value` sin ctor desde `string_view` \u2192 materializar texto a
  `std::string`; el header documenta el SIGSEGV de DAY 183
  (`preventTransactionRollbackOnDestruction`).

### DEBT-LIBCORRELATION-V1-EXTRACT-001 \u2014 Extraer CorrelationWriter \u2192 libcorrelation_v1 (Opci\u00f3n B)
**Severidad:** \U0001f7e1 P1 \u2014 prerrequisito del injector adversarial
**Estado:** ABIERTO \u2014 DAY 184 (decisi\u00f3n Alonso: Opci\u00f3n B sobre A; Consejo 8/8 con condiciones)
**Componente:** `ml-detector/src/correlation_writer.cpp` \u2192 `libs/correlation-v1/`
Extraer la serializaci\u00f3n `correlation_v1` a una librer\u00eda compartida con `struct CorrelationV1Row`
(18 campos planos = mismos que `CorrelationRecord` del consumidor) + `build_row(const
CorrelationV1Row&)`. ml-detector pasa a ser adaptador fino `NetworkSecurityEvent\u2192CorrelationV1Row
\u2192build_row`. La librer\u00eda debe ser **PURA** (struct + serializaci\u00f3n, CERO `LogReader`/`ZmqPublisher`/
`FileWatcher`) \u2014 se justifica por DOS consumidores reales (ml-detector + injector), NO por el
`argus-adapter-producer` hipot\u00e9tico (que es lectura+transporte, no serializaci\u00f3n-desde-struct;
condici\u00f3n Kimi/Gemini/Qwen + dissenso Claude). Mitigaci\u00f3n: test de equivalencia byte-id\u00e9ntica
`event\u2192row\u2192build_row(row)` vs `build_row(event)`, **sobre un fuzzer de protobuf (1M iteraciones,
ejerce todos los optional/repeated)**, NO un caso \u00fanico (chatgpt/Kimi/Mistral). Nota: validar
adem\u00e1s el DOMINIO de los campos enum-derivados (col 17 `authoritative_source`) \u2014 el injector no
debe poder emitir un s\u00edmbolo que el enum protobuf jam\u00e1s producir\u00eda.
**Test de cierre:** equivalencia byte-id\u00e9ntica verde sobre 1M de eventos fuzzed; la librer\u00eda no
enlaza ninguna clase de I/O; ml-detector e injector la usan id\u00e9ntica.
**Estimaci\u00f3n:** 1-2 sesiones (DAY 185).

### DEBT-INJECTOR-ADVERSARIAL-BRONZE-001 \u2014 Injector adversarial del banco de tortura
**Severidad:** \U0001f7e1 P1 \u2014 sin \u00e9l el injector es c\u00f3mplice (prueba contenido, asume stream bien formado)
**Estado:** ABIERTO \u2014 DAY 184 (Consejo 8/8 + s\u00edntesis Claude)
**Componente:** `tools/` (tercer hermano de la familia de stress-testers) + bronce `correlation_v1`
Injector que emula el contrato AspectV1/correlation_v1 (append CSV+HMAC a fichero, consumidor lo
lee por `--follow` tail-poll). Bater\u00eda adversarial = contenido + **forma del stream**:
- **Contenido:** H-1 strings (comillas/backslash/Cypher), `temporal_anomaly`, colisiones de
  `flow_uid`, r\u00e1fagas que fuerzan flush inline, volumen que desborda el acumulador.
- **Topolog\u00eda (Gemini/DeepSeek/Kimi):** **nodo-estrella / alta cardinalidad** \u2014 un `node_id` con
  10^6 aristas en una r\u00e1faga (= un scan nmap real: un origen, miles de destinos) que satura las
  adjacency lists de Kuzu antes del flush. Colisi\u00f3n de hash 64-bit, no de string (Kimi).
- **Forma del stream (Claude, P3):** **l\u00ednea truncada** (writer a media l\u00ednea durante append
  no-at\u00f3mico; el consumidor debe descartarla y aceptarla al completarse, sin contar dos veces ni
  perder); **HMAC v\u00e1lido sobre contenido en frontera** (firma correcta, 18 cols donde se esperan
  19, o campo vac\u00edo que no deber\u00eda); **duplicado exacto con contador** (MERGE deduplica \u2192 si el
  contador del banco cuenta 2 y el grafo tiene 1, la m\u00e9trica de p\u00e9rdida va a negativo y envenena la
  medici\u00f3n); **out-of-order causal** (evento de cierre antes que el de apertura).
**Test de cierre:** cada vector documentado con la hip\u00f3tesis que prueba; el consumidor descarta lo
inv\u00e1lido ANTES del grafo; la m\u00e9trica de p\u00e9rdida nunca da negativo (duplicado contemplado).
**Estimaci\u00f3n:** 2-3 sesiones.

### DEBT-BRONZE-TORTURE-TMPFS-001 \u2014 CSV bronce de tortura en /dev/shm (tmpfs), no disco f\u00edsico
**Severidad:** \U0001f7e1 P1 \u2014 condici\u00f3n de validez de la primera tortura (a\u00edsla la variable I/O)
**Estado:** ABIERTO \u2014 DAY 184 (Gemini/Qwen \u2014 mejor aportaci\u00f3n del Consejo que Claude no vio)
**Componente:** banco de tortura (injector + correlation-engine `--follow`)
Escribir el CSV bronce de la tortura en disco f\u00edsico **sustituye el cuello del NIC por el cuello
del VFS/page-cache** y, peor, mete contenci\u00f3n de write-lock con los `COMMIT` de Kuzu sobre el mismo
disco \u2014 medir\u00edas contenci\u00f3n de I/O, no tu pipeline. El CSV bronce debe vivir en `/dev/shm` (tmpfs,
RAM) para aislar la I/O f\u00edsica como variable. Misma l\u00f3gica que \"BD Kuzu en /tmp guest-nativo, no
vboxsf\", una capa m\u00e1s arriba.
**Test de cierre:** la primera tortura corre con bronce en `/dev/shm`; medici\u00f3n documentada como
\"pipeline de c\u00f3mputo, sin I/O f\u00edsica ni red\" (etiqueta honesta P4).
**Estimaci\u00f3n:** 0.5 sesi\u00f3n (config del banco).

### DEBT-CONTRACT-DRIFT-PROTOBUF-001 \u2014 Un campo nuevo en el protobuf toca muchos tests, no uno
**Severidad:** \U0001f7e2 P2 \u2014 fragilidad de contrato (no un test, una clase)
**Estado:** ABIERTO \u2014 DAY 184 (observaci\u00f3n Alonso, refina P2 de Claude)
**Componente:** `protobuf/network_security.proto` + reader + writer + roundtrip + fuzzer
A\u00f1adir un campo al contrato `correlation_v1`/protobuf no rompe *un* test: toca el reader, el
writer, el roundtrip, el fuzzer de equivalencia y `DEBT-TEST-COL17-CONTRACT-DRIFT-001`
simult\u00e1neamente. No es un parche puntual \u2014 es una **clase de drift** que necesita pol\u00edtica: un gate
que liste expl\u00edcitamente los puntos de contacto del contrato y falle si un campo nuevo no los
actualiza todos. Ref. cruzada: `DEBT-TEST-COL17-CONTRACT-DRIFT-001`.
**Test de cierre:** a\u00f1adir un campo de prueba al .proto \u2192 el gate enumera y exige actualizar todos
los puntos de contacto; ninguno queda obsoleto en silencio.
**Estimaci\u00f3n:** 1 sesi\u00f3n (cuando se toque el contrato).

### BACKLOG-THROUGHPUT-TARGET-001 \u2014 Estimar caudal objetivo de producci\u00f3n (BLOQUEADO POR HARDWARE)
**Estado:** \u23f3 BLOQUEADO \u2014 DAY 184 \u00b7 **Bloqueado por:** BACKLOG-HARDWARE-FEDER-001 (RPi5/N100)
**Prioridad:** P1 cuando llegue hardware f\u00edsico
El criterio de \"suelo suficiente\" de Kimi (\"si CSV-directo aguanta 10\u00d7 el caudal de producci\u00f3n sin
p\u00e9rdida, el suelo es v\u00e1lido\") requiere un n\u00famero: eventos/seg o Mb/s monitorizados por una Raspberry
en un hospital/municipio peque\u00f1o. **Ese n\u00famero NO se estima desde la silla** \u2014 hasta tener tarjetas
f\u00edsicas no hay forma honesta de fijarlo. Decisi\u00f3n Alonso: no se inventa. La primera tortura mide
**p\u00e9rdida absoluta** (rows-in vs nodos-materializados = 0 o no), criterio binario v\u00e1lido sin el
target. El \"suelo suficiente\" relativo espera al hardware.
**Test de cierre:** con RPi5/N100 desplegados, medir caudal real (eventos/seg, Mb/s) bajo carga MITRE
\u2192 fijar el target \u2192 declarar criterio de suelo suficiente operable.
**Estimaci\u00f3n:** post-hardware.

### Regla del banco de tortura (DAY 184 \u2014 Consejo 8/8 + arbitraje Claude)
- **HMAC por env var compartida, nunca hardcode, nunca `--skip-hmac`.** El injector firma con la
  misma clave que el consumidor (`ARGUS_BRONZE_HMAC_KEY_HEX`); ambos la toman de fuera, ninguno la
  provisiona (cero acople nuevo con DEBT-BRONZE-KEY-PROVISIONING-001). RECHAZADO: `--skip-hmac` en el
  consumidor (puerta trasera que mata el invariante de integridad), clave hardcodeada (segunda fuente
  de verdad). Ausencia de clave = error ruidoso, no default silencioso (Kimi).

"""

# ──────────────────────────────────────────────────────────────────────────────
# ANCLAS Y MARCADORES
# ──────────────────────────────────────────────────────────────────────────────

README_STATUS_OPEN = "<!-- DAY-STATUS -->"
README_STATUS_CLOSE = "<!-- /DAY-STATUS -->"
README_HITOS_ANCHOR = "### Hitos DAY 182 \U0001f389"
README_HITOS_184_MARK = "### Hitos DAY 184 \U0001f389"

BACKLOG_DATE_OLD = "*\u00daltima actualizaci\u00f3n: DAY 181 \u2014 2026-06-11*"
BACKLOG_DATE_NEW = "*\u00daltima actualizaci\u00f3n: DAY 184 \u2014 2026-06-14*"
BACKLOG_DATE_DONE = "*\u00daltima actualizaci\u00f3n: DAY 184"
BACKLOG_ENTRADAS_ANCHOR = "## \U0001f195 Entradas DAY 182 \u2014 Smoke B1 ejecutado"
BACKLOG_ENTRADAS_184_MARK = "## \U0001f195 Entradas DAY 184 \u2014 flush()\u2192FlushResult"

# Marcadores que deben aparecer EXACTAMENTE una vez tras la edici\u00f3n (verificaci\u00f3n acotada)
EXPECTED_UNIQUE_README = [README_HITOS_184_MARK]
EXPECTED_UNIQUE_BACKLOG = [
    BACKLOG_ENTRADAS_184_MARK,
    "### DEBT-LIBCORRELATION-V1-EXTRACT-001",
    "### DEBT-INJECTOR-ADVERSARIAL-BRONZE-001",
    "### DEBT-BRONZE-TORTURE-TMPFS-001",
    "### DEBT-CONTRACT-DRIFT-PROTOBUF-001",
    "### BACKLOG-THROUGHPUT-TARGET-001",
]


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

class AbortEdit(Exception):
    pass


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _backup(path):
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak.%s" % (path, ts)
    with open(path, "r", encoding="utf-8") as src, open(bak, "w", encoding="utf-8") as dst:
        dst.write(src.read())
    return bak


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _count(text, needle):
    return text.count(needle)


# ──────────────────────────────────────────────────────────────────────────────
# README
# ──────────────────────────────────────────────────────────────────────────────

def update_readme(text):
    """Devuelve (texto_nuevo, lista_de_acciones). No escribe. Lanza AbortEdit si falta un ancla."""
    actions = []

    # 1) Reemplazar el bloque DAY-STATUS completo (idempotente por construcci\u00f3n).
    if README_STATUS_OPEN not in text or README_STATUS_CLOSE not in text:
        raise AbortEdit("README: no encuentro los marcadores <!-- DAY-STATUS --> / <!-- /DAY-STATUS -->")
    pattern = re.compile(
        re.escape(README_STATUS_OPEN) + r".*?" + re.escape(README_STATUS_CLOSE),
        re.DOTALL,
        )
    new_text, n = pattern.subn(README_DAY_STATUS, text, count=1)
    if n != 1:
        raise AbortEdit("README: el bloque DAY-STATUS no casa de forma \u00fanica")
    if new_text != text:
        actions.append("README: bloque DAY-STATUS \u2192 DAY 184")
    else:
        actions.append("README: bloque DAY-STATUS ya estaba en DAY 184 (sin cambios)")
    text = new_text

    # 2) Insertar Hitos DAY 184 antes de Hitos DAY 182 (idempotente: guard por marcador).
    if README_HITOS_184_MARK in text:
        actions.append("README: Hitos DAY 184 ya presente (sin cambios)")
    elif README_HITOS_ANCHOR in text:
        text = text.replace(README_HITOS_ANCHOR, README_HITOS_184 + README_HITOS_ANCHOR, 1)
        actions.append("README: insertado bloque Hitos DAY 184")
    else:
        raise AbortEdit("README: no encuentro el ancla '%s'" % README_HITOS_ANCHOR)

    return text, actions


# ──────────────────────────────────────────────────────────────────────────────
# BACKLOG
# ──────────────────────────────────────────────────────────────────────────────

def update_backlog(text):
    actions = []

    # 1) Fecha de cabecera.
    if BACKLOG_DATE_OLD in text:
        text = text.replace(BACKLOG_DATE_OLD, BACKLOG_DATE_NEW, 1)
        actions.append("BACKLOG: fecha de cabecera \u2192 DAY 184")
    elif BACKLOG_DATE_DONE in text:
        actions.append("BACKLOG: fecha de cabecera ya en DAY 184 (sin cambios)")
    else:
        # No abortamos por la fecha: solo avisamos. La cabecera puede haber cambiado de formato.
        actions.append("BACKLOG: \u26a0 no encontr\u00e9 la l\u00ednea de fecha esperada \u2014 rev\u00edsala a mano")

    # 2) Insertar Entradas DAY 184 antes de Entradas DAY 182 (guard por marcador).
    if BACKLOG_ENTRADAS_184_MARK in text:
        actions.append("BACKLOG: secci\u00f3n Entradas DAY 184 ya presente (sin cambios)")
    elif BACKLOG_ENTRADAS_ANCHOR in text:
        text = text.replace(BACKLOG_ENTRADAS_ANCHOR, BACKLOG_ENTRADAS_184 + BACKLOG_ENTRADAS_ANCHOR, 1)
        actions.append("BACKLOG: insertada secci\u00f3n Entradas DAY 184 (6 \u00edtems)")
    else:
        raise AbortEdit("BACKLOG: no encuentro el ancla '%s'" % BACKLOG_ENTRADAS_ANCHOR)

    return text, actions


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACI\u00d3N
# ──────────────────────────────────────────────────────────────────────────────

def verify_unique(text, expected, label):
    """Cada marcador de `expected` debe aparecer exactamente una vez. Devuelve lista de problemas."""
    problems = []
    for mark in expected:
        c = _count(text, mark)
        if c != 1:
            problems.append("  [%s] '%s' aparece %d veces (esperado 1)" % (label, mark, c))
    return problems


def audit_duplicate_headings(text, label):
    """Lista headings ## / ### duplicados en el fichero (informativo, lecci\u00f3n DAY 170)."""
    heads = [ln.rstrip() for ln in text.splitlines() if ln.startswith("## ") or ln.startswith("### ")]
    seen = {}
    for h in heads:
        seen[h] = seen.get(h, 0) + 1
    dups = sorted([h for h, c in seen.items() if c > 1])
    if dups:
        print("\n[AUDIT %s] headings repetidos (%d) \u2014 revisi\u00f3n manual, NO bloqueante:" % (label, len(dups)))
        for h in dups:
            print("    %dx  %s" % (seen[h], h))
    else:
        print("\n[AUDIT %s] sin headings ##/### duplicados." % label)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def process(path, updater, expected_unique, dry_run, do_audit, label):
    if not os.path.isfile(path):
        print("\u274c %s: fichero no encontrado: %s" % (label, path))
        return False
    original = _read(path)
    try:
        new_text, actions = updater(original)
    except AbortEdit as exc:
        print("\u274c %s: %s" % (label, exc))
        print("   (no se ha modificado nada)")
        return False

    for a in actions:
        print("   \u2022 " + a)

    if new_text == original:
        print("   = %s sin cambios netos (ya estaba aplicado)." % label)
        if do_audit:
            audit_duplicate_headings(new_text, label)
        return True

    if dry_run:
        print("   [dry-run] %s NO escrito." % label)
        return True

    bak = _backup(path)
    print("   \u2192 backup: %s" % bak)
    _write(path, new_text)

    # Verificaci\u00f3n acotada a mis marcadores.
    final = _read(path)
    problems = verify_unique(final, expected_unique, label)
    if problems:
        print("\u26a0 VERIFICACI\u00d3N FALLIDA en %s:" % label)
        print("\n".join(problems))
        print("   Restaura con: cp '%s' '%s'" % (bak, path))
        return False
    print("   \u2705 %s escrito y verificado (marcadores \u00fanicos)." % label)

    if do_audit:
        audit_duplicate_headings(final, label)
    return True


def main():
    ap = argparse.ArgumentParser(description="Actualiza BACKLOG.md y README.md con el trabajo del DAY 184.")
    ap.add_argument("--backlog", default="docs/BACKLOG.md", help="ruta a BACKLOG.md (default docs/BACKLOG.md)")
    ap.add_argument("--readme", default="README.md", help="ruta a README.md (default README.md)")
    ap.add_argument("--dry-run", action="store_true", help="no escribe; solo muestra qu\u00e9 har\u00eda")
    ap.add_argument("--audit", action="store_true", help="tras editar, lista headings duplicados")
    args = ap.parse_args()

    print("== update_docs_day184.py ==")
    if args.dry_run:
        print("   (modo dry-run: no se escribir\u00e1 nada)\n")

    print("[BACKLOG] %s" % args.backlog)
    ok_b = process(args.backlog, update_backlog, EXPECTED_UNIQUE_BACKLOG, args.dry_run, args.audit, "BACKLOG")
    print("\n[README] %s" % args.readme)
    ok_r = process(args.readme, update_readme, EXPECTED_UNIQUE_README, args.dry_run, args.audit, "README")

    print("\n== resultado: %s ==" % ("OK" if (ok_b and ok_r) else "CON ERRORES"))
    sys.exit(0 if (ok_b and ok_r) else 1)


if __name__ == "__main__":
    main()