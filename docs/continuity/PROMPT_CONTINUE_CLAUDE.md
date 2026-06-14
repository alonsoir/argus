# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 184 → DAY 185

**Repo:** `/Users/aironman/CLionProjects/test-zeromq-docker`
**Branch:** `feature/day183-kuzu-sink-unwind-flush`
**Tag activo:** `v1.0.0-day166` · **Keypair efímero:** regenera en cada EMECAS
**Sesión:** madrugada (~4–6 AM), Badajoz.

---

## 0. EJE NO NEGOCIABLE (no perder nunca de vista)

**¿Pueden los modelos ensemble aprender de la experiencia acumulada de nodos distribuidos?**
Se publica salga **corroborada o seca** la hipótesis. Condición de validez innegociable:
**split MITRE disjunto** (entrenar en técnicas A–M, evaluar en N–Z) por ADR-040/ADR-057 §7.
Todo lo que se construye estos días es **"suelo que protege la medición"**, no production-readiness.

---

## 1. INVARIANTES DE TRABAJO (romperlos rompe la sesión)

- **Construir SIEMPRE con `make <target>` desde el host macOS.** Nunca `cmake -S . -B build` directo
  (riesgo de `.pb.h` rancio + se salta `-Werror`). Nunca envolver `make` en `vagrant ssh -c`
  (el binario `vagrant` no existe en el guest; el Makefile ya hace `vagrant ssh -c` por dentro).
- **EMECAS** = `vagrant destroy -f && vagrant up && make bootstrap && make test-all`.
- **BD Kuzu en `/tmp` guest-nativo** (vboxsf rompe el `mmap`).
- **Ediciones de fichero en macOS por heredoc Python3** — nunca `sed -i` sin `-e ''`.
- **Dos commits por día**: código y docs separados.
- **Makefile = única fuente de verdad.** `-Werror` invariante permanente, 0 warnings.
- Principios: *medir, no votar* · *Via Appia Quality* · *piano piano* · honestidad científica.

---

## 2. HECHO EN DAY 184 (cerrado)

Endurecimiento del **contrato de durabilidad del sink** + síntesis del Consejo (8/8) del banco
de tortura del DAY 185.

- **flush()→FlushResult (commit `4e221ede`).** `IGraphSink::flush()` deja de devolver `void`
  (ocultaba el fallo de durabilidad) → POD `[[nodiscard]] FlushResult {bool ok; uint64_t
  rows_flushed; uint64_t rows_pending; explicit operator bool}`. `[[nodiscard]]` sobre el **TIPO**,
  no sobre cada método → ningún sink presente ni futuro puede descartar el fallo bajo `-Werror`
  (cierre **estructural**, mismo espíritu que H-1: tipado, no `esc()`). `main.cpp:134` → flush
  fallido = `EXIT_FAILURE` (el harness E2E no lee "ok" sobre datos perdidos). 8 touchpoints de
  `IGraphSink` revisados por grep, cero fuga a ml-detector/firewall/etc.
- **KuzuGraphSink batch (commit `112b9df1`).** `write()` acumula (copia `CorrelationRecord` +
  `flow_uid` materializado + `ingested_at` sellado a la entrada). `flush()` ejecuta el batch en
  UNA transacción (`BEGIN`/loop `execute(prepared)`/`COMMIT`, `ROLLBACK`+buffer retenido en fallo).
  **Cierra H-1 en el path EJECUTADO de Kuzu** (`execute(prepared, params)`, no `query(string)`).
  Orden de miembros `db_→conn_→prep_*→accumulator_` por RAII; el destructor grita si el buffer no
  está vacío.
- **VERIFY-3 (test-only).** Dos tests gemelos: mismas N filas, solo cambia COMMIT vs ROLLBACK.
  COMMIT→2 nodos durables, ROLLBACK→0. Prueba que `BEGIN/COMMIT` por string envuelve los
  `execute(prepared)` en 1 transacción = 1 checkpoint por batch. Baseline `test_kuzu_graph_sink`
  0.48s→0.86s (contabilizado). 6/6 verde.
- **3 lecciones del header Kuzu 0.11.3** (verificadas contra `/usr/local/include/kuzu.hpp`):
  (1) control transaccional por string, no método tipado; (2) `execute(prepared, pair<string,
  Args>...)` variádico; (3) `common::Value` sin ctor desde `string_view` → materializar texto a
  `std::string`; el header documenta el SIGSEGV de DAY 183 (`preventTransactionRollbackOnDestruction`).
- **Consejo de Sabios (8/8)** revisó las 5 decisiones del banco de tortura → aprobadas con
  condiciones de validez (ver §3).
- **Docs DAY 184** volcadas con `update_docs_day184.py` (BACKLOG + README a DAY 184, idempotente,
  con backup y verificación de marcadores únicos).

---

## 3. FIRME PARA DAY 185 (destilado de los 8 modelos + arbitraje)

- **CSV bronce de la tortura en `/dev/shm` (tmpfs), no disco físico.** Escribir a disco sustituye
  el cuello del NIC por el del VFS/page-cache y mete contención de write-lock con los COMMIT de
  Kuzu → medirías I/O, no el pipeline. Misma lógica que "BD en /tmp, no vboxsf".
  → `DEBT-BRONZE-TORTURE-TMPFS-001`.
