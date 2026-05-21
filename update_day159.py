#!/usr/bin/env python3
"""
update_day159.py — aRGus NDR DAY 158-159 BACKLOG + README updater
Aplica en local: python3 update_day159.py --repo /path/to/argus
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import date

# ── Constantes ───────────────────────────────────────────────────────────────
TODAY = date.today().isoformat()
DAY   = "159"
TAG   = "v0.9.3-day158"

# ── Bloques a insertar ────────────────────────────────────────────────────────

CLOSED_DAY158_159 = """
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

"""

NEW_DEBTS_DAY159 = """
### DEBT-WIRE-PROTOCOL-TEST-001 — Test unitario wire protocol LZ4 LE/BE
**Severidad:** 🔴 P1 — siguiente merge
**Estado:** ABIERTO — DAY 159 (Consejo 8/8 unánime)
**Componente:** `common/tests/test_wire_protocol.cpp`

El bug de endianness estuvo invisible 61 días porque los tests unitarios no cubren el wire protocol entre componentes. `test-e2e` detecta "fluye o no fluye", no "fluye con el formato correcto".

**Invariante a verificar:** header LZ4 de 4 bytes siempre en little-endian (x86 native `memcpy`). Un header BE (`0xBD020000`) debe ser rechazado o causar fallo explícito.

**Test:**
```cpp
TEST(WireProtocol, LZ4Header_LittleEndian_Canonical) {
    // 1. Serializar payload con mismo código de ml-detector (memcpy LE)
    // 2. Deserializar con mismo código de firewall (memcpy LE)
    // 3. Verificar: decoded_size == original_size, no crypto_errors
    // Tiempo: <2s, sin pipeline completo
}
```

**Ubicación:** `common/tests/` (contrato cross-componente, no interno a uno solo).
**Test de cierre:** test PASSED en `make test-all`. Regresión de endianness detectada en <2s sin EMECAS.
**Estimación:** 30 minutos.

---

### DEBT-E2E-LIVE-DELTA-001 — test-e2e-live usa modo absoluto (falso positivo potencial)
**Severidad:** 🟡 P1 — siguiente merge
**Estado:** ABIERTO — DAY 159 (Gemini/Kimi/Mistral convergentes)
**Componente:** `scripts/check_e2e_pipeline.py` modo `check-abs`

`check-abs` pasa aunque el pipeline lleve horas idle con contadores históricos altos. Un pipeline muerto desde hace 3 horas puede pasar `test-e2e-live` si los contadores absolutos son suficientemente grandes.

**Fix (propuesta Gemini — consenso):** snapshot justo antes del wait de 60s → delta ≥ 1.
```python
# check_e2e_pipeline.py --mode=check-delta --window=60
snapshot_before = read_metrics()
sleep(60)
snapshot_after  = read_metrics()
assert snapshot_after.events_processed - snapshot_before.events_processed >= 1
assert snapshot_after.events_dropped   - snapshot_before.events_dropped   == 0
```

**Test de cierre:** `test-e2e-live` falla si pipeline idle >60s. Pasa si pipeline activo.
**Estimación:** 1h.

---

### DEBT-ALERTING-VAULT-001 — Credenciales Discord/Telegram en Vault
**Severidad:** 🟡 P2
**Estado:** ABIERTO — DAY 158
**Componente:** `alert_client.hpp` + Ansible group_vars + Vault
**Descripción:** Credenciales webhook actualmente en `ansible/group_vars/prod.yml` en texto (cifrado con Ansible Vault). Migrar a HashiCorp Vault para coherencia con el modelo de secretos del proyecto. En producción hospitalaria, los webhooks de alerta son material sensible.
**Test de cierre:** `make bootstrap` + alert_client lee credenciales desde Vault. `ansible/group_vars/prod.yml` sin webhooks en claro.
**Estimación:** 1 sesión.

---

### DEBT-ENTERPRISE-PLUGIN-001 — Primer plugin enterprise firmado: VaultProvider
**Severidad:** 🔴 P0 — bloquea modelo open-core
**Estado:** ABIERTO — DAY 159 (Founder, derivada del análisis post-Consejo)
**Componente:** `plugins/enterprise/vault_provider/` + `libvault_provider.so`

