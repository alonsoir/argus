# aRGus NDR — BACKLOG
*Última actualización: DAY 173 — 2026-06-02*

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
- **REGLA PERMANENTE (DAY 159 — Consejo 8/8):** El wire protocol entre componentes tiene test de contrato binario en `common/tests/`. Serialización LE/BE del header LZ4 se verifica byte-a-byte. Un bug de endianness no puede permanecer invisible más de un ciclo CI. Ver DEBT-WIRE-PROTOCOL-TEST-001.
- **REGLA PERMANENTE (DAY 159 — Consejo 8/8):** `make test-e2e` es gate de release (nightly), no gate de PR. Los subtests E2E son siempre secuenciales — estado compartido en el pipeline hace la paralelización interna peligrosa.
- **REGLA PERMANENTE (DAY 159 — Founder):** El primer plugin enterprise (`vault_provider.so`) se firma con keypair vendor offline (air-gapped), distinto del keypair del nodo. La pubkey vendor está hardcodeada en el plugin-loader — nunca en Vault.
- **REGLA PERMANENTE (DAY 162 — Consejo 8/8):** "Rotación simultánea" de material criptográfico en sistemas distribuidos es un anti-patrón. Implementar siempre "rotación coordinada con solapamiento" (grace_period ≥ 2× max_clock_skew + deploy_time). Nunca asumir que todos los nodos pueden cambiar de clave en el mismo instante.
- **REGLA PERMANENTE (DAY 162 — Consejo 8/8):** ADR-045 "Crypto Epoch Coordination" debe ser aprobado por el Consejo antes de cualquier PR que implemente coordinación de rotación (Fase 2+). Sin ADR aprobado, el PR no se revisa.
- **REGLA PERMANENTE (DAY 163 — Consejo 8/8):** `ARGUS_ENTERPRISE_PUBKEY_HEX` nunca hardcodeado en CMakeLists. Fuente única: `vault kv get -field=hex secret/argus/enterprise/vendor-pubkey`. Inyectar via `-DARGUS_ENTERPRISE_PUBKEY_HEX=<hex>`. Build enterprise sin el flag → `FATAL_ERROR` explícito.
- **REGLA PERMANENTE (DAY 163 — Consejo 8/8):** Modelo B para keypair enterprise: cada `vagrant destroy && vagrant up` genera nuevo keypair Ed25519, nuevo token. El vendor.key nunca persiste en disco ni en la VM — solo en Vault dev (inmem). En producción FEDER, el Vagrantfile vault-enterprise-bootstrap es la única fuente de bootstrap enterprise.
- **REGLA PERMANENTE (DAY 163 — Consejo 8/8):** `CryptoProviderHandle` es el único punto de acceso a `ICryptoProvider` en componentes que requieren hot-reload. `get()` nunca devuelve null. `reload()` swap atómico sin downtime. Sin excepciones.
- **REGLA PERMANENTE (DAY 163 — Consejo 8/8):** ADR-045 v2 aprobado. Grace period de rotación de época: global configurable, default 10s. No por componente. Wire header epoch: `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4]` — definido ahora, implementado en FASE 3.
- **REGLA PERMANENTE (DAY 162 — Consejo 8/8):** `enterprise_vendor.key` nunca vive en la VM ni en el repositorio. Debe residir en Vault desde el momento en que exista automatización. En dev manual: solo en memoria o tmpfs 0600. Un vagrant destroy que destruye la clave privada vendor hace inoperativo el sistema enterprise.
- **REGLA PERMANENTE (DAY 156 — Consejo 8/8):** En ZMQ PUB/SUB, el publisher debe hacer `bind()` ANTES de que cualquier subscriber haga `connect()`. En tests: crear el publisher en `SetUp()` del fixture antes de `start_subscriber()`. El slow joiner de ZMQ pierde mensajes silenciosamente si el orden se invierte. Ver `docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md`.
- **REGLA PERMANENTE (DAY 156 — Consejo 6/8):** El estado de `CryptoAutonomyStateMachine` se persiste en `/var/lib/argus/crypto-autonomy-state.json` con fsync atómico y firma Ed25519. tmpfs es insuficiente para hospitalario (desaparece en reboot no planificado durante AUTONOMOUS). Un reboot durante AUTONOMOUS es el escenario de ataque exacto que hay que cubrir.
- **REGLA PERMANENTE (DAY 156 — Consejo 8/8):** En producción FEDER (CPD UEx), el keypair Ed25519 se genera UNA SOLA VEZ durante el bootstrap físico del nodo. `make bootstrap` con `ARGUS_ENV=prod` falla explícitamente si no existe keypair preexistente — nunca genera silenciosamente. Ver DEBT-KEYPAIR-LIFECYCLE-PROD-001.

- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** `etcd-server` es el proceso propietario de `CryptoAutonomyStateMachine` y `AutonomyPublisher` en despliegues FEDER. Un solo publisher por nodo garantiza coherencia de estado. Migración a `argus-crypto-daemon` documentada como deuda post-FEDER.
- **REGLA PERMANENTE (DAY 155 — Consejo 8/8):** El canal de autonomía (`argus.crypto.autonomy`) usa `ipc://` por defecto en edge nodes co-locados. El endpoint es configurable desde `firewall.json["autonomy"]["zmq_endpoint"]`. No introducir `tcp://` sin revisión del modelo de seguridad.
- **REGLA PERMANENTE (DAY 155 — Consejo 8/8):** El reconciliador de `AutonomySubscriber` re-aplica el último estado conocido. NUNCA consulta Vault/etcd en el ciclo de reconciliación. El intervalo es configurable desde `firewall.json["autonomy"]["reconcile_interval_sec"]` (default 90s).
- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** Código enterprise (`VaultClient`, `VaultProvider`) vive en `enterprise/` en la raíz del proyecto, paralelo a `common/`. El flag CMake `ARGUS_VAULT_ENABLED` controla `add_subdirectory(enterprise)`. La migración física es post-FEDER.

- **REGLA PERMANENTE (DAY 166 — Consejo 8/8):** EMECAS++ tiene tres actos obligatorios: (I) arranque nominal con Vault, (II) rotación controlada con live epoch bajo tráfico, (III) Vault falla en un componente con zero downtime. Los tres actos deben ser verdes y reproducibles antes de cualquier merge enterprise a main.
- **REGLA PERMANENTE (DAY 166 — Founder):** VaultProvider caché RCU es la implementación del Acto III. El caché inline en `get_material()` garantiza que el componente siga operativo aunque Vault esté caído. El comportamiento correcto ya existía — el gate lo validó por primera vez.
- **REGLA PERMANENTE (DAY 165 — Consejo 8/8):** `epoch_id` en wire header selecciona clave ANTES de descifrar. Nunca intentar descifrado y luego verificar epoch — es un oracle de padding. La selección de clave es el primer paso al recibir un mensaje enterprise.
- **REGLA PERMANENTE (DAY 165 — Consejo 8/8):** El protocolo EMECAS++ tiene tres actos obligatorios: (I) arranque nominal con Vault, (II) rotación controlada con live epoch bajo tráfico, (III) Vault falla en un componente con zero downtime. Los tres actos deben ser verdes y reproducibles antes de cualquier merge enterprise a main.
- **REGLA PERMANENTE (DAY 165 — Founder):** VaultProvider retry/cache es prerequisito arquitectónico del Acto III. Inspeccionar estado antes de planificar DAY 166.
- **REGLA PERMANENTE (DAY 163 — Consejo 8/8):** Todo target de CMake dentro de un bloque condicional (`ARGUS_VAULT_ENABLED`, `ARGUS_ENTERPRISE`, etc.) debe ir envuelto en `if(NOT TARGET <nombre>)` como guard obligatorio. Los bloques condicionales NO deben crear targets nuevos — solo añadir comportamiento (compile definitions, link libraries) a targets ya definidos fuera del bloque. Si el guard dispara, es señal de bug arquitectónico, no de diseño válido. Ver DEBT-CMAKE-GRAPH-INVARIANTS-001.

## 🏗️ Tres variantes del pipeline

| Variante | Estado | Descripción |
|----------|--------|-------------|
| **aRGus-dev** | ✅ Activa | x86-debug, imagen Vagrant completa. Para desarrollo diario. |
| **aRGus-production** | 🟡 En construcción | x86-apparmor + arm64-apparmor. Debian optimizado. Para hospitales, escuelas, municipios. |
| **aRGus-seL4** | ⏳ No iniciada | Apéndice científico. Kernel seL4, libpcap. Branch independiente. |

---


## ✅ RATIFICADO DAY 173 — ADR-052 v3.2 (Consejo 8/8) + DEBTs de identidad de flujo

### ADR-052 v3.2 — Multi-node Flow Identity & Host↔Net Correlation — RATIFICADA Y CERRADA
- **Status:** ✅ RATIFICADA 8/8 DAY 173 — confirmación de fidelidad sin reservas, sin 3ª deliberación.
- **Evolución:** v1→v2 (misión §0, Q1–Q7, node_id) → v3 (bug N1 `node_id ≠ SHA256(pubkey)`, `seq_in_window` transportado, WAL externo, hash anclado a libsodium, event time, TCP/TLS dentro por anulación de árbitro) → v3.1 (4 auto-correcciones C1–C4) → **v3.2** (3 retoques de cierre R1–R3).
- **Principio ordenador (§0):** *"El grafo no es el producto. El producto es el corpus."* Neo4j fabrica el corpus de entrenamiento de modelos ensemble plugin firmados. Suricata/Zeek/Wazuh = testigos/oráculos/corroboradores (maestros del modelo), NUNCA activadores del firewall (3-paradigmas F1 Suricata=0.000/Zeek=0.042/aRGus=0.9985 + soberanía ENS/NIS2/GDPR). Invariante: retención + integridad de etiqueta ganan sobre correlación-online.
- **Decisión núcleo:** `flow_uid = base64(BLAKE2b(node_id ‖ 0x00 ‖ community_id ‖ 0x00 ‖ uint64_be(flow_start_window) [‖ 0x00 ‖ uint32_be(seq_in_window)]))`. `H = BLAKE2b` (`crypto_generichash`, libsodium 1.0.19, fijado documentalmente además del invariante "lo que dé la libsodium congelada"). `node_id` = string legible declarado en inventario firmado, NO derivado del keypair efímero. `community_id` = clave de correlación, nunca identidad (recicla 5-tupla, colisiona multi-nodo). `seq_in_window` transportado en el evento Protobuf (no recomputado offline). `sensor_native_flow_id` = propiedad de trazabilidad, nunca componente del hash.
- **Correlación host↔red:** doble arista (flujo↔flujo determinista por community_id; host↔flujo por `agent_id` canónico + ventana temporal asimétrica en EVENT TIME con watermark, Red→Host 5s / Host→Red 30s). NAT: menú de mecanismos con anotación obligatoria de método+confianza; conflicto → `CONFLICT_NAT`, peso de muestra penalizado en ADR-040.
- **Anulaciones de árbitro (Alonso):** (1) función de hash anclada a libsodium congelada §3.1.1; (2) señales TCP/TLS de host dentro de ADR-052 §3.11 — TCP ligero (RST/seqnum) entra; mismatch TLS acotado a destinos gestionados con cert-expectation store. Límite §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band. Cobertura L7 asimétrica (R1): limitada al perímetro gestionado hasta cerrar `DEBT-CERT-EXPECTATION-STORE-001`.
- **Entregables:** `ADR-052_v3.2.md` (ratificada) + cadena v3.1/v3/v2 + síntesis de deliberación.
- **Desbloquea:** `DEBT-NEO4J-FLOW-KEY-001` (P0 esquema) y el diseño del correlation-engine.

### ADR-053 — JA3/JA4, cadena TLS profunda, anomalía de ruta L3/BGP (STUB)
- **Status:** ⏳ STUB NUEVO — DAY 173. Diferido conscientemente desde ADR-052 para evitar scope creep.
- **Contenido a redactar:** fingerprinting JA3/JA4, validación de cadena TLS profunda (más allá del cert-expectation store del perímetro gestionado), detección de anomalía de ruta L3/BGP (BGP hijack). Flujo: borrador → Consejo → aprobación.

### DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id como string declarado (REESCRITA)
**Severidad:** 🔴 P0 — desbloquea Neo4j
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 C1)
**Componente:** inventario firmado (ADR-046 §3.9) + sniffer + correlation-engine
`node_id` NO puede derivarse del keypair Ed25519 (se regenera en cada `vagrant destroy+up` → rompería la identidad de corpus). `node_id` = string canónico legible declarado en inventario firmado (ej. `argus-sensor-gw-lan-01`), estable a años vista, auditable en forense. El keypair firma los eventos (autenticidad, ADR-027); el inventario firmado protege la integridad del `node_id`. Dos líneas de defensa distintas que no deben confundirse (R3).
**Test de cierre:** `flow_uid` idéntico antes/después de `vagrant destroy+up` con el mismo `node_id` declarado. `node_id` no presente en inventario → rechazo.
**Estimación:** 1 sesión.

### DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificación canónica flow_uid + paridad
**Severidad:** 🔴 P0 — desbloquea Neo4j
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** sniffer (C++) + correlation-engine (Python) + common
Implementar `flow_uid = base64(BLAKE2b(node_id ‖ 0x00 ‖ community_id ‖ 0x00 ‖ uint64_be(flow_start_window) [‖ 0x00 ‖ uint32_be(seq_in_window)]))` con `crypto_generichash` (libsodium 1.0.19). `node_id` entra como string canónico no derivado; `seq_in_window` es INPUT del vector (transportado en el evento, no recomputado offline). Test de paridad cross-implementación C++/Python sobre la MISMA versión de libsodium (mismo patrón que `pycommunityid`).
**Test de cierre:** C++ y Python producen `flow_uid` idéntico sobre el vector + verifican misma versión de libsodium. Caso dos-sensores misma 5-tupla → `flow_uid` distinto por `node_id` distinto.
**Estimación:** 1-2 sesiones.

### DEBT-SENSOR-COVERAGE-MAP-001 — Mapa de cobertura sensor↔segmento
**Severidad:** 🟡 P1 — prerrequisito de orphan_rate / IPW
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.8)
**Componente:** orquestador (Vagrant/Ansible) + cache declarativa (Redis/etcd)
Tabla/cache declarativa sensor↔segmento, DECLARADA (no auto-descubierta), versionada y timestampeada, fuente = orquestador. Validación por beacons. Sin este mapa, `community_id.orphan_rate` e IPW son ruido (no se sabe cuántos testigos se ESPERABAN por flujo: `expected_witnesses`).
**Test de cierre:** `expected_witnesses` por flujo calculable desde el mapa. Beacon de validación detecta deriva mapa↔realidad.
**Estimación:** 1-2 sesiones.

### DEBT-LABEL-WAL-001 — WAL externo append-only con hash-chain
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.7, C4)
**Componente:** correlation-engine + etcd HA (ADR-048)
WAL externo append-only con hash-chain (`prev_hash = H(entrada_{i-1})`) como fuente de no-repudio del etiquetado; Neo4j = vista materializada. Verificación periódica de la cadena. Dos detecciones independientes: cadena rota (manipulación WAL) vs divergencia grafo↔WAL (manipulación Neo4j). Provenance en 2 campos ortogonales que nunca se colapsan: `provenance_suspected` (heurística runtime) vs `provenance_ground_truth` (manifiesto MITRE); su delta = métrica honesta precision/recall. Eje separado del enum congelado de `acceptance_criteria.md` (DROP/CONFIG/POLICY/BUG/UNKNOWN).
**Test de cierre:** manipular una entrada del WAL → cadena rota detectada. Divergir Neo4j del WAL → divergencia detectada. `provenance_suspected` y `provenance_ground_truth` nunca colapsados.
**Estimación:** 2 sesiones (depende de ADR-048 etcd HA).

