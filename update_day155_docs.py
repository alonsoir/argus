#!/usr/bin/env python3
# =============================================================================
# update_day155_docs.py — Actualización docs DAY 155
# Ejecutar desde la raíz del proyecto: python3 update_day155_docs.py
# =============================================================================
import re

# =============================================================================
# BACKLOG.md
# =============================================================================

with open("docs/BACKLOG.md", "r") as f:
    backlog = f.read()

# ── 1. Estado global: cerrar deudas DAY 155 ──────────────────────────────────

replacements_backlog = [
    # DEBT-FIREWALL-DENY-SELECTIVE-001
    (
        "DEBT-FIREWALL-DENY-SELECTIVE-001:          0% ⏳  P0 DAY 155 (regla actual rompe hospitales)",
        "DEBT-FIREWALL-DENY-SELECTIVE-001:        100% ✅  DAY 155 — cadena argus-autonomy, whitelist obligatoria JSON",
    ),
    # DEBT-AUTONOMY-ZMQ-EVENTS-001
    (
        "DEBT-AUTONOMY-ZMQ-EVENTS-001:             0% ⏳  P1 DAY 155 (ZMQ pub/sub directo)",
        "DEBT-AUTONOMY-ZMQ-EVENTS-001:           100% ✅  DAY 155 — AutonomyPublisher + AutonomySubscriber (ipc://)",
    ),
    # BACKLOG-ZMQ-TUNING-001
    (
        "BACKLOG-ZMQ-TUNING-001:                  0% ⏳  pre-FEDER",
        "BACKLOG-ZMQ-TUNING-001:                100% ✅  DAY 155 — HWM + RECONNECT_IVL en todos los sockets",
    ),
    # DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 (nueva)
    # Añadir entrada nueva en el estado global justo después de la línea de ZMQ-EVENTS
    (
        "DEBT-AUTONOMY-ZMQ-EVENTS-001:           100% ✅  DAY 155 — AutonomyPublisher + AutonomySubscriber (ipc://)",
        "DEBT-AUTONOMY-ZMQ-EVENTS-001:           100% ✅  DAY 155 — AutonomyPublisher + AutonomySubscriber (ipc://)\n"
        "DEBT-AUTONOMY-CRYPTO-INTEGRATION-001:     0% ⏳  DAY 155 — integración main.cpp pendiente (etcd-server DAY 156)",
    ),
]

for old, new in replacements_backlog:
    if old in backlog:
        backlog = backlog.replace(old, new, 1)
        print(f"✅ BACKLOG estado global: actualizado")
    else:
        print(f"⚠️  Patrón no encontrado (backlog estado global): {old[:60]}...")

# ── 2. Sección deudas abiertas: cerrar DEBT-FIREWALL-DENY-SELECTIVE-001 ──────

old_debt_deny = """### DEBT-FIREWALL-DENY-SELECTIVE-001 — Regla default-deny demasiado agresiva
**Severidad:** 🔴 P0 — DAY 154 (Consejo 8/8 UNÁNIME)
**Estado:** ABIERTO — CERRAR EN DAY 155
**Componente:** `firewall-acl-agent/src/core/autonomy_reactor.cpp`"""

new_debt_deny = """### DEBT-FIREWALL-DENY-SELECTIVE-001 — Regla default-deny selectiva
**Severidad:** ✅ CERRADA DAY 155 — Consejo 8/8 unánime
**Estado:** CERRADO — v0.9.0-day155
**Componente:** `firewall-acl-agent/src/core/autonomy_reactor.cpp`"""

if old_debt_deny in backlog:
    backlog = backlog.replace(old_debt_deny, new_debt_deny, 1)
    print("✅ BACKLOG: DEBT-FIREWALL-DENY-SELECTIVE-001 marcada cerrada")
else:
    print("⚠️  Patrón DEBT-FIREWALL-DENY-SELECTIVE-001 no encontrado en deudas abiertas")

# ── 3. Sección deudas abiertas: cerrar DEBT-AUTONOMY-ZMQ-EVENTS-001 ─────────