El modelo open-core está definido (DAY 150, Consejo 8/8) pero sin ningún plugin enterprise real firmado con Ed25519. `VaultProvider` existe como código compilado pero no como plugin `.so` cargable dinámicamente via ADR-025.

**Trabajo:**
1. Mover `VaultProvider` de `enterprise/` a `plugins/enterprise/vault_provider/`
2. Exponer símbolo `argus_plugin_create()` y `argus_plugin_destroy()` (ADR-025 interface)
3. Compilar como `.so` separado del binario principal
4. Firmar con `Ed25519` via keypair del vendor (distinto al keypair del nodo)
5. Plugin-loader verifica firma antes de `dlopen()`
6. Test: pipeline con `ARGUS_VAULT_ENABLED=OFF` + `vault_provider.so` cargado → funciona idéntico

**Por qué ahora:** sin un plugin enterprise real, el modelo open-core es una promesa en papel. Cerrar esto desbloquea: DEBT-LICENSE-VAULT-001, el modelo de negocio, y la demo FEDER enterprise.

**Keypair vendor (offline, air-gapped):** distinto del keypair del nodo. Generado UNA VEZ por el founder. Pubkey hardcodeada en el plugin-loader (como ADR-025).

**Test de cierre:** `make test-all` + `make test-enterprise-plugin` PASSED. `vault_provider.so` firmado, cargado, verificado, descargado limpiamente.
**Estimación:** 2 sesiones (DAY 160-161).

---

### DEBT-JENKINS-PROD-001 — Jenkins CI/CD en hardware físico real
**Severidad:** 🔴 P0 — FEDER demo requirement
**Estado:** ABIERTO — DAY 159 (Founder)
**Componente:** Jenkinsfile + hardware FEDER

Jenkins existe en Vagrantfile dev pero nunca ha construido en hardware físico real. Para FEDER, necesitamos demostrar que el pipeline CI/CD funciona en la misma categoría de hardware que protegerá hospitales.

**Arquitectura objetivo:**
- Servidor central (MacBook como servidor o N100): Jenkins master + Vault + Neo4j + Wazuh
- Edge nodes (RPi5 + N100): agentes Jenkins que ejecutan `make bootstrap && make test-all && make test-e2e`
- Builds en ARM64 (RPi5) nativos — no cross-compilation

**Prerequisitos:**
1. BACKLOG-HARDWARE-FEDER-001: RPi5 + N100 disponibles (coordinando con Andrés)
2. `DEBT-EMECAS-DUAL-COMPILATION-001`: CI compila `ARGUS_VAULT_ENABLED=ON+OFF`
3. Jenkinsfile: stages `Test Community` + `Test Enterprise` paralelos
4. `make test-e2e` en gate de merge (CI/CD)

**Test de cierre:** PR merged via Jenkins running en N100 hardware físico. Build ARM64 nativo en RPi5. `make test-e2e` verde en CI sin intervención manual.
**Estimación:** 3 sesiones post-hardware.

---

### DEBT-EMECAS-TEST-TO-MERGE-001 — Reforzar gate test-to-merge
**Severidad:** 🔴 P1 — derivado Consejo DAY 159
**Estado:** ABIERTO — DAY 159
**Componente:** Makefile + Jenkinsfile + docs/CONTRIBUTING.md

El bug DAY 159 (61 días invisible) demostró que los gates de merge actuales son insuficientes. El Consejo convergió en una pirámide de 4 niveles que debe estar activa antes del siguiente merge a main con código C++20.

**Pirámide de testing obligatoria (Consejo DAY 159):**
```
UNIT TESTS          → make test-all       (paralelo por componente, <5 min)
WIRE CONTRACT       → make test-wire      (DEBT-WIRE-PROTOCOL-TEST-001, <1 min)
INTEGRATION         → make test-integ     (inyectores sintéticos, <10 min)
E2E                 → make test-e2e       (pipeline completo, ~90 min, nightly)
```

**Gate de merge (PR → main):**
- `make test-all` + `make test-wire` + `make test-integ` OBLIGATORIO en cada PR
- `make test-e2e` OBLIGATORIO en nightly job (no bloquea PR individual, sí bloquea release)
- `make PROFILE=production all` OBLIGATORIO (gate ODR, ya activo)

