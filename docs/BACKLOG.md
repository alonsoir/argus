# aRGus NDR — BACKLOG
*Última actualización: DAY 151 — 14 Mayo 2026*

---

## 📐 Criterio de compleción

| Estado | Criterio |
|---|---|
| ✅ 100% | Implementado + probado en condiciones reales + resultado documentado |
| 🟡 80% | Implementado + compilando + smoke test pasado, sin validación E2E completa |
| 🟡 60% | Implementado parcialmente o con valores placeholder conocidos |
| ⏳ 0% | No iniciado |

---

## 📋 POLÍTICA DE DEUDA TÉCNICA

- **Bloqueante:** se cierra dentro de la feature en que se detectó. No hay merge a main sin test verde.
- **No bloqueante con feature natural:** se asigna a la feature destino. Documentada con ID de feature.
- **No bloqueante sin feature natural:** se acumula hasta abrir `feature/tech-debt-cleanup` (3+ DEBTs sin destino claro).
- **Toda deuda tiene test de cierre.** Implementado sin test = no cerrado.
- **REGLA CRÍTICA:** El Vagrantfile y el Makefile son la única fuente de verdad.
- **REGLA DE SCRIPTS:** Lógica compleja → `tools/script.sh`, nunca inline en Makefile.
- **REGLA SEED:** La seed ChaCha20 es material criptográfico secreto. NUNCA en CMake ni logs. Solo runtime: mlock() + explicit_bzero().
- **REGLA PERMANENTE (DAY 124 — Consejo 7/7):** Ningún fix de seguridad en código de producción se mergea sin test de demostración RED→GREEN. Sin excepciones.
- **REGLA PERMANENTE (DAY 125 — Consejo 8/8):** Todo fix de seguridad incluye: (1) unit test sintético, (2) property test de invariante, (3) test de integración en el componente real. Sin excepciones.
- **REGLA PERMANENTE (DAY 127 — Consejo 8/8):** La taxonomía safe_path tiene tres primitivas activas y una futura. Toda nueva superficie de ficheros debe clasificarse con PathPolicy antes de implementar.
- **REGLA PERMANENTE (DAY 128 — Consejo 8/8):** IPTablesWrapper y cualquier ejecución de comandos del sistema usa execve() directo sin shell. Nunca system() ni popen() con strings concatenados.
- **REGLA PERMANENTE (DAY 129 — Consejo 8/8 RULE-SCP-VM-001):** Toda transferencia de ficheros entre VM y macOS usa `scp -F vagrant-ssh-config` o `vagrant scp`. PROHIBIDO pipe zsh — trunca a 0 bytes silenciosamente.
- **PROTOCOLO CANÓNICO (DAY 130 — REGLA EMECAS):** Toda sesión de desarrollo comienza con `vagrant destroy -f && vagrant up && make bootstrap && make test-all`. Sin excepciones.
- **REGLA PERMANENTE (DAY 133 — Consejo 8/8):** `cap_sys_admin` está prohibida en imágenes de producción si el kernel es ≥5.8. Usar `cap_bpf` para operaciones eBPF. Documentar fallback con DEBT-KERNEL-COMPAT-001 si necesario.
- **REGLA PERMANENTE (DAY 134 — Consejo 8/8):** `make hardened-full` es el EMECAS sagrado de la hardened VM — siempre incluye `vagrant destroy -f`. Para iteración de desarrollo usar `make hardened-redeploy` (sin destroy). Los gates `check-prod-all` se ejecutan siempre en ambos modos.
- **REGLA PERMANENTE (DAY 134 — Consejo 8/8):** Las semillas criptográficas NO se transfieren en el procedimiento EMECAS. La hardened VM arranca sin seeds. Target `prod-deploy-seeds` explícito para el momento del deploy real. Los WARNs de `seed.bin no existe` en `check-prod-permissions` son estado correcto por diseño.
- **REGLA PERMANENTE (DAY 134 — Consejo 8/8):** Falco .deb y artefactos binarios de terceros van en `dist/vendor/` (gitignored). El hash SHA-256 se committea en `dist/vendor/CHECKSUMS`. `make vendor-download` descarga y verifica. Si hash no coincide → abort.
- **REGLA PERMANENTE (DAY 134 — Consejo 8/8):** DEBT-ADR040-002 (`confidence_score` en ml-detector) es prerequisito bloqueante de DEBT-ADR040-006 (IPW). No implementar IPW sin verificar primero que el campo existe y varía en runtime.
- **REGLA PERMANENTE (DAY 138 — Consejo 8/8):** Variant B (libpcap) es monohilo por diseño de pcap_dispatch. Los campos de multihilo no aparecen en sniffer-libpcap.json — se hardcodean en el binario con comentario explícito. No configurable, no negociable.
- **REGLA PERMANENTE (DAY 138 — Consejo 8/8):** ODR violations en C++20 son Undefined Behaviour bloqueante. Sub-tarea P0 de DEBT-COMPILER-WARNINGS-CLEANUP-001. Ningún tag posterior sin resolver ODR primero.
- **REGLA PERMANENTE (DAY 140 — Consejo 8/8):** `-Werror` activo en todos los CMakeLists. 0 warnings es un invariante permanente — ningún merge sin `make all 2>&1 | grep -c 'warning:'` = 0.
- **REGLA PERMANENTE (DAY 140 — Consejo 8/8):** Código de terceros con API deprecated → suprimir por fichero en CMake + entrada en `docs/THIRDPARTY-MIGRATIONS.md`. Nunca suprimir warnings en código propio.
- **REGLA PERMANENTE (DAY 140 — Consejo 7/8):** En C++20, usar `[[maybe_unused]]` para parámetros no usados en interfaces virtuales y código nuevo. `/*param*/` solo en stubs temporales con DEBT asociada. Migrar progresivamente (DEBT-MAYBE-UNUSED-MIGRATION-001).
- **REGLA PERMANENTE (DAY 140 — Consejo 8/8):** Gate ODR pre-merge obligatorio: `make PROFILE=production all` antes de cualquier merge a main. Jenkinsfile documenta el gate CI cuando el servidor FEDER esté disponible (DEBT-ODR-CI-GATE-001).
- **REGLA PERMANENTE (DAY 141 — Consejo 8/8):** Variant A y Variant B nunca corren simultáneamente en el mismo hardware. Exclusión mutua via script de arranque (bash/python en Makefile), pre-FEDER. La lógica de detección NO entra en los binarios — separación de responsabilidades.
- **REGLA PERMANENTE (DAY 141 — Consejo 8/8):** `buffer_size_mb` es variable por diseño en sniffer-libpcap.json — permite trazar la curva de optimización de buffer en hardware real. Implementación pcap_create()+pcap_set_buffer_size() pre-FEDER obligatoria antes del benchmark ARM64.
- **REGLA PERMANENTE (DAY 141 — Consejo 8/8):** Clasificadores de warnings de build: script grep/awk determinista. Un LLM no determinista no hace trabajo determinista.
- **REGLA PERMANENTE (DAY 142 — Consejo 8/8 + founder):** El criterio de disparo del IRP nunca se basa en una señal única. Para FEDER: `threat_score >= 0.95 AND event_type IN (ransomware, lateral_movement, c2_beacon)`. En entornos hospitalarios, un falso positivo sobre un equipo médico crítico (ventilador, bomba de infusión) conectado a la intranet/DMZ es inaceptable. La señal debe ser explicable, auditable y multi-componente.
- **REGLA PERMANENTE (DAY 142 — Consejo 8/8 + founder):** `auto_isolate: true` por defecto en `isolate.json`. El sistema protege sin que el administrador toque nada. Desactivar el aislamiento automático es un acto explícito y consciente. Instalar y funcionar.
- **REGLA PERMANENTE (DAY 142 — Consejo 8/8):** Todo trigger de aislamiento automático usa `fork()+execv()`. El proceso padre (firewall-acl-agent) nunca muere. El agente debe sobrevivir al aislamiento para continuar registrando evidencia forense. Un agente muerto durante un ataque activo es exactamente lo que el atacante busca.
- **REGLA PERMANENTE (DAY 142 — Consejo 8/8):** AppArmor `enforce` desde el primer deploy de cualquier nuevo componente. La fase `complain` no es una característica de seguridad — es deuda de validación. Si el perfil bloquea algo legítimo, se descubre en dev, no en producción.
- **REGLA PERMANENTE (DAY 144 — Consejo 8/8):** `isolate.json` es la ÚNICA fuente de verdad para `auto_isolate`. Campo obligatorio — sin fallback silencioso. Si falta el fichero o el campo, el arranque falla ruidosamente con mensaje claro. Sin excepciones.
- **REGLA PERMANENTE (DAY 144 — Consejo 8/8):** `assert()` debe estar activo en todos los tests independientemente del PROFILE. Usar `target_compile_options(test_target PRIVATE -UNDEBUG)` en CMakeLists de tests. `-DNDEBUG` de producción no debe silenciar la cobertura de tests.
- **REGLA PERMANENTE (DAY 144 — gate ODR confirmado):** `make PROFILE=production all` detecta ODR violations reales bajo `-flto`. Confirmado en DAY 144: 3 categorías de violations encontradas y corregidas. El gate es obligatorio pre-merge sin excepciones.
- **REGLA PERMANENTE (DAY 142 — macOS):** zsh intercepta `!` en heredocs. Para código C++ con emojis o caracteres especiales: siempre `vagrant ssh << 'SSHEOF'` con Python dentro. Nunca heredoc directo desde zsh para código complejo.

---

## 🏗️ Tres variantes del pipeline

| Variante | Estado | Descripción |
|----------|--------|-------------|
| **aRGus-dev** | ✅ Activa | x86-debug, imagen Vagrant completa. Para desarrollo diario. |
| **aRGus-production** | 🟡 En construcción | x86-apparmor + arm64-apparmor. Debian optimizado. Para hospitales, escuelas, municipios. |
| **aRGus-seL4** | ⏳ No iniciada | Apéndice científico. Kernel seL4, libpcap. Branch independiente. |

---

## ✅ CERRADO DAY 151

### ICryptoProvider — Abstracción criptográfica (ADR-044 implementación completa) — DAY 151
- **Status:** ✅ COMPLETADO DAY 151 — main @ `9e692a4e`
- **ICryptoProvider** interfaz abstracta: `get_material()`, `refresh()`, `is_healthy()`, `component_name()`, `get_operational_mode()`
- **SeedFileProvider** (community): `SeedClient` → `crypto_sign_seed_keypair()` → `CryptoMaterial`. Misma derivación Kimi D12.
- **VaultProvider** (enterprise): wrapper delgado sobre `VaultClient` existente.
- **`CryptoProvider::create()`**: factoría, único punto con `#ifdef ARGUS_VAULT_ENABLED` (confinado en `crypto_provider.cpp`).
- **`libcrypto_provider.so`** instalada en `/usr/local/lib`. Headers en `/usr/local/include/vault_client/`.
- **test_crypto_provider_community 10/10 PASSED**: fixture propio con `mkdtemp` + `seed.bin` sintético `0400` — sin dependencia de root.
- **Decisión Opción B (SRP)**: `SeedClient`+`CryptoTransport` (canal ZeroMQ) ≠ `ICryptoProvider` (identidad Ed25519). `CryptoTransport` no tocado.
- **etcd-server STEP 0**: `CryptoProvider::create()` → fingerprint Ed25519 → `/run/argus/etcd-bootstrap-status.json` (0600) → eliminado tras `g_server->start()`. Verificado en log: `fingerprint: 0079087736d9d62a...`
- **ADR-045 aprobado (Consejo 8/8)**: VaultClient por composición — `IVaultTransport`, `ICacheManager`, `IEtcdRegistrar`, `ICryptoDeriver`, `IJitterStrategy`. Implementación DAY 153+.
- **Nuevas deudas DAY 151:**
  - `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` (P1 pre-FEDER): bootstrap status sin firma Ed25519
  - `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (P1): escribir estado autonomía firmado al entrar en AUTONOMOUS
  - `DEBT-AUTONOMY-CLOCK-INJECTION-001` (P1): Clock inyectable en CryptoAutonomyStateMachine para tests
  - `DEBT-AUTONOMY-ZMQ-EVENTS-001` (P1): cada transición emite evento ZeroMQ `crypto.autonomy.transition`
- **make test-all**: ALL TESTS COMPLETE — 55+ tests, pipeline 6/6 RUNNING ✅

## ✅ CERRADO DAY 150

### EMECAS + ADR-044 implementación — DAY 150
- **Status:** ✅ COMPLETADO DAY 150 — main @ `93b4d39c` — 4 PRs mergeados
- **fix/parquet-convert-vagrant-ssh (PR #69):** `parquet-convert` y `test-parquet` ejecutaban en macOS host. Patrón `vagrant ssh -c` aplicado. `make test-all` verde completo — 207,190 filas Parquet. ROUNDTRIP PASSED.
- **feat(adr044): provision_crypto.sh (PR #70):** Script Bash. Vault KV v1 en `argus/`. Seeds 32 bytes por familia (A, B, C) + etcd bootstrap especial. Idempotente (SKIP si existe, `--force` para regenerar). Assert `seed_dev != seed_prod`. Artifact `crypto_audit.json` con fingerprints `sha256(seed)`. Targets Makefile: `provision-crypto`, `provision-crypto-force`.
- **feat(adr044): vault_client C++20 (PR #71):** `libvault_client.so`. `VaultClient::fetch_crypto_material()`. Derivación Kimi D12: `kdf_derive → component_seed → sign_seed_keypair`. Fingerprint = `sha256(pk)` (Kimi D13). Jitter anti-stampede: `component_index * 500ms + rand(0..1000ms)`. Cache tmpfs TTL (1h dev, 72h prod), 0700. Edge autonomy: Vault KO + cache válida → `OK_FROM_CACHE` + WARN; Vault KO + cache vacía → `exit(1)`. `mlock()` opcional. 5/5 tests PASS. Targets: `vault-client-build/clean/test`.
- **feat(adr044): Jenkinsfile stage Provision Crypto (PR #72):** Stage entre `Quick Check` y `Deploy Configs`. Condicional: main siempre, otras ramas si `PROVISION_CRYPTO=true`. `env=prod` en main, `env=dev` en ramas. Artifact `crypto_audit_${BUILD_NUMBER}.json`. `error()` bloquea pipeline si Vault KO.

### Decisión arquitectónica open-core — DAY 150 (Consejo 8/8 + Founder)
- **Un solo binario por arquitectura.** Plugin system como mecanismo de licencias. Community = seed-client. Enterprise = plugins firmados activados por licencia en Vault.
- **`ARGUS_VAULT_ENABLED`** es el único separador compile-time. Solo controla qué `.cpp` linkea — ningún componente ve `#ifdef` en lógica de negocio.
- **`ICryptoProvider` interfaz abstracta** con `SeedFileProvider` (community) y `VaultProvider` (enterprise). Factoría `CryptoProvider::create()` es el único punto de decisión.
- **Cache cifrada obligatoria en producción.** Seed maestra en texto plano: JAMÁS. Sin cifrado de disco → sin cache → Vault obligatorio.

### Decisión autonomía extendida Opción D — DAY 150 (Consejo 8/8)
- **TTL = ventana de renovación preferente, nunca fecha de muerte.** La clave expira solo por revocación explícita firmada desde Vault, EMECAS, o tamper detection. Nunca por el paso del tiempo.
- **Firewall default-deny para tráfico nuevo** en modo EXTENDED_AUTONOMY — más agresivo, no menos.
- **Reconciliación obligatoria** al recuperar Vault — no vuelve a NORMAL sin handshake.
- **Circuit breaker configurable** (default 30 días) con alerta progresiva.
- **Logs firmados locales** con flag `EXTENDED_AUTONOMY=1` durante autonomía.

### DEBT-CRYPTO-STAMPEDE-001 — implementada en vault_client.cpp
- **Status:** ✅ CERRADO DAY 150 — jitter `component_index * 500ms + rand(0..1000ms)` implementado.

## ✅ CERRADO DAY 149

### DEBT-PARQUET-SCHEMA-001 — Schema Arrow v1.0
- **Status:** ✅ CERRADO DAY 149 — **Tag:** `v0.7.2-parquet-schema-001` · PR #62
- **Fix:** Schema Arrow ml_detector_events (15 fields) y firewall_acl_events (7 fields). Tipos acordados Consejo 8/8: int64 timestamps ns, float32 scores, dict(utf8) IDs, int8 enums. Converter CSV→Parquet (Snappy), validación roundtrip. 207,122 filas / 53 días. Ratio 11-12x ml-detector, 1.5x firewall. `make parquet-convert` + `make test-parquet` como dependencia de `test-all`.
- **DEBT-PARQUET-TIMESTAMP-NS-001 registrada:** firewall-acl-agent produce ms, workaround ms×1_000_000 en writer. Fix real: modificar firewall-acl-agent para emitir ns en origen. P2.

### DEBT-CRYPTO-MATERIAL-STORAGE-001 — Vault dev mode + K_pseudo
- **Status:** ✅ CERRADO DAY 149 — **Tag:** mergeado en main · PR #64
- **Fix:** Vault v2.0.0 instalado en Vagrantfile (all-dependencies, idempotente). `scripts/vault/prototype_k_pseudo.sh` valida: KV v2 `argus/k_pseudo`, HMAC-SHA256 determinismo OK, aislamiento K OK, post-destroy irrecuperable. Evidencia técnica para DEBT-LEGAL-DATA-RETENTION-001.

### DEBT-VAULT-PROVISION-PROD-001 — Vault/Ansible/Jinja2/Jenkins en Vagrant
- **Status:** ✅ CERRADO DAY 149 — PR #65
- **Fix:** Vault runtime en `vagrant/hardened-x86/Vagrantfile` y `vagrant/hardened-arm64/Vagrantfile` (BSR axiom respetado, sin compiler). Ansible + Jinja2 + Jenkins en `Vagrantfile` dev (solo dev, ADR-039). Principio: Ansible/Jenkins orquestan DESDE dev HACIA prod.

### Ansible + Jinja2 pipeline CI/CD — DAY 149
- **Status:** ✅ COMPLETADO DAY 149 — PRs #66, #67
- `ansible/inventory/{dev,prod}.yml`, `ansible/group_vars/{argus_dev,argus_prod}.yml`
- `ansible/templates/{sniffer,ml_detector_config,rag_logger_config}.json.j2`
- `ansible/playbooks/deploy_configs.yml` — ejecutado en VM: 9 OK, 3 changed, 0 failed
- `make deploy-configs` (dev) + `make deploy-configs-prod` (prod)
- Jenkins stage "Deploy Configs" entre Quick Check y ODR

### ADR-044 — CI/CD Crypto Pipeline
- **Status:** ✅ DEFINIDO DAY 149 — Consejo 8/8 aprobado
- Jenkins como entropy orchestrator, Vault como única autoridad criptográfica
- common/vault_client módulo C++20 interno (no plugin), cache tmpfs TTL, etcd barrera pre-arranque
- Paths por familia (ADR-021): `argus/{env}/families/family_{A,B,C}/seed`
- etcd-server excepción bootstrap. TODO O NADA con cache como extensión razonable.
- Rotación manual para FEDER. FailureAction=poweroff ELIMINADO — pipeline offline + alerta CRITICAL.
- Edge nodes autónomos: siguen operando si servidor central cae. TTL cache 72h prod.

### Paper Abstract v24 — DAY 149
- **Status:** ✅ CERRADO DAY 149 — PR #63
- "are complementary" → "are architecturally complementary by design"
- Consejo DAY 148 P1 refinamiento 8/8. No subido a arXiv — acumular.

## ✅ CERRADO DAY 148

