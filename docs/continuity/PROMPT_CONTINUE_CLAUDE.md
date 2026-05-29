DAY 170 — aRGus NDR (arXiv:2604.04952)

Estado: main @ 21642e87 (post-merge DAY 168). Tag estable v1.0.0-day166.
Rama activa: ninguna — DAY 169 fue día de arquitectura sin merge de código.
Próxima rama sugerida: feature/day170-community-id-protobuf

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 164-166: Enterprise crypto lifecycle completo. EMECAS++ 3 actos. Merge a main. Tag v1.0.0-day166.
DAY 167: DEBT-ARGUSPP-NTP-001 (P0) ✅ — chrony en todos los nodos, health-check rechaza offset >1s.
correlation-engine scaffold (ADR-048 F2). BACKLOG-CI-ENTERPRISE-001 ✅ — Jenkins gate make emecas++
(11 pasadas hasta verde). Merge a main → 7b45feca.
DAY 168: Vagrantfile multi-VM: Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en ml_defender_gateway_lan
(192.168.100.0/24). community-id habilitado en Suricata y Zeek. 50.248 reglas ET Open.
WAZUH_MANAGER_PASSWORD eliminado (fix seguridad). Merge a main → 21642e87.
DAY 169: Día de arquitectura. ADR-046 v4 APROBADO (Multi-Source Pipeline, separación de planos).
AdapterSpec v1 CERRADO (contrato del adaptador por fuente). ADR-050 PENDIENTE de redacción
(seis vectores de la sesión MITRE + corrección cripto del canal de telemetría).
Documentación 167/168/169 actualizada en local (script update_docs_day169.py).

CLARIFICACIÓN IMPORTANTE sobre community_id:
community_id viene de fábrica en Suricata, Zeek y Wazuh, pero NO en aRGus.
No está calculado en el sniffer ni hay campo en el protobuf. Es el gate real del dataset federado.

VMs (autostart: false — arrancar individualmente):
defender   192.168.100.1   aRGus NDR completo (primary)
suricata   192.168.100.10  Suricata 7.0.10, AF_PACKET, community-id:yes, PROMISC
zeek       192.168.100.11  Zeek 8.2.0, community-id-v1, PROMISC
wazuh      192.168.100.12  Wazuh 4.x manager running, NTP OK
client     192.168.100.50  tcpreplay + nmap/hydra/sqlmap/atomic-red-team

PRIORIDAD DAY 170 (en orden):
1. DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 (P0) — community_id nativo en aRGus
   - protobuf/network_security.proto → añadir campo community_id (string, field ~20)
     protobuf3 backwards-compatible: campos nuevos no rompen componentes existentes
   - sniffer: calcular community_id = SHA1(5-tupla: src_ip+dst_ip+src_port+dst_port+proto)
   - propagar: sniffer → ml-detector → correlation-engine
   - CATCH CRÍTICO (Kimi, gate real): canonicalización idéntica byte a byte a Zeek/Suricata.
     proto NUMÉRICO (6/17) no string ("tcp"); orden de endpoints normalizado (menor primero).
     Si difiere → join cross-tool falla EN SILENCIO. Es el mismo bug de endianness del inicio.
     Verificación obligatoria: misma 5-tupla → mismo ID en las 4 herramientas, diff a mano = 0.
2. RSS bajo carga (lo más barato que cierra el debate de hardware con evidencia)
   - pipeline + client + tcpreplay escalonado. No necesita la víctima MITRE.
   - Medir CPU/RAM de las 4 fuentes bajo carga → calibra tiers RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001)
3. ADR-050 — borrador para el Consejo (Claude tiene los 6 vectores + bootstrap + corrección cripto)
   - flujo: borrador → Consejo → aprobación → implementación (como ADR-046)
4. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1) — lint CI targets duplicados CMake
   - arrastrado desde DAY 169. ChatGPT/Kimi: check cmake -DARGUS_VAULT_ENABLED=ON + grep target dup.
   - ADR propuesto: docs/adr/adr-028-cmake-target-naming.md

DEUDAS ABIERTAS RELEVANTES:
- DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 — community_id nativo aRGus (protobuf+sniffer). P0.
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json → correlation-engine. P1.
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER. P2.
- DEBT-ARGUSPP-MITRE-001 — script ataque MITRE con atomic-red-team (post-FEDER). ADR-047.
- DEBT-ARGUSPP-RESOURCE-001 — medir CPU/RAM/disco 4 fuentes en RPi5/N100. P1 con hardware.
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake. P1.
- ADR-050 — sesión MITRE + corrección cripto telemetría. Borrador pendiente.

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión)
- eth1: intnet ml_defender_gateway_lan (tráfico de ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta tráfico → todos los engines ven el mismo flujo → community_id coherente
- correlation-engine: source_wait_timeout argus=5s/suricata=10s/zeek=20s/wazuh=90s; crisis_idle 120s
- Neo4j: grafo de correlación cross-engine sobre community_id (post-FEDER)
- separación de planos (DAY 169): datos (telemetría cruda por fuente) / correlación (CrisisWindow +
  community_id) / decisión. AdapterSpec v1 es el contrato del adaptador por fuente.

REGLAS CRÍTICAS:
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. Tarda >1h. No negociable.
- Python3 heredoc en macOS (nunca sed -i sin -e ''). vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde.
- vendor.key nunca en disco ni en repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().
- Nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; } explícito.
- DNS fix en provisions nuevos: chattr +i /etc/resolv.conf DESPUÉS de chrony.
- Nunca cat << 'EOF' anidado en <<-SHELL — usar printf.
- alert_client.hpp nunca incluido en componentes que linkan libetcd_client.so.
- community_id: canonicalización byte-idéntica a Zeek/Suricata o el join falla en silencio.

ENTORNO: macOS M2 Pro · i9 8 núcleos · 32GB RAM · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER: colaboración UEx/INCIBE con Dr. Andrés Caro Lindo. No deadline duro — gate real es demostrar
datasets de valor científico (curva F1 multi-fuente, ADR-048). El 22-09-2026 era referencia de ritmo.