**Nuevas reglas permanentes a añadir al BACKLOG:**
- `REGLA DAY 159 (Consejo 8/8):` El wire protocol entre componentes tiene test de contrato binario en `common/tests/`. Un bug de endianness en el header de serialización no puede permanecer invisible más de un ciclo de CI.
- `REGLA DAY 159 (Consejo 8/8):` `make test-e2e` es gate de release (nightly), no gate de PR. Los tests E2E son secuenciales siempre — estado compartido en el pipeline hace la paralelización interna peligrosa.

**Test de cierre:** `docs/CONTRIBUTING.md` actualizado. `Makefile` con targets `test-wire` + `test-integ`. PR template checklist actualizado.
**Estimación:** 1 sesión.

"""

CONSEJO_DAY159_NOTES = """
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

"""

REGLAS_DAY159 = """- **REGLA PERMANENTE (DAY 159 — Consejo 8/8):** El wire protocol entre componentes tiene test de contrato binario en `common/tests/`. Serialización LE/BE del header LZ4 se verifica byte-a-byte. Un bug de endianness no puede permanecer invisible más de un ciclo CI. Ver DEBT-WIRE-PROTOCOL-TEST-001.
- **REGLA PERMANENTE (DAY 159 — Consejo 8/8):** `make test-e2e` es gate de release (nightly), no gate de PR. Los subtests E2E son siempre secuenciales — estado compartido en el pipeline hace la paralelización interna peligrosa.
- **REGLA PERMANENTE (DAY 159 — Founder):** El primer plugin enterprise (`vault_provider.so`) se firma con keypair vendor offline (air-gapped), distinto del keypair del nodo. La pubkey vendor está hardcodeada en el plugin-loader — nunca en Vault.
"""

STATE_TABLE_ADDITIONS = [
    "DEBT-ALERTING-EDGE-SOS-001:             100% ✅  DAY 158 — alert_client.hpp 10/10 tests, Discord+Telegram",
    "DEBT-FIREWALL-CRYPTO-FORMAT-001:        100% ✅  DAY 159 — dos bugs encadenados DAY 98, 100% drop rate resuelto",
    "Synthetic injectors ADR-013 PHASE 2:    100% ✅  DAY 159 — SeedClient+CryptoTransport+LZ4-LE, DAY-49 code eliminado",
    "make test-e2e (gate E2E real):          100% ✅  DAY 159 — synthetic-full + synthetic-firewall + live, EMECAS++ verde",
    "DEBT-WIRE-PROTOCOL-TEST-001:              0% ⏳  P1 siguiente merge (test contrato binario LZ4 LE)",
    "DEBT-E2E-LIVE-DELTA-001:                  0% ⏳  P1 siguiente merge (snapshot+delta en test-e2e-live)",
    "DEBT-ALERTING-VAULT-001:                  0% ⏳  P2 (credenciales Discord/Telegram a Vault)",
    "DEBT-ENTERPRISE-PLUGIN-001:               0% ⏳  P0 DAY 160-161 (primer plugin enterprise vault_provider.so)",
    "DEBT-JENKINS-PROD-001:                    0% ⏳  P0 post-hardware (Jenkins CI/CD en hardware físico)",
    "DEBT-EMECAS-TEST-TO-MERGE-001:            0% ⏳  P1 (pirámide 4 niveles: unit+wire+integ+E2E)",
]

# ── Funciones ─────────────────────────────────────────────────────────────────

def update_backlog(path: Path):
    content = path.read_text(encoding="utf-8")

    # 1. Actualizar fecha de última actualización
    content = re.sub(
        r'\*Última actualización: DAY \d+ — \d+ Mayo \d+\*',
        f'*Última actualización: DAY {DAY} — {TODAY}*',
        content
    )

    # 2. Insertar sección DAY 158-159 justo antes de "## ✅ CERRADO DAY 157"
    marker = "## ✅ CERRADO DAY 157"
    if marker in content and "CERRADO DAY 158" not in content:
        content = content.replace(marker, CLOSED_DAY158_159 + marker)
        print("✅ Secciones DAY 158-159 añadidas")
    else:
        print("⚠️  Sección DAY 158-159 ya existe o marker no encontrado")

    # 3. Insertar reglas permanentes DAY 159
    regla_marker = "- **REGLA PERMANENTE (DAY 156 — Consejo 8/8):** En ZMQ PUB/SUB"
    if regla_marker in content and "REGLA PERMANENTE (DAY 159" not in content:
        content = content.replace(regla_marker, REGLAS_DAY159 + regla_marker)
        print("✅ Reglas permanentes DAY 159 añadidas")

    # 4. Insertar nuevas deudas antes de DEBT-ALERTING-LIBCRYPTO-PROVIDER-001
    debt_marker = "### DEBT-ALERTING-LIBCRYPTO-PROVIDER-001"
    if debt_marker in content and "DEBT-WIRE-PROTOCOL-TEST-001" not in content:
        content = content.replace(debt_marker, NEW_DEBTS_DAY159 + debt_marker)
        print("✅ Nuevas deudas DAY 159 añadidas")

    # 5. Insertar notas Consejo DAY 159 antes de las notas DAY 157
    consejo_marker = "## 📝 Notas del Consejo de Sabios — DAY 157"
    if consejo_marker in content and "DAY 159 (8/8)" not in content:
        content = content.replace(consejo_marker, CONSEJO_DAY159_NOTES + consejo_marker)
        print("✅ Notas Consejo DAY 159 añadidas")

    # 6. Actualizar tabla de estado global
    state_marker = "ADR-031 aRGus-seL4:                      0% ⏳  branch independiente"
    if state_marker in content:
        additions = "\n".join(STATE_TABLE_ADDITIONS)
        # Insertar ANTES del cierre del bloque de estado
        old_close = "```\n\n---\n\n## 📝 Notas del Consejo de Sabios — ADR-0043"
        new_close = f"{additions}\n```\n\n---\n\n## 📝 Notas del Consejo de Sabios — ADR-0043"
        if old_close in content and "DEBT-WIRE-PROTOCOL-TEST-001:" not in content:
            content = content.replace(old_close, new_close)
            print("✅ Tabla de estado global actualizada")

    # 7. Actualizar footer
    content = re.sub(
        r'\*DAY \d+ — \d+ Mayo \d+ · main @ v[\d\w\.-]+\*',
        f'*DAY {DAY} — {TODAY} · main @ {TAG}*',
        content
    )

    path.write_text(content, encoding="utf-8")
    print(f"\n✅ BACKLOG.md actualizado → DAY {DAY} / {TAG}")


def update_readme(path: Path):
    content = path.read_text(encoding="utf-8")

    # Actualizar bloque DAY-STATUS
    new_status = f"""<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | {DAY} |