### DEBT-IRP-FLOAT-TYPES-001 — Unificar tipos score float/double
- **Status:** ✅ CERRADO DAY 148 — **Commits:** `21b52347` (fix) · `82e81c3f` (untrack symlinks)
- **Fix:** `IrpConfig::threat_score_threshold`: `double 0.95` → `float 0.95f`. Consistente con `Detection::confidence` (protobuf `float`). Parche IEEE 754 (`static_cast<double>(...) < threshold - 1e-6`) eliminado de `batch_processor.cpp` `should_auto_isolate()`. Comparación directa `float < float`.
- **Decisión técnica:** `float` correcto para scores de salida del clasificador ML (0.0-1.0). `double` se mantiene en features de entrada del proto (mediciones de paquetes). Contrato protobuf no modificado.
- **EMECAS:** `make PROFILE=production test-all` — ALL TESTS COMPLETE.
- **Rama:** `fix/debt-irp-float-types-001` → PR #58 → main.

### Paper Draft v23 — DAY 148
- **Status:** ✅ CERRADO DAY 148
- **Cambios:** §8.13 párrafo offline validation (suricata -r -k none, 0 ET signatures). §8.14 framing taxonómico (decision architecture taxonomies, measurement layer, telemetry, observability does not imply classification). §10 Future Work 5 subsecciones (baremetal, corpus, acrl, hardened, Zeek Phase 2 detect-botnets.zeek). Tabla §8.2 fila Zeek 8.1.2. Abstract v23 con complementariedad tres paradigmas.
- **arXiv replace:** v19→v23 submitted como v3 (submit/7576269).

### Experimento Suricata offline — DAY 148 (validación irrefutable)
- **Status:** ✅ COMPLETADO DAY 148
- **Protocolo:** `suricata -r botnet-capture-20110810-neris.pcap -S /var/lib/suricata/rules/suricata.rules -k none`. 323,154 paquetes procesados directamente desde pcap. Sin infraestructura live-capture.
- **Ruleset:** 50,010 reglas ET Open (suricata-update 11 Mayo 2026): 251 IRC, 475 botnet/C2, 853 trojan.
- **Resultado:** 0 firmas ET externas disparadas. 128 alertas internas de motor (stream anomalies, protocol detection) — ninguna constituye detección de amenaza. `eve.json` confirma 0 eventos `event_type: alert` de firma ET.
- **Significado:** Elimina throughput, packet loss y timing como explicaciones alternativas al resultado DAY 146. Conclusión irrefutable: el gap es de cobertura de ruleset, no de metodología.
- **Satisface criterio Kimi** (P1 bloqueante Consejo DAY 147): ✅

### fix(.gitignore) + untrack — DAY 148
- **Status:** ✅ CERRADO DAY 148 — **Commit:** `69cdf144`
- Excluir `protocol-EMECAS-output-*.md`, `docs/argus_ndr_v*.pdf`, `docs/latex/*.zip`.
- Untrack build symlinks: `etcd-server/build`, `rag-ingester/build`, `tools/build`.
- Vagrantfile suricata-comparative: `mkdir -p suricata-offline suricata-nochecksum` en provision.

---

## ✅ CERRADO DAY 147

### Bug fix pipeline-status — pgrep fallback para procesos huérfanos
- **Status:** ✅ CERRADO DAY 147 — **Commit:** `42c04b06`
- **Problema:** sniffer PID visible en `pipeline-health` pero STOPPED en `pipeline-status` (proceso huérfano fuera de tmux).
- **Fix:** OR lógico `tmux has-session || pgrep -x <binary>` para los 6 componentes. Script `fix_pipeline_status.py`.
- **Test de cierre:** `make pipeline-status` muestra 6/6 ✅ incluyendo procesos huérfanos.

### Paper v21 — §8.13 hallazgos reales DAY 147
- **Status:** ✅ CERRADO DAY 147 — **Commit:** `a7bfa0bb`
- **Contenido:** búsqueda infructuosa ruleset ET Open 2011 (Wayback Machine, GitHub ET, SecurityOnion/ossim). Hallazgo HTTP C2: Neris escenario 42 usa HTTP C2, no solo IRC — paradigma gap más profundo que signature aging solo. Añade @article{asad2023perspective} (Springer 2023, DOI 10.1007/s10207-023-00794-9).
- **Script:** `upgrade_to_v21.py` — 7/7 verificaciones verdes.

### Experimento comparativo Zeek 8.1.2 vs aRGus NDR — DAY 147 (tres paradigmas)
- **Status:** ✅ COMPLETADO DAY 147 — **Commit:** `[pending git commit tras branch merge]`
- **Infraestructura:** `experiments/zeek-comparative/` — Vagrantfile (debian/bookworm64, 8192MB, 6vCPU, VirtIO), `parse_results_zeek_v2.py`, `makefile_targets.mk`.
- **Protocolo:** Zeek 8.1.2 en modo offline (`zeek -r neris.pcap local`), scripts por defecto, sin tuning. Tres runs (10/50/100 Mbps) — resultado determinístico idéntico en los tres.

**Resultados (CTU-13 Neris, ground truth: 147.32.84.165, 646 flows maliciosos):**

| Sistema | Paradigma | TP | FP | F1 | Precision | Recall |
|---------|-----------|-----|-----|-----|-----------|--------|
| Suricata 6.0.10 | Signature (ET Open) | 0 | 0 | 0.000 | — | 0.000 |
| Zeek 8.1.2 (default) | Scripted behavioral | 14 | 0 | 0.042 | **1.000** | 0.022 |
| **aRGus NDR** | ML behavioral | **646** | 2 | **0.9985** | 0.997 | **1.000** |

**Hallazgos científicos clave:**
- Zeek Precision=1.000: cada alerta identifica correctamente el host malicioso. Los 6 "FP" originales son CaptureLoss (infraestructura, excluidos de métricas corregidas).
- `weird.log` (182 eventos en host malicioso): `irc_invalid_command:30`, `bad_HTTP_request:31`, `empty_http_request:31`, `unknown_dce_rpc_auth_type:33`, `premature_connection_reuse:28`. Zeek observa todo el perfil behavioral sin alertar.
- `irc_invalid_command:30` confirma IRC presente en la captura — refuta parcialmente el README que describe solo HTTP C2.
- Distinción central: Zeek es una plataforma de observabilidad de red (measurement layer). aRGus es un clasificador behavioral (classification layer). No son competidores — son capas distintas.

**Paper v22:** §8.14 "Three Paradigms" — dos tablas (detección + visibilidad Zeek), análisis espectro paradigmas, §13 reproducibilidad Zeek.
**Scripts creados:** `setup_zeek_experiment.py`, `fix_zeek_makefile.py`, `fix_zeek_offline.py`, `parse_results_zeek_v2.py`, `upgrade_to_v22.py`.

## ✅ CERRADO DAY 146

### DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `tools/provision.sh` línea 1250: instala `/etc/tmpfiles.d/argus.conf` con `d /run/argus/irp 0700 argus argus -`. `/run/argus/irp` se recrea automáticamente en cada reboot via `systemd-tmpfiles`. Sin intervención manual.
- **Test de cierre:** reboot VM → `/run/argus/irp/` existe con permisos 0700 → dry-run IRP PASSED.

### DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `firewall-acl-agent/src/core/ipset_wrapper.cpp` líneas 322, 391: `/tmp/ipset_restore.tmp` → `/run/argus/irp/ipset_restore.tmp` y `/tmp/ipset_delete.tmp` → `/run/argus/irp/ipset_delete.tmp`. Firewall recompilado OK (debug).
- **Test de cierre:** `grep -r '/tmp' firewall-acl-agent/src/` = 0 resultados (excluido código comentado).

### DEBT-BOOTSTRAP-SNIFFER-VERIFY-001 — sleep insuficiente en sniffer-start
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `Makefile` líneas 610, 623: `sleep 2` → `sleep 4` en `sniffer-start` y `sniffer-libpcap-start`. Línea 267: verificación real del sniffer antes del banner — exit 1 si STOPPED, no falso positivo.
- **Test de cierre:** EMECAS completo — pipeline-status muestra sniffer RUNNING tras bootstrap.

### DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `README.md` líneas 269-276: párrafo blockquote explicativo del protocolo EMECAS — qué hace, por qué existe, qué significa FAILED=0, comportamiento del sniffer (4s estabilización sesión tmux).
- **Test de cierre:** nuevo desarrollador puede seguir el protocolo sin ambigüedad.

### Experimento comparativo Suricata vs aRGus NDR — DAY 146
- **Status:** ✅ COMPLETADO DAY 146
- **Branch:** `main` → `v0.7.1-day146`
- **Commits:** `df19f1f8` (Vagrantfile) · `19295a7e` (run_experiment.sh) · `ff83b402` (up-argus/up-suricata) · `8e503815` (Makefile targets + parse_results.py) · `e1efbfbc` (resultado)

**Diseño experimental:**
- Suricata 6.0.10 + ET Open (50,010 reglas, Mayo 2026)
- VM idéntica a aRGus: `debian/bookworm64 12.20240905.1`, 8,192 MB, 6 vCPU, VirtIO NIC, VirtualBox 7.2
- Dataset: CTU-13 Neris (320,524 paquetes, 19,135 flows, ground truth: 147.32.84.165, 646 flows maliciosos)
- Topología: VM client → tcpreplay → VM suricata (eth2, promiscuo) — idéntica a aRGus DAY 145
- Velocidades: 10, 50, 100 Mbps

| Sistema | Reglas/Modelo | TP | FP | F1 | Recall |
|---------|--------------|-----|-----|-----|--------|
| **aRGus NDR** | ML behavioral (sintético) | 646 | 2 | **0.9985** | **1.0000** |
| Suricata 6.0.10 | 50,010 ET Open (Mayo 2026) | 0 | 0 | 0.0000 | 0.0000 |

| Target | Mbps real Suricata | Alertas | exit |
|--------|-------------------|---------|------|
| 10 Mbps | 9.99 | 0 | 0 |
| 50 Mbps | 19.43 | 0 | 0 |
| 100 Mbps | 18.82 | 0 | 0 |

**Interpretación científica:**
No es un fallo de Suricata. El motor procesó el tráfico correctamente (`decoder.pkts` confirmado en stats.log). Las reglas ET Open evolucionan — las firmas de 2011 (botnet Neris, IRC C2, SMB lateral movement) han sido retiradas del ruleset actual. aRGus detecta el patrón comportamental independientemente de la antigüedad de la amenaza porque fue entrenado con datos sintéticos que modelan comportamiento, no firmas específicas.

**Significado científico:**
Corrobora la tesis de Sommer & Paxson (2010): la detección basada en firmas requiere conocimiento previo del atacante; la detección comportamental no. Primera comparativa directa publicada entre un NDR ML embebido y un IDS de firmas en producción sobre el mismo dataset, hardware y topología.

**Pendiente:** repetir con ruleset ET Open histórico (~2011) para separar "firma nunca existió" de "firma retirada".

**Makefile targets nuevos:**
- `make up-argus` / `make up-suricata` / `make halt-argus` / `make halt-suricata`
- `make experiment-suricata-up/down/run/results/status`

**Paper:** Draft v20 — nueva §8.13 "Direct Experimental Comparison: aRGus NDR vs Suricata 6.0.10 on CTU-13 Neris". Tabla 6 (tab:comparison) actualizada con datos empíricos Suricata F1=0.000.

## ✅ CERRADO DAY 144
## ✅ COMPLETADO DAY 145

### ADR-029 Variant A vs B — Primer experimento comparativo x86 (DAY 145)
- **Status:** ✅ COMPLETADO DAY 145
- **Branch:** `feature/variant-b-libpcap @ e52870d5` → merge → `v0.7.0-variant-b`
- **Experimento:** CTU-13 Neris (320,524 paquetes, 19,135 flows) via `tcpreplay` a 10/50/100 Mbps. Pipeline completo 6/6. Solo el sniffer binario cambia entre runs.
- **Invariante:** mutex `CHECK_SNIFFER_MUTEX` — Variant A y B nunca simultáneas.

| Variante | Target | Mbps real | PPS | Duración (s) | exit |
|----------|--------|-----------|-----|--------------|------|
| A — eBPF | 10 Mbps | 8.86 | 8,040 | 39.86 | 0 |
| A — eBPF | 50 Mbps | 9.78 | 8,867 | 36.14 | 0 |
| A — eBPF | 100 Mbps | 10.12 | 9,178 | 34.92 | 0 |
| B — libpcap | 10 Mbps | 9.99 | 9,064 | 35.36 | 0 |
| B — libpcap | 50 Mbps | 19.43 | 17,614 | 18.19 | 0 |
| B — libpcap | 100 Mbps | 18.82 | 17,066 | 18.78 | 0 |

- **Hallazgo clave:** Variant B (libpcap) ~2× throughput de Variant A (eBPF) a 50/100 Mbps en VirtualBox virtio. Inversión del orden esperado — artefacto de emulación, no del pipeline. Causa: virtio no expone driver XDP nativo → eBPF cae a modo SKB genérico con overhead por paquete que libpcap no tiene. En hardware real con NIC XDP nativa (Intel ixgbe, Mellanox mlx5), se espera la inversión: eBPF > libpcap. **Este dato es la motivación empírica de la adquisición de hardware FEDER.**
- **Failed packets (2,630 en todos los runs):** Artefacto fijo del pcap CTU-13 Neris. Son frames jumbo del pcap original que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). Evidencias: (1) conteo idéntico en los 6 runs — si fuera saturación variaría; (2) los 320,524 successful son idénticos — propiedad del fichero, no de la red; (3) el rechazo ocurre en el cliente antes de llegar al defender — el sniffer nunca ve esos frames. **No son errores del pipeline.**
- **Equivalencia funcional A/B confirmada:** ambas variantes procesan el corpus Neris sin errores de pipeline.

### Bootstrap múltiple — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- `bootstrap` → alias de `bootstrap-x86-ebpf` (Variant A, referencia)
- `bootstrap-x86-ebpf` — pipeline completo con sniffer eBPF/XDP
- `bootstrap-x86-libpcap` — pipeline completo con sniffer libpcap (compila también `sniffer-libpcap`)
- `pipeline-start-x86-libpcap` — variante de pipeline-start que arranca Variant B

### Relay targets mejorados — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- `test-replay-neris-x86-ebpf` y `test-replay-neris-x86-libpcap` muestran resumen inline tras cada velocidad (grep de líneas relevantes del log). El banner final lista las 4 rutas de log generadas. Nota sobre MTU integrada en el output — no confunde al usuario.
- `pipeline-status` distingue: `RUNNING [Variant A — eBPF]`, `RUNNING [Variant B — libpcap]`, `INVARIANT VIOLATION` (ambos simultáneos), `STOPPED`.

### Paper Draft v19 — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- Nueva subsección §6 (ADR-029 Variant A vs B, tabla comparativa, interpretación virtio/SKB, valor científico).
- §10.9 actualizado con el artefacto virtio/XDP como limitación documentada.
- §11.17 extendido con el dato empírico como motivación FEDER hardware.
- §12 Reproducibility — comandos exactos para reproducir el experimento ADR-029.
- Abstract actualizado con párrafo nuevo sobre el hallazgo ADR-029.
- Acknowledgments: "132 days" → "145 days".



### DEBT-IRP-SIGCHLD-001 — Zombie reaper SA_NOCLDWAIT
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `a44b7ab3`
- **Fix:** `sigaction(SIGCHLD, SA_NOCLDWAIT)` en `setup_signal_handlers()`. El kernel recoge hijos automáticamente sin handler ni polling. Una línea.
- **Test de cierre:** `SigchldTest.NoZombiesAfterNForks` — 20 forks con `/bin/true`, 500ms, cero `defunct` en `/proc`. PASSED.

### DEBT-IRP-AUTOISO-FALSE-001 — auto_isolate false por defecto
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `a44b7ab3`
- **Fix:** `isolate.json` es la ÚNICA fuente de verdad. Campo `auto_isolate` obligatorio — si falta, `parse_irp()` lanza `runtime_error` con mensaje claro. Sin fallback silencioso. `provision.sh` falla con `exit 1` si el fichero fuente no existe. `parse_irp()` movida a `public` para testabilidad directa.
- **Consejo 8/8 unánime:** un FP sobre ventilador mecánico es un evento clínico, no un bug.
- **Tests de cierre:** `DefaultStructIsFalse`, `FileMissingThrows`, `MissingFieldThrows`, `ExplicitFalseIsRespected`, `ExplicitTrueIsRespected` — 5/5 PASSED.

### DEBT-IRP-BACKUP-DIR-001 — /tmp peligroso para artefactos IRP
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `646713e7`
- **Fix:** artefactos nftables migrados a `/run/argus/irp/` (tmpfs, 0700 argus:argus). AppArmor actualizado: eliminadas reglas `/tmp/argus-*.nft`, añadidas `/run/argus/irp/**` y `/var/lib/argus/irp/**`. `provision.sh` crea ambos directorios. `isolate.hpp` default actualizado.
- **Deudas derivadas:** `DEBT-IRP-TMPFILES-001` (tmpfiles.d reboot) + `DEBT-IRP-IPSET-TMP-001` (ipset_wrapper.cpp).
- **Test de cierre:** dry-run → `backup=/run/argus/irp/argus-backup-*.nft`. `ls /tmp/argus-*` vacío. PASSED.

### DEBT-COMPILER-WARNINGS-CLEANUP-001 — ODR violations bajo LTO (parcial)
- **Status:** ✅ PARCIALMENTE CERRADO DAY 144 — **Commits:** `e52870d5`
- **Gate:** `make PROFILE=production all` detectó 4 categorías de ODR violations reales bajo `-flto -Werror`.
- **Fix 1:** anonymous namespace en `internal_trees_inline.hpp` + `traffic_trees_inline.hpp` — `tree_0[]`..`tree_99[]` con tipos distintos visibles cross-módulo.
- **Fix 2:** `contract_validator.h` incluía protobuf stale (`src/protobuf/`, noviembre 2025). Path corregido + `src/protobuf/` eliminado (40k líneas de código generado fuera del repo).
- **Fix 3:** `-UNDEBUG` en targets de test de rag-ingester, rag y etcd-server — `assert()` siempre activo en tests independientemente del PROFILE.
- **Nuevo invariante:** `make PROFILE=production all` — gate ODR pre-merge obligatorio. Confirmado: `ALL COMPONENTS BUILT [production]`.
- **Test de cierre:** `make PROFILE=production all` PASSED — 0 ODR violations.

### DEBT-EMECAS-VERIFICATION-001 — P2 post-merge
- **Status:** ✅ REGISTRADA — P2 post-merge
- **Descripción:** El protocolo EMECAS en sí es correcto. El checklist de verificación post-EMECAS debe documentar explícitamente que el banner `ALL TESTS COMPLETE` + `FAILED=0` son el veredicto autoritativo. Errores intermedios de bootstrap son transientes esperados por diseño. Añadir párrafo en README para desarrolladores.
- **Estimación:** 30 minutos post-merge.

## ✅ CERRADO DAY 143

### DEBT-IRP-NFTABLES-001 — sesión 3/3 (integración firewall-acl-agent + AppArmor)
- **Status:** ✅ CERRADO DAY 143 — **Commits:** `c6e3f4ab` `888bfcbd` `f1ab0c79` `e08f394d` `f00b1809` `7716423b`
- **Bloque 1:** `isolate.json` + `IsolateConfig` — campos `auto_isolate`, `threat_score_threshold`, `auto_isolate_event_types`, `isolate_interface`. Test `test_isolate_config` 9/9.
- **Bloque 2:** `firewall-acl-agent` — `IrpConfig`, `should_auto_isolate()` (función pura testeable), `check_auto_isolate()` con `fork()+execv()`. Mapeo `DetectionType→string`. Bug IEEE 754 detectado por tests y corregido con tolerancia `1e-6`.
- **Bloque 3:** AppArmor profile `argus.argus-network-isolate` — sintaxis validada, 7/7 perfiles enforce en hardened VM. `setup-apparmor.sh` actualizado.
- **Bloque 4:** `test_auto_isolate` 12/12 PASSED (10 unitarios + 2 integración fork/exec).
- **Regresiones EMECAS resueltas:** DEBT-BOOTSTRAP-ORDER-001 (check-build-artifacts separado) + firma `PcapBackend::open()` en 5 test files.
- **Invariante:** EMECAS verde. `make test-all` ALL TESTS COMPLETE.


