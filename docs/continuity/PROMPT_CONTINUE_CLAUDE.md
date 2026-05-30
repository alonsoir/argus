DAY 170 — aRGus NDR (arXiv:2604.04952)

Estado: main @ 96d88338 (post-merge docs DAY 169). Tag estable v1.0.0-day166.
Rama activa: feature/day170-community-id-protobuf (creada, vacía).
DAY 169 fue día de arquitectura: ADR-046 v4 + AdapterSpec v1 + separación de planos. Sin código.

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 164-166: Enterprise crypto lifecycle. EMECAS++ 3 actos. Tag v1.0.0-day166.
DAY 167: DEBT-ARGUSPP-NTP-001 (P0) ✅ chrony, health-check rechaza offset >1s.
correlation-engine scaffold (ADR-048 F2). BACKLOG-CI-ENTERPRISE-001 ✅ Jenkins gate make emecas++.
Merge a main → 7b45feca.
DAY 168: Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24.
community-id habilitado en Suricata y Zeek. 50.248 reglas ET Open. Merge a main → 21642e87.
DAY 169: Día de arquitectura. ADR-046 v4 APROBADO. AdapterSpec v1 CERRADO. ADR-050 PENDIENTE
(seis vectores MITRE + corrección cripto telemetría). Docs 167/168/169 mergeadas → 96d88338.

═══════════════════════════════════════════════════════════════════════════════
PRIORIDAD DAY 170 #1 (P0) — community_id NATIVO en aRGus
═══════════════════════════════════════════════════════════════════════════════
community_id viene de fábrica en Suricata/Zeek/Wazuh, pero NO en aRGus. Es el pegamento
del join cross-tool y el gate del dataset federado.

LA TRANQUILIDAD: NO es ingeniería inversa. Es un ESTÁNDAR ABIERTO documentado.
Community ID Flow Hashing — Corelight (Christian Kreibich).
Spec: https://github.com/corelight/community-id-spec
Oráculo de referencia: pycommunityid (paquete Python con test suite).
Suricata, Zeek y Wireshark lo implementan todos contra la MISMA spec.

FÓRMULA v1:
community_id = "1:" + base64( sha1( seed ‖ 5-tupla-canónica ) )

RECETA DE BYTES EXACTA (orden de concatenación — verificado en impl. de referencia):
seed ‖ saddr ‖ daddr ‖ proto ‖ padding(00) ‖ sport ‖ dport
1. seed   — uint16 BIG-ENDIAN. Default 0 (00:00). DEBE ser idéntico en las 4 herramientas
   y en aRGus. Suricata: community-id-seed. Zeek: igual. Verificar que coinciden.
2. ENDPOINTS CANÓNICOS — ordenar los dos (ip,port): el "menor" primero. Comparar primero
   por IP (como bytes), si empatan por puerto. Esto hace A→B == B→A (bidireccional).
   SALTARSE ESTO O HACERLO AL REVÉS = ID no coincide con Zeek. Es el catch de Kimi.
3. IPs    — forma BINARIA (4 bytes IPv4 / 16 bytes IPv6), nunca string.
4. proto  — número IANA en 1 BYTE: TCP=0x06, UDP=0x11(17), ICMP=0x01. NUNCA string "tcp".
5. padding— 1 byte 0x00 tras el proto.
6. puertos— uint16 BIG-ENDIAN cada uno, en orden canónico.
   Luego SHA1 (20 bytes) → base64 → prefijo "1:".

VECTOR DE PRUEBA conocido (seed 0):
tcp 128.232.110.120 66.35.250.204 34855 80  →  1:LQU9qZlK+B5F3KDmev6m5PMibrg=

ICMP tiene tratamiento especial: mapea type/code a pseudo-puertos (inspirado en Zeek).
Para el primer corte: limitar a TCP/UDP. Dejar ICMP como sub-tarea documentada.

PLAN DE IMPLEMENTACIÓN (orden que minimiza retrabajo):
1. protobuf/network_security.proto → campo community_id (string, field ~20).
   protobuf3 backwards-compatible: ml-detector y firewall siguen compilando sin tocarlos.
