# PROMPT_CONTINUE_CLAUDE — aRGus NDR DAY 161
*Generado: 2026-05-22 · branch: feature/day161-cicd-pipeline · main @ v0.9.4-day160*

---

## Contexto del proyecto

aRGus NDR es un sistema C++20 open-source de Network Detection & Response para infraestructura
crítica (hospitales, escuelas, municipios). PI y único desarrollador: Alonso (Badajoz, Extremadura).
Co-investigador institucional: Dr. Andrés Caro Lindo (UEx/INCIBE).
Paper: arXiv:2604.04952. Repo: github.com/alonsoir/argus.

Metodología: Test-Driven Hardening (TDH), Consejo de Sabios (8 modelos), EMECAS como
invariante de reproducibilidad. "Via Appia Quality". "JSON is the law".

**EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
**EMECAS++:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e`

---

## Realidad estratégica (aclarada DAY 160)

El gate para la colaboración UEx/INCIBE NO es una demo NDR el 22-09-2026.
Es demostrar que el pipeline produce datasets de valor científico suficiente para
que Andrés pueda introducir a Alonso oficialmente en el grupo de investigación.
El FEDER es consecuencia, no objetivo.

**Lo que le interesa a Andrés:** datasets de vanguardia producidos por múltiples
engines de análisis de red correlacionados.

**ADR-048 — Plan de 5 fases:**
- F1: aRGus solo (ya funciona — F1=0.9985)
- F2: aRGus + Suricata
- F3: F2 + Zeek
- F4: F3 + Wazuh
- F5: F4 + Neo4j (correlation engine — dataset final)

La hipótesis científica: al añadir señal progresivamente, el F1 del modelo ensemble
mejora de forma medible. Esa curva de mejora ES la contribución publicable.
Ground truth: sesión MITRE controlada vista por los 5 engines simultáneamente.

---

## Estado inicio DAY 161

**Branch activa:** `feature/day161-cicd-pipeline` (crear desde main @ v0.9.4-day160)
**Tags:** `v0.9.4-day160` en main (2 commits DAY 160)
**EMECAS++ DAY 159:** TODO VERDE (el de DAY 160 no se ejecutó — sesión de madrugada)

### Stack dev operacional (DAY 160)
- Vault v2.0.1 dev mode: `secret/argus/crypto` operacional ✅
- Jenkins 2.555.2: `http://localhost:8080` ✅ (Java 21 Temurin via SDKMAN)
- Plugin enterprise: `libvault_provider.so` — 6 tests verdes ✅
- Makefile: `make test-enterprise-plugin`, `make vault-dev-start`, `make vault-dev-stop` ✅
- Vagrantfile: todos los fixes DAY 160 codificados ✅

### ADVERTENCIA: Vault dev mode no persiste
Cada `vagrant reload` o reinicio mata Vault. Antes de cualquier trabajo:
```bash
make vault-dev-start
# verifica: vagrant ssh defender -c "vault status | grep Sealed"
```

---

## Prioridades DAY 161

### P0 — DEBT-WIRE-PROTOCOL-TEST-001 (30 min — ANTES de todo)
**Consejo 8/8 unánime:** sin este test el pipeline CI/CD no tiene cimientos.

`common/tests/test_wire_protocol.cpp`:
- Serializa payload con código de ml-detector (LZ4 LE memcpy uint32_t)
- Deserializa con código del firewall (mismo memcpy)
- Verifica: decoded_size == original_size, crypto_errors == 0
- El bug DEBT-FIREWALL-CRYPTO-FORMAT-001 (DAY 159) no puede repetirse

### P1 — Pipeline Jenkins básico (Jenkinsfile)
Secuencia del Consejo (ChatGPT/Kimi/DeepSeek convergentes):

```groovy
pipeline {
    agent any
    environment {
        VAULT_ADDR = 'http://127.0.0.1:8200'
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Bootstrap') { steps { sh 'make bootstrap' } }
        stage('Wire Protocol') { steps { sh 'make test-wire-protocol' } }
        stage('Unit Tests') { steps { sh 'make test-all' } }
        stage('Enterprise Plugin') {
            steps {
                withCredentials([string(credentialsId: 'vault-enterprise-token',
                                        variable: 'VAULT_TOKEN')]) {
                    sh 'make test-enterprise-plugin'
                }
            }
        }
        stage('Build .deb') { steps { sh 'make package-deb' } }
        stage('Deploy Vagrant Test') { steps { sh 'make deploy-vagrant-test' } }
    }
    post { always { sh 'make vault-dev-stop || true' } }
}
```

### P2 — generate_config.py --hardware naive
- Perfiles: `edge-low` (≤4GB), `edge-medium` (8GB), `edge-high` (≥16GB)
- Sustituye variables en JSON contrato con valores dev seguros
- TODO explícito en cada parámetro → BACKLOG-ZMQ-TUNING-001
- Sin auto-tuning hasta tener hardware físico UEx

