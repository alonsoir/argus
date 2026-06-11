═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 182 — aRGus NDR · branch feature/day170-community-id-protobuf
═══════════════════════════════════════════════════════════════════════════════
Prompt LEAN a propósito: estado + frentes + invariantes. El detalle vive en el repo.

> NOTA PARA CLAUDE: DAY 181 fue día de ORDEN (DOC) + 1ª vuelta del Consejo sobre ADR-057.
> Cerrado: auditoría de seguridad de Fable aplicada (H-1/H-2/H-3 + tests + make audit),
> backlog DAY 180-181 volcado, README DAY-STATUS a 181, DEBT-DOC-FLOWUID-NEO4J-KUZU-001
> cerrada, ADR-057 refinado a v2 tras Consejo 8/8 + arbitraje. El frente NATURAL de hoy es
> la FASE 0 de ADR-057 (código: ingested_at + smoke de concurrencia adelantado), o sintetizar
> el veredicto event_id que sigue pendiente. PERO Alonso decide. No asumas; mira su 1er mensaje.

───────────────────────────────────────────────────────────────────────────────
QUÉ CERRÓ DAY 181 (hecho — verificar en commits antes de repetir)
───────────────────────────────────────────────────────────────────────────────
DÍA DE ORDEN (frente DOC) + Consejo ADR-057.

- AUDITORÍA DE SEGURIDAD (Fable, DAY 180) APLICADA a la rama. 3 parches vía git am:
  H-1 cypher_builder.hpp esc() escapa la barra invertida antes de la comilla simple ·
  H-2 config_loader allow-list set_name [A-Za-z0-9_-]{1,31} · H-3 main_libpcap rechaza ip_hl<5.
  + 2 tests RED→GREEN. + target `make audit` (contrib/audit/audit.mk). EMECAS verde. Pusheado.
- `make audit`: audit-static (cppcheck) solo tumba en [error], excluye eBPF, PASA limpio.
  audit-taint (semgrep) EN CUARENTENA — semgrep-core se cuelga sobre el árbol C++ completo.
- BACKLOG volcado: deuda DAY 180-181 (5 Kuzu + 2 semgrep) a docs/BACKLOG.md vía script
  idempotente. README <!-- DAY-STATUS --> a DAY 181. Pusheado (commit de docs).
- DEBT-DOC-FLOWUID-NEO4J-KUZU-001 CERRADA: comentario de flow_uid.hpp refleja Kuzu vía
  IGraphSink (antes Neo4j). grep -i neo4j = 0. Pusheado (commit de código).
- ADR-057 REFINADO A v2 tras 1ª vuelta del Consejo (8/8) + arbitraje de Alonso. Acta redactada
  (formato backlog). ⚠️ PENDIENTE DE COMMITEAR si no se hizo al cierre de DAY 181.

CONSEJO ADR-057 — 1ª vuelta (8/8). Veredicto: dirección aprobada, Fase 0 (ingested_at) verde
unánime, resto condicionado a MEDIR. Choque factual de concurrencia Kuzu (Kimi: issues #3295/#3872
RW+RO no → in-process obligatorio; Qwen: MVCC sí) → se resuelve con SMOKE, no con voto.
Arbitraje de Alonso: NL rechazo duro · T5 eliminada · T6 sobrevive como bridge-ORO (con condición
de muerte) · T4 acotada y honesta (no point-in-time) · T7 attack-path adoptada · smoke adelantado.
Corrección al ponente: ingested_at desacopla el eje de transacción del reloj envenenado pero NO
inmuniza el eje de evento (es first_seen, no transaction-time completo) → flag temporal_anomaly.

───────────────────────────────────────────────────────────────────────────────
DEUDA DAY 181 — verificar en docs/BACKLOG.md
───────────────────────────────────────────────────────────────────────────────
NUEVAS (DAY 181):
- DEBT-SEMGREP-CPP-HANG-001 (P2): semgrep-core se cuelga sobre el árbol C++ del firewall (no
  ficheros sueltos; NO es memoria). audit-taint en cuarentena. Pendiente asociado: cablear pipx
  en Vagrantfile (sudo -u vagrant pipx install semgrep) + rutas absolutas en audit.mk + --metrics off.
