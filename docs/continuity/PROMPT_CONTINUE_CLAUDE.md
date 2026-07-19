# PROMPT DE CONTINUIDAD — DAY 224 (continúa DAY 223)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** NO concluir "X no existe" desde un `sed -n`,
  un `head -30` o un grep con filtro estrecho. Grep completo antes de afirmar ausencia.
- **Lección DAY 223 (el grep que costó una noche):** `grep -rn <patrón> .` desde la raíz
  arrastra `build/`, `.git/`, `.venv/`, `vendor/` y **tarda horas**. Se dejó uno corriendo
  toda una noche sin terminar. **Usar `git grep`** (solo ficheros trackeados, respeta
  .gitignore) o apuntar al directorio concreto con `-- ruta/`. Y **nunca encadenar dos
  comandos de salida grande**: el segundo se come la salida del primero en el terminal.
- **Lección DAY 223 (convención del BACKLOG):** en este repo **ninguna deuda vive en fichero
  propio**. Todas son secciones `###` dentro de `docs/BACKLOG.md` (>5300 líneas). Que no
  exista `DEBT-XXX.md` NO significa que la deuda no exista.
- **Lección DAY 222 (parches idempotentes):** un parche Python cuyo `assert count == 1`
  se ancla en el PUNTO DE INSERCIÓN y no en el RESULTADO duplica la línea al relanzarlo.
  Anclar contra el texto que se va a insertar.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable;
  Kuzu = proyección reconstruible por MERGE).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- macOS/zsh: comillas en globs, NUNCA `sed -i`, Python3 heredoc para editar.
  Commits/push desde el HOST. `git add` explícito por fichero, nunca `-u` ni `-a`.
- Rama ANTES del primer `git add`. Scripts scratch → `.gitignore` al crearlos.
- **Guardar SIEMPRE en la rama remota al cerrar sesión.** Los FS locales fallan.
- Un día, una batalla.

---

## Contexto estratégico (actualizado DAY 223 — LEER, cambió el marco)

**Ya NO se va a presentar nada ante Andrés ni ante FEDER.** El propósito original era
entregar un pipeline capaz de (a) producir datasets de calidad, (b) ser analizador fiable
de ataques y (c) producir árboles ensemble que reconocieran ataques nuevos. Eso exige
modelos ensemble muy superiores a los que hay, y **por esta línea de investigación no somos
capaces de producirlos** (techo medido 0.65–0.70; PROBE 0: recall 0.81, AUC 0.746 in-sample).

**Objetivo actual:** cerrar el pipeline lo mejor posible — terminarlo añadiendo al grafo el
resto de señales de los demás componentes — y escribir el paper de la forma más honesta y
científica posible, mostrando los datos, para que en el futuro alguien (o nosotros) pueda
retomar la investigación y producir modelos ensemble fiables que clasifiquen ataques reales
por comportamiento con eficacia >90%.

Fin de proyecto: 31-ago / primera semana de septiembre, repositorio en modo lectura.

### Plan de cierre en 6 pasos
1. Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo.  ← EN CURSO
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado al cierre de DAY 223 — rama `feat/suricata-to-graph` (desde main fb08e8f6)

### DECISIÓN DE ARQUITECTURA (firme, DAY 222)
**SIN switches en ningún JSON. Diseño dirigido por datos:** si los ficheros del contrato
`correlation_v1` de cualquier componente llegan al bronce, el grafo los usa. El arranque de
cada componente sigue fuera del engine (Makefile + Vagrant).

**Separación estricta de feeds:** el ml-detector controla EN EXCLUSIVA el feed de aRGus.
Suricata tendrá su PROPIO JSON, con `base_dir` al mismo buzón plano y su propia constante
`source_sensor="suricata"`. Nunca se toca la config interna de Suricata. Igual Zeek y Wazuh.