---

## ✅ CERRADO DAY 142

### Regresión test_config_parser — safe_path path no compliant
- **Status:** ✅ CERRADO DAY 142 — **Commit:** `4bbc98ee`
- **Fix:** `test_config_parser` pasaba `/vagrant/rag-ingester/config/rag-ingester.json` a `ConfigParser::load()`. ADR-037 (safe_path) bloqueaba correctamente el path de dev. Fix: usar path de producción `/etc/ml-defender/rag-ingester/rag-ingester.json`. `test_config_parser_traversal` (ataques path traversal) ya pasaba — no tocado.
- **Invariante:** EMECAS verde — 8/8 tests rag-ingester PASSED.

### DEBT-IRP-NFTABLES-001 — sesiones 1/3 y 2/3
- **Status:** 🟡 60% — sesiones 1 y 2 cerradas — **Commits:** `6480e234` + `e8928612`
- **Sesión 1:** Binario `argus-network-isolate` C++20 creado en `tools/argus-network-isolate/`. Pasos 1-3: snapshot selectivo (solo tabla `argus_isolate`, excluye tablas iptables-managed con `xt match` incompatibles), generate_rules con whitelist IP/port configurable, validate_dry_run (`nft -c`). Config: `tools/argus-network-isolate/config/isolate.json`. Forense JSONL en `/var/log/argus/network-isolate-forensic.jsonl`.
- **Sesión 2:** Pasos 4-6: apply atómico (`nft -f`), timer `systemd-run --on-active=300s` idempotente (stop+reset-failed antes de crear), rollback robusto (elimina tabla `argus_isolate`, no toca tablas del sistema). Ciclo completo verificado en dev VM (eth2): NORMAL→ISOLATED→STATUS→ROLLBACK→NORMAL. SSH sobrevivió en todo momento (eth0 + whitelist).
- **Pendiente sesión 3:** integración `firewall-acl-agent` + AppArmor profile.
- **Makefile:** `argus-network-isolate-build`, `argus-network-isolate-install`, `argus-network-isolate-test`, `argus-network-isolate-clean`.

### EMECAS reproducibility — argus-network-isolate en pipeline-build + provision
- **Status:** ✅ CERRADO DAY 142 — **Commit:** `e3f5f9c4`
- **Fix:** Vagrantfile: `nftables` declarado explícitamente. `provision.sh`: instala `isolate.json` en `/etc/ml-defender/firewall-acl-agent/` + crea `/var/log/argus/`. Makefile: `argus-network-isolate-build` + `argus-network-isolate-install` en `pipeline-build`. `check-system-deps` verifica nftables + binario instalado.

### DEBT-VARIANT-B-BUFFER-SIZE-001 — pcap_create()+pcap_set_buffer_size()
- **Status:** ✅ CERRADO DAY 142 — **Commit:** `7c4dba58`
- **Fix:** `PcapBackend::open()` refactorizado de `pcap_open_live()` a `pcap_create()+pcap_set_buffer_size()+pcap_activate()`. `buffer_size_mb` del JSON ahora se aplica realmente. `CaptureBackend` interfaz actualizada con el parámetro. Crítico en ARM64/RPi donde el kernel default es 2MB vs 8MB configurado.
- **Test de cierre:** `[pcap] Variant B opened on eth1 buffer=8MB` verificado. `make test-all` sin regresión.

### DEBT-VARIANT-B-MUTEX-001 — exclusión mutua Variant A/B (Nivel 1)
- **Status:** ✅ CERRADO DAY 142 Nivel 1 — **Commit:** `9458a90d`
- **Fix:** `scripts/check-sniffer-mutex.sh` via sesiones tmux. Detecta si hay variant activa antes de arrancar otra. Variant A session: `sniffer`. Variant B session: `sniffer-libpcap`. Conflicto detectado → detiene variant activa + exit 1. Makefile: `sniffer-start` y `sniffer-libpcap-start` llaman al mutex. Nuevo target `sniffer-libpcap-start`.
- **NOTA:** Nivel 1 provisional. Ver `DEBT-MUTEX-ROBUST-001` post-FEDER.
- **Test de cierre:** Variant B activa + intento Variant A → violación detectada, Variant B detenida, exit 1. ✅

---

## ✅ CERRADO DAY 141

### Bug Makefile — dependencia seed-client-build implícita
- **Status:** ✅ CERRADO DAY 141 — **Commit:** `63a37d9d`

### DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 — Contrato lifetime PcapCallbackData
- **Status:** ✅ CERRADO DAY 141 — **Commit:** `63a37d9d`

### DEBT-VARIANT-B-CONFIG-001 — JSON propio sniffer-libpcap + config-driven main
- **Status:** ✅ CERRADO DAY 141
- **Test de cierre:** `make sniffer-libpcap` — 0 warnings. `make test-all` — 9/9 PASSED. ✅

---

## ✅ CERRADO DAY 138

### DEBT-CAPTURE-BACKEND-ISP-001 — CaptureBackend interfaz mínima (ISP)
- **Status:** ✅ CERRADO DAY 138 — **Commit:** `1a7f723a`

### DEBT-VARIANT-B-PCAP-IMPL-001 — Pipeline completo libpcap
- **Status:** ✅ CERRADO DAY 138 — **Commits:** `22df0099` + `da1badf7`
- **Suite 8 tests — 8/8 PASSED en make test-all.**

---

## ✅ CERRADO DAY 134

### Pipeline E2E en hardened VM — check-prod-all PASSED
- **Status:** ✅ CERRADO DAY 134 — **Commits:** `f256e6f0` + `2e9a5b39`

### DEBT-KERNEL-COMPAT-001 · DEBT-PAPER-FUZZING-METRICS-001 · ADR-040 + ADR-041
- **Status:** ✅ CERRADO DAY 134

---

## ✅ CERRADO DAY 133

### Paper Draft v18 · DEBT-PROD-APPARMOR-COMPILER-BLOCK-001 · DEBT-PROD-FALCO-EXOTIC-PATHS-001 · Linux Capabilities
- **Status:** ✅ CERRADO DAY 133

---

## ✅ CERRADO DAY 130–132

