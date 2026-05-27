#!/usr/bin/env python3
"""
update_day165.py — Actualiza docs/BACKLOG.md y README.md con DAY 164-165.

Uso desde la raíz del repo:
    python3 update_day165.py [--root /ruta/al/repo] [--dry-run]
"""

import argparse
import os
import sys

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Escrito: {path}")

# ─── BLOQUES DE CONTENIDO ────────────────────

NOTAS_CONSEJO_DAY165 = """
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
"""

SECCION_DAY165_BACKLOG = """## ✅ CERRADO DAY 165

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

"""

SECCION_DAY164_BACKLOG = """## ✅ CERRADO DAY 164

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

"""

NUEVAS_DEUDAS = """
### BACKLOG-EMECAS-ENTERPRISE-001 — Protocolo EMECAS++ (3 actos)
**Severidad:** 🔴 P0 — bloqueante de merge a main
**Estado:** ABIERTO — DAY 165 (decisión Alonso post-Consejo 8/8)
**Componente:** `Makefile` + `scripts/` + Vault + etcd + pipeline completo

Implementar `make emecas++` con los tres actos obligatorios:

**Acto I — Arranque nominal:** todos los componentes se autentican contra Vault, reciben claves, cifran/descifran, tráfico fluye. Medición: `events_processed`, `crypto_errors==0`, `epoch_id` correcto.

**Acto II — Rotación controlada (5 min o forzada vía etcd):** pipeline sigue corriendo, `CryptoEpochCoordinator` detecta nuevo epoch, `CryptoProviderHandle` hot-reload RCU, wire header actualiza `epoch_id`. Medición: continuo sin gaps, `crypto_errors==0`, `epoch_id` antes/después distintos.

**Acto III — Vault falla en un componente aleatorio:** componente afectado sigue con clave anterior (caché RCU), notifica (log estructurado + señal Jenkins), resto funciona con clave nueva. Al recuperar Vault: componente recibe nueva clave, la aplica. Zero downtime. Datos válidos para paper arXiv.

**Prerequisitos (en orden):**
1. DEBT-VAULT-RECONNECT-001 (estado VaultProvider retry/cache)
2. test-e2e-vault completo (Acto I)
3. Mecanismo notificación → Jenkins (Acto III)
4. Script inyección de fallo controlado (Acto III)

**Test de cierre:** `make emecas++` PASSED — los 3 actos verdes y reproducibles.
**Estimación:** DAY 166-170 (condicionado a B1).

---

### DEBT-VAULT-RECONNECT-001 — VaultProvider retry/cache estado desconocido
**Severidad:** 🔴 P0 — prerequisito del Acto III
**Estado:** ABIERTO — DAY 165
**Componente:** `common/vault_provider.cpp` + `common/vault_transport.cpp`

Estado actual de VaultProvider retry/cache: DESCONOCIDO. Es el prerequisito arquitectónico del Acto III.

**Primera acción obligatoria DAY 166:**
```bash
vagrant ssh -c "grep -A 20 'retry\\|cache\\|reconnect\\|fallback' /vagrant/common/vault_provider.cpp"
vagrant ssh -c "grep -A 20 'retry\\|timeout\\|reconnect' /vagrant/common/vault_transport.cpp"
```

Si existe: el test de reconexión puede pasar sin implementación nueva.
Si no existe: implementar antes del merge.

**Test de cierre:** Vault cae → VaultProvider mantiene última clave en caché RCU → pipeline sigue → Vault vuelve → VaultProvider recibe nueva clave → la aplica.
**Estimación:** 0-1 días (inspección + posible implementación).

---

### DEBT-CRYPTO-NEGATIVE-TEST-001 — Test negativo epoch_id incorrecto
**Severidad:** 🔴 P0 — bloqueante de merge (Consejo 6/8 + Alonso)
**Estado:** ABIERTO — DAY 165
**Componente:** `test-e2e-enterprise` o `common/tests/`

Un `epoch_id` incorrecto indica bug propio o abuso externo. El rechazo correcto es contrato de seguridad.

**Test mínimo (~20 líneas):**
1. Enviar frame con `epoch_id = 0xFFFF` (no existente)
2. Assert: `crypto_errors += 1`, `events_processed` no incrementa
3. Enviar mensaje válido inmediatamente después
4. Assert: pipeline continúa operativo, estado no corrupto

**Test de cierre:** `test_epoch_id_rejection` PASSED.
**Estimación:** 2-4 horas, DAY 166.

---

### BACKLOG-CI-ENTERPRISE-001 — Jenkins gate enterprise
**Severidad:** 🟡 P1 post-merge
**Estado:** ABIERTO — DAY 165 (Consejo unanimidad)
**Componente:** Jenkinsfile.dev + Jenkinsfile.prod

`make emecas++` debe ejecutarse automáticamente en CI post-merge.

**Test de cierre:** pipeline Jenkins ejecuta `make emecas++` verde en cada push a main.
**Estimación:** 1 sesión post-merge.

---

### DEBT-FIREWALL-BUILD-LEGACY-001 — firewall-acl-agent/build ruta antigua
**Severidad:** 🟢 P3
**Estado:** ABIERTO — DAY 165 (no bloquea)
**Componente:** `firewall-acl-agent/build` (CMakeLists o ruta de includes)

La ruta antigua `firewall-acl-agent/build` falla build por `seed_client/seed_client.hpp` no encontrado. La ruta activa es `build-debug`. No bloquea.

**Test de cierre:** `cmake --build firewall-acl-agent/build` sin error.
**Estimación:** 30 min.

"""

