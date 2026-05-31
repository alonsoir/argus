DAY 171 — aRGus NDR (arXiv:2604.04952)

Estado: rama feature/day170-community-id-protobuf @ af9cd812 (community_id cross-sensor + de-dup BACKLOG + provisión Zeek/Suricata). Tag estable v1.0.0-day166.
DAY 170 cerrado: community_id sellado en aRGus(nativo)+Zeek+Suricata con seed 0 explícito; BACKLOG de-duplicado (5336->2839); ritual del Consejo completado (síntesis en docs/counsil/). Consenso 8/8 en P1/P2/P3.

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 167: NTP/chrony (P0). correlation-engine scaffold (ADR-048 F2). Jenkins gate make emecas++.
DAY 168: Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24.
DAY 169: Día de arquitectura. ADR-046 v4 + AdapterSpec v1 + separación de planos. ADR-050 (MITRE) pendiente.
DAY 170: community_id cross-sensor (3 sensores, seed 0, byte a byte vs oráculo pycommunityid; diana 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=). De-dup BACKLOG (DEBT-DOCS-BACKLOG-DEDUP-001). Consejo 8/8.

═══════════════════════════════════════════════════════════════════════════════
CONSENSO DEL CONSEJO DAY 170 — base de DAY 171 (síntesis en docs/counsil/)
═══════════════════════════════════════════════════════════════════════════════
P1 (Wazuh <-> red): (A)+(C). Doble arista en Neo4j. flujo<->flujo por community_id (determinista);
   host<->flujo por host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal MÁS LAXA y
   causal-bidireccional. NAT = menú de mecanismos, SIEMPRE anotando método y confianza en grafo+log.
   (B) solo enriquecimiento oportunista, nunca base.
P2 (seed): gate de arranque P0 (análogo NTP) + health-check huérfanos continuo. Basado en DATA-PLANE:
   se mide el community_id que cada sensor EMITE en runtime, NO se lee config JSON/yaml (el fichero miente).
   -> ADR-051 + DEBT-CORRELATION-SEED-GATE-001.
P3 (identidad flujo multi-nodo): flow_uid = hash(node_id || community_id || flow_start_window).
   community_id permanece como propiedad indexada (clave de correlación + verificable contra oráculo),
   nunca como identidad de nodo. Decidir con grafo vacío = gratis; retrofit = doloroso.
   -> ADR-052 + DEBT-NEO4J-FLOW-KEY-001 (P0 esquema).

NUMERACIÓN ADR (verificado contra BACKLOG): ADR-050 ya cogido (MITRE, pendiente). Nuevos: 051 y 052.

═══════════════════════════════════════════════════════════════════════════════
PRIORIDAD DAY 171 #1 — cross-check E2E community_id (tres ventanas)
═══════════════════════════════════════════════════════════════════════════════
Cierra la paridad OPERACIONAL del community_id (la de especificación + provisión ya está).
1. Cliente .50 replaya el flujo Neris por eth1 (tcpreplay) en la LAN ml_defender_gateway_lan.
2. aRGus + Suricata + Zeek capturan en PARALELO de eth1 (promiscuo) — el MISMO paquete.
3. Verificar que los 3 emiten el MISMO community_id STRING A STRING (diana 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=).
   No confiar en que coincidan: OBSERVARLO sobre el mismo paquete real.
4. Añadidos del Consejo (Kimi/Grok/Mistral):
   - Registrar por sensor: community_id + timestamp relativo de emisión + nº de paquete/flow.
     (los 3 pueden converger en valor pero diferir en CUÁNDO emiten — Suricata flow.timeout, Zeek cierre TCP).
   - Caso con IPs invertidas (paquete de respuesta) -> mismo community_id (bidireccionalidad canónica).
   - NAT simulado si es viable.
Resultado verde -> el join red<->red basado en community_id es viable en producción, no solo en lab.

PRIORIDAD DAY 171 (resto, arrastrado de DAY 170 + nuevo del Consejo):
2. ADR-051 (Seed Parity Gate & Correlation Health) — borrador para el Consejo. Recoge P2.
3. ADR-052 (Multi-node Flow Identity & Host<->Net Correlation) — borrador para el Consejo. Recoge P3+P1.
4. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema) — diseñar flow_uid + node_id obligatorio + constraint Neo4j 5.x
   ANTES de poblar el grafo. Bloquea el diseño del correlation-engine.
5. RSS bajo carga (arrastrado DAY 170) — pipeline + client + tcpreplay escalonado. Mide CPU/RAM de las
   4 fuentes -> calibra tiers RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001). NO necesita víctima MITRE.
6. ADR-050 (MITRE) — borrador (arrastrado). 6 vectores + bootstrap víctima + corrección cripto telemetría.
7. DEBT-ARGUSPP-SURICATA-001 (P1) — Suricata en EMECAS + eve.json -> correlation-engine.
8. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1, arrastrado) — lint CI targets duplicados CMake. ADR-028 propuesto.

DEUDAS ABIERTAS NUEVAS DAY 170 (Consejo):
- ADR-051 — Seed Parity Gate & Correlation Health (data-plane). Borrador pendiente.
- ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. Borrador pendiente.
- DEBT-NEO4J-FLOW-KEY-001 — flow_uid temporal compuesto (P0 esquema).
- DEBT-CORRELATION-SEED-GATE-001 — gate data-plane + health-check huérfanos (P1).
- BACKLOG-RESEARCH-NAT-HOSTNET-001 — puente host<->red bajo NAT (RESEARCH). Prereq: Wazuh.

DEUDAS ABIERTAS RELEVANTES (arrastradas):
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json -> correlation-engine. P1.
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER. P2. (clave correlación = diseño abierto, host-based)
- DEBT-ARGUSPP-MITRE-001 — script ataque MITRE con atomic-red-team (post-FEDER). ADR-047.
- DEBT-ARGUSPP-RESOURCE-001 — medir CPU/RAM/disco 4 fuentes en RPi5/N100. P1 con hardware.
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake. P1.
- ADR-050 — sesión MITRE + corrección cripto telemetría. Borrador pendiente.

PENDIENTE DE PROPAGACIÓN (cuando correlation-engine gradúe de scaffold):
- Makefile: target `cp network_security.pb.*` + meterlo en scripts/verify_protobuf.sh
  (DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 dejó esto anotado P0 para cuando el engine consuma el campo).

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (Suricata 7.0.10, community-id:yes seed 0, PROMISC)
zeek .11 (Zeek 8.2.0, community-id-logging seed 0, PROMISC) · wazuh .12 (Wazuh 4.x, NTP OK)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión) · eth1: intnet (tráfico ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta -> todos los engines ven el mismo flujo -> community_id coherente (seed 0 en los 3)
- correlation-engine: source_wait_timeout argus=5s/suricata=10s/zeek=20s/wazuh=90s; crisis_idle 120s
- Neo4j: grafo de correlación cross-engine. Identidad de nodo-flujo = flow_uid (P3). Post-FEDER.
- separación de planos (DAY 169): datos / correlación (CrisisWindow + community_id) / decisión.
  AdapterSpec v1 = contrato del adaptador por fuente.

REGLAS CRÍTICAS:
- community_id: canonicalización byte-idéntica a Zeek/Suricata o el join falla en silencio.
  Verificar con pycommunityid (oráculo). Seed 0 idéntico en los 3 (garantizado por provisión DAY 170).
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

PRIMER COMANDO DAY 171:
git checkout feature/day170-community-id-protobuf && vagrant up suricata zeek defender client
