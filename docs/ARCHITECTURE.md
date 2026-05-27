# ML Defender (aRGus NDR) — Architecture

> **Version:** 7.0.0 — DAY 100 (28 marzo 2026)
> **Authors:** Alonso Isidoro Román, with the Consejo de Sabios (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai)
> **License:** Open Source — see `LICENSE`
> **Status:** Active research system — arXiv preprint in preparation

---

## Table of Contents

1. [Vision and Motivation](#1-vision-and-motivation)
2. [Target Audience](#2-target-audience)
3. [System Overview](#3-system-overview)
4. [Pipeline Components](#4-pipeline-components)
5. [Data Flow](#5-data-flow)
6. [ASCII Pipeline Diagram](#6-ascii-pipeline-diagram)
7. [Technology Stack](#7-technology-stack)
8. [Architectural Decision Records](#8-architectural-decision-records)
9. [Deployment](#9-deployment)
10. [Security Design](#10-security-design)
11. [ML Subsystem](#11-ml-subsystem)
12. [Performance Envelope](#12-performance-envelope)
13. [Known Limitations](#13-known-limitations)
14. [Roadmap](#14-roadmap)

---

## 1. Vision and Motivation

ML Defender (internal codename **aRGus NDR**) is an open-source, network-level Intrusion Detection System (IDS) / Network Detection and Response (NDR) system written in **C++20**, designed for **resource-constrained organizations**: hospitals, schools, municipal governments, and small businesses.

These organizations are the most frequent victims of ransomware (WannaCry, NotPetya, Conti, LockBit) and are simultaneously the least equipped to defend themselves. Commercial NDR solutions require enterprise licensing, dedicated security staff, and cloud connectivity — all of which are out of reach for a rural hospital or a primary school.

ML Defender is built on a core philosophy:

> **"Via Appia Quality"** — build for permanence. Systems that will still work in 10 years without a support contract.

The system runs entirely **on-premises**, with no cloud dependency, no telemetry, and no external API calls in its critical path. It is designed to be deployed by a single sysadmin with no security background, yet provide detection capabilities comparable to commercial tools.

---

## 2. Target Audience

**For this document:**
- External contributors evaluating the codebase
- Security researchers validating the detection methodology
- Potential adopters assessing deployment feasibility
- Academic reviewers of the companion arXiv preprint

**For the system itself:**
- IT staff at resource-constrained organizations
- Network administrators wanting passive, zero-impact monitoring
- SOC teams at small-to-medium organizations needing an affordable NDR layer

---

## 3. System Overview

ML Defender operates as a **passive network monitor** combined with an **active response layer**. It captures packets at the kernel level via eBPF/XDP, extracts statistical flow features, classifies traffic using an embedded Random Forest model (ONNX Runtime), and — upon detection of malicious flows — applies firewall rules automatically.

A secondary **Retrieval-Augmented Generation (RAG)** subsystem indexes historical detection events and makes them queryable via a confined local LLM, enabling forensic analysis without external connectivity.

### Core properties

| Property | Value |
|---|---|
| Language | C++20 |
| Detection latency | < 1 ms (Fast Detector, Path A) |
| ML inference latency | < 5 ms (ONNX Runtime, Path B) |
| Encryption | ChaCha20-Poly1305 IETF (all inter-component messages) |
| Key derivation | HKDF-SHA256 via libsodium 1.0.19 |
| Integrity | HMAC-SHA256 per message and per CSV row |
| Compression | LZ4 (inter-component transport) |
| Coordination | etcd v3 (service discovery, configuration) |
| Messaging | ZeroMQ (PUSH/PULL topology) |
| Test coverage | 24/24 CTest suites ✅ |
| Fail-closed | set_terminate() + fail-closed EventLoader/RAGLogger |

---

## 4. Pipeline Components

The system consists of **6 active components**, each running as an independent process. They communicate exclusively via encrypted ZeroMQ channels, with etcd as the service discovery authority.

---

### 4.1 `etcd-server`

**Role:** Configuration authority and service discovery broker.

All components register their ZeroMQ endpoint addresses with etcd on startup. No component has a hardcoded peer address — all addresses are resolved dynamically from etcd at connection time.

**Key responsibilities:**
- Publish resource paths (ZeroMQ endpoints) for all other components
- Store and distribute the shared HMAC key (with rotation support — ADR-004)
- Provide a single source of truth for pipeline configuration

**ADR reference:** ADR-005, ADR-004

---

### 4.2 `sniffer`

**Role:** Kernel-space packet capture and flow feature extraction.

The sniffer attaches an **eBPF/XDP** program to the monitored network interface and captures packets at the earliest possible point in the Linux network stack — before the kernel's networking subsystem processes them.

From raw packets, the sniffer assembles **network flows** (5-tuple) and computes a **127-column feature vector** per flow over a configurable time window (default: 10 seconds).

**Output:** Protobuf-serialized `FlowRecord` messages, encrypted with `CryptoTransport` (HKDF context: `CTX_SNIFFER_TO_ML`), LZ4 compressed, published to `ml-detector` via ZeroMQ PUSH.

**ADR reference:** ADR-006 (DEBT-FD-001), ADR-009, ADR-013

---

### 4.3 `ml-detector`

**Role:** Dual-path classification engine.

#### Path A — Fast Detector (`FastDetector::is_suspicious()`)
Handcrafted rule engine with compiled-in thresholds. Operates in **< 1 ms**.

> ⚠️ **DEBT-FD-001:** Path A currently ignores `sniffer.json` thresholds (ADR-006, PHASE 2).

#### Path B — ML Detector (ONNX Runtime)
Random Forest classifier trained on CTU-13 Neris. 127-column feature vector. **F1 = 0.9985**.

**Validated performance (CTU-13 Neris, DAY 86):**
| Metric | Value |
|---|---|
| F1 Score | 0.9985 |
| Recall | 1.0000 |
| False Positive Rate | 6.61% |
| True Positives | 646 |

**Scoring (ADR-007):**
- OR logic → alert
- AND logic → block (prevents ML score poisoning)

**Output:** Alert messages and block commands to `firewall-acl-agent` (context: `CTX_ML_TO_FIREWALL`); flow records to daily CSV consumed by `rag-ingester` (context: `CTX_ML_TO_RAG`).

**ADR reference:** ADR-007, ADR-003, ADR-011, ADR-013

---

### 4.4 `firewall-acl-agent`

**Role:** Automated network response layer.

Receives block commands from `ml-detector` via `CryptoTransport` (context: `CTX_ML_TO_FIREWALL`) and applies **iptables** rules. Implements grace period and cooldown. Never blocks without ml-detector command.

**ADR reference:** ADR-007

---

### 4.5 `rag-ingester`

**Role:** Historical event indexer and FAISS index builder.

Consumes ml-detector daily CSV and firewall audit CSV. Verifies HMAC-SHA256 per row. Builds FAISS indices and SQLite MetadataDB (14-column schema, including `trace_id`).

**ADR reference:** ADR-002, ADR-008

---

### 4.6 `rag-security`

**Role:** Local RAG query interface — confined LLM for forensic analysis.

TinyLlama running entirely locally. Read-only. Strictly confined via skills registry (ADR-010). No internet access, no external API calls.

**ADR reference:** ADR-010, ADR-002

---

## 5. Data Flow

```
[Network Interface]
        │
        ▼ eBPF/XDP (kernel space)
[sniffer]
   • 127-column FlowRecord extraction
   • 10s aggregation window
   • Protobuf serialization
        │ ZeroMQ PUSH
        │ CryptoTransport(CTX_SNIFFER_TO_ML)
        │ HKDF-SHA256 + ChaCha20-Poly1305 + LZ4
        ▼
[ml-detector]
   • Path A: FastDetector (< 1ms, hardcoded rules)
   • Path B: ONNX Runtime RandomForest (< 5ms)
   • Consensus scoring (ADR-007)
   • trace_id generation per flow
        │                         │
        │ CryptoTransport          │ Daily CSV (HMAC per row)
        │ (CTX_ML_TO_FIREWALL)     │ CryptoTransport(CTX_ML_TO_RAG)
        ▼                         ▼
[firewall-acl-agent]         [rag-ingester]
   • iptables rules              • FAISS index build
   • Audit CSV                   • SQLite MetadataDB
                                      │
                                      ▼
                                [rag-security]
                                • FAISS similarity search
                                • TinyLlama (local, confined)
                                • Skills registry (ADR-010)

[etcd-server] ──────────────► all components
   • ZeroMQ endpoint registry
   • HMAC key distribution
   • Pipeline configuration
```

---

## 6. ASCII Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ML DEFENDER (aRGus NDR)                          │
│                      Network Detection and Response                      │
└─────────────────────────────────────────────────────────────────────────┘

         ┌──────────────┐
         │  etcd-server │  ◄── Configuration authority
         │   (port 2379)│      Service discovery
         └──────┬───────┘      HMAC key distribution
                │ service discovery (all components)
                │
 ┌──────────────┼──────────────────────────────────────────────┐
 │              │                                              │
 ▼              ▼              ▼              ▼                ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ sniffer │ │ml-detect │ │ firewall │ │rag-ingest│ │ rag-security │
│         │ │          │ │-acl-agent│ │          │ │              │
│ eBPF/   │ │ Path A:  │ │          │ │ FAISS    │ │ TinyLlama    │
│ XDP     │─►FastDetect│─► iptables │ │ SQLite   │ │ (local only) │
│         │ │ Path B:  │ │ rules    │ │ MetadataDB│ │ Skills API  │
│ 127-col │ │ ONNX RF  │ │          │ │          │─► query iface │
│ features│ │          │ │          │ │          │ │              │
└─────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘
     │            │                         ▲
     │ ZeroMQ     │ ZeroMQ                  │
     │ PUSH       │ PUSH                    │
     │ HKDF+      │ CSV                     │
     │ ChaCha20   │ + HMAC                  │
     │ + LZ4      │                         │
     └────────────┘─────────────────────────┘

Legend:
  ─► ZeroMQ encrypted channel (HKDF-SHA256 + ChaCha20-Poly1305 + LZ4)
  ──► etcd service discovery (gRPC)
  CSV files protected with HMAC-SHA256 per row
  All channels use symmetric HKDF contexts (contexts.hpp)
```

---

## 7. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | C++20 | Sub-microsecond latency; zero GC pauses; embedded target compatibility |
| Packet capture | eBPF/XDP | Kernel-bypass; zero-copy; earliest hook point in Linux network stack |
| Messaging | ZeroMQ 4.x | Battle-tested; PUSH/PULL topology; cross-platform |
| Serialization | Protocol Buffers (proto3) | Schema-enforced; compact binary; forward-compatible |
| Encryption | ChaCha20-Poly1305 IETF (libsodium 1.0.19) | AEAD; constant-time; no hardware AES dependency |
| Key derivation | HKDF-SHA256 (libsodium 1.0.19) | RFC 5869; seed → channel key, never direct use |
| Integrity | HMAC-SHA256 | Per-message and per-CSV-row audit trail |
| Compression | LZ4 | Fastest real-time compression; applied before encryption |
| Coordination | etcd v3 | Distributed KV with watch semantics; gRPC transport |
| ML runtime | ONNX Runtime | Vendor-neutral; supports RandomForest, future neural models |
| Vector search | FAISS (Facebook AI) | Approximate nearest-neighbor at scale; CPU-only deployment |
| Metadata | SQLite 3 | Zero-config; embedded; ACID; 14-column MetadataDB schema |
| LLM | TinyLlama (local) | Fully offline; < 2GB RAM; confined via skills registry |
| Build system | CMake + Conan 2 | Reproducible; cross-platform; `NO_DEFAULT_PATH` for libsodium |
| Test framework | CTest + custom harnesses | 24/24 passing; crypto, HMAC, ML, RAG, trace_id, INTEG suites |
| VM / CI | Vagrant + VirtualBox | Multi-VM lab simulation; repeatable dataset replay |
| CI (static) | GitHub Actions ubuntu-latest | JSON validation, CMakeLists, ADRs, contexts.hpp, set_terminate |

---

## 8. Architectural Decision Records

All major architectural decisions are documented in `docs/adr/`.

| ADR | Title | Status | Impact |
|---|---|---|---|
| ADR-001 | Deployment stack (Vagrant, Docker, bare-metal) | ACCEPTED | Deployment model |
| ADR-002 | Multi-engine provenance situational intelligence | ACCEPTED | RAG architecture |
| ADR-003 | ML autonomous evolution | ACCEPTED | Retraining pipeline |
| ADR-004 | HMAC key rotation with cooldown windows | ACCEPTED | Security — key management |
| ADR-005 | etcd client restoration | ACCEPTED | Resilience |
| ADR-006 | Fast Detector hardcoded thresholds (DEBT-FD-001) | ACCEPTED (debt) | Path A architecture |
| ADR-007 | AND-consensus scoring for firewall blocks | ACCEPTED | Detection logic |
| ADR-008 | Flow graphs and forensic retraining | ACCEPTED | ML evolution |
| ADR-009 | Suspicious datagram capture and correlation | ACCEPTED | Feature extraction |
| ADR-010 | Confined LLM with skills registry (rag-security) | ACCEPTED | LLM safety |
| ADR-011 | Log unification across 6 components | ACCEPTED | Observability |
| ADR-012 | Plugin loader architecture | PROPOSED | Extensibility |
| ADR-013 | Seed distribution and component authentication | ACCEPTED | Crypto chain |
| ADR-014 | Fuzzing strategy | ACCEPTED | Testing |
| ADR-015 | eBPF program integrity verification | PROPOSED (P1) | Kernel security |
| ADR-016 | eBPF runtime kernel telemetry (7th component) | PROPOSED (P2) | Observability |
| ADR-017 | Plugin interface hierarchy | ACCEPTED | Extensibility |
| ADR-018 | eBPF kernel plugin loader | ACCEPTED | Kernel plugins |
| ADR-019 | OS hardening and secure deployment | ACCEPTED | Deployment security |
| ADR-020 | Crypto and compression mandatory (no flags) | ACCEPTED | Transport contract |
| ADR-021 | Deployment topology SSOT + seed families | ACCEPTED (FASE 3) | Distributed deployment |
| ADR-022 | Threat model + Opción 2 discarded | ACCEPTED | Security model |

> **For contributors:** Before implementing any feature that touches detection logic, read ADR-007. Before modifying the RAG subsystem, read ADR-010. Before touching crypto, read ADR-013 and ADR-022. For all new ADRs, use the template in `docs/adr/`.

---

## 9. Deployment

### 9.1 Experimental — Vagrant Single-VM Lab

Used for all dataset replay experiments, stress testing, and CI validation.

```bash
cd /path/to/argus
vagrant up
vagrant ssh -c 'cd /vagrant && make test'
# → 24/24 ✅
```

**Provisioning (required before pipeline start):**
```bash
vagrant ssh -c 'sudo bash /vagrant/tools/provision.sh full'
# Generates Ed25519 keypairs + 32-byte seeds for all 6 components
# Paths: /etc/ml-defender/{component}/seed.bin (chmod 0600)
```

**Validated datasets:**
- CTU-13 Neris (botnet, DAY 79–87 baseline): F1 = 0.9985
- CTU-13 bigFlows (mixed traffic, stress testing)

**Stress test results (DAY 87):**
- VirtualBox NIC bottleneck confirmed at 33–38 Mbps
- Pipeline itself: 100% of deliverable traffic processed, zero errors
- Bare-metal testing is the next P1 milestone

### 9.2 Production — Bare-Metal Linux

**Requirements:**
- Linux kernel ≥ 5.10 (eBPF/XDP support)
- NIC with XDP driver support (Intel i40e, Mellanox mlx5)
- ≥ 4 GB RAM
- ≥ 2 CPU cores
- No internet connectivity required (fully air-gapped capable)
- Capabilities: sniffer needs `CAP_NET_RAW + CAP_NET_ADMIN`; firewall-acl-agent needs `CAP_NET_ADMIN`; all others unprivileged

> ⚠️ **Docker with `--privileged` is explicitly prohibited.** eBPF/XDP requires direct kernel access. Use bare-metal or VM with full kernel access.

**Target hardware:**
- Intel N100 mini PC (~150€) — primary target
- Raspberry Pi 5 arm64 (~80€) — secondary target

### 9.3 Deployment Forms (Roadmap)

| Form | Description | Status |
|------|-------------|--------|
| Vagrant single-VM | Lab, development, paper validation | ✅ Active |
| Debian "Argus" appliance image | Hardened Bookworm image, all components selectable | ⏳ Post-arXiv |
| Individual Debian packages | Per-component `.deb`, advanced operators | ⏳ Post-arXiv |
| Ansible recipe (distributed) | Topology from `deployment.yml`, Jinja2 JSON generation | ⏳ FASE 3 |
| RPM packages | RedHat/CentOS/Fedora | ⏳ If demand |
| Windows (firewall-acl-agent only) | WFP/Npcap alternative to eBPF | ⏳ If demand, I+D required |

### 9.4 Configuration — "JSON is the law"

All component configuration lives in JSON files stored in etcd. **No component may hardcode a parameter that belongs in its config JSON.** Components start from etcd, not from local files.

The `deployment.yml` (FASE 3) will be the topology SSOT — defining instances, hosts, and seed families for distributed deployments.

---

## 10. Security Design

### 10.1 Cryptographic Chain of Trust

```
provision.sh → seed.bin (chmod 0600, /etc/ml-defender/{component}/)
    └► SeedClient (explicit_bzero on unload, validates 0600 perms)
        └► HKDF-SHA256 (libsodium 1.0.19, RFC 5869)
            └► CryptoTransport (ChaCha20-Poly1305 IETF)
                └► ZeroMQ channel (symmetric context per channel)
```

### 10.2 HKDF Context Symmetry (ADR-013 PHASE 2 — DAY 99)

**Critical design rule:** The HKDF context identifies the **channel**, not the component.
Defined in `crypto-transport/include/crypto_transport/contexts.hpp`:

```cpp
// The context belongs to the CHANNEL — not the sender or receiver.
// Emitter and receiver of the same channel use the same constant
// → same derived key → no MAC error.
constexpr const char* CTX_SNIFFER_TO_ML  = "ml-defender:sniffer-to-ml-detector:v1";
constexpr const char* CTX_ML_TO_FIREWALL = "ml-defender:ml-detector-to-firewall:v1";
// ... (6 channels total)
```

This rule was validated by catching a real asymmetry bug in DAY 99 (see ADR-022 — pedagogical case for the arXiv paper).

### 10.3 Fail-Closed Behavior

- **`set_terminate()`** registered in all 6 `main()` functions: unhandled exceptions → `[FATAL]` log + `std::abort()` (DAY 100)
- **EventLoader + RAGLogger**: throw on `CryptoTransport` init failure — no component starts with degraded crypto (DAY 99)
- **Pipeline start gate**: `provision-check` must pass before `pipeline-start` (DAY 95)

### 10.4 Data Integrity

Every CSV row written by `ml-detector` and `firewall-acl-agent` carries an HMAC-SHA256. `rag-ingester` verifies before indexing. A tampered audit log is detected and rejected.

### 10.5 LLM Confinement (ADR-010)

`rag-security` LLM confined by skills registry. Attackers who control traffic payloads indexed in FAISS cannot use those payloads to exfiltrate data or execute commands.

### 10.6 Trace ID System

Every flow gets a `trace_id` derived from the 5-tuple and a timestamp bucket. End-to-end correlation across all 6 components without transmitting the full 5-tuple in every message.

### 10.7 Threat Model Summary (ADR-022)

| Threat | Mitigation |
|--------|-----------|
| Passive eavesdropping | ChaCha20-Poly1305 IETF |
| Message replay | 96-bit monotonic nonce |
| Component impersonation | seed.bin + HKDF → MAC failure |
| seed.bin theft | chmod 0600, mlock() (P2) |
| Config tampering | OS hardening (ADR-019) |
| RAG prompt injection | TinyLlama confined (ADR-010) |

**Out of scope (PHASE 1):** kernel-level attacks (ADR-015), PKI compromise (not used — seed-based), multi-instance replay (FASE 3 families).

---

## 11. ML Subsystem

### 11.1 Model Architecture

Random Forest, 100 trees, trained on CTU-13 Neris. ONNX export → ONNX Runtime C++ API. Inference < 5ms per flow on single CPU core.

### 11.2 Feature Engineering

127-column feature vector:
- Flow-level statistics: duration, packet count, byte count, inter-arrival times
- TCP flag ratios: SYN, ACK, RST (`rst_ratio`), FIN
- Connection quality: `syn_ack_ratio`, half-open connections
- Destination diversity: unique dst IPs, unique dst ports
- Protocol signals: dst port 445 ratio (SMB), DNS query count
- Temporal patterns: connection rate, burst detection

### 11.3 Sentinel Value Taxonomy

| Value | Name | Meaning |
|---|---|---|
| `-9999.0f` | `MISSING_FEATURE_SENTINEL` | Feature not computable — deterministic routing |
| Semantic values | Various | Domain-specific defaults (e.g., `0.5f` for TCP half-open) |

`-9999.0f` is **mathematically unreachable** in real traffic. Embedded in all 40 float fields at initialization, preventing Proto3 default-value-suppression bug (DAY 76–78).

### 11.4 Generalization Limitations

| Attack Type | Estimated Recall | Notes |
|---|---|---|
| Neris IRC botnet | 1.0000 | Training distribution |
| Generic port scanning | ~0.85–0.95 | Similar flow statistics |
| WannaCry / NotPetya (SMB) | ~0.70–0.85 | Requires `rst_ratio`, `syn_ack_ratio` + retraining |
| DNS-based C2 | Low | Layer 3/4 only — DPI required |

---

## 12. Performance Envelope

### Validated (Vagrant / VirtualBox)

| Metric | Value | Condition |
|---|---|---|
| Throughput (pipeline) | 100% at ≤ 38 Mbps | VirtualBox NIC limit |
| Detection latency (Path A) | < 1 ms | FastDetector rule engine |
| Detection latency (Path B) | < 5 ms | ONNX Runtime RandomForest |
| Crypto errors | 0 / 36,000 events | DAY 52–62 stress test |
| F1 Score | 0.9985 | CTU-13 Neris, DAY 86 |
| False Negative Rate | 0.00% | Zero missed malicious flows |

### Next milestone
**Bare-metal stress test** — confirm ≥ 100 Mbps without VirtualBox NIC bottleneck.
Target hardware: Intel N100 mini PC or equivalent with XDP-capable NIC.

---

## 13. Known Limitations

1. **DEBT-FD-001 — Path A hardcoded thresholds:** Ignores `sniffer.json`. Resolution in PHASE 2 (ADR-006).

2. **Single-instance per role (PHASE 1):** Multi-instance requires FASE 3 seed families (ADR-021). No shortcuts — see ADR-022 for why Opción 2 was discarded.

3. **Single-window aggregation:** Fixed 10-second window. NotPetya lateral movement requires 60s+. Mitigation: FEAT-WINDOW-2 (P2).

4. **No DPI:** Layer 3/4 only. DNS-based C2 and encrypted C2 not detectable without DPI. Explicit design choice for resource-constrained targets.

5. **Dataset bias:** Model trained on 98% malicious CTU-13 Neris. Performance on balanced real-world distributions is estimated but not yet validated at bare-metal scale.

6. **libsodium packaging:** 1.0.19 compiled from source (Debian Bookworm caps at 1.0.18). Not managed by apt. Migration to Debian Trixie planned (DEBT-INFRA-001).

7. **haveged entropy:** Acceptable for development. Production deployments should use `rng-tools5` with hardware RNG (DEBT-INFRA-002, ADR-019).

---

## 14. Roadmap

### PHASE 1 — Current (DAY 100)
- ✅ 6/6 pipeline components running end-to-end
- ✅ 24/24 CTest suites passing
- ✅ F1 = 0.9985 on CTU-13 Neris
- ✅ Full cryptographic chain: HKDF-SHA256 + ChaCha20-Poly1305 + symmetric contexts
- ✅ Fail-closed: set_terminate() + EventLoader/RAGLogger + provision-check gate
- ✅ Full arXiv paper draft (v5 + LaTeX)
- 🔄 arXiv submission (endorsers contacted: Sebastian Garcia ✅, Yisroel Mirsky ✅)
- ⏳ Bare-metal stress test (P1 pre-arXiv)

### PHASE 2 — Features (post-arXiv)
| ID | Feature | Priority |
|---|---|---|
| rst_ratio | RST packet ratio feature | P1 |
| syn_ack_ratio | SYN/ACK ratio feature | P1 |
| DEBT-FD-001 | Fix Path A to read sniffer.json | P1 |
| FEAT-NET-1 | DNS/DGA detection | P1 |
| FEAT-WINDOW-2 | 60s secondary aggregation window | P2 |
| DEBT-INFRA-001 | Migrate to Debian Trixie | P2 |
| DEBT-INFRA-002 | rng-tools5 + hardware RNG | P2 |
| FEAT-ROTATION-1 | provision.sh rotate-all policy | P2 |
| ADR-012 PHASE 1b | Plugin loader integrated in sniffer | P3 |

### FASE 3 — Distributed deployment (post-arXiv, Consejo review required)
| Item | Description |
|------|-------------|
| deployment.yml | Topology SSOT (ADR-021) |
| Seed families | Channel-scoped seeds for multi-instance |
| provision.sh refactor | Reads deployment.yml, distributes seeds per family |
| Ansible recipe | Jinja2 templating, 3-environment pipeline (test/preprod/prod) |
| Self-hosted CI | argus-debian-bookworm runner for full build+test |

### Long-term — GAIA Vision
ML Defender is designed as the leaf node of a **hierarchical immune network**:
- **Local RAG-clients** (this system) — per-organization, fully offline
- **Campus RAG-masters** — aggregate threat intelligence across local nodes
- **Global RAG-masters** — federated intelligence sharing across organizations

---

## Contributing

Please read `CONTRIBUTING.md` before submitting pull requests.

**Methodology:** ML Defender uses **Test Driven Hardening (TDH)** — every new feature is accompanied by:
1. A failing test that defines the expected behavior
2. The implementation
3. A passing test suite (24/24 minimum)
4. An ADR if the change affects system architecture

**Consejo de Sabios:** Major architectural decisions are reviewed by a panel of 7 AI models (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai) before acceptance. See `docs/consejo/` for decision records.

**macOS development note:** Never use `sed -i` without `-e ''` on macOS (BSD sed). Use Python3 heredoc scripts or edit inside the Vagrant VM.

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus NDR)*
*DAY 100 — 28 marzo 2026*