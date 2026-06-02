DAY 173 — aRGus NDR (arXiv:2604.04952)

ÚLTIMO HITO DAY 173: ADR-052 v3.2 RATIFICADA por el Consejo (8/8, confirmación de fidelidad sin reservas,
sin 3ª deliberación). Entregable ADR-052_v3.2.md. Genera las DEBTs P0->P3 de identidad de flujo (abajo) y
el stub ADR-053. PENDIENTE aún en DAY 173: commit/push DAY 172, ADR-051 borrador, y empezar las DEBTs P0
(NODEID + FLOWUID + NEO4J-FLOW-KEY) que ADR-052 desbloquea.


Estado: rama feature/day170-community-id-protobuf (community_id cross-sensor + cross-check E2E operacional). Tag estable v1.0.0-day166.
DAY 172 cerrado: cross-check E2E community_id REPRODUCIDO (agree=1029 y 788 en dos corridas) tras reconstruir el entorno multi-VM completo, que NO era reproducible. Verificador parcheado con Opción A (delta inicio de flujo, sanity check). Dos targets nuevos en Makefile (crosscheck-up / crosscheck-run) que automatizan los ~20 comandos de arranque. Tres deudas nuevas registradas. PENDIENTE de commit/push DAY 172.

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 168: Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24.
DAY 169: Día de arquitectura. ADR-046 v4 + AdapterSpec v1 + separación de planos. ADR-050 (MITRE) pendiente.
DAY 170: community_id cross-sensor (3 sensores, seed 0, byte a byte vs oráculo). De-dup BACKLOG. Consejo 8/8 P1/P2/P3.
DAY 171: cross-check E2E 3 ventanas VERDE (paridad operacional). Helper observable + verificador + acceptance_criteria.md congelado. COMMITEADO en 0481d1e3.
DAY 172: entorno reproducido + Opción A entregada + crosscheck-up/run + 3 deudas nuevas. (detalle abajo)

═══════════════════════════════════════════════════════════════════════════════
PRIMERO DE TODO DAY 173 — commit/push de DAY 172 (NO se hizo)
═══════════════════════════════════════════════════════════════════════════════
Sin commitear de DAY 172: tools/community_id_crosscheck.py (parche Opción A), los dos targets
nuevos en Makefile (crosscheck-up / crosscheck-run), y las entradas nuevas en docs/BACKLOG.md
(DEBT-CORRELATION-TIMEOUT-CALIB-001 + hallazgos, DEBT-MAKEFILE-CID-CROSSCHECK-001 cerrada,
DEBT-ZEEK-AUTOSTART-001, DEBT-ZEEK-LOGPATH-001). Commitear todo en la misma piedra.
Verificar antes: git status; git diff --cached | grep -iE 'PRIVATE KEY|vendor.key|password|token';
grep -E '^## ✅ CERRADO DAY' docs/BACKLOG.md | sort | uniq -d (vacío).
Limpieza BACKLOG ya aplicada DAY 172: script fix_backlog_day172.py movió el "Hallazgo DAY 172
(corrida real)" de bajo MAKEFILE-CID a dentro de CALIB-001 (su sitio correcto). Verificar con
grep -n 'corrida real' docs/BACKLOG.md (1 sola línea, dentro de CALIB-001).
Arrastrado sin urgencia: enterprise/enterprise_vendor.pub trackeada (git rm --cached + el patrón
está DUPLICADO en .gitignore, dedupar la línea). sniffer/build/ ya está limpio.

═══════════════════════════════════════════════════════════════════════════════
LO QUE PASÓ DE VERDAD EN DAY 172 — el entorno NO era reproducible
═══════════════════════════════════════════════════════════════════════════════
El objetivo era trivial (commitear DAY 171, ya estaba hecho) pero al re-correr el cross-check
el entorno estaba caído en TRES sitios distintos. Hallazgo central del día: el VERDE de DAY 171
no era reproducible sin pasos manuales no documentados. Resuelto con automatización.

