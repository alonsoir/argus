# PROMPT DE CONTINUIDAD — DAY 223 (continúa DAY 222)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** NO concluir "X no existe" desde un `sed -n`,
  un `head -30` o un `grep` con filtro estrecho. Se pisó DOS veces en DAY 222 (un
  `head -30` comido por Avro; un `find` mal leído que "demostró" que no había VM de
  Wazuh — sí la hay). Grep completo antes de afirmar ausencia.
- **Lección DAY 222 (parches idempotentes):** un parche Python cuyo `assert count == 1`
  se ancla en el PUNTO DE INSERCIÓN y no en el RESULTADO duplica la línea al relanzarlo,
  sin quejarse. Anclar contra el texto que se va a insertar.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable;
  Kuzu = proyección reconstruible por MERGE).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- **Consejo de Sabios** ratifica decisiones de arquitectura.
- macOS/zsh: comillas en globs, NUNCA `sed -i`, Python3 heredoc para editar.
  Commits/push desde el HOST. `git add` explícito por fichero, nunca `-u` ni `-a`.
- Rama ANTES del primer `git add`. Scripts scratch → `.gitignore` al crearlos.
- **Guardar SIEMPRE en la rama remota al cerrar sesión.** Los FS locales fallan.
- Un día, una batalla.

---

## Contexto estratégico (decisión DAY 221, vigente)
aRGus se **DESACTIVA como clasificador**. Techo medido 0.65–0.70 (PROBE 0: recall 0.81,
AUC 0.746 in-sample) — inaceptable para hospital. Se completa el pipeline aguas abajo
para que funcione el **grafo Suricata/Zeek/Wazuh unido por `community_id`** con ground
truth externo. El paper se reescribe super-honesto. Fin de proyecto: 31-ago / primera
semana de septiembre, repositorio en modo lectura.

### Plan de cierre en 6 pasos
1. Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo.  ← EN CURSO
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

**Pendiente personal:** escrito para el Consejo (informe + agradecimiento); Alonso informa a Andrés.

---

## Estado al cierre de DAY 222 — rama `feat/suricata-to-graph` (desde main fb08e8f6)

### DECISIÓN DE ARQUITECTURA (firme)
**SIN switches en ningún JSON. Diseño dirigido por datos:** si los ficheros del contrato
`correlation_v1` de cualquier componente llegan al bronce, el grafo los usa para
actualizarse. El arranque de cada componente sigue fuera del engine (Makefile + Vagrant).
*Descartada* la idea previa de un JSON-interruptor que levantase procesos: mezclaba plano
de control y plano de datos.

**Separación estricta de feeds (ratificada):** el ml-detector controla EN EXCLUSIVA el feed
de aRGus y su config no menciona ningún otro sensor. El feed de Suricata tendrá su PROPIO
JSON, con su `base_dir` al mismo buzón y su propia constante `source_sensor="suricata"`.
Nunca se toca la config interna de Suricata. Igual para Zeek y Wazuh.

### CIRCUITO MEDIDO (no recordado — corrige varios recuerdos falsos)
sensor → CSV bronce (correlation_v1, 19 cols, HMAC por fila)
→ [inotify IN_MOVED_TO — NO ZeroMQ]
→ bronze_to_gold_converter (Flujo A, DAY 205; CLI 3 args;
requiere env ARGUS_BRONZE_HMAC_KEY_HEX)
├─ bronce AVRO (cols 0-18, copia exacta — bronce PRESERVA)
└─ oro Parquet (cols 0-21: + flow_start_window, seq_in_window, flow_uid)
→ parquet_to_kuzu_loader (Flujo B, Eslabón 2, DAY 208)
→ KuzuGraphSink → MERGE (upsert) en Kuzu
- **AVRO sí existe.** **NO hay plano "silver"**: son dos, bronce y oro.
- **El upsert está en el GRAFO, no en el Parquet.** Oro = ledger append-only. Invariante intacto.
- **Semántica ideal para multi-sensor:** dos sensores con el mismo `flow_uid` convergen al
  MISMO nodo `NetworkFlow`, con un `Alert` cada uno colgando por `ALERT_ABOUT`. La
  correlación multi-sensor YA está diseñada; no hay que inventarla.

