═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 181 — aRGus NDR · branch feature/day170-community-id-protobuf
═══════════════════════════════════════════════════════════════════════════════
Prompt LEAN a propósito: estado + frentes + invariantes. El detalle vive en el repo.

> NOTA PARA CLAUDE: DAY 180 cerró el frente A (BACKEND KUZU real detrás de IGraphSink),
> VERDE (4/4 tests). Quedó MUCHA deuda anotada pero NO documentada en docs/BACKLOG.md
> todavía (Alonso se cayó de sueño tras el código). El frente NATURAL de hoy es
> DOCUMENTAR: volcar la deuda de abajo a docs/BACKLOG.md + refinar ADR-057 (borrador
> ya en docs/adr/) + actualizar README DAY-STATUS. NADA de esto pasó por el Consejo aún.
> PERO Alonso decide el frente al arrancar. No asumas; pregunta o mira su primer mensaje.

───────────────────────────────────────────────────────────────────────────────
QUÉ CERRÓ DAY 180 (hecho — verificar en commits antes de repetir)
───────────────────────────────────────────────────────────────────────────────
Frente A: BACKEND KUZU embebido real detrás de IGraphSink. 4/4 tests verdes.

- Kuzu v0.11.3 PROVISIONADO en el guest (Vagrantfile, bloque en all-dependencies):
  libkuzu.so → /usr/local/lib, kuzu.hpp/kuzu.h → /usr/local/include. NO hay .deb upstream;
  tarball de release GitHub, pin por SHA256 = e99f9671ebfacf4d6208aa4b94490016e4ac9be242deed1fea78afb31c058ebd.
  ⚠️ UPSTREAM ARCHIVADO (kuzudb archivó el repo 10-oct-2025; v0.11.3 = release final).
  Mitigado por la abstracción IGraphSink. Plan B = fork Vela-Engineering/kuzu.
- schema.cypher (correlation-engine/schema/): NetworkFlow IDENTIDAD PURA (flow_uid PK,
  node_id, community_id, flow_start_window, seq_in_window). Alert + TelemetryEvent
  ENRIQUECIDOS con veredicto (cols 12-17: final_classification, threat_category, 3 scores,
  authoritative_source). Aristas: CORRELATES_FLOW, ALERT_ABOUT, TELEMETRY_ABOUT (method,confidence).
  La 5-tupla NO va al grafo: vive en bronce + Parquet ORO (datasets salen de ORO, no del grafo).
- cypher_builder.hpp (NUEVO, header compartido): is_alert(r) := final_classification=="MALICIOUS"
  (predicado verificado en zmq_handler.cpp:438, el sink LEE el veredicto, no recalcula).
  build_cypher() emite el modelo nuevo: MERGE {pk} ON CREATE SET, 3 cláusulas en un statement
  (atómico por auto-commit). CRÍTICO: imbue(locale::classic()) en el stream → doubles con
  PUNTO decimal (el guest tiene locale es_ES → habría salido coma → Cypher inválido).
- KuzuGraphSink (NUEVO, .hpp/.cpp): implementa IGraphSink sobre Kuzu embebido. Forward-decl
  de Database/Connection (header NO arrastra kuzu.hpp). Constructor(db_path, schema_path, logger)
  carga schema idempotente (IF NOT EXISTS). write() lleva GUARD: rechaza node_id/flow_uid vacíos
  (invariante de engine — Kuzu no permite NOT NULL en no-PK). flush() = contador (auto-commit).
- LoggingGraphSink: build_cypher() ahora DELEGA en el builder compartido (paridad total).
  Modelo viejo (:NetworkFlow)-[:RAISED]->(:Alert) con 5-tupla+scores aplanados RETIRADO.
- main.cpp: backend seleccionable por env. ARGUS_GRAPH_BACKEND=kuzu → KuzuGraphSink
  (default db /opt/argus/graph/argus_graph.kuzu, schema /vagrant/.../schema.cypher);
  cualquier otro valor / ausente → LoggingGraphSink (default, no requiere Kuzu, CI-safe).
- CMakeLists: kuzu_graph_sink.cpp en la lib; find_library(KUZU_LIB) + link PUBLIC
  (se propaga a bin+tests, patrón ntp_utils); target test_kuzu_graph_sink con SCHEMA_PATH.
- Vagrantfile: bloque "configure-argus-graph-dir" crea /opt/argus/graph (fs LOCAL del guest,
  NO /vagrant: vboxsf rompe el mmap de Kuzu). chown vagrant, chmod 750.
- argus_graph.yaml (reglas Falco TEMPORALES, parking en RAÍZ del repo): integridad del
  graph store. ⚠️ proc.name truncado a 15 chars → "correlation_eng" (no el nombre completo).
- Dialecto Kuzu VALIDADO contra lib real (dialect_smoke.cpp, throwaway): IF NOT EXISTS OK,
  MERGE/ON CREATE SET encadenado OK, enrutado Alert/TelemetryEvent OK, aristas OK.