| Tag | {TAG} |
| Branch | main |
| EMECAS | ✅ Verde ({TODAY}) — incluye gate E2E |
| Pipeline | 6/6 RUNNING |
| EMECAS++ | ✅ test-e2e verde (synthetic-full + firewall + live) |
| Próximo hito | DEBT-ENTERPRISE-PLUGIN-001 (vault_provider.so ADR-025) |
| Deadline FEDER | 22-09-2026 |
<!-- /DAY-STATUS -->"""

    content = re.sub(
        r'<!-- DAY-STATUS -->.*?<!-- /DAY-STATUS -->',
        new_status,
        content,
        flags=re.DOTALL
    )

    # Actualizar tag en header
    content = re.sub(
        r'✅ `main` is tagged `v[\d\w\.-]+`\. DAY \d+:.*?\n',
        f'✅ `main` is tagged `{TAG}`. DAY {DAY}: DEBT-FIREWALL-CRYPTO-FORMAT-001 CERRADA (100% drop rate invisible desde DAY 98, dos bugs encadenados). DEBT-ALERTING-EDGE-SOS-001 CERRADA. Gate E2E real implementado. EMECAS++ completo verde. Consejo 8/8.\n',
        content
    )

    # Actualizar badge hardened
    content = re.sub(
        r'v[\d\w\.-]+-hardened',
        f'{TAG}',
        content
    )
    content = content.replace(
        '[![Hardened](https://img.shields.io/badge/Security-v0.9.2--day157-brightgreen)]',
        f'[![Hardened](https://img.shields.io/badge/Security-{TAG.replace("-", "--")}-brightgreen)]'
    )

    # Actualizar estado actual header
    content = re.sub(
        r'## Estado actual — DAY \d+ \(\d{4}-\d{2}-\d{2}\)',
        f'## Estado actual — DAY {DAY} ({TODAY})',
        content
    )

    # Actualizar tag activo
    content = re.sub(
        r'\*\*Tag activo:\*\* `v[\d\w\.-]+`',
        f'**Tag activo:** `{TAG}`',
        content
    )

    # Añadir hito DAY 159 en la sección de milestones
    milestone_marker = '- ✅ DAY 157: **4 deudas cerradas'
    new_milestone = f"""- ✅ DAY {DAY}: **DEBT-FIREWALL-CRYPTO-FORMAT-001 CERRADA — bugs encadenados desde DAY 98, 100% drop rate invisible resuelto. DEBT-ALERTING-EDGE-SOS-001 CERRADA. Gate E2E real. EMECAS++ verde. {TAG}** 🎉
{milestone_marker}"""
    if milestone_marker in content and f"DAY {DAY}:" not in content:
        content = content.replace(milestone_marker, new_milestone)

    # Actualizar sección Próxima frontera
    frontier_old = "6. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 P2**"
    frontier_new = f"""6. **DEBT-ENTERPRISE-PLUGIN-001 P0** — Primer plugin enterprise `vault_provider.so`. Firmado Ed25519 (keypair vendor offline). Cargable via ADR-025. Cierra modelo open-core en código, no solo en papel. DAY 160-161.