old_debt_zmq = """### DEBT-AUTONOMY-ZMQ-EVENTS-001 — Transiciones de autonomía no emiten eventos ZeroMQ
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Grok, Consejo)
**Componente:** `CryptoAutonomyStateMachine` + ZeroMQ bus"""

new_debt_zmq = """### DEBT-AUTONOMY-ZMQ-EVENTS-001 — ZMQ pub/sub para transiciones de autonomía
**Severidad:** ✅ CERRADA DAY 155
**Estado:** CERRADO — v0.9.0-day155 · Integración main.cpp pendiente: DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
**Componente:** `common/autonomy_publisher.h/.cpp` + `firewall-acl-agent/autonomy_subscriber.hpp/.cpp`"""

if old_debt_zmq in backlog:
    backlog = backlog.replace(old_debt_zmq, new_debt_zmq, 1)
    print("✅ BACKLOG: DEBT-AUTONOMY-ZMQ-EVENTS-001 marcada cerrada")
else:
    print("⚠️  Patrón DEBT-AUTONOMY-ZMQ-EVENTS-001 no encontrado en deudas abiertas")

# ── 4. Actualizar cabecera fecha ──────────────────────────────────────────────

backlog = backlog.replace(
    "*DAY 154 — 16 Mayo 2026 · main @ v0.8.0-adr045*",
    "*DAY 155 — 17 Mayo 2026 · main @ v0.9.0-day155*",
)
print("✅ BACKLOG: cabecera fecha actualizada")

# ── 5. Añadir nueva deuda DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 ───────────────

new_debt_integration = """
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
"""

# Insertar antes de DEBT-ETCD-HA-QUORUM-001
marker = "### DEBT-ETCD-HA-QUORUM-001"
if marker in backlog:
    backlog = backlog.replace(marker, new_debt_integration + marker, 1)
    print("✅ BACKLOG: DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 añadida")
else:
    print("⚠️  Marker DEBT-ETCD-HA-QUORUM-001 no encontrado para inserción")

# ── 6. Añadir notas del Consejo DAY 155 ──────────────────────────────────────

consejo_day155 = """
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

"""

# Insertar antes de las notas del Consejo DAY 154
marker_consejo = "## 📝 Notas del Consejo de Sabios — DAY 154 (8/8)"
if marker_consejo in backlog:
    backlog = backlog.replace(marker_consejo, consejo_day155 + marker_consejo, 1)
    print("✅ BACKLOG: Notas Consejo DAY 155 añadidas")
else:
    print("⚠️  Marker notas Consejo DAY 154 no encontrado")

# ── 7. Añadir reglas permanentes DAY 155 ─────────────────────────────────────

new_permanent_rules = """- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** `etcd-server` es el proceso propietario de `CryptoAutonomyStateMachine` y `AutonomyPublisher` en despliegues FEDER. Un solo publisher por nodo garantiza coherencia de estado. Migración a `argus-crypto-daemon` documentada como deuda post-FEDER.
- **REGLA PERMANENTE (DAY 155 — Consejo 8/8):** El canal de autonomía (`argus.crypto.autonomy`) usa `ipc://` por defecto en edge nodes co-locados. El endpoint es configurable desde `firewall.json["autonomy"]["zmq_endpoint"]`. No introducir `tcp://` sin revisión del modelo de seguridad.
- **REGLA PERMANENTE (DAY 155 — Consejo 8/8):** El reconciliador de `AutonomySubscriber` re-aplica el último estado conocido. NUNCA consulta Vault/etcd en el ciclo de reconciliación. El intervalo es configurable desde `firewall.json["autonomy"]["reconcile_interval_sec"]` (default 90s).
- **REGLA PERMANENTE (DAY 155 — Consejo 6/8):** Código enterprise (`VaultClient`, `VaultProvider`) vive en `enterprise/` en la raíz del proyecto, paralelo a `common/`. El flag CMake `ARGUS_VAULT_ENABLED` controla `add_subdirectory(enterprise)`. La migración física es post-FEDER.
"""

# Insertar después de la última regla permanente DAY 144
marker_rules = "- **REGLA PERMANENTE (DAY 142 — macOS):** zsh intercepta"
if marker_rules in backlog:
    backlog = backlog.replace(
        marker_rules,
        new_permanent_rules + "\n" + marker_rules,
        1
    )
    print("✅ BACKLOG: Reglas permanentes DAY 155 añadidas")
