DAY 174 — aRGus NDR (arXiv:2604.04952)

ÚLTIMO HITO DAY 173: ADR-051 v2.2 RATIFICADA (Consejo 8/8, confirmación de fidelidad, sin 3ª deliberación)
— Community ID Parity Gate & Correlation Health. Junto con ADR-052 v3.2 (ratificada el mismo día), la
arquitectura de identidad/correlación queda CERRADA Y ARCHIVADA. DAY 173 también cerró el cabo de
enterprise_vendor.pub (commit 5c8dc37d). Tag estable v1.0.0-day166. Rama feature/day170-community-id-protobuf.

═══════════════════════════════════════════════════════════════════════════════
EL PLAN DEL MES — leerlo antes de cualquier otra cosa
═══════════════════════════════════════════════════════════════════════════════
La cadena de valor científico que define el próximo mes (ADR-048):
    correlation-engine -> ingesta al grafo Neo4j con relaciones -> sesiones MITRE
    -> datasets de cada fase -> plugins ensemble (curva F1 multi-fuente).
Esa curva F1 es la contribución publicable para Andrés/UEx.

LECCIÓN DAY 173 (no repetir): dos días seguidos (052 ayer, 051 hoy) se fueron en ADRs de arquitectura
cada vez más finos. El Consejo diverge hacia el detalle por naturaleza — cada sabio añade un caso de
borde, y sumados producen robustez de producción para un sistema que aún no se ha construido. RESISTIR
eso. La sobreingeniería se siente como rigor en el momento; la diferencia es si lo que endureces YA EXISTE.
A partir de DAY 174 toca CONSTRUIR el engine, no diseñar más alrededor de él.

═══════════════════════════════════════════════════════════════════════════════
PRIMERO DE TODO DAY 174 — commit/push de DAY 173
═══════════════════════════════════════════════════════════════════════════════
Commitear en la misma piedra: ADR-051_v2.2.md (+ cadena v2.1/v2/v1 + síntesis), las entradas nuevas en
docs/BACKLOG.md (sección RATIFICADO DAY 173 ADR-051 + 8 DEBTs nuevas), README.md (DAY-STATUS + Hitos DAY 173),
y este prompt actualizado. El commit de higiene de enterprise_vendor.pub (5c8dc37d) ya está pusheado.
Verificar antes: git status; git diff --cached | grep -iE 'PRIVATE KEY|vendor.key|password|token';
grep -E '^## ✅ (CERRADO|RATIFICADO) DAY' docs/BACKLOG.md | sort | uniq -d (vacío).
Docs puras = excepción razonada al PR obligatorio (igual que ADR-052), pero el commit incluye solo docs.

═══════════════════════════════════════════════════════════════════════════════
EL SIGUIENTE PASO REAL — DEBT-NEO4J-FLOW-KEY-001 (P0 esquema)
═══════════════════════════════════════════════════════════════════════════════
Esto es lo que DESBLOQUEA el correlation-engine. Es el primer eslabón de la cadena del mes y NO es de
ADR-051 — es de ADR-052 (que lo ratifica). Trabajo de ESQUEMA, no de ADR. Antes de poblar el grafo:
  - flow_uid = base64(BLAKE2b(node_id || community_id || uint64_be(flow_start_window) [|| seq_in_window]))
    con crypto_generichash (libsodium 1.0.19). node_id = string canónico declarado (NO keypair efímero).
  - node_id propiedad OBLIGATORIA en :NetworkFlow, :Alert, :TelemetryEvent.
  - Constraint compuesto nativo Neo4j 5.x. Decidirlo con el grafo VACÍO es gratis; retrofitear con datos
    en producción es doloroso (unánime Consejo DAY 170).
  - Correlación intra-nodo por community_id (propiedad indexada); identidad/dedup inter-nodo por flow_uid.
TEST DE CIERRE: dos flujos misma 5-tupla en nodos distintos -> flow_uid distinto. Misma 5-tupla reciclada
en el tiempo en el mismo nodo -> flow_uid distinto.
DEPENDE DE (ambas P0, también de ADR-052, hacer en este orden):
  - DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id = string declarado en inventario firmado, no keypair.
  - DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificación canónica BLAKE2b + paridad C++/Python sobre la
    MISMA versión de libsodium (mismo patrón que pycommunityid). Caso 2-sensores misma 5-tupla -> distinto.
    Su batería de vectores es COMPARTIDA con DEBT-CID-TEST-VECTORS-001 (ADR-051) — no duplicar.

