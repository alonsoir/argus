# PROMPT_CONTINUE_CLAUDE — aRGus NDR DAY 160
*Generado: 2026-05-21 · main @ v0.9.3-day158*

---

## Contexto del proyecto

aRGus NDR es un sistema C++20 open-source de Network Detection & Response para infraestructura crítica (hospitales, escuelas, municipios). PI y único desarrollador: Alonso (Badajoz, Extremadura). Co-investigador institucional: Dr. Andrés Caro Lindo (UEx/INCIBE). Co-fundador: Hugo Vázquez Caramés. Paper: arXiv:2604.04952. Repo: github.com/alonsoir/argus.

Metodología: Test-Driven Hardening (TDH), Consejo de Sabios (8 modelos: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral), EMECAS como invariante de reproducibilidad. "Via Appia Quality". "JSON is the law".

**EMECAS canonical:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
**EMECAS++:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e`
**macOS constraint:** Python3 heredoc (`<< 'PYEOF'`), nunca `sed -i` sin `-e ''`. Vagrant siempre con `-c`.

---

## Estado actual — DAY 160

**Branch activa:** abrir `feature/day160-enterprise-plugin`
**Tag en main:** `v0.9.3-day158`
**Keypair activo:** regenera en cada `vagrant destroy+up`

### Lo que se cerró en DAY 158-159

**DAY 158 — DEBT-ALERTING-EDGE-SOS-001 CERRADA:**
- `common/include/alert_client.hpp` header-only, Discord+Telegram fire-and-forget
- 10/10 tests, E2E validado. Integrado en etcd-server.
- `DEBT-ALERTING-VAULT-001` abierta P2 (migrar credenciales a Vault).

**DAY 159 — DEBT-FIREWALL-CRYPTO-FORMAT-001 CERRADA (crítica):**
- Dos bugs encadenados desde DAY 98 — 61 días de 100% drop rate invisible en el firewall.
- Bug 1: `hex_to_bytes(config_.crypto_token)` (deprecated, siempre vacío) → fix: `rx_->decrypt(data)`.
- Bug 2: header LZ4 leído BE (bit-shifts manuales) pero ml-detector escribe LE (`memcpy uint32_t x86`). `0x000002BD` → `0xBD020000` = 3,171M → crash sanity check → 100% drop.
- Tras fix: `events_processed=5, events_dropped=0, crypto_errors=0` inmediato.

**DAY 159 — Synthetic injectors migrados a ADR-013 PHASE 2:**
- `tools/synthetic_sniffer_injector.cpp`: lee `sniffer.json → network.output_socket`, `SeedClient + CryptoTransport + LZ4 LE`.
- `tools/synthetic_ml_output_injector.cpp`: lee `ml_detector_config.json → network.output_socket`, mismo patrón.
- DAY-49 code (`get_encryption_key() + hex_to_bytes()`) completamente eliminado.

**DAY 159 — make test-e2e implementado:**
- `scripts/check_e2e_pipeline.py` — modos: snapshot, check, check-firewall, check-abs.
- `make test-e2e-synthetic-full`: delta ml-detector=100, firewall=100 ✅
- `make test-e2e-synthetic-firewall`: delta firewall=158 ✅
- `make test-e2e-live`: events_processed=329, events_dropped=0 ✅
- EMECAS++ completo desde VM limpia: TODO VERDE.

### Consejo de Sabios DAY 159 — Decisiones

| Q | Decisión adoptada |
|---|---|
| Q1 — Wire protocol test | DEBT-WIRE-PROTOCOL-TEST-001 P1: `common/tests/` byte-a-byte LZ4 LE |
| Q2 — test-e2e-live delta | DEBT-E2E-LIVE-DELTA-001 P1: snapshot+60s wait+delta≥1 (Gemini) |
| Q3 — ALERTING-LIBCRYPTO | P2, no P0. Documentar limitación single-point-alerting en FEDER prospectus |
| Q4 — ml_output_injector | No auto-adaptar más parámetros. Docstring+TODO en fichero |
| Q5 — paralelización E2E | No interna. Nightly job en Jenkins post-FEDER |

---

## Prioridades DAY 160

### P0 — Primer plugin enterprise firmado (DEBT-ENTERPRISE-PLUGIN-001)

**Objetivo:** `plugins/enterprise/vault_provider/libvault_provider.so` firmado Ed25519, cargable via ADR-025.

**Por qué ahora:** el modelo open-core (DAY 150, Consejo 8/8) existe solo en papel. Sin un plugin enterprise real firmado, no hay modelo de negocio demostrable, no hay demo FEDER enterprise, no hay DEBT-LICENSE-VAULT-001 posible.

**Arquitectura:**
```
argus-binary (ARGUS_VAULT_ENABLED=OFF)
    └── plugin-loader (ADR-025)
            └── dlopen("libvault_provider.so")
                    └── VaultProvider (enterprise feature)