2. Instalar pycommunityid como ORÁCULO. Generar fixture: 5-tuplas conocidas → ID esperado.
3. Sniffer: implementar la receta (libsodium da SHA1; ensamblar buffer en el orden + base64).
4. Test unitario RED→GREEN contra los vectores del oráculo. Diff byte a byte = 0.
5. Test E2E real: client inyecta por eth1 → capturar mismo flujo en aRGus + Suricata + Zeek
   simultáneamente → confirmar los 3 community_id idénticos STRING A STRING.
   Este es el test que valida de verdad — no confías en que coincidan, lo OBSERVAS sobre
   el mismo paquete real.
6. Propagar: sniffer → ml-detector → correlation-engine.

PRIORIDAD DAY 170 (resto):
2. RSS bajo carga — lo más barato que cierra el debate de hardware con evidencia.
   pipeline + client + tcpreplay escalonado. NO necesita la víctima MITRE.
   Medir CPU/RAM de las 4 fuentes → calibra tiers RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001).
3. ADR-050 — borrador para el Consejo (6 vectores MITRE + bootstrap víctima + corrección cripto).
   Flujo: borrador → Consejo → aprobación → implementación (como ADR-046).
4. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1) — lint CI targets duplicados CMake. Arrastrado.
   ChatGPT/Kimi: check cmake -DARGUS_VAULT_ENABLED=ON + grep target dup. ADR-028 propuesto.

DEUDAS ABIERTAS RELEVANTES:
- DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 — community_id nativo aRGus (protobuf+sniffer). P0.
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json → correlation-engine. P1.
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER. P2.
- DEBT-ARGUSPP-MITRE-001 — script ataque MITRE con atomic-red-team (post-FEDER). ADR-047.
- DEBT-ARGUSPP-RESOURCE-001 — medir CPU/RAM/disco 4 fuentes en RPi5/N100. P1 con hardware.
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake. P1.
- ADR-050 — sesión MITRE + corrección cripto telemetría. Borrador pendiente.

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (Suricata 7.0.10, community-id:yes, PROMISC)
zeek .11 (Zeek 8.2.0, community-id-v1, PROMISC) · wazuh .12 (Wazuh 4.x, NTP OK)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión) · eth1: intnet (tráfico ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta → todos los engines ven el mismo flujo → community_id coherente
- correlation-engine: source_wait_timeout argus=5s/suricata=10s/zeek=20s/wazuh=90s; crisis_idle 120s
- Neo4j: grafo de correlación cross-engine sobre community_id (post-FEDER)
- separación de planos (DAY 169): datos / correlación (CrisisWindow + community_id) / decisión.
  AdapterSpec v1 = contrato del adaptador por fuente.

REGLAS CRÍTICAS:
- community_id: canonicalización byte-idéntica a Zeek/Suricata o el join falla en silencio.
  Verificar con pycommunityid (oráculo) ANTES de declarar cerrado. Seed idéntico en las 4.
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. >1h. No negociable.
- Python3 heredoc en macOS (nunca sed -i sin -e ''). vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde (docs puras = excepción razonada).
- vendor.key nunca en disco ni repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().
- Nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; } explícito.
- DNS fix en provisions nuevos: chattr +i /etc/resolv.conf DESPUÉS de chrony.
- Nunca cat << 'EOF' anidado en <<-SHELL — usar printf.
- alert_client.hpp nunca incluido en componentes que linkan libetcd_client.so.

ENTORNO: macOS M2 Pro · i9 8 núcleos · 32GB RAM · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER: colaboración UEx/INCIBE con Dr. Andrés Caro Lindo. No deadline duro — gate real es demostrar
datasets de valor científico (curva F1 multi-fuente, ADR-048). El 22-09-2026 era referencia de ritmo.

PRIMER COMANDO DAY 170:
git checkout feature/day170-community-id-protobuf && cat protobuf/network_security.proto