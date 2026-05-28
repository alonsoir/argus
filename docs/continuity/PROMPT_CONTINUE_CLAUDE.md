DAY 169 — aRGus NDR (arXiv:2604.04952)

Estado: main @ post-merge feature/day167-ntp-correlation-engine.
Rama activa: feature/day168-suricata-community-id (pendiente EMECAS++ y merge).

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 163: Fix CMake (test_ntp_health_check triplicado). BACKLOG-CRYPTO-VENDOR-KEY-001 ✅.
CryptoProviderHandle RCU ✅. ADR-045 v2 ✅. Consejo 8/8.
DAY 164-166: Enterprise crypto lifecycle completo. EMECAS++ 3 actos. Merge a main. Tag v1.0.0-day166.
DAY 167: NTP+chrony (DEBT-ARGUSPP-NTP-001 P0) + correlation engine scaffold (ADR-048 F2).
11 pasadas Jenkins. EMECAS++ verde. Merge a main → 7b45feca.
DAY 168: Vagrantfile multi-VM: Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x provisionados.
Todos en ml_defender_gateway_lan (192.168.100.0/24).
community-id habilitado en Suricata y Zeek (DEBT-ARGUSPP-COMMUNITY-ID-001 ✅).
REGLA NUEVA: nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; }.
REGLA NUEVA: DNS fix (chattr +i /etc/resolv.conf) SIEMPRE después de instalar chrony.
REGLA NUEVA: nunca cat << 'EOF' anidado en <<-SHELL — usar printf.
Commits: feat(suricata/zeek/wazuh), fix(security) WAZUH_MANAGER_PASSWORD eliminado.

VMs ACTIVAS (autostart: false — arrancar individualmente):
defender   192.168.100.1   aRGus NDR completo (primary)
suricata   192.168.100.10  Suricata 7.0.10, AF_PACKET, community-id:yes, PROMISC ✅
zeek       192.168.100.11  Zeek 8.2.0, community-id-v1, PROMISC ✅
wazuh      192.168.100.12  Wazuh 4.x manager running, NTP OK ✅
client     192.168.100.50  tcpreplay + nmap/hydra/sqlmap/atomic-red-team (autostart:false)

PRIORIDAD DAY 169:
1. EMECAS++ en feature/day168-suricata-community-id → PR → merge a main (P0)
2. DEBT-ARGUSPP-COMMUNITY-ID-001 — community_id en contrato protobuf + sniffer
   - cat protobuf/network_security.proto → añadir campo community_id (string, field ~20)
   - sniffer: calcular community_id (SHA1 5-tupla: src_ip+dst_ip+src_port+dst_port+proto)
   - propagar por pipeline: ml-detector → correlation-engine
   - protobuf3 backwards compatible — campos nuevos no rompen componentes existentes
   source_wait_timeout: argus=5s / suricata=10s / zeek=20s / wazuh=90s
   crisis_idle_timeout: 120s
3. BACKLOG-CI-ENTERPRISE-001 — Jenkins gate make emecas++ (P1)
4. DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake (P1)

DEUDAS ABIERTAS RELEVANTES:
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json → correlation-engine
- DEBT-ARGUSPP-COMMUNITY-ID-001 — Suricata+Zeek OK; falta verificar en outputs reales
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER
- DEBT-ARGUSPP-MITRE-001 — script de ataque MITRE con atomic-red-team (post-FEDER)
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión)
- eth1: intnet ml_defender_gateway_lan (tráfico de ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta tráfico → todos los engines ven el mismo flujo → community_id coherente
- Neo4j: grafo de correlación cross-engine sobre community_id (post-FEDER)

REGLAS CRÍTICAS:
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. Tarda >1h. No negociable.
- Python3 heredoc en macOS. vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde.
- vendor.key nunca en disco ni en repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().
- Nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; } explícito.
- DNS fix en todos los provisions nuevos: chattr +i /etc/resolv.conf DESPUÉS de chrony.
- Nunca cat << 'EOF' anidado en <<-SHELL — usar printf.

ENTORNO: macOS M2 Pro · i9 8 núcleos · 32GB RAM · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER gate: 22 septiembre 2026 · datasets para Dr. Andrés Caro Lindo (UEx/INCIBE).