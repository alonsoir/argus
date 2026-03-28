# ML Defender (aRGus NDR) — BACKLOG
## Via Appia Quality 🏛️

---

## 📐 Criterio de compleción (explícito para paper)

| Estado | Criterio |
|---|---|
| ✅ 100% | Implementado + probado en condiciones reales + resultado documentado |
| 🟡 80% | Implementado + compilando + smoke test pasado, sin validación E2E completa |
| 🟡 60% | Implementado parcialmente o con valores placeholder conocidos |
| ⏳ 0% | No iniciado |

---

## ✅ COMPLETADO

### Day 95 (23 Mar 2026) — Cryptographic Provisioning Infrastructure

**tools/provision.sh — PHASE 1 completado y verificado:**
- `tools/provision.sh` con 4 modos: `full` | `status` | `verify` | `reprovision <component>`
- Ed25519 keypairs + ChaCha20 seeds (32B) para los 6 componentes del pipeline
- Paths AppArmor-compatible desde el primer día (ADR-019):
  `/etc/ml-defender/{component}/{private.pem|public.pem|seed.bin}`
- Permisos: `private.pem` + `seed.bin` → chmod 600, root:root
- Fingerprints SHA256 por componente + metadatos JSON de provisioning
- Backups automáticos antes de `reprovision`
- Verificación de integridad de keypairs (clave pública ↔ privada)
- Check de tamaño exacto del seed (32 bytes)

**Resultado verificado en VM (6/6 ✅):**
```
etcd-server        5d45cfbbd7a4bf14...  2026-03-23
sniffer            86df1c883bf196df...  2026-03-23
ml-detector        74d6e63b64d81573...  2026-03-23
firewall-acl-agent 42b91b813356c318...  2026-03-23
rag-ingester       5d77798b80410a9b...  2026-03-23
rag-security       c3359aac0b900ac9...  2026-03-23
```

**Bloque `identity` añadido a los 6 JSONs de componentes (ADR-013):**
```json
"identity": {
"component_id": "<nombre>",
"keys_dir":    "/etc/ml-defender/<nombre>",
"public_key":  "/etc/ml-defender/<nombre>/public.pem",
"private_key": "/etc/ml-defender/<nombre>/private.pem",
"seed_bin":    "/etc/ml-defender/<nombre>/seed.bin"
}
```

**rag-config.json — corrección arquitectural:**
- `"encryption": "AES-256-CBC"` eliminado (era letra muerta — rag-security
  nunca recibió tráfico ZMQ cifrado)
- Unificado a ChaCha20-Poly1305 con `enabled: false`
- `_architecture_note` documenta el flujo real de datos
- Logging unificado a `/vagrant/logs/lab/rag-security.log`

**Makefile — 4 targets nuevos:**
```makefile
make provision                              # full provisioning
make provision-status                       # tabla visual
make provision-check                        # verificación CI (fail-fast)
make provision-reprovision COMPONENT=<n>    # granular (ADR-013)
```
`pipeline-start` depende de `provision-check` — el pipeline nunca arranca
sin claves válidas.

**Vagrantfile — bloque `cryptographic-provisioning`:**
```ruby
run: "once"  # persiste entre reinicios, re-provisionar con: make provision
```
`tools/provision.sh` añadido a sudoers sin password para vagrant.

**Acta Consejo DAY 95 (6/7 — Parallel.ai pendiente):**
Unanimidad en validación técnica. Puntos críticos identificados:
- DEBT-CRYPTO-001: nonce management entre sesiones con seeds persistentes
- DEBT-CRYPTO-002: HKDF para derivar session keys desde seed (no usar directo)
- DEBT-CRYPTO-003: check de entropy antes de generar claves en VM

---

### Day 93 (21 Mar 2026) — ADR-012 PHASE 1: plugin-loader + ABI validation

**plugin-loader PHASE 1 implementado y validado:**
- `common/include/sentinel.hpp`: `MISSING_FEATURE_SENTINEL = -9999.0f` centralizado
- `plugin-loader/include/plugin_loader/plugin_api.h`: contrato C puro, ABI estable, `PLUGIN_API_VERSION=1`
- `plugin-loader/include/plugin_loader/plugin_loader.hpp`: interfaz C++ con `PluginLoader` + `PluginStats`
- `plugin-loader/src/plugin_loader.cpp`: `dlopen`/`dlsym` lazy loading, sin crypto, sin seed-client
- `plugin-loader/CMakeLists.txt`: patrón idéntico a `crypto-transport`
- `plugins/hello/hello_plugin.cpp`: hello world plugin — validación contrato end-to-end
- `Makefile`: targets `plugin-loader-build/clean/test` + `plugin-hello-build/clean`