1. SNIFFER fail-closed sin etcd: el sniffer aborta limpio si etcd-server no está vivo
   ("hardcoded keys NOT acceptable"). No es standalone — arranca el plano cripto en boot.
   Mínimo para cross-check = sniffer + etcd-server + test-provision-1 (siembra claves).
2. ARGUS_CID_CROSSCHECK=1 NO estaba en el Makefile: el cross-check de DAY 171 se lanzó a mano.
   El binario sí tiene el helper compilado (strings confirma ARGUS_CID_CROSSCHECK + cid_crosscheck_enabled).
   build correcto: build-active -> build-debug (eBPF, ./sniffer). NO libpcap.
3. ZEEK parado y mal configurado: zeekctl no estaba en PATH (/opt/zeek/bin/zeekctl ruta completa).
   zeekctl deploy arranca Zeek en eth1 (interface=eth1 ya en node.cfg) PERO escribe conn.log en su
   SPOOL (/opt/zeek/spool/zeek/conn.log), NO en /vagrant/logs/lab/zeek/. El verificador necesita
   --zeek-conn /opt/zeek/spool/zeek/conn.log hasta que DEBT-ZEEK-LOGPATH-001 se cierre.

SOLUCIÓN (cierra DEBT-MAKEFILE-CID-CROSSCHECK-001): dos targets en Makefile, demostrados en caliente.
  make crosscheck-up   # etcd-server-start + test-provision-1 -> trunca 3 logs -> sniffer(ARGUS_CID_CROSSCHECK=1)
                       #   -> zeekctl deploy -> confirma suricata. Checks OK/XX por paso, exit 1 si falla.
  make crosscheck-run  # test-replay-neris -> sleep 45 (drenaje) -> verificador con --zeek-conn spool.
                       #   exit 2 = hay anomalías (esperado, NO rompe el target); exit 1 = fallo real (rompe).
Reemplaza los ~20 comandos manuales de hoy por dos make. crosscheck-up es idempotente.

═══════════════════════════════════════════════════════════════════════════════
OPCIÓN A ENTREGADA + HALLAZGO REPRODUCIBLE (alimenta B = DEBT-CORRELATION-TIMEOUT-CALIB-001)
═══════════════════════════════════════════════════════════════════════════════
La "DELTA DE TIEMPOS" del Consejo DAY 170 se atacó en dos partes:
- Opción A (HECHA): el verificador ahora lee el timestamp INTERNO de cada registro y reporta el
  spread por cid en agree. Sanity check temporal, NO source_wait_timeout.
- HALLAZGO (reproducible en 2 corridas): NO se puede medir delta restando timestamps internos.
  Suricata (eve.json .timestamp en eventos flow) ancla a FIN de flujo (flow.timeout); Zeek
  (conn.log ts) ancla a INICIO de conexión. Spreads 9.7ms (flujos cortos) a ~116s (largos).
  Miden eventos DISTINTOS -> no comparables. CONSECUENCIA: B debe medir source_wait_timeout por
  WALL-CLOCK de aparición (time.monotonic en host), nunca por ts interno. Y los 5/10/20s supuestos
  de ADR-046 v4 son casi seguro MUY bajos para Suricata en flujos largos.
- aRGus EXCLUIDO del delta: su TSV estampa timestamp SINTÉTICO (contador 1.7e18+N, no system_clock).
  community_id_log.cpp corre bajo reloj inyectado en el build de cross-check. El verificador lo
  neutraliza a ts=0.0. PENDIENTE VERIFICAR: ¿el path de PRODUCCIÓN heredó el reloj inyectado? (bug latente).