DAY 132: DEBT-PROD-COMPAT-BASELINE-001 · README Prerequisites
DAY 130: DEBT-SYSTEMD-AUTOINSTALL-001 · DEBT-SAFE-EXEC-NULLBYTE-001 · DEBT-FUZZING-LIBFUZZER-001 · REGLA EMECAS
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`

---

## ✅ CERRADO DAY 124–129

DAY 124: ADR-037 safe_path → v0.5.1-hardened
DAY 125-126: 8 deudas cerradas · lstat() pre-resolution · prefix fijo
DAY 127: resolve_config() · taxonomía safe_path
DAY 128: Snyk 18 findings · 5 property tests
DAY 129: CWE-78 CERRADO · EtcdClientHmac 9/9

---

## 🔴 DEUDAS ABIERTAS — Seguridad y arquitectura

### DEBT-IRP-NFTABLES-001 — sesión 3/3 pendiente
**Severidad:** 🔴 Alta — P0 pre-FEDER
**Estado:** 🟡 60% — sesiones 1/3 y 2/3 CERRADAS — DAY 142
**Componente:** `firewall-acl-agent` + `tools/argus-network-isolate/` + AppArmor

Pasos 1-6 implementados y verificados en dev VM. Pendiente sesión 3:
1. Añadir a `isolate.json`: `auto_isolate` (default true), `threat_score_threshold` (0.95), `auto_isolate_event_types` (ransomware, lateral_movement, c2_beacon).
2. En `firewall-acl-agent`: detectar umbral + tipo superado → `fork()+execv()` a `argus-network-isolate isolate --interface <iface>`.
3. Test integración: evento sintético score >= 0.95 + tipo correcto → aislamiento automático.
4. AppArmor profile `enforce` para `argus-network-isolate` (combinar perfiles Gemini + Kimi DAY 142).
5. Instalar binario en `provision.sh` para hardened VM.

**Decisiones de diseño aprobadas (Consejo 8/8 + founder DAY 142):**
- `auto_isolate: true` por defecto — instalar y funcionar.
- Criterio disparo: `threat_score >= 0.95 AND event_type IN (ransomware, lateral_movement, c2_beacon)` — señal multi-componente, nunca umbral único.
- `fork()+execv()` — el firewall-acl-agent nunca muere.
- AppArmor `enforce` desde el primer deploy.
- Rollback actual (eliminar solo `argus_isolate`) suficiente para FEDER.

**ADR relacionado:** ADR-042 IRP
**Estimación:** 1 sesión (sesión 3/3)

---

### DEBT-IRP-SIGCHLD-001 — Zombie reaper SA_NOCLDWAIT
**Severidad:** ✅ CERRADA DAY 144
**Estado:** CERRADO — ver sección DAY 144
**Componente:** `firewall-acl-agent/src/main.cpp`

`fork()+execv()` sin `wait()` genera zombies acumulados en ataques persistentes.
Fix: `sigaction(SIGCHLD, SA_NOCLDWAIT)` al inicializar `firewall-acl-agent` —
el kernel recoge los hijos automáticamente sin handler ni polling.
Es el mecanismo más cercano al kernel. Una línea. Sin threads adicionales.

**Consejo 8/8 DAY 143:** SA_NOCLDWAIT (Qwen) es la solución más kernel-centric.
**Test de cierre:** N disparos IRP en loop → `ps aux | grep -c defunct` = 0.
**Estimación:** 30 minutos pre-merge.

---

### DEBT-IRP-AUTOISO-FALSE-001 — auto_isolate false por defecto
**Severidad:** ✅ CERRADA DAY 144
**Estado:** CERRADO — ver sección DAY 144
**Componente:** `tools/argus-network-isolate/config/isolate.json` + documentación

**Consejo 8/8 DAY 143 — UNÁNIME:** `auto_isolate: false` por defecto en producción
hospitalaria. Un ventilador mecánico o bomba de infusión no puede quedar aislado
por señal única sin confirmación humana explícita. "Instalar y funcionar" es válido
para entornos SOHO — inaceptable para hospitales sin onboarding explícito.

Cambio: `isolate.json` default → `false`. Añadir WARNING prominente al arrancar
`firewall-acl-agent` con IRP desactivado. Activar requiere acto explícito y consciente
del administrador tras configurar `whitelist_ips` con activos críticos.

La regla DAY 142 ("auto_isolate: true por defecto") queda **REEMPLAZADA** por esta.

**Test de cierre:** `vagrant destroy && vagrant up && make bootstrap` → IRP arranca
con `auto_isolate: false` y loguea WARNING visible.
**Estimación:** 1 hora pre-merge.

---

### DEBT-IRP-BACKUP-DIR-001 — /tmp peligroso para artefactos IRP
**Severidad:** ✅ CERRADA DAY 144
**Estado:** CERRADO — ver sección DAY 144
**Componente:** `tools/argus-network-isolate/isolate.cpp` + AppArmor profile

**Consejo 8/8 DAY 143 — UNÁNIME:** `/tmp/argus-*.nft` es un vector.
Glob en `/tmp` permite interferencia por race condition o symlink attack.

Fix:
- Artefactos transaccionales volátiles → `/run/argus/irp/` (tmpfs, desaparece en reboot)
- Estado persistente → `/var/lib/argus/irp/`
- Permisos: `0700 argus:argus`
- AppArmor: eliminar reglas `/tmp/**`, añadir `/run/argus/irp/**` y `/var/lib/argus/irp/**`
- Falco: vigilar ambas rutas — escritura por proceso no autorizado = alerta

**Test de cierre:** AppArmor en enforce + dry-run IRP → artefactos en `/run/argus/irp/`.
`ls /tmp/argus-*` vacío.
**Estimación:** 2 horas pre-merge.

---

### DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/
**Severidad:** 🟡 P1 post-merge
**Estado:** ABIERTO — DAY 144
**Componente:** `tools/provision.sh` + configuración systemd

`/run/argus/irp/` es tmpfs — desaparece en cada reboot. En producción, el directorio debe recrearse automáticamente al arrancar. Fix: fichero `tmpfiles.d` en `/etc/tmpfiles.d/argus-irp.conf`:d /run/argus/irp 0700 argus argus -O en `provision.sh`: `systemd-tmpfiles --create` tras instalación.

**Test de cierre:** reboot → `/run/argus/irp/` existe con permisos correctos → dry-run IRP PASSED.
**Estimación:** 30 minutos post-merge.

---

### DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
**Severidad:** 🟡 P1 post-merge
**Estado:** ABIERTO — DAY 144
**Componente:** `firewall-acl-agent/src/core/ipset_wrapper.cpp`

`ipset_wrapper.cpp` usa `/tmp/ipset_restore.tmp` y `/tmp/ipset_delete.tmp`. Scope distinto al IRP (ipset, no nftables) pero mismo problema de seguridad. Migrar a `/run/argus/` con permisos apropiados.

**Test de cierre:** `grep -r '/tmp' firewall-acl-agent/src/` = 0 resultados (excluir .old/.backup).
**Estimación:** 1 hora post-merge.

---

### DEBT-IRP-FLOAT-TYPES-001 — Unificar tipos score float/double
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 143
**Componente:** `firewall-acl-agent/include/firewall/config_loader.hpp` + `batch_processor.cpp`

El bug IEEE 754 detectado por los tests DAY 143: `static_cast<double>(0.95f)` = `0.9499...`
Corregido con tolerancia `1e-6` — parche funcional pero no la solución de raíz.

El problema real: `IsolateConfig::threat_score_threshold` es `double` pero
`Detection::confidence` es `float`. Mezcla de tipos en lógica de decisión crítica.

Preguntas a responder antes del fix:
1. ¿Qué tipo produce exactamente el ml-detector? ¿float 32-bit o double 64-bit?
2. ¿Qué precisión tiene el score en el pipeline ZMQ → protobuf → BatchProcessor?
3. ¿Qué tipo es matemáticamente correcto para el score de un clasificador ML?

**Consejo DAY 143:** Dividido — Claude/Gemini/Grok/DeepSeek prefieren `float` consistente;
Mistral/Qwen prefieren `double` + tolerancia. ChatGPT propone enteros escalados (uint32_t)
para sistemas críticos. Resolver con análisis del pipeline completo antes de FEDER
porque los tests MITRE pueden revelar comportamientos en distribuciones fuera de CIC-IDS-2017.

**Test de cierre:** stress test con CTU-13 + pcap relay + MITRE → 0 disparos IRP
inesperados por error de precisión numérica.
**Estimación:** 1 sesión pre-FEDER.

---

### DEBT-IRP-PROB-CONJUNTA-001 — Función probabilidad conjunta multi-señal
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 143
**Componente:** `firewall-acl-agent/src/core/` — nuevo módulo IrpDecisionEngine

**Consejo 8/8 DAY 143:** Dos señales AND no son suficientes para producción hospitalaria.
Arquitectura acordada: función de decisión que combina TODAS las señales disponibles
con sus pesos, produce una probabilidad conjunta, y la decisión queda completamente
auditada — se sabe exactamente qué señales contribuyeron y con qué peso.

Señales candidatas (no todas obligatorias):
- score >= threshold (necesaria)
- event_type IN lista (necesaria)
- src_ip NOT IN whitelist_assets_criticos (gate de seguridad)
- N eventos en ventana T segundos (correlación temporal — Qwen)
- confirmación segundo sensor ±5s (Falco, Suricata — Mistral)
- segmento de red del activo (Gemini — no escala globalmente)

La función de decisión debe ser: explicable, auditable, publicable en paper.
La probabilidad conjunta de todas las señales disponibles elimina el umbral binario.

**No implementar Gemini's topología por quirófano** — inviable mantener catálogo
de todos los hospitales del mundo.

**Registrado como:** IDEA-IRP-DECISION-MATRIX-001 (referencia cruzada DEBT-IRP-MULTI-SIGNAL-001)
**Test de cierre:** decisión IRP con ≥3 señales → log JSON con contribución de cada señal.
**Estimación:** 3 sesiones post-FEDER.

---

### DEBT-PROTO-DETECTION-TYPES-001 — Ampliar enum DetectionType
**Severidad:** 🟢 Baja — post-fase-MITRE/CTF
**Estado:** ABIERTO — DAY 143
**Componente:** `protobuf/network_security.proto`

`DetectionType` solo modela 4 tipos: DDOS, RANSOMWARE, SUSPICIOUS_TRAFFIC, INTERNAL_THREAT.
El mapeo actual en `should_auto_isolate()` usa aproximaciones:
`DETECTION_INTERNAL_THREAT → "lateral_movement"` y
`DETECTION_SUSPICIOUS_TRAFFIC → "c2_beacon"`.

Ampliar cuando el pipeline enfrente MITRE ATT&CK y CTFs reales y se observen
tipos de ataque no modelados. No antes — sin datos no hay diseño.

Opción B (ampliar proto) descartada conscientemente DAY 143 para no romper
compatibilidad con v0.6.0-hardened-variant-a.

**Test de cierre:** pipeline contra MITRE ATT&CK → 0 eventos "tipo no mapeado" en logs IRP.
**Estimación:** 1 sesión post-MITRE.


---

### DEBT-PARQUET-SCHEMA-001 — Schema Parquet ml-detector y firewall-acl-agent
**Severidad:** 🔴 P0 bloqueante
**Estado:** ABIERTO — DAY 147
**Componente:** `ml-detector` + `firewall-acl-agent` + pipeline de ingesta Neo4j

Schema candidato definido en ADR-0043 v4 D4b. Debe validarse contra los CSVs reales producidos por el pipeline en entorno Vagrant. Confirmar granularidad de eventos (por flow vs. por paquete) y política de registro (todos los eventos vs. solo alertas/denies). Sin schema validado no existe contrato de interfaz y el pipeline de ingesta Neo4j no puede implementarse.

**ADR relacionado:** ADR-0043 D4b
**Test de cierre:** schema Parquet candidato validado contra CSVs reales. Tipos Arrow confirmados. Volumen estimado por nodo por mes documentado.
**Estimación:** 1 sesión en Vagrant

---

### DEBT-VAULT-FEDERATION-001 — Offboarding de instalaciones GDPR
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + Vault central + Neo4j

Procedimiento de offboarding cuando un cliente abandona la red aRGus: destrucción certificada del Vault local, política de retención de datos históricos pseudonimizados en Neo4j. La destrucción del Vault local convierte los datos en Neo4j en efectivamente irrecuperables (anonimización efectiva bajo GDPR). Requiere validación jurídica.

**ADR relacionado:** ADR-0043 D7, DEBT-LEGAL-DATA-RETENTION-001
**Test de cierre:** runbook de offboarding ejecutado en entorno de prueba. Confirmación de irrecuperabilidad de datos.
**Estimación:** 2 sesiones + validación jurídica

---

### DEBT-LEGAL-DATA-RETENTION-001 — Dictamen jurídico retención datos post-cliente
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Interlocutor:** Dr. Andrés Caro Lindo (UEx/INCIBE)

Pregunta específica para el jurista: ¿cuándo exactamente los datos pseudonimizados con HMAC-SHA256 dejan de ser datos personales bajo GDPR si la clave de reversión (K_pseudo) existe pero está técnicamente aislada en un Vault destruido certificadamente? La respuesta determina la política de retención histórica post-offboarding.

**ADR relacionado:** ADR-0043 D2, D7, D8
**Test de cierre:** dictamen jurídico documentado. Política de retención registrada en ADR-0043 o ADR complementario.
**Estimación:** gestión externa — no depende de implementación técnica

---

### DEBT-KPSEUDO-ROTATION-MIGRATION-001 — Migración Neo4j tras rotación K_pseudo
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + Neo4j + pipeline de ingesta

La rotación de K_pseudo cambia todos los anon_id. El procedimiento de migración requiere: coordinación con drenado de batches en vuelo, actualización de relaciones :PREVIOUS_IDENTITY en Neo4j, atomicidad durante la migración, auditoría firmada del proceso. Las queries de evolución histórica a través de múltiples rotaciones requieren recursividad Cypher con límite de profundidad explícito.

**ADR relacionado:** ADR-0043 D3, ADR-004
**Test de cierre:** rotación K_pseudo en entorno de prueba con datos históricos. Continuidad de anon_id verificada via :PREVIOUS_IDENTITY. 0 entidades duplicadas.
**Estimación:** 2 sesiones

---

### DEBT-GDPR-ERASURE-001 — Flujo derecho al olvido GDPR Art. 17
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** instalación local + servidor central Neo4j + canal Ed25519

Implementar el flujo completo: (1) instalación local calcula anon_id = HMAC(K_pseudo, identidad_real), (2) borra registros en SQLite, (3) envía comando firmado Ed25519 al servidor central, (4) servidor ejecuta DELETE en Neo4j, (5) registra auditoría inmutable, (6) instalación recibe confirmación y certifica cumplimiento. Limitación conocida: si el mismo dispositivo generó múltiples anon_id por cambio de identidad primaria, el borrado de uno no alcanza automáticamente a los demás.

**ADR relacionado:** ADR-0043 D8
**Test de cierre:** solicitud de borrado E2E en entorno de prueba. Verificación de ausencia del anon_id en Neo4j. Auditoría firmada verificable.
**Estimación:** 2 sesiones + validación jurídica

---

### DEBT-KPSEUDO-HKDF-HIERARCHY-001 — Jerarquía HKDF para K_pseudo
**Severidad:** ⏳ P3 post-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + función de pseudonimización en nodo

Derivar subclaves especializadas desde K_root usando HKDF (NIST SP 800-108): K_pseudo_host, K_pseudo_flow, K_pseudo_model. Reduce el radio de daño ante compromiso de subclave individual y permite rotación selectiva sin romper coherencia en otras dimensiones. Relevante especialmente para instalaciones de alto valor (hospitales universitarios, municipios grandes). Alineado con ADR-004 (cooldown y máximo 2 claves concurrentes).

**ADR relacionado:** ADR-0043 D3, ADR-004
**Test de cierre:** derivación HKDF en Vault local. Verificación de independencia entre subclaves. Rotación de K_pseudo_flow sin afectar K_pseudo_host.
**Estimación:** 1 sesión post-FEDER

---



### DEBT-PARQUET-TIMESTAMP-NS-001 — firewall-acl-agent produce ms
**Severidad:** 🟡 P2
**Estado:** ABIERTO — DAY 149
**Componente:** `firewall-acl-agent`
**Descripción:** firewall-acl-agent escribe timestamps en milisegundos. ml-detector escribe nanosegundos. Workaround: writer Parquet multiplica ×1_000_000. Fix correcto: modificar firewall-acl-agent para emitir ns directamente. Revisar rag-security si en algún momento consume Parquet directamente.
**Test de cierre:** `firewall_blocks.csv` timestamp en ns. Roundtrip sin conversión.
**Estimación:** 1h

### DEBT-VAULT-ENTROPY-MIXING-001 — Mezcla entropy externa post-FEDER
**Severidad:** 🟢 P2 post-FEDER
**Estado:** ABIERTO — DAY 149 (disidencia Grok/Gemini registrada)
**Descripción:** Para prod con hardware HSM/TPM: mezclar HKDF(Vault_output, getrandom()/RDRAND/TPM) antes de almacenar seed. Para FEDER: `vault write sys/tools/random` es suficiente (NIST SP 800-90A).
**Test de cierre:** provision_crypto.sh mezcla entropy en prod. Assert calidad entropy.
**Estimación:** 1 sesión post-FEDER

### DEBT-VAULT-HA-001 — Vault HA backend raft para producción
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 149
**Descripción:** Backend `file` suficiente para dev/FEDER. Producción real requiere Vault HA con backend `raft` (3+ nodos). Dev y prod no deben ser idénticos — diferencial se mitiga con tests específicos.
**Test de cierre:** Vault HA 3 nodos. Kill del líder → failover < 5s → componentes siguen operativos.
**Estimación:** 2 sesiones post-FEDER

### DEBT-CRYPTO-STAMPEDE-001 — Jitter startup en vault_client
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 149 (AQ2 ChatGPT)
**Componente:** `common/vault_client`
**Descripción:** Si N componentes arrancan simultáneamente, todos hacen GET a Vault en el mismo instante. Necesita jitter: `component_index * 500ms + rand(0-1000ms)`.
**Test de cierre:** 6 componentes arranque simultáneo → Vault no ve burst. Latencia P99 < 2s.
**Estimación:** 30min al implementar vault_client

### DEBT-CRYPTO-AUDIT-FINGERPRINT-001 — Fingerprint en etcd crypto_ready
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 149 (AQ3 ChatGPT + Kimi corrección)
**Componente:** `common/vault_client` + etcd
**Descripción:** Al registrar crypto_ready, incluir fingerprint = sha256(pk) [clave pública, no seed]. key_version, family, derivation_timestamp. NO material sensible en logs.
**Test de cierre:** etcd contiene {component, crypto_ready, key_version, family, fingerprint, timestamp} por componente.
**Estimación:** 1h al implementar vault_client

### DEBT-CRYPTO-HEARTBEAT-001 — Heartbeat periódico post-crypto_ready
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 149 (AQ4 ChatGPT + Kimi spec)
**Componente:** `common/vault_client` + etcd
**Descripción:** Lease etcd TTL=10s, keepalive cada 5s. Si componente no renueva en 10s → offline. Alerta si >2 componentes pierden lease simultáneamente.
**Test de cierre:** Kill componente → etcd detecta en ≤10s. Pipeline alerta.
**Estimación:** 1h al implementar vault_client

### DEBT-ALERTING-EDGE-SOS-001 — Webhook SOS desde edge cuando servidor central offline
**Severidad:** 🔴 P1 pre-FEDER
**Estado:** ABIERTO — DAY 149
**Componente:** `scripts/alerts/sos_vault_unreachable.sh` + Ansible group_vars
**Descripción:** Cuando Vault está caído y cache TTL se degrada, el nodo edge debe alertar via webhook configurable (Discord, Telegram, email, WhatsApp Business API) directamente desde el edge — sin depender del servidor central. Escalado por gravedad según TTL restante:
- TTL > 48h: INFO log local
- TTL < 48h: WARN → Discord/Telegram/email
- TTL < 24h: CRITICAL → todos los canales + retry cada hora
- TTL = 0h: último intento antes de exit(1)
Configurado via `ansible/group_vars/prod.yml` por cliente (discord_webhook, telegram_bot_token, email_to, etc.).
**Test de cierre:** Simular Vault caído → alerta llega a Discord/Telegram en < 1min.
**Estimación:** 1 sesión pre-FEDER

### DEBT-CRYPTO-AUTONOMY-001 — Máquina de estados autonomía extendida
**Severidad:** 🔴 P1 pre-FEDER
**Estado:** ABIERTO — DAY 150 (Opción D Consejo 8/8)
**Componente:** `common/vault_client.cpp` + todos los componentes

Implementar máquina de estados formal:
```
NORMAL → EXTENDED_AUTONOMY → RECONCILIATION → REVOKED
```
- `NORMAL`: Vault responde, clave vigente, renovación periódica.
- `EXTENDED_AUTONOMY`: Vault inaccesible > TTL. Continúa operando. Log CRITICAL cada 15 min. Webhook SOS. Intentos renovación cada 5 min en background.
- `RECONCILIATION`: Vault recuperado. Envía `key_version` actual. Valida antes de volver a NORMAL.
- `REVOKED`: Revocación explícita firmada recibida. Descarga nueva clave. EMECAS si necesario.

Invalidación de clave SOLO por: revocación explícita firmada desde Vault, EMECAS, tamper detection. NUNCA por TTL.
Circuit breaker configurable (default 30 días) con alerta progresiva.
Logs firmados locales con flag `EXTENDED_AUTONOMY=1` para cadena forense.

**Test de cierre:** Kill Vault → componente entra en EXTENDED_AUTONOMY + SOS webhook. Recuperar Vault → RECONCILIATION → NORMAL. Revocación explícita → REVOKED.
**Estimación:** 2 sesiones

---

### DEBT-FIREWALL-AUTONOMY-MODE-001 — Firewall default-deny en EXTENDED_AUTONOMY
**Severidad:** 🔴 P1 pre-FEDER
**Estado:** ABIERTO — DAY 150 (Consejo 8/8 + Founder)
**Componente:** `firewall-acl-agent`

Cuando `vault_client` entra en `EXTENDED_AUTONOMY`, `firewall-acl-agent` debe:
1. Cambiar política a default-deny para tráfico nuevo (solo flujos establecidos permitidos)
2. Umbral ML más sensible (más FP aceptables, cero FN)
3. Logging en nivel DEBUG — retención máxima local
4. Todos los eventos Parquet con `EXTENDED_AUTONOMY=1`
5. Al volver a NORMAL: restaurar política original + sincronizar logs

La pérdida de Vault es un indicador de ataque inminente, no una razón para relajar la defensa.

**Test de cierre:** Vault KO → firewall en default-deny → tráfico nuevo bloqueado → flujos establecidos pasan. Vault recuperado → política restaurada.
**Estimación:** 1 sesión

---

### DEBT-CRYPTO-REVOCATION-LOCAL-001 — Revocación offline sin Vault
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 150 (Founder + Claude)
**Componente:** `common/vault_client` + herramienta administrador

Si Vault es inaccesible y el administrador del hospital necesita invalidar claves comprometidas, necesita mecanismo local: fichero firmado con clave offline del administrador (air-gapped) que el pipeline reconoce como orden de revocación. Complemento simétrico a la autonomía edge.

Formato: `/var/lib/argus/emergency-revocation.json` firmado con clave Ed25519 del administrador.
El pipeline verifica firma antes de procesar la revocación.

**Test de cierre:** Vault KO → fichero de revocación firmado → pipeline entra en REVOKED → descarga nueva clave cuando Vault vuelve.
**Estimación:** 1 sesión post-FEDER

---

### DEBT-CRYPTO-RECONCILIATION-001 — Handshake de validación al recuperar Vault
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 150 (Kimi/Consejo 8/8)
**Componente:** `common/vault_client`

Al detectar que Vault vuelve a estar disponible:
1. El nodo envía su `key_version` actual a Vault
2. Vault responde: `VALID` → vuelve a NORMAL; `REVOKED` → descarga nueva clave y rota; `UNKNOWN` → EMECAS
3. No vuelve a NORMAL sin handshake completado
4. Logs del período de autonomía se sincronizan al central
5. Operador recibe resumen del período de autonomía extendida

Previene que un atacante que suplante Vault induzca fin prematuro del modo seguro.

**Test de cierre:** Vault KO → EXTENDED_AUTONOMY → Vault recuperado → RECONCILIATION → `key_version` validada → NORMAL. Vault suplantado → RECONCILIATION rechazada → sigue en EXTENDED_AUTONOMY.
**Estimación:** 1 sesión

---

### DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001 — Cache persistente cifrada en producción edge
**Severidad:** 🔴 P1 pre-FEDER
**Estado:** ABIERTO — DAY 150 (Consejo 8/8)
**Componente:** `common/vault_client` + Ansible/Jinja2

- **Dev / EMECAS:** `/run/argus/crypto-cache/` — tmpfs, se pierde en destroy. Correcto por diseño.
- **Prod edge:** `/var/lib/argus/{component}/crypto-cache/` — persistente, permisos 0600, propietario `argus:argus`.

**Precondición obligatoria:** Ansible verifica que el filesystem está cifrado (LUKS/dm-crypt) antes de habilitar cache persistente. Si no hay cifrado → despliegue falla con error explícito. Seed maestra en texto plano es inaceptable bajo cualquier circunstancia.

**Advertencia en docs:** sin TPM/LUKS, cache persistente = seed en disco plano. La opción de Vault obligatorio en cada arranque es preferible en ese caso.

`VaultClientConfig.cache_dir` ya es configurable — solo requiere Ansible/Jinja2 que inyecte el path correcto según ambiente.

**Test de cierre:** deploy prod → Ansible verifica LUKS → cache en `/var/lib/argus/` → reboot → pipeline arranca sin Vault → cache válida usada → WARN en log.
**Estimación:** 1 sesión

---

### DEBT-EMECAS-DUAL-COMPILATION-001 — CI compila ARGUS_VAULT_ENABLED ON y OFF
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 150 (DeepSeek/Consejo 8/8)
**Componente:** Jenkinsfile + Makefile

El pipeline EMECAS debe compilar AMBAS variantes en cada build:
- `ARGUS_VAULT_ENABLED=OFF` (community, seed-client)
- `ARGUS_VAULT_ENABLED=ON` (enterprise, VaultClient)

Cualquier error de compilación o enlace en la rama enterprise aparecerá inmediatamente.
Elimina la divergencia silenciosa — si un PR rompe community, el build rojo lo detecta.

Jenkinsfile: dos stages paralelos `Test Community` y `Test Enterprise`.
Makefile: targets `vault-client-build-community` y `vault-client-build-enterprise`.

**Test de cierre:** PR que rompe community → CI rojo. PR que rompe enterprise → CI rojo. Ambas variantes compilan y tests pasan → CI verde.
**Estimación:** 1 sesión

---


### ADR-045 — VaultClient Decomposition by Composition
**Estado:** ✅ APROBADO DAY 151 — Consejo 8/8 + Founder | **Implementación:** DAY 153+
**Descripción:** VaultClient se descompone en interfaces inyectables para eliminar el monolito:
- `IVaultTransport` → HTTP a Vault API
- `ICacheManager` → tmpfs, TTL, mlock, permisos
- `IEtcdRegistrar` → registro + keepalive
- `ICryptoDeriver` → KDF + sign_seed_keypair
- `IJitterStrategy` → anti-stampede
- `CryptoAutonomyStateMachine` → estados operativos

`VaultProvider` las compone. Cada responsabilidad testeable en aislamiento sin Vault, sin red, sin etcd. Independencia de proveedor: hoy Vault, mañana lo que sea, pasado mañana el nuestro propio. Documentado en `docs/adr/ADR-045-vaultclient-decomposition.md`.

**Test de cierre:** cada interfaz testeada con mock independiente. `make test-all` verde.
**Estimación:** DAY 153 (IVaultTransport + ICacheManager) + DAY 154 (IEtcdRegistrar + ICryptoDeriver)

---

### DEBT-LICENSE-VAULT-001 — Servidor de licencias en Vault
**Severidad:** 🟡 P2 post-FEDER
**Estado:** ABIERTO — DAY 150 (Founder + DeepSeek)
**Componente:** Vault + plugin system

Junto con las seeds, Vault contiene `argus/{env}/features/license` — objeto firmado que habilita/deshabilita plugins enterprise. El binario es el mismo; lo que cambia es qué plugins se descargan y activan según la licencia.

```json
{
  "edition": "enterprise",
  "features": ["vault_crypto", "neo4j_graph", "opencanary", "falco_actuation"],
  "valid_until": "2027-12-31",
  "installation_id": "hospital-badajoz-001"
}
```

Licencia firmada con clave Ed25519 offline del vendor. El plugin-loader verifica firma antes de cargar cualquier plugin enterprise.

**Test de cierre:** licencia community → plugins enterprise no se cargan. Licencia enterprise → plugins enterprise disponibles. Licencia expirada → plugins enterprise deshabilitados + alerta SOS.
**Estimación:** 2 sesiones post-FEDER

---

### DEBT-PLUGIN-ENTERPRISE-001 — Definir plugins enterprise vs community
**Severidad:** 🟡 P2 post-FEDER
**Estado:** ABIERTO — DAY 150
**Componente:** plugin system + docs/OPEN_CORE.md

Definir formalmente qué módulos van detrás de licencia enterprise:
- **Community:** pipeline C++20 completo, seed-client, AppArmor básico, Falco reglas básicas, argus-network-isolate
- **Enterprise (plugins firmados):** VaultClient (governance criptográfico), Neo4j connector (graph analytics), OpenCanary (honeypot/deception), Falco actuation avanzado (JA3/JA4, forensic chain)

La detección ML (F1=0.9985) es idéntica en ambas ediciones. La separación es governance, operabilidad y escalabilidad — nunca capacidad de detección.

Crear `docs/OPEN_CORE.md` con la matriz de funcionalidades y la regla de diseño:
> "Todo lo que afecta a la precisión de detección debe ser idéntico en community y enterprise."

**Test de cierre:** docs/OPEN_CORE.md creado. Matrix de features documentada. ADR-045 Open-Core Feature Flags creado.
**Estimación:** 1 sesión



### DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 — Bootstrap status sin firma Ed25519
**Severidad:** 🔴 Alta — P1 pre-FEDER
**Estado:** ABIERTO — DAY 151 (Claude + Grok, Consejo)
**Componente:** `etcd-server/src/main.cpp`, `/run/argus/etcd-bootstrap-status.json`

El fichero de bootstrap status escrito en STEP 0 no lleva firma Ed25519. Un atacante con acceso local podría reemplazarlo con fingerprint falso antes del arranque. Firmar con `crypto_material.sk` (disponible en STEP 0) y verificar la firma antes de consumir el fichero en cualquier componente. Misma cadena de confianza que los plugins (ADR-025).

**Test de cierre:** bootstrap status firmado Ed25519. Verificación de firma falla con fichero manipulado.
**Estimación:** 1h pre-FEDER

---

### DEBT-AUTONOMY-STATE-PERSISTENCE-001 — Estado autonomía sin persistencia firmada
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Grok, Consejo)
**Componente:** `CryptoAutonomyStateMachine`

Al entrar en `AUTONOMOUS`, escribir `/run/argus/crypto-autonomy-state.json` firmado Ed25519 con timestamp + fingerprint. Al recuperar, validar la firma antes de reconciliar. Previene que un atacante manipule el estado de autonomía persistido.

**Test de cierre:** entrar en AUTONOMOUS → fichero escrito y firmado. Manipulación detectada.
**Estimación:** 1h

---

### DEBT-AUTONOMY-CLOCK-INJECTION-001 — Clock no inyectable en CryptoAutonomyStateMachine
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Kimi, Consejo)
**Componente:** `common/crypto_autonomy.h`

`CryptoAutonomyStateMachine` usa `std::chrono::steady_clock` directamente. Sin inyección de clock, los tests que verifican el TTL del circuit breaker deben esperar 30 días reales. Implementar `template<typename Clock = std::chrono::steady_clock>` o interfaz `IClock` inyectable.

**Test de cierre:** test avanza clock sintético 31 días → transición a DEGRADED sin esperar.
**Estimación:** 30min al implementar la clase

---


### DEBT-FIREWALL-DENY-SELECTIVE-001 — Regla default-deny demasiado agresiva
**Severidad:** 🔴 P0 — DAY 154 (Consejo 8/8 UNÁNIME)
**Estado:** ABIERTO — CERRAR EN DAY 155
**Componente:** `firewall-acl-agent/src/core/autonomy_reactor.cpp`

La regla actual `iptables -I INPUT 1 -j DROP` en modo AUTONOMOUS bloquea:
- Loopback (127.0.0.1) → rompe IPC interno, health checks, métricas
- Conexiones establecidas (ESTABLISHED, RELATED) → rompe sesiones activas de médicos en el HIS
- Subredes internas del hospital (imaging, monitorización, HL7, DICOM) → puede parar un quirófano
- SSH de management → deja al sysadmin fuera en momento de crisis

**Regla correcta (Kimi — orden crítico):**
```bash
iptables -I INPUT 1 -i lo -j ACCEPT --comment "argus-autonomy-lo"
iptables -I INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT \
  --comment "argus-autonomy-established"
iptables -I INPUT 3 -s 10.0.0.0/8 -j ACCEPT --comment "argus-autonomy-rfc1918-a"
iptables -I INPUT 4 -s 172.16.0.0/12 -j ACCEPT --comment "argus-autonomy-rfc1918-b"
iptables -I INPUT 5 -s 192.168.0.0/16 -j ACCEPT --comment "argus-autonomy-rfc1918-c"
iptables -I INPUT 6 -j DROP --comment "argus-autonomy-deny"
```

Subnets whitelist configurables vía JSON — no hardcodeadas.
El DROP debe ser la ÚLTIMA regla de INPUT, no la primera.

**Test de cierre:** AUTONOMOUS activado → loopback responde, SSH interno funciona,
tráfico externo bloqueado → 6 tests actualizados PASSED.
**Estimación:** 1.5h DAY 155

### DEBT-AUTONOMY-ZMQ-EVENTS-001 — Transiciones de autonomía no emiten eventos ZeroMQ
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Grok, Consejo)
**Componente:** `CryptoAutonomyStateMachine` + ZeroMQ bus

**Consenso Consejo DAY 154 (7/8):** ZMQ pub/sub directo, sin polling como mecanismo principal. Solo polling reconciliador lento (60-120s) como safety net. Topic: `argus.crypto.autonomy`. Transport: `inproc://argus.autonomy` (mismo proceso) o `ipc:///run/argus/autonomy.sock`. Founder (Alonso): acuerda ZMQ como mecanismo principal.

Cada transición de estado (`NORMAL→AUTONOMOUS`, `AUTONOMOUS→RECONCILING`, etc.) debe emitir un evento ZeroMQ interno en el topic `crypto.autonomy.transition`. Permite que firewall, alerting y RAG reaccionen sin polling.

**Test de cierre:** transición de estado → evento ZeroMQ recibido por suscriptor.
**Estimación:** 1h

---

### DEBT-ETCD-HA-QUORUM-001 — etcd-server en HA con quorum
**Severidad:** 🔴 Alta — P0 post-FEDER (OBLIGATORIO, no opcional)
**Estado:** ABIERTO — DAY 142
**Componente:** `etcd-server/` — arquitectura multi-nodo

etcd-server actual es single-node. Si cae, ningún componente puede registrarse ni coordinarse — y ningún mecanismo de mutex entre componentes puede ser robusto. Diseño requerido:
- Múltiples instancias etcd-server con quorum (Raft o equivalente).
- Componentes se registran ante el primer etcd disponible al arrancar.
- Al recuperarse un nodo etcd caído, se une al quorum y sincroniza estado.
- Quorum garantiza que todos los componentes registrados y vivos compartan el mismo estado.
- Líder elegido — si cae, quorum inmediato para elegir nuevo líder.
- Nuevo etcd que llega se une al quorum y, cuando le toque, es el nuevo líder.

**Nota:** No es deuda "eterna" — es deuda crítica que hay que cerrar. Es prerequisito de `DEBT-MUTEX-ROBUST-001` y de cualquier coordinación fiable entre componentes en producción.

**Test de cierre:** `make hardened-full` con 3 instancias etcd. Kill del líder → quorum en < 5s → componentes siguen operativos → nuevo líder elegido.
**Estimación:** 3-4 sesiones post-FEDER

---

### DEBT-MUTEX-ROBUST-001 — Mutex robusto entre variantes sniffer
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 142 (Nivel 1 via tmux cerrado)
**Componente:** `scripts/check-sniffer-mutex.sh` + coordinación etcd

La implementación actual via sesiones tmux (Nivel 1) es provisional. No es robusta en producción — depende de una herramienta de usuario, no de un mecanismo de coordinación del sistema. Alternativas a evaluar para Nivel 2: `flock` (lockfile), PID file en `/var/run/argus/`, o coordinación via etcd cuando esté en HA (`DEBT-ETCD-HA-QUORUM-001`). La solución definitiva no puede depender de una única fuente de verdad que pueda caer.

**Test de cierre:** exclusión mutua funciona incluso si tmux no está disponible o etcd está caído.
**Estimación:** 1 sesión post-FEDER (tras DEBT-ETCD-HA-QUORUM-001)

---

### DEBT-IRP-MULTI-SIGNAL-001 — Criterio de disparo multi-señal IRP
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 142
**Componente:** `firewall-acl-agent` + `isolate.json`

Para FEDER: dos condiciones AND mínimas (score + event_type). Para producción hospitalaria real: señal más rica. Contexto: monitores de quirófano, bombas de infusión y ventiladores mecánicos pueden estar en la intranet/DMZ del hospital — `firewall-acl-agent` en esos nodos tiene sentido. Un falso positivo que aísle un equipo médico es inaceptable. El criterio de disparo debe ser explicable, auditable y resistente a falsos positivos transitorios.

**Diseño futuro (IDEA-IRP-DECISION-MATRIX-001):** matriz de decisión con score + tipo + ventana temporal + potencialmente whitelist de dispositivos críticos.

**Nota sobre Platt scaling:** Qwen (Consejo DAY 142) advierte que sin calibración del score (Platt scaling o isotonic regression), el valor 0.95 no tiene significado estadístico real. Registrar como sub-tarea de DEBT-ADR040-002.

**Estimación:** 2 sesiones post-FEDER

---

### DEBT-IRP-LAST-KNOWN-GOOD-001 — Rollback con estado persistente
**Severidad:** 🟢 Baja post-FEDER
**Estado:** ABIERTO — DAY 142
**Componente:** `tools/argus-network-isolate/isolate.cpp`

El rollback actual elimina solo la tabla `argus_isolate` — correcto y suficiente para FEDER. En entornos con rulesets nftables propios del cliente (hospitales con segmentación VLAN, QoS, reglas personalizadas), el rollback podría dejar el sistema en estado inconsistente. Solución: `/etc/ml-defender/firewall-acl-agent/last-known-good.nft` actualizado periódicamente, firmado Ed25519. Restauración selectiva en rollback.

**Estimación:** 1 sesión post-FEDER

---

### DEBT-IRP-QUEUE-PROCESSOR-001
**Severidad:** 🔴 Alta — post-merge
**Estado:** ABIERTO — DAY 136
**Componente:** ADR-042 IRP
**Descripción:** Cola irp-queue sin límites ni procesador systemd dedicado.
**Estimación:** 1 sesión (junto a IRP-NFTABLES sesión 3)

---

### DEBT-EMECAS-AUTOMATION-001
**Severidad:** 🟡 Media
**Estado:** ABIERTO — DAY 140
**Componente:** Makefile raíz + directorio logs/
Targets `make emecas-dev/prod-x86/prod-arm64` con log automático fechado.
**Estimación:** 1 sesión

---

### DEBT-LLAMA-API-UPGRADE-001
**Severidad:** 🟡 Media — API deprecated, no CVE activo
**Estado:** ABIERTO — DAY 140
**Componente:** `rag/src/llama_integration_real.cpp:29`
**Estimación:** 1 sesión post-FEDER (salvo CVE)

---

### DEBT-ODR-CI-GATE-001
**Severidad:** 🔴 Alta
**Estado:** ABIERTO — DAY 140
**Componente:** Jenkinsfile + `make check-odr`
**Estimación:** 1 sesión post-hardware FEDER

---

### DEBT-GENERATED-CODE-CI-001
**Severidad:** 🟡 Media
**Estado:** ABIERTO — DAY 140
**Estimación:** 1 sesión post-hardware

---

### DEBT-MAYBE-UNUSED-MIGRATION-001
**Severidad:** 🟢 Baja
**Estado:** ABIERTO — DAY 140
**Estimación:** 1 sesión

---

### DEBT-JENKINS-SEED-DISTRIBUTION-001
**Severidad:** 🔴 Alta | **Estado:** ABIERTO — DAY 136

### DEBT-CRYPTO-MATERIAL-STORAGE-001
**Severidad:** 🔴 Alta | **Estado:** ABIERTO — DAY 136

### DEBT-PROD-APT-SOURCES-INTEGRITY-001
**Severidad:** 🔴 Crítica | **Estado:** ABIERTO

### DEBT-SEEDS-SECURE-TRANSFER-001 · DEBT-SEEDS-LOCAL-GEN-001 · DEBT-SEEDS-BACKUP-001
**Severidad:** 🔴 Alta | **Corrección:** post-FEDER

### DEBT-KEY-SEPARATION-001 · DEBT-DEBIAN13-UPGRADE-001 · DEBT-PROD-APPARMOR-PORTS-001
**Severidad:** 🟡 Media | **Target:** post-FEDER

### DEBT-PROD-FALCO-RULES-EXTENDED-001 · DEBT-APT-TIMEOUT-CONFIG-001 · DEBT-FEDER-DEMO-SCRIPT-001 · DEBT-CHECK-PROD-SEED-CONDITIONAL-001
**Severidad:** 🟡 Media | **Target:** varios

---

## 🔵 BACKLOG — Deuda de seguridad crítica (pre-producción)

| ID | Tarea | Test de cierre | Feature destino |
|----|-------|---------------|----------------|
| **DEBT-SAFE-PATH-RESOLVE-MODEL-001** | `resolve_model()` para modelos firmados Ed25519 | test RED→GREEN | feature/adr038-acrl |
| **DEBT-CRYPTO-003a** | mlock() + explicit_bzero(seed) post-derivación HKDF | Valgrind/ASan | feature/crypto-hardening |
| **DEBT-SNIFFER-SEED** | Unificar sniffer bajo SeedClient | sniffer arranca con SeedClient | feature/crypto-hardening |
| **DEBT-NATIVE-LINUX-BOOTSTRAP-001** | README + make deps-native sin Vagrant | make deps-native verde en Ubuntu 22.04 | post-FEDER |

---

## 📋 BACKLOG — ADR-040 y ADR-041

### DEBT-ADR040-001 a 012 — ML Plugin Retraining Contract
**Target:** post-FEDER (implementación Año 1) | **Consejo 8/8 DAY 134**

| ID | Descripción | Target |
|----|-------------|--------|
| DEBT-ADR040-001 | Golden set v1 (≥50K flows, Parquet, SHA-256 embebido en plugin) | v1.0 |
| DEBT-ADR040-002 | confidence_score ∈ [0,1] en salida ZeroMQ + Platt scaling | v1.0 |
| DEBT-ADR040-003 | walk_forward_split.py — mín. 3 ventanas, KS drift | v1.1 |
| DEBT-ADR040-004 | check_guardrails.py — Recall −0.5pp / F1 −2pp → exit 1 | v1.1 |
| DEBT-ADR040-005 | Guardrail integrado en firma Ed25519 (ADR-025) | v1.1 |
| DEBT-ADR040-006 | IPW + uncertainty sampling (P≈0.5), ratio [3%-10%] | v1.2 |
| DEBT-ADR040-007 | Interfaz web revisión exploración en rag-security | v1.2 |
| DEBT-ADR040-008 | Informe diversidad por ciclo: Shannon entropy, ATT&CK coverage | v1.2 |
| DEBT-ADR040-009 | Competición algoritmos: XGBoost vs CatBoost vs LightGBM vs RF | pre-lock-in |
| DEBT-ADR040-010 | Dataset lineage en metadatos del plugin | v1.1 |
| DEBT-ADR040-011 | Canary deployment: 5-10% tráfico 24h antes de 100% | v1.2 |
| DEBT-ADR040-012 | docs/GOLDEN-SET-REGISTRY.md | v1.0 |

### DEBT-ADR041-001 a 006 — Hardware Acceptance Metrics FEDER
**Target:** pre-FEDER, deadline 22 sep 2026 | **Consejo 8/8 DAY 134**

| ID | Descripción | Estado |
|----|-------------|--------|
| DEBT-ADR041-001 | pcap CTU-13 benchmark versionado con SHA-256 | ⏳ |
| DEBT-ADR041-002 | make golden-set-eval ARCH=$(uname -m) | ⏳ |
| DEBT-ADR041-003 | make feder-demo — suite completa <30 min | ⏳ |
| DEBT-ADR041-004 | Compra hardware x86 (NUC, NIC XDP nativo) | ⏳ |
| DEBT-ADR041-005 | Compra Raspberry Pi 4/5 | ⏳ |
| DEBT-ADR041-006 | Ejecución protocolo completo en hardware físico | ⏳ |

---

## 📋 BACKLOG — Benchmarks Empíricos (FEDER Year 1)


### BACKLOG-PAPER-METHODOLOGY-001 — Paper arXiv: TDH + Consejo de Sabios
**Estado:** ⏳ BACKLOG — cuando aRGus pueda dejarse solo unos días
**Prioridad:** P2 post-FEDER
**Target:** arXiv cs.SE
**Co-autor natural:** Dr. Andrés Caro Lindo (UEx/INCIBE)
**Título tentativo:** "Test-Driven Hardening and Multi-Model Peer Review:
A Methodology for Human-AI Collaborative Engineering of Security-Critical Systems"

**Contribución:** La metodología — no el sistema técnico (ya en arXiv:2604.04952).
Cómo un investigador independiente, sin institución ni financiación, construyó
un sistema de seguridad para infraestructura crítica en 150+ días usando:
- Consejo de Sabios (8 modelos IA como peer review adversarial)
- Test-Driven Hardening (TDH) como disciplina de calidad
- EMECAS como invariante de reproducibilidad
- ADRs como separación intent/spec/implementation
- Prompts de continuidad como memoria externa estructurada

**Datos disponibles:** 150+ días de commits públicos, ADRs, decisiones rechazadas
por el Consejo, bugs encontrados por tests, momentos en que EMECAS salvó merges.

**Ángulo principal:** democratización del peer review experto via LLMs.
Históricamente, un investigador solo no tiene acceso a 8 expertos adversariales.

**Conexión con Kapil Viren Ahuja (Medium):** su "three-layer schematic" (intent/spec/
implementation) es exactamente lo que ADRs + tests + código implementan por
construcción en aRGus. El paper de metodología es el antídoto empírico a los
frameworks SDD que él critica.

**Nota:** Las notas se están tomando solas. Prompts de continuidad, notas del
Consejo, ADRs — todo es material primario. El paper casi se escribe solo.


### BACKLOG-DEPLOY-CALCULATOR-001 — Calculadora deployment.yml → configs óptimas
**Estado:** ⏳ BACKLOG — requiere hardware físico para calibrar
**Prioridad:** P1 cuando lleguen RPi + N100
**Descripción:** Lee `deployment.yml` (topología declarativa) + `hardware_profile.yml`
(RAM, CPU, NIC disponibles en cada nodo) y genera los JSONs de configuración
óptimos para cada componente.

Calcula automáticamente:
- `worker_threads` según CPU disponible
- `buffer_size_mb` según RAM
- `queue_depth` según latencia de red medida
- familias criptográficas según topología de canal

Es el "optimizador de hardware" que conecta con las templates Jinja2.
Jenkins llama al calculador antes de Ansible para inyectar valores óptimos.

**Conexión con ADR-021 (seed families) y ADR-034 (Declarative Deployment):**
deployment.yml ya esbozado en ADR-021. El calculador es la implementación.

**Prerequisito:** hardware físico real (RPi + N100) para calibrar los valores.
Sin datos reales, cualquier fórmula es especulativa.

**Tiers de despliegue que el calculador debe soportar:**
- Tier 1: RPi5 (~80€) — clínica rural, libpcap
- Tier 2: N100 (~300€) — hospital comarcal, eBPF nativo
- Tier 3: HW empresarial — hospital universitario, XDP offload
- Tier 4: Cloud soberana — red hospitales nacional (post-FEDER)


### BACKLOG-HARDWARE-FEDER-001 — Adquisición hardware lab distribuido
**Estado:** ⏳ PENDIENTE — coordinando con Andrés Caro Lindo (UEx/INCIBE)
**Prioridad:** P0 — desbloquea ADR-041, BACKLOG-BENCHMARK-CAPACITY-001,
  inversión eBPF/XDP bare-metal, datasets UEx, convocatoria FEDER

**Inventario mínimo propuesto (~460€):**
| Hardware | Cantidad | Precio/ud | Rol |
|---|---|---|---|
| Raspberry Pi 5 (8GB) | 2 | ~80€ | Edge ARM64, libpcap Variant B |
| Intel N100 miniPC | 2 | ~150€ | Edge x86-64, eBPF/XDP nativo |
| Switch 8 puertos gigabit | 1 | ~30€ | Intranet emulada |
| MacBook Pro (existente) | 1 | — | Servidor central (Vagrant VM) |

**Por qué el N100 es crítico:**
- NIC Intel i226-V tiene driver XDP nativo (igc) — sin SKB fallback
- VirtualBox virtio: eBPF ~10 Mbps (SKB mode) vs libpcap ~19 Mbps
- N100 bare-metal: eBPF/XDP puede dar Gbps — inversión total
- Sin N100, las cifras del paper son el SUELO, nunca el techo
- El delta VirtualBox vs bare-metal es el argumento más fuerte para FEDER

**Experimentos que desbloquea:**
1. ADR-029 Variant A vs B en bare-metal real — inversión predicha pero no medida
2. Los 2 FP VirtualBox (mDNS + broadcast) probablemente desaparecen en bare-metal
3. Reentrenamiento ML en el propio nodo con datos capturados reales
4. Hospital simulado completo con múltiples configuraciones
5. HA etcd con 3 nodos físicos (DEBT-ETCD-HA-QUORUM-001)
6. Datasets bajo paraguas UEx publicables

**Vagrantfile servidor central (pendiente):**
vagrant/central-server/Vagrantfile — debian minimal, provisionado
incrementalmente. MacBook como servidor mientras llegan fondos UEx.

### BACKLOG-ZMQ-TUNING-001
**Estado:** ⏳ BACKLOG | **Prioridad:** P1 — Prerequisito de BENCHMARK-CAPACITY
**Bloqueado por:** ADR-029 Variant A + Variant B estables

### BACKLOG-BENCHMARK-CAPACITY-001
**Estado:** ⏳ BACKLOG | **Prioridad:** P1 — FEDER Year 1 Deliverable
**Bloqueado por:** BACKLOG-ZMQ-TUNING-001 + hardware físico

### BACKLOG-BUILD-WARNING-CLASSIFIER-001
**Estado:** ⏳ BACKLOG | **Prioridad:** Post-FEDER
**Decisión Consejo DAY 141:** script grep/awk determinista. Workaround actual: `grep 'warning:' output.md | grep -v 'defender:'`

---

## 📋 BACKLOG — P3 Features futuras

### PHASE 5 — Loop Adversarial

| ID | Tarea | Gates mínimos |
|----|-------|--------------|
| **DEBT-PENTESTER-LOOP-001** | ACRL: Caldera → eBPF → XGBoost warm-start → Ed25519 → hot-swap | G1–G5 sandbox |
| **ADR-038** | ACRL ADR formal | Aprobado por Consejo |
| **ADR-025-EXT-001** | Emergency Patch Protocol — Plugin Unload vía mensaje firmado | TEST-INTEG-SIGN-8/9/10 RED→GREEN |

### Variantes de producción

| Variante | Tarea | Feature destino |
|----------|-------|----------------|
| **aRGus-production x86** | Pipeline E2E hardened · check-prod-all verde | feature/adr030-variant-a |
| **aRGus-production arm64** | Imagen Debian arm64 + AppArmor + Vagrantfile | feature/production-images |
| **aRGus-seL4** | Kernel seL4, libpcap, sniffer monohilo. Branch independiente. | feature/sel4-research |

---

## BACKLOG-FEDER-001

**Estado:** ACTIVO — colaboración UEx/INCIBE en curso
**Contacto:** Andrés Caro Lindo — UEx/INCIBE — andresc@unex.es
**Deadline límite:** referencia de ritmo, NO deadline duro (DAY 149)
**Convocatoria:** pendiente identificar — limitada a investigador independiente sin empresa
**Colaboración:** Andrés como co-investigador, no solo asesor. Posible infra UEx para servidor.
**Hardware en camino (DAY 149):** RPi × N + switch desde UEx. Email pendiente para añadir N100 x86.
**Emails enviados DAY 141:** hardware FEDER + scope standalone vs federado
**Llamada DAY 149:** datasets bajo paraguas UEx prerequisito convocatoria

### Gate de entrada

- [x] ADR-026 mergeado a main (XGBoost F1=0.9978)
- [x] ADR-030 Variant A infraestructura completa (DAY 133)
- [x] Pipeline E2E en hardened VM verde (`make check-prod-all`) — DAY 134 ✅
- [x] DEBT-VARIANT-B-BUFFER-SIZE-001 implementada ✅ DAY 142
- [ ] ADR-030 Variant B (ARM64) estable
- [ ] DEBT-IRP-NFTABLES-001 sesión 3/3 — integración firewall-acl-agent
- [ ] Demo técnica grabable < 10 minutos (`scripts/feder-demo.sh`)
- [ ] ADR-041 protocolo hardware: métricas validadas en x86 + ARM (`make feder-demo`)
- [ ] Golden set v1 creado y versionado (DEBT-ADR040-001)
- [ ] BACKLOG-ZMQ-TUNING-001 concluido
- [ ] BACKLOG-BENCHMARK-CAPACITY-001 concluido (FEDER Year 1 Deliverable)
- [ ] Clarificación scope con Andrés: NDR standalone vs federación (antes julio 2026)

---

## 🔑 Decisiones de diseño consolidadas

| Decisión | Resolución | DAY |
|---|---|---|
| **Test RED→GREEN obligatorio** | Todo fix de seguridad requiere test antes del merge. | Consejo 7/7 · DAY 124 |
| **Property test obligatorio** | Todo fix de seguridad incluye property test si aplica. | Consejo 8/8 · DAY 125 |
| **Symlinks en seeds: NO** | resolve_seed(): lstat() ANTES de resolve(). | Consejo 8/8 · DAY 125-126 |
| **ConfigParser prefix fijo** | allowed_prefix explícito, default /etc/ml-defender/. | Consejo 8/8 · DAY 125-126 |
| **resolve_config() para configs** | lexically_normal() verifica prefix ANTES de seguir symlinks. | DAY 127 |
| **Taxonomía safe_path: 3 primitivas activas** | resolve() · resolve_seed() · resolve_config(). | Consejo 8/8 · DAY 127 |
| **CWE-78 execve()** | execv() sin shell. | Consejo 8/8 · DAY 128 |
| **RULE-SCP-VM-001** | scp/vagrant scp. Prohibido pipe zsh. | Consejo 8/8 · DAY 129 |
| **REGLA EMECAS** | vagrant destroy -f && vagrant up && make bootstrap && make test-all. | DAY 130 |
| **AppArmor como primera línea BSR** | AppArmor bloquea compiladores. check-prod-no-compiler es auditoría. | DAY 132 — founder |
| **cap_bpf reemplaza cap_sys_admin** | Linux ≥5.8: cap_bpf para eBPF. | Consejo 8/8 · DAY 133 |
| **cap_net_bind_service eliminada** | Puerto 2379 > 1024. Innecesaria. | Consejo 8/8 · DAY 133 |
| **LimitMEMLOCK en systemd** | etcd-server: LimitMEMLOCK=16M. | Consejo 8/8 · DAY 133 |
| **deny explícitos en AppArmor** | Mantener — claridad auditiva hospitalaria. | Founder · DAY 133 |
| **Walk-forward obligatorio (ADR-040)** | K-fold prohibido. Split sobre timestamp_first_packet. Mín. 3 ventanas. | ADR-040 · Consejo 8/8 · DAY 134 |
| **Golden set inmutable (ADR-040)** | ≥50K flows, SHA-256 embebido en plugin firmado. | ADR-040 · Consejo 8/8 · DAY 134 |
| **Guardrail asimétrico Ed25519 (ADR-040)** | Recall −0.5pp. F1 −2pp. FPR +1pp. Latencia p99 +10%. Exit 1 = no firma. | ADR-040 · Consejo 8/8 · DAY 134 |
| **IPW + uncertainty sampling (ADR-040)** | 5% exploración (P≈0.5). Ratio adaptativo [3%-10%]. | ADR-040 · Consejo 8/8 · DAY 134 |
| **CaptureBackend mínima (ISP)** | 5 métodos puros. EbpfBackend tiene métodos eBPF. main.cpp usa EbpfBackend directamente. | Consejo 5-2-1 · DAY 137 → Cerrado DAY 138 |
| **Variant B monohilo permanente** | libpcap no es thread-safe sobre mismo handle. zmq_sender_threads=1 hardcodeado, no configurable. | Consejo 8/8 · DAY 138 |
| **dontwait policy NDR** | Mejor perder paquete que bloquear loop captura. Exponer send_failures como métrica. | Consejo 8/8 · DAY 138 |
| **nftables transaccional para IRP** | nft -f atómico. Snapshot + rollback 300s. Fallback ip link down. iptables rechazado en Debian 12. | Consejo 8/8 · DAY 138 |
| **ODR es P0 bloqueante** | ODR violations en C++20 = UB. Bloqueante para cualquier tag posterior. | Consejo 8/8 · DAY 138 |
| **-Werror invariante permanente** | 0 warnings es invariante. Ningún merge sin grep -c warning: = 0. | Consejo 8/8 · DAY 140 |
| **Terceros deprecated: suprimir + doc** | APIs deprecated de terceros → suprimir por fichero + THIRDPARTY-MIGRATIONS.md. Nunca suprimir código propio. | Consejo 8/8 · DAY 140 |
| **[[maybe_unused]] en C++20** | Interfaces virtuales y código nuevo → [[maybe_unused]]. Stubs temporales → /*param*/ con DEBT. | Consejo 7/8 · DAY 140 |
| **Gate ODR pre-merge obligatorio** | make PROFILE=production all antes de merge a main. Jenkinsfile cuando haya servidor. | Consejo 8/8 · DAY 140 |
| **seL4 no diseñar ahora** | CaptureBackend (5 métodos) es reutilizable. Todo lo demás reescritura. YAGNI hasta equipo especializado. | Consejo 8/8 · DAY 138 |
| **seed-client-build dependencia explícita** | firewall y pipeline-build deben declarar seed-client-build. En VM limpia sin binarios previos el build falla silenciosamente. | DAY 141 |
| **Exclusión mutua Variant A/B** | Nunca simultáneas en el mismo hardware. Nivel 1: script bash via tmux (pre-FEDER). Nivel 2: robusto post-FEDER (DEBT-MUTEX-ROBUST-001). Lógica NO en binarios. | Consejo 8/8 · DAY 141-142 |
| **buffer_size_mb variable por diseño** | Permite trazar curva de optimización. pcap_create()+pcap_set_buffer_size() implementado DAY 142. | Consejo 8/8 · DAY 141 → Cerrado DAY 142 |
| **Warning classifier: grep/awk** | Script determinista. Un LLM no determinista no hace trabajo determinista. | Consejo 8/8 · DAY 141 |
| **auto_isolate: true por defecto** | El sistema protege sin configuración manual. Desactivar es acto explícito. | Consejo 8/8 + founder · DAY 142 |
| **IRP criterio multi-señal** | score >= 0.95 solo no es suficiente. FEDER: score AND event_type. Producción: señal más rica. | Consejo 8/8 + founder · DAY 142 |
| **fork()+execv() en IRP** | firewall-acl-agent nunca muere al disparar aislamiento. Operación atómica. | Consejo 8/8 · DAY 142 |
| **AppArmor enforce desde primer deploy** | Nuevos componentes: enforce desde el commit inicial. complain máximo 1 día en dev. | Consejo 8/8 · DAY 142 |
| **auto_isolate: false por defecto** | REEMPLAZA regla DAY 142. En hospitales, default false + WARNING. Activar es acto explícito. | Consejo 8/8 · DAY 143 |
| **SA_NOCLDWAIT para IRP** | fork()+execv() → sigaction SA_NOCLDWAIT. Kernel recoge hijos. Sin zombies. | Consejo 8/8 · DAY 143 |
| **/run/argus/irp/ para IRP** | Artefactos nftables fuera de /tmp. /run/ (volátil) + /var/lib/ (persistente). Falco vigila. | Consejo 8/8 · DAY 143 |
| **DEBT-PROTO-DETECTION-TYPES-001** | No ampliar enum sin datos MITRE reales. Sin datos no hay diseño. | Founder · DAY 143 |
| **IRP prob. conjunta multi-señal** | No topología por quirófano (inviable). Función de decisión con todas las señales disponibles + pesos. | Consejo 8/8 · DAY 143 |
| **etcd-server HA es deuda crítica** | Single-node etcd no es robusta. DEBT-ETCD-HA-QUORUM-001 obligatoria post-FEDER. | Founder · DAY 142 |