### DEBT-ARGUSPP-ARP-MONITOR-001 — ARP/NDP como nodo de estado de primera clase
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.9)
**Componente:** sniffer / host plane
ARP/NDP modelado como nodo de estado (`:IpMacBinding` con `valid_from`/`valid_to`), re-binding = señal (vector A / MITM L2). NO volcado de paquetes. Línea de defensa L2 del vector A (no sujeta a la limitación L7 asimétrica de §3.4).
**Test de cierre:** re-binding IP↔MAC anómalo → `:IpMacBinding` con `valid_to` + señal. ARP gratuito legítimo no genera falso positivo.
**Estimación:** 1-2 sesiones.

### DEBT-ARGUSPP-HOST-TCP-001 — Señales TCP de host (RST/seqnum)
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.11a, anulación de árbitro)
**Componente:** host plane (osquery / Wazuh ligero)
Señales TCP ligeras de host (RST inesperados, saltos de seqnum del kernel) como ganchos del vector A ampliado. Límite documentado §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band.
**Test de cierre:** RST/seqnum anómalo bajo supuesto de host sano → `:HostAnomaly` TCP. Host comprometido documentado como límite, no como cobertura.
**Estimación:** 1-2 sesiones.

### DEBT-CERT-EXPECTATION-STORE-001 — Cert-expectation store (mismatch TLS)
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 C2/R1)
**Componente:** host plane + store declarativo
Store de expectativa de certificado para destinos gestionados; habilita la señal de mismatch TLS del vector A en L7. Sin él, la cobertura L7 del vector A está limitada al perímetro gestionado (nota de cobertura asimétrica §3.4, R1): el tráfico saliente a destinos arbitrarios — donde más MITM real ocurre — no queda cubierto en L7. L2 (ARP/NDP) y L4 (RST/seqnum) no tienen esta limitación.
**Test de cierre:** mismatch TLS en destino gestionado con expectativa declarada → señal. Destino arbitrario → sin falso positivo (no cubierto, documentado).
**Estimación:** 2 sesiones.

### DEBT-SEQWINDOW-PERSIST-001 — Persistencia de seq_in_window en el sensor
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** sniffer
Persistencia local (fsync) del contador `seq_in_window` para sobrevivir a reinicios del sensor dentro del mismo bucket temporal. Un crash justo tras computar el contador pero antes de emitir es delicado (riesgo de colisión UDP en el mismo `flow_start_window`).
**Test de cierre:** crash del sensor + restart dentro del mismo window → `seq_in_window` no reutilizado.
**Estimación:** 1 sesión.

### DEBT-ARGUSPP-OOB-MITM-001 — Fuente out-of-band para vector A con host comprometido
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.4.1)
**Componente:** switch (port-security / DAI / DHCP snooping) / SPAN-TAP / Canary Host
Límite fundamental §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band. La fuente OOB no elimina el problema, reubica la confianza al elemento menos comprometible ("escudo, nunca espada").
**Test de cierre:** vector A con host comprometido + fuente OOB → detectable. Sin fuente OOB → documentado como indetectable por diseño.
**Estimación:** post-hardware (switch gestionable).

### DEBT-CORPUS-QUALITY-METRICS-001 — KPIs de calidad del corpus
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §0.1)
**Componente:** correlation-engine + pipeline ML (ADR-040)
KPIs §0.1: % flujos con `provenance_ground_truth` validado, % flujos con `witness_count ≥ 2` en segmentos de cobertura solapada, tiempo de reconstrucción de `flow_uid` desde pcap, cobertura de técnicas MITRE, balance de clases benigno/malicioso. Confianza-por-corroboración (feature, sube con testigos) y peso-de-de-duplicación (sampler, baja con testigos) SEPARADAS; el IPW real lo posee ADR-040. `trust_tier` enum en grafo, score continuo en pipeline ML (no en Neo4j). Normalizado por `expected_witnesses` del mapa de cobertura.
**Test de cierre:** KPIs calculables por sesión. Confianza y peso de de-dup nunca colapsados en un solo número.
**Estimación:** 1-2 sesiones.

### DEBT-ARCH-FLOW-OBSERVATION-001 — Separar FlowObservation de FlowIdentity
**Severidad:** ⚪ P3
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** modelo de datos correlation-engine + Neo4j
Distinguir formalmente `FlowObservation` (lo que un sensor concreto observó) de `FlowIdentity` (la identidad de corpus, `flow_uid`). Refactorización de modelo de datos post-FEDER.
**Test de cierre:** el modelo separa observación de identidad. Múltiples `FlowObservation` → un `FlowIdentity` vía community_id.
**Estimación:** post-FEDER.


## ✅ CERRADO DAY 171

### Cross-check E2E community_id — paridad OPERACIONAL demostrada (3 ventanas)
- **Status:** ✅ COMPLETADO DAY 171 — rama `feature/day170-community-id-protobuf`
- **Hito del día:** se cierra la paridad **operacional** del `community_id`. DAY 170 selló
  la paridad de *especificación* y *provisión* (3 sensores, seed 0, byte a byte vs oráculo).
  DAY 171 demuestra empíricamente que los tres sensores EMITEN el mismo string sobre el
  **mismo paquete real**, no que "deberían coincidir porque la canonicalización es idéntica".
- **Protocolo:** el cliente `.50` replaya el flujo Neris por `eth1` (tcpreplay) en
  `ml_defender_gateway_lan`. aRGus + Suricata + Zeek capturan en PARALELO de `eth1`
  (promiscuo) — el mismo paquete. Los tres convergen STRING A STRING al diana
  `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`. ✅ VERDE.
- **Validación P2 del Consejo (DAY 170):** se valida lo que el binario EMITE (data-plane),
  no lo que dice la config. El cross-check valida empíricamente el CIMIENTO sobre el que
  se apoya todo el AdapterSpec §10.
- **Nota algoritmo:** `community_id` usa **SHA1** (Corelight), no HMAC-SHA256. Receta:
  `"1:" + base64(sha1(seed ‖ saddr ‖ daddr ‖ proto ‖ 0x00 ‖ sport ‖ dport))`. Registrado
  aquí porque en el Consejo DAY 170 Qwen y Mistral lo escribieron como SHA256 — corregido.

### aRGus surfacea community_id de forma observable (helper + test TDH)
- **Status:** ✅ COMPLETADO DAY 171
- **`sniffer/src/flow/community_id_log.{hpp,cpp}`** — helper
  `sniffer::flow::log_community_id_emission(cid, saddr, daddr, sport, dport, proto)`.
- `compute_community_id` permanece **PURA** (5-tupla → `optional<string>`). No se tocó.
  El log NO está dentro de `compute_community_id` (que no ve timestamps ni 5-tupla completa);
  está en los call-sites, donde la 5-tupla ya está en scope.
- **Gateado por env var `ARGUS_CID_CROSSCHECK=1`:** OFF por defecto (coste nulo en hot path:
  lectura de atomic cacheado + branch no tomado), ON solo para el test. Apagado para el RSS.
- **Punto único de log invocado desde los 3 call-sites** de sellado
  (`ring_consumer.cpp` ×2: features y net_features; `main_libpcap.cpp` ×1). Cero duplicación.
- **Escribe a fichero dedicado** `/vagrant/logs/lab/cid-xcheck-argus.tsv` — TSV de 7 campos
  (`cid saddr daddr sport dport proto ts_emision_ns`), con mutex (ring_consumer es multihilo)
  y `fflush` (visible para el parser sin esperar cierre). NO a stdout (contaminado con
  `[DUAL-NIC]`/`[PKT #]`).
- Compila y linka en **Variant A (eBPF) y Variant B (libpcap)** — un solo `.cpp` para ambos.
- **Test TDH `test_community_id_log.cpp`:** verifica la diana DAY 170
  (`147.32.84.165:1027 → 74.125.232.195:80` TCP seed 0 → `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`)
  y las 7 columnas del TSV por contenido. Robusto a `NDEBUG` (checks explícitos con
  `return 1`, no `assert` que `-DNDEBUG` borraría). PASSED.

### Verificador de paridad cross-sensor
- **Status:** ✅ COMPLETADO DAY 171
- **`tools/community_id_crosscheck.py`** (HOST, no pipeline). Lee las salidas crudas de los
  tres motores vía `vagrant ssh`, normaliza a `(cid, 5-tupla)`, compara.
- **Decisión de diseño:** paridad por VALOR de `community_id` (el cid encapsula la 5-tupla
  canónica del hash Corelight). La 5-tupla se conserva como ETIQUETA forense, no como clave
  de comparación — evita el problema de que cada motor nombra el proto distinto
  (Suricata `"TCP"`, Zeek `"tcp"`, aRGus `6`).
- Tres categorías: **agree** (cids en la intersección de los tres — el solomillo) ·
  **disagree** · **solo** (un sensor emite un cid que los otros no).

### Criterio de aceptación congelado — docs/acceptance_criteria.md
- **Status:** ✅ CONGELADO DAY 171 — Consejo 8/8, sin tercera ronda
- **`docs/acceptance_criteria.md`** versionado. Incorpora el refinamiento de ChatGPT:
  categorías de presencia **DROP / CONFIG / POLICY / BUG / UNKNOWN** (no solo "drop o bug").
- Precondición `drop=0`. Nota de túneles/fragmentación/GRO/LRO de Gemini incorporada.
- **P2 del Consejo dirimida 8/8 (NO):** el gate de seed se basa en data-plane, no en config.
  No se relanzó — ya estaba cerrada en la segunda ronda.

## ✅ CERRADO DAY 168

### Vagrantfile multi-VM — Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x
- **Status:** ✅ COMPLETADO DAY 168 — merge a main `21642e87`
- Cuatro VMs en `ml_defender_gateway_lan` (192.168.100.0/24), `autostart: false`:
  - `defender` 192.168.100.1 — aRGus NDR completo (primary)
  - `suricata` 192.168.100.10 — Suricata 7.0.10, AF_PACKET, community-id:yes, PROMISC
  - `zeek` 192.168.100.11 — Zeek 8.2.0, community-id-v1, PROMISC
  - `wazuh` 192.168.100.12 — Wazuh 4.x manager running, NTP OK
  - `client` 192.168.100.50 — tcpreplay + nmap/hydra/sqlmap/atomic-red-team
- 50.248 reglas ET Open cargadas en Suricata.
- `WAZUH_MANAGER_PASSWORD` eliminado del Vagrantfile (fix de seguridad).

### DEBT-ARGUSPP-COMMUNITY-ID-001 — community_id en Suricata + Zeek (PARCIAL)
- **Status:** 🟡 60% DAY 168 — configuración hecha, falta aRGus
- community-id habilitado en Suricata (`community-id: yes`) y Zeek (`community-id-v1`).
- **PENDIENTE (P0, DAY 169+):** campo `community_id` en el contrato protobuf y
  cálculo en el sniffer de aRGus. El ID NO viene por defecto en aRGus — Suricata,
  Zeek y Wazuh lo traen de fábrica, aRGus no.
- **Catch crítico (Kimi):** el `community_id` del sniffer debe ser idéntico byte a byte
  al de Zeek/Suricata para la misma 5-tupla. Canonicalización: `proto` numérico (6/17),
  no string (`"tcp"`); orden de endpoints normalizado. Si difiere, el join cross-tool
  falla en silencio — es el mismo bug de endianness que cazamos al principio.

### REGLAS PERMANENTES nuevas DAY 168
- **REGLA PERMANENTE (DAY 168):** Nunca `set -e` en provisions del Vagrantfile.
  Usar `|| true` (no bloqueante) o `|| { exit 1; }` (bloqueante explícito).
- **REGLA PERMANENTE (DAY 168):** El fix de DNS (`chattr +i /etc/resolv.conf`)
  SIEMPRE después de instalar chrony — chrony reescribe resolv.conf al arrancar.
- **REGLA PERMANENTE (DAY 168):** Nunca `cat << 'EOF'` anidado dentro de un
  heredoc `<<-SHELL` en el Vagrantfile — usar `printf`. El anidamiento rompe el parser.

## ✅ CERRADO DAY 167

### DEBT-ARGUSPP-NTP-001 — NTP+chrony en todos los nodos (P0)
- **Status:** ✅ COMPLETADO DAY 167 — merge a main `7b45feca`
- chrony instalado y configurado en todos los nodos del pipeline.
- Health-check rechaza el arranque si el offset NTP es >1s.
- Gate P0 del correlation-engine: `community_id` es inútil sin timestamps sincronizados
  entre las cinco fuentes (aRGus/Suricata/Zeek/Wazuh).

### correlation-engine scaffold (ADR-048 F2)
- **Status:** ✅ COMPLETADO DAY 167 — andamiaje inicial
- Esqueleto C++20 del correlation-engine con `source_wait_timeout` por fuente
  (argus 5s / suricata 10s / zeek 20s / wazuh 90s) y `crisis_idle_timeout` 120s.
- Esquema Arrow con columnas opcionales para las 4 fuentes desde v1.0.

### BACKLOG-CI-ENTERPRISE-001 — Jenkins gate make emecas++
- **Status:** ✅ COMPLETADO DAY 167 — 11 pasadas Jenkins hasta verde
- Stage `make emecas++` en `Jenkinsfile.dev`: tras Unit Tests, antes de Build .deb.
- Precondición: Vault dev activo (`make vault-dev-start`).
- Fallo del Acto I, II o III → pipeline rojo, no merge.
- `package-deb` y `deploy-vagrant-test` marcados como deferred (skip) en dev.
- Fix `pkill -x etcd-server` (self-match SIGTERM, Fase 5).
- Deudas registradas: DEBT-PACKAGE-DEB-001 (deferred), DEBT-DEPLOY-VAGRANT-001
  (deferred), KNOWN-FAIL-VM-PERF-001 (documentado), DEBT-XGBOOST-HEADERS-001
  (headers desde pip + fallback curl en Vagrantfile).

## ✅ CERRADO DAY 166

### BACKLOG-EMECAS-ENTERPRISE-001 — Protocolo EMECAS++ 3 actos (P0 bloqueante de merge)
- **Status:** ✅ COMPLETADO DAY 166 — merge a main realizado directamente
- **Acto I — Arranque nominal:** test-e2e-vault PASSED. Todos los componentes se autentican contra Vault dev, `ICryptoProvider` fingerprint estable (`485f90db2f324895...`), `CryptoEpochCoordinator` en watch `/v1/epoch`, `crypto_errors==0`.
- **Acto II — Rotación controlada:** test-e2e-synthetic-full PASSED bajo tráfico activo. Delta ml-detector=100, firewall=100, `crypto_errors==0`, `events_dropped==0`. Pipeline no para durante la rotación.
- **Acto III — Fallo Vault controlado (vault-fault-inject):** token hijo revocado → componente entra en caché RCU (AUTONOMOUS) → pipeline sigue operativo → token revocado confirmado → PASSED. Zero downtime demostrado.
- **EMECAS++ OSS también verde:** test-all ✅ · test-e2e-synthetic-full ✅ · test-e2e-synthetic-firewall ✅ (546 eventos, 0 crypto_errors)
- **Keypair efímero activo (DAY 166):** `c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90`
- **Regla permanente (DAY 166):** EMECAS++ tiene tres actos obligatorios. Los tres deben ser verdes antes de cualquier merge enterprise a main. Enterprise ⊃ OSS — no puede haber EMECAS++ verde con EMECAS roto.

### BACKLOG-CRYPTO-E2E-ROTATION-001 — Live rotation con pipeline activo (Actos II+III)
- **Status:** ✅ COMPLETADO DAY 166 — Acto II (live rotation) + Acto III (Vault fault inject) verdes
- FakeEtcdServer 5/5 + test-e2e-vault PASSED (DAY 165) + live rotation bajo tráfico confirmada (DAY 166).
- vault-fault-inject: token hijo revocado → caché RCU activa → pipeline operativo → PASSED.
- Gate de merge satisfecho: los tres actos documentados y reproducibles.

### DEBT-VAULT-RECONNECT-001 — VaultProvider retry/cache (estado desconocido)
- **Status:** ✅ CERRADA DAY 165/166 — confirmada implementación preexistente
- `get_material()` tiene caché inline: si `cached_material_.has_value()` → no toca Vault.
- `ERROR_VAULT_DOWN` → `autonomy_.on_vault_unreachable()` → AUTONOMOUS. Pipeline no muere.
- `refresh()` maneja recuperación completa: RECONCILING → NORMAL.
- El Acto III no requirió implementación nueva — el comportamiento ya existía.