NUEVAS_REGLAS = """- **REGLA PERMANENTE (DAY 165 — Consejo 8/8):** `epoch_id` en wire header selecciona clave ANTES de descifrar. Nunca intentar descifrado y luego verificar epoch — es un oracle de padding. La selección de clave es el primer paso al recibir un mensaje enterprise.
- **REGLA PERMANENTE (DAY 165 — Consejo 8/8):** El protocolo EMECAS++ tiene tres actos obligatorios: (I) arranque nominal con Vault, (II) rotación controlada con live epoch bajo tráfico, (III) Vault falla en un componente con zero downtime. Los tres actos deben ser verdes y reproducibles antes de cualquier merge enterprise a main.
- **REGLA PERMANENTE (DAY 165 — Founder):** VaultProvider retry/cache es prerequisito arquitectónico del Acto III. Inspeccionar estado antes de planificar DAY 166.
"""

ESTADO_GLOBAL_NUEVAS = """DEBT-ETCD-REGISTRAR-REAL-001:                  100% ✅  DAY 164 — HttpEtcdRegistrar REST 5/5 tests, WatchState CONNECTED/DEGRADED/STALE
BACKLOG-CRYPTO-EPOCH-001:                       100% ✅  DAY 164 — CryptoEpochCoordinator 5/5 tests, etcd-server integrado
BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001:               100% ✅  DAY 165 — FASE 3: wire header epoch_id, 13/13 tests
BACKLOG-CRYPTO-E2E-ROTATION-001 (FakeEtcd):     60% 🟡  DAY 165 — FakeEtcdServer 5/5 + test-e2e-vault PASSED; live rotation pendiente
BACKLOG-EMECAS-ENTERPRISE-001:                   0% ⏳  P0 — protocolo EMECAS++ 3 actos, bloqueante de merge
DEBT-VAULT-RECONNECT-001:                         0% ⏳  P0 — VaultProvider retry/cache estado desconocido (inspeccionar DAY 166)
DEBT-CRYPTO-NEGATIVE-TEST-001:                    0% ⏳  P0 — test negativo epoch_id incorrecto, bloqueante pre-merge
BACKLOG-CI-ENTERPRISE-001:                        0% ⏳  P1 post-merge (Jenkins gate enterprise)
DEBT-FIREWALL-BUILD-LEGACY-001:                   0% ⏳  P3 — firewall-acl-agent/build ruta antigua (no bloquea)"""

HITOS_DAY164_README = """### Hitos DAY 164 🎉
- **DEBT-ETCD-REGISTRAR-REAL-001 CERRADA (FASE 2a)** — `HttpEtcdRegistrar` REST real: `register_status()`, `start_keepalive()` (hilo heartbeat), `watch_epoch()` (polling 2s), `last_seen_revision`, WatchState CONNECTED/DEGRADED/STALE. 5/5 tests RED→GREEN.
  - **BACKLOG-CRYPTO-EPOCH-001 CERRADA (FASE 2b)** — `CryptoEpochCoordinator`: watch `/v1/epoch`, callback `on_epoch_change` → `handle.reload()`, ACK timestamp monotónico ns. 5/5 tests RED→GREEN. etcd-server: GET/PUT `/v1/epoch` + EpochInfo thread-safe.
  - **Fix ODR httplib** — `CPPHTTPLIB_OPENSSL_SUPPORT` via CMake en todos los targets. `alert_client.hpp` #ifndef guard. vault-enterprise-bootstrap token via @file.
  - **12/12 suite common verde.**

"""