| **Open-core: un solo binario por arquitectura (DAY 150 — Consejo 8/8 + Founder)** | Plugin system como mecanismo de licencias. Community = seed-client. Enterprise = plugins firmados activados por licencia en Vault. Cero variantes de código. `ARGUS_VAULT_ENABLED` único separador compile-time. | DAY 150 |
| **ICryptoProvider interfaz abstracta (DAY 150 — Consejo 8/8)** | `SeedFileProvider` (community) y `VaultProvider` (enterprise) implementan la misma interfaz. Ningún componente ve `#ifdef` en lógica de negocio. El flag CMake solo controla qué `.cpp` se linka. | DAY 150 |
| **Migración por canal, no por componente (DAY 150 — Gemini/Consejo 8/8)** | ZeroMQ es bilateral. Si sniffer usa VaultProvider y ml-detector usa SeedFile, los keypairs derivados no coinciden y el canal se rompe. Migrar simultáneamente: etcd-server → sniffer+ml-detector → firewall-acl-agent → rag-ingester+rag-security. | DAY 150 |
| **TTL = ventana de renovación preferente (DAY 150 — Consejo 8/8)** | TTL no es fecha de muerte criptográfica. La clave expira solo por: revocación explícita firmada desde Vault, EMECAS, o tamper detection. Nunca por el paso del tiempo. | DAY 150 |
| **Firewall default-deny en EXTENDED_AUTONOMY (DAY 150 — Consejo 8/8 + Founder)** | Cuando Vault es inaccesible, el firewall-acl-agent pasa a bloquear todo tráfico nuevo. La pérdida de Vault es un indicador de ataque inminente, no una razón para relajar la defensa. | DAY 150 |
| **Reconciliación obligatoria post-Vault (DAY 150 — Consejo 8/8)** | Al recuperar conectividad con Vault, el nodo no vuelve a NORMAL automáticamente. Envía `key_version` actual. Vault responde: válida → NORMAL; revocada → nueva clave; no reconocida → EMECAS. | DAY 150 |
| **Cache cifrada obligatoria en prod (DAY 150 — Founder)** | Seed maestra en texto plano: JAMÁS. En producción, cache solo si filesystem cifrado (LUKS o equivalente). Sin cifrado de disco → Vault obligatorio en cada arranque. | DAY 150 |
| **MAC unicast como identidad primaria** | `HMAC-SHA256(K_pseudo, MAC)`. Jerarquía MAC→hostname→IP. `Host` vs `NetworkPresence`. MAC nunca sale del nodo. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Pseudonimización determinista K_pseudo** | HMAC-SHA256 con clave por instalación en Vault local. Coherencia temporal garantizada. Rotación es evento excepcional. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Paquete mensual edge→central** | Parquet ×2 + plugin firmado + metadatos. idempotency_key = firma Ed25519(batch_content). Estable a N reintentos. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Cola local batches pendientes (D9)** | `/var/spool/argus/batches/pending/`. Independiente de SQLite. Retención 90 días. FIFO. Backoff exponencial. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Neo4j DAG sin ciclos** | Patrón entidad persistente + episodio temporal. Sin PRECEDES materializado — ordenamiento por Episode.period ISO 8601. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Timestamps UTC epoch nanoseconds** | int64 UTC en Parquet. ISO 8601 con sufijo Z en JSON. Sin excepciones. system_clock en C++20, nunca steady_clock. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Vault jerarquía root+operativo** | Vault central = root of trust (wrapping keys). Vault local = operativo (K_pseudo, Ed25519, seeds). | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Flujo GDPR Art. 17** | Borrado via comando firmado Ed25519 desde instalación → DELETE en Neo4j → auditoría certificada inmutable. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **FailureAction=poweroff ELIMINADO (DAY 149 — Consejo 8/8)** | systemd NO apaga el host en fallo crypto. Pipeline offline + alerta CRITICAL. Host sigue vivo para diagnóstico forense. En infraestructura crítica, el host offline es peor que el NDR offline. | DAY 149 |
| **Edge nodes autónomos (DAY 149 — Consejo 8/8)** | Los nodos edge siguen operando si el servidor central (Jenkins/Vault) está caído. Keypair en memoria, ZeroMQ abierto. Servidor central gestiona lifecycle y rotación pero no bloquea protección activa. Cache tmpfs TTL=72h prod. | DAY 149 |
| **EMECAS PROFILE=production en merge a main con código (DAY 149 — Founder)** | Cada merge a main que incluya código C++20 (no solo infra/docs) requiere `vagrant destroy -f && vagrant up && make bootstrap && make PROFILE=production test-all`. Registrado como recordatorio para DAY 150+ cuando se implemente vault_client. | DAY 149 |
| **SOS webhook desde edge (DAY 149 — Founder)** | Cada despliegue en cliente configura webhook de alerta (Discord/Telegram/email) que dispara desde el edge directamente. Independiente del servidor central. Escalado por TTL cache restante. Sin internet = problema físico que trasciende el software. | DAY 149 |
| **ADR-035 OQ-2 CERRADA** | Topología etcd parametrizada por tamaño de instalación. Single-node aceptado en instalaciones pequeñas con SPOF documentado. | ADR-0043 v4 · cierra ADR-035 OQ-2 · DAY 147 |
| **ADR-038 §Anonimización SUPERSEDIDA** | Rotating salt → HMAC determinista (ADR-0043 D2-D3). BitTorrent → ZeroMQ (ADR-0043 D4). Resto ADR-038 vigente. | ADR-0043 v4 · DAY 147 |
---

