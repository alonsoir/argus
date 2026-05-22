# CONSEJO DE SABIOS — DAY 160
*Fecha: 2026-05-22 · Branch: feature/day160-enterprise-vault-crypto · Tag: v0.9.4-day160*

---

## Lo que se hizo hoy

### DEBT-ENTERPRISE-PLUGIN-001 — CERRADA

El modelo open-core de aRGus NDR tiene su primer artefacto real.

**Stack construido desde cero:**
- `ICryptoProvider.hpp` (ADR-044) — interfaz pura C++20
- `VaultProvider` — obtiene seed de HashiCorp Vault KV v2 via libcurl, deriva 32 bytes via SHA-256 (libsodium), expone C ABI `argus_enterprise_create/destroy` con `visibility=default`
- `libvault_provider.so` — compila con `-Werror -fvisibility=hidden` limpio
- **6 tests RED→GREEN:**
    - T1: config vacía → constructor lanza
    - T2: token Vault inválido → HTTP 403 → lanza
    - T3: secreto inexistente → HTTP 404 → lanza
    - T4: Vault inalcanzable → curl error → lanza
    - T5: seed válido → exactamente 32 bytes, no todo ceros
    - T6: C ABI via dlopen → create/get_seed/is_healthy/destroy

**Infraestructura dev levantada:**
- Vault v2.0.1 dev mode operacional, `secret/argus/crypto` visible en UI
- Jenkins 2.555.2 operacional con Java 21 Temurin (via SDKMAN)
- Port forwarding: 8080 Jenkins + 8200 Vault
- Todos los fixes codificados en el Vagrantfile para reproducibilidad

**Bugs resueltos en provision (para historia futura):**
- Jenkins key `jenkins.io-2023.key` rotada → fix: keyserver.ubuntu.com `7198F4B714ABFC68`
- Jenkins 2.555+ requiere Java 21 mínimo (Java 17 falla silenciosamente)
- Java 21 no está en repos Bookworm → SDKMAN + Temurin 21.0.7
- Vault dev mode es inmem → autostart en provision con recreación de secreto
- `-fvisibility=hidden` en `.so` oculta símbolos C ABI → fix: `visibility("default")`

**Makefile:** `make test-enterprise-plugin`, `make vault-dev-start`, `make vault-dev-stop`

---

## Lo que haremos mañana — DAY 161

**Objetivo principal: Pipeline CI/CD dev→prod con imagen Debian**
Jenkins pipeline (DAY 161):

git checkout feature/day161-cicd-pipeline
make bootstrap (EMECAS)
make test-all
make test-enterprise-plugin (Vault activo)
Generar imagen Debian con todos los componentes:

Sustituir variables en JSON contrato con valores naive (dev)
Cifrado/seed sale de Vault via plugin enterprise autorizado por token
Producir .deb o imagen Vagrant-test deployable


Deploy a VM Vagrant-test (sustituto del hardware físico UEx pendiente)


**La pregunta de arquitectura central para mañana:**
¿Cómo se calculan los valores óptimos de los JSON contrato en función del hardware destino?
Por ahora: valores naive de dev. Post-FEDER: BACKLOG-ZMQ-TUNING-001 + BACKLOG-BENCHMARK-CAPACITY-001.

---

## Preguntas para el Consejo — DAY 161

**Q1 — Imagen de producción: ¿.deb o Vagrant box?**
Para el demo FEDER necesitamos algo deployable en hardware físico (RPi5, N100).
¿Producimos un `.deb` instalable, una Vagrant box exportable, o ambos?
Tradeoffs: `.deb` es más limpio para producción; Vagrant box es más rápido de validar.

**Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?**
Los JSON contrato tienen variables (HWM, IO threads, batch size, timeouts).
Para DAY 161 proponemos valores hardcoded de dev.
¿O debería haber un script que detecte CPUs/RAM y calcule valores mínimos seguros?

**Q3 — Token enterprise en CI/CD: ¿cómo se gestiona?**
El plugin vault_crypto necesita `enterprise.token` válido para cargar.
En Jenkins: ¿secreto en Credentials store de Jenkins, o fichero en la VM?
Implicaciones de seguridad en ambos casos.

**Q4 — DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001**
Quedaron abiertas de DAY 159 como P1.
¿Se hacen antes del pipeline CI/CD (DAY 161) o después?
El pipeline sin wire protocol test es una casa sin cimientos.

**Q5 — Vault dev mode en CI/CD: ¿aceptable para el gate FEDER?**
Vault dev mode es inmem y no persiste. Para la demo FEDER necesitaremos Vault
en modo producción con unseal keys. ¿Cuándo abordamos DEBT-JENKINS-PROD-001?
¿Es bloqueante para BACKLOG-FEDER-001?

---

## Estado de deudas activas post-DAY 160

| DEBT | Prioridad | Estado |
|------|-----------|--------|
| DEBT-ENTERPRISE-PLUGIN-001 | P0 | ✅ CERRADA DAY 160 |
| DEBT-WIRE-PROTOCOL-TEST-001 | P1 | Abierta DAY 159 |
| DEBT-E2E-LIVE-DELTA-001 | P1 | Abierta DAY 159 |
| DEBT-JENKINS-PROD-001 | P0 | post-hardware UEx |
| DEBT-CRYPTO-AUTONOMY-001 | P1 | EXTENDED_AUTONOMY state machine |
| DEBT-ALERTING-VAULT-001 | P2 | Migrar credenciales a Vault |
| BACKLOG-FEDER-001 | deadline 2026-09-22 | Gate: pipeline CI/CD + hardware |

---

## Métricas DAY 160

- Sesión: ~4h (03:32 → 05:00 aproximado)
- Bugs de provision resueltos: 5
- Tests nuevos: 6 (todos verdes)
- Ficheros creados: 6 (ICryptoProvider.hpp, vault_provider.hpp/cpp, CMakeLists x2, test)
- Líneas añadidas al Vagrantfile: ~70 (fixes documentados)
- Commits: 2 · Tag: v0.9.4-day160