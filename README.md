# ML Defender (aRGus NDR)

**Open-source, embedded-ML network detection and response system protecting critical infrastructure from ransomware and DDoS attacks.**

[![Via Appia Quality](https://img.shields.io/badge/Via_Appia-Quality-gold)](https://en.wikipedia.org/wiki/Appian_Way)
[![Council of Wise Ones](https://img.shields.io/badge/Architecture-Reviewed_by_8_Models-blueviolet)](#-consejo-de-sabios--multi-model-peer-review)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![F1=0.9985 Validated](https://img.shields.io/badge/Status-F1%3D0.9985_Validated-brightgreen)]()
[![Tests: make test-all VERDE](https://img.shields.io/badge/Tests-make_test--all_VERDE-brightgreen)]()
[![Pipeline: 6/6](https://img.shields.io/badge/Pipeline-6%2F6_RUNNING-brightgreen)]()
[![Plugin Integrity](https://img.shields.io/badge/Plugin_Integrity-ADR--025_Ed25519-brightgreen)](docs/adr/ADR-025-plugin-integrity-ed25519.md)
[![safe_path](https://img.shields.io/badge/safe__path-ADR--037_header--only-brightgreen)](contrib/safe-path/)
[![PHASE 4](https://img.shields.io/badge/PHASE_4-COMPLETADA-brightgreen)]()
[![AppArmor](https://img.shields.io/badge/AppArmor-7%2F7_enforce-brightgreen)]()
[![Falco](https://img.shields.io/badge/Falco-11_reglas_aRGus-brightgreen)]()
[![BSR](https://img.shields.io/badge/BSR-cap__bpf_ADR--039-brightgreen)]()
[![ADR-040](https://img.shields.io/badge/ADR--040-ML_Retraining_Contract-blue)](docs/adr/ADR-040-ml-plugin-retraining-contract.md)
[![ADR-041](https://img.shields.io/badge/ADR--041-FEDER_HW_Metrics-orange)](docs/adr/ADR-041-hardware-acceptance-metrics-feder.md)
[![Variant B](https://img.shields.io/badge/ADR--029-Variant_B_libpcap_pipeline-blue)]()
[![Reproducible](https://img.shields.io/badge/Infra-make_bootstrap-brightgreen)]()
[![XGBoost](https://img.shields.io/badge/XGBoost-Prec%3D0.9945_In--Distribution-brightgreen)]()
[![Hardened](https://img.shields.io/badge/Security-v0.7.0--variant__b-brightgreen)]()
[![PRE-PRODUCTION](https://img.shields.io/badge/Status-PRE--PRODUCTION-orange)]()
[![Crypto](https://img.shields.io/badge/Crypto-HKDF_SHA256+ChaCha20_Poly1305-orange)]()
[![arXiv](https://img.shields.io/badge/arXiv-2604.04952_cs.CR-red)](https://arxiv.org/abs/2604.04952)
[![TDH](https://img.shields.io/badge/Methodology-Test_Driven_Hardening-purple)](https://github.com/alonsoir/test-driven-hardening)
[![IRP](https://img.shields.io/badge/IRP-argus--network--isolate_ADR--042-red)]()
[![ADR-043](https://img.shields.io/badge/ADR--043-Memoria_Episódica_Distribuida-blue)](docs/adr/ADR-0043-memoria-episodica-distribuida-v4.md)

📜 Living contracts: [Protobuf schema](docs/contracts/Protobuf%20contracts.md) · [Pipeline configs](docs/contracts/JSON%20contracts.md) · [RAG API](docs/contracts/Rag%20security%20commands.md)

---

✅ `main` is tagged `v0.7.1-day147`. Branch activa: `main` — Experimento comparativo tres paradigmas completado (DAY 147). Paper v22 generado.
**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**

---

## Estado actual — DAY 147 (2026-05-10)

**Tag activo:** `v0.7.1-day147` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v22 (tres paradigmas: Suricata + Zeek + aRGus + DAY 147)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026

### Pipeline
- 6/6 componentes RUNNING — validado EMECAS DAY 145 ✅
- `make test-all`: ALL TESTS COMPLETE (65/65 PASSED — 0 FAILED) ✅
- `make PROFILE=production all`: Gate ODR — ALL COMPONENTS BUILT ✅
- `make argus-network-isolate-test`: dry-run PASSED ✅

### Hitos DAY 145 🎉
- **ADR-029 Variant A vs B x86** — libpcap ~2× eBPF en VirtualBox virtio (artefacto SKB mode). Equivalencia funcional confirmada.
- **Bootstrap múltiple** — `bootstrap-x86-ebpf` + `bootstrap-x86-libpcap`. `bootstrap` = alias de A.
- **pipeline-status** distingue Variant A/B + detecta invariant violation.
- **Relay targets** — resumen inline por velocidad + rutas log + nota MTU en banner.
- **Paper v19** — §6 ADR-029, §10.9, §11.17, §12, abstract actualizado.
- **Failed packets (2,630):** artefacto fijo pcap CTU-13 Neris — frames jumbo MTU VirtualBox. No son errores del pipeline.

### Hitos DAY 146 🎉
- **EMECAS verde** — 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
- **Experimento comparativo Suricata 6.0.10 vs aRGus NDR** — CTU-13 Neris, mismas condiciones. Suricata: 0 alertas (ET Open no cubre Neris 2011). aRGus: F1=0.9985, Recall=1.0000.
- **Makefile**: `make up-argus`, `make up-suricata`, `make halt-argus`, `make halt-suricata`, `make experiment-suricata-run/results`.
- **Paper Draft v20** generado — nueva §8.13 con comparativa directa, Tabla comparación actualizada con datos empíricos Suricata.
- **Vagrantfile Suricata** operativo — `nictype1 virtio` (fix crítico DHCP NAT), 50,010 reglas ET Open cargadas.

### Hitos DAY 147 🎉
- **Bug fix pipeline-status** — pgrep fallback para procesos huérfanos (tmux + pgrep OR). Commit `42c04b06`.
- **Búsqueda ruleset ET Open 2011** — no encontrado en fuentes públicas. Hallazgo clave: Neris CTU-13 escenario 42 usa HTTP C2, no solo IRC. Paper v21 §8.13 actualizado.
- **Experimento Zeek 8.1.2 (tres paradigmas)** — modo offline (`zeek -r pcap`), scripts por defecto, determinístico:
  - Suricata 6.0.10: F1=0.000, TP=0 (sin firmas para Neris 2011)
  - Zeek 8.1.2 (default): F1=0.042, Precision=1.000, TP=14 (SSL::Invalid_Server_Cert)
  - aRGus NDR: F1=0.9985, Recall=1.000, TP=646
- **weird.log**: Zeek observa IRC, HTTP beaconing, SMB lateral movement, spam — sin alertar. Distinción observabilidad vs detección.
- **Paper Draft v21** — §8.13 hallazgos reales DAY 147 + Springer 2023 (signature aging).
- **Paper Draft v22** — §8.14 Three Paradigms (tablas + análisis + §13 reproducibilidad Zeek).
- **Makefile**: `make experiment-zeek-up/run/results`. Infraestructura `experiments/zeek-comparative/`.
- **Tag:** `v0.7.1-day147`.

### Hitos DAY 143-144 🎉
- **DEBT-IRP-NFTABLES-001 CERRADA** — IRP completo: config → disparo → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests.
- **DEBT-IRP-SIGCHLD-001 CERRADA** — SA_NOCLDWAIT. SigchldTest.NoZombiesAfterNForks PASSED.
- **DEBT-IRP-AUTOISO-FALSE-001 CERRADA** — isolate.json única fuente de verdad. 5 tests PASSED.
- **DEBT-IRP-BACKUP-DIR-001 CERRADA** — /run/argus/irp/. AppArmor + provision.sh actualizados.
- **Gate ODR production SUPERADO** — 3 ODR violations reales detectadas y corregidas bajo -flto.

### Deuda técnica abierta

| Deuda | Prioridad | Target |
|-------|-----------|--------|
| DEBT-IRP-TMPFILES-001 | ✅ CERRADA DAY 146 | tmpfiles.d + provision.sh |
| DEBT-IRP-IPSET-TMP-001 | ✅ CERRADA DAY 146 | ipset_wrapper /run/argus/irp/ |
| DEBT-EMECAS-VERIFICATION-001 | ✅ CERRADA DAY 146 | README.md blockquote EMECAS |
| DEBT-IRP-FLOAT-TYPES-001 | 🟡 P1 | pre-FEDER (tipos score float/double) |
| DEBT-IRP-PROB-CONJUNTA-001 | 🟡 P1 | post-FEDER (señal conjunta) |
| DEBT-ETCD-HA-QUORUM-001 | 🔴 P0 | post-FEDER (OBLIGATORIO) |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Alta | post-merge |
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | 🔴 Alta | pre-FEDER |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | 🔴 Alta | pre-FEDER |
| DEBT-MUTEX-ROBUST-001 | 🟡 P1 | post-FEDER |
| DEBT-ADR040-001..012 | ⏳ | post-FEDER |
| DEBT-ADR041-001..006 | ⏳ | pre-FEDER |

| DEBT-PARQUET-SCHEMA-001 | 🔴 P0 bloqueante | Definir schema Parquet ml-detector y firewall-acl-agent desde CSVs reales |
| DEBT-VAULT-FEDERATION-001 | 🟡 P1 pre-FEDER | Offboarding instalaciones: destrucción de claves, retención de datos GDPR |
| DEBT-LEGAL-DATA-RETENTION-001 | 🟡 P1 pre-FEDER | Dictamen jurídico GDPR retención datos pseudonimizados post-cliente |
| DEBT-KPSEUDO-ROTATION-MIGRATION-001 | 🟡 P1 pre-FEDER | Migración identidades Neo4j tras rotación K_pseudo |
| DEBT-GDPR-ERASURE-001 | 🟡 P1 pre-FEDER | Flujo derecho al olvido Art. 17 GDPR — comando borrado firmado |
| DEBT-KPSEUDO-HKDF-HIERARCHY-001 | ⏳ P3 post-FEDER | Jerarquía HKDF para K_pseudo (host/flow/model desde K_root) |
### Próxima frontera — DAY 146+
1. DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot
2. DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
3. Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores)
4. Abrir feature/adr029-variant-c-arm64 scope definido

---

## 🏗️ Tres variantes del pipeline

| Variante | Estado | Descripción |
|----------|--------|-------------|
| **aRGus-dev** | ✅ Activa (`main`) | x86-debug, imagen Vagrant completa. Para investigación y desarrollo diario. |
| **aRGus-production** | 🟡 En construcción | x86-apparmor + arm64-apparmor. AppArmor enforce, cap_bpf, Falco, noexec. Para hospitales, escuelas, municipios. |
| **aRGus-seL4** | ⏳ Research track post-FEDER | Kernel seL4, libpcap. Reescritura completa. Branch independiente. |

---

## 📄 Preprint

**arXiv:** [arXiv:2604.04952 \[cs.CR\]](https://arxiv.org/abs/2604.04952)
**Published:** 3 April 2026 · **Draft v19** (ADR-029 Variant A vs B) · MIT license
**Code:** https://github.com/alonsoir/argus

---

## 🎯 Mission

Democratize enterprise-grade cybersecurity for hospitals, schools, and small organizations that cannot afford commercial solutions.

**Philosophy**: *Via Appia Quality* — Systems built like Roman roads, designed to endure.

> *"Un escudo que aprende de su propia sombra."*

---

## 📊 Validated Results

| Metric | Value | Notes |
|---|---|---|
| **F1-score (CTU-13 Neris)** | **0.9985** | Stable across 4 replay runs |
| **Precision** | **0.9969** | |
| **Recall** | **1.0000** | Zero missed attacks (FN=0) |
| **Suricata 6.0.10 F1 (CTU-13 Neris)** | **0.000** | 0 alerts — ET Open rules retired for 2011 threats |
| **Zeek 8.1.2 F1 (CTU-13 Neris, default)** | **0.042** | Precision=1.000, 14 TP (SSL::Invalid_Server_Cert) |
| **XGBoost Precision (CIC-IDS-2017 val)** | **0.9945** | In-distribution, threshold=0.8211 |
| **XGBoost Wednesday OOD** | **Documented impossibility** | Structural covariate shift — §8 paper |
| **Inference latency (XGBoost)** | **1.986 µs/sample** | Gate <2µs ✅ |
| **Inference latency (RF)** | **0.24–1.06 µs** | Per-class, embedded C++20 |
| **Throughput ceiling (virtualized)** | **~33–38 Mbps** | VirtualBox NIC limit, not pipeline |
| **Stress test** | **2,374,845 packets — 0 drops** | 100 Mbps requested, loop=3 |
| **RAM (full pipeline)** | **~1.28 GB** | Stable under load |
| **BSR — Dev VM** | **719 pkgs / 5.9 GB** | gcc, g++, clang, cmake present |
| **BSR — Hardened VM** | **304 pkgs / 1.3 GB** | NONE (check-prod-no-compiler: OK) ✅ |
| **AppArmor profiles** | **6/6 enforce** | cap_bpf (Linux ≥5.8), no cap_sys_admin |
| **Falco rules** | **11 aRGus-specific** | modern_ebpf driver |
| **Variant B tests** | **9/9 PASSED** | DAY 142 — buffer=8MB verificado |
| **ADR-029 Variant A eBPF (VBox)** | **~10 Mbps / 9,178 pps** | DAY 145 — techo virtio SKB mode |
| **ADR-029 Variant B libpcap (VBox)** | **~19 Mbps / 17,614 pps** | DAY 145 — ~2× eBPF en virtio |
| **IRP cycle** | **PASS** | NORMAL→ISOLATED→ROLLBACK→NORMAL DAY 142 |

> **Nota ADR-029 — Failed packets (2,630):** Artefacto fijo del pcap CTU-13 Neris. Frames jumbo que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). Conteo idéntico en los 6 runs — confirma origen en el fichero, no en el pipeline. El sniffer nunca ve esos frames. **No son errores del pipeline.**

---

## 🔒 Security Hardening — ADR-030 Variant A

### Build/Runtime Separation (BSR) — ADR-039

| Environment | Packages | Disk | Compilers |
|---|---|---|---|
| Dev VM | 719 | 5.9 GB | gcc, g++, clang, cmake |
| **Hardened VM** | **304** | **1.3 GB** | **NONE** ✅ |

### Linux Capabilities — no SUID root

| Component | Capabilities |
|---|---|
| sniffer | `cap_net_admin,cap_net_raw,cap_bpf,cap_ipc_lock` |
| firewall-acl-agent | `cap_net_admin` |
| etcd-server | `cap_ipc_lock` (+ LimitMEMLOCK=16M) |
| argus-network-isolate | `cap_net_admin` (AppArmor enforce — DAY 143) |
| ml-detector, rag-ingester, rag-security | none |

### AppArmor — 6 profiles enforce · Falco — 11 aRGus-specific rules

---

## 🔧 Prerequisites

### macOS

```bash
brew install --cask virtualbox
brew install --cask vagrant
xcode-select --install
```

> **Note:** `git clone --recurse-submodules` is required. `third_party/llama.cpp` is a git submodule. Cloning without this flag leaves it empty and `rag-security` builds without LLM support. Use `make submodule-init` to fix an existing clone.

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y make
```

VirtualBox from official repo (apt may be outdated):
```bash
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo gpg --dearmor -o /usr/share/keyrings/oracle-virtualbox.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox.gpg] https://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | sudo tee /etc/apt/sources.list.d/virtualbox.list
sudo apt-get update && sudo apt-get install -y virtualbox-7.0
```

Vagrant:
```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y vagrant
```

### Linux (RHEL/Fedora/CentOS)

```bash
sudo dnf install -y make
```

VirtualBox:
```bash
sudo dnf install -y kernel-devel kernel-headers dkms
sudo dnf config-manager --add-repo https://download.virtualbox.org/virtualbox/rpm/fedora/virtualbox.repo
sudo dnf install -y VirtualBox-7.0
```

Vagrant:
```bash
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf install -y vagrant
```

> **Note:** `git clone --recurse-submodules` is required. `third_party/llama.cpp` is a git submodule. Cloning without this flag leaves it empty and `rag-security` builds without LLM support. Use `make submodule-init` to fix an existing clone.

> **Note (RHEL/CentOS):** VirtualBox requires Secure Boot to be disabled or the kernel module to be signed. On WSL2, VirtualBox is not supported — use a native Linux install.

### Windows 11 (best-effort, not officially supported)

> ⚠️ **aRGus NDR only produces Linux binaries** (x86-64 and ARM64). There are no Windows binaries and none are planned. The pipeline runs inside a Linux VM — Windows is only the host.

Prerequisites:
```powershell
winget install Git.Git
winget install Oracle.VirtualBox
winget install Hashicorp.Vagrant
```

Run all commands from **Git Bash** (not CMD or PowerShell — the Makefile requires bash syntax).

> ⚠️ **Hyper-V conflict:** Windows 11 enables Hyper-V by default for WSL2. VirtualBox 7.0+ has experimental Hyper-V support but with ~30% performance penalty. You must choose one of:
> - Disable Hyper-V (loses WSL2): `bcdedit /set hypervisorlaunchtype off` + reboot
> - Use VirtualBox 7.0+ in Hyper-V mode (slower, less stable)

**Not tested by the maintainer.** If you hit issues on Windows 11, please [open an issue](https://github.com/alonsoir/argus/issues) — we'll help with the resources we have.


---

## 🚀 Quick Start

> ⚠️ **Vagrant is required.** Native Linux bootstrap without Vagrant is not yet implemented ([DEBT-NATIVE-LINUX-BOOTSTRAP-001](docs/KNOWN-DEBTS-v0.6.md)). Running `make` directly on a bare Linux host will fail.

```bash
# STEP 1 — Clone with submodules (mandatory — llama.cpp is a git submodule)
git clone --recurse-submodules https://github.com/alonsoir/argus.git
cd argus

# Already cloned without --recurse-submodules? Fix it:
# make submodule-init
```

> 📦 **TinyLlama model** (`tinyllama-1.1b-chat-v1.0.Q4_0.gguf`, ~700MB) is downloaded
> automatically during `vagrant up`. It is gitignored and never committed to the repo.

```bash
# STEP 2 — Start VM and provision all dependencies (~20-30 min first time)
# Downloads TinyLlama, builds llama.cpp, installs FAISS/ONNX/XGBoost/libsodium
make up && make bootstrap
```

### Workflow diario (REGLA EMECAS)

```bash
vagrant destroy -f && vagrant up && make bootstrap && make test-all
```

> **¿Por qué EMECAS?** El protocolo garantiza reproducibilidad total: cada sesión parte de una VM limpia, claves criptográficas regeneradas, pipeline compilado desde cero y suite de tests completa. Un ❌ en cualquier punto es bloqueante — no se fusiona ni avanza trabajo hasta que `make test-all` termina con exit 0 y `pipeline-status` muestra 6/6 RUNNING. El sniffer puede tardar hasta 4 segundos en estabilizar su sesión tmux tras el arranque; si `pipeline-status` muestra ❌ sniffer inmediatamente después del bootstrap, esperar 5 segundos y repetir `make pipeline-status` antes de escalar.



### Hardened VM (ADR-030 Variant A)

```bash
make hardened-full   # destroy → up → provision → build → deploy → check
```

---

## 🗺️ Roadmap

### ✅ DONE — DAY 146 (9 May 2026) — Suricata Comparative + Deudas 🎉

| Task | Result |
|---|---|
| EMECAS verde | ✅ 4 deudas cerradas |
| Experimento Suricata vs aRGus | ✅ 0 alertas Suricata vs F1=0.9985 aRGus |
| Makefile up/halt-argus/suricata | ✅ Topología dual |
| Paper Draft v20 | ✅ §8.13 + Tabla comparativa empírica |

### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉

| Task | Result |
|---|---|
| EMECAS ritual | ✅ 65/65 PASSED |
| PCAP relay x86 eBPF (Variant A) | ✅ ~10 Mbps, 320,524 pkts, exit=0 |
| PCAP relay x86 libpcap (Variant B) | ✅ ~19 Mbps, 320,524 pkts, exit=0 |
| Merge feature/variant-b-libpcap → main | ✅ v0.7.0-variant-b |
| Bootstrap múltiple (x86-ebpf / x86-libpcap) | ✅ Makefile actualizado |
| Paper Draft v19 | ✅ §6 ADR-029, §10.9, §11.17, §12 |

### ✅ DONE — DAY 143-144 — IRP completo + ODR gate 🎉
- [x] DEBT-IRP-NFTABLES-001 CERRADA — IRP completo, AppArmor 7/7 enforce, 12/12 tests
- [x] DEBT-IRP-SIGCHLD-001 CERRADA — SA_NOCLDWAIT
- [x] DEBT-IRP-AUTOISO-FALSE-001 CERRADA — isolate.json única fuente de verdad
- [x] DEBT-IRP-BACKUP-DIR-001 CERRADA — /run/argus/irp/
- [x] Gate ODR production PASSED — 3 violations reales corregidas bajo -flto

### ✅ DONE — DAY 138-142 — ADR-029 Variant B pipeline 🎉
- [x] DEBT-CAPTURE-BACKEND-ISP-001 CERRADA — `CaptureBackend` 5 métodos puros
- [x] DEBT-VARIANT-B-PCAP-IMPL-001 CERRADA — pipeline pcap → proto → LZ4 → ChaCha20 → ZMQ
- [x] DEBT-VARIANT-B-BUFFER-SIZE-001 CERRADA — pcap_create()+pcap_set_buffer_size()
- [x] DEBT-VARIANT-B-MUTEX-001 CERRADA (Nivel 1) — exclusión mutua via tmux
- [x] Suite 9 tests Variant B — 9/9 PASSED

### ✅ DONE — DAY 137 (30 Apr 2026) — feature/variant-b-libpcap 🎉
- [x] EMECAS dev + EMECAS hardened PASSED
- [x] capture_backend.hpp · ebpf_backend.hpp/cpp · pcap_backend.hpp/cpp
- [x] main_libpcap.cpp — Variant B sin #ifdef
- [x] sniffer-libpcap compilable y arranca limpio

### ✅ DONE — DAY 135-136: v0.6.0 🎉
- [x] make hardened-full EMECAS PASSED
- [x] feature/adr030-variant-a → main MERGEADO
- [x] Tag v0.6.0-hardened-variant-a publicado
- [x] arXiv replace v15 → v18 ENVIADO

### ✅ DONE — DAY 133-134: ADR-030 + ADR-040 + ADR-041 🎉
- [x] AppArmor 6/6 enforce · Falco 10 reglas · cap_bpf · Paper v18
- [x] ADR-040 ML Retraining Contract (8/8, 17 enmiendas)
- [x] ADR-041 Hardware Acceptance Metrics FEDER (8/8)
- [x] Pipeline E2E hardened · check-prod-all PASSED

### 🔜 NEXT — DAY 146+

| Priority | Task |
|---|---|
| 🔴 P0-bloqueante | `suricata -r neris.pcap` offline — verificar 0 alertas (blinda comparativa ante revisores) |
| 🔴 P0-paper | Refinar §8.14: "measurement layer" vs "classification layer" (framing Consejo DAY 147) |
| 🔴 P0-paper | §10 Future Work: añadir Zeek Phase 2 (Intel framework, detect-botnets.zeek) |
| 🟡 P1 | DEBT-IRP-FLOAT-TYPES-001 — unificar tipos score float/double pre-FEDER |
| 🟡 P1 | Tabla §8.2 comparison: añadir fila Zeek 8.1.2 |
| 🟡 P1 | Decisión arXiv replace v22 (tras verificación suricata -r) |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |

### 🔜 THEN — PHASE 5: Adversarial Capture-Retrain Loop

- DEBT-PENTESTER-LOOP-001 — ACRL completo
- BACKLOG-FEDER-001 — presentación Andrés Caro Lindo
- aRGus-production ARM64
- aRGus-seL4 research branch (post-FEDER, equipo especializado)

---

## 🗺️ Milestones

- ✅ DAY 111: **arXiv:2604.04952 PUBLICADO** 🎉
- ✅ DAY 113: **ADR-025 MERGED — v0.3.0-plugin-integrity** 🎉
- ✅ DAY 118: **PHASE 3 COMPLETADA — v0.4.0** 🎉
- ✅ DAY 122: **PHASE 4 COMPLETADA — v0.5.0-preproduction** 🎉
- ✅ DAY 124: **ADR-037 MERGED — v0.5.1-hardened** 🎉
- ✅ DAY 129: **CWE-78 CERRADO — execv() sin shell** 🎉
- ✅ DAY 130: **REGLA EMECAS · libFuzzer 2.4M runs** 🎉
- ✅ DAY 133: **ADR-030 Variant A — cap_bpf · AppArmor 6/6 · Falco 10 reglas** 🎉
- ✅ DAY 134: **ADR-040 (8/8, 17 enmiendas) · ADR-041 FEDER HW Metrics (8/8)** 🎉
- ✅ DAY 136: **v0.6.0-hardened-variant-a · merge main** 🎉
- ✅ DAY 137: **feature/variant-b-libpcap · sniffer-libpcap compilable · KISS** 🎉
- ✅ DAY 138: **ISP cerrado · pipeline Variant B completo · 8/8 tests · Consejo 8/8** 🎉
- ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio** 🎉
- ✅ DAY 141: **DEBT-VARIANT-B-CONFIG-001 · sniffer-libpcap.json · emails FEDER** 🎉
- ✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉
- ✅ DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA — IRP completo · AppArmor 7/7 · 12 tests** 🎉
- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 65/65 tests** 🎉
- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio · Bootstrap múltiple · Paper v19 · v0.7.0-variant-b** 🎉
- ✅ DAY 146: **Experimento Suricata comparativo · 0 alertas ET Open vs F1=0.9985 aRGus · Paper v20 §8.13 · v0.7.1-day146** 🎉
- ✅ DAY 147: **Experimento tres paradigmas (Suricata+Zeek+aRGus) · Paper v22 §8.14 · HTTP C2 hallazgo · weird.log behavioral profile · v0.7.1-day147** 🎉
- ✅ DAY 147: **ADR-0043 v4 ACEPTADO** — Memoria Episódica Distribuida, Consejo 8/8, 4 versiones 🎉
- 🔜 DAY 146+: **DEBT-IRP-TMPFILES-001 · DEBT-IRP-IPSET-TMP-001 · experiment-comparative · ARM64 scope**

---

## 🧠 Consejo de Sabios — Multi-Model Peer Review

**Claude** (Anthropic) · **Grok** (xAI) · **ChatGPT** (OpenAI) · **DeepSeek** · **Qwen** (Alibaba) · **Gemini** (Google) · **Kimi** (Moonshot) · **Mistral**

Metodología: desacuerdo estructurado. Documentado en §6 del preprint.

---

## Hardened Deployment (ADR-030 Variant A)

```bash
make hardened-full          # EMECAS sagrado — destroy → up → provision → build → deploy → check
make hardened-redeploy      # iteración rápida sin destroy
make prod-deploy-seeds      # deploy seeds explícito (nunca en EMECAS)
make check-prod-all         # 5/5 gates: BSR + AppArmor + cap_bpf + permissions + Falco
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE)

**Via Appia Quality** 🏛️ — *Built to last decades.*