## 📊 Estado global del proyecto

```
Foundation + Thread-Safety:             100% ✅
HMAC Infrastructure:                    100% ✅
F1=0.9985 (CTU-13 Neris):              100% ✅
CryptoTransport (HKDF+AEAD):            100% ✅
ADR-025 Plugin Integrity (Ed25519):     100% ✅
TEST-INTEG-4a/4b/4c/4d/4e + SIGN:      100% ✅
arXiv:2604.04952 PUBLICADO:             100% ✅
PHASE 3 v0.4.0:                         100% ✅
PHASE 4 v0.5.0-preprod:                 100% ✅
ADR-026 XGBoost Prec=0.9945:            100% ✅
ADR-037 safe_path v0.5.1-hardened:      100% ✅  DAY 124
DEBT-PROD-APPARMOR-COMPILER-BLOCK-001:  100% ✅  DAY 133
DEBT-PROD-FALCO-EXOTIC-PATHS-001:       100% ✅  DAY 133
DEBT-PROD-FS-MINIMIZATION-001:           60% 🟡  DAY 133 (parcial)
vagrant/hardened-x86/ completo:         100% ✅  DAY 133
DEBT-PAPER-FUZZING-METRICS-001:         100% ✅  DAY 134
DEBT-KERNEL-COMPAT-001:                 100% ✅  DAY 134
ADR-040 ML Retraining Contract (def.):  100% ✅  DAY 134
ADR-041 HW Acceptance Metrics (def.):   100% ✅  DAY 134
make hardened-full EMECAS:              100% ✅  DAY 135
DEBT-PROD-APT-SOURCES-INTEGRITY-001:    100% ✅  DAY 135
DEBT-CONFIDENCE-SCORE-001:              100% ✅  DAY 135
arXiv replace v15→v18:                  100% ✅  DAY 135
v0.6.0-hardened-variant-a mergeado:     100% ✅  DAY 136
docs/KNOWN-DEBTS-v0.6.md:              100% ✅  DAY 136 (actualizado DAY 138)
DEBT-CAPTURE-BACKEND-ISP-001:           100% ✅  DAY 138
DEBT-VARIANT-B-PCAP-IMPL-001:          100% ✅  DAY 138 (8/8 tests)
DEBT-COMPILER-WARNINGS-CLEANUP-001:    100% ✅  DAY 144 (ODR LTO production gate PASSED)
ADR-029 Variant A vs B x86 (DAY 145):  100% ✅  DAY 145 (experimento comparativo completo)
Experimento Suricata vs aRGus (DAY 146):  100% ✅  DAY 146 (0 alertas ET Open vs F1=0.9985)
Paper Draft v19:                        100% ✅  DAY 145 (§6 ADR-029 + §10.9 + §11.17 + §12)
Paper Draft v20:                        100% ✅  DAY 146 (§8.13 Suricata + tab:comparison empírico)
Paper Draft v21:                        100% ✅  DAY 147 (§8.13 hallazgos reales + HTTP C2 + Springer 2023)
Paper Draft v22:                        100% ✅  DAY 147 (§8.14 tres paradigmas + abstract + conclusion + §13)
Paper Draft v23:                        100% ✅  DAY 148 (offline validation + §10 Future Work + abstract complementariedad)
arXiv replace v3 (v19→v23):            100% ✅  DAY 148 (submit/7576269)
Experimento Suricata offline (DAY 148): 100% ✅  DAY 148 (0 ET signatures, 323,154 pkts, irrefutable)
Experimento Zeek 8.1.2 (DAY 147):     100% ✅  DAY 147 (offline, 3 runs determinísticos, parse_results_zeek_v2.py)
Bug fix pipeline-status pgrep:          100% ✅  DAY 147 (commit 42c04b06)
Bootstrap múltiple x86 A/B:            100% ✅  DAY 145 (bootstrap-x86-ebpf + bootstrap-x86-libpcap)
feature/variant-b-libpcap mergeado:    100% ✅  DAY 145 → v0.7.0-variant-b
DEBT-PCAP-CALLBACK-LIFETIME-DOC-001:   100% ✅  DAY 141
DEBT-VARIANT-B-CONFIG-001:             100% ✅  DAY 141 (9/9 tests, 0 warnings)
Bug Makefile seed-client-build:         100% ✅  DAY 141 (commit 63a37d9d)
DEBT-VARIANT-B-BUFFER-SIZE-001:        100% ✅  DAY 142 (commit 7c4dba58)
DEBT-VARIANT-B-MUTEX-001 (Nivel 1):    100% ✅  DAY 142 (commit 9458a90d)
DEBT-IRP-NFTABLES-001:                 100% ✅  DAY 143 — CERRADA (sesión 3/3 completa)
DEBT-IRP-SIGCHLD-001:                 100% ✅  DAY 144 (SA_NOCLDWAIT + test NoZombiesAfterNForks)
DEBT-IRP-AUTOISO-FALSE-001:           100% ✅  DAY 144 (única fuente verdad + 5 tests)
DEBT-IRP-BACKUP-DIR-001:             100% ✅  DAY 144 (/run/argus/irp/ + AppArmor)
DEBT-IRP-TMPFILES-001:               100% ✅  DAY 146 (tmpfiles.d + provision.sh)
DEBT-IRP-IPSET-TMP-001:               100% ✅  DAY 146 (ipset_wrapper /run/argus/irp/)
DEBT-EMECAS-VERIFICATION-001:          100% ✅  DAY 146 (README blockquote EMECAS)
DEBT-IRP-FLOAT-TYPES-001:              100% ✅  DAY 148 — CERRADA (float consistente, parche IEEE 754 eliminado)
DEBT-IRP-PROB-CONJUNTA-001:             0% ⏳  P1 post-FEDER (función prob. conjunta multi-señal)
DEBT-PROTO-DETECTION-TYPES-001:         0% ⏳  Baja post-MITRE/CTF (ampliar enum DetectionType)
DEBT-ETCD-HA-QUORUM-001:                0% ⏳  P0 post-FEDER (OBLIGATORIO)
DEBT-MUTEX-ROBUST-001:                   0% ⏳  post-FEDER (tras HA etcd)
DEBT-IRP-MULTI-SIGNAL-001:              0% ⏳  post-FEDER
DEBT-IRP-LAST-KNOWN-GOOD-001:           0% ⏳  post-FEDER
DEBT-IRP-QUEUE-PROCESSOR-001:           0% ⏳  post-merge
BACKLOG-PAPER-METHODOLOGY-001:             0% ⏳  post-FEDER (paper cs.SE TDH+Consejo)
BACKLOG-DEPLOY-CALCULATOR-001:             0% ⏳  cuando llegue hardware físico
BACKLOG-HARDWARE-FEDER-001:               0% ⏳  coordinando con Andrés (RPi+N100+switch)
BACKLOG-ZMQ-TUNING-001:                  0% ⏳  pre-FEDER
BACKLOG-BENCHMARK-CAPACITY-001:           0% ⏳  FEDER Year 1 Deliverable
BACKLOG-BUILD-WARNING-CLASSIFIER-001:    0% ⏳  post-FEDER (grep/awk script)
DEBT-LLAMA-API-UPGRADE-001:              0% ⏳  post-FEDER (salvo CVE)
DEBT-ODR-CI-GATE-001:                    0% ⏳  requiere servidor CI/CD
DEBT-GENERATED-CODE-CI-001:              0% ⏳  requiere servidor CI/CD
DEBT-MAYBE-UNUSED-MIGRATION-001:         0% ⏳  cosmético, post deudas P0
DEBT-EMECAS-AUTOMATION-001:              0% ⏳  post deudas P0
DEBT-JENKINS-SEED-DISTRIBUTION-001:      0% ⏳  pre-FEDER
DEBT-CRYPTO-MATERIAL-STORAGE-001:      100% ✅  DAY 149 (Vault dev mode + K_pseudo prototipo validado)
DEBT-KEY-SEPARATION-001:                 0% ⏳  post-FEDER
DEBT-ADR040-001..012:                    0% ⏳  post-FEDER Año 1
DEBT-ADR041-001..006:                    0% ⏳  pre-FEDER
ADR-0043 v4 Memoria Episódica Distribuida:  100% ✅  DAY 147 (Consejo 8/8 · ACEPTADO)
ADR-035 OQ-2 cerrada (etcd topología):     100% ✅  DAY 147 (referenciada en ADR-0043 D6)
DEBT-PARQUET-SCHEMA-001:                   100% ✅  DAY 149 (schema Arrow v1.0, 207K filas, 11-12x, roundtrip PASSED)
DEBT-VAULT-FEDERATION-001:                   0% ⏳  P1 pre-FEDER (offboarding instalaciones GDPR)
DEBT-LEGAL-DATA-RETENTION-001:               0% ⏳  P1 pre-FEDER (dictamen jurídico retención datos)
DEBT-KPSEUDO-ROTATION-MIGRATION-001:         0% ⏳  P1 pre-FEDER (migración Neo4j tras rotación K_pseudo)
DEBT-GDPR-ERASURE-001:                       0% ⏳  P1 pre-FEDER (flujo derecho al olvido Art. 17)
DEBT-KPSEUDO-HKDF-HIERARCHY-001:             0% ⏳  P3 post-FEDER (jerarquía HKDF para K_pseudo)
DEBT-VAULT-PROVISION-PROD-001:             100% ✅  DAY 149 (Vault/Ansible/Jinja2/Jenkins en Vagrant)
ADR-044 CI/CD Crypto Pipeline:             100% ✅  DAY 149 (definido, Consejo 8/8, impl DAY 150+)
ICryptoProvider + SeedFileProvider + VaultProvider: 100% ✅  DAY 151 (factoría, tests, etcd STEP 0)
DEBT-BOOTSTRAP-STATUS-SIGNATURE-001:      0% ⏳  P1 pre-FEDER (bootstrap status sin firma)
DEBT-AUTONOMY-STATE-PERSISTENCE-001:      0% ⏳  P1 (estado autonomía sin persistencia firmada)
DEBT-AUTONOMY-CLOCK-INJECTION-001:        0% ⏳  P1 (clock no inyectable)
DEBT-FIREWALL-DENY-SELECTIVE-001:          0% ⏳  P0 DAY 155 (regla actual rompe hospitales)
DEBT-AUTONOMY-ZMQ-EVENTS-001:             0% ⏳  P1 DAY 155 (ZMQ pub/sub directo)
ADR-045 VaultClient Decomposition:      100% ✅  CERRADA DAY 154 — v0.8.0-adr045
Ansible+Jinja2 deploy_configs pipeline:    100% ✅  DAY 149 (3 templates, playbook, 9 OK 0 failed)
Paper Abstract v24:                        100% ✅  DAY 149 (architecturally complementary by design)
DEBT-PARQUET-TIMESTAMP-NS-001:               0% ⏳  P2 (firewall ms→ns en origen)
DEBT-VAULT-ENTROPY-MIXING-001:               0% ⏳  P2 post-FEDER (mezcla entropy externa)
DEBT-VAULT-HA-001:                           0% ⏳  P1 post-FEDER (Vault HA raft)
DEBT-CRYPTO-STAMPEDE-001:                    0% ⏳  P1 (jitter vault_client)
DEBT-CRYPTO-AUDIT-FINGERPRINT-001:           0% ⏳  P1 (fingerprint etcd)
DEBT-CRYPTO-HEARTBEAT-001:                   0% ⏳  P1 (heartbeat etcd)
DEBT-ALERTING-EDGE-SOS-001:                  0% ⏳  P1 pre-FEDER (SOS webhook edge)
ADR-044 provision_crypto.sh:                100% ✅  DAY 150 (Vault KV v1, familias A/B/C + etcd, idempotente)
ADR-044 vault_client.h/.cpp:               100% ✅  DAY 150 (derivación D12/D13, jitter, cache, 5/5 tests)
ADR-044 Jenkinsfile Provision Crypto:      100% ✅  DAY 150 (stage separado, condicional, artifact)
DEBT-CRYPTO-STAMPEDE-001:                  100% ✅  DAY 150 (jitter implementado en vault_client.cpp)
Decisión open-core plugin system:          100% ✅  DAY 150 (Consejo 8/8 + Founder)
Decisión autonomía extendida Opción D:     100% ✅  DAY 150 (Consejo 8/8)
DEBT-CRYPTO-AUTONOMY-001:                    0% ⏳  P1 pre-FEDER (máquina de estados EXTENDED_AUTONOMY)
DEBT-FIREWALL-AUTONOMY-MODE-001:           100% ✅  CERRADA DAY 154 (FirewallAutonomyReactor)
DEBT-CRYPTO-REVOCATION-LOCAL-001:            0% ⏳  P1 post-FEDER (revocación offline)
DEBT-CRYPTO-RECONCILIATION-001:              0% ⏳  P1 pre-FEDER (handshake post-Vault)
DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001:       0% ⏳  P1 pre-FEDER (cache cifrada en prod edge)
DEBT-EMECAS-DUAL-COMPILATION-001:            0% ⏳  P1 (CI compila ON+OFF)
DEBT-LICENSE-VAULT-001:                      0% ⏳  P2 post-FEDER (servidor licencias en Vault)
DEBT-PLUGIN-ENTERPRISE-001:                  0% ⏳  P2 post-FEDER (definir plugins enterprise)
ADR-031 aRGus-seL4:                      0% ⏳  branch independiente
```

