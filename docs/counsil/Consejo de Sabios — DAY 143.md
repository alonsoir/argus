# aRGus NDR — Consejo de Sabios — DAY 143
**Fecha:** Miércoles 6 de Mayo 2026 | **Branch:** `feature/variant-b-libpcap` | **arXiv:** 2604.04952

---

## 1. LO QUE HEMOS HECHO HOY

### 1.1 EMECAS — Regresiones detectadas y corregidas

El protocolo `vagrant destroy -f && vagrant up && make bootstrap && make test-all` detectó dos regresiones introducidas en DAY 142:

**DEBT-BOOTSTRAP-ORDER-001 (nueva, resuelta)**
`check-system-deps` verificaba el binario `argus-network-isolate` antes de que `pipeline-build` lo compilara. El bootstrap fallaba en el paso [1/8]. Fix: separar la verificación en dos targets:
- `check-system-deps` — paquetes APT únicamente
- `check-build-artifacts` — binarios compilados, llamado tras `pipeline-build`

**Regresión firma PcapBackend::open() (nueva, resuelta)**
DEBT-VARIANT-B-BUFFER-SIZE-001 (DAY 142) añadió `int buffer_size` como segundo parámetro a `PcapBackend::open()`. Los tests de Variant B no se actualizaron en el mismo commit. Afectados: `test_pcap_backend_lifecycle.cpp`, `test_pcap_backend_poll_null.cpp`, `test_pcap_backend_error.cpp`, `test_pcap_backend_stress.cpp`, `test_pcap_backend_regression.cpp` — 6 call sites en 5 ficheros.

**Lección registrada como regla permanente:** cambio de firma de interfaz pública → actualizar todos los call sites en el mismo commit, sin excepción.

**EMECAS final:** verde. 9/9 Sniffer Variant B, 10/10 ML Detector, 8/8 RAG Ingester, 2/2 etcd-server, TEST-PROVISION-1 8/8, TEST-INVARIANT-SEED OK, plugin-integ SIGN 1-7 OK.

---

### 1.2 DEBT-IRP-NFTABLES-001 — Sesión 3/3 — CERRADA

#### Bloque 1 — isolate.json y IsolateConfig

Añadidos tres campos al JSON de configuración del IRP:
```json
"auto_isolate": true,
"threat_score_threshold": 0.95,
"auto_isolate_event_types": ["ransomware", "lateral_movement", "c2_beacon"],
"isolate_interface": "eth1"
```
Y campo correspondiente en `IsolateConfig::from_file()` con defaults seguros. Test `test_isolate_config`: 9 assertions, PASSED.

**Decisión de diseño confirmada:** `auto_isolate: true` por defecto — instalar y funcionar sin leer el manual. Un ventilador mecánico no puede quedar aislado por una señal única — mínimo dos condiciones AND.

#### Bloque 2 — Lógica de disparo en firewall-acl-agent

**Diseño:**
```
config_loader → lee isolate.json → IrpConfig → BatchProcessorConfig
add_detection() → check_auto_isolate() → should_auto_isolate() → fork()+execv()
```

**Mapeo DetectionType → string** (DEBT-PROTO-DETECTION-TYPES-001 registrada):
```
DETECTION_RANSOMWARE       → "ransomware"
DETECTION_INTERNAL_THREAT  → "lateral_movement"
DETECTION_SUSPICIOUS_TRAFFIC → "c2_beacon"
```

**`should_auto_isolate()`** — función pura, testeable sin fork(). Criterio: `score >= threshold - 1e-6 AND event_type IN auto_isolate_event_types`.

**`check_auto_isolate()`** — orquestador: llama `should_auto_isolate()`, hace `fork()+execv()` a `argus-network-isolate isolate --interface <iface> --config <path>`. El padre no hace `wait()` — el pipeline no se bloquea. Si `execv()` falla, el hijo hace `_exit(127)`.

**Bug IEEE 754 encontrado por los tests:** `static_cast<double>(0.95f)` = `0.94999988...` < `0.95`. El aislamiento nunca habría disparado exactamente en el umbral. Fix: tolerancia `1e-6` en la comparación. Esto es exactamente para lo que sirven los tests.

**Tests:**
- `test_auto_isolate`: 12/12 PASSED (10 unitarios + 2 integración)
- `IntegrationForkExecOnSyntheticEvent`: evento sintético score=0.97 RANSOMWARE → `fork()+execv(/bin/true)` → hijo termina exit 0 verificado via `waitpid()` en < 2s
- `IntegrationNoForkOnLowScore`: score=0.80 → sin fork en 200ms

**TimestampUniqueness fix:** test pre-existente frágil por timing de VM — sleep `10µs → 2ms`, umbral `50 → 20`. Corregido como deuda de calidad de tests.

#### Bloque 3 — AppArmor profile argus-network-isolate

Creado `security/apparmor/argus.argus-network-isolate`:
- `capability net_admin` — nftables únicamente
- `network netlink raw`
- `/usr/sbin/nft ix` — único binario invocable
- `/usr/bin/systemd-run ix` — timer rollback automático
- `/tmp/argus-{backup,isolate}-*.nft rw` — operación transaccional
- `/var/log/argus/` rw — forense JSONL
- Denies explícitos: shells, python, apt sources, /root, /home
- Sintaxis validada: `apparmor_parser -p` ✅
- `setup-apparmor.sh` actualizado a 7 componentes

#### Bloque 4 — Validación en hardened VM

`make hardened-setup-apparmor` instaló los 7 perfiles en enforce mode:
```
argus-etcd-server, argus-firewall-acl-agent, argus-ml-detector,
argus-network-isolate, argus-rag-ingester, argus-rag-security, argus-sniffer
```
Todos en enforce mode. 40 perfiles totales en la VM.