else:
    print("⚠️  Marker reglas permanentes no encontrado")

with open("docs/BACKLOG.md", "w") as f:
    f.write(backlog)

print("\n✅ docs/BACKLOG.md actualizado\n")

# =============================================================================
# README.md
# =============================================================================

with open("README.md", "r") as f:
    readme = f.read()

# ── 1. Tag activo ─────────────────────────────────────────────────────────────

readme = readme.replace(
    "**Tag activo:** `v0.8.0-adr045` | **Branch activa:** `main`",
    "**Tag activo:** `v0.9.0-day155` | **Branch activa:** `main`",
)
print("✅ README: tag activo actualizado")

readme = readme.replace(
    "✅ `main` is tagged `v0.7.2-day149`.",
    "✅ `main` is tagged `v0.9.0-day155`.",
)

# ── 2. Hitos DAY 154 → añadir DAY 155 ────────────────────────────────────────

new_hitos_day155 = """### Hitos DAY 155 🎉
- **DEBT-FIREWALL-DENY-SELECTIVE-001 CERRADA** — Cadena dedicada `argus-autonomy`: lo→ESTABLISHED→CIDRs→DROP→INPUT. `whitelist_cidrs` obligatorio desde `firewall.json`. `AutonomyConfig` + `parse_autonomy()` fail-fast. 12/12 tests. 49/49 firewall tests verdes.
- **DEBT-AUTONOMY-ZMQ-EVENTS-001 CERRADA** — `AutonomyPublisher` (`common/`) + `AutonomySubscriber` (`firewall-acl-agent/`). Topic `argus.crypto.autonomy`. Transport `ipc:///run/argus/autonomy.sock`. 4/4 + 6/6 tests PASSED.
- **BACKLOG-ZMQ-TUNING-001 CERRADA** — HWM + RECONNECT_IVL en todos los sockets ZMQ del proyecto. Prerequisito de BACKLOG-BENCHMARK-CAPACITY-001 satisfecho.
- **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 registrada** — Integración en `etcd-server/main.cpp` pendiente (P0 DAY 156). Consejo 6/8: etcd-server como proceso propietario.
- **EMECAS HARDENED PASSED** — `-Werror` + `-O3` + `-flto` + producción limpio. AppArmor 6/6. Falco 11 reglas. BSR verificado. Tag `v0.9.0-day155`.

"""

marker_hitos = "### Hitos DAY 154 🎉"
if marker_hitos in readme:
    readme = readme.replace(marker_hitos, new_hitos_day155 + marker_hitos, 1)
    print("✅ README: Hitos DAY 155 añadidos")
else:
    print("⚠️  Marker hitos DAY 154 no encontrado")

# ── 3. Tabla deuda técnica: actualizar entradas DAY 155 ──────────────────────

readme = readme.replace(
    "| DEBT-FIREWALL-DENY-SELECTIVE-001 | 🔴 P0 DAY 155 | Regla actual rompe hospitales — selectiva |",
    "| DEBT-FIREWALL-DENY-SELECTIVE-001 | ✅ CERRADA DAY 155 | Cadena argus-autonomy selectiva, whitelist JSON |",
)
readme = readme.replace(
    "| DEBT-AUTONOMY-ZMQ-EVENTS-001 | 🟡 P1 | ZMQ pub/sub `argus.crypto.autonomy` (inproc/ipc) |",
    "| DEBT-AUTONOMY-ZMQ-EVENTS-001 | ✅ CERRADA DAY 155 | AutonomyPublisher + AutonomySubscriber (ipc://) |",
)
print("✅ README: tabla deuda técnica actualizada")

# ── 4. Sección "Próxima frontera" ─────────────────────────────────────────────