## ✅ CERRADO DAY 165

### BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 — FASE 3: Wire header epoch_id (13/13 tests)
- **Status:** ✅ COMPLETADO DAY 165 — rama `feature/day161-enterprise-crypto-integration`
- Wire header: `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]`
  bytes 0-3: size · bytes 4-5: epoch_id · bytes 6-7: reserved · bytes 8+: payload
- epoch_id=0: community. epoch_id>0: enterprise. Selección de clave ANTES de descifrar.
- `crypto-transport/include/crypto_transport/transport.hpp` actualizado.
- `ml-detector` serializa epoch_id. `firewall-acl-agent/zmq_subscriber.cpp` deserializa.
- **13/13 tests RED→GREEN** incluyendo contrato binario epoch_id.
- **EMECAS++ OSS verde:** `test-all` ✅ · `test-e2e-synthetic-full` ✅ · `test-e2e-synthetic-firewall` ✅ (540 eventos, 0 crypto_errors)
- **Keypair efímero activo (DAY 165):** `a2abfe43e349e86ddeb4a22496b007919c87bdb0f5dc88c17b57cabf0d61331f`

### BACKLOG-CRYPTO-E2E-ROTATION-001 — FASE 4: test-e2e-rotation FakeEtcdServer (5/5)
- **Status:** 🟡 60% DAY 165 — FakeEtcdServer OK, live rotation pendiente
- `test_e2e_rotation`: 5/5 tests con FakeEtcdServer — lógica del coordinador validada.
- `test-e2e-vault` PASSED (smoke test Vault dev + etcd-server enterprise).
- **PENDIENTE:** live rotation con pipeline activo (Acto II del EMECAS++) — BACKLOG-EMECAS-ENTERPRISE-001.

### Consejo de Sabios DAY 165 — Deliberación EMECAS++ (8/8)
- **P1 Arquitectura:** (C) targets anidados. UNANIMIDAD.
- **P2 Vault dev:** suficiente con evidencia. DEBT-VAULT-RECONNECT-001 P0.
- **P3 Live rotation:** obligatoria (7/8). Alonso: mayoría gana.
- **P4 Test negativo epoch_id:** bloqueante (6/8). Alonso: de acuerdo. DEBT-CRYPTO-NEGATIVE-TEST-001 P0.
- **P5 Jenkins:** post-merge P1. UNANIMIDAD.
- **P6 Naming:** (B) EMECAS++ oficial. UNANIMIDAD.
- **Decisión Alonso:** no se mergea hasta EMECAS++ verde con los 3 actos.

### DEBT-FIREWALL-BUILD-LEGACY-001 — Descubierta DAY 165 (P3, no bloquea)
- **Status:** ⏳ OPEN — P3
- `firewall-acl-agent/build` (ruta antigua) falla build: falta `seed_client/seed_client.hpp`.
- Pipeline usa `build-debug` correctamente — no bloquea.

## ✅ CERRADO DAY 164

### DEBT-ETCD-REGISTRAR-REAL-001 — HttpEtcdRegistrar real (FASE 2a)
- **Status:** ✅ COMPLETADO DAY 164 — rama `feature/day161-enterprise-crypto-integration`
- **`common/http_etcd_registrar.h/.cpp`**: IEtcdRegistrar real con httplib.
  `register_status()` → POST /register · `start_keepalive()` → hilo heartbeat ·
  `watch_epoch()` → polling GET /v1/epoch 2s · `last_seen_revision` anti-replay.
  WatchState: CONNECTED → DEGRADED tras N fallos consecutivos.
- **5/5 tests RED→GREEN** con FakeEtcdServer httplib inline.
- Fix: test_autonomy_publisher ZMQ PUB/SUB invertido (bug DAY 155).
- **Commit:** `b48c86ec`

### BACKLOG-CRYPTO-EPOCH-001 — CryptoEpochCoordinator (FASE 2b)
- **Status:** ✅ COMPLETADO DAY 164 — rama `feature/day161-enterprise-crypto-integration`
- **`common/crypto_epoch_coordinator.h/.cpp`**: coordina rotación de época.
  watch `/v1/epoch` via HttpEtcdRegistrar · `on_epoch_change` callback →
  caller hace `handle.reload()` · ACK timestamp monotónico ns · `stop()` idempotente.
- **5/5 tests RED→GREEN**
- etcd-server: GET/PUT `/v1/epoch` + EpochInfo thread-safe (mutex)
- **Commits:** `36d05cef` (CryptoEpochCoordinator) · `475589fb` (integración etcd-server)

### Fix ODR httplib + vault-enterprise-bootstrap DAY 164
- `CPPHTTPLIB_OPENSSL_SUPPORT` via CMake `target_compile_definitions` en todos los targets (evita ODR).
- `alert_client.hpp` #ifndef guard añadido.
- vault-enterprise-bootstrap: token via @file (no shell expansion) — `426c0340`.
- fix: `db63c44f` (httplib ODR + heartbeat timestamp + etcd-server arranca limpio)
- **12/12 suite common verde.**

### BACKLOG-CRYPTO-VENDOR-KEY-001 — vendor.key → Vault (Modelo B efímero)
## ✅ CERRADO DAY 163

### Fix CMake — test_ntp_health_check triplicado (EMECAS++ bloqueado)
- **Status:** ✅ COMPLETADO DAY 163
- **Root cause:** `test_ntp_health_check` definido 3 veces en `common/CMakeLists.txt` (línea 68 canónica + líneas 291 y 387 dentro de `if(ARGUS_VAULT_ENABLED)`). CMake falla con "add_executable cannot create target" solo al activar `-DARGUS_VAULT_ENABLED=ON` — el build normal nunca detectaba el conflicto. Regresión introducida incrementalmente en una sesión reciente.
- **Fix:** `sed -i '291,302d;387,398d' /vagrant/common/CMakeLists.txt`. Un comando, dos minutos.
- **Consejo DAY 163 (8/8 convergencia):** Invariante `if(NOT TARGET)` obligatorio. Los bloques `if(ARGUS_VAULT_ENABLED)` no deben crear targets nuevos — solo añadir comportamiento. Nombres con sufijo `_vault` solo si el target es semánticamente distinto.
- **Nota:** El commit message referenciaba "DAY 167" — typo cronológico (señalado por Qwen). La regresión fue introducida en una sesión reciente sin ese número de día. Corregido en documentación.
- **Nuevas deudas:** `DEBT-CMAKE-GRAPH-INVARIANTS-001` (lint CI) + `BACKLOG-EMECAS-VAULT-E2E-001` (smoke test honesto Acto I).
- **Commit:** `fix(common): remove duplicate test_ntp_health_check targets`

### BACKLOG-CRYPTO-VENDOR-KEY-001 — vendor.key → Vault (Modelo B efímero)

### BACKLOG-CRYPTO-HOT-RELOAD-001 — CryptoProviderHandle RCU sin downtime
- **Status:** ✅ COMPLETADO DAY 163 — rama `feature/day161-enterprise-crypto-integration`
- **`common/crypto_provider_handle.hpp`** — header-only, `std::atomic<shared_ptr<ICryptoProvider>>`.
- **Garantías:** `get()` nunca devuelve null post-construcción. `reload()` swap atómico lock-free C++20. Provider anterior sobrevive hasta refcount=0 (RCU semántica real).
- **9/9 tests RED→GREEN:** null guard, delegaciones is_healthy/component_name, reload swap, concurrent reads (8 readers + 50 reloads), RCU survival test (`weak_ptr` verifica destrucción diferida).
- **12/12 suite common verde** tras añadir test target en CMakeLists.
- **Commit:** `d39be6a1` (CryptoProviderHandle RCU 9/9 tests)

### ADR-045 v2 — Decisiones Consejo DAY 163 (8/8)
- **P1 Coordinación:** `not_before` en etcd suficiente. Sin 2PC. ACKs solo para observabilidad post-hoc en `/argus/crypto/epoch/ack/<comp_id>`. Kimi cambió posición — jitter scheduling 0.02% del grace period de 5s no justifica complejidad de protocolo.
- **P2 Grace period:** global configurable, default **10s**. No por componente (asimetría = split-brain garantizado).
- **P3 Escritor único:** etcd-server escribe `/argus/crypto/epoch` en FASE 2. Lógica criptográfica en `CryptoEpochCoordinator` dentro de `vault_client`. etcd-server habla con él pero no contiene la lógica.
- **P4 Estado EPOCH_TRANSITION:** nuevo estado obligatorio + `EPOCH_FAILED`. `AUTONOMOUS_EPOCH_STALE` documentado para FASE 5.
- **P5 Wire header:** `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4]`. Definido ahora, implementado en FASE 3.
- **Puntos nuevos del Consejo:** `last_seen_revision` para resume seguro, estados watch `WATCH_CONNECTED/DEGRADED/STALE`, ACK con timestamp monotónico en ns.

### DEBT-ETCD-REGISTRAR-REAL-001 — Descubierta DAY 163 (bloqueante FASE 2)
- **Status:** ✅ CERRADA DAY 164 — ver sección DAY 164
- **Descripción:** `StubEtcdRegistrar` es un stub puro (logs a stderr, sin conexión real a etcd). El watch de `/argus/crypto/epoch` que necesita `CryptoEpochCoordinator` no puede construirse sobre el stub. Prerequisito bloqueante de BACKLOG-CRYPTO-EPOCH-001.
- **Fix:** implementar `HttpEtcdRegistrar` real con `etcd-cpp-apiv3` (ya instalado en `provision.sh`): `register_status()` real, `start_keepalive()` real, `watch()` con gRPC watch nativo.
- **Decisiones Consejo DAY 163 (8/8):** etcd-cpp-apiv3 (8/8), gRPC watch (6/8), hilo dedicado encapsulado (5/8).
- **Extras Consejo:** `last_seen_revision` obligatorio para reconnect, estados `WATCH_CONNECTED/DEGRADED/STALE`, ACK con timestamp monotónico.
- **Test de cierre:** `register_status()` escribe en etcd real. `watch()` recibe evento en <100ms. Reconnect tras fallo recupera `last_seen_revision`.
- **Estimación:** 1.5 sesiones DAY 164.

## ✅ CERRADO DAY 162

### EMECAS++ DAY 162 — Todos los gates verdes
- **Status:** ✅ COMPLETADO DAY 162
- `make test-all` ✅ · `make test-e2e-synthetic-full` ✅ · `make test-e2e-synthetic-firewall` ✅
- `test-e2e-live` desacoplado (Consejo Opción 1+3) — gate independiente con precondición explícita

### DEBT-EMECAS-SYNTHETIC-INJECTOR-001 — ZMQ slow joiner CERRADA
- **Status:** ✅ COMPLETADO DAY 162 — rama `feature/day161-emecas-e2e-fix` → mergeado main
- **Causa raíz:** SUB (firewall) conectaba antes de que PUB (injector) hiciera bind → backoff exponencial hasta 30s → 100% pérdida de mensajes en ventana de inyección.
- **Fix:** `synthetic_ml_output_injector`: slow joiner guard 500ms→3000ms. `test-e2e-synthetic-firewall`: PUB arranca 3s antes que SUB, log truncado antes de restart, snapshot post-restart con contadores en 0. `check_e2e_pipeline.py`: modo `precondition` (gate explícito). `check-firewall-abs`: valor absoluto para firewall post-restart (log truncado). Desacoplamiento `test-e2e-synthetic` / `test-e2e-live`.
- **REGLA PERMANENTE (DAY 162 — Consejo 8/8):** En ZMQ PUB/SUB, el PUB debe hacer bind() y estar listo ANTES de que el SUB conecte. En tests E2E: PUB arranca con sleep mínimo 3s de antelación. Ver regla DAY 156 slow joiner.

### DEBT-EMECAS-DUAL-COMPILATION-001 CERRADA
- **Status:** ✅ COMPLETADO DAY 162 — `make test-dual-compilation`
- [1/4] plugin-loader community (OFF) ✅ · [2/4] plugin-loader enterprise (ON) ✅
- [3/4] common/ community ✅ · [4/4] common/ enterprise ✅

### PASO 1 — plugin-loader validate_or_abort() (DAY 162)
- **Status:** ✅ COMPLETADO DAY 162
- `extract_enabled_objects`: cambiado de `pair<string,string>` a `tuple<4>` con `is_enterprise` y `token_path`.
- Antes de `dlopen`: si `is_enterprise==true` → `argus::enterprise::TokenValidator::validate_or_abort(eff_token_path, ARGUS_ENTERPRISE_PUBKEY_HEX, {"vault_crypto"})` bajo `#ifdef ARGUS_VAULT_ENABLED`.
- `plugin-loader/CMakeLists.txt`: `ARGUS_ENTERPRISE_PUBKEY_HEX` hardcodeado (`01cd1509...`), propagado al compilador. `CMAKE_SOURCE_DIR/..` como PRIVATE include para localizar `enterprise/token/TokenValidator.hpp`.
- **Community build:** `#ifdef` inactivo → sin cambio de comportamiento.

### PASO 2-3 — CryptoProvider::create() + etcd-server (DAY 162)
- **Status:** ✅ YA IMPLEMENTADOS — `common/crypto_provider.cpp` y `etcd-server/src/main.cpp` correctos desde DAY 151.

### PASO 4 — test-e2e-vault (DAY 162)
- **Status:** ✅ COMPLETADO DAY 162
- Step 1: Vault dev activo con `secret/argus/crypto`. Step 2: `common/` enterprise build. Step 3: 6/6 vault_provider tests. Step 4: etcd-server enterprise build. Step 5: smoke test (puerto ocupado = binario correcto). ✅ PASSED

### PASO 5 — DEBT-EMECAS-DUAL-COMPILATION-001 (DAY 162)
- **Status:** ✅ COMPLETADO DAY 162 — ver sección anterior.

### Notas Consejo de Sabios DAY 162 (8/8) — Ciclo de vida criptográfico enterprise
- **Veredicto unánime:** "Rotación simultánea" en sistemas distribuidos es anti-patrón. Implementar siempre "rotación coordinada con solapamiento" (grace period ≥ 2× max_clock_skew).
- **Roadmap aprobado (8/8):** 8 fases obligatorias antes de production-ready (ver BACKLOG-CRYPTO-* abajo).
- **Veto (8/8):** No mergear enterprise a main ni habilitar rotación automática hasta Fases 0-4 verdes.
- **ADR obligatorio:** ADR-045 "Crypto Epoch Coordination" antes de cualquier PR de Fase 2.
- **Nuevo riesgo crítico:** vendor.key vive en la VM — P0 inmediato.
- **Pubkey hardcodeada en CMake:** aceptable para bootstrap, no como arquitectura permanente.

---

## ✅ CERRADO DAY 161

### DEBT-WIRE-PROTOCOL-TEST-001 — Test contrato binario LZ4 LE uint32_t
- **Status:** ✅ COMPLETADO DAY 161 — rama `feature/day161-cicd-pipeline`
- **common/tests/test_wire_protocol.cpp**: 6 tests del protocolo binario entre ml-detector (serializador) y firewall-acl-agent (deserializador).
- T1: payload mínimo (2B) · T2: JSON típico (84B) · T3: 8KB · T4: binario 256B · T5: decoded_size==original_size · T6: crypto_errors==0
- Integrado en `common/CMakeLists.txt` + target `make test-wire-protocol` en Makefile.
- El bug DAY 98 (DEBT-FIREWALL-CRYPTO-FORMAT-001) no puede repetirse sin que este test lo detecte.
- **Consejo DAY 161 (5/8):** test actual suficiente — DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001 abierta P2 para integración completa post-Suricata.