7. **DEBT-JENKINS-PROD-001 P0** — Jenkins CI/CD en hardware físico (N100 + RPi5). Requiere BACKLOG-HARDWARE-FEDER-001.
8. **DEBT-WIRE-PROTOCOL-TEST-001 P1** — Test contrato binario LZ4 LE/BE en `common/tests/`. 30 min, previene regresión de endianness.
9. **DEBT-E2E-LIVE-DELTA-001 P1** — Cambiar `test-e2e-live` a snapshot+delta (propuesta Gemini DAY 159).
10. **DEBT-EMECAS-TEST-TO-MERGE-001 P1** — Pirámide 4 niveles: unit+wire+integ+E2E (gate nightly).
11. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 P2**"""
    if frontier_old in content and "DEBT-ENTERPRISE-PLUGIN-001" not in content:
        content = content.replace(frontier_old, frontier_new)

    path.write_text(content, encoding="utf-8")
    print(f"✅ README.md actualizado → DAY {DAY} / {TAG}")


def main():
    parser = argparse.ArgumentParser(description="aRGus NDR DAY 159 updater")
    parser.add_argument("--repo", default=".", help="Ruta al repo argus")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar cambios sin escribir")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    backlog = repo / "docs" / "BACKLOG.md"
    readme  = repo / "README.md"

    for f in [backlog, readme]:
        if not f.exists():
            # Intentar en raíz del repo directamente
            alt = repo / f.name
            if alt.exists():
                f = alt
            else:
                print(f"⚠️  No encontrado: {f}")
                continue

    print(f"\n{'='*60}")
    print(f"aRGus NDR — DAY {DAY} updater")
    print(f"Repo: {repo}")
    print(f"Tag:  {TAG}")
    print(f"{'='*60}\n")

    if not args.dry_run:
        if backlog.exists():
            update_backlog(backlog)
        elif (repo / "BACKLOG.md").exists():
            update_backlog(repo / "BACKLOG.md")
        else:
            print("⚠️  BACKLOG.md no encontrado en docs/ ni en raíz")

        if readme.exists():
            update_readme(readme)
        else:
            print("⚠️  README.md no encontrado")
    else:
        print("DRY RUN — no se escribe nada")
        print("\nBloques que se insertarían:")
        print("1. Sección CERRADO DAY 158-159")
        print("2. Reglas permanentes DAY 159 (3 reglas)")
        print("3. Nuevas deudas: WIRE-PROTOCOL-TEST, E2E-LIVE-DELTA, ALERTING-VAULT, ENTERPRISE-PLUGIN, JENKINS-PROD, EMECAS-TEST-TO-MERGE")
        print("4. Notas Consejo de Sabios DAY 159")
        print("5. Tabla estado global (+10 entradas)")
        print("6. README: DAY-STATUS, badges, milestones, próxima frontera")

    print("\n✅ Listo. Siguiente paso:")
    print("  git add docs/BACKLOG.md README.md")
    print(f"  git commit -m 'docs: DAY {DAY} — BACKLOG + README actualizados'")
    print(f"  git push origin main")


if __name__ == "__main__":
    main()