HITOS_DAY165_README = """### Hitos DAY 165 🎉
- **BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 CERRADA (FASE 3)** — Wire header enterprise: `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]`. Selección de clave ANTES de descifrar (seguridad crítica). 13/13 tests RED→GREEN. `ml-detector` serializa, `firewall-acl-agent/zmq_subscriber` deserializa.
  - **EMECAS++ OSS verde** — `test-all` ✅ · `test-e2e-synthetic-full` ✅ · `test-e2e-synthetic-firewall` ✅ (540 eventos, 0 crypto_errors).
  - **FASE 4 parcial** — `test_e2e_rotation` FakeEtcdServer 5/5 PASSED + `test-e2e-vault` PASSED. Live rotation pipeline activo pendiente.
  - **Keypair efímero activo:** `a2abfe43e349e86ddeb4a22496b007919c87bdb0f5dc88c17b57cabf0d61331f`
  - **Consejo de Sabios (8/8)** — 6 preguntas EMECAS++. Unanimidades: targets anidados, EMECAS++ naming, Jenkins post-merge. Decisión Alonso: 3 actos obligatorios (Vault nominal + rotación + fallo componente). No merge hasta los 3 actos verdes.
  - **DEBT-FIREWALL-BUILD-LEGACY-001** descubierta (P3, no bloquea).

"""


def update_backlog(content):
    # 1. Header fecha
    content = content.replace(
        "*Última actualización: DAY 163 — 2026-05-25*",
        "*Última actualización: DAY 165 — 2026-05-26*"
    )

    # 2. Footer fecha
    content = content.replace(
        "*DAY 159 — 2026-05-21 · main @ v0.9.3-day158*",
        "*DAY 165 — 2026-05-26 · main @ feature/day161-enterprise-crypto-integration*"
    )

    # 3. Nuevas reglas permanentes
    target_reglas = "- **REGLA PERMANENTE (DAY 142 — macOS):** zsh intercepta"
    if target_reglas in content and "epoch_id en wire header" not in content:
        content = content.replace(target_reglas, NUEVAS_REGLAS + target_reglas)

    # 4. Insertar secciones DAY 165 y 164 antes de DAY 163
    target_163 = "## ✅ CERRADO DAY 163\n"
    if "## ✅ CERRADO DAY 165" not in content:
        content = content.replace(
            target_163,
            SECCION_DAY165_BACKLOG + SECCION_DAY164_BACKLOG + target_163
        )

    # 5. Actualizar estado DEBT-ETCD-REGISTRAR-REAL-001 en sección 163
    content = content.replace(
        "- **Status:** ⏳ OPEN — P0 DAY 164\n- **Descripción:** `StubEtcdRegistrar`",
        "- **Status:** ✅ CERRADA DAY 164 — ver sección DAY 164\n- **Descripción:** `StubEtcdRegistrar`"
    )

    # 6. Actualizar estado BACKLOG-CRYPTO-EPOCH-001
    content = content.replace(
        "### BACKLOG-CRYPTO-EPOCH-001 — CryptoEpoch en etcd (P1) → ADR-045\n**Estado:** ⏳ OPEN — DAY 164-165",
        "### BACKLOG-CRYPTO-EPOCH-001 — CryptoEpoch en etcd (P1) → ADR-045\n**Estado:** ✅ CERRADA DAY 164 — CryptoEpochCoordinator 5/5 tests"
    )

    # 7. Actualizar BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001
    content = content.replace(
        "### BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 — Ventana dual-key ZMQ (P1)\n**Estado:** ⏳ OPEN — DAY 165-166",
        "### BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001 — Ventana dual-key ZMQ (P1)\n**Estado:** ✅ CERRADA DAY 165 — FASE 3: wire header epoch_id, 13/13 tests"
    )

    # 8. Actualizar BACKLOG-CRYPTO-E2E-ROTATION-001
    content = content.replace(
        "### BACKLOG-CRYPTO-E2E-ROTATION-001 — test-e2e-rotation Vault HA (P1)\n**Estado:** ⏳ OPEN — DAY 166-167",
        "### BACKLOG-CRYPTO-E2E-ROTATION-001 — test-e2e-rotation Vault HA (P1)\n**Estado:** 🟡 60% DAY 165 — FakeEtcdServer 5/5 + test-e2e-vault PASSED. Pendiente: live rotation pipeline activo (Actos II-III EMECAS++)"
    )

    # 9. Añadir nuevas deudas antes de BACKLOG-FEDER-001
    target_feder = "## BACKLOG-FEDER-001\n"
    if "BACKLOG-EMECAS-ENTERPRISE-001" not in content and target_feder in content:
        content = content.replace(target_feder, NUEVAS_DEUDAS + target_feder)

    # 10. Actualizar estado global
    old_last = "Jenkinsfile.dev + Jenkinsfile.prod:      100% ✅  DAY 161 — separación dev/prod, agent any vs argus-server\n```"
    new_last = (
            "Jenkinsfile.dev + Jenkinsfile.prod:      100% ✅  DAY 161 — separación dev/prod, agent any vs argus-server\n"
            + ESTADO_GLOBAL_NUEVAS + "\n```"
    )
    if old_last in content:
        content = content.replace(old_last, new_last)

    # 11. Añadir notas Consejo DAY 165 antes de HIPÓTESIS CENTRAL
    target_hip = "## 🧬 HIPÓTESIS CENTRAL — Inmunidad Global Adaptativa"
    if "DAY 165 — Deliberación sobre el diseño del protocolo EMECAS++" not in content and target_hip in content:
        content = content.replace(target_hip, NOTAS_CONSEJO_DAY165 + "\n" + target_hip)

    return content