**Restricciones PHASE 1 respetadas:**
- Plugins: SOLO feature extraction — decisión de bloqueo NUNCA en plugin ✅
- Sin crypto, sin seed-client (PHASE 2, ADR-013) ✅
- `MISSING_FEATURE_SENTINEL` desde cabecera común, no redefinido por plugin ✅

**ABI validation via Python3/ctypes:**
```
plugin_api_version() = 1  →  ABI version match: True ✅
```

**Artefactos desplegados:**
- `libplugin_loader.so.1.0.0` → `/usr/local/lib/` (53K) ✅
- `libplugin_hello.so` → `/usr/lib/ml-defender/plugins/` (16K) ✅

---

### Day 83 (12 Mar 2026) — Ground truth bigFlows + CSV E2E + MERGE TO MAIN

**FPR ML = 2/40,467 = 0.0049%** — dato publicable de especificidad
ML reduce FPs del Fast Detector en factor ~15,500x (2 vs 31,065)
CSV Pipeline E2E: **100% ✅**
**MERGE TO MAIN ejecutado DAY 83 — tag: v0.83.0-day83-main** ✅

---

### Day 82 (11 Mar 2026) — Balanced dataset validation + DEBT-FD-001
### Day 81 (10 Mar 2026) — Comparativa F1 limpia + ADR-005
### Day 80 (9 Mar 2026) — JSON is the LAW ✅ — F1=0.9934
### Day 79 (8 Mar 2026) — Sentinel Fix + F1=0.9921 baseline CTU-13 Neris
### Day 76 (5 Mar 2026) — Proto3 Sentinel Fix + Pipeline Estable
### Day 72 (Feb 2026) — Deterministic trace_id correlation
### Day 64 (21 Feb 2026) — CSV Pipeline + Test Suite
### Day 53 — HMAC Infrastructure (32/32 tests ✅)
### Day 52 — Stress Testing (364 ev/s, 54% CPU, 127MB, 0 crypto errors)

---

## 🔄 EN CURSO / INMEDIATO

### DAY 96 — seed-client + ADR-012 PHASE 1b (P1)

**P0 — Paper arXiv:**
- Draft v5 completado DAY 88 ✅ | LaTeX DAY 89 ✅
- Email endorser Sebastian Garcia enviado DAY 89 ✅
- **Pendiente:** respuesta endorser → submit arXiv cs.CR
- Deadline: DAY 96 — si no responde → email Yisroel Mirsky (Tier 2)

**P1 — libs/seed-client:**

> ⚠️ ATENCIÓN — Insight crítico del Consejo DAY 95 (ChatGPT + Grok, unanimidad):
> El seed NO debe usarse directamente como clave simétrica.
> Arquitectura correcta:
> ```
> SeedClient → entrega seed a CryptoTransport
> CryptoTransport → HKDF(seed, context) → session_key efímera
> ```
> `SeedClient` sigue siendo igual de simple — entrega material, no claves.
> El contrato debe quedar explícito en la interfaz y en los comentarios.

```cpp
// libs/seed-client/include/seed_client/seed_client.hpp
class SeedClient {
public:
    explicit SeedClient(const std::string& config_json_path);
    void load();                                     // lee seed.bin del identity.keys_dir del JSON
    const std::array<uint8_t, 32>& seed() const;    // material base para HKDF en crypto-transport
    bool is_loaded() const;
    const std::string& component_id() const;
    // PHASE 2: seed_rotated() para rotación futura
private:
    std::string keys_dir_;
    std::string component_id_;
    std::array<uint8_t, 32> seed_;
    bool loaded_ = false;
};
```

**SeedClient NO hace:** red, generación, distribución, cifrado/descifrado
**SeedClient SÍ hace:** leer `identity.keys_dir` del JSON → abrir `seed.bin`
→ verificar 32 bytes exactos → exponer como `array<uint8_t,32>`

```
libs/seed-client/
  CMakeLists.txt
  include/seed_client/seed_client.hpp
  src/seed_client.cpp
  tests/test_seed_client.cpp
```

**Dependencias:** solo nlohmann_json. Más primitivo que crypto-transport y etcd-client.

**P1 — ADR-012 PHASE 1b (si queda tiempo):**
- Integrar plugin-loader en sniffer
- Test suite con CTest