old_frontera = """### Próxima frontera — DAY 151+
1. **EMECAS protocolo** — `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
2. **DEBT-FIREWALL-DENY-SELECTIVE-001 P0** — regla default-deny selectiva (loopback + ESTABLISHED + RFC1918)
3. **DEBT-AUTONOMY-ZMQ-EVENTS-001** — ZMQ pub/sub `argus.crypto.autonomy` (inproc/ipc)
4. **BACKLOG-ZMQ-TUNING-001** — HWM + Linger en todos los sockets — `#ifdef ARGUS_VAULT_ENABLED`, `ICryptoProvider`, fichero local bootstrap + registro vía loopback
3. **DEBT-CRYPTO-AUTONOMY-001** — máquina de estados EXTENDED_AUTONOMY en `vault_client.cpp`
4. **DEBT-FIREWALL-AUTONOMY-MODE-001** — firewall default-deny en modo autonomía
5. **DEBT-ALERTING-EDGE-SOS-001** — webhook SOS configurable por despliegue
6. **DEBT-EMECAS-DUAL-COMPILATION-001** — CI compila community + enterprise"""

new_frontera = """### Próxima frontera — DAY 156+
1. **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 P0** — Integrar `CryptoAutonomyStateMachine` + `AutonomyPublisher` en `etcd-server/main.cpp`. Consejo 6/8: etcd-server como propietario para FEDER.
2. **DEBT-AUTONOMY-STATE-PERSISTENCE-001 P1** — Estado firmado Ed25519 en `/run/argus/crypto-autonomy-state.json` en tmpfs.
3. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 P1** — Firma Ed25519 en bootstrap status.
4. **DEBT-CRYPTO-AUTONOMY-001 P2** — Máquina de estados EXTENDED_AUTONOMY completa en `etcd-server`.
5. **DEBT-CRYPTO-RECONCILIATION-001 P1** — Handshake de validación al recuperar Vault.
6. **DEBT-ALERTING-EDGE-SOS-001 P1** — Webhook SOS configurable por despliegue.
7. **BACKLOG-BENCHMARK-CAPACITY-001** — Benchmarks sintéticos VirtualBox (baseline) + hardware físico FEDER."""

if old_frontera in readme:
    readme = readme.replace(old_frontera, new_frontera, 1)
    print("✅ README: sección próxima frontera actualizada")
else:
    print("⚠️  Sección próxima frontera no encontrada exacta — revisar manualmente")

# ── 5. Milestones: añadir DAY 155 ────────────────────────────────────────────

old_milestone_154 = "- ✅ DAY 154: **ADR-045 VaultClient decomposition · DEBT-FIREWALL-AUTONOMY-MODE-001 CERRADA · 48/48 tests · v0.8.0-adr045** 🎉"
new_milestone_155 = (
        old_milestone_154 + "\n"
                            "- ✅ DAY 155: **DEBT-FIREWALL-DENY-SELECTIVE-001 · DEBT-AUTONOMY-ZMQ-EVENTS-001 · BACKLOG-ZMQ-TUNING-001 · 49/49 tests · EMECAS HARDENED PASSED · v0.9.0-day155** 🎉"
)

if old_milestone_154 in readme:
    readme = readme.replace(old_milestone_154, new_milestone_155, 1)
    print("✅ README: milestone DAY 155 añadido")
else:
    print("⚠️  Milestone DAY 154 no encontrado")

# ── 6. Estado actual header ───────────────────────────────────────────────────

readme = readme.replace(
    "## Estado actual — DAY 151 (2026-05-14)",
    "## Estado actual — DAY 155 (2026-05-17)",
)
readme = readme.replace(
    "**Tag activo:** `v0.8.0-adr045` | **Branch activa:** `main`\n**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`\n**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv\n**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo",
    "**Tag activo:** `v0.9.0-day155` | **Branch activa:** `main`\n**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d827d1d6d4c938b720e34331f8a73f478ee85daa`\n**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv\n**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo",
)
print("✅ README: estado actual actualizado")

with open("README.md", "w") as f:
    f.write(readme)

print("\n✅ README.md actualizado")
print("\n=== Actualización DAY 155 completada ===")
print("Revisar manualmente:")
print("  - Tabla deuda técnica en README si hay patrones no encontrados")
print("  - Sección próxima frontera si el patrón exacto difiere")
print("  - Notas del Consejo DAY 155 en BACKLOG si el marker no coincidió")