def update_readme(content):
    # 1. Línea de estado inicial
    OLD_STATUS_LINE = "✅ `main` is tagged `v0.9.5-day161` (EMECAS++ verde). DAY 162: enterprise crypto PASO 1-5 completados. DAY 161: DEBT-WIRE-PROTOCOL-TEST-001 CERRADA (6/6 tests LZ4 LE uint32_t). Jenkinsfile.dev+prod separados. test-e2e-live modo delta. Consejo 8/8. Branch `feature/day161-cicd-pipeline` pendiente EMECAS++ → merge → v0.9.5-day161."
    NEW_STATUS_LINE = "✅ DAY 165: FASE 3 wire header epoch_id (13/13 tests) + EMECAS++ OSS verde + Consejo 8/8 EMECAS++ protocolo 3 actos definido. Branch `feature/day161-enterprise-crypto-integration`. DAY 164: FASE 2a+2b (HttpEtcdRegistrar + CryptoEpochCoordinator, 10/10 tests)."
    content = content.replace(OLD_STATUS_LINE, NEW_STATUS_LINE)

    # 2. Bloque DAY-STATUS
    OLD_STATUS_BLOCK = """<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 163 |
| Tag | pendiente (feature/day161-enterprise-crypto-integration) |
| Branch | feature/day161-enterprise-crypto-integration |
| EMECAS | ⏳ Pendiente pre-merge (EMECAS justo antes de mergear) |
| Pipeline | 6/6 RUNNING |
| Crypto lifecycle | FASE 0 ✅ + FASE 1 ✅ — FASE 2 en curso (DAY 164) |
| CryptoProviderHandle | ✅ RCU header-only 9/9 tests |
| vendor.key | ✅ Modelo B — solo en Vault dev, nunca en disco |
| ADR-045 v2 | ✅ Consejo 8/8 — decisiones finales |
| DEBT-ETCD-REGISTRAR-REAL-001 | ⏳ P0 DAY 164 — prerequisito FASE 2 |
| Próximo hito | DAY 164: HttpEtcdRegistrar real + CryptoEpochCoordinator |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""

    NEW_STATUS_BLOCK = """<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 165 |