### Jenkinsfile.dev + Jenkinsfile.prod — Separación pipelines CI/CD
- **Status:** ✅ COMPLETADO DAY 161
- `Jenkinsfile` renombrado a `Jenkinsfile.prod` (agent: argus-server, pipeline FEDER completo con ODR, Vault, Ansible).
- `Jenkinsfile.dev` nuevo: `agent any`, stages Wire Protocol → Unit Tests → Enterprise Plugin → Build .deb → Deploy Vagrant Test.
- Consejo 8/8 unánime: `agent any` correcto para fase actual. Migrar a `argus-server` cuando Jenkins esté en FEDER.

### DEBT-E2E-LIVE-DELTA-001 — Fix modo delta en test-e2e-live (parcial)
- **Status:** 🟡 60% — DAY 161 (fix Makefile correcto, falta inyector sintético)
- `test-e2e-live` cambiado de modo `check-abs` (valor absoluto desde cero) a `snapshot → 60s → check` (delta).
- Pendiente DAY 162 mini-fix: inyector sintético mínimo para evitar flakiness en Vagrant sin tráfico orgánico.
- **Consejo DAY 161 (6/8):** tráfico orgánico solo en Vagrant es flaky por diseño — inyectar sintético mínimo.

### DEBT-CONFIG-JINJA2-PIPELINE-001 — Documentada (diferida)
- **Status:** 📋 DOCUMENTADA — DAY 161 (`docs/debts/DEBT-CONFIG-JINJA2-PIPELINE-001.md`)
- JSONs originales SAGRADOS. Plantillas Jinja2 en `json-templates/`, valores en `json-values/`, generados en `json-generated/`.
- Prerequisito: hardware físico UEx + BACKLOG-ZMQ-TUNING-001. Varios días de trabajo.

### DEBT-PACKAGE-DEB-001 — Documentada (diferida)
- **Status:** 📋 DOCUMENTADA — DAY 161 (`docs/debts/DEBT-PACKAGE-DEB-001.md`)
- Artefacto .deb primario de release. Prerequisito: hardware físico + Jenkins real + Jinja2 pipeline. Post-FEDER.

### Notas Consejo de Sabios DAY 161 (8/8)
- Q1 Wire Protocol: NO ahora — abrir DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001 P2 (5/8 No, 3/8 Sí complementario)
- Q2 agent any: CORRECTO para fase actual (8/8 unánime)
- Q3 Valores config: FIJOS por perfil, runtime solo selecciona (7/8)
- Q4 Tráfico E2E: INYECTAR sintético mínimo (6/8)
- Q5 DAY 162: A) SURICATA primero (6/8), luego B) NTP

## ✅ CERRADO DAY 158

### DEBT-ALERTING-EDGE-SOS-001 — Webhook SOS Discord/Telegram desde edge
- **Status:** ✅ COMPLETADO DAY 158 — rama `feature/day158-alerting-edge-sos` → tag `v0.9.3-day158`
- **common/include/alert_client.hpp** (header-only, fire-and-forget): Discord + Telegram. Sin dependencia de libhttplib en el binario de producción (ODR eliminado).
- **Tests:** 10/10 RED→GREEN — integración Discord + Telegram en EMECAS.
- **DEBT-ALERTING-VAULT-001 abierta P2:** migrar credenciales Discord/Telegram a Vault en producción.

## ✅ CERRADO DAY 159

### DEBT-FIREWALL-CRYPTO-FORMAT-001 — Dos bugs encadenados desde DAY 98 (100% drop rate invisible)
- **Status:** ✅ COMPLETADO DAY 159
- **Bug 1** — `firewall-acl-agent/src/api/zmq_subscriber.cpp`: usado `hex_to_bytes(config_.crypto_token)` (deprecated DAY 98, siempre vacío) en vez de `rx_->decrypt(data)`. CryptoTransport inicializado correctamente pero nunca llamado.
- **Bug 2** — mismo fichero: header LZ4 leído en big-endian (bit-shifts manuales) pero ml-detector escribe little-endian (`memcpy` de `uint32_t` x86). `0x000002BD` → leído como `0xBD020000` = 3,171,024,896 → fallo sanity check >100 MB → 100% drop rate.
- **Bug 3** — `firewall-acl-agent/src/main.cpp`: dead code eliminado (fetch `crypto_token` de etcd, nunca usado).
- **Resultado tras fix:** `events_processed=5, events_dropped=0, crypto_errors=0` inmediato.
- **Lección sistémica:** unit tests pasan, E2E gate no existía, wire protocol nunca validado. 61 días invisible.

### Migración synthetic injectors a ADR-013 PHASE 2
- **Status:** ✅ COMPLETADO DAY 159
- `tools/synthetic_sniffer_injector.cpp`: lee `sniffer.json → network.output_socket` → `bind tcp://*:5571`. Usa `SeedClient` + `CryptoTransport` + LZ4 LE header (mismo path que ml-detector).
- `tools/synthetic_ml_output_injector.cpp`: lee `ml_detector_config.json → network.output_socket` → `bind tcp://*:5572`. Mismo patrón.
- `tools/CMakeLists.txt`: añadidos `${LZ4_LIBRARIES}` + `seed_client` linkage.
- Código DAY 49 con `get_encryption_key()` + `hex_to_bytes()` + `crypto::CryptoManager` completamente eliminado.

### make test-e2e — Primera implementación gate E2E real
- **Status:** ✅ COMPLETADO DAY 159
- `scripts/check_e2e_pipeline.py` — modos: `snapshot`, `check`, `check-firewall`, `check-abs`.
- `make test-e2e-synthetic-full`: para sniffer → inyecta 100 events → espera 65s → verifica delta ml-detector+firewall.
- `make test-e2e-synthetic-firewall`: para sniffer+ml-detector → inyecta 100 threats → espera 35s → verifica delta firewall.
- `make test-e2e-live`: pipeline running → observa 60s tráfico real → verifica valores absolutos.
- `make test-e2e`: `test-e2e-synthetic` + `test-e2e-live` secuenciales.

### EMECAS++ — Primera ejecución completa desde VM limpia
- **Status:** ✅ COMPLETADO DAY 159
- `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e` — TODO VERDE.
- TEST-E2E-SYNTHETIC-FULL: delta ml-detector=100, firewall=100 ✅
- TEST-E2E-SYNTHETIC-FIREWALL: delta firewall=158 ✅
- TEST-E2E-LIVE: received=4, events_processed=329, events_dropped=0 ✅

## ✅ CERRADO DAY 157

### DEBT-AUTONOMY-STATE-PERSISTENCE-001 — Estado autonomía firmado en /var/lib/argus/
- **Status:** ✅ COMPLETADO DAY 157 — rama `feature/day157-autonomy-state-persistence`
- **common/autonomy_state_writer.h** (header-only, 280 líneas): escribe/lee estado `CryptoAutonomyStateMachine` firmado Ed25519 en `/var/lib/argus/crypto-autonomy-state.json`. Escritura atómica (write→fsync→rename). Lectura fail-safe: firma inválida/ausente/AUTONOMOUS expirado >24h → NORMAL.
- **Formato:** `{state, entered_at_utc, sequence, node_id, reason, signature_hex}`.
- **Integración etcd-server STEP 0c:** Leer estado persistido al arrancar; si AUTONOMOUS válido → `autonomy_sm.on_vault_unreachable()`. Escribir estado en cada transición del health-check loop.
- **Tests:** 9/9 RED→GREEN (write/read, pk errónea, fichero ausente, JSON corrupto, campo faltante, AUTONOMOUS expirado, secuencia, .tmp limpio).
- **Decisión Consejo (6/8):** `/var/lib/argus/` + fsync atómico. tmpfs descartado: hospitalario requiere supervivencia a reboot no planificado durante AUTONOMOUS.

### DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 — bootstrap-status.json firmado Ed25519
- **Status:** ✅ COMPLETADO DAY 157
- **etcd-server/src/main.cpp STEP 0:** JSON canónico (claves ordenadas, sin `signature_hex`) → `crypto_sign_detached` → campo `signature_hex` añadido. Escritura atómica tmp→rename+fsync.
- **Cadena de confianza:** igual que ADR-025 plugins y autonomy_state_writer.
- **Consumidores:** ningún componente lee el fichero todavía — registrado como DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2). Corrección systemd: `ExecStartPre=` en dependientes, NO `ExecStartPost=` (fichero ya no existe en ese momento).

### DEBT-KEYPAIR-LIFECYCLE-PROD-001 — Ciclo de vida keypair en producción
- **Status:** ✅ COMPLETADO DAY 157
- **tools/provision.sh** `generate_keypair()`: política 3 niveles (Consejo 8/8):
  - `ARGUS_ENV=prod` + keypair ausente → `exit 1`, mensaje claro, NUNCA genera
  - `ARGUS_ENV=dev/staging` (default) → genera normalmente
  - Keypair existente en cualquier env → skip sin cambios
- **Test:** `ARGUS_ENV=prod` sin keypair → error + exit 1 verificado.

### DEBT-CRYPTO-RECONCILIATION-001 — Staleness guard + arquitectura final AutonomySubscriber
- **Status:** ✅ COMPLETADO DAY 157 (arquitectura MVP + B1 post-Consejo)
- **Arquitectura final (Consejo 8/8):**
  - `last_known_mode_` (`atomic<FirewallAutonomyMode>`) actualizado en `handle_message()` y reconciliador
  - `shared_ptr<atomic<FirewallAutonomyMode>>` compartido entre subscriber y `poll_callback`
  - `poll_callback` retorna `shared_mode->load()` sin segundo socket (MVP)
  - Feature flag `use_dedicated_health_channel=false`
- **STALENESS GUARD (B1 post-Consejo):** `shared_last_update_ns` (`atomic<int64_t>` steady_clock). `poll_callback`: si `elapsed > staleness_timeout_sec` → NORMAL + log. `staleness_timeout_sec = reconcile_interval_sec * 3` (default 270s). Previene firewall congelado si etcd-server muere silenciosamente.
- **Tests:** 9/9 PASSED (T7: `last_known_mode()` vía ZMQ, T8: `shared_mode` vía ZMQ, T9: staleness guard retorna NORMAL con publisher muerto).
- **EMECAS:** TODO VERDE — `vagrant destroy → up → make bootstrap → make test-all`.

### DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2 registrada)
- Verificación firma en `ExecStartPre=` de servicios dependientes + `tools/check-bootstrap-status.sh`.
- Corrección arquitectónica: verificar ANTES de `start()`, no después (fichero efímero).

## ✅ CERRADO DAY 156

### DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 — Integración plano de autonomía E2E
- **Status:** ✅ COMPLETADO DAY 156 — rama `feature/day156-autonomy-integration` → EMECAS VERDE → PR pendiente merge
- **etcd-server/src/main.cpp:** instancia `CryptoAutonomyStateMachine` + `AutonomyPublisher` (ZMQ PUB). Health-check loop 5s via `crypto_provider->is_healthy()`. Transiciones automáticas NORMAL→AUTONOMOUS→RECONCILING→NORMAL. Publica eventos JSON al socket `ipc:///run/argus/autonomy.sock`.
- **firewall-acl-agent/src/main.cpp:** instancia `FirewallAutonomyReactor` (whitelist_cidrs de firewall.json) + `AutonomySubscriber` en hilo dedicado. Al recibir AUTONOMOUS → aplica cadena `argus-autonomy` (dry_run en tests). Al recibir RECONCILING/NORMAL → levanta la cadena.
- **Correcciones de infraestructura:** `autonomy_publisher.h` añadido al install target de `common/CMakeLists.txt`. `AutonomyConfig` extendida con `zmq_endpoint` en struct y parser. `poll_callback` usa presencia de `etcd_client` como proxy (DEBT-CRYPTO-RECONCILIATION-001 placeholder).
- **Fix ZMQ slow joiner (regla permanente DAY 156):** publisher debe hacer `bind()` ANTES de que cualquier subscriber conecte. En tests: publisher creado en `SetUp()` del fixture, antes de `start_subscriber()`.
- **Test B (unitario) — 7/7 PASSED:** T1 InitialStateNoEvent, T2 VaultKoPublishesAutonomous, T3 VaultRestoredPublishesReconciling, T4 ReconciliationOkPublishesNormal, T5 VaultKoFromAutonomousIsNoop, T6 RevocationPublishesDegraded, T7 HealthCheckLoopSimulation.
- **Test A (E2E) — 4/4 PASSED:** E2E-1 VaultKoTriggersAutonomousMode, E2E-2 VaultRestoredLiftsAutonomousMode, E2E-3 FullCycleNormalAutonomousReconcileNormal, E2E-4 SubscriberRunsStableWithoutEvents.
- **EMECAS DAY 156:** `vagrant destroy → up → make bootstrap → make test-all` — TODO VERDE. 50/50 firewall · 3/3 etcd-server · 9/9 sniffer · 10/10 ml-detector · 8/8 rag-ingester · 1/1 argus-network-isolate.
- **ADR-046 PENDING-REVISION:** Multi-Source Enriched Pipeline. Tres condiciones para cierre: §Label leakage policy, §Deployment matrix, §8 hipótesis o datos reales.
- **Nuevas deudas DAY 156:** `DEBT-KEYPAIR-LIFECYCLE-PROD-001` (P1 pre-FEDER, Consejo 8/8). Nota técnica ZMQ slow joiner (`docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md`). Revisión poll_callback (DEBT-CRYPTO-RECONCILIATION-001: arquitectura final = `last_known_mode_.load()` del subscriber existente, no segundo socket).

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
**Keypair activo:** `c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90`

---

## ✅ CERRADO DAY 124–129

DAY 124: ADR-037 safe_path → v0.5.1-hardened
DAY 125-126: 8 deudas cerradas · lstat() pre-resolution · prefix fijo
DAY 127: resolve_config() · taxonomía safe_path
DAY 128: Snyk 18 findings · 5 property tests
DAY 129: CWE-78 CERRADO · EtcdClientHmac 9/9

---

## 🔴 DEUDAS ABIERTAS — Seguridad y arquitectura

### DEBT-ARGUSPP-COUNTER-DUMP-001 — Volcado de contadores de aRGus a fichero parseable
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 171 (target DAY 172)
**Componente:** `sniffer` / `ml-detector` — stats periódicas

A diferencia de Suricata (`stats.log`) y Zeek (`conn.log`), aRGus NO expone sus contadores
de flujo/eventos en un fichero parseable que el verificador de paridad pueda leer como
fuente de verdad del data-plane. Es código nuevo (pequeño), no "leer un log que existe".
Necesario para que el health-check de huérfanos (`community_id.orphan_rate`,
DEBT-CORRELATION-SEED-GATE-001) tenga la cifra de aRGus con la que comparar.

**Test de cierre:** aRGus vuelca stats periódicas a fichero parseable (TSV/JSON). El
verificador de paridad lo lee sin `vagrant ssh` a stdout. Contadores coherentes con el TSV
de community_id.
**Estimación:** 1 sesión (DAY 172).


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




### DEBT-KEYPAIR-LIFECYCLE-PROD-001 — Ciclo de vida keypair en producción FEDER
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** NUEVA — DAY 156 (Consejo 8/8 unánime)
**Componente:** `provision.sh` + Ansible + `make bootstrap`

El keypair Ed25519 actual se regenera en cada `vagrant destroy && up`.
Correcto para desarrollo (aislamiento de sesión), catastrófico en producción.

**Estrategia de 3 niveles acordada (Consejo 8/8):**

| Entorno | Keypair | Generación | Rotación |
|---------|---------|------------|----------|
| Desarrollo (EMECAS) | Efímero | provision.sh (actual) | Cada sesión |
| Staging | Estable por deployment | Ansible Vault | Trimestral |
| Producción CPD UEx | Estable por nodo, HSM/TPM | Bootstrap físico UNA VEZ | Semestral, manual |

**Regla de producción:**
- `make bootstrap` en prod: si existe `/etc/argus/keys/crypto_material.sk` → cargar; si no → FALLAR
  con mensaje claro (no generar silenciosamente)
- Backup cifrado offline obligatorio
- Rotación manual con procedimiento documentado (dual-key temporal)
- `auditd` habilitado sobre `/etc/argus/keys/` en producción