### TRABAJO HECHO HOY (3 commits, todo pusheado)
1. **`source_sensor` en el grafo.** Era el eslabón perdido: la col 1 viajaba íntegra por
   writer → lib → reader → Parquet → loader y **se caía al escribir el nodo**. Añadida a
   `Alert` y `TelemetryEvent` (NO a `NetworkFlow`: identidad pura, el flujo es compartido).
   RED→GREEN sobre `test_graph_sink_loop`. Suite correlation-engine **9/9 verde**.
   Ficheros: `schema.cypher`, `cypher_builder.hpp`, `kuzu_graph_sink.cpp` (14→15 params),
   `logging_graph_sink.hpp` (comentario fósil `:RAISED` retirado), `test_graph_sink_loop.cpp`.
2. **Prefijo de sensor + buzón plano.** `get_basename()` deriva el prefijo de
   `CORRELATION_SOURCE_SENSOR` (punto único con la col 1) → `argus-%Y-%m-%d-%H%M%S.csv`.
   `base_dir`/`root_dir` → `/vagrant/logs/correlation` (plano) en los DOS únicos JSON que
   cablean la ruta. **Motivo medido:** `BronzeDirWatcher` usa un solo `inotify_add_watch` y
   **NO es recursivo** → con subdirectorio por sensor, el engine no vería a Suricata.
   `make ml-detector` limpio con `-Werror`; `test_correlation_roundtrip` PASA.
3. Este prompt de continuidad.

### HALLAZGO GORDO — el gate de tests del ml-detector NO MIDE (arreglar DAY 223)
Dos defectos apilados:
- **(a) `DEBT-MAKEFILE-TEST-GATE-MASKED-001` (P1).** En `test-components`, cada componente
  termina en `|| echo "⚠️ No X tests configured"`. Ese `||` se traga el fallo: no distingue
  "no hay tests" de "los tests fallan". Afecta a **sniffer, ml-detector, rag-ingester,
  etcd-server, rag-security y firewall**. Solo `correlation-engine-test` escala de verdad
  (va como dependencia, sin `||`).
- **(b) `DEBT-MLDETECTOR-TESTS-NOT-BUILT-001` (P1).** De los **11** tests registrados con
  `add_test` en el ml-detector, **10 están en `Not Run`**: el ejecutable no existe en
  `build/tests`. No fallan — nunca se construyen. Son: `test_classifier`,
  `test_feature_extractor`, `test_rag_logger_artifact_save`, `test_model_loader`,
  `test_zmq_memory_overflow`, `RansomwareDetectorUnit`, `test_pipeline`,
  `test_csv_event_writer`, `test_csv_feature_extraction`, `test_etcd_client_hmac`.
  El único que sí corre es `test_correlation_roundtrip`.

**Consecuencia:** `test-all` —y por tanto EMECAS+++— lleva un tiempo indeterminado dando
verde con **un solo test de ml-detector corriendo de verdad**. Misma familia que
`DEBT-VERDICT-MONOCAPA-001`: un gate que parece medir y no mide.
**Para el paper:** cualquier afirmación tipo "la suite pasa" sobre el ml-detector necesita asterisco.

**Aviso antes de arreglarlo:** al construir esos 10, lo más probable es que salgan rojos
de verdad (deudas de ML ya conocidas y dadas por irrecuperables). NO dejar que eso bloquee
la rama de Suricata. Decidir explícitamente qué se arregla y qué se marca como known-red.

---

## Plan DAY 223
1. **Pieza 4: deudas al `docs/BACKLOG.md`.**
   - `DEBT-MAKEFILE-TEST-GATE-MASKED-001` (P1, nueva)
   - `DEBT-MLDETECTOR-TESTS-NOT-BUILT-001` (P1, nueva)
   - Deuda del **grafo** multi-sensor: `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` cubre el
     Parquet ORO, **no** el grafo. Registrar el hueco (parcialmente cerrado hoy con `source_sensor`).
   - `file_pattern` de `correlation_engine.json` es **campo muerto** y ahora miente más
     (declara `%Y-%m-%d.csv`, el writer produce `argus-%Y-%m-%d-%H%M%S.csv`). Corregir o borrar.
