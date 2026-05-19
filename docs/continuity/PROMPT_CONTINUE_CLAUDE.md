Soy Alonso Isidoro Román, PI y desarrollador único de aRGus NDR (arXiv:2604.04952), sistema C++20 de detección de red para infraestructura crítica (hospitales, escuelas, municipios). Colaboradores: Dr. Andrés Caro Lindo (UEx/INCIBE, FEDER) y Hugo Vázquez Caramés (co-founder). Repo: github.com/alonsoir/argus.

## ESTADO HOY — DAY 158 (19 Mayo 2026)

Tag: v0.9.2-day157 | Branch: main @ 92533d03
EMECAS DAY 157: VERDE. Pipeline 6/6. make test-all PASSED.
Keypair activo: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa

## CERRADO DAY 157
- DEBT-AUTONOMY-STATE-PERSISTENCE-001 ✅ (autonomy_state_writer.h, 9/9 tests)
- DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 ✅ (Ed25519 firmado, escritura atómica)
- DEBT-KEYPAIR-LIFECYCLE-PROD-001 ✅ (3 niveles dev/staging/prod)
- DEBT-CRYPTO-RECONCILIATION-001 ✅ (staleness guard 30s, 9/9 tests)
- Tag v0.9.2-day157 en main. PR mergeado. Rama feature eliminada.

## PENDIENTE INMEDIATO DAY 158
1. DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2): tools/check-bootstrap-status.sh + ExecStartPre= en systemd units dependientes
2. DEBT-CRYPTO-AUTONOMY-001 (P2): EXTENDED_AUTONOMY state machine completa
3. DEBT-ALERTING-EDGE-SOS-001 (P1 pre-FEDER): webhook SOS configurable (Discord/Telegram/email)

## EMAIL A ANDRÉS CARO LINDO — PENDIENTE ENVÍO
Redactado y listo para enviar por Gmail. Tres temas:
1. Hardware lab: RPi5×2 (8GB) + N100 miniPC×2 (NIC i226-V) + switch 8p gigabit + cables Cat6 + accesorios RPi. Sin precios (dependen de UEx/INCIBE).
2. Ampliación pipeline Suricata+Zeek+Wazuh (aRGus++): señal más rica, datasets mejores, NDR→NDR/EDR híbrido. Wazuh agent en edge (cabe en RPi 8GB), manager en servidor central (~8GB).
3. Dictamen GDPR: ¿datos HMAC-SHA256 dejan de ser datos personales Art.4(5) si clave en Vault destruido certificadamente? Necesario antes de agosto.

## ADR-046 v3 — APROBADO CONSEJO 8/8 DAY 158
Documento: docs/adr/ADR-046-v3-multi-source-enriched-pipeline-arguspp.md
Supersede v1 y v2. Amendments clave:
- community_id como primary key de correlación cross-tool (ChatGPT)
- source_wait_timeout (técnico, por fuente) ≠ crisis_idle_timeout (semántico, 120s) — ChatGPT
- crisis_generation: permite crisis simultáneas/solapadas en mismo nodo — ChatGPT
- late_arrival: true para Wazuh tardío — Grok
- Secuencia v1.0→v1.1→v1.2→v2.0 — Kimi
- NTP como gate P0 (chrony + offset >1s bloquea arranque) — DeepSeek+Grok
- Principio: "la crisis es la ventana". Sin ventana fija artificial.
- Disparadores múltiples: aRGus, Suricata, Zeek, Wazuh (cualquiera puede disparar)
- Protobuf NO se modifica hasta evidencia empírica MITRE ATT&CK
- Cada herramienta genera su Parquet con su propio esquema. Schema Neo4j es aditivo.
- community_id es el pegamento entre esquemas distintos.
- CrisisWindow = registro de evento, NO dataset de entrenamiento. Datasets = miles de CrisisWindows acumuladas (ADR-040).
- Timeouts del servidor controlan convergencia de señales post-disparo, no período de recolección del edge (que es continuo).
- ADR-047 pendiente: mitre-generator (consenso 8/8)

## 12 NUEVAS DEUDAS TÉCNICAS (DEBT-ARGUSPP-*)
- DEBT-ARGUSPP-NTP-001 (P0): chrony + gate arranque offset >1s
- DEBT-ARGUSPP-COMMUNITY-ID-001 (P0 en v1.1): habilitar community_id Suricata+Zeek
- DEBT-ARGUSPP-SURICATA-001 (P1): Vagrantfile + EMECAS
- DEBT-ARGUSPP-ZEEK-001 (P1): Vagrantfile + EMECAS
- DEBT-ARGUSPP-CORRELATION-001 (P1): correlation-engine v1.0 C++20
- DEBT-ARGUSPP-TIMEOUT-CONFIG-001 (P1): mapa timeouts JSON
- DEBT-ARGUSPP-NEO4J-TTL-001 (P1): TTL+compactación pre-producción
- DEBT-ARGUSPP-RESOURCE-001 (P1 con hardware): medir CPU/RAM 4 fuentes RPi5+N100
- DEBT-ARGUSPP-MITRE-001 (P1 post-hardware): mitre-generator + Atomic Red Team
- DEBT-ARGUSPP-BENCHMARK-001 (P1 post-hardware): benchmark con 4 fuentes
- DEBT-ARGUSPP-WAZUH-001 (P2): post-medición recursos
- DEBT-PAPER-SYNTHETIC-001 (P2): sección paper v24 datasets sintéticos vs académicos

## EXPERIMENTO DATASETS — CONFIRMADO (para §8 paper v24)
- Experimento 1: 100% académico → F1≈0.3 (pcap relay catastrófico)
- Experimento 2: mezcla proporcional → degradaba el modelo al añadir académico
- Experimento 3: 100% sintético estadístico (DeepSeek) → F1=0.9985, Recall=1.000, detecta Neris 2011
- Hallazgo: datasets académicos = benchmark, NO entrenamiento. Sesgo de construcción.
- Referencias: Arp et al.[2022], Wagner et al.[2022], Sommer&Paxson[2010]
- Reproducible: si artefactos perdidos, re-ejecutar (la reproducibilidad es el punto)

## BACKLOG PRIORIDAD ABSOLUTA PRE-FEDER (deadline 22 sep 2026)
1. Email a Andrés — ESTA SEMANA (desbloqueante externo hardware + GDPR)
2. DEBT-ALERTING-EDGE-SOS-001
3. DEBT-CRYPTO-AUTONOMY-001 (EXTENDED_AUTONOMY)
4. DEBT-JENKINS-SEED-DISTRIBUTION-001
5. DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001
6. Hardware físico (RPi5 + N100) — desbloquea ADR-041 y benchmarks
7. DEBT-VAULT-FEDERATION-001 + DEBT-GDPR-ERASURE-001

## REGLAS PERMANENTES
- EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all
- macOS: siempre Python3 heredoc, nunca sed -i sin -e ''
- Vagrant: siempre -c flag
- ZMQ PUB/SUB: publisher bind() ANTES de subscriber connect()
- Keypair activo regenera en cada EMECAS: b5b6cbdf67dad75cdd7e3169d827d1d6d4c938b720e34331f8a73f478ee85daa
- ADR-047 pendiente: mitre-generator (Consejo 8/8 unánime)

## METODOLOGÍA
- Consejo de Sabios: 8 modelos (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)
- Test-Driven Hardening (TDH): RED→GREEN obligatorio. Sin test = no cerrado.
- Via Appia Quality. JSON is the law. KISS.