---

## 📝 Notas del Consejo de Sabios — ADR-0043 v4 (8/8) · DAY 147

> "ADR-0043 v4 — APROBADO UNÁNIMEMENTE. Cuatro versiones, tres rondas de revisión del Consejo, ocho modelos.
>
> **Decisiones clave:**
> - Identidad por MAC unicast con jerarquía de fallback (MAC→hostname→IP). DHCP no rompe la coherencia del grafo.
> - Pseudonimización determinista HMAC-SHA256 con K_pseudo por instalación en Vault local. La MAC nunca abandona el nodo.
> - idempotency_key = firma Ed25519(batch_content). Estable a través de cualquier número de reintentos.
> - Cola local /var/spool/argus/batches/ independiente de SQLite. Retención 90 días. OQ-1 convertida en D9.
> - DAG Neo4j sin PRECEDES materializado. Episode.period ISO 8601 como eje temporal.
> - Timestamps UTC epoch nanoseconds en Parquet. system_clock en C++20.
> - ADR-035 OQ-2 cerrada: topología etcd parametrizable por tamaño de instalación.
> - ADR-038 §Anonimización y §Canal de distribución supersedidos.
>
> **Deudas P0/P1 pre-FEDER registradas:** DEBT-PARQUET-SCHEMA-001 (P0 bloqueante), DEBT-VAULT-FEDERATION-001, DEBT-LEGAL-DATA-RETENTION-001, DEBT-KPSEUDO-ROTATION-MIGRATION-001, DEBT-GDPR-ERASURE-001.
>
> **Próximo paso:** examinar CSVs reales de ml-detector y firewall-acl-agent en entorno Vagrant para cerrar DEBT-PARQUET-SCHEMA-001. Sin schema real no hay contrato de interfaz.
>
> 'La memoria distribuida no es solo almacenamiento: es un pacto de confianza temporal entre el edge y el centro.' — Qwen"
> — Consejo de Sabios (8/8) · DAY 147
## 📝 Notas del Consejo de Sabios — DAY 147 (8/8)

> "DAY 147 — Experimento de tres paradigmas completado. CTU-13 Neris, condiciones idénticas.
>
> **Resultados:** Suricata 6.0.10: F1=0.000 (sin firmas, comportamiento correcto). Zeek 8.1.2 (default): F1=0.042, Precision=1.000, 14 TP (SSL::Invalid_Server_Cert). aRGus NDR: F1=0.9985, Recall=1.000, 646 TP.
>
> **Consenso P1 — Validez metodológica (7/8):** El modo offline de Zeek es estándar aceptado para pcaps históricos. La asimetría favorece a Zeek (100% paquetes vs Suricata live con 2,630 dropped). Declarar explícitamente en el paper — ya está hecho. Kimi (1/8): ejecutar `suricata -r neris.pcap` offline para blindar completamente la comparativa. Acción: P0 bloqueante DAY 148.
>
> **Consenso P2 — Framing científico (8/8):** Framing correcto y publicable. Refinamiento: usar 'measurement layer' (Zeek) vs 'classification layer' (aRGus) — más preciso que observabilidad/detección (Claude). ChatGPT: 'Observability does not imply classification' como frase del abstract. Kimi: elevar de benchmark a contribución taxonómica (arquitecturas de decisión, no ranking de rendimiento). Qwen: 'registrar el mundo vs juzgarlo automáticamente'. El experimento de tres vías es el único que produce el hallazgo — con dos sistemas sería invisible.
>
> **Consenso P3 — Zeek Phase 2 (7/8 → future work):** Phase 1 out-of-the-box suficiente para arXiv. Phase 2 con Intel framework, threat feeds, detect-botnets.zeek queda como future work explícito en §10. Gemini: feeds de 2026 no encontrarían nada de 2011 — Phase 2 reintroduce el paradigma de firmas. DeepSeek: si hay tiempo, un solo script IRC (detect-botnets.zeek) cierra el flanco del revisor.
>
> **Hallazgo adicional DAY 147:** Búsqueda ruleset ET Open agosto 2011 — no encontrado en fuentes públicas (Wayback Machine, GitHub ET, SecurityOnion, ossim). Neris escenario 42 usa HTTP C2 (no IRC según README), pero weird.log confirma IRC presente (irc_invalid_command:30). El paradigma gap es más profundo que signature aging solo.
>
> **Acciones DAY 148:**
> (1) `suricata -r neris.pcap` — 10 minutos, blinda la comparativa.
> (2) Refinar §8.14: measurement/classification layer.
> (3) §10 Future Work: Zeek Phase 2 con detect-botnets.zeek mencionado.
> (4) DEBT-IRP-FLOAT-TYPES-001 — aplazada de DAY 147.
> (5) Decisión arXiv replace v22.
>
> 'No estamos comparando herramientas — estamos comparando filosofías: registrar el mundo vs juzgarlo automáticamente.' — Qwen · DAY 147"
> — Consejo de Sabios (8/8) · DAY 147

## 📝 Notas del Consejo de Sabios — DAY 146 (8/8)

> "DAY 146 — Experimento comparativo Suricata 6.0.10 (50,010 reglas ET Open Mayo 2026) vs aRGus NDR sobre CTU-13 Neris 2011. Condiciones idénticas de hardware, VM, dataset y topología de red.
>
> **Resultado:** Suricata: 0 alertas. aRGus: F1=0.9985, Recall=1.0000.
>
> **Interpretación unánime (8/8):** No es un fallo de Suricata. El motor procesó el tráfico correctamente. Las reglas ET Open 2026 no cubren el botnet Neris 2011 porque esas firmas han sido retiradas. El resultado es el comportamiento esperado de un IDS de firmas cuando no existe regla para la amenaza.
>
> **Significado científico:** Primera comparativa directa publicada entre NDR ML embebido e IDS de firmas en producción sobre el mismo dataset. Corrobora Sommer & Paxson (2010): firmas = conocimiento previo necesario; comportamiento = generalización temporal. aRGus fue entrenado con datos sintéticos que modelan comportamiento, no con CTU-13 directamente.
>
> **Consenso sobre narrativa:** Los sistemas son complementarios, no competidores. Un despliegue hospitalario óptimo combinaría ambos. No atacar a Suricata en el paper.
>
> **Pendiente:** buscar ruleset ET Open histórico (~agosto 2011) para separar 'firma nunca existió' de 'firma retirada'. Ambos resultados son científicamente válidos.
>
> 4 deudas técnicas cerradas. EMECAS verde. v0.7.1-day146 tagueado.
>
> 'El cero de Suricata no es un error — es una coordenada en el mapa de la evolución de las amenazas.' — Qwen · adaptado"
> — Consejo de Sabios (8/8) · DAY 146


## 📝 Notas del Consejo de Sabios — DAY 144 (8/8)
## 📝 Notas del Consejo de Sabios — DAY 145 (8/8)

> "DAY 145 — Primer experimento comparativo ADR-029 Variant A (eBPF) vs Variant B (libpcap) en x86-64 VirtualBox. Resultado contraintuitivo: libpcap ~2× throughput que eBPF a 50/100 Mbps. Causa identificada: virtio no expone driver XDP nativo, eBPF cae a modo SKB genérico. En hardware físico con NIC XDP nativa, se espera inversión.
>
> **Sobre los 2,630 failed packets:** artefacto fijo del pcap CTU-13 Neris. Frames jumbo que superan MTU VirtualBox (errno=90 EMSGSIZE). Conteo idéntico en los 6 runs confirma origen en el fichero, no en el pipeline. El sniffer nunca ve esos frames — no son pérdidas de captura. Documentado en README, BACKLOG y paper v19 para evitar confusión futura.
>
> **Equivalencia funcional A/B confirmada:** ambas variantes procesan el corpus Neris completo sin errores de pipeline. La comparación de rendimiento real queda pendiente de hardware físico — que es exactamente el argumento FEDER.
>
> **Bootstrap múltiple:** `bootstrap-x86-ebpf` (Variant A, referencia) y `bootstrap-x86-libpcap` (Variant B). `bootstrap` queda como alias de A — el EMECAS habitual no cambia. `pipeline-status` distingue variante activa e impide invariant violation.
>
> **Paper v19:** §6 nueva subsección con tabla comparativa, interpretación virtio/SKB, y valor científico. El hallazgo es publicable tal cual: el delta A/B depende críticamente del hardware subyacente.
>
> 'Hacer ciencia es esto: observar algo contraintuitivo, identificar la causa, y convertirlo en evidencia empírica para el siguiente argumento.' — Founder DAY 145"
> — Consejo de Sabios (8/8) · DAY 145



> "DAY 144 — Tres deudas P0 IRP cerradas en una sesión de madrugada (04:00-08:00). Gate ODR production superado tras corregir tres categorías de violaciones reales bajo `-flto -Werror`.
>
> **DEBT-IRP-SIGCHLD-001 (8/8):** `SA_NOCLDWAIT` en `setup_signal_handlers()`. El kernel recoge hijos muertos automáticamente. `SigchldTest.NoZombiesAfterNForks` — 20 forks, 500ms, cero zombies. PASSED.
>
> **DEBT-IRP-AUTOISO-FALSE-001 (8/8 unánime):** `isolate.json` es la única fuente de verdad. Campo `auto_isolate` obligatorio. Fallo ruidoso si falta. Sin fallback silencioso. Un FP sobre ventilador mecánico es un evento clínico, no un bug. 5 tests nuevos PASSED.
>
> **DEBT-IRP-BACKUP-DIR-001 (8/8 unánime):** `/tmp` eliminado de la ruta IRP. `/run/argus/irp/` (tmpfs, 0700). AppArmor actualizado. provision.sh actualizado. Dry-run PASSED.
>
> **Gate ODR (confirmación empírica):** `make PROFILE=production all` encontró 3 ODR violations reales que el build debug nunca habría detectado: (1) `tree_0[]`..`tree_99[]` con tipos distintos en dos headers incluidos en distintas unidades de compilación → anonymous namespace; (2) protobuf stale de noviembre 2025 en `src/protobuf/` → eliminado (40k líneas); (3) `assert()` desactivado por `-DNDEBUG` en tests → `-UNDEBUG` en targets de test.
>
> **Consenso sobre experimento comparativo (P4):** No es una competición. Es una caracterización de paradigmas complementarios. La afirmación publicable es: 'Los sistemas basados en firmas y los basados en comportamiento son complementarios. Un despliegue hospitalario óptimo combinaría ambos.' aRGus como cooperador, no como sustituto.
>
> **Consenso P3 multi-señal:** Qwen propone acumulador de evidencia con decadencia exponencial — determinista, sin reentrenamiento, auditable, estándar NIST/MITRE. Superior a regresión logística para infraestructura crítica. Adoptado.
>
> 65/65 tests verdes. Gate ODR: ALL COMPONENTS BUILT [production].
>
> 'El gate ODR no es burocracia — es la única herramienta que ve lo que el compilador diario no ve.' — ChatGPT"
> — Consejo de Sabios (8/8) · DAY 144

## 📝 Notas del Consejo de Sabios — DAY 143 (8/8)

> "DAY 143 — DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA. IRP completo: config → disparo → fork()+execv() → AppArmor enforce → 12 tests. Bug IEEE 754 encontrado por tests — `float 0.95f → double 0.9499...` — corregido. 7/7 perfiles AppArmor enforce en hardened VM.
>
> Cinco deudas nuevas registradas tras Consejo:
>
> **DEBT-IRP-SIGCHLD-001 (8/8 unánime):** SA_NOCLDWAIT — el kernel recoge hijos muertos automáticamente. Sin zombies en ataques persistentes. P0 pre-merge.
>
> **DEBT-IRP-AUTOISO-FALSE-001 (8/8 unánime):** auto_isolate: false por defecto. La regla DAY 142 queda reemplazada. En hospitales, la automatización sin onboarding explícito es un riesgo de vida. P0 pre-merge.
>
> **DEBT-IRP-BACKUP-DIR-001 (8/8 unánime):** /tmp es peligroso para artefactos IRP. Migrar a /run/argus/irp/ (volátil) + /var/lib/argus/irp/ (persistente). Falco vigila ambas rutas. P0 pre-merge.
>
> **DEBT-IRP-FLOAT-TYPES-001 (dividido):** Mezcla float/double en lógica de decisión es un error de diseño. La tolerancia 1e-6 es un parche. Unificar tipos. Investigar qué produce exactamente el ml-detector antes de decidir el tipo correcto. P1 pre-FEDER.
>
> **DEBT-IRP-PROB-CONJUNTA-001 (8/8):** Dos señales AND no son suficientes para hospital. Función probabilidad conjunta sobre todas las señales disponibles — explicable, auditable, publicable. No implementar topología por quirófano (Gemini) — inviable a escala global. P1 post-FEDER.
>
> 'Un escudo que corta sin medir no protege: amputa.' — Qwen"
> — Consejo de Sabios (8/8) · DAY 143


## 📝 Notas del Consejo de Sabios — DAY 142 (8/8)

