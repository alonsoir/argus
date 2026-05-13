# aRGus NDR — DAY 151 CONTINUITY PROMPT
# Estado: main @ 93b4d39c | DAY 150 COMPLETO
# Paper: arXiv:2604.04952 | v24 local (v3 en arXiv)
# FEDER: pendiente identificar convocatoria adecuada (investigador independiente)

## COMPLETADO DAY 150
- fix/parquet-convert-vagrant-ssh PR #69: vagrant ssh -c en parquet targets
- feat(adr044) PR #70: provision_crypto.sh — Vault KV v1, familias A/B/C + etcd, idempotente, crypto_audit.json
- feat(adr044) PR #71: vault_client.h/.cpp — derivación D12/D13, jitter, cache tmpfs, 5/5 tests, pipeline-build
- feat(adr044) PR #72: Jenkinsfile stage Provision Crypto — separado, condicional, artifact, bloquea si Vault KO
- DEBT-CRYPTO-STAMPEDE-001: CERRADA (jitter implementado)
- Email Dr. Andrés Caro Lindo: inventario hardware ~460€ + datasets UEx + VM supercomputador
- Decisión open-core: plugin system como mecanismo de licencias (Consejo 8/8 + Founder)
- Decisión autonomía extendida Opción D (Consejo 8/8): TTL = ventana renovación preferente
- BACKLOG.md + README.md actualizados

## 🔴 DECISIONES ARQUITECTÓNICAS MAYORES (DAY 150)

### Open-core model definitivo
- Un solo binario por arquitectura (x86-ebpf, x86-libpcap, ARM64-libpcap, seL4-futuro)
- Plugin system = mecanismo de licencias. NO hay versión community vs enterprise separada
- Community: seed-client + pipeline C++20 completo (siempre libre, siempre capaz)
- Enterprise: plugins firmados activados por licencia en Vault (governance, escala, compliance)
- `ARGUS_VAULT_ENABLED` único separador compile-time — solo controla qué .cpp se linka
- `ICryptoProvider` interfaz abstracta: `SeedFileProvider` (community) + `VaultProvider` (enterprise)
- Factoría `CryptoProvider::create()` único punto de decisión — ningún componente ve #ifdef
- DEBT-EMECAS-DUAL-COMPILATION-001: CI compila ON y OFF en cada build

### Autonomía extendida Opción D (hospital scenario)
- TTL = ventana de renovación preferente, NUNCA fecha de muerte
- Máquina de estados: NORMAL → EXTENDED_AUTONOMY → RECONCILIATION → REVOKED
- EXTENDED_AUTONOMY: continúa operando, Log CRITICAL cada 15 min, SOS webhook, reintentos cada 5 min
- Firewall default-deny para tráfico nuevo en EXTENDED_AUTONOMY
- Reconciliación obligatoria al recuperar Vault (envía key_version, Vault valida)
- Circuit breaker configurable (default 30 días)
- Logs firmados locales con flag EXTENDED_AUTONOMY=1
- Cache persistente en prod solo sobre filesystem cifrado (LUKS obligatorio)
- Clave invalidada SOLO por: revocación explícita firmada, EMECAS, tamper detection

### Migración por canal (no por componente)
- ZeroMQ bilateral: si sniffer usa VaultProvider y ml-detector usa SeedFile → keypairs incompatibles
- Orden de migración:
    1. etcd-server (bootstrap especial)
    2. sniffer + ml-detector (simultáneamente — canal A)
    3. firewall-acl-agent (canal B)
    4. rag-ingester + rag-security (simultáneamente — canal C)

## PENDIENTES DAY 151 (por prioridad)

### P0 — EMECAS PRIMERO
1. vagrant destroy -f && vagrant up && make bootstrap && make test-all

### P0 — Integración etcd-server con VaultClient
2. Rama: feature/adr044-etcd-vault-integration
   a) Crear ICryptoProvider interfaz abstracta en common/crypto_provider.h
   b) SeedFileProvider implementa ICryptoProvider (wraps seed-client actual)
   c) VaultProvider implementa ICryptoProvider (wraps VaultClient)
   d) Factoría CryptoProvider::create() con #ifdef ARGUS_VAULT_ENABLED
   e) etcd-server integra ICryptoProvider en lugar de seed-client directo
   f) fichero local /run/argus/etcd-bootstrap-status.json (0600, AppArmor + Falco)
   g) Una vez etcd arranca → registro vía loopback → borra fichero temporal
   h) Tests: ARGUS_VAULT_ENABLED=ON y =OFF ambos verdes
   i) EMECAS verde con make PROFILE=production test-all

### P1 — DEBT-CRYPTO-AUTONOMY-001
3. Máquina de estados en vault_client.cpp:
   enum class CryptoState { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED }
    - EXTENDED_AUTONOMY: Log CRITICAL cada 15 min + SOS webhook + reintentos background
    - RECONCILIATION: handshake key_version con Vault antes de volver a NORMAL
    - REVOKED: revocación explícita → descarga nueva clave