═══════════════════════════════════════════════════════════════════════════════
CONSENSO DEL CONSEJO DAY 170 — sigue siendo la base de la arquitectura de correlación
═══════════════════════════════════════════════════════════════════════════════
P1 (Wazuh <-> red): (A)+(C). Doble arista en Neo4j. flujo<->flujo por community_id (determinista);
   host<->flujo por host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal MÁS LAXA y
   causal-bidireccional. NAT = menú de mecanismos, SIEMPRE anotando método y confianza en grafo+log.
P2 (seed): gate de arranque P0 (análogo NTP) + health-check huérfanos continuo. Basado en DATA-PLANE:
   se mide el community_id que cada sensor EMITE en runtime, NO se lee config JSON/yaml.
   El cross-check E2E de DAY 171 es la PRIMERA validación práctica de este principio.
   -> ADR-051 + DEBT-CORRELATION-SEED-GATE-001.
P3 (identidad flujo multi-nodo): flow_uid = hash(node_id || community_id || flow_start_window).
   community_id permanece como propiedad indexada (clave de correlación + verificable contra oráculo),
   nunca como identidad de nodo. -> ADR-052 + DEBT-NEO4J-FLOW-KEY-001 (P0 esquema).

NUMERACIÓN ADR (verificado contra BACKLOG): ADR-050 ya cogido (MITRE, pendiente). Nuevos: 051 y 052.

PRIORIDAD DAY 173 (arrastrado + nuevo):
1. commit/push DAY 172 (arriba).
2. ADR-051 (Seed Parity Gate & Correlation Health) — borrador para el Consejo. Recoge P2. El cross-check
   E2E (data-plane) es ya la evidencia empírica del gate. Trabajo de CABEZA — hacerlo fresco.
3. ✅ ADR-052 v3.2 RATIFICADA (Consejo 8/8, DAY 173) — Multi-node Flow Identity & Host<->Net Correlation.
   Confirmación de fidelidad unánime, sin 3a deliberacion. flow_uid = base64(BLAKE2b(node_id || community_id ||
   flow_start_window [|| seq_in_window])); node_id = string legible declarado (no keypair efimero); community_id =
   clave de correlacion, nunca identidad. Anulaciones de arbitro: hash libsodium (3.1.1) + TCP/TLS host (3.11).
   Entregable ADR-052_v3.2.md. DESBLOQUEA DEBT-NEO4J-FLOW-KEY-001 (#4). Genera DEBTs P0->P3 de identidad de flujo
   (ver lista de deudas) + stub ADR-053 (JA3/JA4, TLS profundo, BGP). ADR-051 (#2) SIGUE pendiente de redaccion.
4. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema) — flow_uid + node_id obligatorio + constraint Neo4j 5.x ANTES
   de poblar el grafo. Bloquea el diseño del correlation-engine. VA DESPUÉS de ADR-052 (lo ratifica).
5. DEBT-ARGUSPP-COUNTER-DUMP-001 (P1) — volcado de contadores de aRGus a fichero parseable. Necesario
   para que el health-check de huérfanos (community_id.orphan_rate de ADR-051) tenga la cifra de aRGus
   con que comparar. 2->3 es correcto: sin el volcado, orphan_rate es aspiracional.
6. B = DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1) — refactor verificador one-shot->poll, medir wall-clock
   de aparición sobre 2-3 FORMAS de flujo. Entorno ya reproducible (make crosscheck-up). Sesión propia.
7. RSS bajo carga (arrastrado) — pipeline + client + tcpreplay escalonado. Mide CPU/RAM de las 4 fuentes
   -> calibra tiers RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001). NO necesita víctima MITRE. Apagar
   ARGUS_CID_CROSSCHECK=1 para medir el hot path real.
8. ADR-050 (MITRE) — borrador (arrastrado). 6 vectores + bootstrap víctima + corrección cripto telemetría.
9. DEBT-ARGUSPP-SURICATA-001 (P1) — Suricata en EMECAS + eve.json -> correlation-engine.
10. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1, arrastrado) — lint CI targets duplicados CMake. ADR-028 propuesto.