---

## 🔐 BACKLOG CRIPTOGRÁFICO (nuevo — DAY 95)

### DEBT-CRYPTO-001 — Nonce management entre sesiones (🔴 P1 — DAY 96)

**Origen:** ChatGPT + Grok, feedback unánime DAY 95.

ChaCha20 con nonce reutilizado = ruptura total del cifrado. Con seeds
persistentes en disco existe riesgo de reúso de nonce entre sesiones.

**Acción:** verificar en crypto-transport que el nonce management es correcto
cuando el seed viene de `SeedClient` (PHASE 2). Documentar política de nonce
antes de activar seed-client en producción.

**Afecta:** diseño de seed-client DAY 96 — el contrato debe dejar claro
que `crypto-transport` es el único responsable del nonce.

### DEBT-CRYPTO-002 — HKDF para derivación de session keys (🔴 P1 — DAY 96)

**Origen:** ChatGPT + Grok + Gemini, feedback unánime DAY 95.

El seed de 32B es **material base**, no clave simétrica directa.

```
seed.bin → HKDF(seed, context="ml-defender:{component}:v1") → session_key
```

Sin HKDF:
- No hay forward secrecy
- Compromiso de seed = descifrado histórico completo
- Rotación difícil sin reinicio

**Acción:** `crypto-transport` debe recibir el seed de `SeedClient` y aplicar
HKDF internamente. `SeedClient` nunca debe documentar su salida como
"clave lista para usar".

### DEBT-CRYPTO-003 — Check de entropy antes de generar claves (🟡 P2 — DAY 96)

**Origen:** Grok, feedback DAY 95.

VMs con entropy pobre al arranque pueden generar claves débiles.

```bash
# Añadir en provision.sh antes de openssl genpkey:
avail=$(cat /proc/sys/kernel/random/entropy_avail)
if [ "$avail" -lt 256 ]; then
    apt-get install -y haveged
    systemctl start haveged
fi
```

**Acción:** añadir check + haveged como fallback en `tools/provision.sh`.

### FEAT-CRYPTO-1 — Rotación de claves sin downtime (🟡 P2 — DAY 97+)

**Origen:** ChatGPT + Grok + Gemini, pregunta explícita de Gemini DAY 95.

Diseñar mecanismo de rotación:
- `reprovision` actual requiere restart del componente
- Zero-downtime requiere: grace period + doble lectura de seed
- Relacionado con ADR-013 PHASE 2 (seed-client)

**Acción:** diseño en ADR-013 addendum antes de implementar.

### FEAT-CRYPTO-2 — Handshake efímero entre componentes (🟢 P3 — PHASE 2)

**Origen:** ChatGPT (Noise simplificado), feedback DAY 95.

Una vez que seed-client esté integrado, preparar terreno para:
- Handshake efímero tipo Noise_XX
- Session keys distintas por par de componentes
- Forward secrecy real

### FEAT-CRYPTO-3 — TPM 2.0 / HSM para claves enterprise (🟢 P3 — ENT-8)

**Origen:** Gemini + Grok, feedback DAY 95. Ver también ENT-8.

PHASE 1: claves en `/etc/ml-defender/` con chmod 600 (correcto para open-source)
PHASE 2 enterprise: TPM 2.0 (`tpm2-tools`) / YubiKey / Nitrokey

**Acción:** documentar en `docs/SECURITY_MODEL.md` los límites actuales
y el roadmap evolutivo. Gemini propone texto explícito:
```markdown
## Cryptographic Key Storage (PHASE 1)
- Keys stored in /etc/ml-defender/ with 0600 permissions
- Protected by OS DAC + AppArmor (MAC)
- Limitation: compromise of root account exposes keys
- PHASE 2 roadmap: TPM 2.0 integration (ENT-8)
```

---

## 📋 BACKLOG — COMMUNITY

### 🟥 P0 — Recolección sistemática de datos etiquetados

- [ ] **FEAT-LABEL-1:** Almacenar eventos con etiqueta del fast detector
- [ ] **FEAT-LABEL-2:** Campo "revisión humana" opcional

### 🟧 P1 — Mejora y observabilidad del Fast Detector