### P1 — DEBT-FIREWALL-AUTONOMY-MODE-001
4. firewall-acl-agent detecta vault_client en EXTENDED_AUTONOMY
   → default-deny para tráfico nuevo
   → umbral ML más sensible
   → logs DEBUG, retención máxima

### P1 — DEBT-ALERTING-EDGE-SOS-001
5. scripts/alerts/sos_vault_unreachable.sh
    - Webhook Discord/Telegram/email configurable por despliegue via Ansible
    - Escalado: TTL<48h WARN, TTL<24h CRITICAL, TTL=0 último intento

### P1 — DEBT-EMECAS-DUAL-COMPILATION-001
6. Jenkinsfile: stages paralelos Test Community (VAULT_ENABLED=OFF) + Test Enterprise (ON)
   Makefile: vault-client-build-community + vault-client-build-enterprise

## DEUDAS NUEVAS DAY 150
- DEBT-CRYPTO-AUTONOMY-001: máquina de estados EXTENDED_AUTONOMY (P1 pre-FEDER)
- DEBT-FIREWALL-AUTONOMY-MODE-001: default-deny en autonomía (P1 pre-FEDER)
- DEBT-CRYPTO-REVOCATION-LOCAL-001: revocación offline sin Vault (P1 post-FEDER)
- DEBT-CRYPTO-RECONCILIATION-001: handshake post-Vault (P1 pre-FEDER)
- DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001: cache cifrada prod LUKS (P1 pre-FEDER)
- DEBT-EMECAS-DUAL-COMPILATION-001: CI compila ON+OFF (P1)
- DEBT-LICENSE-VAULT-001: servidor licencias en Vault (P2 post-FEDER)
- DEBT-PLUGIN-ENTERPRISE-001: definir plugins enterprise (P2 post-FEDER)

## DEUDAS ABIERTAS RELEVANTES (DAY 151)
- DEBT-CRYPTO-HEARTBEAT-001: lease etcd TTL=10s keepalive 5s (P1) — stub en vault_client
- DEBT-CRYPTO-AUDIT-FINGERPRINT-001: fingerprint sha256(pk) en etcd (P1) — struct implementada, etcd stub
- DEBT-ALERTING-EDGE-SOS-001: webhook SOS (P1 pre-FEDER)
- DEBT-VAULT-HA-001: Vault HA raft post-FEDER
- DEBT-LEGAL-DATA-RETENTION-001: esperando Dr. Andrés Caro Lindo

## NOVEDADES ANDRÉS (DAY 149-150)
- Llamó la noche del DAY 149 — co-investigador activo, no asesor pasivo
- Hardware en camino: RPi × N + switch
- Email DAY 150: inventario completo ~460€ (RPi5×2 + N100×2 + switch)
  Argumento clave: sin N100 no medimos eBPF bare-metal real
- FEDER: deadline 22-Sep NO es duro — busca convocatoria adecuada para investigador independiente
- Supercomputador UEx: VM (no bare-metal), sistema virtualización pendiente conocer

## ESTADO TÉCNICO
- main @ 93b4d39c
- Keypair post-destroy DAY 133: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa
- Vault instalado en VM: v2.0.0 — NO corriendo tras vagrant destroy (provision_crypto.sh lo arranca)
- vault_client instalado: /usr/local/lib/libvault_client.so.1.0.0
- common/vault_client.h + common/vault_client.cpp + common/CMakeLists.txt + common/tests/
- ICryptoProvider: POR IMPLEMENTAR (DAY 151 P0)
- Scripts: scripts/jenkins/provision_crypto.sh ✅
- Paper: docs/latex/main.tex (v24 local)

## REGLAS PERMANENTES
- macOS: nunca sed -i sin -e ''; usar python3 inline
- Makefile: única fuente de verdad
- EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all
- EMECAS con código C++20: añadir make PROFILE=production test-all
- Consejo: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral (8 modelos)
- No ARM64 antes de pipeline x86 end-to-end verde (Kimi, DAY 148)
- GITHUB: push directo a main BLOQUEADO. Flujo obligatorio:
  git checkout -b feature/nombre → git push → gh pr create → merge → git checkout main && git pull
- JSON originales INTOCABLES: Ansible genera *.dev.json / *.prod.json separados
- #ifdef ARGUS_VAULT_ENABLED: único separador compile-time. Solo en factoría, nunca en lógica de negocio
- Migración por canal: sniffer+ml-detector simultáneamente, nunca mezclados
- TTL = ventana de renovación preferente, NUNCA fecha de muerte criptográfica
- Firewall default-deny en EXTENDED_AUTONOMY: obligatorio, sin excepciones
- Cache cifrada en prod: LUKS obligatorio. Seed en texto plano: JAMÁS