Frente C (de DAY 180): DIAGNOSTICADO + ESCALADO al Consejo, decisión POSTERGADA.
event_id = bpf_ktime_get_ns() (sniffer.bpf.c:246) → monótono-desde-boot → NO replay-stable.
El mismo pcap da event_ids distintos entre runs → rompe golden tier. Deuda P1 REAL.
Brief medible redactado (docs/counsil/Consulta...event_id.md) + respuestas de los 8 modelos
YA recogidas en docs/counsil/ — PENDIENTE: sintetizar el veredicto del Consejo (no hecho).

───────────────────────────────────────────────────────────────────────────────
DEUDA TÉCNICA ACUMULADA DAY 180 — VOLCAR A docs/BACKLOG.md (no hecho aún)
───────────────────────────────────────────────────────────────────────────────
NUEVAS (DAY 180):
- DEBT-KUZU-UPSTREAM-ARCHIVED-001 (P2): upstream Kuzu archivado 10-oct-2025. Mitigado por
  IGraphSink; plan B fork Vela-Engineering/kuzu. Vigilar CVEs sin parche. Candidato a ADR corto.
- DEBT-KUZU-SCHEMA-EMBED-001 (P3): el sink lee schema.cypher de fichero en runtime. Para el
  binario de producción desplegado, embeber el DDL o instalarlo junto al ejecutable.
- DEBT-KUZU-DB-LOCATION-PROD-001 (P3): /opt/argus/graph es dev. La ruta de prod (Raspberry)
  está por decidir; ligada a quién corre el engine (usuario) y a la migración Iceberg.
- DEBT-FALCO-ARGUS-GRAPH-RULES-001 (P2): argus_graph.yaml está en la RAÍZ (parking). Su hogar
  es donde ADR-030 materialice las 10-11 reglas argus_ (no existen como .yaml versionado en el
  repo — verificar dónde las genera el hardening). Sumar bajo DEBT-PROD-FALCO-RULES-EXTENDED-001.
- DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (P3): ld avisa libsodium.so.26 vs .so.23 al linkar
  crypto-transport (Kuzu trae libsodium transitivo/embebido). Ruido conocido, tests pasan. Vigilar.

ARRASTRADAS (siguen abiertas):
- DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (P1): event_id no reproducible (ver Frente C). EN CONSEJO.
- DEBT-FLOWUID-SEQ-COLLISION-001 (P2): seq=0 fijo. Hermano del problema del desambiguador de
  event_id (Opción 1 del brief al Consejo los unifica).
- DEBT-DOC-FLOWUID-NEO4J-KUZU-001 (P3): comentarios de flow_uid.hpp dicen "Neo4j", es Kuzu (5 min).
- DEBT-TEST-COL17-CONTRACT-DRIFT-001 (P2): alinear fixture al símbolo DetectorSource.
- DEBT-ENGINE-INOTIFY-001 (P3): el --follow es tail-poll, no inotify.
- DEBT-PROD-FALCO-RULES-EXTENDED-001: ptrace, DNS tunneling, /dev/mem, conexiones salientes.

PENDIENTES DE PROCESO (no son deuda de código):
- Sintetizar veredicto del Consejo sobre reproducibilidad event_id (8 respuestas ya recogidas).
- Pasar por el Consejo: lo realizado en DAY 180 (backend Kuzu) + el ADR-057 nuevo. NO hecho.
- Actualización al Consejo arrastrada desde DAY 178/179: ADR-055 ratificada + §10.1 + F1 cerrado.
- README bloque <!-- DAY-STATUS --> sin actualizar a DAY 180.

───────────────────────────────────────────────────────────────────────────────
ADR-057 (BORRADOR — refinar entre Alonso y Claude ANTES del Consejo)
───────────────────────────────────────────────────────────────────────────────
"Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla"
docs/adr/ADR-057-... .md (borrador inicial creado DAY 180). Tres ejes a desarrollar:
1. Capa de CONSULTA sobre Kuzu: cómo se exponen las queries del grafo (API, plantillas
   parametrizadas, no Cypher crudo al usuario). Quién puede leer el grafo (ligado a Falco).
2. BITEMPORALIDAD: tiempo de evento (flow_start_window) vs tiempo de ingestión/decisión.
   El grafo hoy solo tiene tiempo de evento; falta el eje de cuándo se materializó/supo.
3. Acceso NL→PLANTILLA: lenguaje natural a plantilla Cypher acotada (NO NL→Cypher libre,
   por seguridad/inyección). Catálogo de plantillas auditables.
   Estado: embrión. Se refina iterativamente día a día antes de convocar al Consejo.

