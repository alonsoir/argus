═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 180 — aRGus NDR · branch feature/day170-community-id-protobuf
═══════════════════════════════════════════════════════════════════════════════
Prompt LEAN a propósito: estado + frentes + primer comando + invariantes.
El detalle vive en el repo (ver "DÓNDE LEER MÁS"). La cola histórica está en git log.

> NOTA PARA CLAUDE: DAY 179 cerró el consumidor F1 (aRGus únicamente) con backend
> LoggingGraphSink (Cypher a log). El frente NATURAL de hoy es el BACKEND KUZU real
> detrás de IGraphSink — la interfaz ya existe, hoy se sustituye el backend trivial por
> Kuzu embebido. PERO Alonso decide el frente al arrancar (ver "FRENTES VIVOS"). No
> asumas Kuzu sin confirmarlo: pregunta o mira qué dice Alonso en el primer mensaje.

───────────────────────────────────────────────────────────────────────────────
QUÉ CERRÓ DAY 179 (hecho — verificar estado en commits antes de repetir)
───────────────────────────────────────────────────────────────────────────────
Día de CÓDIGO. Consumidor F1 del bronce → grafo, VERDE E2E (3/3 tests + EMECAS PASSED).

- IGraphSink (interfaz Cypher) NACE: include/correlation_engine/i_graph_sink.hpp.
  Método write(record, flow_uid) por registro + flush() no-op por defecto.
- LoggingGraphSink: backend de hoy. Emite Cypher completo
  (MERGE (:NetworkFlow {flow_uid})-[:RAISED]->(:Alert {...})) por write + contador
  agregado en flush(). build_cypher() estático, expuesto para test. NO toca disco de grafo.
- correlation-engine/src/main.cpp deja de ser scaffold: loop one-shot + flag --follow
  (tail-poll). Cadena: file_watch bronce → parse_and_verify → window_micros →
  compute_flow_uid (seq=0) → sink.write. NTP gate (ADR-046 P0) intacto delante.
  Clave HMAC por env ARGUS_BRONZE_HMAC_KEY_HEX (lado lector de DEBT-BRONZE-KEY-PROVISIONING-001).
- Binario correlation_engine_bin linkado contra libntp_utils.a vía find_library
  (NO add_subdirectory — contamina el ctest del engine con los 13 tests del common).
- test_graph_sink_loop: caso A (MockGraphSink valida descarte — invariante Mistral:
  fila corrupta/HMAC-malo NO llega al sink) + caso B (LoggingGraphSink valida Cypher).
- Fix colateral: test_correlation_reader.cpp col17 (authoritative_source) string vs int
  → desbloqueó compilación (DEBT-TEST-COL17-CONTRACT-DRIFT-001 anotada).
- Smoke one-shot contra bronce real (2026-06-07.csv): [verificar resultado en notas/log].

Deudas nuevas DAY 179 (en docs/BACKLOG.md): DEBT-FLOWUID-SEQ-COLLISION-001 (P2),
DEBT-TEST-COL17-CONTRACT-DRIFT-001 (P2), DEBT-ENGINE-INOTIFY-001 (P3),
DEBT-DOC-FLOWUID-NEO4J-KUZU-001 (P3).

───────────────────────────────────────────────────────────────────────────────
FRENTES VIVOS — Alonso elige el de HOY al arrancar
───────────────────────────────────────────────────────────────────────────────
A) BACKEND KUZU real detrás de IGraphSink (frente natural, ES CÓDIGO).
   El .gitkeep lo ordenó: "interfaz Cypher + backend Kuzu embebido". Hoy: KuzuGraphSink
   implements IGraphSink, ejecuta el Cypher de build_cypher() contra Kuzu v0.11.3 embebido.
   LoggingGraphSink se mantiene (útil para tests sin Kuzu). Pregunta de diseño antes de
   teclear: ¿el Cypher actual (MERGE (:NetworkFlow)-[:RAISED]->(:Alert)) es válido en el
   dialecto Cypher de Kuzu, o hay que ajustarlo? Kuzu no es Neo4j 1:1.
   · flow_uid se calcula EN EL ENGINE (server-side), ya disponible — Kuzu solo materializa.
   · "Bronce PRESERVA, gold DECIDE": no aplanar DETECTOR_SOURCE_DIVERGENCE al entrar.

