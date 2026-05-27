#!/usr/bin/env python3
# update_day156.py — Actualiza README.md y BACKLOG.md con los resultados del DAY 156
# Ejecutar desde la raíz del repo: python3 tools/update_day156.py
# Idempotente: detecta si el parche ya fue aplicado antes de modificar.

from pathlib import Path
import sys

OK  = "✅"
ERR = "❌"
INF = "🔧"

def fail(msg):
    print(f"{ERR} {msg}", file=sys.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────
README = Path("README.md")
if not README.exists():
    fail("README.md no encontrado — ejecutar desde la raíz del repo")

readme = README.read_text()

# Guard idempotencia
if "DAY 156" in readme and "v0.9.1-day156" in readme:
    print(f"{OK} README.md ya actualizado — skip")
else:
    # 1. Badge version
    readme = readme.replace(
        "[![Hardened](https://img.shields.io/badge/Security-v0.8.0--day151-brightgreen)]",
        "[![Hardened](https://img.shields.io/badge/Security-v0.9.1--day156-brightgreen)]"
    )

    # 2. Tag en línea de estado
    readme = readme.replace(
        "✅ `main` is tagged `v0.9.0-day155`.",
        "✅ `main` is tagged `v0.9.1-day156`."
    )

    # 3. Encabezado Estado actual
    readme = readme.replace(
        "## Estado actual — DAY 155 (2026-05-17)",
        "## Estado actual — DAY 156 (2026-05-18)"
    )

    # 4. Tag activo + keypair
    readme = readme.replace(
        "**Tag activo:** `v0.9.0-day155` | **Branch activa:** `main`",
        "**Tag activo:** `v0.9.1-day156` | **Branch activa:** `main`"
    )

    # 5. Test count en pipeline
    readme = readme.replace(
        "`make test-all`: ALL TESTS COMPLETE (65/65 PASSED — 0 FAILED) ✅",
        "`make test-all`: ALL TESTS COMPLETE (50/50 firewall · 3/3 etcd-server · 9/9 sniffer · 10/10 ml-detector · 8/8 rag-ingester · 1/1 argus-network-isolate) ✅"
    )

    # 6. Hitos DAY 155 — añadir DAY 156 justo antes
    hito_156 = """### Hitos DAY 156 🎉
- **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA** — `CryptoAutonomyStateMachine` + `AutonomyPublisher` integrados en `etcd-server/main.cpp`. Health-check loop 5s dispara `on_vault_unreachable/restored`. `FirewallAutonomyReactor` + `AutonomySubscriber` integrados en `firewall-acl-agent/main.cpp`. `AutonomyConfig.zmq_endpoint` añadido a struct y parser. `autonomy_publisher.h` añadido al install target de CMake.
- **Test B (unitario): 7/7 PASSED** — `CryptoAutonomyStateMachine` + `AutonomyPublisher` via ZMQ real. T1-T7 incluyendo `HealthCheckLoopSimulation`.
- **Test A (E2E): 4/4 PASSED** — Pipeline `Publisher→IPC→Subscriber→Reactor` dry_run. `VaultKoTriggersAutonomousMode`, `VaultRestoredLiftsAutonomousMode`, `FullCycleNormalAutonomousReconcileNormal`, `SubscriberRunsStableWithoutEvents`.
- **Fix ZMQ slow joiner** — publisher debe hacer `bind()` ANTES de que cualquier subscriber conecte. Regla permanente para todos los pares PUB/SUB del proyecto.
- **EMECAS DAY 156 VERDE** — `vagrant destroy → up → make bootstrap → make test-all` — TODO VERDE. 50/50 firewall, 3/3 etcd-server, 9/9 sniffer, 10/10 ml-detector, 8/8 rag-ingester.
- **ADR-046 PENDING-REVISION** — Multi-Source Enriched Pipeline aRGus++. Tres condiciones para cierre: §Label leakage policy, §Deployment matrix RPi5 vs edge server, §8 datos empíricos o hipótesis.

"""
    readme = readme.replace(
        "### Hitos DAY 155 🎉",
        hito_156 + "### Hitos DAY 155 🎉"
    )

    # 7. Próxima frontera — actualizar lista
    readme = readme.replace(
        "1. **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 P0** — Integrar `CryptoAutonomyStateMachine` + `AutonomyPublisher` en `etcd-server/main.cpp`. Consejo 6/8: etcd-server como propietario para FEDER.",
        "1. ✅ **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA DAY 156**"
    )
    readme = readme.replace(
        "2. **DEBT-AUTONOMY-STATE-PERSISTENCE-001 P1** — Estado firmado Ed25519 en `/run/argus/crypto-autonomy-state.json` en tmpfs.",
        "2. **DEBT-AUTONOMY-STATE-PERSISTENCE-001 P1** — Estado firmado Ed25519 en `/var/lib/argus/crypto-autonomy-state.json` (Consejo 6/8: fichero regular + fsync, NO tmpfs). Arranque desde AUTONOMOUS si firma válida y timestamp < 24h."
    )

    # 8. Milestone DAY 156
    readme = readme.replace(
        "- ✅ DAY 155: **DEBT-FIREWALL-DENY-SELECTIVE-001 · DEBT-AUTONOMY-ZMQ-EVENTS-001 · BACKLOG-ZMQ-TUNING-001 · 49/49 tests · EMECAS HARDENED PASSED · v0.9.0-day155** 🎉",
        "- ✅ DAY 155: **DEBT-FIREWALL-DENY-SELECTIVE-001 · DEBT-AUTONOMY-ZMQ-EVENTS-001 · BACKLOG-ZMQ-TUNING-001 · 49/49 tests · EMECAS HARDENED PASSED · v0.9.0-day155** 🎉\n- ✅ DAY 156: **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 · Test B 7/7 + Test A 4/4 · Fix ZMQ slow joiner · EMECAS VERDE 50/50 · v0.9.1-day156** 🎉"
    )

    # 9. Footer fecha
    readme = readme.replace(
        "*DAY 155 — 17 Mayo 2026 · main @ v0.9.0-day155*",
        "*DAY 156 — 18 Mayo 2026 · main @ v0.9.1-day156*"
    ) if "*DAY 155 — 17 Mayo 2026" in readme else readme

    README.write_text(readme)
    print(f"{OK} README.md actualizado — DAY 156 · v0.9.1-day156")


# ─────────────────────────────────────────────────────────────────────────────
# docs/BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────
BACKLOG = Path("docs/Backlog.md")
if not BACKLOG.exists():
    BACKLOG = Path("docs/BACKLOG.md")
if not BACKLOG.exists():
    fail("docs/Backlog.md / docs/BACKLOG.md no encontrado")

backlog = BACKLOG.read_text()

if "DAY 156" in backlog and "DEBT-AUTONOMY-CRYPTO-INTEGRATION-001" in backlog and "CERRADA DAY 156" in backlog:
    print(f"{OK} BACKLOG.md ya actualizado — skip")
else:

    # ── 1. Cerrar DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 ────────────────────────
    backlog = backlog.replace(
        "DEBT-AUTONOMY-CRYPTO-INTEGRATION-001:     0% ⏳  DAY 155 — integración main.cpp pendiente (etcd-server DAY 156)",
        "DEBT-AUTONOMY-CRYPTO-INTEGRATION-001:   100% ✅  DAY 156 — CERRADA. 7/7 + 4/4 tests. EMECAS verde."
    )

    # ── 2. Actualizar DEBT-AUTONOMY-STATE-PERSISTENCE-001 (tmpfs → /var/lib) ──
    backlog = backlog.replace(
        """### DEBT-AUTONOMY-STATE-PERSISTENCE-001 — Estado autonomía sin persistencia firmada
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Grok, Consejo)
**Componente:** `CryptoAutonomyStateMachine`

Al entrar en `AUTONOMOUS`, escribir `/run/argus/crypto-autonomy-state.json` firmado Ed25519 con timestamp + fingerprint. Al recuperar, validar la firma antes de reconciliar. Previene que un atacante manipule el estado de autonomía persistido.

**Test de cierre:** entrar en AUTONOMOUS → fichero escrito y firmado. Manipulación detectada.
**Estimación:** 1h""",
        """### DEBT-AUTONOMY-STATE-PERSISTENCE-001 — Estado autonomía sin persistencia firmada
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
**Estimación:** 1 sesión DAY 157"""
    )

    # ── 3. Actualizar estado en tabla de progreso ──────────────────────────────
    backlog = backlog.replace(
        "DEBT-AUTONOMY-STATE-PERSISTENCE-001:      0% ⏳  P1 (estado autonomía sin persistencia firmada)",
        "DEBT-AUTONOMY-STATE-PERSISTENCE-001:      0% ⏳  P1 DAY 157 — /var/lib/argus/ + fsync + Ed25519 (Consejo 6/8)"
    )

    # ── 4. Añadir DEBT-KEYPAIR-LIFECYCLE-PROD-001 ─────────────────────────────
    nueva_deuda_keypair = """
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

"""

    # Insertar antes de DEBT-BOOTSTRAP-STATUS-SIGNATURE-001
    backlog = backlog.replace(
        "### DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 — Bootstrap status sin firma Ed25519",
        nueva_deuda_keypair + "### DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 — Bootstrap status sin firma Ed25519"
    )

    # ── 5. Añadir en tabla de progreso ────────────────────────────────────────
    backlog = backlog.replace(
        "DEBT-BOOTSTRAP-STATUS-SIGNATURE-001:      0% ⏳  P1 pre-FEDER (bootstrap status sin firma)",
        "DEBT-KEYPAIR-LIFECYCLE-PROD-001:           0% ⏳  P1 pre-FEDER (3 niveles: dev/staging/prod — Consejo 8/8)\nDEBT-BOOTSTRAP-STATUS-SIGNATURE-001:      0% ⏳  P1 pre-FEDER (bootstrap status sin firma)"
    )

    # ── 6. Añadir sección CERRADO DAY 156 ─────────────────────────────────────
    seccion_day156 = """## ✅ CERRADO DAY 156

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

"""

    # Insertar antes de "## ✅ CERRADO DAY 155"
    if "## ✅ CERRADO DAY 155" in backlog:
        backlog = backlog.replace(
            "## ✅ CERRADO DAY 155",
            seccion_day156 + "## ✅ CERRADO DAY 155"
        )
    else:
        # Insertar antes de "## ✅ CERRADO DAY 151"
        backlog = backlog.replace(
            "## ✅ CERRADO DAY 151",
            seccion_day156 + "## ✅ CERRADO DAY 151"
        )

    # ── 7. Reglas permanentes DAY 156 ─────────────────────────────────────────
    reglas_day156 = """- **REGLA PERMANENTE (DAY 156 — Consejo 8/8):** En ZMQ PUB/SUB, el publisher debe hacer `bind()` ANTES de que cualquier subscriber haga `connect()`. En tests: crear el publisher en `SetUp()` del fixture antes de `start_subscriber()`. El slow joiner de ZMQ pierde mensajes silenciosamente si el orden se invierte. Ver `docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md`.
- **REGLA PERMANENTE (DAY 156 — Consejo 6/8):** El estado de `CryptoAutonomyStateMachine` se persiste en `/var/lib/argus/crypto-autonomy-state.json` con fsync atómico y firma Ed25519. tmpfs es insuficiente para hospitalario (desaparece en reboot no planificado durante AUTONOMOUS). Un reboot durante AUTONOMOUS es el escenario de ataque exacto que hay que cubrir.
- **REGLA PERMANENTE (DAY 156 — Consejo 8/8):** En producción FEDER (CPD UEx), el keypair Ed25519 se genera UNA SOLA VEZ durante el bootstrap físico del nodo. `make bootstrap` con `ARGUS_ENV=prod` falla explícitamente si no existe keypair preexistente — nunca genera silenciosamente. Ver DEBT-KEYPAIR-LIFECYCLE-PROD-001.

"""

    # Insertar reglas DAY 156 antes de las reglas DAY 155
    backlog = backlog.replace(
        "- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** `etcd-server` es el proceso propietario",
        reglas_day156 + "- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** `etcd-server` es el proceso propietario"
    )

    # ── 8. Notas del Consejo DAY 156 ──────────────────────────────────────────
    notas_day156 = """## 📝 Notas del Consejo de Sabios — DAY 156 (8/8)

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

"""

    # Insertar antes de las notas DAY 155
    backlog = backlog.replace(
        "## 📝 Notas del Consejo de Sabios — DAY 155 (8/8)",
        notas_day156 + "## 📝 Notas del Consejo de Sabios — DAY 155 (8/8)"
    )

    # ── 9. Actualizar fecha del backlog ───────────────────────────────────────
    backlog = backlog.replace(
        "*Última actualización: DAY 151 — 14 Mayo 2026*",
        "*Última actualización: DAY 156 — 18 Mayo 2026*"
    )
    backlog = backlog.replace(
        "*DAY 155 — 17 Mayo 2026 · main @ v0.9.0-day155*",
        "*DAY 156 — 18 Mayo 2026 · main @ v0.9.1-day156*"
    )

    BACKLOG.write_text(backlog)
    print(f"{OK} BACKLOG.md actualizado — DAY 156")

print(f"\n{OK} Actualizaciones completadas.")
print("Verificar con: git diff README.md docs/Backlog.md")