- DEBT-NL-BENCHMARK-001 (P2): corpus etiquetado + métricas del clasificador NL antes de Fase 3 ADR-057.
- DEBT-KUZU-CONCURRENCY-SMOKE-001 (P1): smoke multiproceso RW+RO + contención lectura bajo carga (Fase 0).
- restore_from_wal_smoke_test: bajo DEBT-LABEL-WAL-001 (recuperación ante corrupción del WAL).

CERRADAS (DAY 181):
- DEBT-SEMGREP-DEPS-001: conflicto urllib3 resuelto aislando semgrep con pipx.
- DEBT-DOC-FLOWUID-NEO4J-KUZU-001: comentario alineado a Kuzu.

HIGIENE PENDIENTE (destapada hoy por el guard del script de backlog):
- 7 cabeceras DUPLICADAS preexistentes en docs/BACKLOG.md: 5 IRP (cross-ref índice/día, ¿deliberado?)
  · DEBT-IRP-FLOAT-TYPES-001 (estado contradictorio CERRADA vs ABIERTA) · BACKLOG-CRYPTO-VENDOR-KEY-001
  (stub vacío x2). Decidir convención del índice "DEUDAS ABIERTAS" + fundir las derivas reales.
  Ofrecido auditor de solo-lectura (audit_backlog_dupes.py) — no ejecutado aún.

ARRASTRADAS (siguen abiertas, sin tocar hoy):
- DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (P1): event_id no reproducible. EN CONSEJO, veredicto SIN sintetizar.
- DEBT-FLOWUID-SEQ-COLLISION-001 (P2) · DEBT-TEST-COL17-CONTRACT-DRIFT-001 (P2) ·
  DEBT-ENGINE-INOTIFY-001 (P3) · DEBT-PROD-FALCO-RULES-EXTENDED-001 · las 5 Kuzu (P2/P3).

───────────────────────────────────────────────────────────────────────────────
ADR-057 v2 — estado tras Consejo (docs/adr/)
───────────────────────────────────────────────────────────────────────────────
"Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla" — v2, 1ª vuelta cerrada.
Catálogo: T1 vecindario (LIMIT fan-out+timeout) · T2 contexto alerta · T3 densidad (acotada tiempo) ·
T4 retro-hunt IOC acotado · T5 ELIMINADA · T6 bridge-ORO (condición de muerte) · T7 attack-path ·
T-hist futura (WAL). Fase 0 = ingested_at (ON CREATE SET, ns UTC, first_seen) + temporal_anomaly +
índice + SMOKE adelantado (concurrencia + contención + monotonía NTP). NL = rechazo duro, params por
gramática, LLM solo clasifica, ADR propio. Firma diferida Fase 4. Pendiente: ejecutar smoke y
adjuntar números → 2ª vuelta o cierre.

───────────────────────────────────────────────────────────────────────────────
FRENTES VIVOS — Alonso elige al arrancar
───────────────────────────────────────────────────────────────────────────────
ADR-057-F0) FASE 0 (código, frente natural): ingested_at en schema.cypher (3 tablas) +
cypher_builder.hpp (ON CREATE SET) + temporal_anomaly + índice + smoke de concurrencia/contención
contra libkuzu real. NO toca bronce/protobuf/sniffer. El smoke ZANJA Kimi-vs-Qwen.
CONSEJO) Sintetizar el veredicto event_id (8 respuestas en docs/counsil/, SIN sintetizar desde DAY 180).
DOC-HIGIENE) audit_backlog_dupes.py + fundir los 7 duplicados + commitear ADR v2 + acta si falta.
D) DEBT-TEST-COL17-CONTRACT-DRIFT-001 (P2, 0.5 sesión).
B) ADR-054 confianza bronce multi-nodo (Ed25519 jerárquico, Kimi). Sigue pendiente.
E2E) Engine en ARGUS_GRAPH_BACKEND=kuzu contra bronce real, verificar /opt/argus/graph se puebla.