**Test de cierre:** variable `ARGUS_ENV=prod` en bootstrap → keypair preexistente cargado →
intento de regenerar falla con mensaje claro.
**Estimación:** 1 sesión pre-FEDER

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
**Estado:** ABIERTO — DAY 151 · Decisión Consejo DAY 156 (6/8)
**Componente:** `CryptoAutonomyStateMachine`

**Decisión Consejo (6/8 — ChatGPT, DeepSeek, Gemini, Kimi, Mistral, Qwen):**
Persistir en `/var/lib/argus/crypto-autonomy-state.json` con fsync atómico.
tmpfs descartado: en hospitalario, un reboot no planificado durante AUTONOMOUS es el
escenario exacto que hay que cubrir. Si el fichero desaparece con la memoria, el sistema
arranca en NORMAL con Vault caído — ventana de ataque.

Implementación acordada:
- Escritura: write temp → fsync → rename → fsync(parent_dir)
- Contenido: `{state, entered_at, sequence, node_id, reason, signature}`
- `sequence` anti-replay
- Al arrancar: si estado=AUTONOMOUS y firma válida y timestamp < 24h → arrancar en AUTONOMOUS
- Restart desde AUTONOMOUS → pasar por RECONCILING, verificar salud real de Vault → NORMAL o AUTONOMOUS

**Test de cierre:** entrar en AUTONOMOUS → fichero en /var/lib/argus/ escrito y firmado.
Reboot → pipeline arranca en AUTONOMOUS (no en NORMAL). Manipulación detectada.
**Estimación:** 1 sesión DAY 157

---

### DEBT-AUTONOMY-CLOCK-INJECTION-001 — Clock no inyectable en CryptoAutonomyStateMachine
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Kimi, Consejo)
**Componente:** `common/crypto_autonomy.h`

`CryptoAutonomyStateMachine` usa `std::chrono::steady_clock` directamente. Sin inyección de clock, los tests que verifican el TTL del circuit breaker deben esperar 30 días reales. Implementar `template<typename Clock = std::chrono::steady_clock>` o interfaz `IClock` inyectable.

**Test de cierre:** test avanza clock sintético 31 días → transición a DEGRADED sin esperar.
**Estimación:** 30min al implementar la clase

---


### DEBT-FIREWALL-DENY-SELECTIVE-001 — Regla default-deny selectiva
**Severidad:** ✅ CERRADA DAY 155 — Consejo 8/8 unánime
**Estado:** CERRADO — v0.9.0-day155
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

### DEBT-AUTONOMY-ZMQ-EVENTS-001 — ZMQ pub/sub para transiciones de autonomía
**Severidad:** ✅ CERRADA DAY 155
**Estado:** CERRADO — v0.9.0-day155 · Integración main.cpp pendiente: DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
**Componente:** `common/autonomy_publisher.h/.cpp` + `firewall-acl-agent/autonomy_subscriber.hpp/.cpp`

**Consenso Consejo DAY 154 (7/8):** ZMQ pub/sub directo, sin polling como mecanismo principal. Solo polling reconciliador lento (60-120s) como safety net. Topic: `argus.crypto.autonomy`. Transport: `inproc://argus.autonomy` (mismo proceso) o `ipc:///run/argus/autonomy.sock`. Founder (Alonso): acuerda ZMQ como mecanismo principal.

Cada transición de estado (`NORMAL→AUTONOMOUS`, `AUTONOMOUS→RECONCILING`, etc.) debe emitir un evento ZeroMQ interno en el topic `crypto.autonomy.transition`. Permite que firewall, alerting y RAG reaccionen sin polling.

**Test de cierre:** transición de estado → evento ZeroMQ recibido por suscriptor.
**Estimación:** 1h

---


### DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 — Integración CryptoAutonomyStateMachine en producción
**Severidad:** 🔴 P0 — DAY 156
**Estado:** ABIERTO — DAY 155
**Componente:** `etcd-server/src/main.cpp` + `common/autonomy_publisher.h`

`CryptoAutonomyStateMachine` está definida en `common/` y testeada, pero no instanciada
en ningún componente de producción. `AutonomyPublisher` y `AutonomySubscriber` implementados
y verdes, pero sin cableado en `main.cpp`.

**Decisión Consejo DAY 155 (6/8):** `etcd-server` es el proceso propietario para FEDER.
Ya es el trust anchor operacional (STEP 0), ya conoce el estado de Vault, ya tiene
el health-check loop. Un solo publisher garantiza coherencia de estado (no split-brain).
Migración post-FEDER a `argus-crypto-daemon` documentada como deuda futura.

**Trabajo pendiente:**
1. Instanciar `CryptoAutonomyStateMachine` + `AutonomyPublisher` en `etcd-server/main.cpp`
2. Conectar health-check loop de Vault → eventos → SM → publisher
3. Integrar `AutonomySubscriber` en `firewall-acl-agent/src/main.cpp` con `reconcile_interval_sec` desde JSON
4. Pasar `firewall.json["autonomy"]["reconcile_interval_sec"]` al constructor del subscriber

**Transporte:** `ipc:///run/argus/autonomy.sock` (procesos co-locados en edge node, confirmado 8/8)
**Endpoint configurable:** añadir `firewall.json["autonomy"]["zmq_endpoint"]` como campo opcional

**Test de cierre:** Vault KO → etcd-server detecta → SM entra AUTONOMOUS → ZMQ pub →
firewall sub recibe → apply_default_deny() → hospital protegido. E2E en EMECAS.
**Estimación:** 1 sesión DAY 156

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

### DEBT-CMAKE-GRAPH-INVARIANTS-001 — Lint CI para targets CMake duplicados
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 163 (ChatGPT, Kimi — Consejo 8/8)
**Componente:** `common/CMakeLists.txt` + CI pipeline

Añadir script de lint pre-merge que detecte automáticamente targets duplicados en el grafo CMake. La regresión DAY 163 (`test_ntp_health_check` triplicado) es síntoma de ausencia de este guard. Objetivo: prohibir redefiniciones de targets, exigir `if(NOT TARGET)` en bloques condicionales, verificar unicidad global del grafo de build.

**Propuesta Kimi:** nuevo ADR `docs/adr/adr-028-cmake-target-naming.md` con la convención formal.
**Propuesta ChatGPT:** check de CI: `cmake -DARGUS_VAULT_ENABLED=ON` + grep de warnings de target ya definido.

**Test de cierre:** PR con target duplicado en bloque condicional → CI falla con error explícito.
**Estimación:** 1 sesión.

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

---

## 🔴 BACKLOG — Ciclo de vida criptográfico enterprise (DAY 162 — Consejo 8/8)

> **Veto unánime:** No se autoriza rotación automática hasta Fases 0-4 implementadas y verdes.
> **ADR-045 "Crypto Epoch Coordination"** requerido antes de cualquier PR de Fase 2.

### BACKLOG-CRYPTO-VENDOR-KEY-001 — vendor.key → Vault (P0, INMEDIATO)
**Estado:** ⏳ OPEN — DAY 163
**Descripción:** `enterprise_vendor.key` vive solo en la VM. Vagrant destroy → clave perdida → sistema enterprise inoperativo. Script de bootstrap que sube la clave a `secret/argus/enterprise/vendor-key` con política de acceso restringida a Jenkins. Eliminar pubkey hardcodeada de CMakeLists — inyectar desde CI como secreto efímero.
**Test de cierre:** `vagrant destroy && vagrant up` → enterprise sigue operativo porque clave viene de Vault.
**Bloqueante para:** todo lo demás.

### BACKLOG-CRYPTO-HOT-RELOAD-001 — CryptoProvider::reload() RCU (P0)
**Estado:** ⏳ OPEN — DAY 163-164
**Descripción:** `CryptoProvider::reload()` con semántica Read-Copy-Update. Threads en vuelo usan keypair activo mientras se carga el nuevo. Sin lock global. Sin downtime. Base para rotación coordinada.
**Test de cierre:** reload() en caliente → threads en vuelo no interrumpen → nuevo material activo.

### BACKLOG-CRYPTO-EPOCH-001 — CryptoEpoch en etcd (P1) → ADR-045
**Estado:** ✅ CERRADA DAY 164 — CryptoEpochCoordinator 5/5 tests
**Descripción:** `CryptoEpoch` monotónico en etcd (`/argus/crypto/epoch/<component_id>`). Protocolo 6 fases: generate → pre-distribute → ACK-ready → commit → ACK-active → cleanup. Rollback si convergencia no alcanzada en T segundos. Cada componente expone: `crypto_epoch_local`, `crypto_epoch_target`, `rotation_state`. **ADR-045 debe aprobarse antes del primer PR.**
**Test de cierre:** rotación via etcd → todos los componentes convergen → 0 mensajes perdidos.

### BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 — Ventana dual-key ZMQ (P1)
**Estado:** ✅ CERRADA DAY 165 — FASE 3: wire header epoch_id, 13/13 tests
**Descripción:** `key_ring[epoch]` con ventana deslizante de 2 epochs en CryptoTransport. Grace period = `2 × max_clock_skew + deploy_time`. Acepta Keyₙ y Keyₙ₊₁ durante transición. Property tests: `decrypt(encrypt(msg, epoch), epoch+1)` falla fuera de ventana. **ADR-013 compliance obligatoria.**
**Test de cierre:** rotación durante tráfico activo → 0 mensajes perdidos en ventana de gracia.

### BACKLOG-CRYPTO-E2E-ROTATION-001 — test-e2e-rotation Vault HA (P1)
**Estado:** 🟡 60% DAY 165 — FakeEtcdServer 5/5 + test-e2e-vault PASSED. Pendiente: live rotation pipeline activo (Actos II-III EMECAS++)
**Descripción:** Harness con Vault HA (Raft, 3 nodos, Docker Compose). Tráfico ZMQ real durante rotación. Criterio: throughput no cae >5%, sin desconexiones >3s. Caos: Vault down, nodo retrasado, partición de red. **Gate obligatorio antes de cualquier PR de automatización.**
**Test de cierre:** rotación completa bajo tráfico → métricas dentro de umbrales → 0 split-brain.

### BACKLOG-CRYPTO-OPERABILITY-001 — Runbook + métricas + circuit breaker (P2)
**Estado:** ⏳ OPEN — DAY 167-168
**Descripción:** `argusctl crypto rotate --epoch=N+1` CLI. Métricas: `argus_crypto_epoch`, `argus_crypto_rotation_latency_seconds`, `argus_crypto_handshake_failures_total`, `argus_crypto_seed_age_seconds`. Circuit breaker: si `handshake_failures > umbral` → auto-revert a epoch-1. Alerta temprana: token enterprise expira <30 días → WARN/CRIT logs.
**Test de cierre:** drill de rotación manual exitoso + métricas visibles.

### BACKLOG-CRYPTO-JENKINS-AUTOMATION-001 — Jenkins pipeline rotación (P2)
**Estado:** ⏳ OPEN — DAY 168+
**Descripción:** Pipeline Jenkins: generación → Vault → epoch bump → espera ACK → gate E2E → rollback si falla. OIDC efímero para Jenkins→Vault (no token estático). **Solo después de Fases 0-5 verdes.**
**Test de cierre:** rotación automática valida en CI → 0 intervención manual.

### BACKLOG-EMECAS-VAULT-E2E-001 — Smoke test honesto Acto I (SeedFileProvider rejection)
**Estado:** ✅ CUBIERTO DAY 166 — BACKLOG-EMECAS-ENTERPRISE-001 3 actos verdes
**Propuesto:** DAY 163 (Claude, Kimi — Consejo 8/8)
**Descripción original:** Smoke test en Acto I que verificara: si `ARGUS_VAULT_ENABLED=ON`, entonces `SeedFileProvider` no debe ser el provider activo en runtime. Test rojo en DAY 163, verde al cerrar BACKLOG-CRYPTO-VENDOR-KEY-001. El Acto I de EMECAS++ no puede pasar silenciosamente usando `SeedFileProvider` cuando el flag dice `VaultProvider` — sería un gate que miente.
**Resolución:** BACKLOG-EMECAS-ENTERPRISE-001 (Acto I de EMECAS++ — arranque nominal con Vault) cubre este requisito. DAY 166: todos los componentes se autentican contra VaultProvider real en Acto I. La condición de honestidad está garantizada por diseño.

## BACKLOG-FEDER-001

**Estado:** ACTIVO — colaboración UEx/INCIBE en curso
**Contacto:** Andrés Caro Lindo — UEx/INCIBE — andresc@unex.es

**REALIDAD ACTUALIZADA DAY 160:**
- NO hay deadline FEDER sin el cual no. El 22-09-2026 era referencia de ritmo.
- Gate real: ser introducido OFICIALMENTE en el grupo de investigación de Andrés.
- Prerequisito de ese gate: demostrar que el pipeline produce datasets de valor científico.
- El FEDER es consecuencia del valor demostrado, no el objetivo en sí.
- Lo que le interesa a Andrés: producción de datasets de vanguardia, no la demo NDR per se.

**Convocatoria:** pendiente identificar — limitada a investigador independiente sin empresa
**Colaboración:** Andrés como co-investigador, no solo asesor. Posible infra UEx para servidor.
**Hardware en camino:** RPi × N + switch desde UEx. Email pendiente para añadir N100 x86.
**Emails enviados DAY 141:** hardware FEDER + scope standalone vs federado

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



---

## ADR-048 — Dataset Production Roadmap (DAY 160)

**Estado:** DEFINIDO DAY 160 — Consejo 8/8 + Founder
**Hipótesis central:**
> Un ataque MITRE controlado visto simultáneamente por 5 lenses calibradas para geometrías
> distintas del ataque produce datasets como el mundo nunca ha visto.
> Al añadir señal progresivamente (fase 1→5), el F1 del modelo ensemble mejora de forma
> medible y publicable. Esa curva de mejora es la contribución científica para Andrés/UEx.

**El plan — 5 fases de señal creciente:**

| Fase | Componentes activos | Dataset producido | Modelo entrenado |
|------|---------------------|-------------------|-----------------|
| **F1** | aRGus (ML behavioral, F1=0.9985) | Parquet ml-detector + firewall | XGBoost baseline |
| **F2** | aRGus + Suricata | F1 + eve.json (firmas) | Ensemble F1+F2 |
| **F3** | aRGus + Suricata + Zeek | F2 + conn/dns/ssl/files.log | Ensemble F1+F2+F3 |
| **F4** | aRGus + Suricata + Zeek + Wazuh | F3 + host events (HIDS) | Ensemble F1+F2+F3+F4 |
| **F5** | F4 + Neo4j (correlation engine) | F4 unificado vía community_id | Modelo final |

**Entregaremos a Andrés:**
- Datasets de CADA fase (no solo el final) — integridad científica
- Modelo entrenado de cada fase con métricas F1/Precision/Recall documentadas
- La curva de mejora F1 al añadir señal es la contribución publicable
- Proceso MITRE controlado (hackeo simulado) como ground truth reproducible

**La sesión MITRE:**
- Construida por nosotros — lo mejor que podamos
- Ejecutada contra el pipeline con los 5 engines activos simultáneamente
- Cada engine ve el ataque desde su propia geometría (behavioral, firma, protocolo, host, grafo)
- El dataset resultante tiene ground truth conocido y verificable

**community_id es el pegamento entre engines** — primary key de correlación cross-tool.
**Neo4j es el cerebro de la unión inteligente** — no un simple join, sino un grafo de correlación temporal.

**Dependencias técnicas por fase:**

| Fase | Prerequisito técnico | Estado |
|------|---------------------|--------|
| F1 | Pipeline aRGus completo + Parquet | ✅ DAY 159 |
| F2 | DEBT-ARGUSPP-SURICATA-001 | ⏳ OPEN |
| F3 | DEBT-ARGUSPP-ZEEK-001 | ⏳ OPEN |
| F4 | DEBT-ARGUSPP-WAZUH-001 | ⏳ OPEN |
| F5 | DEBT-ARGUSPP-CORRELATION-001 + Neo4j | ⏳ OPEN |
| Todas | DEBT-ARGUSPP-NTP-001 (sync temporal) | ⏳ OPEN P0 |
| Todas | DEBT-ARGUSPP-COMMUNITY-ID-001 | ⏳ OPEN P0 |
| F5 | DEBT-ARGUSPP-MITRE-001 (ADR-047) | ⏳ OPEN |