- **Test de equivalencia B sobre fuzzer de protobuf (1M iteraciones)**, no caso único. Además
  validar el **dominio de los campos enum-derivados** (col 17 `authoritative_source`): el injector
  no debe poder emitir un símbolo que el enum protobuf jamás produciría.
- **Injector adversarial = contenido + forma del stream:**
    - contenido: H-1 strings, `temporal_anomaly`, colisiones `flow_uid`, ráfagas (flush inline),
      volumen (desbordar acumulador);
    - topología: **nodo-estrella / alta cardinalidad** (un `node_id`, 10^6 aristas = scan nmap real);
    - forma: **línea truncada** (append no-atómico), **HMAC válido sobre contenido en frontera**
      (19→18 cols, campo vacío que no debe), **duplicado exacto con contador** (MERGE deduplica → si
      el banco cuenta 2 y el grafo 1, la métrica de pérdida va a negativo), **out-of-order causal**.
      → `DEBT-INJECTOR-ADVERSARIAL-BRONZE-001`.
- **`libcorrelation_v1` PURA** (struct `CorrelationV1Row` + `build_row`, CERO `LogReader`/
  `ZmqPublisher`/`FileWatcher`). Se justifica por DOS consumidores reales (ml-detector + injector),
  NO por el `argus-adapter-producer` hipotético (lectura+transporte ≠ serialización-desde-struct).
  → `DEBT-LIBCORRELATION-V1-EXTRACT-001`.
- **HMAC por env var compartida** (`ARGUS_BRONZE_HMAC_KEY_HEX`), nunca hardcode, nunca `--skip-hmac`.
  Ausencia de clave = error ruidoso. Cero acople nuevo con `DEBT-BRONZE-KEY-PROVISIONING-001`.
- **Caudal objetivo de producción: BLOQUEADO POR HARDWARE.** El "suelo suficiente" relativo (10×)
  necesita un número (eventos/seg, Mb/s de una RPi) que **no se inventa desde la silla** — espera a
  las Raspberries. La primera tortura mide **pérdida absoluta** (rows-in vs nodos-materializados =
  0 o no), criterio binario válido sin el target. → `BACKLOG-THROUGHPUT-TARGET-001`.
- **Drift de contrato protobuf:** un campo nuevo toca reader+writer+roundtrip+fuzzer+col17-drift a
  la vez — es una clase, no un test. → `DEBT-CONTRACT-DRIFT-PROTOBUF-001`.

### Orden de trabajo DAY 185
1. Extraer `CorrelationWriter` → `libcorrelation_v1` (Opción B): struct plano + `build_row`, lib
   pura. Equivalencia byte-idéntica `event→row→build_row(row)` vs `build_row(event)` **sobre fuzzer
   1M** + validación de dominio de enums.
2. Construir el **injector adversarial** (`tools/`, tercer hermano de la familia de stress-testers).
3. **Primera tortura:** injector → bronce en `/dev/shm` → `correlation-engine --follow` → Kuzu.
   Medir: rows-in vs nodos-materializados (pérdida), RSS acotado, staleness. Etiqueta honesta:
   "pipeline de cómputo, sin red".

---

## 4. FRENTES ABIERTOS (arrastrados)

- **D3** (Arrow/C++ solo vs +DuckDB para joins silver→gold) — ABIERTO. ADR-057 §2.7/§3.2. La
  primera tortura es el camino crítico antes de B2 (Arrow vs DuckDB).
- **Frente C — event_id replay-stable.** `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1): verificar si
  el path de PRODUCCIÓN heredó el reloj inyectado del build de cross-check (`bpf_ktime_get_ns`).
- **`kTemporalMarginNs` = 2s placeholder** — calibrar.
- **ADR-057 §8 (endurecimiento DIFERIDO)** = un solo problema = cola hacia un único writer de tasa
  fija → subsistema `IngestQueue` (WAL durability real, poison/atomicidad, backpressure sostenido).
  No es camino crítico del experimento.
- **`DEBT-GRAPH-ENGINE-EXTRACTION-001`** — extraer clases de grafo de `correlation-engine` a
  `graph-engine` cuando se materialice la frontera Iceberg.
- **`DEBT-SEMGREP-CPP-HANG-001`** — `audit-taint` en cuarentena.
- **Higiene BACKLOG:** ~7 headings duplicados preexistentes (no introducidos hoy; el script de docs
  no los toca, los lista con `--audit`).

---

## 5. RECORDATORIOS DE PROCESO

- Consejo de Sabios = 8 modelos (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) como
  peer review adversarial. Brief → 8 respuestas → síntesis (señal vs ruido) → arbitraje Alonso.
- La síntesis del DAY 184 separó ruido (`--skip-hmac`, clave hardcodeada, "SQL injection" mal
  categorizada) de señal (tmpfs, fuzzer protobuf, nodo-estrella, librería pura).
- **El riesgo de este plan no es construir mal — es etiquetar mal lo que mides.** Para un proyecto
  cuyo eje es "se publica salga como salga", la **precisión del claim es el producto**.