| Tag | pendiente (feature/day161-enterprise-crypto-integration) |
| Branch | feature/day161-enterprise-crypto-integration |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ⏳ Pendiente — protocolo 3 actos (Consejo 8/8 DAY 165) |
| Pipeline | 6/6 RUNNING |
| Crypto lifecycle | FASE 0 ✅ + FASE 1 ✅ + FASE 2a ✅ + FASE 2b ✅ + FASE 3 ✅ |
| Wire header epoch_id | ✅ [uint32_t][uint16_t epoch_id][2B reserved][LZ4] — 13/13 tests |
| vendor.key | ✅ Modelo B — solo en Vault dev, nunca en disco |
| ADR-045 v2 | ✅ Consejo 8/8 — implementado FASES 0-3 |
| Próximo hito | DAY 166: inspeccionar VaultProvider retry/cache + Acto I EMECAS++ |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""

    content = content.replace(OLD_STATUS_BLOCK, NEW_STATUS_BLOCK)

    # 3. Insertar hitos DAY 164 y 165 antes de hitos DAY 156
    target = "### Hitos DAY 156 🎉\n"
    if "### Hitos DAY 165 🎉" not in content and target in content:
        content = content.replace(target, HITOS_DAY164_README + HITOS_DAY165_README + target)

    # 4. Actualizar milestones
    OLD_MILE = "  - 🔜 DAY 146+: **DEBT-IRP-TMPFILES-001 · DEBT-IRP-IPSET-TMP-001 · experiment-comparative · ARM64 scope**"
    NEW_MILE = (
        "  - ✅ DAY 164: **FASE 2a+2b enterprise · HttpEtcdRegistrar + CryptoEpochCoordinator · 10/10 tests** 🎉\n"
        "  - ✅ DAY 165: **FASE 3 wire header epoch_id · 13/13 tests · EMECAS++ OSS verde · Consejo 8/8 protocolo 3 actos** 🎉\n"
        "  - 🔜 DAY 166+: **VaultProvider retry/cache + test-e2e-vault Acto I + EMECAS++ 3 actos**"
    )
    if OLD_MILE in content:
        content = content.replace(OLD_MILE, NEW_MILE)

    return content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Raíz del repo")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    backlog_path = os.path.join(root, "docs", "BACKLOG.md")
    readme_path = os.path.join(root, "README.md")

    for p in [backlog_path, readme_path]:
        if not os.path.exists(p):
            print(f"❌ No encontrado: {p}")
            sys.exit(1)

    print(f"📁 Root: {root}")

    backlog = read(backlog_path)
    readme = read(readme_path)

    new_backlog = update_backlog(backlog)
    new_readme = update_readme(readme)

    checks = [
        ("BACKLOG — fecha DAY 165", "DAY 165 — 2026-05-26" in new_backlog),
        ("BACKLOG — CERRADO DAY 165", "## ✅ CERRADO DAY 165" in new_backlog),
        ("BACKLOG — CERRADO DAY 164", "## ✅ CERRADO DAY 164" in new_backlog),
        ("BACKLOG — EMECAS-ENTERPRISE-001", "BACKLOG-EMECAS-ENTERPRISE-001" in new_backlog),
        ("BACKLOG — VAULT-RECONNECT-001", "DEBT-VAULT-RECONNECT-001" in new_backlog),
        ("BACKLOG — CRYPTO-NEGATIVE-TEST-001", "DEBT-CRYPTO-NEGATIVE-TEST-001" in new_backlog),
        ("BACKLOG — Notas Consejo DAY 165", "DAY 165 — Deliberación sobre el diseño del protocolo EMECAS++" in new_backlog),
        ("BACKLOG — FASE 3 cerrada en estado global", "BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001:               100%" in new_backlog),
        ("README — DAY-STATUS 165", "| DAY | 165 |" in new_readme),
        ("README — Hitos DAY 165", "### Hitos DAY 165 🎉" in new_readme),
        ("README — Hitos DAY 164", "### Hitos DAY 164 🎉" in new_readme),
        ("README — milestone DAY 165", "FASE 3 wire header epoch_id" in new_readme),
    ]

    all_ok = True
    for desc, ok in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {desc}")
        if not ok:
            all_ok = False

    print()

    if not all_ok:
        print("❌ Verificaciones fallaron. Revisar el script.")
        sys.exit(1)

    if args.dry_run:
        print("🔍 Dry-run: no se escriben ficheros.")
        return

    write(backlog_path, new_backlog)
    write(readme_path, new_readme)

    print()
    print("Próximos pasos:")
    print("  git add docs/BACKLOG.md README.md")
    print("  git commit -m 'docs: DAY 165 — FASE 3 wire header epoch_id, EMECAS++ protocolo 3 actos, Consejo 8/8'")
    print("  git push origin feature/day161-enterprise-crypto-integration")


if __name__ == "__main__":
    main()