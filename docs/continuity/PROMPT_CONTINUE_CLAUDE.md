# PROMPT DE CONTINUIDAD — DAY 225 (continúa DAY 223-224)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** NO concluir "X no existe" desde un `sed -n`,
  un `head` o un grep con filtro estrecho. Aplica también a los barridos de Claude: leer las
  primeras 2000 líneas de un fichero de 87 MB es un `head` disfrazado. Fichero entero antes
  de afirmar ausencia.
- **Lección DAY 223 (el grep que costó una noche):** `grep -rn <patrón> .` desde la raíz
  arrastra `build/`, `.git/`, `.venv/`, `vendor/` y **tarda horas**. **Usar `git grep`** o
  acotar con `-- ruta/`. Y **nunca encadenar dos comandos de salida grande**: el segundo se
  come la salida del primero.
- **Lección DAY 223 (convención del BACKLOG):** ninguna deuda vive en fichero propio. Todas
  son secciones `###` dentro de `docs/BACKLOG.md` (>5400 líneas). Que no exista `DEBT-XXX.md`
  NO significa que la deuda no exista.
- **Lección DAY 224 (el número que nadie midió):** el "24 campos" del BACKLOG llevaba desde
  DAY 207 sin que nadie lo comparase con el código. Era CIERTO — del diseño — y la
  implementación salió con 22. Un número copiado de un revisor a una entrada y de ahí a la
  verdad. Antes de propagar una cifra al paper, medirla.
- **Lección DAY 224 (constructos que no distinguen "hizo" de "no hizo"):** `sed -i` devuelve 0
  aunque no sustituya nada → un `sed ... || fallback` tiene el fallback muerto. Igual que el
  `||` del Makefile. Toda activación de opción lleva verificación ruidosa detrás.
- **Lección DAY 222 (parches idempotentes):** anclar el `assert` contra el texto que se va a
  insertar, NO contra el punto de inserción.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable;
  Kuzu = proyección reconstruible por MERGE).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- macOS/zsh: comillas en globs, NUNCA `sed -i`, Python3 heredoc para editar.
  Commits/push desde el HOST. `git add` explícito por fichero, nunca `-u` ni `-a`.
- Rama ANTES del primer `git add`. Scripts scratch → `.gitignore` al crearlos.
- **Guardar SIEMPRE en la rama remota al cerrar sesión.** Los FS locales fallan.
- Un día, una batalla.

---

## Contexto estratégico (vigente desde DAY 223)

**Ya NO se presenta nada ante Andrés ni ante FEDER.** El propósito original era entregar un
pipeline capaz de producir datasets de calidad, ser analizador fiable y generar árboles ensemble
que reconocieran ataques nuevos. Eso exige modelos muy superiores a los que hay, y por esta línea
de investigación no somos capaces de producirlos (techo medido 0.65–0.70; PROBE 0: recall 0.81,
AUC 0.746 in-sample).

**Objetivo actual:** cerrar el pipeline lo mejor posible — añadiendo al grafo las señales del
resto de componentes — y escribir el paper de la forma más honesta y científica posible,
mostrando los datos, para que en el futuro alguien pueda retomar la investigación y producir
modelos ensemble fiables (>90% sobre ataques reales, por comportamiento).

Fin de proyecto: 31-ago / primera semana de septiembre, repositorio en modo lectura.

### Plan de cierre en 6 pasos
1. Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo.  ← EN CURSO
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado — rama `feat/suricata-to-graph` (desde main fb08e8f6)

### Arquitectura (firme, DAY 222)
**SIN switches en ningún JSON. Dirigido por datos:** si los ficheros del contrato
`correlation_v1` de cualquier componente llegan al bronce, el grafo los usa. El arranque de cada
componente vive fuera del engine (Makefile + Vagrant).
**Separación estricta de feeds:** el ml-detector controla EN EXCLUSIVA el feed de aRGus. Suricata
tendrá su PROPIO JSON, con `base_dir` al mismo buzón plano y `source_sensor="suricata"`. Nunca se
toca la config interna de Suricata. Igual Zeek y Wazuh.

### Circuito medido
sensor → CSV bronce (19 cols, HMAC por fila) → [inotify `IN_MOVED_TO`, watcher NO recursivo]
→ `bronze_to_gold_converter` (env `ARGUS_BRONZE_HMAC_KEY_HEX`) → bronce AVRO (copia exacta) +
oro Parquet (22 cols) → `parquet_to_kuzu_loader` → `KuzuGraphSink` → MERGE.
El upsert está en el GRAFO, no en el Parquet. Oro = ledger append-only.

### Hecho en DAY 223-224
- `file_pattern` **borrado** (campo muerto: se parseaba, nadie lo leía). 9/9 verde sobre árbol
  limpio con `make correlation-engine-clean && make correlation-engine-test`.
- 3 deudas nuevas en `BACKLOG.md` (sección DAY 223): `DEBT-MAKEFILE-TEST-GATE-MASKED-001`,
  `DEBT-MLDETECTOR-TESTS-NOT-BUILT-001`, `DEBT-GRAPH-SCHEMA-MULTISENSOR-001`.
- Sección DAY 224: `DEBT-PROVISION-SED-SILENT-NOOP-001` + inventario de Suricata.
- Corregidas dos líneas obsoletas de `DEBT-ARGUSPP-COMMUNITY-ID-001` (estado y policy de Zeek).

---

## Lo medido en DAY 224 (no repetir)