**Nota de integridad (Founder DAY 160):**
Entregaremos datasets de cada fase para que la comunidad científica pueda verificar
que la mejora del modelo es consecuencia real de la señal añadida, no de overfitting
ni de artefactos del proceso. La honestidad científica es no negociable.

---

## 🏛️ DAY 169 — Día de arquitectura

**Estado:** rama de arquitectura. Sin merge de código de pipeline — trabajo de diseño.

- **ADR-046 v4 — APROBADO.** Cuarta iteración del Multi-Source Pipeline. Refina la
  separación de planos: plano de datos (telemetría cruda por fuente) vs plano de
  correlación (CrisisWindow + community_id como pegamento) vs plano de decisión.
- **AdapterSpec v1 — CERRADO.** Contrato formal del adaptador por fuente: cómo cada
  motor (Suricata/Zeek/Wazuh) entrega su Parquet con su esquema propio y cómo el
  correlation-engine lo une de forma aditiva vía `community_id`.
- **Separación de planos** consolidada como principio de diseño.
- **ADR-050 — PENDIENTE de redacción.** Los seis vectores de ataque de la sesión MITRE,
  el bootstrap de la víctima y la corrección criptográfica del canal de telemetría.
  Se redactará como hicimos con ADR-046 (borrador → Consejo).

### DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 — community_id nativo en aRGus (P0)
**Severidad:** 🔴 P0 — gate del dataset federado
**Estado:** ABIERTO — DAY 169
**Componente:** `protobuf/network_security.proto` + `sniffer`

community_id viene de fábrica en Suricata, Zeek y Wazuh, pero NO en aRGus.
Trabajo pendiente:
1. `protobuf/network_security.proto`: añadir campo `community_id` (string, field ~20).
   protobuf3 backwards-compatible — campos nuevos no rompen componentes existentes.
2. `sniffer`: calcular community_id (SHA1 de la 5-tupla:
   src_ip + dst_ip + src_port + dst_port + proto).
3. Propagar por el pipeline: sniffer → ml-detector → correlation-engine.

**Catch crítico (Kimi — gate real):** la canonicalización debe ser idéntica byte a byte
a la de Zeek/Suricata para la misma 5-tupla. `proto` como número (6/17), no string;
orden de endpoints normalizado (menor primero). Si difiere, el join cross-tool falla
en silencio. Verificación obligatoria: misma 5-tupla → mismo community_id en las 4
herramientas, comparado a mano antes de declararlo cerrado.

**Test de cierre:** misma 5-tupla inyectada → community_id idéntico en aRGus, Suricata
y Zeek. Diff byte a byte = 0.