───────────────────────────────────────────────────────────────────────────────
FRENTES VIVOS — Alonso elige al arrancar
───────────────────────────────────────────────────────────────────────────────
DOC) DOCUMENTAR DAY 180 (frente natural): volcar la deuda de arriba a docs/BACKLOG.md,
refinar ADR-057, actualizar README DAY-STATUS. Día de orden, bajo en energía.
B)   ADR-054 — confianza bronce multi-nodo (DISEÑO, sigue PENDIENTE). Ed25519 jerárquico (Kimi).
D)   Deudas baratas: DEBT-DOC-FLOWUID-NEO4J-KUZU-001 (5 min) / DEBT-TEST-COL17-CONTRACT-DRIFT-001.
CONSEJO) Sintetizar el veredicto sobre event_id + convocar Consejo sobre Kuzu/ADR-057.
E2E) Ejecutar el engine en modo Kuzu real (ARGUS_GRAPH_BACKEND=kuzu) contra bronce real,
verificar que /opt/argus/graph se puebla. PRIMERA vez que se corre fuera de tests.

NO HOY salvo decisión explícita: Suricata/Zeek/Wazuh (F2/F3).

───────────────────────────────────────────────────────────────────────────────
INVARIANTES DURABLES (no re-litigar, no violar) — + nuevas de DAY 180
───────────────────────────────────────────────────────────────────────────────
BUILD / ENTORNO
- Construir SIEMPRE vía `make <target>`. Recetas make desde el HOST macOS; lo demás vía
  `vagrant ssh -c`. macOS anfitrión; build Linux-only (guest). NUNCA cmake en el host.
- macOS: nunca `sed -i` sin `-e ''`; heredoc Python3. Scripts un-solo-uso → gitignored.
- Dos commits/día separados: código y docs. EMECAS = vagrant destroy -f && up && bootstrap && test-all.
- ntp_utils Y libkuzu se linkan por find_library sobre la lib instalada (NO add_subdirectory).

KUZU / GRAFO (NUEVO DAY 180)
- Kuzu v0.11.3, upstream ARCHIVADO. Vendorizado tras IGraphSink (intercambiable). Pin SHA256.
- BD Kuzu = fichero único .kuzu (v0.11.0+). NO en /vagrant (vboxsf rompe mmap) → /opt/argus/graph.
- Schema-first OBLIGATORIO: Kuzu exige DDL declarado antes de insertar. PK STRING/numérica.
  node_id NO puede ser NOT NULL (no-PK) → el GUARD del sink lo hace cumplir en código.
- cypher_builder.hpp = ÚNICA fuente del Cypher; ambos sinks delegan (paridad). Stream con
  locale::classic() SIEMPRE (el guest es es_ES → coma decimal rompería el Cypher).
- is_alert(r) := final_classification=="MALICIOUS" (el sink LEE el veredicto, NO recalcula).
- Grafo = vista DERIVADA del bronce (reconstruible). NetworkFlow identidad pura; veredicto
  en Alert/TelemetryEvent. Datasets cruzados → Parquet ORO, NO el grafo.

BRONCE / IDENTIDAD (sin cambios)
- Contrato correlation_v1: 19 cols (18 + HMAC). Reader valida HMAC ANTES de parsear; inválida DESCARTA.
- event_id NUESTRO, determinista (PERO ver DEBT-CLOCK-INJECTION: bpf_ktime no es replay-stable).
- flow_uid = base64(BLAKE2b-256(encode(node_id, community_id, flow_start_window, seq))), server-side.
- community_id = SHA1 Corelight; clave de join, NUNCA identidad.
- "Bronce PRESERVA, gold DECIDE": no aplanar DETECTOR_SOURCE_DIVERGENCE.
- Consejo de Sabios = 8 modelos. "Medir, no votar".

───────────────────────────────────────────────────────────────────────────────
DÓNDE LEER MÁS
───────────────────────────────────────────────────────────────────────────────
- correlation-engine/include/correlation_engine/{i_graph_sink,cypher_builder,kuzu_graph_sink,flow_uid}.hpp
- correlation-engine/src/{kuzu_graph_sink,logging_graph_sink,main}.cpp
- correlation-engine/schema/schema.cypher → modelo del grafo (DAY 180).
- correlation-engine/CMakeLists.txt → find_library(KUZU_LIB), target test_kuzu_graph_sink.
- Vagrantfile → bloque Kuzu en all-dependencies + configure-argus-graph-dir.
- argus_graph.yaml (raíz, parking) → reglas Falco temporales del graph store.
- docs/adr/ADR-057-... → borrador capa de consulta + bitemporalidad + NL→plantilla.
- docs/counsil/Consulta...event_id*.md → brief + 8 respuestas (sintetizar veredicto).
- docs/BACKLOG.md → deudas P0-P3 (PENDIENTE volcar las de DAY 180 listadas arriba).
- ml-detector/src/zmq_handler.cpp:438 → final_classification (predicado de is_alert).

NUMERACIÓN ADR: 053 RESERVADO (JA3/JA4+TLS+BGP) · 054 PENDIENTE (confianza bronce multi-nodo)
· 055 RATIFICADA (injectors/golden) · 056 ? · 057 BORRADOR (consulta grafo + bitemporal + NL→plantilla).