> "DAY 142 — Seis commits. Tres DEBTs cerradas. El IRP pasa de arquitectura a sistema ejecutable y verificable.
>
> P1 (8/8 + founder): Umbral único `score >= 0.95` para FEDER, pero nunca como señal única. Mínimo dos condiciones AND: score + event_type. En entornos hospitalarios, equipos médicos conectados a intranet/DMZ (monitores de quirófano, bombas de infusión) son activos que `firewall-acl-agent` debe proteger — un falso positivo que los aísle es inaceptable. La señal debe ser explicable, auditable y multi-componente. Platt scaling registrado como sub-tarea de DEBT-ADR040-002.
>
> P2 (8/8): `fork()+execv()` obligatorio. El firewall-acl-agent nunca puede morir durante un incidente. Es el único componente que puede registrar evidencia y ejecutar rollback. `FD_CLOEXEC` en descriptores heredados. `prctl(PR_SET_PDEATHSIG, SIGTERM)` en el hijo.
>
> P3 (8/8): AppArmor `enforce` desde el primer deploy. Perfiles aportados por Gemini y Kimi para combinar en sesión 3.
>
> P4 (8/8): Diseño actual de rollback correcto para FEDER. `DEBT-IRP-LAST-KNOWN-GOOD-001` registrada post-FEDER.
>
> Founder: el mutex via tmux es provisional — `DEBT-MUTEX-ROBUST-001` post-FEDER. La raíz del problema es etcd single-node — `DEBT-ETCD-HA-QUORUM-001` es deuda crítica obligatoria, no opcional. Un sistema de coordinación que depende de una única fuente de verdad que puede caer no es robusto en producción hospitalaria.
>
> 'auto_isolate: true por defecto. Instalar y funcionar. Un hospital que no toca la configuración debe estar protegido.' — Founder
>
> 'El agente de firewall debe sobrevivir al aislamiento. Un agente muerto durante un ataque activo es exactamente lo que el atacante busca.' — Claude, Grok, DeepSeek, Gemini, Kimi, Mistral, Qwen, ChatGPT (8/8)"
> — Consejo de Sabios (8/8) · DAY 142

---

## 📝 Notas del Consejo de Sabios — DAY 141 (8/8)

> "DAY 141 — Bug Makefile seed-client-build cerrado. DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 cerrado. DEBT-VARIANT-B-CONFIG-001 cerrado — sniffer-libpcap.json propio + main_libpcap.cpp config-driven. 9/9 tests PASSED. 0 warnings. Emails FEDER enviados a Andrés Caro Lindo.
>
> Q1 (8/8 + founder): Exclusión mutua obligatoria. DEBT-VARIANT-B-MUTEX-001 registrada. Nivel 1 via script bash/python en Makefile, pre-FEDER. La lógica de detección NO entra en los binarios.
>
> Q2 (8/8 + founder): buffer_size_mb pre-FEDER obligatorio. Variable por diseño — script de barrido paramétrico para trazar curva de optimización.
>
> Q3 (8/8 + founder): Script grep/awk determinista para clasificar warnings de build.
>
> 'buffer_size_mb no es una opción de confort — es una variable experimental. Sin ella, el benchmark ARM64 mide el default del kernel, no el hardware.' — Claude"
> — Consejo de Sabios (8/8) · DAY 141

---

## 📝 Notas del Consejo de Sabios — DAY 140 (8/8)

> "DAY 140 — 192 → 0 warnings. `-Werror` activo como invariante permanente. ODR limpio con LTO."
> — Consejo de Sabios (8/8) · DAY 140

---

## 📝 Notas del Consejo de Sabios — DAY 138 (8/8)

> "DAY 138 — ISP cerrado. Pipeline Variant B completo. ODR P0 bloqueante confirmado."
> — Consejo de Sabios (8/8) · DAY 138

---

## 📝 Notas del Consejo de Sabios — DAY 136 (8/8)

> "DAY 136 — v0.6.0-hardened-variant-a mergeado. DEBT-IRP-NFTABLES-001 es P0 pre-FEDER. argus-network-isolate inexistente = fail catastrófico en demo."
> — Consejo de Sabios (8/8) · DAY 136

---

## 📝 Notas del Consejo de Sabios — DAY 134 (8/8)

> "ADR-040 + ADR-041: contratos de calidad ML y métricas de aceptación hardware. Walk-forward obligatorio. Golden set inmutable. Temperatura ARM ≤75°C gate no negociable."
> — Consejo de Sabios (8/8) · DAY 134

---

## 📝 Notas del Consejo de Sabios — DAY 133 (8/8)

> "Transición de 'diseño correcto' a 'comportamiento real verificable'. cap_bpf. AppArmor 6/6. 'Un escudo que no se prueba contra el ataque real es un escudo de teatro.' — Qwen"
> — Consejo de Sabios (8/8) · DAY 133

---

## 🧬 HIPÓTESIS CENTRAL — Inmunidad Global Adaptativa

**Formulada:** DAY 128 | **Estado:** Pendiente demostración (DEBT-PENTESTER-LOOP-001)

Un sistema con ACRL converge hacia cobertura de técnicas ATT&CK en tiempo polinomial. Un sistema estático no converge nunca.

---

*DAY 154 — 16 Mayo 2026 · main @ v0.8.0-adr045*
*"Via Appia Quality — Un escudo que aprende de su propia sombra."*




## 📝 Notas del Consejo de Sabios — DAY 154 (8/8)

> "DAY 154 — ADR-045 VaultClient decomposition completa. DEBT-FIREWALL-AUTONOMY-MODE-001 cerrada.
>
> **Hitos técnicos:**
> `ICryptoDeriver` + `HkdfCryptoDeriver`: 6 tests (determinismo, aislamiento family/index, seed inválido → nullopt, fingerprint).
> `IEtcdRegistrar` + `StubEtcdRegistrar`: 4 tests. VaultClient por composición completa (4º ctor). 7 tests common/.
> `FirewallAutonomyReactor`: AUTONOMOUS/DEGRADED → default-deny, NORMAL → lift. Executor inyectable. 6 tests. 48/48 firewall tests.
> EMECAS: bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅.
>
> **Consenso P1 — ZMQ directo (7/8 + Founder):**
> No polling como mecanismo principal. `TransitionCallback` ya definido en `crypto_autonomy.h` — el cableado es mínimo. Latencia 30s inaceptable en entorno ransomware activo. Añadir polling reconciliador 60-120s solo como safety net. Topic: `argus.crypto.autonomy`. Transport: `inproc://` si mismo proceso, `ipc://` si procesos separados. ChatGPT: 'Polling → race windows → comportamiento no determinista → debugging infernal en fail-closed systems.'
>
> **Consenso P2 — Default-deny SELECTIVO (8/8 UNÁNIME):**
> La regla actual `-I INPUT 1 -j DROP` es INCORRECTA para hospitales. Eleva a P0 DAY 155.
> Kimi: 'Un `vagrant up` en un laptop no sufre. Un hospital sí.' DROP en posición 1 rompe loopback → IPC interno del propio NDR queda ciego. Orden correcto: lo → ESTABLISHED → RFC1918 → DROP. Subnets whitelist configurables vía JSON.
>
> **Consenso P3 — HWM primero (8/8):**
> Sin HWM explícito, benchmarks no son reproducibles. Throughput alto con 50% drops silenciosos es una mentira. Medir tres estados: steady, failure, recovery.
>
> **Consenso P4 — ISP después (8/8):**
> `DEBT-CAPTURE-BACKEND-ISP-001` espera a post-benchmark. Reactor con señal real es P0 funcional; ISP es P2 de calidad.
>
> **ChatGPT — transición arquitectónica:**
> 'El sistema ya no es solo un NDR. Empieza a comportarse como una plataforma resiliente distribuida. Propagación de estado, reconciliación, persistencia, backpressure y recovery semantics son ahora más importantes que añadir features nuevas.'
>
> **Nueva deuda registrada:**
> `DEBT-FIREWALL-DENY-SELECTIVE-001` (P0, DAY 155): regla actual puede paralizar hospital en autonomía.
>
> 'No estamos comparando herramientas — estamos construyendo el sistema que protege a los que no tienen escudo.' — Founder · DAY 154"
> — Consejo de Sabios (8/8) · DAY 154 · v0.8.0-adr045

## 📝 Notas del Consejo de Sabios — DAY 151 (8/8)

> "DAY 151 — ICryptoProvider completa. etcd-server STEP 0 funcionando. ADR-045 aprobado.
>
> **Consenso Q1 — Prioridad DAY 152 (8/8):** Opción A — máquina de estados primero.
> `CryptoAutonomyStateMachine` es el núcleo de la propuesta de valor para infraestructura crítica.
> Sin ella, `ICryptoProvider` es una abstracción elegante sin comportamiento de resiliencia.
> `DEBT-EMECAS-DUAL-COMPILATION-001` es deuda de calidad, no de funcionalidad — DAY 153.
>
> **Consenso Q2 — Clase separada (8/8):** Sí, `CryptoAutonomyStateMachine` extraída.
> `VaultClient` ya tiene seis responsabilidades. La séptima la convierte en inmantenible.
> Founder amplía: VaultClient por composición completa — ADR-045 aprobado.
> `IVaultTransport`, `ICacheManager`, `IEtcdRegistrar`, `ICryptoDeriver`, `IJitterStrategy`.
> Independencia de proveedor: hoy Vault, mañana cualquier backend, pasado el nuestro propio.
>
> **Consenso Q3 — Exponer en ICryptoProvider (6/8 sí, 2/8 con matiz):**
> `get_operational_mode()` expuesto con default `NORMAL`. Community y enterprise tienen
> el mismo contrato. `SeedFileProvider` siempre retorna `NORMAL`. Nombre recomendado por Kimi:
> `OperationalMode` (`NORMAL`, `AUTONOMOUS`, `RECONCILING`, `DEGRADED`).
>
> **Principio rector adoptado (Founder, DAY 151):**
> Calidad sobre fechas. No hay deadline duro para FEDER. Los datasets se generan cuando
> el pipeline esté listo. La calidad no se negocia. Plan MITRE/CTF en backlog, después de
> infraestructura consolidada y primer plugin enterprise.
>
> **Nuevas deudas Consejo:**
> `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` (Claude+Grok, P1): bootstrap status sin firma Ed25519.
> `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (Grok): estado autonomía firmado al entrar en AUTONOMOUS.
> `DEBT-AUTONOMY-CLOCK-INJECTION-001` (Kimi): Clock inyectable para tests sin esperar 30 días.
> `DEBT-AUTONOMY-ZMQ-EVENTS-001` (Grok): transiciones emiten evento ZeroMQ.
>
> **Fingerprint verificado en log real:** `0079087736d9d62a...` — estable entre arranques.
> Mismo `seed.bin` → mismo keypair → mismo fingerprint. Derivación determinista confirmada.
>
> **Plan DAY 152:** `CryptoAutonomyStateMachine` + `ICryptoProvider::get_operational_mode()`.
> **Plan DAY 153:** ADR-045 — `IVaultTransport` + `ICacheManager` primero.
> **Plan DAY 154:** `IEtcdRegistrar` + `ICryptoDeriver` + dual compilation CI.
>
> 'La soberanía tecnológica no es un objetivo teórico — es una decisión de diseño que se toma
> hoy, en cada interfaz que defines. Si `VaultClient` no es reemplazable, no somos soberanos.'
> — Founder · DAY 151"
> — Consejo de Sabios (8/8) · DAY 151

## 📝 Notas del Consejo de Sabios — DAY 150 (8/8)

> "DAY 150 — ADR-044 completado. 4 PRs mergeados. EMECAS verde. Decisiones arquitectónicas mayores adoptadas.
>
> **Consenso Q1 (8/8):** Un solo código fuente, interfaz abstracta `ICryptoProvider` con `SeedFileProvider` (community) y `VaultProvider` (enterprise). El flag CMake `ARGUS_VAULT_ENABLED` solo controla qué `.cpp` se linka — ningún componente ve `#ifdef` en lógica de negocio. `DEBT-EMECAS-DUAL-COMPILATION-001` registrada (DeepSeek): CI compila ambas variantes.
>
> **Consenso Q2 — Migración por canal (8/8 + Gemini):** ZeroMQ es bilateral. Migración simultánea por canal: etcd-server → sniffer+ml-detector → firewall-acl-agent → rag-ingester+rag-security. Orden dentro del canal: ChatGPT propone ml-detector antes que sniffer (latencia arranque); Gemini propone simultáneo. Decisión: simultáneo dentro del canal. Mezcla de providers en el mismo canal = claves incompatibles.
>
> **Consenso Q3 (8/8 — Kimi/Qwen):** etcd-server escribe estado en fichero local `/run/argus/etcd-bootstrap-status.json` (0600, AppArmor + Falco vigilando). Una vez etcd arranca, se registra en sí mismo vía loopback y borra el fichero. Un solo mecanismo de registro para todos los componentes.
>
> **Consenso Q4 — Opción D adoptada (8/8):** TTL = ventana de renovación preferente, nunca fecha de muerte. Máquina de estados NORMAL → EXTENDED_AUTONOMY → RECONCILIATION → REVOKED. Firewall default-deny en autonomía. Circuit breaker 30 días configurable. Logs firmados locales. Cache cifrada en prod (LUKS obligatorio). El hospital se protege hasta el último gramo de electricidad.
>
> **Consenso Q5 (8/8 — ChatGPT + DeepSeek):** No hay crippleware. Plugin system como mecanismo de licencias. Un solo binario por arquitectura. Community = técnicamente útil y respetable. Enterprise = governance, escala, compliance. `ARGUS_VAULT_ENABLED` suficiente para FEDER; roadmap post-FEDER con feature flags granulares en Vault.
>
> **Nuevas deudas registradas:**
> DEBT-CRYPTO-AUTONOMY-001 (P1), DEBT-FIREWALL-AUTONOMY-MODE-001 (P1),
> DEBT-CRYPTO-REVOCATION-LOCAL-001 (P1 post-FEDER), DEBT-CRYPTO-RECONCILIATION-001 (P1),
> DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001 (P1), DEBT-EMECAS-DUAL-COMPILATION-001 (P1),
> DEBT-LICENSE-VAULT-001 (P2 post-FEDER), DEBT-PLUGIN-ENTERPRISE-001 (P2 post-FEDER).
>
> **Mañana DAY 151:**
> EMECAS. Integración etcd-server con VaultClient + ICryptoProvider (#ifdef ARGUS_VAULT_ENABLED).
> Implementar DEBT-CRYPTO-AUTONOMY-001 máquina de estados en vault_client.cpp.
>
> 'La elegancia no está en la pureza teórica, sino en la resiliencia operacional.
> En un hospital bajo ataque, un NDR que sigue detectando con claves stale pero válidas
> es infinitamente más valioso que un NDR criptográficamente puro pero apagado.' — Qwen · DAY 150"
> — Consejo de Sabios (8/8) · DAY 150

## 📝 Notas del Consejo de Sabios — DAY 149 (8/8)

> "DAY 149 — Arquitectura CI/CD criptográfica definida. ADR-044 aprobado unánimemente.
>
> **Consenso Q1-Q7 (síntesis):**
> Vault RNG suficiente para FEDER (NIST SP 800-90A). Cache tmpfs no viola TODO O NADA (TTL 72h prod).
> etcd-server excepción bootstrap (trust anchor operacional). Backend file para dev/FEDER, raft post-FEDER.
> Rotación manual orquestada para FEDER (no automática). Stage separado 'Provision Crypto' en Jenkinsfile.
> Paths por familia `argus/{env}/families/family_X/seed` (ADR-021 respetado).
>
> **Correcciones técnicas críticas (Kimi):**
> Derivación keypairs: `crypto_kdf_derive_from_key()` → component_seed → `crypto_sign_seed_keypair()`.
> Context string único por familia. Fingerprint = sha256(pk), no de seed ni sk.
>
> **Decisión D10 — FailureAction=poweroff ELIMINADO (ChatGPT, adoptado):**
> Host sigue vivo para diagnóstico forense. Pipeline offline + alerta CRITICAL.
> Edge nodes autónomos: siguen operando con keypair en memoria. TTL cache 72h prod.
> Cuando servidor central cae: logs registran el impasse, rotación se pospone, servicio continúa.
>
> **DEBT-ALERTING-EDGE-SOS-001 (Founder):**
> Webhook configurable por despliegue (Discord/Telegram/email) desde el edge directamente.
> Sin internet = problema físico. Con internet = SOS llega aunque el servidor central esté quemado.
>
> **Logros técnicos DAY 149:**
> DEBT-PARQUET-SCHEMA-001 cerrada (207K filas, 11-12x, roundtrip PASSED).
> Vault dev mode + K_pseudo prototipo (determinismo, aislamiento, post-destroy irrecuperable).
> Ansible + Jinja2 pipeline funcional (deploy_configs: 9 OK, 0 failed).
> Jenkins stage Deploy Configs integrado. Abstract v24.
> 5 PRs mergeados. Main limpio.
>
> **Mañana DAY 150:**
> EMECAS protocolo (vagrant destroy -f && vagrant up && make bootstrap && make test-all).
> Implementar scripts/jenkins/provision_crypto.sh (Vault backend file, seeds por familia, assert dev≠prod).
> Crear common/vault_client.h/.cpp (GET seed, tmpfs cache, etcd register, jitter, timeout 5s).
>
> 'El mayor riesgo ya no es criptográfico. Ahora es complejidad operacional emergente.
> Y eso, sinceramente, es una muy buena señal arquitectónica.' — ChatGPT · DAY 149"
> — Consejo de Sabios (8/8) · DAY 149

## 📝 Notas del Consejo de Sabios — DAY 148 (8/8)

> "DAY 148 — Validación offline Suricata irrefutable. Paper v23. DEBT-IRP-FLOAT-TYPES-001 cerrada.
>
> **P1 — Framing de complementariedad (8/8 MANTENER EN ABSTRACT):**
> Consenso unánime: la afirmación es una contribución arquitectónica válida. Los tres sistemas
> operan en capas de encoding distintas (telemetría, firmas, clasificación behavioral) y sus
> outputs son ortogonales — la complementariedad es una inferencia válida de los datos, no una
> promesa de integración. Refinamiento recomendado (ChatGPT, DeepSeek, Kimi, Qwen convergentes):
> cambiar 'are complementary' → 'are architecturally complementary by design'. Una palabra,
> máximo blindaje ante revisores. Acción: aplicar en v24 / próxima revisión. No urgente.
>
> **P2 — DEBT-PARQUET-SCHEMA-001 (8/8 consenso técnico):**
> Granularidad: 8/8 por flow sin excepción. Política de registro: dividido en dos posiciones —
> (4/8: ChatGPT, Mistral, Kimi, Qwen) todos los eventos + relevance_flag para máxima flexibilidad;
> (4/8: Claude, DeepSeek, Grok, Gemini) solo alertas/denies + muestreo 1% de normales. Decisión:
> híbrida — todos los eventos de ml-detector, solo DENY/DROP de firewall-acl-agent. Confirmar
> con datos reales en la sesión Vagrant.
> Tipos Arrow acordados (8/8): int64 epoch ns para timestamps, float32 para scores, utf8
> dictionary-encoded para IDs pseudonimizados, int8/dictionary para enums, int64/int32 para
> contadores.
>
> **P3 — Secuencia DAY 149+ (8/8):**
> DAY 149: A) DEBT-PARQUET-SCHEMA-001 — P0 bloqueante, desbloquea todo ADR-0043.
> DAY 150-152: C) Vault prototype (K_pseudo, Ed25519) — antes que Jenkins.
> DAY 153-155: B) Jenkins seed distribution.
> DAY 156+: D) ARM64 scope — solo si A+B+C verdes. No portar antes de estabilizar.
> Buffer E: ½ día cada 10 días de desarrollo intenso.
> Dependencia oculta crítica (Qwen + DeepSeek): contactar Dr. Andrés Caro Lindo ESTA SEMANA
> para iniciar DEBT-LEGAL-DATA-RETENTION-001 en paralelo. El proceso jurídico tiene latencia
> externa independiente del trabajo técnico.
>
> 'El schema Parquet no es un detalle de implementación — es el contrato de soberanía entre
> el edge y el centro.' — Qwen · DAY 148"
> — Consejo de Sabios (8/8) · DAY 148