**Contrato: 24 diseñadas, 22 implementadas.** El diseño del Eslabón 1 define hasta la col 23:
0-18 bronce + 19 `flow_start_window` + 20 `seq_in_window` + 21 `flow_uid` + **22 `ingested_at`**
+ **23 `temporal_anomaly`**. El converter escribe 22. Las dos que faltan son clase E (las deriva
el converter, no el sensor) y están cubiertas por `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`.

**Suricata, barrido completo (211.136 eventos):** `alert` 2.762 (1,3%), el resto telemetría
(`dns` 169.140, `flow` 34.692, `http` 2.810…). `community_id` **no aparece ni una vez** en esos
logs — son del banquillo `experiments/`, con el `sed` sin verificar. La configuración correcta SÍ
existe en el **Vagrantfile raíz** (Suricata 1169-1180: `community-id: yes` + `seed: 0` con echo
de verificación; Zeek 1245-1267).

**Cobertura de los 19 campos desde Suricata:** nuestros (`schema_version`, `source_sensor`,
`node_id`, `authoritative_source`, `hmac_row`) · directos (`src_ip`, `dest_ip`, `src_port`,
`dest_port`, `proto`) · config (`community_id`) · **`flow_start` de `flow.start`, NO del
`timestamp` del evento** · **sin contrapartida** los 5 de veredicto · `event_id` a acuñar.

---

## Plan DAY 225
1. **`vagrant up suricata`** (VM del Vagrantfile raíz, hoy *not created*). Verificar en la VM
   que `community-id: yes` y `community-id-seed: 0` quedaron puestos de verdad en
   `/etc/suricata/suricata.yaml` — no fiarse del provisioning, mirar el YAML.
2. **Generar tráfico y capturar** un `eve.json` con `community_id`. Diana E2E conocida:
   `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` sobre flujo Neris `147.32.84.165:1027 → 74.125.232.195:80`.
3. **Medir sobre esa captura**, no sobre la vieja: presencia de `community_id`, y si `flow.start`
   aparece en los eventos de tipo `alert` o solo en los de tipo `flow` (decide si el adapter
   necesita correlacionar dos eventos para componer una fila del contrato).
4. **Escribir la puerta de diseño** (documento, no código): tabla campo × sensor, decisión sobre
   los 5 campos de veredicto sin contrapartida, y decisión de `event_id`.
5. Pendientes que NO bloquean: EMECAS+++ y PR de esta rama · rama aparte `fix/test-gate-masked` ·
   nota recíproca en `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (5138) apuntando a la del grafo.

### Bloqueantes antes de escribir una línea del adapter
- **`event_id` es PK de `Alert`.** El de Suricata no puede colisionar con el de aRGus: un `MERGE`
  machacaría el evento del otro sensor **sin error y sin traza**.
- **`flow_start` divergente rompe el `flow_uid`** y con él la convergencia al mismo `NetworkFlow`.
- **Los 5 campos de veredicto no tienen contrapartida.** Rellenarlos con centinelas contamina el
  grafo con un veredicto que Suricata nunca emitió. Decisión de diseño, no de código.
- `CREATE NODE TABLE IF NOT EXISTS` **NO migra catálogos Kuzu existentes**.
- HMAC multi-productor → `DEBT-BRONZE-HMAC-KEY-POLICY-001` + `DEBT-SECRETS-MANAGER-PERSISTENCE-001`.

## Punteros (re-verificar al abrir)
- `docs/design/eslabon-1-flujo-a-avro-parquet/eslabon-1-flujo-a-avro-parquet.md` — tabla nominal
  de las 24 columnas. **Léelo entero al abrir DAY 225**: es también la plantilla de cómo se lleva
  un CSV al grafo, y por tanto el modelo para el resto de sensores.
- `correlation-engine/tools/bronze_to_gold_converter.cpp:323-344` — los 22 `arrow::field`.
- `correlation-engine/schema/schema.cypher` — NetworkFlow (identidad pura) / Alert /
  TelemetryEvent (con `source_sensor`). `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`.
- `correlation-engine/src/kuzu_graph_sink.cpp` — `exec_row`, 15 params.
- `tools/community_id_crosscheck.py` — lee `/var/log/suricata/eve.json` y
  `/vagrant/logs/lab/zeek/conn.log` (rutas de VM, NO `logs/experiment/`).
- Vagrantfile raíz: cinco VMs — defender (running), client, suricata, zeek, wazuh (*not created*).
- `DEBT-HOST-DOMAIN-CONTRACT-001` (BACKLOG:4714) — Wazuh es dominio host, contrato propio
  `host_domain_v1`, separado de `correlation_v1`. El contrato NUNCA fue universal para los cuatro.
- Paper arXiv:2604.04952 — reescritura honesta pendiente.

## Comandos útiles
make correlation-engine-test        # HOST. Depende de -build: rm -rf build + cmake + ctest
make ml-detector                    # incremental
git grep -n '<patrón>' -- <ruta>/   # NUNCA grep -rn desde la raíz
vagrant up suricata                 # VM del Vagrantfile raíz

## Ritmo
DAY 224 no produjo casi código y fue de los días más productivos: dirimió un número que llevaba
17 días mintiendo en el BACKLOG, encontró dos campos diseñados y nunca implementados, descubrió
que los logs de Suricata que dábamos por buenos no tienen la clave de unión, y localizó un `sed`
que no puede fallar. Todo por preguntar "¿seguro que los campos de aRGus son los de Suricata?"
— la pregunta la hizo Alonso, no la máquina.

*Via Appia Quality — medir quién habla, no solo qué dice. Y medir el número antes de escribirlo.*