B) ADR-054 — confianza bronce multi-nodo (DISEÑO, sigue PENDIENTE de redacción).
   HMAC simétrico no escala a N sensores → Kuzu central. Ed25519 jerárquico (Kimi).
   Flujo: borrador → Consejo → aprobación. Prerequisito del lado consumidor cross-nodo.

C) DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (= deuda event_id determinista golden, P1).
   Localizar event.timestamp en el struct del ring buffer eBPF: ¿kernel (bpf_ktime/frame
   ts → reproducible) o userspace (wall-clock → deuda real)? Resolver una resuelve ambas.
   PRIMER PASO: grep del struct del ring buffer + ring_consumer.cpp:853.

D) DEUDAS DAY 179 baratas si quieres día ligero: DEBT-DOC-FLOWUID-NEO4J-KUZU-001 (P3,
   5 min — comentarios de flow_uid.hpp dicen "Neo4j", el backend es Kuzu) o
   DEBT-TEST-COL17-CONTRACT-DRIFT-001 (P2, alinear fixture al símbolo DetectorSource).

NO HOY salvo decisión explícita: Suricata/Zeek/Wazuh (F2/F3 — disparan DEBT-LIB-001,
extraer libs/flow-identity/). El contrato unificado NO necesita reader por sensor.

───────────────────────────────────────────────────────────────────────────────
PRIMER COMANDO — si el frente es (A) Kuzu: ver qué hay de Kuzu hoy y validar el Cypher
───────────────────────────────────────────────────────────────────────────────
vagrant ssh -c "echo '=== Kuzu instalado/embebido en el guest? ==='; find / -iname 'kuzu*' 2>/dev/null | grep -v proc | head -20; echo '=== IGraphSink + sinks actuales ==='; ls -la /vagrant/correlation-engine/include/correlation_engine/i_graph_sink.hpp /vagrant/correlation-engine/include/correlation_engine/logging_graph_sink.hpp 2>/dev/null; echo '=== el Cypher que generamos hoy (revisar dialecto Kuzu) ==='; sed -n '1,60p' /vagrant/correlation-engine/src/logging_graph_sink.cpp"

───────────────────────────────────────────────────────────────────────────────
INVARIANTES DURABLES (no re-litigar, no violar)
───────────────────────────────────────────────────────────────────────────────
BUILD / ENTORNO
- Construir SIEMPRE vía `make <target>` (corre dep proto, .pb.h fresco, -Werror del Makefile).
  NUNCA `cmake -S . -B build` directo → compila contra .pb.h rancio.
- Recetas make desde el HOST macOS; NO envolver en `vagrant ssh -c` (el Makefile ya lo hace
  por dentro donde toca). Todo lo demás vía `vagrant ssh -c` (siempre con -c).
- macOS es anfitrión; eBPF/XDP y el build son Linux-only (guest Debian). NUNCA cmake en el host.
- macOS: nunca `sed -i` sin `-e ''`; usar heredoc Python3. Scripts: sin git, sin auto-commit.
  Scripts de aplicación de un solo uso → gitignored (apply_dayNNN_*.py), NO entran en commit.
- Dos commits/día separados: código y docs. EMECAS = vagrant destroy -f && up && bootstrap && test-all.
- ntp_utils se linka por find_library sobre la .a instalada (NO add_subdirectory ../common:
  arrastra el enable_testing() del common y contamina el ctest del engine — lección DAY 179).

BRONCE / IDENTIDAD
- Contrato correlation_v1: 19 columnas (18 contenido 0-17 + HMAC), sin header, HMAC-SHA256
  por fila sobre cols 0-17. Reader valida HMAC ANTES de parsear; fila inválida se DESCARTA,
  no lanza. col 17 = string simbólico (DetectorSource_Name()).
  Columnas: 0 schema_version · 1 source_sensor · 2 event_id · 3 originating_node_id ·
  4 community_id · 5 flow_start_sec · 6 flow_start_nano · 7 source_ip · 8 destination_ip ·
  9 source_port · 10 destination_port · 11 protocol_name · 12 final_classification ·
  13 threat_category · 14 fast_detector_score · 15 ml_detector_score · 16 overall_threat_score ·
  17 authoritative_source (string).