- [ ] **FEAT-FP-1:** Registro de falsos positivos y negativos del fast detector
- [ ] **FEAT-FP-2 / DEBT-FD-001:** Migrar FastDetector Path A a configuración JSON
    - THRESHOLD_EXTERNAL_IPS=10, THRESHOLD_SMB_CONNS=3, THRESHOLD_PORT_SCAN=10,
      THRESHOLD_RST_RATIO=0.2, WINDOW_NS=10s — todos hardcodeados en fast_detector.hpp
    - Path B (send_ransomware_features) sí lee JSON ✅
    - Fix: inyectar FastDetectorConfig en constructor de FastDetector
    - Documentado en ADR-006. **Prerequisito bloqueante para FEAT-RANSOM-* y FEAT-RETRAIN-***

### 🟨 P2 — Ciclo de reentrenamiento ML con datos pipeline-native

- [ ] **FEAT-RETRAIN-1:** Generar dataset balanceado desde datos recolectados
- [ ] **FEAT-RETRAIN-2:** Entrenar y evaluar nuevos modelos RandomForest C++20
- [ ] **FEAT-RETRAIN-3:** A/B testing — dos versiones ML en paralelo

---

### 🟨 P2 — Expansión por familias de ransomware (FEAT-RANSOM-*)

**Prerequisito bloqueante:** DEBT-FD-001 cerrado (FEAT-FP-2)

**Principios de diseño (inmutables):**
1. **Dificultad ascendente** — familias más fáciles primero.
2. **Modelo fundacional, no modelos especializados** — objetivo final: un único
   RandomForest ensemble que haya visto todo.
3. **Misma estrategia que la actual** — sintético → modelo prueba → pcap relay →
   dataset pipeline-native → modelo mejorado. Repetir hasta convergencia.
4. **Features como decisión del Consejo** — consultar antes de implementar cada familia.
5. **La misma infraestructura sirve para todo** — FEAT-RETRAIN-* es reutilizable.
6. **Open source primero, enterprise después.**

---

#### FEAT-RANSOM-2 — Neris Extended | FEAT-RANSOM-1 — WannaCry/NotPetya
#### FEAT-RANSOM-3 — DDoS Variants | FEAT-RANSOM-4 — Ryuk/Conti
#### FEAT-RANSOM-5 — LockBit (BLOQUEADO hasta DEBT-PHASE2)

*(contenido detallado sin cambios respecto a versión anterior)*

---

### 🟨 P2 — Pipeline genérico de reentrenamiento (FEAT-RETRAIN-*)

*(contenido detallado sin cambios respecto a versión anterior)*

---

### 🟩 P3 — Aprendizaje continuo (Enterprise)

- [ ] **ENT-RETRAIN:** Ciclo de reentrenamiento automático periódico
- [ ] **ENT-1 (Federated):** prerequisito: validación local P2

### 🟩 P4 — Consenso mejorado firewall
- [ ] ADR-007: Consenso AND para bloqueo | P1-PHASE2 | zmq_handler.cpp

---

### Nota del Consejo de Sabios (DAY 81)

> "El fast detector ya es el backbone que protege. El ml-detector es hoy un
> observador silencioso y una fábrica de datos. La prioridad es no romper
> el escudo mientras alimentamos la máquina de aprendizaje."

### Nota del Consejo de Sabios (DAY 95 — acta #3)

> "Day 95 cierra con la base de confianza sobre la cual se construirán
> ENT-1 (federación), ENT-3 (P2P seed) y ENT-5 (rag-world).
> Sin esta piedra angular, esos features serían inseguros por diseño."
>
> "El seed no es una clave — es material base. HKDF primero."
>
> — ChatGPT5 · DeepSeek · Gemini · Grok · Qwen (unanimidad 5/5)
> — Parallel.ai (pendiente)

---

### FASE 3 — rag-ingester HMAC validation
### CsvEventLoader — rag-ingester
### CsvRetentionManager / ADR-005 / Estandarización logs ES→EN
### FASE 4 — Grace Period + Key Versioning
### FASE 5 — Auto-Rotation claves HMAC
### rag-local — informes PDF, geolocalización, historial

---

## 🏢 BACKLOG — ENTERPRISE

### ENT-MODEL-1 — Epic pcap relay (primer modelo enterprise — aprendizaje)
### ENT-MODEL-2 — Modelos de flota distribuida (largo plazo)
### ENT-1 — Federated Threat Intelligence
### ENT-2 — Attack Graph Generation (GraphML + STIX 2.1)
### ENT-3 — P2P Seed Distribution via Protobuf
### ENT-4 — Hot-Reload de Configuración en Runtime
### ENT-5 — rag-world (Telemetría Global Federada)
### ENT-6 — Integración Threat Intelligence (MISP/OpenCTI)
### ENT-7 — Observabilidad OpenTelemetry + Grafana
### ENT-8 — SecureBusNode (HSM + USB Root Key) ← ver FEAT-CRYPTO-3
### ENT-9 — Captura y correlación opcional de datagramas sospechosos