### CIRCUITO MEDIDO
sensor → CSV bronce (`correlation_v1`, HMAC por fila)
→ [inotify IN_MOVED_TO — NO ZeroMQ, watcher NO recursivo]
→ `bronze_to_gold_converter` (Flujo A; CLI 3 args; env `ARGUS_BRONZE_HMAC_KEY_HEX`)
  ├─ bronce AVRO (copia exacta — bronce PRESERVA)
  └─ oro Parquet (+ `flow_start_window`, `seq_in_window`, `flow_uid`)
→ `parquet_to_kuzu_loader` (Flujo B) → `KuzuGraphSink` → MERGE (upsert) en Kuzu
- **El upsert está en el GRAFO, no en el Parquet.** Oro = ledger append-only.
- **Semántica multi-sensor ya diseñada:** dos sensores con el mismo `flow_uid` convergen al
  MISMO nodo `NetworkFlow`, con un `Alert` cada uno por `ALERT_ABOUT`.

### TRABAJO DE DAY 223 (1 commit de contenido + este prompt)
**Pieza 4 cerrada.**
- `file_pattern` **borrado** de `correlation_engine.json`, `config_loader.hpp` y
  `config_loader.cpp`. Medido con `git grep`: se parseaba pero **nadie leía**
  `cfg.bronze.file_pattern`. No era solo un campo que mentía — era un campo que mentía y
  que nadie escuchaba. El bronce se localiza por directorio, no por patrón.
  Verificado con `make correlation-engine-clean && make correlation-engine-test`
  (árbol limpio, reconstrucción entera) → **9/9 verde**.
- Tres entradas nuevas al final de `docs/BACKLOG.md`, sección `## 🆕 Entradas DAY 223`:
  `DEBT-MAKEFILE-TEST-GATE-MASKED-001`, `DEBT-MLDETECTOR-TESTS-NOT-BUILT-001`,
  `DEBT-GRAPH-SCHEMA-MULTISENSOR-001`.
- `.gitignore`: `temporal.md`, `tools/temporal.md`.

**Hallazgo lateral:** `DEBT-BRONZE-HMAC-KEY-POLICY-001` (BACKLOG.md:566) **ya cubre** la
cuestión del HMAC multi-productor. No hay que crear deuda nueva para eso — hay que
referenciarla y actualizarla cuando llegue el adapter.

---

## 🔴 MEDICIÓN PENDIENTE — ¿19, 22 o 24 campos?

`DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (BACKLOG.md:5138) describe `correlation_v1` como
**24 campos**. Lo medido en DAY 222 es **19 columnas** en el CSV bronce (0-18) y **22** en el
oro (0-21). **Nadie sabe cuál es cierto.** Duda concreta de Alonso: lo que se guarda a Avro
es lo que viene en CSV, pero ¿el Parquet se genera **tal cual** desde el Avro o **añade**
campos? **No propagar ningún número a ningún sitio (ni al paper) hasta medirlo.**

Sitios donde mirar (con `git grep`, no con grep recursivo):
- el serializador de `libcorrelation_v1` — cuántas columnas escribe realmente
- el esquema Avro (¿`.avsc` embebido o construido en código?)
- el esquema Arrow/Parquet en `bronze_to_gold_converter.cpp`
- si aparece un 24 en algún sitio, dirimir si es el **protobuf** (que sí puede tener campos
  que no viajan al CSV) o un número fósil de DAY 207.

Al cerrar: corregir la entrada 5138 con el número medido y añadir allí la línea recíproca
que apunta a `DEBT-GRAPH-SCHEMA-MULTISENSOR-001` (pendiente de DAY 223, diff aparte).

---

## Plan DAY 224
1. **Medir los campos** (arriba). Es barato y desbloquea el paper y la entrada 5138.
2. **EMECAS+++ completo → PR de `feat/suricata-to-graph`.** La rama parte de un main que
   pasó EMECAS+++ y solo añade `source_sensor` al grafo, prefijo de sensor, bronce plano,
   borrado de campo muerto y documentación. **No se espera rojo.**
3. **Rama aparte `fix/test-gate-masked`** para los dos defectos del gate. Va SEPARADA a
   propósito: al construir los 10 tests del ml-detector lo más probable es que salgan
   **rojos de verdad** (deudas ML dadas por irrecuperables). Ahí el rojo es información, no
   un bloqueo. Decidir explícitamente qué se arregla y qué se marca **known-red** con ID.
4. **Después, la puerta de diseño de Suricata:** `parquet_to_kuzu_loader` declara alcance v1
   mono-fuente y advierte que NO se generalice sin `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`
   + ronda de Consejo. Es trabajo de **escritura**, no de código, y va antes del adapter.

### Bloqueante que hay que resolver antes de escribir una sola línea del adapter
**Colisión de `event_id`.** Es PK de `Alert`. El `event_id` de Suricata no puede colisionar
con el de aRGus: un `MERGE` machacaría el evento del otro sensor **sin error y sin traza**.
No es un hueco de diseño, es pérdida de datos silenciosa desde la primera fila. Decidir
esquema (namespacing `sensor:uid` vs hash compuesto). Ver `DEBT-EVENT-ID-FACTORY-001`.

### Otros abiertos
- `CREATE NODE TABLE IF NOT EXISTS` **NO migra catálogos Kuzu existentes**. Una BD de antes
  de DAY 222 no tiene `source_sensor` y necesita recrearse. Tests y EMECAS+++ NO lo detectan
  (parten de base fresca / VM destruida).
- HMAC del bronce multi-productor → `DEBT-BRONZE-HMAC-KEY-POLICY-001` +
  `DEBT-SECRETS-MANAGER-PERSISTENCE-001`.

## Punteros (re-verificar al abrir)
- `correlation-engine/schema/schema.cypher` — NetworkFlow (identidad pura) / Alert /
  TelemetryEvent (ambos con veredicto + `source_sensor`) / CORRELATES_FLOW / ALERT_ABOUT /
  TELEMETRY_ABOUT. `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`.
- `correlation-engine/include/correlation_engine/cypher_builder.hpp` — `make_bindings()` es
  la FUENTE ÚNICA de derivados.
- `correlation-engine/src/kuzu_graph_sink.cpp` — `exec_row`, 15 params.
- `correlation-engine/src/bronze_dir_watcher.cpp` — inotify NO recursivo, `IN_MOVED_TO`.
- `ml-detector/include/correlation_writer.hpp:46` — `CORRELATION_SOURCE_SENSOR = "argus"`.
- Vagrantfile raíz: **cinco VMs** — defender (running), client, suricata, zeek, wazuh
  (las cuatro *not created*). La topología multi-sensor ya está declarada.
- Logs ya capturados: `logs/experiment/suricata-*/eve.json`, `logs/experiment/zeek/*`.
- `tools/community_id_crosscheck.py` — paridad `community_id` validada E2E.
- Paper arXiv:2604.04952 — reescritura honesta pendiente.

## Comandos útiles
make correlation-engine-test        # HOST. Depende de -build: rm -rf build + cmake + ctest
make correlation-engine-clean       # HOST
make ml-detector                    # incremental
vagrant ssh -c 'cd /vagrant/ml-detector/build && ctest --output-on-failure'
git grep -n '<patrón>' -- <ruta>/   # NUNCA grep -rn desde la raíz

## Ritmo
DAY 223 arrancó con una discusión de orden de ramas y acabó con la Pieza 4 cerrada y dos
correcciones de método que valen más que el código: el `grep -rn` desde la raíz (una noche
perdida) y la suposición de que una deuda sin `.md` no existía — cuando el propio índice del
BACKLOG la tenía en la línea 5138. Las dos son la misma familia que el hallazgo del gate
enmascarado: creer que se ha medido cuando no se ha medido. El método aguanta porque el que
mide es Alonso, no la memoria.

*Via Appia Quality — medir quién habla, no solo qué dice. Y medir cuántos campos son, antes
de escribirlo en un paper.*
