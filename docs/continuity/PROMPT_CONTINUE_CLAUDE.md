═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 178 — aRGus NDR · branch feature/day170-community-id-protobuf
═══════════════════════════════════════════════════════════════════════════════
Prompt LEAN a propósito: estado + dos frentes + primer comando + invariantes.
El detalle vive en el repo (ver "DÓNDE LEER MÁS"). La cola histórica de días
anteriores está en git log de este fichero, no aquí.

───────────────────────────────────────────────────────────────────────────────
QUÉ CERRÓ DAY 177 (hecho y commiteado — NO repetir)
───────────────────────────────────────────────────────────────────────────────
Lado PRODUCTOR del bronce en forma final + injectors sellados E2E. 3 commits.
- (B) col 17 authoritative_source → string simbólico. DetectorSource_Name() en el
  writer; reader almacena string; engine LIMPIO de protobuf. Round-trip verde +
  bronce real: 150 ML_PRIORITY + 9 DIVERGENCE (strings). Orden B-vs-A resuelto
  MIDIENDO: test_correlation_roundtrip es injector-independiente → B fue antes.
- node_id sintético — DEBT-INJECTOR-NODEID-001 CERRADA. Isomorfo synth-node-00 fijo;
  mock synth:node:<id>. flow_uid ya no degenera (102 filas synth-node-00 en bronce).
- Proto benigno (hallazgo, NO deuda — "completar A"): el injector ponía protocol_number
  aleatorio → ~99% no-TCP/UDP → compute_community_id() nullopt → bronce a 0 filas. Fix:
  coin flip use_tcp gobierna number+name. community_id 0%→100% (159/159 "1:...=").
- DEBT-INJECTOR-ROWGAP-001 REENCUADRADA y cerrada como característica: send(dontwait)
  reproduce fielmente la entrega no-garantizada de ZMQ PUSH (bidireccional). Q1 arbitraje
  Alonso vs mayoría Consejo → INSTRUMENTAR, no re-arquitecturar (ADR-055 §0).
- Deudas nuevas (P2, no bloqueantes): DEBT-INJECTOR-DELIVERY-METRIC-001 (diff de conjuntos
  {enviados}/{escritos}, reemplaza el "fix" de ROWGAP) · DEBT-INJECTOR-PROTO-MIX-001 (modo
  realistic con semilla fija + aserción de ausencia en bronce; default deterministic).

───────────────────────────────────────────────────────────────────────────────
DOS FRENTES DAY 178
───────────────────────────────────────────────────────────────────────────────
(1) CERRAR ADR-055 — confirmación de FIDELIDAD (barato, primero).
Las 8 respuestas ya están en docs/counsil/ADR-055-*.md. NO es re-deliberación:
verificar que ADR-055 v1 refleja el consenso y deja clara la anulación de árbitro
en Q1 (solo instrumento). Si hay consenso → BORRADOR → ratificada (1 línea en
ADR-055 + BACKLOG Estado + README DAY-STATUS). Si hay objeción → registrarla, NO ratificar.

(2) LADO CONSUMIDOR del engine (el grueso) — desbloqueado porque el contrato bronce ya
está en forma final:
file_watch del bronce → clave HMAC desde etcd /secrets/<componente> (campo key,
NO seed.hex) → parse_and_verify PRIMERO → Avro → ZMQ al servidor.
INVARIANTE (riesgo Mistral): parse_and_verify es el PRIMER paso; fila inválida / clave
mala se DESCARTA antes de tocar Kuzu — una clave mala no corrompe el grafo.
Deudas que aterrizan aquí: DEBT-BRONZE-KEY-PROVISIONING-001 (P1, clave de etcd no seed.hex)
y DEBT-BRONZE-PROVISIONING-E2E-001 (P1, el test obtiene la clave del mecanismo real en
AMBOS lados, no hardcodeada).

NO HOY: DEBT-LIB-001 (extraer libs/flow-identity/) — su disparador son los adaptadores
Suricata/Zeek, no el consumidor. ADR-054 (confianza bronce multi-nodo) sigue PENDIENTE.

PRIMER COMANDO — fotografiar el estado del consumidor antes de construir:
vagrant ssh -c "ls -la /vagrant/correlation-engine/src /vagrant/correlation-engine/include/correlation_engine 2>/dev/null; echo '=== file_watch / avro / zmq / secrets presentes? ==='; grep -rn 'file_watch\|inotify\|avro\|Avro\|zmq\|parse_and_verify\|/secrets/' /vagrant/correlation-engine/ 2>/dev/null | head -40"

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
- Dos commits/día separados: código y docs. EMECAS = vagrant destroy -f && up && bootstrap && test-all.

BRONCE / IDENTIDAD
- Contrato correlation_v1: 19 columnas, sin header, HMAC-SHA256 por fila sobre cols 0-17.
  Reader valida HMAC ANTES de parsear (anti-tampering + detector de escritura a medias);
  fila inválida se DESCARTA, no lanza. col 17 = string simbólico (DetectorSource_Name()).
- Clave HMAC del bronce = etcd /secrets/<componente> campo key. NO seed.hex.
- flow_uid = hash(node_id ‖ community_id ‖ flow_start_window), BLAKE2b digest 32, calculado
  SERVER-SIDE en Kuzu (no en transporte). node_id = identidad opaca del PUNTO DE CAPTURA.
- community_id = SHA1 Corelight; clave de correlación/join, NUNCA identidad. TODAS las variantes
  del sniffer deben poblarlo. compute_community_id() devuelve nullopt si proto ∉ {TCP6,UDP17}.
- "Bronce PRESERVA, gold DECIDE": no aplanar la divergencia (DETECTOR_SOURCE_DIVERGENCE) al
  entrar en Kuzu (ADR-055 §3.5). Procedencia extremo a extremo.
- Herramientas de tools/ son SUPLANTADORES FIELES del componente que imitan (ADR-055 §0): no
  hacerlas más fiables que el componente real; propagación bidireccional.

OPERATIVA
- Limpiar bronce SIEMPRE con el ml-detector parado (borrar en caliente deja inode huérfano →
  filas perdidas). Secuencia: tmux kill-session → rm CSV → make ml-detector-start.
- El injector necesita: sudo env LD_LIBRARY_PATH=/usr/local/lib (lee seed.bin 0400 + .so instaladas).
- Consejo de Sabios = 8 modelos (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen).
  Principio: "medir, no votar".

───────────────────────────────────────────────────────────────────────────────
DÓNDE LEER MÁS (bajo demanda, no cargar todo)
───────────────────────────────────────────────────────────────────────────────
- docs/BACKLOG.md → "Entradas DAY 177" (deudas + decisiones del día); deudas abiertas P0-P3.
- docs/adr/ADR-055-inyectores-sinteticos.md → decisión completa (v1 BORRADOR).
- docs/counsil/ADR-055-*.md y Consulta...DAY 177-*.md → las 8 respuestas para la fidelidad.
- README.md → bloque <!-- DAY-STATUS --> (snapshot del día) + Hitos DAY 177.
- correlation-engine/ → reader (correlation_reader.{hpp,cpp}), flow_uid.hpp, schema/schema.cypher.
- git log -- docs/continuity/PROMPT_CONTINUE_CLAUDE.md → prompts históricos de días anteriores.

NUMERACIÓN ADR: 053 RESERVADO (JA3/JA4 + TLS + BGP) · 054 PENDIENTE (confianza bronce
multi-nodo Ed25519/HMAC) · 055 = injectors/golden/entrega (v1 BORRADOR, ratificable hoy).