PRIORIDAD DAY 174 (en orden):
1. commit/push DAY 173 (arriba).
2. DEBT-NODEID-CRYPTO-IDENTITY-001 + DEBT-FLOWUID-CANONICAL-ENCODING-001 (P0) — la pieza de identidad
   que el esquema necesita. Paridad C++/Python verificable contra vectores.
3. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema) — flow_uid + node_id obligatorio + constraint Neo4j 5.x.
   Bloquea el diseño del correlation-engine. CONSTRUCCIÓN, no diseño.
4. DEBT-ARGUSPP-COUNTER-DUMP-001 (P1) — volcado de contadores de aRGus a fichero parseable. Lo necesita
   el health-check de orphan_rate (Fase 2 de ADR-051) Y la cadena ADR-048. 1 sesión.
5. B = DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1) — wall-clock de aparición, 2-3 formas de flujo. Entorno
   reproducible (make crosscheck-up). Sesión propia. Recibe los inputs de calibración de ADR-051 §5.3.
6. ADR-050 (MITRE) — borrador (arrastrado, P1 para la cadena del mes). 6 vectores + bootstrap víctima +
   corrección cripto telemetría. Es el ground truth de los datasets. Trabajo de CABEZA — fresco.
7. DEBT-ARGUSPP-SURICATA-001 (P1) — Suricata en EMECAS + eve.json -> correlation-engine (Fase 2 ADR-048).
8. RSS bajo carga (arrastrado) — pipeline + tcpreplay escalonado, mide CPU/RAM 4 fuentes -> tiers RPi5/N100
   (DEBT-ARGUSPP-RESOURCE-001). Apagar ARGUS_CID_CROSSCHECK=1 para medir el hot path real.
9. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1, arrastrado) — lint CI targets duplicados. ADR-028 propuesto.

ADR-051 — DEBTs GENERADAS (todas DIFERIBLES salvo donde se indique; duermen hasta que exista engine):
- DEBT-CID-TEST-VECTORS-001 (P1, camino crítico, fixture compartido con FLOWUID) — batería V1-V4.
- DEBT-SEED-GATE-DIAGNOSTIC-001 (P1, camino crítico) — diagnóstico verbose + runbook.
- DEBT-CID-STATE-MACHINE-001 (P1) — máquinas de estado gate + confianza sensor.
- DEBT-CID-CROSSCHECK-CI-001 (P1) — crosscheck-up/run en CI (requiere Jenkins hardware FEDER).
- DEBT-CID-ORACLE-QUORUM-001 (P2) — oráculo dos niveles + quórum N>=3.
- DEBT-SEED-CHAOS-TEST-001 (P2) — pruebas de caos de drift.
- DEBT-SEED-ACTIVE-PROBE-001 (P3, DIFERIDA) — sonda activa, mitiga latencia orphan_rate en valles.
- DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (P1) — verificar que producción no heredó el reloj inyectado
  del build de cross-check (community_id_log.cpp). Bug latente, hallazgo DAY 172.

═══════════════════════════════════════════════════════════════════════════════
CONSENSO DEL CONSEJO DAY 170 — base de la arquitectura de correlación (ya ratificada en 051+052)
═══════════════════════════════════════════════════════════════════════════════
P1 (Wazuh <-> red): (A)+(C). Doble arista Neo4j. flujo<->flujo por community_id; host<->flujo por
   host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal MÁS LAXA causal-bidireccional. NAT =
   menú de mecanismos, SIEMPRE anotando método+confianza. -> ADR-052 (RATIFICADA).
P2 (seed): gate de arranque P0 data-plane + health-check huérfanos. -> ADR-051 (RATIFICADA v2.2).
P3 (identidad flujo): flow_uid = hash(node_id || community_id || flow_start_window). community_id =
   propiedad indexada, nunca identidad de nodo. -> ADR-052 (RATIFICADA) + DEBT-NEO4J-FLOW-KEY-001 (P0).

