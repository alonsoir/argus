# CONSEJO DE SABIOS — DAY 161
*Fecha: 2026-05-23 · Branch: feature/day161-cicd-pipeline · Base: v0.9.4-day160*

---

## Lo que se hizo hoy

### Contexto de entrada
- DAY 160 estaba sin cerrar: `feature/day160-enterprise-vault-crypto` no mergeada a main
- VM en estado `aborted` — EMECAS++ nunca se había ejecutado en DAY 160
- Vault dev mode no persistió entre sesiones

### Secuencia real de DAY 161

**1. Cierre de DAY 160 (trabajo previo)**
- EMECAS++ ejecutado desde VM limpia — TODO VERDE (salvo DEBT-E2E-LIVE-DELTA-001 pre-existente)
- `make vault-dev-start` + `make test-enterprise-plugin` — 6/6 PASSED
- PR mergeado a main → `v0.9.4-day160` en main
- Rama `feature/day160-enterprise-vault-crypto` eliminada

**2. DEBT-WIRE-PROTOCOL-TEST-001 — CERRADA (P0)**
- `common/tests/test_wire_protocol.cpp`: 6 tests, protocolo LZ4 LE uint32_t
- Integrado en `common/CMakeLists.txt`
- Target `make test-wire-protocol` en Makefile
- El bug DAY 98 (DEBT-FIREWALL-CRYPTO-FORMAT-001) no puede repetirse sin que este test lo detecte

**3. Jenkinsfile.dev + Jenkinsfile.prod (P1)**
- `Jenkinsfile` renombrado a `Jenkinsfile.prod` (agent: argus-server, servidor FEDER)
- `Jenkinsfile.dev` nuevo: pipeline Vagrant con stages Wire Protocol, Unit Tests, Enterprise Plugin
- Separación clara dev/prod con credencial `vault-enterprise-token`

**4. DEBT-CONFIG-JINJA2-PIPELINE-001 — documentada (P2)**
- Sistema Jinja2 para generar configs por perfil hardware
- JSONs originales son SAGRADOS — nunca se modifican
- `json-templates/` + `json-values/` + `json-generated/` — diseño acordado
- Requiere varios días + hardware físico UEx — diferida correctamente

**5. DEBT-PACKAGE-DEB-001 — documentada (P3)**
- Artefacto .deb primario de release
- Prerequisito: hardware físico + Jenkins real + Jinja2 pipeline
- Diferida correctamente

**6. DEBT-E2E-LIVE-DELTA-001 — CERRADA**
- `test-e2e-live` usaba modo `check-abs` (valor absoluto desde cero)
- Fix: modo `snapshot → 60s → check` (delta ≥1 evento nuevo)
- El fallo en EMECAS++ de DAY 160 no se repetirá

---

## Estado de la rama
feature/day161-cicd-pipeline (4 commits):
79bcea48 feat(day161): DEBT-WIRE-PROTOCOL-TEST-001
e912ec4c feat(day161): Jenkinsfile.dev + Jenkinsfile.prod
21096b23 docs(day161): DEBT-CONFIG-JINJA2-PIPELINE-001
f0ef51df docs(day161): DEBT-PACKAGE-DEB-001
3c5a6d24 fix(day161): DEBT-E2E-LIVE-DELTA-001
Pendiente: EMECAS++ en esta rama para verificar fix delta E2E → merge a main → v0.9.5-day161

---

## Preguntas para el Consejo

**Q1 — Wire Protocol Test**
El test actual verifica el protocolo LZ4 LE uint32_t sin cifrado (solo la capa de compresión).
¿Debería haber un segundo test que pase por CryptoTransport completo (cifrado + compresión)?
¿O es suficiente con los tests existentes de `crypto-transport` + este test de protocolo binario?

**Q2 — Jenkinsfile.dev vs Jenkinsfile.prod**
El `Jenkinsfile.dev` tiene `agent any` y asume que Jenkins corre en la misma máquina que Vagrant.
¿Es correcto este diseño para la fase actual (Mac del fundador + VM Vagrant)?
¿Cuándo tiene sentido mover a `agent { label 'argus-server' }`?

**Q3 — DEBT-CONFIG-JINJA2-PIPELINE-001**
El diseño acordado: JSONs originales sagrados, plantillas Jinja2, valores por perfil hardware, generados en `.gitignore`.
En producción (RPi5, N100, servidor FEDER) los JSONs originales NO existirán — solo los generados.
¿Es correcto que el script calcule los valores óptimos en función del hardware detectado en runtime?
¿O los valores deben ser fijos por perfil (naive/edge-low/edge-medium/edge-high)?

**Q4 — EMECAS++ y el fix del delta E2E**
El fix cambia `test-e2e-live` de valor absoluto a delta (snapshot→60s→check).
Riesgo: si el sniffer no captura tráfico real en 60s (Vagrant en Mac), el delta será 0 y el test fallará igualmente.
¿Debería el test-e2e-live inyectar tráfico sintético mínimo para garantizar al menos 1 evento,
o debe medir solo tráfico orgánico?

**Q5 — Prioridad DAY 162**
Con la rama lista para merge tras EMECAS++, ¿cuál es el siguiente hito más valioso?
Opciones:
  A) DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2 — primera señal externa)
  B) DEBT-ARGUSPP-NTP-001 (prerequisito correlación multi-engine)
  C) DEBT-CRYPTO-AUTONOMY-001 (EXTENDED_AUTONOMY state machine)
  D) DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 (mover AlertClient a libcrypto_provider)