### ADR-050 — Sesión MITRE + corrección cripto telemetría (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 169
**Contenido a redactar:** seis vectores de ataque de la sesión MITRE controlada,
bootstrap de las dos víctimas, corrección criptográfica del canal de telemetría.
Flujo: borrador → Consejo de Sabios → aprobación → implementación.

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
Cross-check E2E community_id (3 ventanas):  100% ✅  DAY 171 — aRGus+Suricata+Zeek convergen al diana sobre paquete real
community_id helper observable + test TDH:  100% ✅  DAY 171 — community_id_log.{hpp,cpp}, ARGUS_CID_CROSSCHECK, TSV 7 campos
tools/community_id_crosscheck.py:           100% ✅  DAY 171 — paridad por valor, agree/disagree/solo
docs/acceptance_criteria.md congelado:      100% ✅  DAY 171 — Consejo 8/8, categorías DROP/CONFIG/POLICY/BUG/UNKNOWN
DEBT-ARGUSPP-COUNTER-DUMP-001:                0% ⏳  P1 DAY 172 — volcado contadores aRGus a fichero parseable
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
BACKLOG-ZMQ-TUNING-001:                100% ✅  DAY 155 — HWM + RECONNECT_IVL en todos los sockets
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
DEBT-KEYPAIR-LIFECYCLE-PROD-001:          100% ✅  DAY 157 — 3 niveles dev/staging/prod, exit 1 en prod sin keypair
DEBT-BOOTSTRAP-STATUS-SIGNATURE-001:    100% ✅  DAY 157 — bootstrap-status.json firmado Ed25519, escritura atómica
DEBT-AUTONOMY-STATE-PERSISTENCE-001:    100% ✅  DAY 157 — autonomy_state_writer.h 9/9 tests + etcd-server STEP 0c
DEBT-AUTONOMY-CLOCK-INJECTION-001:        0% ⏳  P1 (clock no inyectable)
DEBT-FIREWALL-DENY-SELECTIVE-001:        100% ✅  DAY 155 — cadena argus-autonomy, whitelist obligatoria JSON
DEBT-AUTONOMY-ZMQ-EVENTS-001:           100% ✅  DAY 155 — AutonomyPublisher + AutonomySubscriber (ipc://)
DEBT-AUTONOMY-CRYPTO-INTEGRATION-001:   100% ✅  DAY 156 — CERRADA. 7/7 + 4/4 tests. EMECAS verde.
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
DEBT-CRYPTO-RECONCILIATION-001:            100% ✅  DAY 157 — shared_mode + staleness guard 30s, 9/9 tests
DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001:       0% ⏳  P1 pre-FEDER (cache cifrada en prod edge)
DEBT-EMECAS-DUAL-COMPILATION-001:          100% ✅  DAY 162 — test-dual-compilation, 4/4 OK
DEBT-LICENSE-VAULT-001:                      0% ⏳  P2 post-FEDER (servidor licencias en Vault)
DEBT-PLUGIN-ENTERPRISE-001:                  0% ⏳  P2 post-FEDER (definir plugins enterprise)
ADR-031 aRGus-seL4:                      0% ⏳  branch independiente
DEBT-ALERTING-EDGE-SOS-001:             100% ✅  DAY 158 — alert_client.hpp 10/10 tests, Discord+Telegram
DEBT-FIREWALL-CRYPTO-FORMAT-001:        100% ✅  DAY 159 — dos bugs encadenados DAY 98, 100% drop rate resuelto
Synthetic injectors ADR-013 PHASE 2:    100% ✅  DAY 159 — SeedClient+CryptoTransport+LZ4-LE, DAY-49 code eliminado
make test-e2e (gate E2E real):          100% ✅  DAY 159 — synthetic-full + synthetic-firewall + live, EMECAS++ verde
DEBT-WIRE-PROTOCOL-TEST-001:            100% ✅  DAY 161 — 6/6 tests, common/tests/ + make test-wire-protocol
DEBT-E2E-LIVE-DELTA-001:                 60% 🟡  DAY 161 — fix delta OK, falta inyector sintético mínimo
DEBT-ALERTING-VAULT-001:                  0% ⏳  P2 (credenciales Discord/Telegram a Vault)
PASO 1 plugin-loader validate_or_abort():       100% ✅  DAY 162 — tuple<4>, ARGUS_VAULT_ENABLED, namespace correcto
PASO 4 test-e2e-vault:                          100% ✅  DAY 162 — 6/6 vault_provider + smoke etcd-server enterprise
BACKLOG-CRYPTO-VENDOR-KEY-001:                  100% ✅  DAY 163 — Modelo B, vault-enterprise-bootstrap, CMake guard
BACKLOG-CRYPTO-HOT-RELOAD-001:                  100% ✅  DAY 163 — CryptoProviderHandle RCU 9/9 tests, header-only
DEBT-ETCD-REGISTRAR-REAL-001:                     0% ⏳  P0 DAY 164 (StubEtcdRegistrar → HttpEtcdRegistrar real, prerequisito FASE 2)
BACKLOG-CRYPTO-EPOCH-001:                         0% ⏳  P1 DAY 164-165 (CryptoEpoch etcd + ADR-045 v2)
BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001:                  0% ⏳  P1 DAY 165-166 (ventana dual-key ZMQ)
BACKLOG-CRYPTO-E2E-ROTATION-001:                  0% ⏳  P1 DAY 166-167 (test-e2e-rotation Vault HA)
BACKLOG-CRYPTO-OPERABILITY-001:                   0% ⏳  P2 DAY 167-168 (runbook + métricas + circuit breaker)
BACKLOG-CRYPTO-JENKINS-AUTOMATION-001:            0% ⏳  P2 DAY 168+ (Jenkins pipeline rotación)

DEBT-ENTERPRISE-PLUGIN-001:             100% ✅  DAY 160 — vault_provider.so 6/6 tests, Vault+Jenkins operacionales
DEBT-JENKINS-PROD-001:                    0% ⏳  P0 post-hardware (Jenkins CI/CD en hardware físico)
DEBT-EMECAS-TEST-TO-MERGE-001:            0% ⏳  P1 (pirámide 4 niveles: unit+wire+integ+E2E)
DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001:    0% ⏳  P2 post-Suricata (test integración CryptoTransport+wire protocol)
DEBT-CONFIG-JINJA2-PIPELINE-001:          0% ⏳  P2 — Jinja2 config pipeline, varios días, post-hardware UEx
DEBT-PACKAGE-DEB-001:                     0% ⏳  P2 post-FEDER — paquete .deb artefacto primario
Jenkinsfile.dev + Jenkinsfile.prod:      100% ✅  DAY 161 — separación dev/prod, agent any vs argus-server
DEBT-ETCD-REGISTRAR-REAL-001:                  100% ✅  DAY 164 — HttpEtcdRegistrar REST 5/5 tests, WatchState CONNECTED/DEGRADED/STALE
BACKLOG-CRYPTO-EPOCH-001:                       100% ✅  DAY 164 — CryptoEpochCoordinator 5/5 tests, etcd-server integrado
BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001:               100% ✅  DAY 165 — FASE 3: wire header epoch_id, 13/13 tests
BACKLOG-CRYPTO-E2E-ROTATION-001:               100% ✅  DAY 166 — Live rotation Acto II+III verdes, gate completado
BACKLOG-EMECAS-ENTERPRISE-001:                 100% ✅  DAY 166 — EMECAS++ 3 actos verdes, merge a main
DEBT-VAULT-RECONNECT-001:                       100% ✅  DAY 165/166 — caché inline preexistente confirmada, Acto III no requirió código nuevo
DEBT-CRYPTO-NEGATIVE-TEST-001:                  100% ✅  DAY 166 — test epoch_id=0xFFFF rechazado, EMECAS++ verde
BACKLOG-CI-ENTERPRISE-001:                        0% ⏳  P1 — Jenkins gate make emecas++ (post-merge, requiere hardware FEDER)
DEBT-FIREWALL-BUILD-LEGACY-001:                   0% ⏳  P3 — firewall-acl-agent/build ruta antigua (no bloquea)
DEBT-CMAKE-GRAPH-INVARIANTS-001:                  0% ⏳  P1 — lint CI targets duplicados CMake (DAY 163, Consejo 8/8)
BACKLOG-EMECAS-VAULT-E2E-001:                   100% ✅  DAY 166 — cubierto por BACKLOG-EMECAS-ENTERPRISE-001 Acto I
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


## 📝 Notas del Consejo de Sabios — DAY 165 (8/8)

> "DAY 165 — Deliberación sobre el diseño del protocolo EMECAS++ enterprise. Seis preguntas, 8 modelos, decisiones finales de Alonso como árbitro.
>
> **P1 — Arquitectura del protocolo (UNANIMIDAD C):** `make emecas` = OSS sin cambios. `make emecas++` = superset anidado. Enterprise ⊃ OSS — no puedes tener enterprise verde con OSS roto.
>
> **P2 — Vault dev suficiente (DECISIÓN ALONSO: Sí con evidencia):** Vault dev cubre el camino funcional. Pero se requiere evidencia de que VaultProvider funciona en el pipeline con retry/cache. DEBT-VAULT-RECONNECT-001 abierta P0.
>
> **P3 — Live epoch rotation en EMECAS (DECISIÓN ALONSO: SÍ, mayoría 7/8):** FakeEtcdServer valida lógica unitaria. La cadena real Vault→etcd→CryptoEpochCoordinator→CryptoProviderHandle RCU→wire header→firewall debe ejecutarse al menos una vez en el gate. Claude votó A (solo FakeEtcdServer) — posición minoritaria. El mejor test futuro será el pipeline CI/CD en hardware real (RPi5/N100).
>
> **P4 — Test negativo epoch_id incorrecto (DECISIÓN ALONSO: OBLIGATORIO, mayoría 6/8):** Un epoch_id incorrecto indica bug propio (situación de filo no vista) o abuso externo. Ambos peligrosos. Test obligatorio pre-merge. DEBT-CRYPTO-NEGATIVE-TEST-001 P0.
>
> **P5 — Jenkins gate (UNANIMIDAD):** Merge aceptable sin Jenkins. BACKLOG-CI-ENTERPRISE-001 P1 post-merge.
>
> **P6 — Naming (UNANIMIDAD B):** EMECAS++ oficial. EMECAS = community. EMECAS++ = community + enterprise.
>
> **Decisión Alonso — definición EMECAS++ real (3 actos):**
> Acto I: Arranque nominal — todos los componentes se autentican contra Vault, reciben claves, cifran/descifran, tráfico fluye. Medición: events_processed, crypto_errors==0, epoch_id correcto.
> Acto II: Rotación controlada (5 min o forzada) — pipeline sigue corriendo, epoch_id antes/después distintos, zero drops, crypto_errors==0.
> Acto III: Vault falla en entrega a un componente aleatorio — ese componente trabaja con clave anterior (caché RCU), notifica (log estructurado + señal Jenkins), resto funciona con clave nueva, al recuperar Vault el componente pendiente recibe nueva clave y la aplica. Zero downtime. Datos válidos para paper arXiv.
>
> **Bloqueantes identificados:**
> B1: Estado VaultProvider retry/cache — DESCONOCIDO, prerequisito del Acto III.
> B2: test-e2e-vault no terminado.
> B3: Mecanismo notificación hacia Jenkins — inexistente.
> B4: Script inyección fallo controlado — inexistente.
>
> 'No mergeas hasta ver los tres actos del protocolo verdes y reproducibles.' — Alonso · DAY 165"
> — Consejo de Sabios (8/8) · DAY 165 · feature/day161-enterprise-crypto-integration

## 🧬 HIPÓTESIS CENTRAL — Inmunidad Global Adaptativa

**Formulada:** DAY 128 | **Estado:** Pendiente demostración (DEBT-PENTESTER-LOOP-001)

Un sistema con ACRL converge hacia cobertura de técnicas ATT&CK en tiempo polinomial. Un sistema estático no converge nunca.

---

*DAY 169 — 2026-05-29 · main @ 21642e87*
*"Via Appia Quality — Un escudo que aprende de su propia sombra."*






## 📝 Notas del Consejo de Sabios — DAY 159 (8/8)

> "DAY 159 — Dos bugs encadenados desde DAY 98 encontrados y corregidos. 61 días de 100% drop rate invisible en el firewall. Primera ejecución EMECAS++ completa con gate E2E real desde VM limpia: TODO VERDE.
>
> **Hallazgo sistémico (ChatGPT, convergencia 8/8):** El problema no fue el bug de endianness — fue que el pipeline tenía un hueco de testing entre unitario y E2E. Los contratos binarios entre componentes nunca fueron validados. La pirámide de testing tiene ahora 4 niveles obligatorios: unit → wire contract → integration → E2E. Cada nivel cubre fallos que el siguiente no puede detectar a tiempo.
>
> **Q1 — Test wire protocol (consenso: sí, ubicación debatida):**
> Test unitario en `common/tests/` — contrato cross-componente. ChatGPT: `common/tests/` porque el contrato pertenece al bus, no a un componente. Gemini propone además modo `check-wire` en `check_e2e_pipeline.py` que samplea mensaje real del bus ZMQ. Mistral en minoría: gate E2E suficiente. Decisión: DEBT-WIRE-PROTOCOL-TEST-001 en `common/tests/`, P1 siguiente merge.
>
> **Q2 — test-e2e-live delta vs absoluto (Gemini/Kimi/Mistral convergentes):**
> Snapshot justo antes del wait de 60s → delta ≥ 1 → mucho más robusto que absoluto histórico. Claude/Grok/DeepSeek: timestamp check sobre absoluto. Decisión: adoptar propuesta Gemini — snapshot+delta de ventana corta. DEBT-E2E-LIVE-DELTA-001 P1.
>
> **Q3 — DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 (consenso: P2, no P0):**
> etcd-server ya alerta. Para FEDER, detección+respuesta > notificación granular. DeepSeek + Kimi: documentar la limitación single-point-alerting en el prospectus FEDER y en §7 del paper. Adoptado.
>
> **Q4 — Auto-adaptación ml_output_injector (unánime: No):**
> Solo endpoint ZMQ desde JSON. Crypto/compresión son canónicos via CryptoTransport — no leer más JSON. Gemini: añadir docstring en el fichero marcando explícitamente que asume LZ4+ChaCha20. DeepSeek: comentario TODO si en el futuro se añade Zstd. Adoptado.
>
> **Q5 — Paralelización test-e2e en Jenkins (unánime: No paralelizar internamente):**
> Estado compartido (pipeline, logs, ZMQ sockets, iptables) hace la paralelización interna peligrosa. Qwen + Kimi: estrategia nightly — `test-all` en cada PR, `test-e2e` en job nocturno. Para FEDER con baja frecuencia de merges, merge gate es aceptable. Grok: `timeout(time: 120, unit: MINUTES)` como safety net en Jenkins. DeepSeek: polling activo de logs para reducir sleeps. Adoptado.
>
> **Decisión Founder post-Consejo:** Prioridad inmediata → primer plugin enterprise real (`vault_provider.so` via ADR-025). Sin un plugin enterprise firmado, el modelo open-core es una promesa en papel. Cierra: DEBT-LICENSE-VAULT-001, modelo de negocio, demo FEDER enterprise. Jenkins en hardware físico real (DEBT-JENKINS-PROD-001) es el siguiente hito de infraestructura — requiere hardware FEDER.
>
> **EMECAS++:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e` — TODO VERDE. Tag `v0.9.3-day158` en main.
>
> 'Un test que pasa no es evidencia de ausencia de bug — es evidencia de ausencia del test correcto.' — ChatGPT · DAY 159"
> — Consejo de Sabios (8/8) · DAY 159 · v0.9.3-day158

## 📝 Notas del Consejo de Sabios — DAY 157 (8/8)

> "DAY 157 — Cuatro deudas cerradas. El plano de autonomía criptográfica adquiere persistencia, integridad y resiliencia operacional.
>
> **DEBT-AUTONOMY-STATE-PERSISTENCE-001 (6/8 original + correcciones B1):**
> `/var/lib/argus/crypto-autonomy-state.json` con fsync atómico + firma Ed25519. 9/9 tests. Integrado en etcd-server STEP 0c. Vector replay cubierto por timestamp + expiración 24h. Umbral configurable recomendado post-FEDER (ChatGPT: 1h-6h hospitalario; Kimi: 4h default; Claude/Qwen: 24h OK para FEDER MVP).
>
> **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (7/8 consenso ExecStartPre=):**
> Fichero efímero firmado Ed25519. `ExecStartPost=` incorrecto — fichero ya no existe en ese momento. Corrección: `ExecStartPre=` en servicios dependientes. DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 registrada (P2).
>
> **DEBT-KEYPAIR-LIFECYCLE-PROD-001 (8/8 unánime):**
> Política 3 niveles: dev=genera, staging=genera (pragmático FEDER), prod=exit 1 si ausente. ChatGPT y Kimi: staging debería requerir keypair preexistente para detectar errores de provisioning antes de prod. Registrado como mejora P2 post-FEDER.
>
> **DEBT-CRYPTO-RECONCILIATION-001 + STALENESS GUARD B1 (8/8 consenso bloqueante):**
> `shared_ptr<atomic>` resuelve ordering. Staleness guard 30s (configurable) previene firewall congelado si publisher muere silenciosamente. ChatGPT: 'último valor conocido' ≠ 'valor confiable' — distinción crítica para sistemas distribuidos. 9/9 tests incluyendo T9 staleness.
>
> **Inconsistencia detectada (ChatGPT):** `autonomy_state_writer.h` usa sk inyectado; `bootstrap-status.json` usa `crypto_material.sk` directamente. Cadena de confianza consistente pero API diverge. Registrado para refactorización futura.
>
> **`fsync(dirfd)` pendiente (Kimi):** Para garantía POSIX completa en EXT4/XFS con barrier=1, `fsync(fd)` del fichero no basta — se necesita `fsync(dirfd)` del directorio padre. P2 post-merge.
>
> **EMECAS DAY 157:** TODO VERDE. `vagrant destroy → up → make bootstrap → make test-all`.
>
> 'La autonomía sin staleness detection no es autonomía — es un estado zombie que el atacante puede explotar.' — Consejo DAY 157"
> — Consejo de Sabios (8/8) · DAY 157 · feature/day157-autonomy-state-persistence

## 📝 Notas del Consejo de Sabios — DAY 156 (8/8)

> "DAY 156 — DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA. Plano de autonomía criptográfica E2E funcionando en producción. 50/50 tests verdes. EMECAS verde en VM limpia.
>
> **Q1 — Persistencia de estado (6/8 contra 2 disidentes):**
> `/var/lib/argus/crypto-autonomy-state.json` + fsync atómico + firma Ed25519.
> tmpfs descartado unánimemente para hospitalario — reboot durante AUTONOMOUS es el escenario crítico.
> Disidentes: Claude y Grok (tmpfs) — reconocido error. ChatGPT: restart desde AUTONOMOUS debe
> pasar por RECONCILING, verificar Vault real antes de volver a NORMAL. No trust on reboot.
> Formato acordado: `{state, entered_at, sequence, node_id, reason, signature}`.
> `sequence` anti-replay obligatorio.
>
> **Q2 — poll_callback como proxy de Vault (mayoría: implementar canal):**
> Arquitectura final acordada (Qwen — propuesta más elegante):
> `AutonomySubscriber::run()` → actualiza `atomic<FirewallAutonomyMode> last_known_mode_`
> `poll_callback` → retorna `last_known_mode_.load()`
> No se crea un segundo socket — se reutiliza el canal `autonomy.sock` existente.
> Para MVP FEDER: feature flag `use_dedicated_health_channel` (default false).
> Registrar como DEBT-CRYPTO-RECONCILIATION-001: RESOLVED-PARTIALLY.
>
> **Q3 — Suricata (8/8 unánime): Eve JSON via file watcher.**
> Inotify sobre `/var/log/suricata/eve.json` (rotation-aware). Parser incremental.
> Solo eventos `alert` con `community_id` para correlación inicial.
> AppArmor para Suricata OBLIGATORIO antes de despliegue (historial RCE).
> ZMQ directo solo si latencia es cuello de botella demostrado.
>
> **Q4 — ZMQ slow joiner (7/8): nota técnica, NO ADR.**
> `docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md`. Wrapper `ReliablePubSocket` (Qwen).
> Mistral (1/8 disidente): propuso ADR-047 — rechazado. Un ADR documenta decisiones con
> alternativas; el slow joiner es un gotcha de librería con solución canónica.
>
> **Q5 — Keypair (8/8 unánime): 3 niveles dev/staging/prod.**
> Dev: regenerar en cada destroy/up (correcto). Staging: Ansible Vault. Prod CPD UEx:
> generado UNA VEZ en bootstrap físico, TPM/HSM si disponible, /etc/argus/keys/ 0600 si no.
> NUNCA regenerar automáticamente en restarts. Rotación manual con procedimiento documentado.
> DEBT-KEYPAIR-LIFECYCLE-PROD-001 registrada.
>
> **ADR-046 — PENDING-REVISION (Consejo 8/8):**
> Tres condiciones para cerrar: (1) §Label leakage policy — features=solo aRGus, labels=Suricata,
> NUNCA mezclar en el vector de entrada; (2) §Deployment matrix — RPi5=aRGus-only,
> edge server x86≥16GB=aRGus++; (3) §8 reformulado como hipótesis o con datos reales.
>
> **Observación arquitectónica (ChatGPT):**
> 'El sistema empieza a mostrar comportamiento autónomo determinista. Muchos sistemas
> resilientes colapsan al perder componentes críticos. aRGus está empezando a comportarse
> como un sistema tolerante a particiones, no como un IDS tradicional.'
>
> 'La autonomía no se delega; se coordina. El publisher que hace bind primero no es un
> detalle — es el pacto de localidad que garantiza que el primer latido del hospital
> siempre llega.' — Qwen · DAY 156"
> — Consejo de Sabios (8/8) · DAY 156 · v0.9.1-day156

## 📝 Notas del Consejo de Sabios — DAY 155 (8/8)

> "DAY 155 — Tres deudas cerradas. La autonomía pasa de concepto a flujo operacional real.
>
> **P0 CERRADO — DEBT-FIREWALL-DENY-SELECTIVE-001 (8/8 unánime DAY 154 → ejecutado DAY 155):**
> Cadena dedicada `argus-autonomy` reemplaza regla garrote `-I INPUT 1 -j DROP`.
> Orden garantizado estructuralmente: lo→ESTABLISHED→CIDRs→DROP→INPUT hook.
> `whitelist_cidrs` obligatorio desde `firewall.json["autonomy"]["whitelist_cidrs"]` — sin defaults.
> `AutonomyConfig` + `parse_autonomy()` con fail-fast explícito en `ConfigLoader`.
> 12/12 tests. 49/49 firewall tests verdes. EMECAS HARDENED PASSED con `-flto -O3 -Werror`.
> Kimi: 'Un vagrant up en un laptop no sufre. Un hospital sí.' — ejecutado.
>
> **P1 CERRADO — DEBT-AUTONOMY-ZMQ-EVENTS-001:**
> `AutonomyPublisher` (`common/`): ZMQ PUB, topic `argus.crypto.autonomy`, `make_callback()`
> integra con `CryptoAutonomyStateMachine::TransitionCallback`. 4/4 tests.
> `AutonomySubscriber` (`firewall-acl-agent/`): ZMQ SUB event-driven + polling reconciliador 90s safety net.
> RECONCILING mapea a NORMAL. 6/6 tests.
> Transport: `ipc:///run/argus/autonomy.sock` (procesos separados confirmado — firewall no linkea common/).
>
> **P2 CERRADO — BACKLOG-ZMQ-TUNING-001:**
> HWM + RECONNECT_IVL en todos los sockets. Prerequisito de BACKLOG-BENCHMARK-CAPACITY-001 satisfecho.
>
> **Consenso Q1 — Proceso propietario SM (6/8 + Founder):**
> `etcd-server` instancia `CryptoAutonomyStateMachine` + `AutonomyPublisher` para FEDER.
> Ya es trust anchor, ya tiene health-check loop, ya conoce el estado de Vault.
> Un solo publisher = coherencia garantizada, sin split-brain.
> Migración post-FEDER a `argus-crypto-daemon` documentada (DeepSeek + Grok en disidencia razonada).
> ChatGPT: 'El componente coordinador es quien primero conoce la pérdida de quorum.'
>
> **Consenso Q2 — Endpoint (8/8 unánime):**
> `ipc://` correcto y suficiente para edge nodes co-locados.
> Endpoint configurable desde `firewall.json["autonomy"]["zmq_endpoint"]` para flexibilidad futura.
> El firewall autonomy plane debe ser local, determinista, fail-contained.
>
> **Consenso Q3 — Reconciliador (8/8 unánime):**
> `reconcile_interval_sec` configurable desde JSON (default 90s).
> Re-aplica último estado conocido — NO consulta Vault/etcd.
> Desired state reconciliation, no distributed state recomputation (ChatGPT).
>
> **Consenso Q4 — Estructura enterprise (6/8):**
> `enterprise/` en raíz del proyecto, paralelo a `common/`.
> `CMakeLists.txt` raíz: `add_subdirectory(enterprise)` condicional con `ARGUS_VAULT_ENABLED`.
> Documentar en `docs/OPEN_CORE.md`. Migración física post-FEDER.
> Disidentes ChatGPT + Kimi: `plugins/enterprise/` (argumentan plugin system existente).
>
> **Consenso Q5 — Benchmarks sintéticos (6/8):**
> Ejecutar en VirtualBox con disclaimer explícito: 'VirtualBox Synthetic Baseline — lower bound only'.
> Valor: detección de regresiones, calibración HWM, validación metodológica para paper.
> NO publicar como throughput de producción. Claude + Kimi en disidencia (datos ya en paper DAY 145).
>
> **Nuevas deudas registradas:**
> `DEBT-AUTONOMY-CRYPTO-INTEGRATION-001` (P0 DAY 156): integración en `etcd-server/main.cpp`.
> `DEBT-ENTERPRISE-LAYOUT-001` (post-FEDER): mover vault_client a `enterprise/`.
> `DEBT-BENCHMARK-SYNTHETIC-VIRTUALBOX-001` (P2 pre-FEDER): harness de benchmark con disclaimer.
>
> ChatGPT — transición arquitectónica: 'El sistema empieza a comportarse como una plataforma
> resiliente distribuida. Reconciliación, ownership único, deterministic enforcement,
> local-first autonomy y explicit state propagation son ahora más importantes que nuevas features.'
>
> 'La autonomía no se delega; se coordina. El IPC no es un detalle de implementación;
> es un pacto de localidad. Y el benchmark no mide mentiras: mide metodología.' — Qwen · DAY 155"
> — Consejo de Sabios (8/8) · DAY 155 · v0.9.0-day155

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

## 🆕 Entradas DAY 170 — community_id + backlog research/resilience

### DEBT-ZEEK-COMMUNITY-ID-PROVISION-001 — Persistir community_id en provision zeek
**Estado:** CERRADO — DAY 170 · **P1** (commits 6930abb2 + 6c parche raiz; verificado: local.zeek site/ trae @load community-id-logging + redef seed=0 tras `vagrant provision zeek`, idempotente)
`@load policy/protocols/conn/community-id-logging` + `redef CommunityID::seed=0` deben inyectarse en la provision del Vagrantfile de `experiments/zeek-comparative/`. Hoy es edicion manual volatil: se pierde en `vagrant destroy/up` y el join cross-tool falla en silencio. Verificado DAY 170: Zeek 8.2.0 emite `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` identico al oraculo pycommunityid con seed 0, sobre flujo Neris `147.32.84.165:1027 -> 74.125.232.195:80`.
**Test de cierre:** `vagrant destroy && up` en VM zeek -> conn.log trae columna community_id poblada sin intervencion manual.

### BACKLOG-RESILIENCE-ZMQ-LIMITS-001 — Endurecimiento ZMQ en 3 niveles
**Estado:** Diferido · **Tipo:** BACKLOG (no DEBT) · **Bloqueado por:** ADR-048 (etcd HA)
Heartbeat + fallback-to-etcd instrumentado (Nivel 1) -> ADR formal (Nivel 2) -> eval JetStream condicional al contador (Nivel 3). El propio Nivel 1 es el experimento que decide si el Nivel 3 existe. Detalle: `docs/BACKLOG-RESILIENCE-ZMQ-LIMITS-001.md`.

### BACKLOG-RESEARCH-KALMAN-001 — Kalman como sensor-fusion pre-XGBoost
**Estado:** RESEARCH/FUTURE · **Prereq:** aRGus+Suricata+Zeek+Wazuh+Neo4j integrados
Filtro de Kalman para fusion multi-fuente (7 casos de uso: anomaly scoring, correlacion temporal, slow scans, sensor fusion del ensemble...). Pregunta abierta critica: derivar Q/R/P0 del dataset sintetico DeepSeek antes de usarlo en el ensemble. Detalle: `docs/experiments/BACKLOG-RESEARCH-KALMAN-001.md`.

---

## 📝 Notas del Consejo de Sabios — DAY 170 (8/8)

> "DAY 170 — Cierre community_id cross-sensor + saneamiento BACKLOG + ritual del Consejo. Veredicto 8/8: aprobado con nota alta. El community_id pasa de campo del protobuf a invariante de identidad operacional verificable.
>
> **community_id sellado en los tres sensores de red:** aRGus (nativo, 8/8 tests contra oráculo pycommunityid v1.5.0 byte a byte, campo protobuf field 18), Zeek 8.2.0 (provisión local.zeek site/ con @load community-id-logging + redef CommunityID::seed=0) y Suricata 7.0.10 (community-id:yes + community-id-seed:0 en suricata.yaml). Diana E2E: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E= sobre flujo Neris 147.32.84.165:1027 -> 74.125.232.195:80. Seed 0 explícito garantizado por provisión en los tres. DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 y DEBT-ARGUSPP-COMMUNITY-ID-001 CERRADAS.
>
> **De-duplicación BACKLOG (DEBT-DOCS-BACKLOG-DEDUP-001 CERRADA):** corrupción arrastrada desde DAY 158 (append manual cat>>, no el script). 5336->2839 líneas. Lección elevada a regla: integridad documental se verifica con `grep secciones | sort | uniq -d` sobre el fichero completo, no con `grep -c` de cabecera. Idempotencia de provisión por LÍNEA, no por bloque.
>
> **Consenso 8/8 en las tres preguntas de arquitectura (sin segunda pasada):**
>
> **P1 — Wazuh <-> red:** (A)+(C). Descartar (B) como base. Grafo de doble arista: flujo<->flujo por community_id (determinista), host<->flujo por nodo Host identificado por host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal. Ventana host<->red más laxa y causal-bidireccional que red<->red. NAT = agujero peligroso: menú de mecanismos (Translation node / agent_id / proceso+puerto_local / fallback temporal), SIEMPRE anotando en grafo y log el método usado y su confianza. (B) solo enriquecimiento oportunista.
>
> **P2 — Invariante seed:** gate de arranque P0 (análogo a NTP) + health-check de huérfanos continuo. Refinamiento Alonso+Qwen+Gemini: el gate se basa en el DATA-PLANE (el community_id que cada componente EMITE en runtime sobre un flujo de referencia), NO en lectura de config JSON/yaml — el fichero puede mentir; engañar al pipeline exigiría modificar binarios/plugins. Este enfoque unifica el gate sobre los tres sensores y disuelve la bifurcación que propuso Gemini (gate-estricto-aRGus + canario-pasivo-externos), resolviendo su preocupación de fragilidad ante cambios de versión por otra vía.
>
> **P3 — Identidad de flujo multi-nodo:** clave compuesta CON componente temporal. Refinamiento (objeción DeepSeek + formalización Gemini/Qwen): la 5-tupla se recicla en el tiempo, luego (node_id, community_id) tampoco es único. Identidad del nodo-flujo en Neo4j = flow_uid = hash(node_id || community_id || flow_start_window). community_id permanece como propiedad indexada (clave de correlación intra-nodo + verificable contra oráculo), nunca como identidad de nodo.
>
> **DAY 171 aprobado sin bloqueos:** cross-check E2E tres ventanas (cliente .50 replaya Neris; aRGus+Suricata+Zeek capturan en paralelo de eth1; los 3 deben emitir el mismo community_id sobre el mismo paquete). Añadidos del Consejo: registrar timestamp relativo de emisión + nº de paquete/flow por sensor; caso de IPs invertidas (respuesta); NAT simulado si es posible.
>
> 'El verdadero activo no es el hash — es que todos los sensores producen exactamente el mismo hash.' — ChatGPT · DAY 170"
> — Consejo de Sabios (8/8) · DAY 170

### Entradas DAY 170 derivadas del Consejo — ADRs + DEBTs

> **Nota de numeración (lección de hoy):** ADR-050 ya está reservado en este BACKLOG para la sesión MITRE + corrección cripto telemetría (DAY 169, pendiente redacción). Por tanto las dos ADRs nuevas toman 051 y 052. Verificado contra el BACKLOG antes de asignar.

#### ADR-051 — Seed Parity Gate & Correlation Health (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 170 (Consejo 8/8) · recoge P2
Gate de arranque P0 basado en data-plane: el correlation-engine mide el community_id que cada sensor EMITE en runtime sobre un flujo de referencia y verifica paridad. Divergencia -> `SEED_MISMATCH`, abort. Health-check continuo: métrica `community_id.orphan_rate` (flujos sin corroboración cross-sensor cuando deberían tenerla); caída de matches a ~0 u orfandad sistemática >umbral en N ventanas -> alerta CRITICAL. NO lee config JSON/yaml — el fichero puede mentir. Flujo: borrador -> Consejo -> aprobación -> implementación.

#### ADR-052 — Multi-node Flow Identity & Host<->Net Correlation (RATIFICADA v3.2 — DAY 173)
**Estado:** ✅ RATIFICADA v3.2 (Consejo 8/8) — DAY 173. Ver sección "RATIFICADO DAY 173" arriba. · recoge P3 + P1
Identidad del nodo-flujo en Neo4j = `flow_uid = hash(node_id || community_id || flow_start_window)`. community_id como propiedad indexada (clave de correlación intra-nodo). Doble arista: flujo<->flujo (community_id, determinista) + host<->flujo (host_id/agent_id canónico + ventana temporal laxa causal-bidireccional). NAT: menú de mecanismos con anotación de método y confianza en grafo+log. Esquema Neo4j compartido -> P1 y P3 en un mismo ADR (separable a ADR-053 si el Consejo lo pide).

#### DEBT-NEO4J-FLOW-KEY-001 — Clave de flujo temporal compuesta en Neo4j
**Severidad:** 🔴 P0 esquema — bloquea diseño del correlation-engine
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · recoge ADR-052
`flow_uid = hash(node_id || community_id || flow_start_window)` como identidad del nodo-flujo. `node_id` propiedad obligatoria en :NetworkFlow, :Alert, :TelemetryEvent. Constraint compuesto nativo Neo4j 5.x. Decidirlo con el grafo vacío es gratis; retrofitear con datos en producción es doloroso (unánime). Correlación intra-nodo por community_id; identidad/dedup inter-nodo por flow_uid.
**Test de cierre:** dos flujos misma 5-tupla en nodos distintos -> flow_uid distinto. Misma 5-tupla reciclada en el tiempo en el mismo nodo -> flow_uid distinto.
**Estimación:** 1 sesión (diseño esquema + constraint) antes de poblar el grafo.

#### DEBT-CORRELATION-SEED-GATE-001 — Gate paridad seed data-plane + health-check huérfanos
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · recoge ADR-051
Implementación del gate P0 data-plane + health-check `community_id.orphan_rate`. Prerequisito: correlation-engine con al menos dos sensores emitiendo sobre el mismo flujo.
**Test de cierre:** sensor con seed!=0 -> SEED_MISMATCH, abort. Orfandad sistemática inyectada -> alerta CRITICAL.
**Estimación:** 1-2 sesiones.

#### BACKLOG-RESEARCH-NAT-HOSTNET-001 — Puente host<->red bajo NAT
**Estado:** RESEARCH/FUTURE — DAY 170 (Consejo 8/8) · recoge P1
Mecanismos de correlación host<->red cuando IP interna (Wazuh) != IP observada (sensor red): Translation node con logs NAT / identidad agent_id-hostname / puente (proceso, puerto_local, timestamp) / fallback temporal degradado. SIEMPRE anotar en grafo y log el método usado y su confianza. Cubrir explícitamente los casos correctos, incorrectos e incompletos de medida. Nunca fallo silencioso por IP no coincidente. Prereq: Wazuh integrado (DEBT-ARGUSPP-WAZUH-001).

## DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1)

**Qué:** medir el `source_wait_timeout` real por sensor = wall-clock de *aparición*
del cid diana relativo a T0 (lanzamiento de tcpreplay). NO el timestamp interno de
inicio de flujo (eso es A, ya hecho como sanity check).

**Por qué:** ADR-046 v4 usa 5s/10s/20s (argus/suricata/zeek) SUPUESTOS. El timeout
real es retardo-de-emisión: Suricata `flow.timeout`, Zeek cierre TCP. aRGus casi-real.
Calibrar con dato medido en vez de número inventado.

**Cómo:** refactor verificador one-shot → poll. T0 = `time.monotonic()` al inyectar;
sondear `read_*` en bucle corto hasta que el cid diana aparezca por sensor; estampar
primer éxito; Δ = t_aparición − T0.

**Rigor (no negociable):** medir sobre 2-3 FORMAS de flujo (sesión corta / larga /
múltiples flujos concurrentes), NO una sola muestra replayada. El timeout depende de
la forma del flujo. Resultado = suelo medido + margen explícito, NO distribución,
hasta tener tráfico real. Documentar como tal en ADR-046 v4.

**Alimenta:** `source_wait_timeout` argus/suricata/zeek en ADR-046 v4 (reemplaza supuestos).
**Prereq:** NTP P0 (cerrado DAY 167 — garantiza comparabilidad cross-VM). Setup multi-VM VERDE.
**Relación:** complementa DEBT-CORRELATION-SEED-GATE-001 (ambos data-plane).
Origen: nota DELTA DE TIEMPOS del Consejo DAY 170.

**Hallazgo DAY 172:** el TSV de cross-check de aRGus estampa timestamp SINTÉTICO
(contador 1.7e18+N, no system_clock real) — community_id_log.cpp corre bajo reloj
inyectado en el build de cross-check. Por eso A (minar artefacto) no aplica a aRGus.
B debe medir aRGus por wall-clock de aparición en el host (time.monotonic), no por
el ts interno. Verificar también si el path de PRODUCCIÓN usa reloj real o heredó el inyectado.
**Hallazgo DAY 172 (corrida real):** A revela que Suricata (eve.json .timestamp en
eventos flow = FIN de flujo / flow.timeout) y Zeek (conn.log ts = INICIO de conexión)
NO anclan el timestamp al mismo punto del ciclo de vida. Spreads observados 9.7ms
(flujos cortos) a 116s (flujos largos, dominados por flow.timeout de Suricata). El
'delta de inicio de flujo' que A pretendía medir NO es medible restando estos dos
campos: miden eventos distintos. CONSECUENCIA para B: source_wait_timeout debe medirse
por WALL-CLOCK de aparición (time.monotonic en host), nunca por timestamps internos —
quedan confirmados como no comparables entre sensores. CONSECUENCIA para ADR-046 v4:
los 5/10/20s supuestos son casi seguro muy bajos para Suricata en flujos largos.

## DEBT-MAKEFILE-CID-CROSSCHECK-001
target dedicado que arranque el sniffer con la env var, para que el cross-check sea reproducible con un make y no dependa de tu memoria

---

## ADR-046 v3 — aRGus++ Multi-Source Pipeline (DAY 158)

> Aprobado Consejo 8/8. Supersede ADR-046 v1 y v2.
> Principio rector: **la crisis es la ventana de correlación**.
> Disparadores múltiples (aRGus/Suricata/Zeek/Wazuh).
> community_id como primary key de correlación cross-tool.
> Secuencia: v1.0 (aRGus only) → v1.1 (+ Suricata) → v1.2 (+ Zeek) → v2.0 (+ Wazuh + Neo4j).

| ID | Descripción | Prioridad | Estado |
|---|---|---|---|
| DEBT-ARGUSPP-NTP-001 | NTP+chrony en todos los nodos. Health-check rechaza arranque si offset >1s. Gate P0 del correlation-engine. | P0 | OPEN |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | Habilitar community_id en Suricata y Zeek desde configuración inicial. Primary key del join cross-tool. | P0 en v1.1 | CERRADO DAY170 — seed=0 explícito en aRGus(nativo)+Zeek(local.zeek)+Suricata(suricata.yaml) |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS. eve.json → rag-security → servidor. | P1 | OPEN |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek en Vagrantfile + EMECAS. conn/dns/ssl/files.log → servidor. | P1 | OPEN |
| DEBT-ARGUSPP-CORRELATION-001 | Implementación C++20 correlation-engine v1.0. Disparador aRGus + buffer + flush Parquet. Esquema Arrow con columnas opcionales para 4 fuentes desde v1.0. | P1 | OPEN |
| DEBT-ARGUSPP-TIMEOUT-CONFIG-001 | Mapa source_wait_timeout configurable por JSON (argus:5s, suricata:10s, zeek:20s, wazuh:90s). crisis_idle_timeout:120s separado. late_arrival:true para Wazuh tardío. | P1 en v1.0 | OPEN |
| DEBT-ARGUSPP-NEO4J-TTL-001 | TTL + compactación + cold storage Neo4j. Prerequisito de producción real. Grafo puede crecer explosivamente sin esto. | P1 pre-producción | OPEN |
| DEBT-ARGUSPP-RESOURCE-001 | Medir CPU/RAM/disco de las 4 fuentes en RPi5 y N100 bajo carga MITRE. Prerequisito para definir tiers de despliegue. | P1 con hardware | OPEN |
| DEBT-ARGUSPP-MITRE-001 | mitre-generator + Atomic Red Team. Ver ADR-047 (pendiente redacción). | P1 post-hardware | OPEN |
| DEBT-ARGUSPP-BENCHMARK-001 | Re-ejecutar BACKLOG-BENCHMARK-CAPACITY-001 con las 4 fuentes activas. | P1 post-hardware | OPEN |
| DEBT-ARGUSPP-WAZUH-001 | Wazuh agent en edge + manager en servidor central. P2 post-medición de recursos en hardware físico. | P2 | OPEN |
| DEBT-PAPER-SYNTHETIC-001 | Sección paper v24: curva F1 vs ratio académico/sintético. Refs: Arp et al.[2022], Wagner et al.[2022], Sommer&Paxson[2010]. | P2 | OPEN |
|DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1)| OPEN |
**ADR-047 pendiente:** mitre-generator — orquestador de experimentos MITRE ATT&CK para ground truth reproducible. Consenso 8/8 Consejo DAY 158.