HALLAZGO TIMESTAMPS DAY 172 (sigue vigente): Suricata ancla a FIN de flujo (flow.timeout), Zeek a INICIO
de conexión, aRGus reloj sintético. Spreads 9.7ms-116s. NO comparables. Correlación temporal por WALL-CLOCK
de aparición (time.monotonic en host), nunca por ts interno. Los 5/10/20s de ADR-046 v4 son casi seguro
muy bajos para Suricata en flujos largos -> los recalibra B (DEBT-CORRELATION-TIMEOUT-CALIB-001).

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (7.0.10, community-id:yes seed 0, PROMISC)
zeek .11 (8.2.0, community-id-logging seed 0, PROMISC, escribe en /opt/zeek/spool/zeek/) · wazuh .12 (4.x)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)
NOTA: wazuh estaba 'aborted' en DAY 172 (no bloquea cross-check de los 3 sensores de red).

ARRANQUE CROSS-CHECK (reproducible, DAY 172):
- make crosscheck-up   # etcd-server-start + test-provision-1 -> trunca 3 logs ->
                       #   sniffer(ARGUS_CID_CROSSCHECK=1) -> zeekctl deploy -> confirma suricata. Idempotente.
- make crosscheck-run  # test-replay-neris -> sleep 45 -> verificador --zeek-conn /opt/zeek/spool/zeek/conn.log.
                       #   exit 2 = anomalías (esperado); exit 1 = fallo real.
- sniffer eBPF: build-active -> build-debug, ./sniffer, NO libpcap. Requiere etcd vivo + claves o aborta.
- diana: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E= sobre flujo Neris 147.32.84.165:1027 -> 74.125.232.195:80.

REGLAS CRÍTICAS:
- community_id: SHA1 (Corelight), NO HMAC-SHA256. Canonicalización byte-idéntica a Zeek/Suricata o el
  join falla en silencio. Oráculo: pycommunityid. Seed 0 idéntico en los 3 (garantizado por provisión).
- flow_uid: BLAKE2b (libsodium 1.0.19), NO la misma función que community_id. node_id = string declarado.
- Oracle divergence (ADR-051): sensores coinciden entre sí pero no con oráculo -> WARNING, arranca.
  Fail-closed SOLO por disparidad entre sensores. (N-version: 3 implementaciones independientes coincidiendo
  es evidencia fuerte de corrección; un oráculo solo discrepante es más probablemente el desfasado.)
- Helper community_id observable: gateado ARGUS_CID_CROSSCHECK=1 (OFF por defecto, coste nulo hot path).
  compute_community_id permanece PURA. Apagar para medir RSS/hot path real.
- Gate de seed: data-plane (lo que el binario EMITE), nunca config JSON/yaml.
- NAT host<->red: SIEMPRE anotar método y confianza en grafo+log. Nunca fallo silencioso por IP no coincidente.
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS = vagrant destroy -f && vagrant up && make bootstrap && make test-all.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. >1h. No negociable.
- Python3 heredoc en macOS (nunca sed -i sin -e ''). vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde (docs puras = excepción razonada).
- vendor.key nunca en disco ni repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().
- Nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; } explícito.
- DNS fix en provisions nuevos: chattr +i /etc/resolv.conf DESPUÉS de chrony.
- Nunca cat << 'EOF' anidado en <<-SHELL — usar printf.
- Idempotencia de provisión por LÍNEA, no por bloque (lección DAY 170 Zeek).
- Integridad de docs grandes: grep secciones | sort | uniq -d del fichero completo (lección DAY 170 BACKLOG).
- alert_client.hpp nunca incluido en componentes que linkan libetcd_client.so.

ENTORNO: macOS M2 Pro · i9 8 núcleos · 32GB RAM · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER: colaboración UEx/INCIBE con Dr. Andrés Caro Lindo. No deadline duro — gate real es demostrar
datasets de valor científico (curva F1 multi-fuente, ADR-048). El 22-09-2026 era referencia de ritmo.

PRIMER COMANDO DAY 174:
git status   # revisar lo de DAY 173 sin commitear (ADR-051 v2.2 + síntesis, BACKLOG, README, este prompt)
             # commitear todo en la misma piedra tras secret-scan + uniq -d
             # LUEGO: bajar a DEBT-NODEID/FLOWUID/NEO4J-FLOW-KEY. CONSTRUIR el engine, no más ADRs.