---

## 🗺️ Roadmap ransomware expansion

*(sin cambios respecto a versión anterior)*

---

## 🔔 Consultas pendientes al Consejo de Sabios

| Consulta | Timing | Objetivo |
|---|---|---|
| Features WannaCry/NotPetya | Antes de FEAT-RANSOM-1 | ¿DNS query feature? ¿Packet size? |
| WINDOW_NS para Ryuk/Conti | Antes de FEAT-RANSOM-4 | ¿Ventanas de minutos? ¿Coste latencia? |
| Features LockBit | Antes de FEAT-RANSOM-5 | TLS anomaly, byte ratio |
| Python vs C++20 FEAT-RETRAIN-2 | Antes de FEAT-RETRAIN-2 | Prototipo vs producción |
| Proporciones dataset épico | Antes de ENT-MODEL-1 | Balance óptimo entre familias |
| Política de nonce ChaCha20 | DAY 96 (DEBT-CRYPTO-001) | Gestión nonce con seeds persistentes |
| HKDF context string | DAY 96 (DEBT-CRYPTO-002) | Formato canónico para derivación |

---

## 📊 Estado global del proyecto

```
                              [criterio: impl+test E2E+documentado = 100%]

Foundation + Thread-Safety:           ████████████████████ 100% ✅
Contract Validation:                  ████████████████████ 100% ✅
Build System:                         ████████████████████ 100% ✅
HMAC Infrastructure (F1+F2):          ████████████████████ 100% ✅
Proto3 Pipeline Stability:            ████████████████████ 100% ✅
Logging Standard (6 components):      ████████████████████ 100% ✅
Sentinel Correctness:                 ████████████████████ 100% ✅
F1-Score Validation (CTU-13):         ████████████████████ 100% ✅
Thresholds desde JSON:                ████████████████████ 100% ✅
F1 Comparativa Limpia:                ████████████████████ 100% ✅
Infraestructura Experimentos:         ████████████████████ 100% ✅
CSV Pipeline ml-detector:             ████████████████████ 100% ✅
CSV Pipeline firewall-acl-agent:      ████████████████████ 100% ✅
F1-Score Validación (balanceado):     ████████████████████ 100% ✅
ML Score Investigation:               ████████████████████ 100% ✅
pipeline_health.sh:                   ████████████████████ 100% ✅
Paper arXiv (draft v5):               ████████████████████ 100% ✅  ← DAY 88
LaTeX main.tex:                       ████████████████████ 100% ✅  ← DAY 89
Email endorser Sebastian Garcia:      ████████████████████ 100% ✅  ← DAY 89
Cryptographic Provisioning PHASE 1:   ████████████████████ 100% ✅  ← DAY 95
Identity blocks (6 JSONs):            ████████████████████ 100% ✅  ← DAY 95
ChaCha20 unificado pipeline:          ████████████████████ 100% ✅  ← DAY 95
plugin-loader ADR-012 PHASE 1:        ████████████████░░░░  80% 🟡  integración sniffer DAY 96
trace_id correlación:                 ████████████████░░░░  80% 🟡  2 fallos DAY 72
Test Suite:                           ████████████████░░░░  80% 🟡  2 fallos trace_id
Ring Consumer Real Features:          ████████████░░░░░░░░  60% 🟡  28/40 reales
seed-client (libs/):                  ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P1 DAY 96
DEBT-CRYPTO-001 (nonce mgmt):         ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P1 DAY 96
DEBT-CRYPTO-002 (HKDF):              ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P1 DAY 96
DEBT-CRYPTO-003 (entropy check):      ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2 DAY 96
Fast Detector Config (DEBT-FD-001):   ████░░░░░░░░░░░░░░░░  20% 🟡  fix PHASE2
rag-local (community):                ████░░░░░░░░░░░░░░░░  20% 🟡
FEAT-RANSOM-2 (Neris Extended):       ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2, post DEBT-FD-001
FEAT-RANSOM-1 (WannaCry/NotPetya):    ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2
FEAT-RANSOM-3 (DDoS Variants):        ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2
FEAT-RANSOM-4 (Ryuk/Conti):           ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2, req PHASE2
FEAT-RANSOM-5 (LockBit):              ░░░░░░░░░░░░░░░░░░░░   0% ⏳  BLOQUEADO (PHASE2)
FEAT-RETRAIN-1+2+3:                   ░░░░░░░░░░░░░░░░░░░░   0% ⏳  P2, paralelo
ENT-MODEL-1 (epic pcap relay):        ░░░░░░░░░░░░░░░░░░░░   0% ⏳  post todos fundacionales
FASE 3 rag-ingester HMAC:             ░░░░░░░░░░░░░░░░░░░░   0% ⏳
CsvEventLoader rag-ingester:          ░░░░░░░░░░░░░░░░░░░░   0% ⏳
Attack Graph Generation:              ░░░░░░░░░░░░░░░░░░░░   0% ⏳  ENT-2
Federated Threat Intelligence:        ░░░░░░░░░░░░░░░░░░░░   0% ⏳  ENT-1
P2P Seed Distribution:                ░░░░░░░░░░░░░░░░░░░░   0% ⏳  ENT-3
ENT-MODEL-2 (flota distribuida):      ░░░░░░░░░░░░░░░░░░░░   0% ⏳  largo plazo
```

