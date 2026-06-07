═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 178 — aRGus NDR · branch feature/day170-community-id-protobuf
═══════════════════════════════════════════════════════════════════════════════
Prompt LEAN a propósito: estado + frentes + primer comando + invariantes.
El detalle vive en el repo (ver "DÓNDE LEER MÁS"). La cola histórica de días
anteriores está en git log de este fichero, no aquí.

> NOTA PARA CLAUDE: gran parte de lo que sigue salió de una conversación larga al
> cerrar DAY 177 (tarde). Si necesitas el razonamiento fino (los "tres cubos" de
> campos de SecurityEvent, la distinción Caso A / Caso B), pídele a Alonso que te
> traiga esa conversación — aquí está el destilado, no el desarrollo.

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
DESCUBIERTO EN EL CIERRE DAY 177 (relevante para hoy — leído, no implementado)
───────────────────────────────────────────────────────────────────────────────
- AdapterSpec v1 EXISTE y es NORMATIVO (no era una frase de intención). Vive en
  docs/engineering_decisions/AdapterSpec v1 — Contrato de Ingesta de Adapters...md.
  Define el contrato común de TODO adapter (Suricata/Zeek/Wazuh/sniffer aRGus) hacia el
  engine: at-least-once + dedup idempotente por (source_engine, native_event_id);
  exactly-once explícitamente FUERA de alcance. Tier determinista exige stream bit-a-bit
  reproducible. → Tu decisión "diseñar alrededor del contrato" YA tiene contra qué diseñar.

- DOS DECISIONES DE ARQUITECTURA QUE ALONSO CERRÓ (no re-litigar):
  1. FRONTERA CON ANDRÉS / fuentes externas: Alonso publica el CONTRATO
     (correlation_v1 + AdapterSpec); quien quiera entrar al grafo produce eso. El
     correlation-engine NO conoce el formato nativo de nadie. La señal de Andrés (y Wazuh)
     entra como OTRA ARISTA: si no tiene 5-tupla → sin community_id → se ancla por host_key,
     domain=HOST. Ya está escrito en AdapterSpec §3/§10. Confirmar la geometría de la señal
     de Andrés (red / host / física) en la charla, no adivinarla.
  2. IDENTIDAD DEL EVENTO: event_id lo generamos NOSOTROS, en el sniffer, en origen.
     NUNCA derivado de algo "que venga de fuera". Determinista, fiable, representativo.
     Es el ancla de la dedup (Caso B) y la identidad del evento observado (Caso A).

- CASO A vs CASO B (regla que ordena "qué hacer si un campo no llega"):
  · Caso A — el sniffer OBSERVA el cable: campo ausente = HECHO observado, no error.
  NUNCA rellenar, NUNCA descartar el evento por incompletitud. Ausencia y valor
  manipulado son FEATURES legítimas (el modelo debe verlas). Disciplina: distinguir
  "0 porque no se observó" de "0 porque el valor era 0" — usar optional/has_*()/flag
  donde el default mudo sea ambiguo, no en todos.
  · Caso B — el engine RECIBE de otro sensor por red: validar HMAC PRIMERO → fila
  inválida/truncada/manipulada se DESCARTA (no rellenar, no adivinar) → dedup por
  (source_engine, native_event_id) absorbe duplicados/reenvíos → nunca confiar en un
  campo de IDENTIDAD que venga de fuera. (Respalda el arbitraje del dontwait de DAY 177.)

───────────────────────────────────────────────────────────────────────────────
⚠️ PREGUNTA ABIERTA #1 — RESOLVER ANTES DE ESCRIBIR CÓDIGO DEL CONSUMIDOR
───────────────────────────────────────────────────────────────────────────────
Hay DOS nombres de contrato que NO son el mismo mensaje, y la relación está SIN cerrar:
· correlation_v1 = CSV de bronce (19 cols + HMAC) que ml-detector escribe. CERRADO.
· SecurityEvent = envelope que AdapterSpec manda publicar al engine (source_engine,
native_event_id, event_time_unix_ns, optional community_id/host_key, domain
NETWORK|HOST|HYBRID, raw_payload, metadata).
· NetworkSecurityEvent = lo que SÍ existe en el .proto (línea 569, campos 1-35). Es
RICO y específico de aRGus (TricapaMLAnalysis, RAGAnalysis, GeoEnrichment...).

HECHO verificado DAY 177: "message SecurityEvent" NO aparece en el grep del .proto. Solo
existe NetworkSecurityEvent. → Puede que SecurityEvent (a) haya que CREARLO, (b) sea
NetworkSecurityEvent con otro nombre, o (c) sean dos tramos distintos que conviven
(adapter→engine = SecurityEvent ; engine→bronce/Avro→Kuzu = otra cosa).

HIPÓTESIS (de Claude, A CONFIRMAR — no es decisión): NetworkSecurityEvent es DEMASIADO
aRGus-específico para ser el envelope cross-engine; SecurityEvent es agnóstico por diseño
(AdapterSpec). Lo natural sería: SecurityEvent = envelope del engine; raw_payload del
adapter de aRGus = NetworkSecurityEvent (o NetworkFeatures) serializado dentro. Pero
SecurityEvent quizá no existe aún → primer trabajo podría ser DEFINIR el mensaje, no el consumidor.