```

**Keypair vendor (DISTINTO del keypair nodo):**
- Generado UNA VEZ por el founder, air-gapped, offline
- Pubkey hardcodeada en el plugin-loader (como ADR-025 con plugins XGBoost)
- Nunca en Vault, nunca en disco del nodo en producción
- En dev: puede estar en `vendor_keypair.pub` (gitignored)

**Pasos:**
1. Crear `plugins/enterprise/vault_provider/CMakeLists.txt`
2. Exponer símbolo `argus_plugin_create()` + `argus_plugin_destroy()` (ADR-025 interface)
3. Mover `VaultProvider` de `enterprise/` a este nuevo plugin
4. Compilar como `.so` separado
5. Generar keypair vendor: `tools/gen_vendor_keypair.sh` (gitignored output)
6. Firmar `.so` con keypair vendor
7. Plugin-loader: verificar firma vendor antes de `dlopen()`
8. Tests: 6 tests RED→GREEN

**Test de cierre:** `make test-all` + `make test-enterprise-plugin` PASSED. Plugin cargado, verificado, funcional, descargado limpiamente. `ARGUS_VAULT_ENABLED=OFF` binario principal + plugin .so → idéntico a `ARGUS_VAULT_ENABLED=ON` monolítico.

### P1 — DEBT-WIRE-PROTOCOL-TEST-001
- `common/tests/test_wire_protocol.cpp`
- Serializa un payload con código de ml-detector (LZ4 LE memcpy)
- Lo deserializa con código del firewall (mismo memcpy)
- Verifica decoded_size == original_size, no errores
- ~30 minutos

### P1 — DEBT-E2E-LIVE-DELTA-001
- `scripts/check_e2e_pipeline.py`: añadir modo `check-delta`
- `make test-e2e-live`: snapshot → 60s → delta ≥ 1
- ~1h

### P1 — DEBT-EMECAS-TEST-TO-MERGE-001
- `make test-wire` (llama a test_wire_protocol)
- `docs/CONTRIBUTING.md`: pirámide 4 niveles documentada
- PR template: checklist actualizado
- ~1 sesión

---

## Deudas abiertas P1 pre-FEDER (orden de prioridad)

| DEBT | Prioridad | Estimación |
|------|-----------|-----------|
| DEBT-ENTERPRISE-PLUGIN-001 | 🔴 P0 | 2 sesiones (DAY 160-161) |
| DEBT-WIRE-PROTOCOL-TEST-001 | 🔴 P1 | 30 min |
| DEBT-E2E-LIVE-DELTA-001 | 🔴 P1 | 1h |
| DEBT-EMECAS-TEST-TO-MERGE-001 | 🔴 P1 | 1 sesión |
| DEBT-JENKINS-PROD-001 | 🔴 P0 | post-hardware |
| DEBT-CRYPTO-AUTONOMY-001 | 🔴 P1 | 2 sesiones |
| DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001 | 🟡 P1 | 1 sesión |
| DEBT-ALERTING-VAULT-001 | 🟡 P2 | 1 sesión |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 | 🟡 P2 | 1h |
| DEBT-AUTONOMY-CLOCK-INJECTION-001 | 🟡 P1 | 30 min |

---

## Reglas permanentes críticas (no cambiar)

- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all` — sin excepciones
- **EMECAS++:** añadir `&& make test-e2e` para gates de release
- **Wire protocol test (DAY 159):** todo contrato binario cross-componente tiene test en `common/tests/`
- **ZMQ PUB/SUB (DAY 156):** publisher hace `bind()` ANTES de que subscriber conecte
- **ODR gate:** `make PROFILE=production all` antes de cualquier merge a main con C++20
- **-Werror:** 0 warnings es invariante permanente
- **JSON is the law:** toda config desde JSON canónico, nunca hardcodeada
- **fork()+execv() en IRP:** firewall-acl-agent nunca muere
- **Ed25519 signing:** todo artefacto firmable (plugins, bootstrap-status, autonomy-state) lleva firma
- **Keypair vendor (DAY 159):** air-gapped, distinto del keypair nodo, pubkey hardcodeada en loader
- **test-e2e secuencial:** no paralelizar internamente (estado compartido)

---

## Arquitectura pipeline

```
sniffer (eBPF/XDP o libpcap)
    PUSH bind:5571
        → ml-detector PULL connect:5571
            PUB bind:5572
                → firewall-acl-agent SUB connect:5572
                → rag-ingester

etcd-server: trust anchor, autonomy publisher (ipc:///run/argus/autonomy.sock)
firewall-acl-agent: autonomy subscriber + reactor

Crypto bus: SeedClient → CryptoTransport (ChaCha20-Poly1305 + HKDF)
Serialización: Protobuf → LZ4 compress (LE header, memcpy uint32_t) → ChaCha20 encrypt
Plugin system: Ed25519 signed .so via ADR-025
```

---

## FEDER deadline

22 Septiembre 2026 (BACKLOG-FEDER-001). Contacto: Dr. Andrés Caro Lindo (andresc@unex.es).

Hardware en camino via UEx: RPi5 × N + switch. Email pendiente para N100 x86.

Gate FEDER: ADR-026 ✅, ADR-029 A+B ✅, Pipeline E2E ✅, DEBT-ENTERPRISE-PLUGIN-001 ⏳, make feder-demo ⏳, hardware físico ⏳.

---

## Para comenzar DAY 160

```bash
git checkout main && git pull origin main --ff-only
git checkout -b feature/day160-enterprise-plugin
# Abrir Consejo con las preguntas de arquitectura del plugin enterprise
# Ver: docs/adr/ADR-025-plugin-integrity-ed25519.md para la interfaz existente
# Keypair vendor: tools/gen_vendor_keypair.sh (crear nuevo)
vagrant destroy -f && vagrant up && make bootstrap && make test-all
```