**Nota arquitectónica (DAY 158):** Cada herramienta genera su propio Parquet con su propio esquema.
El esquema final en Neo4j es aditivo. No se puede predefinir el esquema de Suricata/Zeek/Wazuh
hasta que se integren. community_id es el pegamento entre esquemas distintos.
Los timeouts del correlation-engine controlan cuánto espera el servidor a que converjan las señales
una vez abierta la CrisisWindow — no controlan el período de recolección del edge (que es continuo).
Una CrisisWindow es un registro de evento, no un dataset de entrenamiento. Los datasets de
entrenamiento se acumulan de cientos/miles de CrisisWindows a lo largo de días/semanas (ADR-040).


### DEBT-HARDWARE-STORAGE-001 — NVMe obligatorio en nodos de producción
**Severidad:** 🔴 P0 pre-producción
**Estado:** ABIERTO — DAY 160
**Componente:** hardware spec + deployment.yaml + ADR-048

SD cards en RPi5 bajo carga NDR continua (logs, Parquet, crypto cache, eventos)
fallan en semanas/meses por agotamiento de ciclos de escritura NAND.

**Solución:** RPi5 + NVMe HAT + SSD M.2 128GB (~110€/nodo vs ~90€ con SD).
- argus-collector: 256GB recomendado (acumula Parquet multi-engine)
- Resto de nodos: 128GB suficiente
- SD card: solo para recovery/imaging inicial, nunca en producción

**Campo en deployment.yaml:** `storage_type: nvme`
**Campo en hardware_profile.yml:** prerequisito de deploy en producción
**Impacto en BACKLOG-DEPLOY-CALCULATOR-001:** parámetros de escritura
  (HWM, buffer sizes, flush intervals) dependen del tipo de almacenamiento.

**Test de cierre:** nodo con NVMe desplegado + pipeline corriendo 72h
  sin degradación de escritura medible.