DEUDAS ABIERTAS RELEVANTES (arrastradas + nuevas DAY 172):
- DEBT-CORRELATION-TIMEOUT-CALIB-001 — B: wall-clock de aparición, 2-3 formas de flujo (P1, NUEVA DAY 172).
- DEBT-MAKEFILE-CID-CROSSCHECK-001 — CERRADA DAY 172 (crosscheck-up/run en Makefile, demostrados).
- DEBT-ZEEK-AUTOSTART-001 — Zeek no arranca solo; hoy a mano con zeekctl deploy (NUEVA DAY 172).
- DEBT-ZEEK-LOGPATH-001 — Zeek escribe en spool, no en /vagrant/logs/lab/zeek/. Cuando cierre,
  cambiar la ruta --zeek-conn hardcodeada en el target crosscheck-run (NUEVA DAY 172).
- DEBT-ARGUSPP-COUNTER-DUMP-001 — volcado contadores aRGus a fichero parseable (P1, DAY 171).
- ADR-051 — Seed Parity Gate & Correlation Health (data-plane). Borrador pendiente.
- ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. RATIFICADA v3.2 (8/8, DAY 173). Entregable ADR-052_v3.2.md.
- ADR-053 — JA3/JA4, cadena TLS profunda, anomalia de ruta L3/BGP. STUB (diferido de ADR-052). Borrador pendiente.
- DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id = string declarado en inventario firmado, no keypair efimero (P0, ADR-052 C1). Desbloquea Neo4j.
- DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificacion canonica BLAKE2b + paridad C++/Python + seq_in_window transportado + caso 2-sensores (P0, ADR-052).
- DEBT-SENSOR-COVERAGE-MAP-001 — mapa sensor<->segmento declarativo, versionado, beacons (P1, ADR-052 3.8). Prereq de orphan_rate/IPW.
- DEBT-LABEL-WAL-001 — WAL externo append-only hash-chain (prev_hash), Neo4j vista materializada, doble deteccion (P1, ADR-052 3.7).
- DEBT-ARGUSPP-ARP-MONITOR-001 — ARP/NDP como :IpMacBinding, re-binding=senal vector A L2 (P1, ADR-052 3.9).
- DEBT-ARGUSPP-HOST-TCP-001 — senales TCP host RST/seqnum, vector A ampliado (P1, ADR-052 3.11a).
- DEBT-CERT-EXPECTATION-STORE-001 — store expectativa cert para mismatch TLS; cobertura L7 asimetrica hasta cerrarlo (P2, ADR-052 C2/R1).
- DEBT-SEQWINDOW-PERSIST-001 — persistencia fsync de seq_in_window en sensor (P2, ADR-052).
- DEBT-ARGUSPP-OOB-MITM-001 — fuente out-of-band (port-security/SPAN/Canary) para vector A con host comprometido (P2, ADR-052 3.4.1).
- DEBT-CORPUS-QUALITY-METRICS-001 — KPIs corpus 0.1; confianza-corroboracion vs peso-de-dedup separados; IPW en ADR-040 (P2, ADR-052).
- DEBT-ARCH-FLOW-OBSERVATION-001 — separar FlowObservation de FlowIdentity (P3, ADR-052).
- DEBT-NEO4J-FLOW-KEY-001 — flow_uid temporal compuesto (P0 esquema).
- DEBT-CORRELATION-SEED-GATE-001 — gate data-plane + health-check huérfanos (P1).
- BACKLOG-RESEARCH-NAT-HOSTNET-001 — puente host<->red bajo NAT (RESEARCH). Prereq: Wazuh.
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json -> correlation-engine. P1.
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER. P2.
- DEBT-ARGUSPP-MITRE-001 — script ataque MITRE con atomic-red-team (post-FEDER). ADR-047.
- DEBT-ARGUSPP-RESOURCE-001 — medir CPU/RAM/disco 4 fuentes en RPi5/N100. P1 con hardware.
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake. P1.
- ADR-050 — sesión MITRE + corrección cripto telemetría. Borrador pendiente.
- POSIBLE-FUTURA: triage de anomalías del cross-check — clasificar las ~14k anomaly por protocolo
  para separar cobertura asimétrica legítima (aRGus solo TCP/UDP) de pérdida REAL de TCP/UDP que
  aRGus debería haber visto. El anomalies.tsv se vuelca pero nunca se ha mirado. No urge.