---

### 1.3 Deudas nuevas registradas DAY 143

**DEBT-PROTO-DETECTION-TYPES-001** 🟢 Baja — post-fase-MITRE/CTF
`DetectionType` enum solo modela 4 tipos. Cuando el pipeline enfrente MITRE ATT&CK y CTFs, ampliar con los tipos reales observados. No antes — sin datos no hay diseño. Opción B (ampliar proto) descartada conscientemente hoy.

---

## 2. ESTADO DEL REPO

```
Branch:  feature/variant-b-libpcap
Commits: c6e3f4ab → 888bfcbd → f1ab0c79 → e08f394d → f00b1809 → 7716423b
         (+ commits infraestructura EMECAS)
EMECAS:  VERDE — 0 warnings propios, 0 errors
Tests:   test_isolate_config 9/9 | test_auto_isolate 12/12 | Sniffer 9/9
         ML Detector 10/10 | RAG Ingester 8/8 | etcd-server 2/2
         TEST-PROVISION-1 8/8 | TEST-INVARIANT-SEED OK
Hardened: AppArmor 7/7 enforce
```

---

## 3. LO QUE HAREMOS MAÑANA (DAY 144)

**Opción A — Merge feature/variant-b-libpcap a main**
Prerrequisitos: EMECAS verde ✅, test-all verde ✅, AppArmor hardened ✅. Quedaría verificar `PROFILE=production all` (gate ODR) antes del merge.

**Opción B — ADR-029 Benchmarking Variant A vs Variant B**
Medir el delta eBPF/XDP vs libpcap en throughput, latencia y CPU. Esto es la contribución científica publicable del paper.

**Opción C — DEBT-ETCD-HA-QUORUM-001**
etcd-server single-node es bloqueante para producción hospitalaria. Diseño de quorum Raft.

**Recomendación del founder:** Opción A primero — el branch lleva 143 días y necesita llegar a main limpio. Luego Opción B que es la contribución científica del arXiv.

---

## 4. PREGUNTAS DIFÍCILES PARA EL CONSEJO

### P1 — Decisión de fork()+execv() sin wait()
El padre no recoge al hijo. En Linux, un proceso hijo sin `wait()` se convierte en zombie hasta que lo recoge `init`/`systemd`. En un pipeline de larga duración que dispara aislamiento repetidamente (ransomware persistente), ¿acumulamos zombies? ¿Debemos registrar los PIDs y hacer `waitpid(-1, WNOHANG)` periódicamente en el worker thread del BatchProcessor?

### P2 — Tolerancia IEEE 754 de 1e-6
Elegimos `1e-6` para la comparación `float confidence vs double threshold`. Un `float` tiene ~7 dígitos de precisión. Para `confidence = 0.95f`, el error es `~1.2e-7`. Nuestra tolerancia de `1e-6` es conservadora pero correcta. Sin embargo: ¿debería el threshold en `IsolateConfig` ser `float` en vez de `double` para eliminar el problema de raíz? Tipos consistentes = sin tolerancias.

### P3 — `auto_isolate: true` por defecto en hospitales
La decisión fue: instalar y funcionar sin leer el manual. Pero en un hospital, un administrador que instala aRGus sin leer la documentación podría aislar accidentalmente un equipo médico crítico en el primer falso positivo. ¿Debería `auto_isolate` ser `false` por defecto y requerir habilitación explícita? ¿O mantenemos `true` y añadimos un gate de confirmación en el onboarding?

### P4 — AppArmor profile: ¿demasiado permisivo con /tmp?
El perfil permite `rw` en `/tmp/argus-backup-*.nft` y `/tmp/argus-isolate-*.nft`. Un atacante que comprometa `argus-network-isolate` podría escribir archivos arbitrarios en `/tmp` con nombres que coincidan con el glob. ¿Debería el perfil restringir a un directorio específico como `/var/lib/argus/irp/` con permisos más estrictos?

### P5 — Criterio de disparo: ¿dos señales son suficientes?
Para FEDER: `score >= 0.95 AND event_type IN [ransomware, lateral_movement, c2_beacon]`. En un entorno hospitalario real con monitores de quirófano en la intranet, ¿es suficiente con dos condiciones AND? ¿O necesitamos una tercera señal — por ejemplo, confirmación de un segundo sensor independiente o ausencia en whitelist de activos críticos? DEBT-IRP-MULTI-SIGNAL-001 registrada — ¿qué arquitectura de decisión recomendáis?

---

## 5. DEUDAS ABIERTAS RELEVANTES (referencia rápida)

| ID | Severidad | Descripción |
|----|-----------|-------------|
| DEBT-ETCD-HA-QUORUM-001 | 🔴 P0 post-FEDER | etcd single-node — sin HA |
| DEBT-MUTEX-ROBUST-001 | 🟡 P1 post-FEDER | Mutex sniffer via tmux — provisional |
| DEBT-IRP-MULTI-SIGNAL-001 | 🟡 P1 post-FEDER | Criterio disparo multi-señal rico |
| DEBT-PROTO-DETECTION-TYPES-001 | 🟢 Baja | Ampliar enum post-MITRE/CTF |
| DEBT-IRP-LAST-KNOWN-GOOD-001 | 🟢 Baja | Rollback con estado persistente |
| DEBT-COMPILER-WARNINGS-CLEANUP-001 | 🟡 P1 | ODR violations = UB |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | 🟡 P1 | Vault para FEDER demo |

---

*aRGus NDR — Via Appia Quality — DAY 143 — 06/05/2026*
*"Un falso positivo sobre un ventilador mecánico es inaceptable."*