2. **Arreglar el gate de tests** (los dos defectos), con la cautela de arriba.
3. **EMECAS+++** completo → PR de `feat/suricata-to-graph`.
4. **Después, la puerta de diseño de Suricata:** `parquet_to_kuzu_loader` declara alcance v1
   mono-fuente y advierte explícitamente que NO se generalice sin pasar antes por
   `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` **+ su propia ronda de Consejo**. Eso es
   trabajo de escritura, no de código, y va antes del adapter.

### Cuestiones abiertas para el diseño del adapter de Suricata
- **HMAC (col 18).** Cada productor necesita firmar. ¿Firma cada adapter (distribución de
  clave a N productores) o firma un colector único al aterrizar (una sola clave, pero el
  bronce deja de ser "lo que emanó el sensor")? Afecta a la cadena de custodia.
  Toca `DEBT-SECRETS-MANAGER-PERSISTENCE-001` (P1, claves solo en memoria).
- **`event_id` es PK de `Alert`.** El de Suricata NO puede colisionar con el de aRGus o un
  `MERGE` machacaría el evento del otro sensor.
- **`CREATE NODE TABLE IF NOT EXISTS` NO migra catálogos Kuzu existentes.** Una BD
  persistida de antes del cambio de hoy necesita recrearse. Tests y EMECAS+++ no lo
  detectan (parten de base fresca / VM destruida).

## Punteros (medidos DAY 222 — re-verificar al abrir)
- `correlation-engine/schema/schema.cypher` — NetworkFlow (identidad pura) / Alert /
  TelemetryEvent (ambos con veredicto + `source_sensor`) / CORRELATES_FLOW / ALERT_ABOUT /
  TELEMETRY_ABOUT. `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`.
- `correlation-engine/include/correlation_engine/cypher_builder.hpp` — `make_bindings()` es
  la FUENTE ÚNICA de derivados; 2 plantillas parametrizadas + `build_cypher` (solo logging).
- `correlation-engine/src/kuzu_graph_sink.cpp` — `exec_row`, 15 params.
- `correlation-engine/src/bronze_dir_watcher.cpp` — inotify NO recursivo, `IN_MOVED_TO`.
- `ml-detector/src/correlation_writer.cpp` — `get_basename()` (~192), `ensure_open()` (~199).
- `ml-detector/include/correlation_writer.hpp:46` — `CORRELATION_SOURCE_SENSOR = "argus"`.
- Vagrantfile raíz: **cinco VMs** — defender (running), client, suricata, zeek, wazuh
  (las cuatro *not created*). La topología multi-sensor ya está declarada.
- Logs ya capturados: `logs/experiment/suricata-*/eve.json`, `logs/experiment/zeek/*`.
- `tools/community_id_crosscheck.py` — paridad `community_id` validada E2E contra Suricata+Zeek.
- Paper arXiv:2604.04952 — reescritura honesta pendiente.

## Comandos útiles
make correlation-engine-build                 # rm -rf build: reconstruye entero
vagrant ssh -c 'cd /vagrant/correlation-engine/build && 
make -j4 <target> && ctest -R <target> --output-on-failure'
make ml-detector                              # incremental
vagrant ssh -c 'cd /vagrant/ml-detector/build && ctest --output-on-failure'
## Ritmo
DAY 222: 07:30–10:00, dos horas y media de trabajo limpio y sin baches. La sesión empezó
con un prompt de continuidad obsoleto (DAY 211 congelado en main) y acabó con tres piezas
medidas, commiteadas y pusheadas, más dos deudas nuevas encontradas por el método de
siempre: mirar el binario en vez del banner. El hallazgo del gate enmascarado no es un
revés — es la vigilancia funcionando otra vez, a seis semanas del cierre. Ritmo real
marcado por el cuidado familiar y las ventanas de crédito.

*Via Appia Quality — medir quién habla, no solo qué dice. Un grafo que sabe de qué sensor
viene cada señal.*