PENDIENTE DE PROPAGACIÓN (cuando correlation-engine gradúe de scaffold):
- Makefile: target `cp network_security.pb.*` + meterlo en scripts/verify_protobuf.sh
  (DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 dejó esto anotado P0 para cuando el engine consuma el campo).

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (Suricata 7.0.10, community-id:yes seed 0, PROMISC)
zeek .11 (Zeek 8.2.0, community-id-logging seed 0, PROMISC, escribe en /opt/zeek/spool/zeek/) · wazuh .12 (Wazuh 4.x)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)
NOTA: wazuh estaba 'aborted' en DAY 172 (no bloquea cross-check de los 3 sensores de red).

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión) · eth1: intnet (tráfico ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta -> todos los engines ven el mismo flujo -> community_id coherente (seed 0 en los 3)
- correlation-engine: source_wait_timeout argus=5s/suricata=10s/zeek=20s/wazuh=90s; crisis_idle 120s
  (OJO: estos timeouts son SUPUESTOS; B los va a recalibrar con datos reales)
- Neo4j: grafo de correlación cross-engine. Identidad de nodo-flujo = flow_uid (P3). Post-FEDER.
- separación de planos (DAY 169): datos / correlación (CrisisWindow + community_id) / decisión.
  AdapterSpec v1 = contrato del adaptador por fuente.

ARRANQUE CROSS-CHECK (DAY 172, reproducible):
- sniffer eBPF: build-active -> build-debug, ./sniffer, env ARGUS_CID_CROSSCHECK=1, NO libpcap.
- sniffer requiere etcd-server vivo + claves sembradas (test-provision-1) o aborta fail-closed.
- zeek: /opt/zeek/bin/zeekctl deploy (ruta completa, no en PATH). Escribe en /opt/zeek/spool/zeek/conn.log.
- diana: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E= sobre flujo Neris 147.32.84.165:1027 -> 74.125.232.195:80.

REGLAS CRÍTICAS:
- community_id: SHA1 (Corelight), NO HMAC-SHA256 (Qwen/Mistral lo escribieron mal en el Consejo).
  Canonicalización byte-idéntica a Zeek/Suricata o el join falla en silencio. Oráculo: pycommunityid.
  Seed 0 idéntico en los 3 (garantizado por provisión). Paridad operacional verificada DAY 171/172.
- Helper community_id observable: gateado ARGUS_CID_CROSSCHECK=1 (OFF por defecto, coste nulo hot path).
  compute_community_id permanece PURA — el log vive en los call-sites, no dentro.
- TIMESTAMPS INTERNOS NO COMPARABLES entre sensores (hallazgo DAY 172): Suricata ancla fin-flujo,
  Zeek inicio-conexión, aRGus reloj sintético. Para correlación temporal usar wall-clock de aparición.
- Gate de seed (futuro): basado en data-plane (lo que el binario EMITE), nunca en config JSON/yaml.
- Identidad de flujo Neo4j: flow_uid = hash(node_id || community_id || flow_start_window). community_id es
  propiedad indexada, no identidad de nodo.
- NAT host<->red: SIEMPRE anotar método y confianza en grafo+log. Nunca fallo silencioso por IP no coincidente.
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
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

PRIMER COMANDO DAY 173:
git status   # revisar lo de DAY 172 sin commitear (verificador, 2 targets Makefile, 3 deudas BACKLOG)
             # commitear todo en la misma piedra tras secret-scan + uniq -d
