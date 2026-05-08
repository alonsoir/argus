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
[![Hardened](https://img.shields.io/badge/Security-v0.6.0--hardened__variant__a-brightgreen)]()
[![PRE-PRODUCTION](https://img.shields.io/badge/Status-PRE--PRODUCTION-orange)]()
[![Crypto](https://img.shields.io/badge/Crypto-HKDF_SHA256+ChaCha20_Poly1305-orange)]()
[![arXiv](https://img.shields.io/badge/arXiv-2604.04952_cs.CR-red)](https://arxiv.org/abs/2604.04952)
[![TDH](https://img.shields.io/badge/Methodology-Test_Driven_Hardening-purple)](https://github.com/alonsoir/test-driven-hardening)
[![IRP](https://img.shields.io/badge/IRP-argus--network--isolate_ADR--042-red)]()

📜 Living contracts: [Protobuf schema](docs/contracts/Protobuf%20contracts.md) · [Pipeline configs](docs/contracts/JSON%20contracts.md) · [RAG API](docs/contracts/Rag%20security%20commands.md)

---

✅ `main` is tagged `v0.7.0-variant-b`. Branch activa: `main` — ADR-029 Variant A vs B x86 completado (DAY 145). Paper v19 publicado.
**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**

---

## Estado actual — DAY 145 (2026-05-08)

**Tag activo:** `v0.7.0-variant-b` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v19 (ADR-029 Variant A vs B)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026

### Pipeline
- 6/6 componentes RUNNING — validado EMECAS DAY 142 ✅
- `make test-all`: ALL TESTS COMPLETE (65/65 PASSED — 0 FAILED) ✅
- `make PROFILE=production all`: Gate ODR — ALL COMPONENTS BUILT ✅
- `make argus-network-isolate-test`: dry-run PASSED ✅

### Hitos DAY 144 🎉
- **Gate ODR production SUPERADO** — `make PROFILE=production all` limpio. 3 ODR violations reales detectadas y corregidas (anonymous namespace, protobuf stale, -UNDEBUG en tests).
- **DEBT-IRP-SIGCHLD-001 CERRADA** — `SA_NOCLDWAIT` en `setup_signal_handlers()`. `SigchldTest.NoZombiesAfterNForks` PASSED.
- **DEBT-IRP-AUTOISO-FALSE-001 CERRADA** — `isolate.json` única fuente de verdad. Campo obligatorio, fallo ruidoso si ausente. `parse_irp()` public. 5 tests nuevos PASSED.
- **DEBT-IRP-BACKUP-DIR-001 CERRADA** — `/tmp` → `/run/argus/irp/`. AppArmor + provision.sh actualizados. Dry-run PASSED.
- **DEBT-COMPILER-WARNINGS-CLEANUP-001 PARCIALMENTE CERRADA** — ODR violations bajo LTO.

### Hitos DAY 143 🎉
- **DEBT-IRP-NFTABLES-001 CERRADA** — IRP completo: config → disparo → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests.

### Hitos DAY 142 🎉
- **DEBT-VARIANT-B-BUFFER-SIZE-001 CERRADA** — commit `7c4dba58`. `pcap_create()+pcap_set_buffer_size()+pcap_activate()`. Buffer configurable en ARM64/RPi. `CaptureBackend` interfaz actualizada.
- **DEBT-VARIANT-B-MUTEX-001 CERRADA (Nivel 1)** — commit `9458a90d`. `scripts/check-sniffer-mutex.sh` via sesiones tmux. `sniffer-start` y nuevo `sniffer-libpcap-start` verifican exclusión mutua. Verificado: conflicto detectado → exit 1.
- **DEBT-IRP-NFTABLES-001 sesiones 1/3 y 2/3** — commits `6480e234` + `e8928612`. `argus-network-isolate` C++20 con pasos 1-6 completos. Ciclo NORMAL→ISOLATED→ROLLBACK→NORMAL verificado. Timer systemd-run 300s operativo. Forense JSONL.
- **Reproducibilidad EMECAS** — commit `e3f5f9c4`. Vagrantfile + provision.sh + Makefile garantizan que `vagrant destroy && up` reproduzca todo el trabajo.
- **Consejo 8/8 DAY 142** — 4 preguntas IRP, veredictos unánimes: auto_isolate por defecto, fork()+execv(), AppArmor enforce, criterio multi-señal.

### Deuda técnica abierta

| Deuda | Prioridad | Target |
|-------|-----------|--------|
| ~~DEBT-IRP-NFTABLES-001~~ | ✅ CERRADA | DAY 143 |
| ~~DEBT-IRP-SIGCHLD-001~~ | ✅ CERRADA | DAY 144 |
| ~~DEBT-IRP-AUTOISO-FALSE-001~~ | ✅ CERRADA | DAY 144 |
| ~~DEBT-IRP-BACKUP-DIR-001~~ | ✅ CERRADA | DAY 144 |
| DEBT-IRP-TMPFILES-001 | 🟡 P1 | post-merge (tmpfiles.d reboot) |
| DEBT-IRP-IPSET-TMP-001 | 🟡 P1 | post-merge (ipset_wrapper /tmp) |
| DEBT-EMECAS-VERIFICATION-001 | 🟢 P2 | post-merge (README devs) |
| DEBT-IRP-FLOAT-TYPES-001 | 🟡 P1 | pre-FEDER (tipos score) |
| DEBT-IRP-PROB-CONJUNTA-001 | 🟡 P1 | post-FEDER (señal conjunta) |
| DEBT-ETCD-HA-QUORUM-001 | 🔴 P0 | post-FEDER (OBLIGATORIO) |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Alta | post-merge |
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | 🔴 Alta | pre-FEDER |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | 🔴 Alta | pre-FEDER |
| DEBT-MUTEX-ROBUST-001 | 🟡 P1 | post-FEDER |
| DEBT-IRP-MULTI-SIGNAL-001 | 🟡 P1 | post-FEDER |
| DEBT-IRP-LAST-KNOWN-GOOD-001 | 🟢 Baja | post-FEDER |
| DEBT-SEEDS-SECURE-TRANSFER-001 | 🔴 Alta | post-FEDER |
| DEBT-ADR040-001..012 | ⏳ | post-FEDER |
| DEBT-ADR041-001..006 | ⏳ | pre-FEDER |

### Próxima frontera — DAY 143
1. EMECAS obligatorio + verificar reproducibilidad argus-network-isolate
2. `DEBT-IRP-NFTABLES-001` sesión 3/3 — integración `firewall-acl-agent` + AppArmor

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
**Published:** 3 April 2026 · **Draft v18** (Cornell procesando) · MIT license
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

> **Nota ADR-029 — Failed packets (2,630):** Artefacto fijo del pcap CTU-13 Neris. Son frames jumbo que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). El conteo es idéntico en los 6 runs (3 velocidades × 2 variantes) — confirma origen en la estructura del fichero, no en el pipeline. El rechazo ocurre en el cliente antes de llegar al defender; el sniffer nunca ve esos frames. **No son errores del pipeline ni del sniffer.**

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

## 🛡️ Incident Response Protocol — ADR-042

`argus-network-isolate` — binario C++20 independiente que aísla una interfaz de red via nftables en 6 pasos transaccionales:

```
1. Snapshot selectivo del ruleset actual (solo tabla argus_isolate)
2. Generar reglas de aislamiento con whitelist IP/port configurable
3. Validar en seco: nft -c -f (aborta sin tocar nada si falla)
4. Aplicar atómico: nft -f (una sola operación)
5. Timer systemd-run: rollback automático en 300s si nadie confirma
6. Rollback: elimina tabla argus_isolate, restaura estado previo
```

**Disparado automáticamente** por `firewall-acl-agent` cuando:
`threat_score >= 0.95 AND event_type IN (ransomware, lateral_movement, c2_beacon)`

**Por defecto:** `auto_isolate: false` — habilitar explícitamente tras configurar whitelist. (DEBT-IRP-AUTOISO-FALSE-001)

```bash
# Verificar estado
argus-network-isolate status

# Dry-run (pasos 1-3, sin aplicar)
argus-network-isolate isolate --interface eth1 --dry-run

# Rollback manual
argus-network-isolate rollback --backup /tmp/argus-backup-<ts>.nft
```

---

## 🔧 Prerequisites

### macOS

```bash
brew install --cask virtualbox
brew install --cask vagrant
xcode-select --install
```

> **Note:** `git clone --recurse-submodules` is required. `third_party/llama.cpp` is a git submodule.

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y make
```

VirtualBox from official repo:
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
sudo dnf config-manager --add-repo https://download.virtualbox.org/virtualbox/rpm/fedora/virtualbox.repo
sudo dnf install -y VirtualBox-7.0
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf install -y vagrant
```

### Windows 11 (best-effort, not officially supported)

```powershell
winget install Git.Git
winget install Oracle.VirtualBox
winget install Hashicorp.Vagrant
```

Run all commands from **Git Bash**. Hyper-V conflict: VirtualBox 7.0+ has experimental Hyper-V support but with ~30% performance penalty.

---

## 🚀 Quick Start

```bash
# STEP 1 — Clone with submodules (mandatory)
git clone --recurse-submodules https://github.com/alonsoir/argus.git
cd argus

# STEP 2 — Start VM and provision (~20-30 min first time)
make up && make bootstrap
```

### Workflow diario (REGLA EMECAS)

```bash
vagrant destroy -f && vagrant up && make bootstrap && make test-all
```

### Build Profiles

| Profile | Flags | Cuándo usarlo |
|---------|-------|---------------|
| `debug` (**default**) | `-g -O0` | Desarrollo diario |
| `production` | `-O3 -flto -march=native -DNDEBUG` | ODR verification, capacity benchmarks |
| `tsan` | `-fsanitize=thread -g -O1` | Race conditions |
| `asan` | `-fsanitize=address,undefined -g -O1` | Memory errors |

```bash
make all                        # debug (default)
make PROFILE=production all     # ODR check via LTO
make PROFILE=tsan all           # ThreadSanitizer
make PROFILE=asan all           # AddressSanitizer + UBSan
```

### IRP Commands

```bash
make argus-network-isolate-build   # compilar
make argus-network-isolate-test    # dry-run en eth1
```

### Hardened VM (ADR-030 Variant A)

```bash
make hardened-full   # destroy → up → provision → build → deploy → check
```

---

## 🗺️ Roadmap

### ✅ DONE — DAY 142 (5 May 2026) — IRP + Variant B completa 🎉
- [x] DEBT-VARIANT-B-BUFFER-SIZE-001 CERRADA — `pcap_create()+pcap_set_buffer_size()` — buffer=8MB verificado
- [x] DEBT-VARIANT-B-MUTEX-001 CERRADA (Nivel 1) — `scripts/check-sniffer-mutex.sh` via tmux
- [x] DEBT-IRP-NFTABLES-001 sesiones 1/3 y 2/3 — pasos 1-6 implementados, ciclo completo verificado
- [x] argus-network-isolate: timer systemd-run 300s, forense JSONL, rollback robusto
- [x] Reproducibilidad EMECAS: Vagrantfile + provision.sh + Makefile garantizan reproducción
- [x] Consejo 8/8 DAY 142 — auto_isolate por defecto, fork()+execv(), AppArmor enforce

### ✅ DONE — DAY 141 (4 May 2026)
- [x] DEBT-VARIANT-B-CONFIG-001 — sniffer-libpcap.json propio, 9/9 tests
- [x] DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 — contrato lifetime
- [x] Bug Makefile seed-client-build

### ✅ DONE — DAY 140 (Apr 2026) — 192→0 warnings 🎉
- [x] DEBT-COMPILER-WARNINGS-CLEANUP-001 — `-Werror` activo, ODR limpio

### ✅ DONE — DAY 138 (1 May 2026) — ADR-029 Variant B pipeline 🎉
- [x] DEBT-CAPTURE-BACKEND-ISP-001 — `CaptureBackend` 5 métodos puros
- [x] DEBT-VARIANT-B-PCAP-IMPL-001 — pipeline pcap → proto → LZ4 → ChaCha20 → ZMQ
- [x] Suite 8 tests Variant B — 8/8 PASSED

### ✅ DONE — DAY 135-136: v0.6.0 🎉
- [x] feature/adr030-variant-a → main MERGEADO
- [x] Tag v0.6.0-hardened-variant-a publicado

### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉

| Task | Result |
|---|---|
| EMECAS ritual | ✅ 65/65 PASSED |
| PCAP relay x86 eBPF (Variant A) | ✅ ~10 Mbps, 320,524 pkts, exit=0 |
| PCAP relay x86 libpcap (Variant B) | ✅ ~19 Mbps, 320,524 pkts, exit=0 |
| Merge `feature/variant-b-libpcap` → main | ✅ v0.7.0-variant-b |
| Bootstrap múltiple (x86-ebpf / x86-libpcap) | ✅ Makefile actualizado |
| Relay targets con resumen inline + rutas log | ✅ Sin mensajes confusos |
| Paper Draft v19 | ✅ §6 ADR-029, §10.9, §11.17, §12 |

### 🔜 NEXT — DAY 146+

| Priority | Task |
|---|---|
| 🟡 P1 | DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot |
| 🟡 P1 | DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp |
| 🟡 P1 | Diseño `experiment-comparative` (aRGus + Suricata + Zeek como cooperadores) |
| 🟡 P1 | Abrir `feature/adr029-variant-c-arm64` scope definido |
| 🟢 P2 | DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs |

### 🔜 THEN — PHASE 5: Adversarial Capture-Retrain Loop

- DEBT-PENTESTER-LOOP-001 — ACRL completo
- BACKLOG-FEDER-001 — presentación Andrés Caro Lindo
- aRGus-production ARM64
- DEBT-ETCD-HA-QUORUM-001 — etcd en HA con quorum (post-FEDER, OBLIGATORIO)
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
- ✅ DAY 133: **ADR-030 Variant A — cap_bpf · AppArmor 6/6 · Falco** 🎉
- ✅ DAY 134: **ADR-040 (8/8) · ADR-041 FEDER HW Metrics (8/8)** 🎉
- ✅ DAY 136: **v0.6.0-hardened-variant-a · merge main** 🎉
- ✅ DAY 138: **ISP cerrado · pipeline Variant B completo · 8/8 tests** 🎉
- ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio** 🎉
- ✅ DAY 141: **DEBT-VARIANT-B-CONFIG-001 · sniffer-libpcap.json · emails FEDER** 🎉
- ✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉
- ✅ DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA — IRP completo · AppArmor 7/7 · 12 tests** 🎉
- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 3 ODR violations corregidas · 65/65 tests** 🎉
- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio (inversión esperada en bare metal) · Bootstrap múltiple · Paper v19 · Merge → main · v0.7.0-variant-b** 🎉
- 🔜 DAY 146+: **DEBT-IRP-TMPFILES-001 + DEBT-IRP-IPSET-TMP-001 · experiment-comparative (aRGus+Suricata+Zeek) · feature/adr029-variant-c-arm64 scope**

---

## 🧠 Consejo de Sabios — Multi-Model Peer Review

**Claude** (Anthropic) · **Grok** (xAI) · **ChatGPT** (OpenAI) · **DeepSeek** · **Qwen** (Alibaba) · **Gemini** (Google) · **Kimi** (Moonshot) · **Mistral**

Metodología: desacuerdo estructurado. Documentado en §6 del preprint arXiv:2604.04952.

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