NO HOY salvo decisión explícita: Suricata/Zeek/Wazuh (F2/F3) · implementar la capa NL (necesita benchmark).

───────────────────────────────────────────────────────────────────────────────
INVARIANTES DURABLES (no re-litigar, no violar) — + nuevas de ADR-057
───────────────────────────────────────────────────────────────────────────────
BUILD / ENTORNO
- Construir SIEMPRE vía `make <target>` desde el HOST macOS; lo demás vía `vagrant ssh -c`.
  NUNCA cmake en el host. macOS: nunca `sed -i` sin `-e ''`; heredoc Python3; scripts un-uso gitignored.
- Dos commits/día separados: código y docs. EMECAS = vagrant destroy -f && up && bootstrap && test-all.
- ntp_utils Y libkuzu por find_library sobre la lib instalada (NO add_subdirectory).

KUZU / GRAFO
- Kuzu v0.11.3, upstream ARCHIVADO. Tras IGraphSink (intercambiable). Pin SHA256. BD en
  /opt/argus/graph (vboxsf rompe mmap). Schema-first. cypher_builder = única fuente del Cypher,
  locale::classic() siempre. is_alert := final_classification=="MALICIOUS". Grafo = vista derivada
  del bronce; NetworkFlow identidad pura; veredicto en Alert/TelemetryEvent; datasets → Parquet ORO.

BRONCE / IDENTIDAD
- correlation_v1: 19 cols (18 + HMAC), HMAC-first (inválida descarta). event_id determinista (PERO
  CLOCK-INJECTION: bpf_ktime no replay-stable). flow_uid = base64(BLAKE2b(node_id, community_id,
  flow_start_window, seq)) server-side. community_id = SHA1 Corelight, clave de join NUNCA identidad.
  "Bronce PRESERVA, gold DECIDE". Consejo = 8 modelos. "Medir, no votar".

NUEVAS (ADR-057 v2 — pendientes de 2ª vuelta/cierre)
- Capa de consulta IN-PROCESS (probablemente obligatoria por el lock de Kuzu — confirmar con smoke).
- NL→plantilla = RECHAZO DURO ante ambigüedad (decisión Alonso). LLM clasifica; params por gramática.
- ingested_at = first_seen (ON CREATE SET), NO transaction-time completo (eso vive en el WAL).
- temporal_anomaly=TRUE si flow_start_window > ingested_at + margen (aísla CLOCK-INJECTION).
- Catálogo de plantillas = frontera de portabilidad: no acumular Cypher nativo fuera de él.
- SMOKE antes de implementar plantillas (medir, no votar).

───────────────────────────────────────────────────────────────────────────────
DÓNDE LEER MÁS
───────────────────────────────────────────────────────────────────────────────
- docs/adr/ADR-057-... → v2 tras Consejo (catálogo + fases + tabla de arbitraje).
- docs/BACKLOG.md → acta Consejo DAY 181 + deuda DAY 180-181 volcada.
- contrib/audit/audit.mk → make audit (audit-static OK, audit-taint en cuarentena).
- correlation-engine/schema/schema.cypher → modelo del grafo (Fase 0 añade ingested_at).
- correlation-engine/include/correlation_engine/cypher_builder.hpp → ON CREATE SET (Fase 0).
- docs/counsil/Consulta...event_id*.md → brief + 8 respuestas (sintetizar veredicto).

NUMERACIÓN ADR: 053 RESERVADO · 054 PENDIENTE (confianza bronce) · 055 RATIFICADA · 056 ? ·
057 v2 1ª-vuelta-cerrada (consulta grafo + bitemporal + NL→plantilla).
