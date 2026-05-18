═══════════════════════════════════════════════════════════
PROMPT DE CONTINUIDAD — aRGus NDR
DAY 157 · 2026-05-19 · Continuación de DAY 156
arXiv:2604.04952 · GitHub: alonsoir/argus
═══════════════════════════════════════════════════════════

## ESTADO AL INICIO DE DAY 157

**Tag activo:** v0.9.1-day156
**Rama activa:** feature/day156-autonomy-integration → PENDIENTE merge a main via PR
**Keypair activo:** b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa
**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv

### EMECAS DAY 156 — RESULTADO FINAL
vagrant destroy → up → make bootstrap → make test-all: TODO VERDE
- seed-client: 3/3 ✅
- crypto-transport: 5/5 ✅
- etcd-client HMAC: 12/12 ✅
- plugin-loader + sign: PASSED ✅
- sniffer: 9/9 ✅
- ml-detector: 10/10 ✅
- rag-ingester: 8/8 ✅
- etcd-server: 3/3 (incluye test_autonomy_integration 7/7) ✅
- firewall: 50/50 (incluye test_autonomy_e2e 4/4) ✅
- argus-network-isolate: 1/1 ✅

### P0 CERRADA DAY 156: DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
- etcd-server/src/main.cpp: CryptoAutonomyStateMachine + AutonomyPublisher integrados.
  Health-check loop 5s. Transiciones NORMAL→AUTONOMOUS→RECONCILING→NORMAL.
- firewall-acl-agent/src/main.cpp: FirewallAutonomyReactor + AutonomySubscriber integrados.
  AutonomyConfig.zmq_endpoint en struct y parser. dry_run en tests.
- Fix ZMQ slow joiner: publisher bind() ANTES de subscriber connect() — REGLA PERMANENTE.
- Tests: Test B 7/7 (unitario) + Test A 4/4 (E2E dry_run) — integrados en make test-all.

### ESTADO GIT
Commits en feature/day156-autonomy-integration:
1. fix: add autonomy_publisher.h to CMake install target (+ ADR-046 + respuestas Consejo)
2. feat: DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA (DAY 156)
   PR pendiente a main. Merge tras EMECAS en rama (ya ejecutado, verde).

### DEUDAS PENDIENTES POST-DAY 156 (en orden de prioridad)

**P1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001 (DAY 157)**
Estado firmado Ed25519 en /var/lib/argus/crypto-autonomy-state.json (NO tmpfs).
Decisión Consejo 6/8: fichero regular + fsync atómico.
Formato: {state, entered_at, sequence, node_id, reason, signature}
Al arrancar: si estado=AUTONOMOUS y firma válida y timestamp < 24h → arrancar en AUTONOMOUS.
Restart desde AUTONOMOUS → pasar por RECONCILING, no volver a NORMAL sin verificar Vault.
Nuevo fichero: common/autonomy_state_writer.h/.cpp

**P1 — DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (DAY 157)**
Firmar /run/argus/etcd-bootstrap-status.json con crypto_material.sk en STEP 0.
Verificar firma antes de consumir en cualquier componente.
Misma cadena de confianza que ADR-025 plugins.

**P1 — DEBT-KEYPAIR-LIFECYCLE-PROD-001 (nueva DAY 156)**
Estrategia 3 niveles dev/staging/prod. Consejo 8/8.
make bootstrap con ARGUS_ENV=prod: usar keypair preexistente o FALLAR — nunca generar silenciosamente.

**P2 — DEBT-CRYPTO-AUTONOMY-001**
SM EXTENDED_AUTONOMY: circuit breaker 30 días (configurable), alerta progresiva,
logs firmados con flag EXTENDED_AUTONOMY=1.
Implementar SOLO después de P1s cerradas.

**P2 — DEBT-CRYPTO-RECONCILIATION-001 (arquitectura final acordada)**
poll_callback arquitectura final: AutonomySubscriber::run() → actualiza
atomic<FirewallAutonomyMode> last_known_mode_. poll_callback retorna last_known_mode_.load().
No se crea un segundo socket. Feature flag use_dedicated_health_channel (default false para MVP).

**ADR-046 — PENDING-REVISION (sesión dedicada)**
Tres condiciones para cerrar:
1. §Label leakage policy (features=solo aRGus, labels=Suricata, NUNCA mezclar)
2. §Deployment matrix (RPi5=aRGus-only, edge server x86≥16GB=aRGus++)
3. §8 reformulado como hipótesis o con datos reales (antes de arXiv v24)

### REGLAS CRÍTICAS DEL PROYECTO
- macOS: NUNCA sed -i sin -e ''. Para edits de ficheros: Python3 inline o dentro de la VM.
- ZMQ PUB/SUB: publisher bind() ANTES de subscriber connect(). Sin excepciones.
- EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all (invariante).
- Makefile es la única fuente de verdad. Nunca cmake/make directamente.
- -Werror activo: 0 warnings es invariante permanente.
- Toda deuda tiene test de cierre. Sin test = no cerrado.
- Merge a main solo via PR. EMECAS verde en rama antes del PR.

### PROTOCOLO DE INICIO DAY 157
1. Abrir PR de feature/day156-autonomy-integration → main
2. EMECAS apertura en main (tras merge): vagrant destroy → up → make bootstrap → make test-all
3. Si verde: tag v0.9.1-day156 en main
4. Iniciar DEBT-AUTONOMY-STATE-PERSISTENCE-001:
    - Leer headers de autonomy_publisher.h y crypto_autonomy.h (ya conocidos)
    - Nuevo fichero common/autonomy_state_writer.h/.cpp
    - Escribir estado firmado al entrar en AUTONOMOUS
    - Leer y verificar al arrancar etcd-server (STEP 0b)

### CONTEXTO DEL PROYECTO
- aRGus NDR: C++20 NDR open-source para infraestructura crítica (hospitales, municipios)
- Dev: macOS M2 Pro host, Vagrant/VirtualBox, Debian Bookworm guest
- Pipeline: sniffer(eBPF/XDP) → ml-detector → etcd-server → firewall-acl-agent → rag-ingester/rag-security
- ZeroMQ + ChaCha20-Poly1305 + Ed25519 + HKDF-SHA256 via libsodium 1.0.19
- F1=0.9985, ROC-AUC=1.0000 en CIC-IDS-2017
- FEDER Extremadura 2026 deadline: 22 Septiembre 2026
- Consejo de Sabios: 8 modelos (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)
- Qwen se autoidentifica como DeepSeek — registrar siempre como Qwen en actas

═══════════════════════════════════════════════════════════
Alonso Isidoro Román — PI aRGus NDR
arXiv:2604.04952 · DAY 157 · Extremadura, España
"Via Appia Quality — Un escudo que aprende de su propia sombra."
═══════════════════════════════════════════════════════════