- Clave HMAC del bronce = etcd /secrets/<componente> campo key. NO seed.hex.
- event_id es NUESTRO, generado en el sniffer, determinista, único sobre el mismo input.
  NUNCA derivado de algo que venga de fuera. Ancla de la dedup del engine.
  (DEUDA: aún no anclado a offset-pcap para tier golden — DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001.)
- flow_uid = base64(BLAKE2b-256(encode(node_id, community_id, flow_start_window, seq))),
  digest 32, calculado SERVER-SIDE en el engine (compute_flow_uid en flow_uid.hpp).
  node_id = identidad opaca del PUNTO DE CAPTURA. seq=0 hoy (DEBT-FLOWUID-SEQ-COLLISION-001).
- community_id = SHA1 Corelight; clave de correlación/join, NUNCA identidad. compute_community_id()
  devuelve nullopt si proto ∉ {TCP6,UDP17}.
- domain (NETWORK|HOST|HYBRID) = NATURALEZA; source_engine = QUIÉN la vio. Ortogonales.
- "Bronce PRESERVA, gold DECIDE": no aplanar DETECTOR_SOURCE_DIVERGENCE al entrar en Kuzu.
- AdapterSpec §10.1 = contrato F1 del adapter de aRGus (mapeo bronce→envelope). NORMATIVO.
  El envelope se materializa como fila CSV bronce + Cypher en el sink. NO hay message
  SecurityEvent en el .proto (verificado DAY 178); el consumidor LEE el veredicto, no recalcula.
- IGraphSink = abstracción del destino del grafo. write(record, flow_uid) por registro.
  Backend intercambiable: LoggingGraphSink (hoy) / KuzuGraphSink (objetivo). Mismo contrato.
- Herramientas de tools/ = SUPLANTADORES FIELES (ADR-055 §0); propagación bidireccional.

OPERATIVA
- Limpiar bronce SIEMPRE con el ml-detector parado: tmux kill-session → rm CSV → make ml-detector-start.
- El injector necesita: sudo env LD_LIBRARY_PATH=/usr/local/lib (seed.bin 0400 + .so instaladas).
- correlation-engine: target make correlation-engine-test (build + ctest). El binario one-shot:
  ARGUS_BRONZE_HMAC_KEY_HEX=<64hex> ARGUS_BRONZE_CSV=<csv> build/correlation_engine_bin.
- Consejo de Sabios = 8 modelos (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen).
  Principio: "medir, no votar". PENDIENTE: actualización al Consejo sobre ADR-055 ratificada
  + §10.1 + consumidor F1 cerrado (arrastrado desde DAY 178/179).

───────────────────────────────────────────────────────────────────────────────
DÓNDE LEER MÁS (bajo demanda, no cargar todo)
───────────────────────────────────────────────────────────────────────────────
- correlation-engine/include/correlation_engine/i_graph_sink.hpp → interfaz (DAY 179).
- correlation-engine/include/correlation_engine/logging_graph_sink.hpp + src/.cpp → backend hoy.
- correlation-engine/include/correlation_engine/flow_uid.hpp → compute_flow_uid + window_micros.
- correlation-engine/include/correlation_engine/correlation_reader.hpp → parse_and_verify.
- correlation-engine/src/main.cpp → loop one-shot/--follow (DAY 179).
- docs/engineering_decisions/AdapterSpec v1 — ... .md → §10.1 mapeo aRGus + §3/§4/§5/§10.
- proto/network_security.proto → NetworkSecurityEvent (NO existe SecurityEvent — verificado DAY 178).
- docs/adr/ADR-055-inyectores-sinteticos.md → RATIFICADA con enmiendas (DAY 178).
- docs/adr/ADR-046 V4 — ... .md → §3.3/§3.8/§3.10/§3.11.
- docs/BACKLOG.md → deudas P0-P3; entradas DAY 179 (consumidor F1 + 4 deudas nuevas).
- ml-detector/src/zmq_handler.cpp → cálculo del verdicto + CorrelationWriter (productor bronce).
- README.md → bloque <!-- DAY-STATUS --> + Hitos.
- git log -- docs/continuity/PROMPT_CONTINUE_CLAUDE.md → prompts históricos (incl. DAY 179).

NUMERACIÓN ADR: 053 RESERVADO (JA3/JA4 + TLS + BGP) · 054 PENDIENTE (confianza bronce multi-nodo)
· 055 = injectors/golden/entrega (RATIFICADA DAY 178).
