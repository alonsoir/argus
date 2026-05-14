#!/usr/bin/env python3
# update_day151.py — Actualiza README.md y BACKLOG.md con los cambios de DAY 151
# Ejecutar desde la raíz del proyecto: python3 update_day151.py

import sys

# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────

def update_readme():
    with open("README.md", "r") as f:
        content = f.read()

    if "## Estado actual — DAY 151" in content:
        print("⚠️  README.md: patch DAY 151 ya aplicado — nada que hacer")
        return

    # 1. Estado actual: DAY 149 → DAY 151
    content = content.replace(
        "## Estado actual — DAY 149 (2026-05-12)",
        "## Estado actual — DAY 151 (2026-05-14)"
    )
    content = content.replace(
        "**Tag activo:** `v0.7.2-day149` | **Branch activa:** `main`",
        "**Tag activo:** `v0.8.0-day151` | **Branch activa:** `main`"
    )
    content = content.replace(
        "**Paper:** arXiv:2604.04952 · Draft v24 local (abstract v24: architecturally complementary by design) · v3 en arXiv\n**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026",
        "**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv\n**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo"
    )

    # 2. Hitos DAY 149 bloque → añadir DAY 150-151 después
    OLD_NEXT = "### 🔜 NEXT — DAY 149+ (secuencia confirmada Consejo 8/8)"
    NEW_HITOS = """### ✅ DONE — DAY 151 (14 May 2026) — ICryptoProvider + etcd-server STEP 0 🎉

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

### 🔜 NEXT — DAY 149+ (secuencia confirmada Consejo 8/8)"""

    if OLD_NEXT in content:
        content = content.replace(OLD_NEXT, NEW_HITOS)

    # 3. Milestones — añadir DAY 151
    OLD_MILESTONE = "- ✅ DAY 149: **Schema Parquet Arrow v1.0 · Vault CI/CD pipeline · ADR-044 · Ansible+Jinja2 · 5 PRs · v0.7.2-day149** 🎉"
    NEW_MILESTONE = OLD_MILESTONE + "\n- ✅ DAY 150: **ADR-044 implementación completa · provision_crypto.sh · vault_client C++20 · Jenkinsfile Provision Crypto · EMECAS verde** 🎉\n- ✅ DAY 151: **ICryptoProvider + SeedFileProvider + VaultProvider · etcd-server STEP 0 · ADR-045 aprobado · 55+ tests verdes · v0.8.0-day151** 🎉"
    if OLD_MILESTONE in content:
        content = content.replace(OLD_MILESTONE, NEW_MILESTONE)

    # 4. Decisiones de diseño — añadir DAY 151
    OLD_DECISIONS_END = "| **ADR-035 OQ-2 CERRADA** | Topología etcd parametrizada por tamaño de instalación."
    NEW_DECISIONS = """| **ICryptoProvider + SRP (DAY 151 — Consejo 8/8 + Founder)** | `CryptoTransport`+`SeedClient` (canal ZeroMQ) y `ICryptoProvider` (identidad Ed25519) son responsabilidades separadas. `#ifdef ARGUS_VAULT_ENABLED` confinado en `crypto_provider.cpp`. Ningún componente ve el flag en lógica de negocio. | DAY 151 |
| **VaultClient por composición (DAY 151 — Consejo 8/8 + Founder)** | `VaultClient` se descompone en interfaces inyectables: `IVaultTransport`, `ICacheManager`, `IEtcdRegistrar`, `ICryptoDeriver`, `IJitterStrategy`. Cada responsabilidad testeable en aislamiento. ADR-045. | DAY 151 |
| **CryptoAutonomyStateMachine separada (DAY 151 — Consejo 8/8)** | La máquina de estados vive en `common/crypto_autonomy.h`, owned por `VaultProvider`. VaultClient no contiene lógica de estados. Clock inyectable para tests. Thread-safe: mutex transiciones + atomic lectura. | DAY 151 |
| **OperationalMode en ICryptoProvider (DAY 151 — Consejo 6/8)** | `get_operational_mode()` expuesto en la interfaz con default `NORMAL`. Community y enterprise tienen el mismo contrato. `SeedFileProvider` siempre retorna `NORMAL`. | DAY 151 |
| **Calidad sobre fechas (DAY 151 — Founder)** | No hay deadline duro para FEDER. Los datasets se generan cuando el pipeline esté listo. La calidad del pipeline no se negocia por fechas. Plan MITRE/CTF en backlog, después de infraestructura consolidada y primer plugin enterprise. | DAY 151 |
| **ADR-035 OQ-2 CERRADA** | Topología etcd parametrizada por tamaño de instalación."""
    if OLD_DECISIONS_END in content:
        content = content.replace(OLD_DECISIONS_END, NEW_DECISIONS)

    # 5. Badge update
    content = content.replace(
        "[![Hardened](https://img.shields.io/badge/Security-v0.7.2--day149-brightgreen)]()",
        "[![Hardened](https://img.shields.io/badge/Security-v0.8.0--day151-brightgreen)]()"
    )

    with open("README.md", "w") as f:
        f.write(content)
    print("✅ README.md actualizado para DAY 151")