### P3 — make package-deb (.deb como artefacto primario)
- `dpkg-deb` o `cmake --build --target package` (CPack)
- arm64 para RPi5, x86_64 para N100
- Jenkins archiva el .deb como artefacto del build

### P4 — DEBT-E2E-LIVE-DELTA-001
- `scripts/check_e2e_pipeline.py`: modo `check-delta`
- snapshot → 60s → delta ≥ 1
- Más robusto que valor absoluto histórico

---

## Secuencia recomendada DAY 161
git checkout -b feature/day161-cicd-pipeline
EMECAS++ (verificar todo verde desde DAY 160)
make vault-dev-start (Vault no persiste entre reinicios)
DEBT-WIRE-PROTOCOL-TEST-001 — common/tests/test_wire_protocol.cpp (30 min)
Jenkinsfile básico en raíz
Configurar Jenkins credentials: vault-enterprise-token (Secret Text)
generate_config.py --hardware naive
make package-deb (target nuevo)
make deploy-vagrant-test (VM Vagrant limpia instala el .deb)
DEBT-E2E-LIVE-DELTA-001
Commit + tag v0.9.5-day161
---

## Deudas abiertas (orden prioridad)

| DEBT | Prioridad | Estado |
|------|-----------|--------|
| DEBT-WIRE-PROTOCOL-TEST-001 | 🔴 P1 | HOY — antes del pipeline |
| DEBT-E2E-LIVE-DELTA-001 | 🔴 P1 | HOY si queda tiempo |
| DEBT-JENKINS-PROD-001 | 🔴 P0 | post-hardware UEx |
| DEBT-CRYPTO-AUTONOMY-001 | 🔴 P1 | EXTENDED_AUTONOMY state machine |
| DEBT-VAULT-PROD-SETUP-001 | 🔴 P0 | deadline: primera semana septiembre 2026 |
| DEBT-ARGUSPP-NTP-001 | 🔴 P0 | prerequisito correlación multi-engine |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | 🔴 P0 | Suricata+Zeek: community_id activo |
| DEBT-ARGUSPP-SURICATA-001 | 🟡 P1 | ADR-048 F2 |
| DEBT-EMECAS-DUAL-COMPILATION-001 | 🟡 P1 | CI compila ON+OFF |

**Nueva deuda a abrir DAY 161:**
- `DEBT-VAULT-PROD-SETUP-001` P0: Vault single-node producción (file backend, TLS,
  AppRole, audit log, unseal manual documentado). Deadline: primera semana septiembre 2026.
  Prerequisito para demo FEDER con Andrés. Dev mode no es aceptable en demo final.

---

## Reglas permanentes críticas

- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **Wire protocol (DAY 159):** todo contrato binario cross-componente tiene test en `common/tests/`
- **Enterprise fail-closed:** sin token válido el sistema para, nunca fallback silencioso
- **Artefacto primario:** `.deb` — Vagrant box es entorno de validación, no artefacto de release
- **Token enterprise en CI:** Jenkins Credentials Store (Secret Text) — nunca fichero en VM
- **Vault dev mode no persiste:** `make vault-dev-start` al inicio de cada sesión
- **-Werror:** 0 warnings es invariante permanente
- **JSON is the law:** toda config desde JSON canónico

---

## Jenkins — primer arranque DAY 160

- URL: `http://localhost:8080`
- Password inicial: `e0652929610d4b638a2cec1f453f800b`
- Plugins instalados: Git 5.10.1, HashiCorp Vault 379.v080d932e61e4
- Plugins necesarios DAY 161: Pipeline, Credentials Binding
- Configurar credential: `vault-enterprise-token` (Secret Text) =
  contenido de `/etc/argus/enterprise.token` en la VM

---

## ADR-048 — Roadmap Dataset Production

Ver BACKLOG.md sección ADR-048 para el plan completo de 5 fases.
DAY 161 está en F1 (pipeline aRGus solo, ya operacional).
La F2 (+ Suricata) es el siguiente hito científico — DEBT-ARGUSPP-SURICATA-001.

---

## Para comenzar DAY 161

```bash
# 1 — Crear rama
git checkout main
git pull
git checkout -b feature/day161-cicd-pipeline

# 2 — Verificar estado VM
vagrant status

# 3 — Si VM corriendo: arrancar Vault (no persiste)
make vault-dev-start

# 4 — EMECAS++ desde VM limpia si hay dudas
# vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e

# 5 — Primer objetivo: wire protocol test
# ver common/tests/ y añadir test_wire_protocol.cpp

# 6 — Jenkins en http://localhost:8080
# Configurar credential vault-enterprise-token antes de crear el pipeline
```