---

## 🔑 Decisiones de diseño consolidadas

| Decisión | Resolución |
|----------|------------|
| CSV cifrado | ❌ No — sin cifrado, con HMAC por fila |
| Sentinel correctness | -9999.0f fuera del dominio ✅ DAY 79 |
| 0.5f TCP half-open | Valor semántico válido — comentario protector ✅ DAY 79 |
| Thresholds ML | Desde JSON — CERRADO ✅ DAY 80 |
| Fichero fuente JSON sniffer | `sniffer/config/sniffer.json` (NO build-debug) ✅ DAY 81 |
| Log standard | /vagrant/logs/lab/COMPONENTE.log ✅ DAY 79 |
| Dual logs ml-detector | detector.log=fuente verdad, ml-detector.log=arranque — ADR-005 ✅ |
| FlowStatistics Phase 2 | tcp_udp_ratio/protocol_variety/duration_std → DEBT-PHASE2 ✅ |
| GeoIP en critical path | ❌ Deliberadamente fuera — latencia inaceptable |
| Fast Detector dual-path | Path A hardcodeado (DAY 13), Path B JSON (DAY 80). DEBT-FD-001. Fix PHASE2 |
| ML attack counters | 3 semánticas distintas: RF vote / conf>=0.65 / malicious_threshold |
| level1_attack threshold | 0.65 en ml-detector/config/ml_detector_config.json |
| CSV paths (fuente verdad) | ml-detector: /vagrant/logs/ml-detector/events/ — firewall: /vagrant/logs/firewall_logs/ ✅ |
| pipeline_health.sh VM | vagrant ssh defender (no server) ✅ DAY 83 |
| Modelo fundacional vs especializado | Un único RF ensemble que lo haya visto todo ✅ DAY 89 |
| Orden expansión familias | Dificultad ascendente: Neris→WannaCry→DDoS→Ryuk→LockBit ✅ DAY 89 |
| LockBit bloqueado | Indetectable hasta DEBT-PHASE2 (12 features TLS/byte ratio) ✅ DAY 89 |
| Enterprise vs open source | Fundacionales → MIT core. Enterprise → flota distribuida ✅ DAY 89 |
| Algoritmo de cifrado pipeline | ChaCha20-Poly1305 unificado en 6 componentes ✅ DAY 95 |
| AES-256-CBC en rag-security | Eliminado — era letra muerta. rag-security lee FAISS/SQLite, no ZMQ ✅ DAY 95 |
| Seed como material base | Seed → HKDF → session_key. Nunca usar seed como clave directa ✅ DAY 95 |
| Provisioning tool location | `tools/provision.sh` (no `scripts/`) — mismo nivel que stress/fuzzing ✅ DAY 95 |
| Keys AppArmor-compatible | `/etc/ml-defender/{component}/` paths fijos, chmod 600 ✅ DAY 95 |
| Fail-closed security | pipeline-start depende de provision-check. Sin claves = no arranca ✅ DAY 95 |
| Vagrant provisioning crypto | run:"once" — claves persisten entre reinicios ✅ DAY 95 |

---

*Última actualización: Day 95 — 23 Mar 2026*
*Branch: feature/plugin-loader-adr012*
*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic), Grok, ChatGPT5, DeepSeek, Qwen, Gemini, Parallel.ai*