# ─────────────────────────────────────────────────────────────────────────────
# BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

def update_backlog():
    with open("docs/BACKLOG.md", "r") as f:
        content = f.read()

    if "## ✅ CERRADO DAY 151" in content:
        print("⚠️  BACKLOG.md: patch DAY 151 ya aplicado — nada que hacer")
        return

    # 1. Actualizar fecha de última actualización
    content = content.replace(
        "*Última actualización: DAY 146 — 9 Mayo 2026*",
        "*Última actualización: DAY 151 — 14 Mayo 2026*"
    )

    # 2. Añadir sección CERRADO DAY 151 antes de CERRADO DAY 150
    NEW_DAY151 = """## ✅ CERRADO DAY 151

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

"""

    OLD_DAY150_MARKER = "## ✅ CERRADO DAY 150"
    if OLD_DAY150_MARKER in content:
        content = content.replace(OLD_DAY150_MARKER, NEW_DAY151 + OLD_DAY150_MARKER)

    # 3. Añadir nuevas deudas abiertas
    NEW_DEBTS = """
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

### DEBT-AUTONOMY-ZMQ-EVENTS-001 — Transiciones de autonomía no emiten eventos ZeroMQ
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 151 (Grok, Consejo)
**Componente:** `CryptoAutonomyStateMachine` + ZeroMQ bus

Cada transición de estado (`NORMAL→AUTONOMOUS`, `AUTONOMOUS→RECONCILING`, etc.) debe emitir un evento ZeroMQ interno en el topic `crypto.autonomy.transition`. Permite que firewall, alerting y RAG reaccionen sin polling.

**Test de cierre:** transición de estado → evento ZeroMQ recibido por suscriptor.
**Estimación:** 1h

---

"""

    # Insertar antes de DEBT-ETCD-HA-QUORUM-001
    OLD_DEBT_ANCHOR = "### DEBT-ETCD-HA-QUORUM-001 — etcd-server en HA con quorum"
    if OLD_DEBT_ANCHOR in content:
        content = content.replace(OLD_DEBT_ANCHOR, NEW_DEBTS + OLD_DEBT_ANCHOR)

    # 4. Añadir ADR-045 al backlog
    ADR045_BACKLOG = """
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

"""
    OLD_DEBT_LICENSE = "### DEBT-LICENSE-VAULT-001 — Servidor de licencias en Vault"
    if OLD_DEBT_LICENSE in content:
        content = content.replace(OLD_DEBT_LICENSE, ADR045_BACKLOG + OLD_DEBT_LICENSE)

    # 5. Actualizar tabla de estado global
    content = content.replace(
        "ADR-044 CI/CD Crypto Pipeline:             100% ✅  DAY 149 (definido, Consejo 8/8, impl DAY 150+)",
        "ADR-044 CI/CD Crypto Pipeline:             100% ✅  DAY 149 (definido, Consejo 8/8, impl DAY 150+)\nICryptoProvider + SeedFileProvider + VaultProvider: 100% ✅  DAY 151 (factoría, tests, etcd STEP 0)\nDEBT-BOOTSTRAP-STATUS-SIGNATURE-001:      0% ⏳  P1 pre-FEDER (bootstrap status sin firma)\nDEBT-AUTONOMY-STATE-PERSISTENCE-001:      0% ⏳  P1 (estado autonomía sin persistencia firmada)\nDEBT-AUTONOMY-CLOCK-INJECTION-001:        0% ⏳  P1 (clock no inyectable)\nDEBT-AUTONOMY-ZMQ-EVENTS-001:             0% ⏳  P1 (transiciones sin eventos ZMQ)\nADR-045 VaultClient Decomposition:        0% ⏳  DAY 153+ (IVaultTransport + ICacheManager primero)"
    )

    # 6. Añadir notas del Consejo DAY 151
    OLD_NOTAS_END = "## 📝 Notas del Consejo de Sabios — DAY 150 (8/8)"
    NEW_NOTAS = """## 📝 Notas del Consejo de Sabios — DAY 151 (8/8)

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

""" + OLD_NOTAS_END

    if OLD_NOTAS_END in content:
        content = content.replace(OLD_NOTAS_END, NEW_NOTAS)

    # 7. Actualizar pie del fichero
    content = content.replace(
        "*DAY 150 — 13 Mayo 2026 · main @ 93b4d39c*",
        "*DAY 151 — 14 Mayo 2026 · main @ 9e692a4e*"
    )

    with open("docs/BACKLOG.md", "w") as f:
        f.write(content)
    print("✅ docs/BACKLOG.md actualizado para DAY 151")


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    update_readme()
    update_backlog()
    print("\n✅ Todos los ficheros actualizados para DAY 151")
    print("   Siguiente: python3 update_day151.py → git add README.md docs/BACKLOG.md → commit")