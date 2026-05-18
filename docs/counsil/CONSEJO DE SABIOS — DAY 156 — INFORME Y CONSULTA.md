═══════════════════════════════════════════════════════════
CONSEJO DE SABIOS — aRGus NDR
DAY 156 · 2026-05-18 · Rama: feature/day156-autonomy-integration
Modelos: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral
═══════════════════════════════════════════════════════════

## QUÉ HEMOS HECHO HOY

### P0 CERRADA — DEBT-AUTONOMY-CRYPTO-INTEGRATION-001

El plano de autonomía criptográfica ha quedado integrado de extremo a extremo
en el pipeline de producción. Esto significa que el sistema ahora reacciona
automáticamente ante la caída de Vault sin intervención humana.

**etcd-server/src/main.cpp:**
- Instancia `CryptoAutonomyStateMachine` + `AutonomyPublisher` (ZMQ PUB)
- Health-check loop cada 5s: `crypto_provider->is_healthy()`
- Transiciones automáticas: NORMAL → AUTONOMOUS → RECONCILING → NORMAL
- Publica eventos JSON firmados al socket IPC `ipc:///run/argus/autonomy.sock`

**firewall-acl-agent/src/main.cpp:**
- Instancia `FirewallAutonomyReactor` (whitelist_cidrs de firewall.json)
- `AutonomySubscriber` arranca en hilo dedicado
- Al recibir AUTONOMOUS: aplica cadena `argus-autonomy` con deny selectivo
- Al recibir RECONCILING/NORMAL: levanta la cadena
- dry_run=true en tests: sin root, sin iptables real

**Correcciones de infraestructura:**
- `autonomy_publisher.h` no estaba en `CMakeLists.txt` install target
- `AutonomyConfig` no tenía `zmq_endpoint` en struct ni parser
- `EtcdClient` no expone `isHealthy()` — poll_callback usa presencia del puntero

**Tests nuevos integrados en make test-all:**
- Test B (unitario): 7/7 PASSED — SM + Publisher via ZMQ real
  T1: InitialStateNoEvent
  T2: VaultKoPublishesAutonomous
  T3: VaultRestoredPublishesReconciling
  T4: ReconciliationOkPublishesNormal
  T5: VaultKoFromAutonomousIsNoop
  T6: RevocationPublishesDegraded
  T7: HealthCheckLoopSimulation

- Test A (E2E): 4/4 PASSED — Publisher→IPC→Subscriber→Reactor dry_run
  E2E-1: VaultKoTriggersAutonomousMode
  E2E-2: VaultRestoredLiftsAutonomousMode
  E2E-3: FullCycleNormalAutonomousReconcileNormal
  E2E-4: SubscriberRunsStableWithoutEvents

**Fix ZMQ crítico descubierto:**
El slow joiner de ZMQ PUB/SUB hace perder el primer mensaje si el subscriber
conecta antes de que el publisher haga bind. Solución: publisher bind PRIMERO
en todos los fixtures de test. Esto es relevante para cualquier componente
futuro que use ZMQ PUB/SUB en aRGus.

**EMECAS DAY 156:**
vagrant destroy → up → make bootstrap → make test-all
Resultado: TODO VERDE — 50/50 firewall, 3/3 etcd-server, 9/9 sniffer,
10/10 ml-detector, 8/8 rag-ingester, 1/1 argus-network-isolate

---

## QUÉ HAREMOS MAÑANA (DAY 157)

**P1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001**
El estado de la SM no sobrevive a un restart del proceso. Si etcd-server
se reinicia durante AUTONOMOUS, vuelve a NORMAL sin pasar por RECONCILING.
Propuesta: fichero firmado Ed25519 en tmpfs `/run/argus/crypto-autonomy-state.json`
con el estado actual, timestamp y firma. El subscriber lo lee al arrancar.

**P1 — DEBT-BOOTSTRAP-STATUS-SIGNATURE-001**
`/run/argus/etcd-bootstrap-status.json` se escribe sin firma. Cualquier
proceso puede modificarlo. Propuesta: firmarlo con `crypto_material.sk`
en STEP 0, verificar antes de consumir.

**P2 — DEBT-CRYPTO-AUTONOMY-001**
SM EXTENDED_AUTONOMY: circuit breaker configurable (default 30 días),
transición AUTONOMOUS → EXTENDED_AUTONOMY si `time_in_current_mode() > threshold`.
EXTENDED_AUTONOMY es degradado suave — opera pero con alertas elevadas.

---

## PREGUNTAS AL CONSEJO

### Q1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001: ¿tmpfs o etcd?

El estado firmado podría persistirse en:
a) tmpfs `/run/argus/` — rápido, desaparece en reboot (¿es suficiente?)
b) etcd local embebido — no depende de Vault, pero añade complejidad
c) Fichero regular `/var/lib/argus/` — persiste en reboot, requiere fsync

En infraestructura hospitalaria, un reboot no planificado durante AUTONOMOUS
es el escenario exacto que queremos cubrir. ¿Cuál es el trade-off correcto?

### Q2 — poll_callback como proxy de Vault

Actualmente el `poll_callback` del firewall usa la presencia del puntero
`etcd_client` como proxy del estado de Vault. Esto es un placeholder
(DEBT-CRYPTO-RECONCILIATION-001). La alternativa correcta sería consultar
el estado publicado por etcd-server vía ZMQ. ¿Tiene sentido implementar
un segundo canal SUB en el firewall para el estado de salud, o es
sobreingeniería para el MVP FEDER?

### Q3 — Suricata como primera fuente ADR-046

El Consejo aprobó ADR-046 con condiciones. La primera iteración de
aRGus++ incluiría solo aRGus + Suricata como fuentes de correlación.
¿Cuál es la estrategia mínima para integrar Suricata sin romper el
pipeline actual? ¿Eve JSON via file watcher (como los CSVs actuales)
o un conector ZMQ directo?

### Q4 — ZMQ slow joiner como deuda de documentación

El slow joiner de ZMQ PUB/SUB es un problema conocido de la librería
que afecta a cualquier par PUB/SUB donde el publisher se crea después
de que el subscriber conecta. ¿Debería registrarse como ADR o como
nota técnica en el BACKLOG para que futuros desarrolladores no repitan
el error?

### Q5 — Keypair regeneration en EMECAS

Cada `vagrant destroy && vagrant up` genera un nuevo keypair Ed25519.
El keypair activo cambia con cada EMECAS. Esto es correcto para el
entorno de desarrollo (aislamiento de sesión), pero en producción el
keypair debe ser estable. ¿Cuál es la estrategia correcta de gestión
de keypairs para el despliegue FEDER en CPD de UEx?

═══════════════════════════════════════════════════════════
Alonso Isidoro Román — PI aRGus NDR
arXiv:2604.04952 · DAY 156 · Extremadura, España
═══════════════════════════════════════════════════════════