Hasta resolver esto, NO se sabe si el consumidor produce Avro-de-correlation_v1,
SecurityEvent, o NetworkSecurityEvent. Resolverlo es el gate de todo lo demás de hoy.

───────────────────────────────────────────────────────────────────────────────
FRENTES DAY 178 (en orden)
───────────────────────────────────────────────────────────────────────────────
(1) CERRAR ADR-055 — confirmación de FIDELIDAD (barato, primero).
Las 8 respuestas ya están en docs/counsil/ADR-055-*.md. NO es re-deliberación:
verificar que ADR-055 v1 refleja el consenso y deja clara la anulación de árbitro en
Q1 (solo instrumento). Consenso → BORRADOR→ratificada (1 línea en ADR-055 + BACKLOG
Estado + README DAY-STATUS). Objeción → registrarla, NO ratificar.

(2) RESOLVER PREGUNTA ABIERTA #1 (arriba) — leer el .proto y el código de ingesta del
engine; decidir CON ALONSO si SecurityEvent se crea, se mapea, o conviven tramos.
Esto es diseño, no teclear: sale de mirar, no de asumir.

(3) CONSUMIDOR del engine (el grueso, SOLO tras resolver #1) — F1, aRGus únicamente:
file_watch del bronce → clave HMAC desde etcd /secrets/<componente> (campo key, NO
seed.hex) → parse_and_verify PRIMERO → [envelope que decida #1] → ZMQ al servidor.
INVARIANTE (Mistral): parse_and_verify es el PRIMER paso; fila inválida/clave mala se
DESCARTA antes de tocar Kuzu — una clave mala no corrompe el grafo.
Deudas que aterrizan: DEBT-BRONZE-KEY-PROVISIONING-001 (P1, clave de etcd no seed.hex),
DEBT-BRONZE-PROVISIONING-E2E-001 (P1, clave del mecanismo real en AMBOS lados).
NOTA: el consumidor de aRGus es un RE-EMPAQUETADOR de lo que el sniffer ya produce —
NO calcula features nuevas. F1 no pide medir nada que no se mida ya.

NO HOY: DEBT-LIB-001 (extraer libs/flow-identity/) — disparador = adaptadores Suricata/Zeek,
no el consumidor. ADR-054 (confianza bronce multi-nodo) sigue PENDIENTE de redacción.

PRIMER COMANDO — resolver Pregunta Abierta #1 antes que nada:
vagrant ssh -c "echo '=== SecurityEvent existe como message en algun .proto? ==='; grep -rn 'message SecurityEvent' /vagrant 2>/dev/null | head; echo '=== que mensaje/serializacion espera el engine al ingerir? ==='; grep -rn 'SecurityEvent\|NetworkSecurityEvent\|parse_and_verify\|avro\|Avro\|deserialize\|file_watch\|inotify\|/secrets/' /vagrant/correlation-engine/ 2>/dev/null | head -50"

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
- event_id es NUESTRO, generado en el sniffer, determinista, único sobre el mismo input.
  NUNCA derivado de algo que venga de fuera. Es el ancla de la dedup del engine.
- flow_uid = hash(node_id ‖ community_id ‖ flow_start_window), BLAKE2b digest 32, calculado
  SERVER-SIDE en Kuzu (no en transporte). node_id = identidad opaca del PUNTO DE CAPTURA.
- community_id = SHA1 Corelight; clave de correlación/join, NUNCA identidad. TODAS las variantes
  del sniffer deben poblarlo. compute_community_id() devuelve nullopt si proto ∉ {TCP6,UDP17}.
- domain (NETWORK|HOST|HYBRID) = NATURALEZA de la señal; source_engine = QUIÉN la vio. Ortogonales.
  NETWORK se une por community_id; HOST se ancla por host_key (Wazuh, señal de Andrés).
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
- docs/engineering_decisions/AdapterSpec v1 — ... .md → contrato de ingesta normativo (clave hoy).
- proto/network_security.proto → message NetworkSecurityEvent (línea 569, campos 1-35).
- docs/adr/ADR-046 V4 — Multi-Source Enriched Pipeline ... .md → §3.3/§3.8/§3.10/§3.11 (referenciado por AdapterSpec).
- docs/BACKLOG.md → "Entradas DAY 177"; deudas abiertas P0-P3.
- docs/adr/ADR-055-inyectores-sinteticos.md → decisión injectors (v1 BORRADOR).
- docs/counsil/ADR-055-*.md → las 8 respuestas para la fidelidad de ADR-055.
- README.md → bloque <!-- DAY-STATUS --> (snapshot) + Hitos DAY 177.
- correlation-engine/ → reader (correlation_reader.{hpp,cpp}), flow_uid.hpp, schema/schema.cypher.
- git log -- docs/continuity/PROMPT_CONTINUE_CLAUDE.md → prompts históricos de días anteriores.

NUMERACIÓN ADR: 053 RESERVADO (JA3/JA4 + TLS + BGP) · 054 PENDIENTE (confianza bronce
multi-nodo Ed25519/HMAC) · 055 = injectors/golden/entrega (v1 BORRADOR, ratificable hoy).