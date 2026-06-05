# ML Defender (aRGus NDR)

**Open-source, embedded-ML network detection and response system protecting critical infrastructure from ransomware and DDoS attacks.**

[![Via Appia Quality](https://img.shields.io/badge/Via_Appia-Quality-gold)](https://en.wikipedia.org/wiki/Appian_Way)
[![Council of Wise Ones](https://img.shields.io/badge/Architecture-Reviewed_by_8_Models-blueviolet)](#-consejo-de-sabios--multi-model-peer-review)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![F1=0.9985 Validated](https://img.shields.io/badge/Status-F1%3D0.9985_Validated-brightgreen)]()
[![Tests: make test-all VERDE](https://img.shields.io/badge/Tests-make_test--all_VERDE-brightgreen)]()
[![Pipeline: 6/6](https://img.shields.io/badge/Pipeline-6%2F6_RUNNING-brightgreen)]()
[![Plugin Integrity](https://img.shields.io/badge/Plugin_Integrity-ADR--025_Ed25519-brightgreen)](docs/adr/ADR-025-plugin-integrity-ed25519.md)
[![safe_path](https://img.shields.io/badge/safe__path-ADR--037_header--only-brightgreen)](contrib/safe-path/)
[![PHASE 4](https://img.shields.io/badge/PHASE_4-COMPLETADA-brightgreen)]()
[![AppArmor](https://img.shields.io/badge/AppArmor-7%2F7_enforce-brightgreen)]()
[![Falco](https://img.shields.io/badge/Falco-11_reglas_aRGus-brightgreen)]()
[![BSR](https://img.shields.io/badge/BSR-cap__bpf_ADR--039-brightgreen)]()
[![ADR-040](https://img.shields.io/badge/ADR--040-ML_Retraining_Contract-blue)](docs/adr/ADR-040-ml-plugin-retraining-contract.md)
[![ADR-041](https://img.shields.io/badge/ADR--041-FEDER_HW_Metrics-orange)](docs/adr/ADR-041-hardware-acceptance-metrics-feder.md)
[![Variant B](https://img.shields.io/badge/ADR--029-Variant_B_libpcap_pipeline-blue)]()
[![Reproducible](https://img.shields.io/badge/Infra-make_bootstrap-brightgreen)]()
[![XGBoost](https://img.shields.io/badge/XGBoost-Prec%3D0.9945_In--Distribution-brightgreen)]()
[![Hardened](https://img.shields.io/badge/Security-v0.9.6--day162-brightgreen)]()
[![PRE-PRODUCTION](https://img.shields.io/badge/Status-PRE--PRODUCTION-orange)]()
[![Crypto](https://img.shields.io/badge/Crypto-HKDF_SHA256+ChaCha20_Poly1305-orange)]()
[![arXiv](https://img.shields.io/badge/arXiv-2604.04952_cs.CR-red)](https://arxiv.org/abs/2604.04952)
[![TDH](https://img.shields.io/badge/Methodology-Test_Driven_Hardening-purple)](https://github.com/alonsoir/test-driven-hardening)
[![IRP](https://img.shields.io/badge/IRP-argus--network--isolate_ADR--042-red)]()
[![ADR-043](https://img.shields.io/badge/ADR--043-Memoria_Episódica_Distribuida-blue)](docs/adr/ADR-0043-memoria-episodica-distribuida-v4.md)

📜 Living contracts: [Protobuf schema](docs/contracts/Protobuf%20contracts.md) · [Pipeline configs](docs/contracts/JSON%20contracts.md) · [RAG API](docs/contracts/Rag%20security%20commands.md)

---

✅ DAY 166: EMECAS++ 3 actos verdes y reproducibles. VaultProvider caché RCU confirmado. vault-fault-inject PASSED. Zero downtime demostrado. Branch `feature/day161-enterprise-crypto-integration` → mergeado a main. Tag `v1.0.0-day166`.
**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**

---

## Estado actual — DAY 173 (2026-06-02)

<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 173 |
| Tag | v1.0.0-day166 |
| Branch | feature/day170-community-id-protobuf |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| NTP/chrony | ✅ DEBT-ARGUSPP-NTP-001 — health-check rechaza offset >1s (DAY 167) |
| correlation-engine | 🟡 scaffold ADR-048 F2 (DAY 167) |
| Multi-VM | ✅ Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24 (DAY 168) |
| community_id | ✅ paridad OPERACIONAL cross-sensor — cross-check E2E reproducible (DAY 171/172) |
| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 · ✅ ADR-052 v3.2 RATIFICADA · ✅ ADR-051 v2.2 RATIFICADA (Community ID Parity Gate, 8/8 DAY 173) · ⏳ ADR-050 (MITRE) + ADR-053 (JA3/JA4/BGP) pendientes |
| Próximo hito | DEBT-NEO4J-FLOW-KEY-001 (esquema Neo4j) → correlation-engine. ADR-051/052 ratificados y archivados |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->

**Tag activo:** `v1.0.0-day166` | **Branch activa:** `main`
**Keypair activo:** `c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90` *(regenera en cada EMECAS)*
**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv
**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo
**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo

### Pipeline
- 6/6 componentes RUNNING — validado EMECAS DAY 145 ✅
  - `make test-all`: ALL TESTS COMPLETE (50/50 firewall · 3/3 etcd-server · 9/9 sniffer · 10/10 ml-detector · 8/8 rag-ingester · 1/1 argus-network-isolate) ✅
  - `make PROFILE=production all`: Gate ODR — ALL COMPONENTS BUILT ✅
  - `make argus-network-isolate-test`: dry-run PASSED ✅

### Hitos DAY 157 🎉
- **DEBT-AUTONOMY-STATE-PERSISTENCE-001 CERRADA** — `common/autonomy_state_writer.h` header-only. Escritura atómica fsync+rename, firma Ed25519, lectura fail-safe (AUTONOMOUS expirado >24h → NORMAL). 9/9 tests RED→GREEN. Integrado en etcd-server STEP 0c.
  - **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 CERRADA** — `bootstrap-status.json` firmado Ed25519. JSON canónico → `crypto_sign_detached` → `signature_hex`. Escritura atómica tmp→rename+fsync. Misma cadena de confianza que ADR-025.
  - **DEBT-KEYPAIR-LIFECYCLE-PROD-001 CERRADA** — `provision.sh` `generate_keypair()`: `ARGUS_ENV=prod` sin keypair → `exit 1`. NUNCA genera silenciosamente en producción. 3 niveles: dev/staging=genera, prod=falla.
  - **DEBT-CRYPTO-RECONCILIATION-001 CERRADA + STALENESS GUARD (B1 post-Consejo)** — `AutonomySubscriber`: `shared_ptr<atomic<FirewallAutonomyMode>>` + `shared_ptr<atomic<int64_t>>` (last_update_ns). `poll_callback`: si `elapsed > staleness_timeout_sec` → NORMAL + log. Previene firewall congelado si etcd-server muere silenciosamente. 9/9 tests (T9: staleness guard).
  - **Consejo 8/8 consultado** — Dos bloqueantes identificados y resueltos antes del merge: B1 (staleness) + B2 (ExecStartPre= vs ExecStartPost= para fichero efímero, pendiente DAY 158).
  - **EMECAS DAY 157 VERDE** — `vagrant destroy → up → make bootstrap → make test-all` — TODO VERDE.

### Hitos DAY 175 🎉
- **Zona bronce `correlation_v1` CABLEADA y verificada E2E.** El `CorrelationWriter`
  (productor, ml-detector) deja de estar suelto. Cadena completa con datos reales:
  sniffer eBPF → community_id → ZMQ → ml-detector → bronce → `parse_and_verify` del
  correlation-engine. **3.712 filas reales** en `/vagrant/logs/correlation/argus/`,
  todas con community_id poblado; una fila real validada con la clave de PRODUCCIÓN
  de etcd. 4 pasos verdes: alta CMake + hook en punto único (antes de la bifurcación
  rag/no-rag) + round-trip unitario (prueba de oro writer↔reader) + pipeline vivo.
  - **Lección (DEBT-BRONZE-KEY-PROVISIONING-001):** la clave HMAC del bronce no es
    `seed.hex` sino la de etcd `/secrets/<componente>`. El round-trip con clave
    hardcodeada validaba el contrato pero ocultaba el provisioning.
  - **REGLA PERMANENTE (DAY 175):** construir siempre vía `make <target>` (corre la
    dependencia `proto` y aplica `-Werror` del Makefile), nunca `cmake` directo
    (riesgo de `.pb.h` rancio).
  - **INVARIANTE:** community_id es el punto de unión con Suricata/Zeek — TODAS las
    variantes del sniffer (x86/ARM, eBPF/libpcap) deben poblarlo.
  - **Consejo 8/8:** injectors sintéticos primero (ambos modos: isomorfo + mock) ·
    col 17 `authoritative_source` → string simbólico · ADR-054 (modelo de confianza
    Ed25519 con/en-vez-de HMAC a escala multi-nodo) pendiente de redacción.

### Hitos DAY 173 🏛️
- **ADR-051 v2.2 RATIFICADA — Consejo 8/8.** Community ID Parity Gate & Correlation Health. Confirmación de fidelidad sin 3ª deliberación (precedente ADR-052). Renombrado desde "Seed Parity Gate" (el gate valida paridad de `community_id` emitido, de la que el drift de seed es una causa, no la única). Decisión clave: **Oracle Divergence** — si los sensores heterogéneos coinciden entre sí pero no con `pycommunityid`, arranca con WARNING crítico, NO fail-closed (argumento N-version); fail-closed reservado a disparidad ENTRE sensores. Máquinas de estado del gate y de confianza del sensor (DEGRADED estadístico / QUARANTINED binario confirmado). **Diseño ratificado para archivar** — solo el gate de arranque mínimo (cross-check DAY 171/172) está en camino crítico; el resto duerme hasta que exista engine que proteger. Entregable `ADR-051_v2.2.md`.
  - **DEBTs nuevas (corte camino-crítico/diferible):** P1 `DEBT-CID-TEST-VECTORS-001` (fixture compartido con FLOWUID), `DEBT-SEED-GATE-DIAGNOSTIC-001`, `DEBT-CID-STATE-MACHINE-001`, `DEBT-CID-CROSSCHECK-CI-001`; P2 `DEBT-CID-ORACLE-QUORUM-001`, `DEBT-SEED-CHAOS-TEST-001`; P3 diferida `DEBT-SEED-ACTIVE-PROBE-001`. Más `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1, hallazgo DAY 172: verificar que producción no heredó el reloj inyectado del cross-check).
  - **Higiene DAY 173:** `enterprise_vendor.pub` huérfana destrackeada de la raíz (commit `5c8dc37d`). Verificado sin fuga de clave privada.
- **ADR-052 v3.2 RATIFICADA — Consejo 8/8.** Multi-node Flow Identity & Host↔Net Correlation. Confirmación de fidelidad unánime, sin tercera deliberación. Principio ordenador §0: *"El grafo no es el producto. El producto es el corpus."* `flow_uid = base64(BLAKE2b(node_id ‖ community_id ‖ flow_start_window [‖ seq_in_window]))`; `node_id` = string legible declarado en inventario firmado (NO derivado del keypair efímero); `community_id` = clave de correlación, nunca identidad. Dos anulaciones de árbitro: hash anclado a libsodium (§3.1.1) y señales TCP/TLS de host dentro del ADR (§3.11). Entregable `ADR-052_v3.2.md`. **Desbloquea `DEBT-NEO4J-FLOW-KEY-001`.**
  - **DEBTs de identidad de flujo registradas (orden de dependencia P0→P3):** P0 `DEBT-NODEID-CRYPTO-IDENTITY-001` (reescrita) + `DEBT-FLOWUID-CANONICAL-ENCODING-001` + `DEBT-NEO4J-FLOW-KEY-001`; P1 `DEBT-SENSOR-COVERAGE-MAP-001` / `DEBT-LABEL-WAL-001` (hash-chain) / `DEBT-ARGUSPP-ARP-MONITOR-001` / `DEBT-ARGUSPP-HOST-TCP-001`; P2 `DEBT-CERT-EXPECTATION-STORE-001` / `DEBT-SEQWINDOW-PERSIST-001` / `DEBT-ARGUSPP-OOB-MITM-001` / `DEBT-CORPUS-QUALITY-METRICS-001`; P3 `DEBT-ARCH-FLOW-OBSERVATION-001`.
  - **ADR-053 stub abierto** — JA3/JA4, cadena TLS profunda, anomalía de ruta L3/BGP (diferido conscientemente de ADR-052 para evitar scope creep). **ADR-050 (MITRE) y ADR-051 (Seed Parity Gate) siguen pendientes de redacción.**

### Hitos DAY 171 🎉
- **Cross-check E2E community_id — paridad OPERACIONAL demostrada.** El cliente `.50` replaya el flujo Neris por `eth1`; aRGus + Suricata + Zeek capturan en paralelo (promiscuo) el MISMO paquete y los tres convergen STRING A STRING al diana `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`. Se cierra la paridad operacional (DAY 170 cerró especificación + provisión). Validación data-plane (P2 Consejo): se mide lo que el binario EMITE, no lo que dice la config.
  - **aRGus surfacea community_id observable** — `sniffer/src/flow/community_id_log.{hpp,cpp}`. `compute_community_id` permanece pura; el log vive en los 3 call-sites de sellado (`ring_consumer.cpp` ×2, `main_libpcap.cpp` ×1). Gateado por `ARGUS_CID_CROSSCHECK=1` (OFF por defecto, coste nulo en hot path). TSV 7 campos a `/vagrant/logs/lab/cid-xcheck-argus.tsv` con mutex + `fflush`. Compila en Variant A y B. Test TDH `test_community_id_log.cpp` PASSED.
  - **Verificador de paridad** — `tools/community_id_crosscheck.py` (host). Paridad por VALOR del cid; 5-tupla como etiqueta forense (cada motor nombra el proto distinto). Categorías: agree / disagree / solo.
  - **Criterio de aceptación congelado** — `docs/acceptance_criteria.md`, Consejo 8/8 sin tercera ronda. Refinamiento ChatGPT: categorías de presencia DROP/CONFIG/POLICY/BUG/UNKNOWN, precondición drop=0, nota de túneles de Gemini.
  - **DEBT-ARGUSPP-COUNTER-DUMP-001 abierta (P1, DAY 172)** — volcado de contadores de aRGus a fichero parseable (código nuevo, no "leer un log que existe" como Suricata/Zeek).
  - **Nota algoritmo:** `community_id` usa SHA1 (Corelight), no HMAC-SHA256.

### Hitos DAY 170 🎉
- **community_id cross-sensor sellado** — aRGus (nativo, 8/8 tests contra oráculo pycommunityid v1.5.0 byte a byte, campo protobuf field 18), Zeek 8.2.0 (provisión `local.zeek` site/: `@load community-id-logging` + `redef CommunityID::seed=0`) y Suricata 7.0.10 (`community-id:yes` + `community-id-seed:0`). Diana E2E `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` sobre flujo Neris. Seed 0 explícito en los 3 garantizado por provisión. `DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001` + `DEBT-ARGUSPP-COMMUNITY-ID-001` CERRADAS.
  - **DEBT-ZEEK-COMMUNITY-ID-PROVISION-001 CERRADA** — guardas de idempotencia por línea en el Vagrantfile (no por bloque). `vagrant provision zeek` deja `local.zeek` con `@load` + `seed=0` sin intervención manual.
  - **DEBT-DOCS-BACKLOG-DEDUP-001 CERRADA** — `docs/BACKLOG.md` corrupto desde DAY 158 (append manual `cat>>`, no el script). 5336->2839 líneas. Lección: verificar integridad con `grep secciones | sort | uniq -d` del fichero completo, no `grep -c` de cabecera.
  - **Consejo de Sabios (8/8) — consenso unánime P1/P2/P3.** Gate seed por data-plane (no config), identidad de flujo `hash(node_id || community_id || flow_start_window)`, doble arista host<->red con host_id canónico. ADR-051 (Seed Parity Gate) + ADR-052 (Multi-node Flow Identity & Host<->Net) pendientes de redacción. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema).

### Hitos DAY 169 🏛️
- **Día de arquitectura.** `ADR-046 v4` aprobado (Multi-Source Pipeline, separación de planos). `AdapterSpec v1` cerrado (contrato del adaptador por fuente). `ADR-050` pendiente de redacción (seis vectores de la sesión MITRE + corrección cripto telemetría).
  - **DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 abierta (P0)** — community_id nativo en aRGus: campo en protobuf + cálculo SHA1 de la 5-tupla en el sniffer. Catch de Kimi: canonicalización idéntica byte a byte a Zeek/Suricata o el join cross-tool falla en silencio.

### Hitos DAY 168 🎉
- **Vagrantfile multi-VM** — Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x + client en `ml_defender_gateway_lan` (192.168.100.0/24, `autostart: false`). community-id habilitado en Suricata y Zeek. 50.248 reglas ET Open. `WAZUH_MANAGER_PASSWORD` eliminado (fix seguridad). Merge a main `21642e87`.
  - **3 reglas permanentes nuevas** — nunca `set -e` en provisions (usar `|| true` / `|| { exit 1; }`); DNS fix `chattr +i` SIEMPRE tras chrony; nunca heredoc `cat << 'EOF'` anidado en `<<-SHELL` (usar `printf`).

### Hitos DAY 167 🎉
- **DEBT-ARGUSPP-NTP-001 CERRADA (P0)** — chrony en todos los nodos, health-check rechaza arranque si offset >1s. Gate del correlation-engine: community_id es inútil sin timestamps sincronizados.
  - **correlation-engine scaffold (ADR-048 F2)** — esqueleto C++20 con `source_wait_timeout` por fuente y `crisis_idle_timeout` 120s.
  - **BACKLOG-CI-ENTERPRISE-001 CERRADA** — stage `make emecas++` en Jenkinsfile.dev (11 pasadas hasta verde). Vault dev como precondición. Acto I/II/III rojo → no merge. Merge a main `7b45feca`.

### Hitos DAY 163 🎉
- **Fix CMake: test_ntp_health_check triplicado** — `test_ntp_health_check` definido 3 veces en `common/CMakeLists.txt`. Bloqueaba EMECAS++ Acto I (`-DARGUS_VAULT_ENABLED=ON`). Fix: `sed -i '291,302d;387,398d'`. Un comando, dos minutos. **Consejo DAY 163 (8/8):** invariante `if(NOT TARGET)` obligatorio. Los bloques `if(ARGUS_VAULT_ENABLED)` no crean targets — solo añaden comportamiento. Nueva deuda: `DEBT-CMAKE-GRAPH-INVARIANTS-001` con lint CI (ChatGPT, Kimi). ADR propuesto: `adr-028-cmake-target-naming.md`.
  - **BACKLOG-CRYPTO-VENDOR-KEY-001 CERRADA** — Modelo B: keypair enterprise efímero por `vagrant up`. `vault-enterprise-bootstrap` (run:always) genera Ed25519 + token + sube a Vault + limpia `/tmp`. vendor.key nunca en disco. CMakeLists guard `FATAL_ERROR` sin `-DARGUS_ENTERPRISE_PUBKEY_HEX`. `enterprise_vendor.pub` + `enterprise.token` gitignored.
  - **BACKLOG-CRYPTO-HOT-RELOAD-001 CERRADA** — `common/crypto_provider_handle.hpp` RCU header-only. `std::atomic<shared_ptr<ICryptoProvider>>`. `get()` nunca null. `reload()` swap atómico lock-free. 9/9 tests incluyendo concurrencia 8 readers + 50 reloads y RCU survival via `weak_ptr`.
  - **ADR-045 v2 aprobado (Consejo 8/8)** — `not_before` suficiente (sin 2PC), grace period 10s global, etcd-server escritor único via `CryptoEpochCoordinator` en `vault_client`, `EPOCH_TRANSITION` + `EPOCH_FAILED`, wire header `[uint32_t][uint16_t epoch_id][2B reserved][LZ4]`.
  - **DEBT-ETCD-REGISTRAR-REAL-001 descubierta** — `StubEtcdRegistrar` es stub puro. Prerequisito bloqueante de FASE 2. P0 DAY 164.
  - **12/12 suite common verde** — nuevo test target `test_crypto_provider_handle` integrado.

### Hitos DAY 164 🎉
- **DEBT-ETCD-REGISTRAR-REAL-001 CERRADA (FASE 2a)** — `HttpEtcdRegistrar` REST real: `register_status()`, `start_keepalive()` (hilo heartbeat), `watch_epoch()` (polling 2s), `last_seen_revision`, WatchState CONNECTED/DEGRADED/STALE. 5/5 tests RED→GREEN.
  - **BACKLOG-CRYPTO-EPOCH-001 CERRADA (FASE 2b)** — `CryptoEpochCoordinator`: watch `/v1/epoch`, callback `on_epoch_change` → `handle.reload()`, ACK timestamp monotónico ns. 5/5 tests RED→GREEN. etcd-server: GET/PUT `/v1/epoch` + EpochInfo thread-safe.
  - **Fix ODR httplib** — `CPPHTTPLIB_OPENSSL_SUPPORT` via CMake en todos los targets. `alert_client.hpp` #ifndef guard. vault-enterprise-bootstrap token via @file.
  - **12/12 suite common verde.**

### Hitos DAY 165 🎉
- **BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 CERRADA (FASE 3)** — Wire header enterprise: `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]`. Selección de clave ANTES de descifrar (seguridad crítica). 13/13 tests RED→GREEN. `ml-detector` serializa, `firewall-acl-agent/zmq_subscriber` deserializa.
  - **EMECAS++ OSS verde** — `test-all` ✅ · `test-e2e-synthetic-full` ✅ · `test-e2e-synthetic-firewall` ✅ (540 eventos, 0 crypto_errors).
  - **FASE 4 parcial** — `test_e2e_rotation` FakeEtcdServer 5/5 PASSED + `test-e2e-vault` PASSED. Live rotation pipeline activo pendiente.
  - **Keypair efímero activo:** `a2abfe43e349e86ddeb4a22496b007919c87bdb0f5dc88c17b57cabf0d61331f`
  - **Consejo de Sabios (8/8)** — 6 preguntas EMECAS++. Unanimidades: targets anidados, EMECAS++ naming, Jenkins post-merge. Decisión Alonso: 3 actos obligatorios (Vault nominal + rotación + fallo componente). No merge hasta los 3 actos verdes.
  - **DEBT-FIREWALL-BUILD-LEGACY-001** descubierta (P3, no bloquea).

### Hitos DAY 156 🎉
- **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA** — `CryptoAutonomyStateMachine` + `AutonomyPublisher` integrados en `etcd-server/main.cpp`. Health-check loop 5s dispara `on_vault_unreachable/restored`. `FirewallAutonomyReactor` + `AutonomySubscriber` integrados en `firewall-acl-agent/main.cpp`. `AutonomyConfig.zmq_endpoint` añadido a struct y parser. `autonomy_publisher.h` añadido al install target de CMake.
  - **Test B (unitario): 7/7 PASSED** — `CryptoAutonomyStateMachine` + `AutonomyPublisher` via ZMQ real. T1-T7 incluyendo `HealthCheckLoopSimulation`.
  - **Test A (E2E): 4/4 PASSED** — Pipeline `Publisher→IPC→Subscriber→Reactor` dry_run. `VaultKoTriggersAutonomousMode`, `VaultRestoredLiftsAutonomousMode`, `FullCycleNormalAutonomousReconcileNormal`, `SubscriberRunsStableWithoutEvents`.
  - **Fix ZMQ slow joiner** — publisher debe hacer `bind()` ANTES de que cualquier subscriber conecte. Regla permanente para todos los pares PUB/SUB del proyecto.
  - **EMECAS DAY 156 VERDE** — `vagrant destroy → up → make bootstrap → make test-all` — TODO VERDE. 50/50 firewall, 3/3 etcd-server, 9/9 sniffer, 10/10 ml-detector, 8/8 rag-ingester.
  - **ADR-046 PENDING-REVISION** — Multi-Source Enriched Pipeline aRGus++. Tres condiciones para cierre: §Label leakage policy, §Deployment matrix RPi5 vs edge server, §8 datos empíricos o hipótesis.

### Hitos DAY 155 🎉
- **DEBT-FIREWALL-DENY-SELECTIVE-001 CERRADA** — Cadena dedicada `argus-autonomy`: lo→ESTABLISHED→CIDRs→DROP→INPUT. `whitelist_cidrs` obligatorio desde `firewall.json`. `AutonomyConfig` + `parse_autonomy()` fail-fast. 12/12 tests. 49/49 firewall tests verdes.
  - **DEBT-AUTONOMY-ZMQ-EVENTS-001 CERRADA** — `AutonomyPublisher` (`common/`) + `AutonomySubscriber` (`firewall-acl-agent/`). Topic `argus.crypto.autonomy`. Transport `ipc:///run/argus/autonomy.sock`. 4/4 + 6/6 tests PASSED.
  - **BACKLOG-ZMQ-TUNING-001 CERRADA** — HWM + RECONNECT_IVL en todos los sockets ZMQ del proyecto. Prerequisito de BACKLOG-BENCHMARK-CAPACITY-001 satisfecho.
  - **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 registrada** — Integración en `etcd-server/main.cpp` pendiente (P0 DAY 156). Consejo 6/8: etcd-server como proceso propietario.
  - **EMECAS HARDENED PASSED** — `-Werror` + `-O3` + `-flto` + producción limpio. AppArmor 6/6. Falco 11 reglas. BSR verificado. Tag `v0.9.0-day155`.

### Hitos DAY 154 🎉
- **ADR-045 VaultClient decomposition COMPLETA** — `ICryptoDeriver` + `HkdfCryptoDeriver` (6 tests), `IEtcdRegistrar` + `StubEtcdRegistrar` (4 tests). VaultClient por composición con 4º ctor inyectable. 7 tests common/. v0.8.0-adr045.
  - **DEBT-FIREWALL-AUTONOMY-MODE-001 CERRADA** — `FirewallAutonomyReactor`: AUTONOMOUS/DEGRADED → `iptables -I INPUT 1 argus-autonomy-deny DROP`, NORMAL → `iptables -D INPUT`. Executor inyectable (testable sin root). 6 tests. 48/48 firewall tests verdes.
  - **Fix EMECAS** — `crypto_deriver.h` y `etcd_registrar.h` añadidos al install target. `test_auto_isolate` T6 corregido para `-Werror` en production build.
  - **Consejo 8/8** — ZMQ directo para señal autonomía (P0 DAY 155). Default-deny actual INCORRECTA para hospitales → `DEBT-FIREWALL-DENY-SELECTIVE-001` P0 DAY 155.
  - **EMECAS:** bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅.

### Hitos DAY 149 🎉
- **DEBT-PARQUET-SCHEMA-001 CERRADA** — Schema Arrow v1.0: ml_detector_events (15 fields) + firewall_acl_events (7 fields). 207,122 filas / 53 días. Ratio 11-12x. `make parquet-convert` + `make test-parquet` en `test-all`. Tipos acordados Consejo 8/8.
  - **Vault dev mode + K_pseudo prototipo** — Vault v2.0.0. HMAC-SHA256 determinismo OK, aislamiento OK, post-destroy irrecuperable. Evidencia técnica GDPR para Dr. Andrés Caro Lindo.
  - **Ansible + Jinja2 CI/CD pipeline** — `ansible/templates/*.json.j2`, `deploy_configs.yml`. Ejecutado en VM: 9 OK, 3 changed, 0 failed. `make deploy-configs`.
  - **ADR-044 aprobado (Consejo 8/8)** — Jenkins como entropy orchestrator. Vault autoridad criptográfica. common/vault_client C++20. Paths por familia. etcd barrera pre-arranque. Rotación manual FEDER. Edge nodes autónomos con cache TTL 72h.
  - **Abstract v24** — "architecturally complementary by design". PR #63.
  - **5 PRs mergeados.** Main en 81490fcb.

### Hitos DAY 145 🎉
- **ADR-029 Variant A vs B x86** — libpcap ~2× eBPF en VirtualBox virtio (artefacto SKB mode). Equivalencia funcional confirmada.
  - **Bootstrap múltiple** — `bootstrap-x86-ebpf` + `bootstrap-x86-libpcap`. `bootstrap` = alias de A.
  - **pipeline-status** distingue Variant A/B + detecta invariant violation.
  - **Relay targets** — resumen inline por velocidad + rutas log + nota MTU en banner.
  - **Paper v19** — §6 ADR-029, §10.9, §11.17, §12, abstract actualizado.
  - **Failed packets (2,630):** artefacto fijo pcap CTU-13 Neris — frames jumbo MTU VirtualBox. No son errores del pipeline.

### Hitos DAY 146 🎉
- **EMECAS verde** — 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
  - **Experimento comparativo Suricata 6.0.10 vs aRGus NDR** — CTU-13 Neris, mismas condiciones. Suricata: 0 alertas (ET Open no cubre Neris 2011). aRGus: F1=0.9985, Recall=1.0000.
  - **Makefile**: `make up-argus`, `make up-suricata`, `make halt-argus`, `make halt-suricata`, `make experiment-suricata-run/results`.
  - **Paper Draft v20** generado — nueva §8.13 con comparativa directa, Tabla comparación actualizada con datos empíricos Suricata.
  - **Vagrantfile Suricata** operativo — `nictype1 virtio` (fix crítico DHCP NAT), 50,010 reglas ET Open cargadas.

### Hitos DAY 148 🎉
- **Suricata offline validation** — `suricata -r neris.pcap -k none`, 50,010 ET Open rules (251 IRC, 475 botnet/C2, 853 trojan). 323,154 paquetes. 0 firmas ET disparadas. 128 alertas internas de motor. Criterio de Kimi satisfecho — conclusión irrefutable.
  - **§8.13 paper** — párrafo "Offline validation with full ruleset enforcement" insertado (DAY 148).
  - **§8.14 paper** — framing taxonómico: "decision architecture taxonomies", "measurement layer", "telemetry platform", "Observability does not imply classification".
  - **§10 Future Work** — 5 subsecciones completas: baremetal, corpus, acrl, hardened, Zeek Phase 2 (`detect-botnets.zeek`, Intel framework temporal limitation).
  - **Tabla §8.2** — fila Zeek 8.1.2 añadida (F1=0.042, Prec=1.000, Recall=0.022).
  - **Abstract v23** — tres paradigmas + complementariedad (Zeek telemetry + Suricata signatures + aRGus ML behavioral).
  - **arXiv replace v19→v23** — submitted como v3 (submit/7576269).
  - **DEBT-IRP-FLOAT-TYPES-001 CERRADA** — `IrpConfig::threat_score_threshold` double→float. Parche IEEE 754 eliminado. EMECAS PROFILE=production ALL TESTS COMPLETE.
  - **fix(.gitignore)** — excluir protocol-EMECAS-output-*.md, docs/argus_ndr_v*.pdf, docs/latex/*.zip. Untrack build symlinks.
  - **Tag:** `v0.7.1-day148`.

### Hitos DAY 147 🎉
- **Bug fix pipeline-status** — pgrep fallback para procesos huérfanos (tmux + pgrep OR). Commit `42c04b06`.
  - **Búsqueda ruleset ET Open 2011** — no encontrado en fuentes públicas. Hallazgo clave: Neris CTU-13 escenario 42 usa HTTP C2, no solo IRC. Paper v21 §8.13 actualizado.
  - **Experimento Zeek 8.1.2 (tres paradigmas)** — modo offline (`zeek -r pcap`), scripts por defecto, determinístico:
    - Suricata 6.0.10: F1=0.000, TP=0 (sin firmas para Neris 2011)
    - Zeek 8.1.2 (default): F1=0.042, Precision=1.000, TP=14 (SSL::Invalid_Server_Cert)
    - aRGus NDR: F1=0.9985, Recall=1.000, TP=646
  - **weird.log**: Zeek observa IRC, HTTP beaconing, SMB lateral movement, spam — sin alertar. Distinción observabilidad vs detección.
  - **Paper Draft v21** — §8.13 hallazgos reales DAY 147 + Springer 2023 (signature aging).
  - **Paper Draft v22** — §8.14 Three Paradigms (tablas + análisis + §13 reproducibilidad Zeek).
  - **Makefile**: `make experiment-zeek-up/run/results`. Infraestructura `experiments/zeek-comparative/`.
  - **Tag:** `v0.7.1-day147`.

### Hitos DAY 143-144 🎉
- **DEBT-IRP-NFTABLES-001 CERRADA** — IRP completo: config → disparo → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests.
  - **DEBT-IRP-SIGCHLD-001 CERRADA** — SA_NOCLDWAIT. SigchldTest.NoZombiesAfterNForks PASSED.
  - **DEBT-IRP-AUTOISO-FALSE-001 CERRADA** — isolate.json única fuente de verdad. 5 tests PASSED.
  - **DEBT-IRP-BACKUP-DIR-001 CERRADA** — /run/argus/irp/. AppArmor + provision.sh actualizados.
  - **Gate ODR production SUPERADO** — 3 ODR violations reales detectadas y corregidas bajo -flto.

### Deuda técnica abierta

| Deuda | Prioridad | Target |
|-------|-----------|--------|
| DEBT-IRP-TMPFILES-001 | ✅ CERRADA DAY 146 | tmpfiles.d + provision.sh |
| DEBT-IRP-IPSET-TMP-001 | ✅ CERRADA DAY 146 | ipset_wrapper /run/argus/irp/ |
| DEBT-EMECAS-VERIFICATION-001 | ✅ CERRADA DAY 146 | README.md blockquote EMECAS |
| DEBT-IRP-FLOAT-TYPES-001 | ✅ CERRADA DAY 148 | float consistente con Detection::confidence (protobuf) |
| DEBT-IRP-PROB-CONJUNTA-001 | 🟡 P1 | post-FEDER (señal conjunta) |
| DEBT-ETCD-HA-QUORUM-001 | 🔴 P0 | post-FEDER (OBLIGATORIO) |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Alta | post-merge |
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | 🔴 Alta pre-FEDER | ADR-044 definido — implementación DAY 150+ |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | ✅ CERRADA DAY 149 | Vault dev mode + K_pseudo prototipo |
| DEBT-MUTEX-ROBUST-001 | 🟡 P1 | post-FEDER |
| DEBT-PARQUET-TIMESTAMP-NS-001 | 🟡 P2 | firewall-acl-agent ms→ns en origen |
| DEBT-ALERTING-EDGE-SOS-001 | 🔴 P1 pre-FEDER | SOS webhook edge→Discord/Telegram/email |
| DEBT-CRYPTO-STAMPEDE-001 | ✅ CERRADA DAY 150 | Jitter implementado en vault_client.cpp |
| DEBT-CRYPTO-HEARTBEAT-001 | 🟡 P1 | Heartbeat periódico etcd post-crypto_ready |
| DEBT-VAULT-HA-001 | 🟡 P1 post-FEDER | Vault HA backend raft para producción |
| DEBT-ADR040-001..012 | ⏳ | post-FEDER |
| DEBT-ADR041-001..006 | ⏳ | pre-FEDER |

| DEBT-PARQUET-SCHEMA-001 | ✅ CERRADA DAY 149 | Schema Arrow v1.0, 207K filas, 11-12x |
| DEBT-VAULT-FEDERATION-001 | 🟡 P1 pre-FEDER | Offboarding instalaciones: destrucción de claves, retención de datos GDPR |
| DEBT-LEGAL-DATA-RETENTION-001 | 🟡 P1 pre-FEDER | Dictamen jurídico GDPR retención datos pseudonimizados post-cliente |
| DEBT-KPSEUDO-ROTATION-MIGRATION-001 | 🟡 P1 pre-FEDER | Migración identidades Neo4j tras rotación K_pseudo |
| DEBT-GDPR-ERASURE-001 | 🟡 P1 pre-FEDER | Flujo derecho al olvido Art. 17 GDPR — comando borrado firmado |
| DEBT-CRYPTO-AUTONOMY-001 | 🔴 P1 pre-FEDER | Máquina de estados EXTENDED_AUTONOMY |
| DEBT-FIREWALL-AUTONOMY-MODE-001 | ✅ CERRADA DAY 154 | FirewallAutonomyReactor |
| DEBT-FIREWALL-DENY-SELECTIVE-001 | ✅ CERRADA DAY 155 | Cadena argus-autonomy selectiva, whitelist JSON |
| DEBT-CRYPTO-RECONCILIATION-001 | ✅ CERRADA DAY 157 | shared_mode + staleness guard 30s, 9/9 tests |
| DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001 | 🟡 P1 pre-FEDER | Cache cifrada en prod edge (LUKS obligatorio) |
| DEBT-EMECAS-DUAL-COMPILATION-001 | 🟡 P1 | CI compila ARGUS_VAULT_ENABLED=ON y OFF |
| DEBT-CRYPTO-REVOCATION-LOCAL-001 | 🟡 P1 post-FEDER | Revocación offline sin Vault |
| DEBT-LICENSE-VAULT-001 | ⏳ P2 post-FEDER | Servidor licencias en Vault (plugin system) |
| DEBT-PLUGIN-ENTERPRISE-001 | ⏳ P2 post-FEDER | Definir plugins enterprise vs community |
| DEBT-KPSEUDO-HKDF-HIERARCHY-001 | ⏳ P3 post-FEDER | Jerarquía HKDF para K_pseudo (host/flow/model desde K_root) |
### Próxima frontera — DAY 158+
1. ✅ **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA DAY 156**
   2. ✅ **DEBT-AUTONOMY-STATE-PERSISTENCE-001 CERRADA DAY 157**
   3. ✅ **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 CERRADA DAY 157**
   4. ✅ **DEBT-KEYPAIR-LIFECYCLE-PROD-001 CERRADA DAY 157**
   5. ✅ **DEBT-CRYPTO-RECONCILIATION-001 CERRADA DAY 157 (staleness guard B1)**
   6. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 P2** — `ExecStartPre=` + `check-bootstrap-status.sh`. Verificar firma Ed25519 antes de iniciar componentes dependientes.
   7. **DEBT-CRYPTO-AUTONOMY-001 P2** — Máquina de estados EXTENDED_AUTONOMY completa en `etcd-server`.
   8. **DEBT-ALERTING-EDGE-SOS-001 P1** — Webhook SOS configurable por despliegue.
   9. **BACKLOG-BENCHMARK-CAPACITY-001** — Benchmarks sintéticos VirtualBox (baseline) + hardware físico FEDER.

---

## 🏗️ Tres variantes del pipeline

| Variante | Estado | Descripción |
|----------|--------|-------------|
| **aRGus-dev** | ✅ Activa (`main`) | x86-debug, imagen Vagrant completa. Para investigación y desarrollo diario. |
| **aRGus-production** | 🟡 En construcción | x86-apparmor + arm64-apparmor. AppArmor enforce, cap_bpf, Falco, noexec. Para hospitales, escuelas, municipios. |
| **aRGus-seL4** | ⏳ Research track post-FEDER | Kernel seL4, libpcap. Reescritura completa. Branch independiente. |

---

## 📄 Preprint

**arXiv:** [arXiv:2604.04952 \[cs.CR\]](https://arxiv.org/abs/2604.04952)
**Published:** 3 April 2026 · **Draft v19** (ADR-029 Variant A vs B) · MIT license
**Code:** https://github.com/alonsoir/argus

---

## 🎯 Mission

Democratize enterprise-grade cybersecurity for hospitals, schools, and small organizations that cannot afford commercial solutions.

**Philosophy**: *Via Appia Quality* — Systems built like Roman roads, designed to endure.

> *"Un escudo que aprende de su propia sombra."*

---

## 📊 Validated Results

| Metric | Value | Notes |
|---|---|---|
| **F1-score (CTU-13 Neris)** | **0.9985** | Stable across 4 replay runs |
| **Precision** | **0.9969** | |
| **Recall** | **1.0000** | Zero missed attacks (FN=0) |
| **Suricata 6.0.10 F1 (CTU-13 Neris)** | **0.000** | 0 alerts — ET Open rules retired for 2011 threats |
| **Zeek 8.1.2 F1 (CTU-13 Neris, default)** | **0.042** | Precision=1.000, 14 TP (SSL::Invalid_Server_Cert) |
| **XGBoost Precision (CIC-IDS-2017 val)** | **0.9945** | In-distribution, threshold=0.8211 |
| **XGBoost Wednesday OOD** | **Documented impossibility** | Structural covariate shift — §8 paper |
| **Inference latency (XGBoost)** | **1.986 µs/sample** | Gate <2µs ✅ |
| **Inference latency (RF)** | **0.24–1.06 µs** | Per-class, embedded C++20 |
| **Throughput ceiling (virtualized)** | **~33–38 Mbps** | VirtualBox NIC limit, not pipeline |
| **Stress test** | **2,374,845 packets — 0 drops** | 100 Mbps requested, loop=3 |
| **RAM (full pipeline)** | **~1.28 GB** | Stable under load |
| **BSR — Dev VM** | **719 pkgs / 5.9 GB** | gcc, g++, clang, cmake present |
| **BSR — Hardened VM** | **304 pkgs / 1.3 GB** | NONE (check-prod-no-compiler: OK) ✅ |
| **AppArmor profiles** | **6/6 enforce** | cap_bpf (Linux ≥5.8), no cap_sys_admin |
| **Falco rules** | **11 aRGus-specific** | modern_ebpf driver |
| **Variant B tests** | **9/9 PASSED** | DAY 142 — buffer=8MB verificado |
| **ADR-029 Variant A eBPF (VBox)** | **~10 Mbps / 9,178 pps** | DAY 145 — techo virtio SKB mode |
| **ADR-029 Variant B libpcap (VBox)** | **~19 Mbps / 17,614 pps** | DAY 145 — ~2× eBPF en virtio |
| **IRP cycle** | **PASS** | NORMAL→ISOLATED→ROLLBACK→NORMAL DAY 142 |

> **Nota ADR-029 — Failed packets (2,630):** Artefacto fijo del pcap CTU-13 Neris. Frames jumbo que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). Conteo idéntico en los 6 runs — confirma origen en el fichero, no en el pipeline. El sniffer nunca ve esos frames. **No son errores del pipeline.**

---

## 🔒 Security Hardening — ADR-030 Variant A

### Build/Runtime Separation (BSR) — ADR-039

| Environment | Packages | Disk | Compilers |
|---|---|---|---|
| Dev VM | 719 | 5.9 GB | gcc, g++, clang, cmake |
| **Hardened VM** | **304** | **1.3 GB** | **NONE** ✅ |

### Linux Capabilities — no SUID root

| Component | Capabilities |
|---|---|
| sniffer | `cap_net_admin,cap_net_raw,cap_bpf,cap_ipc_lock` |
| firewall-acl-agent | `cap_net_admin` |
| etcd-server | `cap_ipc_lock` (+ LimitMEMLOCK=16M) |
| argus-network-isolate | `cap_net_admin` (AppArmor enforce — DAY 143) |
| ml-detector, rag-ingester, rag-security | none |

### AppArmor — 6 profiles enforce · Falco — 11 aRGus-specific rules

---

## 🔧 Prerequisites

### macOS

```bash
brew install --cask virtualbox
brew install --cask vagrant
xcode-select --install
```

> **Note:** `git clone --recurse-submodules` is required. `third_party/llama.cpp` is a git submodule. Cloning without this flag leaves it empty and `rag-security` builds without LLM support. Use `make submodule-init` to fix an existing clone.

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y make
```

VirtualBox from official repo (apt may be outdated):
```bash
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo gpg --dearmor -o /usr/share/keyrings/oracle-virtualbox.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox.gpg] https://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | sudo tee /etc/apt/sources.list.d/virtualbox.list
sudo apt-get update && sudo apt-get install -y virtualbox-7.0
```

Vagrant:
```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y vagrant
```

### Linux (RHEL/Fedora/CentOS)

```bash
sudo dnf install -y make
```

VirtualBox:
```bash
sudo dnf install -y kernel-devel kernel-headers dkms
sudo dnf config-manager --add-repo https://download.virtualbox.org/virtualbox/rpm/fedora/virtualbox.repo
sudo dnf install -y VirtualBox-7.0
```

Vagrant:
```bash
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf install -y vagrant
```

> **Note:** `git clone --recurse-submodules` is required. `third_party/llama.cpp` is a git submodule. Cloning without this flag leaves it empty and `rag-security` builds without LLM support. Use `make submodule-init` to fix an existing clone.

> **Note (RHEL/CentOS):** VirtualBox requires Secure Boot to be disabled or the kernel module to be signed. On WSL2, VirtualBox is not supported — use a native Linux install.

### Windows 11 (best-effort, not officially supported)

> ⚠️ **aRGus NDR only produces Linux binaries** (x86-64 and ARM64). There are no Windows binaries and none are planned. The pipeline runs inside a Linux VM — Windows is only the host.

Prerequisites:
```powershell
winget install Git.Git
winget install Oracle.VirtualBox
winget install Hashicorp.Vagrant
```

Run all commands from **Git Bash** (not CMD or PowerShell — the Makefile requires bash syntax).

> ⚠️ **Hyper-V conflict:** Windows 11 enables Hyper-V by default for WSL2. VirtualBox 7.0+ has experimental Hyper-V support but with ~30% performance penalty. You must choose one of:
> - Disable Hyper-V (loses WSL2): `bcdedit /set hypervisorlaunchtype off` + reboot
>   - Use VirtualBox 7.0+ in Hyper-V mode (slower, less stable)

**Not tested by the maintainer.** If you hit issues on Windows 11, please [open an issue](https://github.com/alonsoir/argus/issues) — we'll help with the resources we have.


---

## 🚀 Quick Start

> ⚠️ **Vagrant is required.** Native Linux bootstrap without Vagrant is not yet implemented ([DEBT-NATIVE-LINUX-BOOTSTRAP-001](docs/KNOWN-DEBTS-v0.6.md)). Running `make` directly on a bare Linux host will fail.

```bash
# STEP 1 — Clone with submodules (mandatory — llama.cpp is a git submodule)
git clone --recurse-submodules https://github.com/alonsoir/argus.git
cd argus

# Already cloned without --recurse-submodules? Fix it:
# make submodule-init
```

> 📦 **TinyLlama model** (`tinyllama-1.1b-chat-v1.0.Q4_0.gguf`, ~700MB) is downloaded
> automatically during `vagrant up`. It is gitignored and never committed to the repo.

```bash
# STEP 2 — Start VM and provision all dependencies (~20-30 min first time)
# Downloads TinyLlama, builds llama.cpp, installs FAISS/ONNX/XGBoost/libsodium
make up && make bootstrap
```

### Workflow diario (REGLA EMECAS)

```bash
vagrant destroy -f && vagrant up && make bootstrap && make test-all
```

> **¿Por qué EMECAS?** El protocolo garantiza reproducibilidad total: cada sesión parte de una VM limpia, claves criptográficas regeneradas, pipeline compilado desde cero y suite de tests completa. Un ❌ en cualquier punto es bloqueante — no se fusiona ni avanza trabajo hasta que `make test-all` termina con exit 0 y `pipeline-status` muestra 6/6 RUNNING. El sniffer puede tardar hasta 4 segundos en estabilizar su sesión tmux tras el arranque; si `pipeline-status` muestra ❌ sniffer inmediatamente después del bootstrap, esperar 5 segundos y repetir `make pipeline-status` antes de escalar.



### Hardened VM (ADR-030 Variant A)

```bash
make hardened-full   # destroy → up → provision → build → deploy → check
```

---

## 🗺️ Roadmap

### ✅ DONE — DAY 146 (9 May 2026) — Suricata Comparative + Deudas 🎉

| Task | Result |
|---|---|
| EMECAS verde | ✅ 4 deudas cerradas |
| Experimento Suricata vs aRGus | ✅ 0 alertas Suricata vs F1=0.9985 aRGus |
| Makefile up/halt-argus/suricata | ✅ Topología dual |
| Paper Draft v20 | ✅ §8.13 + Tabla comparativa empírica |

### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉

| Task | Result |
|---|---|
| EMECAS ritual | ✅ 65/65 PASSED |
| PCAP relay x86 eBPF (Variant A) | ✅ ~10 Mbps, 320,524 pkts, exit=0 |
| PCAP relay x86 libpcap (Variant B) | ✅ ~19 Mbps, 320,524 pkts, exit=0 |
| Merge feature/variant-b-libpcap → main | ✅ v0.7.0-variant-b |
| Bootstrap múltiple (x86-ebpf / x86-libpcap) | ✅ Makefile actualizado |
| Paper Draft v19 | ✅ §6 ADR-029, §10.9, §11.17, §12 |

### ✅ DONE — DAY 143-144 — IRP completo + ODR gate 🎉
- [x] DEBT-IRP-NFTABLES-001 CERRADA — IRP completo, AppArmor 7/7 enforce, 12/12 tests
  - [x] DEBT-IRP-SIGCHLD-001 CERRADA — SA_NOCLDWAIT
  - [x] DEBT-IRP-AUTOISO-FALSE-001 CERRADA — isolate.json única fuente de verdad
  - [x] DEBT-IRP-BACKUP-DIR-001 CERRADA — /run/argus/irp/
  - [x] Gate ODR production PASSED — 3 violations reales corregidas bajo -flto

### ✅ DONE — DAY 138-142 — ADR-029 Variant B pipeline 🎉
- [x] DEBT-CAPTURE-BACKEND-ISP-001 CERRADA — `CaptureBackend` 5 métodos puros
  - [x] DEBT-VARIANT-B-PCAP-IMPL-001 CERRADA — pipeline pcap → proto → LZ4 → ChaCha20 → ZMQ
  - [x] DEBT-VARIANT-B-BUFFER-SIZE-001 CERRADA — pcap_create()+pcap_set_buffer_size()
  - [x] DEBT-VARIANT-B-MUTEX-001 CERRADA (Nivel 1) — exclusión mutua via tmux
  - [x] Suite 9 tests Variant B — 9/9 PASSED

### ✅ DONE — DAY 137 (30 Apr 2026) — feature/variant-b-libpcap 🎉
- [x] EMECAS dev + EMECAS hardened PASSED
  - [x] capture_backend.hpp · ebpf_backend.hpp/cpp · pcap_backend.hpp/cpp
  - [x] main_libpcap.cpp — Variant B sin #ifdef
  - [x] sniffer-libpcap compilable y arranca limpio

### ✅ DONE — DAY 135-136: v0.6.0 🎉
- [x] make hardened-full EMECAS PASSED
  - [x] feature/adr030-variant-a → main MERGEADO
  - [x] Tag v0.9.3-day158-variant-a publicado
  - [x] arXiv replace v15 → v18 ENVIADO

### ✅ DONE — DAY 133-134: ADR-030 + ADR-040 + ADR-041 🎉
- [x] AppArmor 6/6 enforce · Falco 10 reglas · cap_bpf · Paper v18
  - [x] ADR-040 ML Retraining Contract (8/8, 17 enmiendas)
  - [x] ADR-041 Hardware Acceptance Metrics FEDER (8/8)
  - [x] Pipeline E2E hardened · check-prod-all PASSED

### ✅ DONE — DAY 151 (14 May 2026) — ICryptoProvider + etcd-server STEP 0 🎉

| Task | Result |
|---|---|
| ICryptoProvider interfaz abstracta (ADR-044) | ✅ SeedFileProvider + VaultProvider + factoría |
| #ifdef ARGUS_VAULT_ENABLED confinado en crypto_provider.cpp | ✅ único punto de decisión |
| libcrypto_provider.so instalada | ✅ /usr/local/lib |
| test_crypto_provider_community 10/10 | ✅ fixture propio sin root |
| etcd-server STEP 0: bootstrap status + fingerprint | ✅ 0079087736d9d62a... |
| Opción B SRP: SeedClient/CryptoTransport ≠ ICryptoProvider | ✅ responsabilidades separadas |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 registrada | ✅ P1 pre-FEDER |
| make test-all verde 55+ tests | ✅ pipeline 6/6 RUNNING |
| ADR-045 aprobado (VaultClient por composición) | ✅ Consejo 8/8 |

### 🔜 NEXT — DAY 149+ (secuencia confirmada Consejo 8/8)

| Priority | Task |
|---|---|
| ✅ | **DAY 149** — DEBT-PARQUET-SCHEMA-001: CERRADA. Schema Arrow v1.0, 207K filas, 11-12x |
| ✅ | **DAY 149** — DEBT-CRYPTO-MATERIAL-STORAGE-001: CERRADA. Vault dev mode + K_pseudo prototipo |
| 🔴 P0 | **DAY 150** — EMECAS + provision_crypto.sh + common/vault_client (ADR-044 implementación) |
| 🟡 P1 | **DAY 153-155** — DEBT-JENKINS-SEED-DISTRIBUTION-001: CI/CD seed distribution |
| 🟡 P1 | **DAY 156+** — feature/adr029-variant-c-arm64: solo si A+B+C verdes |
| 🟡 P1 | **Esta semana** — Email Dr. Andrés Caro Lindo: iniciar DEBT-LEGAL-DATA-RETENTION-001 |

### 🔜 THEN — PHASE 5: Adversarial Capture-Retrain Loop

- DEBT-PENTESTER-LOOP-001 — ACRL completo
  - BACKLOG-FEDER-001 — presentación Andrés Caro Lindo
  - aRGus-production ARM64
  - aRGus-seL4 research branch (post-FEDER, equipo especializado)

---

## 🗺️ Milestones

- ✅ DAY 111: **arXiv:2604.04952 PUBLICADO** 🎉
  - ✅ DAY 113: **ADR-025 MERGED — v0.3.0-plugin-integrity** 🎉
  - ✅ DAY 118: **PHASE 3 COMPLETADA — v0.4.0** 🎉
  - ✅ DAY 122: **PHASE 4 COMPLETADA — v0.5.0-preproduction** 🎉
  - ✅ DAY 124: **ADR-037 MERGED — v0.9.3-day158** 🎉
  - ✅ DAY 129: **CWE-78 CERRADO — execv() sin shell** 🎉
  - ✅ DAY 130: **REGLA EMECAS · libFuzzer 2.4M runs** 🎉
  - ✅ DAY 133: **ADR-030 Variant A — cap_bpf · AppArmor 6/6 · Falco 10 reglas** 🎉
  - ✅ DAY 134: **ADR-040 (8/8, 17 enmiendas) · ADR-041 FEDER HW Metrics (8/8)** 🎉
  - ✅ DAY 136: **v0.9.3-day158-variant-a · merge main** 🎉
  - ✅ DAY 137: **feature/variant-b-libpcap · sniffer-libpcap compilable · KISS** 🎉
  - ✅ DAY 138: **ISP cerrado · pipeline Variant B completo · 8/8 tests · Consejo 8/8** 🎉
  - ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio** 🎉
  - ✅ DAY 141: **DEBT-VARIANT-B-CONFIG-001 · sniffer-libpcap.json · emails FEDER** 🎉
  - ✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉
  - ✅ DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA — IRP completo · AppArmor 7/7 · 12 tests** 🎉
  - ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 65/65 tests** 🎉
  - ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio · Bootstrap múltiple · Paper v19 · v0.7.0-variant-b** 🎉
  - ✅ DAY 146: **Experimento Suricata comparativo · 0 alertas ET Open vs F1=0.9985 aRGus · Paper v20 §8.13 · v0.7.1-day146** 🎉
  - ✅ DAY 147: **Experimento tres paradigmas (Suricata+Zeek+aRGus) · Paper v22 §8.14 · HTTP C2 hallazgo · weird.log behavioral profile · v0.7.1-day147** 🎉
  - ✅ DAY 147: **ADR-0043 v4 ACEPTADO** — Memoria Episódica Distribuida, Consejo 8/8, 4 versiones 🎉
  - ✅ DAY 149: **Schema Parquet Arrow v1.0 · Vault CI/CD pipeline · ADR-044 · Ansible+Jinja2 · 5 PRs · v0.7.2-day149** 🎉
  - ✅ DAY 150: **ADR-044 implementación completa · provision_crypto.sh · vault_client C++20 · Jenkinsfile Provision Crypto · EMECAS verde** 🎉
  - ✅ DAY 154: **ADR-045 VaultClient decomposition · DEBT-FIREWALL-AUTONOMY-MODE-001 CERRADA · 48/48 tests · v0.8.0-adr045** 🎉
  - ✅ DAY 155: **DEBT-FIREWALL-DENY-SELECTIVE-001 · DEBT-AUTONOMY-ZMQ-EVENTS-001 · BACKLOG-ZMQ-TUNING-001 · 49/49 tests · EMECAS HARDENED PASSED · v0.9.0-day155** 🎉
  - ✅ DAY 163: **FASE 0+1 crypto lifecycle · Modelo B vendor.key efímero · CryptoProviderHandle RCU · ADR-045 v2 (Consejo 8/8) · 9/9 tests** 🎉
  - ✅ DAY 161: **DEBT-WIRE-PROTOCOL-TEST-001 · Jenkinsfile.dev+prod · test-e2e-live delta · Consejo 8/8 · v0.9.5-day161 (pendiente)** 🎉
  - ✅ DAY 160: **DEBT-ENTERPRISE-PLUGIN-001 · libvault_provider.so 6/6 tests · Jenkins 2.555.2 + Vault v2.0.1 · ADR-048 Dataset Production Roadmap definido · v0.9.4-day160** 🎉
  - ✅ DAY 157: **4 deudas cerradas · Consejo 8/8 · Staleness guard · Keypair lifecycle prod · Bootstrap firmado · EMECAS VERDE · v0.9.2-day157** 🎉
  - ✅ DAY 156: **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 · Test B 7/7 + Test A 4/4 · Fix ZMQ slow joiner · EMECAS VERDE 50/50 · v0.9.1-day156** 🎉
  - ✅ DAY 151: **ICryptoProvider + SeedFileProvider + VaultProvider · etcd-server STEP 0 · ADR-045 aprobado · 55+ tests verdes · v0.8.0-day151** 🎉
  - ✅ DAY 148: **Suricata offline irrefutable · Paper v23 · arXiv replace v3 · DEBT-IRP-FLOAT-TYPES-001 cerrada · v0.7.1-day148** 🎉
  - ✅ DAY 164: **FASE 2a+2b enterprise · HttpEtcdRegistrar + CryptoEpochCoordinator · 10/10 tests** 🎉
  - ✅ DAY 165: **FASE 3 wire header epoch_id · 13/13 tests · EMECAS++ OSS verde · Consejo 8/8 protocolo 3 actos** 🎉
  - ✅ DAY 166: **EMECAS++ 3 actos verdes · merge enterprise a main · VaultProvider caché RCU confirmado · vault-fault-inject PASSED · Zero downtime demostrado · Tag v1.0.0-day166** 🎉
  - ✅ DAY 167: **DEBT-ARGUSPP-NTP-001 (P0) · correlation-engine scaffold ADR-048 F2 · BACKLOG-CI-ENTERPRISE-001 Jenkins gate · merge main 7b45feca** 🎉
  - ✅ DAY 168: **Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x · community-id Suricata/Zeek · 3 reglas permanentes · merge main 21642e87** 🎉
  - ✅ DAY 169: **Día de arquitectura · ADR-046 v4 + AdapterSpec v1 · separación de planos · ADR-050 pendiente · community_id nativo aRGus P0 abierto** 🏛️
  - ✅ DAY 171: **Cross-check E2E community_id 3 ventanas VERDE · paridad operacional demostrada · helper observable + verificador + acceptance_criteria.md congelado (Consejo 8/8) · DEBT-COUNTER-DUMP-001 abierta** 🎉
  - ✅ DAY 170: **community_id cross-sensor sellado (aRGus+Zeek+Suricata, seed 0, vs oráculo) · de-dup BACKLOG · Consejo 8/8 P1/P2/P3 · ADR-051/052 pendientes** 🎉
  - 🔜 DAY 172: **volcado contadores aRGus a fichero parseable (DEBT-COUNTER-DUMP-001) + ADR-051/052 borrador + DEBT-NEO4J-FLOW-KEY-001 (esquema Neo4j) + ADR-050 MITRE borrador + DEBT-ARGUSPP-SURICATA-001 (eve.json → correlation-engine)**
  - ✅ DAY 173: **ADR-052 v3.2 RATIFICADA (Consejo 8/8)** — Multi-node Flow Identity & Host↔Net · DEBTs P0→P3 de identidad de flujo · ADR-053 stub (JA3/JA4/BGP) · desbloquea DEBT-NEO4J-FLOW-KEY-001 🏛️

---

## 🧠 Consejo de Sabios — Multi-Model Peer Review

**Claude** (Anthropic) · **Grok** (xAI) · **ChatGPT** (OpenAI) · **DeepSeek** · **Qwen** (Alibaba) · **Gemini** (Google) · **Kimi** (Moonshot) · **Mistral**

Metodología: desacuerdo estructurado. Documentado en §6 del preprint.

---

## Hardened Deployment (ADR-030 Variant A)

```bash
make hardened-full          # EMECAS sagrado — destroy → up → provision → build → deploy → check
make hardened-redeploy      # iteración rápida sin destroy
make prod-deploy-seeds      # deploy seeds explícito (nunca en EMECAS)
make check-prod-all         # 5/5 gates: BSR + AppArmor + cap_bpf + permissions + Falco
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE)

**Via Appia Quality** 🏛️ — *Built to last decades.*