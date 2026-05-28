DAY 168 — aRGus NDR (arXiv:2604.04952)

Estado: main @ post-merge feature/day167-ntp-correlation-engine. EMECAS++ 3 actos verdes.

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 163: Fix CMake (test_ntp_health_check triplicado). BACKLOG-CRYPTO-VENDOR-KEY-001 ✅.
CryptoProviderHandle RCU ✅. ADR-045 v2 ✅. Consejo 8/8.
DAY 164-166: Enterprise crypto lifecycle completo. EMECAS++ 3 actos. Merge a main.
DAY 167: NTP+chrony (DEBT-ARGUSPP-NTP-001 P0) + correlation engine (ADR-048 F2).
11 pasadas para ajustar Jenkins. EMECAS++ verde. Merge a main.

PRIORIDAD DAY 168 (por completar ADR-048 F2):
- DEBT-ARGUSPP-COMMUNITY-ID-001 — habilitar community_id en Suricata y Zeek (P0 en v1.1)
- DEBT-ARGUSPP-SURICATA-001 — Suricata en Vagrantfile + EMECAS, eve.json → rag-security
- BACKLOG-CI-ENTERPRISE-001 — Jenkins gate `make emecas++` (P1 post-merge)

DEUDAS NUEVAS DAY 163:
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake (P1)
- BACKLOG-EMECAS-VAULT-E2E-001 — cubierto por EMECAS++ Acto I

REGLAS CRÍTICAS:
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. Tarda >1h. No negociable.
- Python3 heredoc en macOS. vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde.
- vendor.key nunca en disco ni en repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().

ENTORNO: macOS M2 Pro · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER gate: datasets de valor científico para Dr. Andrés Caro Lindo (UEx/INCIBE).