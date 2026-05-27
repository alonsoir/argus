# Synthetic Data Generation Spec — WannaCry / NotPetya SMB Traffic

> **Path:** `docs/design/synthetic_data_wannacry_spec.md`
> **Status:** DRAFT — DAY 91 (19 marzo 2026)
> **Origin:** Consejo de Sabios — Consulta #1 (DAY 90)
> **Authors:** Alonso Isidoro Román + Claude (Anthropic)
> **Purpose:** Define the ground truth for synthetic SMB ransomware traffic generation,
> enabling `rst_ratio` / `syn_ack_ratio` feature validation and model retraining.

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Scope and Non-Scope](#2-scope-and-non-scope)
3. [Attack Profile — WannaCry](#3-attack-profile--wannacry)
4. [Attack Profile — NotPetya](#4-attack-profile--notpetya)
5. [Feature Targets (Quantitative)](#5-feature-targets-quantitative)
6. [Control Negative — Legitimate Windows SMB Traffic](#6-control-negative--legitimate-windows-smb-traffic)
7. [Dataset Composition](#7-dataset-composition)
8. [Generation Methodology](#8-generation-methodology)
9. [Validation Criteria](#9-validation-criteria)
10. [Known Constraints and Honest Limitations](#10-known-constraints-and-honest-limitations)
11. [Implementation Backlog](#11-implementation-backlog)

---

## 1. Motivation

The current ML Defender model (Random Forest, CTU-13 Neris baseline) achieves **F1 = 0.9985** on IRC botnet C2 traffic. However, as established by the Consejo de Sabios in Consulta #1 (DAY 90), the model's estimated recall against SMB-based ransomware (WannaCry, NotPetya) **without retraining** is:

> **Recall ≈ 0.70–0.85**

This gap exists for two reasons:

1. **Missing features:** `rst_ratio` and `syn_ack_ratio` — the primary discriminators for SMB scanning behavior — are currently sentinel-valued (`-9999.0f`) for all flows. The model has never seen real values for these features.

2. **Training distribution mismatch:** CTU-13 Neris captures IRC C2 traffic. WannaCry/NotPetya propagation via SMB port 445 produces a fundamentally different flow signature.

This document specifies the **ground truth** for synthetic data generation that will:
- Provide realistic `rst_ratio` / `syn_ack_ratio` values for feature validation
- Enable retraining of the Random Forest with SMB ransomware examples
- Establish a labeled control negative set (legitimate Windows SMB traffic) for FPR calibration

---

## 2. Scope and Non-Scope

### In scope
- Layer 3/4 flow statistics (packet rates, byte rates, TCP flag ratios, connection counts)
- Port 445 (SMB) traffic patterns for WannaCry and NotPetya propagation phases
- Lateral movement within a /24 subnet (typical organizational network)
- Legitimate Windows administrative traffic as control negatives

### Explicitly out of scope

> **Killswitch DNS domain lookup (WannaCry):**
> The WannaCry killswitch mechanism — a DNS query to a specific domain before payload execution — is **not included** as a detection signal.
>
> **Rationale (Consejo unanimous):**
> - ML Defender operates at Layer 3/4 only. DNS content (the queried domain name) requires DPI.
> - The DNS→SMB composite signature was analyzed and discarded: the pattern (DNS query followed by SMB activity) appears in **legitimate Windows traffic** (WSUS updates, domain controller lookups) at an FPR that makes the signal unreliable.
> - WannaCry's propagation via SMB scanning **already produces a strong signal** through `rst_ratio` alone. The killswitch lookup adds no discriminative value for a layer 3/4 detector.
>
> **Consequence:** A host that has already checked the killswitch domain and is now propagating is indistinguishable at layer 3/4 from a host that never checked. Both produce the same SMB scan signature. This is an explicit, honest limitation — see §10.

---

## 3. Attack Profile — WannaCry

### 3.1 Behavioral Description

WannaCry's propagation mechanism is a **mass-scanning SMB worm** exploiting EternalBlue (MS17-010). An infected host:

1. Generates TCP SYN packets to random IPs on port 445 at high rate
2. Receives RST from most targets (hosts down, filtered, or not vulnerable)
3. Completes TCP handshake only with vulnerable hosts
4. Exploits the vulnerability and installs the payload
5. The newly infected host immediately begins scanning

The key flow-level observable: **massive RST flood from non-responsive targets**, producing an extremely high `rst_ratio` and extremely low `syn_ack_ratio`.

### 3.2 Flow Characteristics

| Characteristic | WannaCry Value | Notes |
|---|---|---|
| Target port | 445 (TCP) | SMB — occasionally also 139 |
| Scan strategy | Pseudo-random IP generation | Biased toward /8 subnets of the infected host |
| Connection rate | **100–200 SYN/s per infected host** | Peak during active propagation |
| RST ratio | **> 0.7** (often 0.85–0.95) | Most targets do not respond or actively reset |
| SYN/ACK ratio | **< 0.1** | Only vulnerable hosts complete the handshake |
| Unique dst IPs | **Hundreds to thousands / 10s window** | True mass scanning |
| Bytes per flow | Very low for failed connections (SYN only) | High for successful exploitation |
| Flow duration | Bimodal: < 50ms (failed) / seconds (exploited) | |
| Inter-arrival time | Very low (< 10ms between SYNs) | High-rate scanning |

### 3.3 Within-Subnet Signature (10s window)

During active propagation within a /24:

```
source_ip:     single infected host
dst_port:      445 (constant)
unique_dst_ips: 50–254 (scanning entire /24)
syn_count:     500–2000
ack_count:     < 50
rst_count:     400–1800
rst_ratio:     > 0.80
syn_ack_ratio: < 0.05
connection_rate: > 100/s
dst_port_445_ratio: ~1.0
```

---

## 4. Attack Profile — NotPetya

### 4.1 Behavioral Description

NotPetya is a **destructive wiper** (not ransomware in the strict sense) that spreads via multiple mechanisms:
- EternalBlue (same as WannaCry, port 445)
- WMIC (Windows Management Instrumentation — WMI) lateral movement
- PsExec-based credential reuse
- Mimikatz-based credential extraction (memory-only, not observable at L3/4)

The SMB scanning phase is similar to WannaCry but **more targeted**: NotPetya prioritized internal network ranges rather than random internet IPs.

### 4.2 Flow Characteristics

| Characteristic | NotPetya Value | Notes |
|---|---|---|
| Target port | 445 (TCP), 135 (WMI/RPC), 139 | More protocol diversity than WannaCry |
| Scan strategy | Internal subnet priority, then random external | Explains the catastrophic internal spread |
| Connection rate | **50–150 SYN/s** | Slightly lower than WannaCry per host |
| RST ratio | **> 0.5** (0.6–0.85) | Lower than WannaCry — more hosts respond internally |
| SYN/ACK ratio | **< 0.2** | More completions than WannaCry (internal hosts more likely up) |
| Unique dst IPs | **Tens to hundreds / 10s window** | Internal /16 scope |
| Protocol diversity | Higher (SMB + WMI + RPC) | `port_diversity_ratio` P2 feature is relevant here |
| Temporal pattern | **Sustained over minutes** | 10s window may miss early phase — FEAT-WINDOW-2 motivation |

### 4.3 FEAT-WINDOW-2 Rationale

NotPetya's internal scan rate is lower than WannaCry. In a 10-second window, an early-phase NotPetya infection may produce only **20–50 SYN packets** to port 445 — insufficient to trigger `rst_ratio` thresholds calibrated for WannaCry's 100+/s rate.

A **60-second secondary aggregation window** (FEAT-WINDOW-2, P2 backlog) would accumulate 120–300 SYNs, making the pattern unambiguous.

**Decision (Consejo):** Maintain the 10s window as primary (sufficient for WannaCry). Add FEAT-WINDOW-2 as P2 to cover NotPetya's slower ramp.

---

## 5. Feature Targets (Quantitative)

These are the **ground truth values** the synthetic dataset must reproduce. The synthetic generator must produce flows where these features fall within the specified ranges.

### 5.1 Malicious Class — WannaCry

| Feature | Column Name | Target Range | Hard Threshold |
|---|---|---|---|
| RST ratio | `rst_ratio` | 0.70 – 0.95 | > 0.50 (P1 Fast Detector) |
| SYN/ACK ratio | `syn_ack_ratio` | 0.02 – 0.10 | < 0.15 (P1 Fast Detector) |
| Connection rate | `connection_rate` | 100 – 200 /s | > 100/s |
| Unique dst IPs | `unique_dst_ips_count` | 50 – 2000 / 10s | > 20 |
| DST port 445 ratio | `dst_port_445_ratio` | 0.90 – 1.00 | > 0.80 (P2) |
| Port diversity ratio | `port_diversity_ratio` | 0.01 – 0.05 | Low (P2) |
| Flow duration (failed) | `flow_duration_ms` | 10 – 100 ms | — |
| **Min flow duration** | **`flow_duration_min`** | **< 50 ms** | **P2 — aporte DeepSeek DAY 91; legítimos > 200ms** |
| Bytes per packet | `bytes_per_packet` | 60 – 80 bytes | — (SYN-only) |

### 5.2 Malicious Class — NotPetya

| Feature | Column Name | Target Range | Notes |
|---|---|---|---|
| RST ratio | `rst_ratio` | 0.50 – 0.85 | Lower — more internal hosts respond |
| SYN/ACK ratio | `syn_ack_ratio` | 0.05 – 0.20 | More completions |
| Connection rate | `connection_rate` | 50 – 150 /s | Slower than WannaCry |
| Unique dst IPs | `unique_dst_ips_count` | 20 – 500 / 10s | Internal /16 focus |
| DST port 445 ratio | `dst_port_445_ratio` | 0.60 – 0.85 | Mixed with WMI/RPC |
| Port diversity ratio | `port_diversity_ratio` | 0.05 – 0.20 | Higher — WMI/RPC ports |
| Protocol mix | 445 + 135 + 139 | — | `dst_port_445_ratio` < 1.0 |

### 5.3 Summary Discriminator Table

| Feature | WannaCry | NotPetya | Legitimate Windows | Discriminative? |
|---|---|---|---|---|
| `rst_ratio` | **> 0.70** | **> 0.50** | < 0.10 | **YES — P1** |
| `syn_ack_ratio` | **< 0.10** | **< 0.20** | > 0.70 | **YES — P1** |
| `connection_rate` | > 100/s | > 50/s | < 10/s | YES |
| `unique_dst_ips_count` | Hundreds | Tens–hundreds | 2–10 | YES |
| `flow_duration_min` | **< 50 ms** | **< 100 ms** | > 200 ms | **P2 — aporte DeepSeek DAY 91** |
| `dst_port_445_ratio` | ~1.0 | 0.60–0.85 | 0.10–0.40 | P2 |
| `port_diversity_ratio` | Very low | Low–medium | Medium | P2 |
| `dns_query_count` | (not used) | (not used) | Variable | **NOT USED — P3** |

---

## 6. Control Negative — Legitimate Windows SMB Traffic

The control negative set must represent **normal Windows administrative traffic** that:
- Uses port 445 legitimately (file shares, printer discovery, DC authentication)
- Generates SYN/RST traffic at low rates (host discovery, timeout retries)
- Would produce **false positives** if the detector is poorly calibrated

### 6.1 Legitimate SMB Sources

| Traffic Type | Port(s) | Expected `rst_ratio` | Expected `syn_ack_ratio` | Notes |
|---|---|---|---|---|
| Windows file share access | 445 | < 0.05 | > 0.85 | Most connections complete |
| Network printer discovery | 445, 139 | 0.10 – 0.30 | 0.60 – 0.85 | Some hosts don't respond |
| Domain controller auth | 445, 88, 389 | < 0.05 | > 0.90 | Highly reliable connections |
| WSUS update distribution | 445, 8530 | < 0.10 | > 0.80 | Controlled client list |
| SCCM / Endpoint Manager | 445, 135, 445 | 0.05 – 0.20 | 0.70 – 0.90 | Mixed protocol |
| Backup agents (Veeam etc.) | 445 | < 0.05 | > 0.90 | Long-duration, high-byte flows |
| NetBIOS name resolution | 137, 138 (UDP) | N/A | N/A | UDP — separate handling |

### 6.2 Hard Rule for Control Negative

A control negative flow is valid **only if** all of the following hold:

```
rst_ratio       < 0.30    (not a scanning pattern)
syn_ack_ratio   > 0.50    (majority of connections complete)
connection_rate < 20/s    (not a burst)
unique_dst_ips  < 15      (not scanning a subnet)
dst_port_445_ratio < 0.70 (mixed protocol use expected in admin traffic)
```

Any synthetic flow violating these bounds should be reclassified as suspicious and excluded from the control negative set.

### 6.3 Why This Matters

The Consejo confirmed (Consulta #1) that `rst_ratio` alone is a **high-signal feature** for WannaCry/NotPetya. However, without a realistic control negative set, the model may learn:

> "High `rst_ratio` AND port 445 → malicious"

...and fail on legitimate network environments where port 445 RSTs are common (e.g., a hospital network with many dormant workstations responding with RST to file share discovery).

The control negative set prevents this overfitting.

---

## 7. Dataset Composition

### 7.1 Target Split

| Class | Count (flows) | Ratio | Notes |
|---|---|---|---|
| WannaCry (malicious) | 5,000 | 25% | 10s windows per infected host |
| NotPetya (malicious) | 3,000 | 15% | 10s and 60s windows |
| Legitimate Windows SMB | 8,000 | 40% | Control negative |
| Benign general traffic | 4,000 | 20% | From CTU-13 background flows |
| **Total** | **20,000** | 100% | |

**Rationale for balance:** The CTU-13 Neris training set had ~98% malicious traffic, which introduced dataset bias. This synthetic set targets a realistic 40% malicious / 60% benign split.

### 7.2 Feature Coverage

All 127 features in the `FlowRecord` schema must be populated. Features not relevant to SMB scanning (e.g., ICMP-specific fields) should receive **realistic benign values** from the CTU-13 background distribution, not sentinel values.

Only features for which no ground truth exists (non-computable for a given flow type) should use `MISSING_FEATURE_SENTINEL = -9999.0f`.

### 7.3 Label Schema

```csv
flow_id, label, attack_family, window_seconds, rst_ratio, syn_ack_ratio, 
connection_rate, unique_dst_ips_count, dst_port_445_ratio, ...
```

- `label`: 0 (benign) / 1 (malicious)
- `attack_family`: "wannacry" / "notpetya" / "benign_smb" / "benign_general"
- `window_seconds`: 10 or 60

---

## 8. Generation Methodology

### 8.1 Options Evaluated

| Method | Pros | Cons | Decision |
|---|---|---|---|
| **tcpreplay of real captures** | Highest fidelity | Legal/ethical issues distributing WannaCry pcaps; VirtualBox NIC bottleneck | Use for reference only |
| **Scapy / libpcap packet crafting** | Full control; no legal issues | Complex; must validate statistical properties | **Primary method** |
| **Statistical sampling from distributions** | Fast; controllable | No packet-level fidelity; risk of unrealistic correlations | Use for augmentation |
| **GAN-based generation** | Could learn complex correlations | Overkill for L3/4 features; training cost | Future / P3 |

### 8.2 Recommended Pipeline

```
Step 1 — Define per-class parameter distributions
   For each attack class: sample rst_ratio, syn_ack_ratio, 
   connection_rate from the ranges in §5.
   Use truncated normal distributions, not uniform 
   (real traffic is not uniform within a range).

Step 2 — Generate individual flow records
   For each synthetic flow:
   a. Sample class-appropriate feature values
   b. Derive correlated features consistently
      (e.g., if rst_ratio=0.85, then ack_count ≈ 0.15 * syn_count)
   c. Add realistic noise (±5–10%) to avoid artificially sharp boundaries
   d. Populate non-SMB features from CTU-13 background distribution

Step 3 — Validate against §9 criteria
   Reject any flow that violates label consistency rules.

Step 4 — Export to CSV with HMAC-SHA256 per row
   Use the same format as ml-detector's daily CSV output.
   This enables direct ingestion by rag-ingester for validation.

Step 5 — Replay via tcpreplay (optional)
   If packet-level validation is needed, generate .pcap from
   the synthetic flows using Scapy and replay through the
   sniffer in the Vagrant lab.
```

### 8.3 Correlation Constraints

The following inter-feature correlations must be enforced to avoid unrealistic flows:

```python
# WannaCry example — must hold simultaneously:
assert rst_count ≈ rst_ratio * total_packets
assert syn_count ≈ connection_rate * window_seconds
assert ack_count ≈ syn_ack_ratio * syn_count
assert unique_dst_ips_count <= connection_rate * window_seconds
assert dst_port_445_ratio > 0.85
# Bytes: SYN-only flows are 60-80 bytes; completed flows are larger
assert bytes_per_packet < 100 if syn_ack_ratio < 0.1 else bytes_per_packet > 200
```

---

## 9. Validation Criteria

A synthetic dataset batch is **accepted** if and only if:

### 9.1 Statistical Validity

| Check | Method | Pass Criterion |
|---|---|---|
| `rst_ratio` distribution (WannaCry) | KS test vs. target range | p > 0.05, mean > 0.70 |
| `syn_ack_ratio` distribution (WannaCry) | KS test vs. target range | p > 0.05, mean < 0.10 |
| Control negative `rst_ratio` | Max check | No flow > 0.30 |
| Feature correlation consistency | Pearson r | `rst_ratio` ↔ `syn_ack_ratio` r < -0.70 |
| Sentinel value rate | Count | < 5% of non-DNS fields are sentinel |

### 9.2 Classifier Sanity Check

Train a separate hold-out Random Forest on the **synthetic dataset only** and verify:

| Metric | Minimum Acceptable |
|---|---|
| F1 (synthetic WannaCry) | > 0.85 |
| F1 (synthetic NotPetya) | > 0.80 |
| FPR on control negative | < 0.15 |
| FPR on benign general | < 0.10 |

If these thresholds are not met, the generator parameters must be revised before the dataset is used for production retraining.

### 9.3 Pipeline Integration Test

The synthetic CSV must pass through the existing ml-detector pipeline without errors:
- HMAC verification: 0 failures
- Sentinel routing: correct for all flows with missing features
- No `MISSING_FEATURE_SENTINEL` propagation to features that should have real values

---

## 10. Known Constraints and Honest Limitations

These limitations are explicitly acknowledged and must be included in any paper or report using this dataset.

1. **No real WannaCry/NotPetya captures used.** The synthetic dataset is generated from behavioral descriptions and published research, not from actual malware execution. Distribution tails (extreme cases, unusual variants) may be underrepresented.

2. **Killswitch DNS not detectable.** The WannaCry DNS killswitch lookup is excluded by design. A host that queries the killswitch domain and then starts scanning produces the same layer 3/4 flow signature as one that does not. See §2 for full rationale.

3. **10s window underrepresents early NotPetya.** The primary 10s aggregation window may miss early-phase NotPetya infections with slow scan rates (< 20 SYN/s). FEAT-WINDOW-2 (60s window) is required for full coverage.

4. **No SMB variant coverage.** EternalBlue variants (EternalRomance, EternalSynergy) and newer SMB exploits (PrintNightmare, ZeroLogon) are not modeled. The synthetic data targets MS17-010 behavior specifically.

5. **No encrypted SMB (SMB3).** Modern Windows environments use SMB3 with encryption. Encrypted SMB traffic renders payload-based features meaningless, but **flow-level statistics remain observable** — `rst_ratio` and `syn_ack_ratio` are payload-agnostic and remain valid signals.

6. **Generalization to other worms not validated.** The feature ranges defined here are specific to WannaCry/NotPetya. Other scanning worms (Mirai, Blaster) may produce different `rst_ratio` / `syn_ack_ratio` profiles and are not covered.

---

## 11. Implementation Backlog

Tasks required to execute this spec:

| ID | Task | Priority | Dependency |
|---|---|---|---|
| SYN-1 | Implement `rst_ratio` feature extractor in sniffer | **P1** | None |
| SYN-2 | Implement `syn_ack_ratio` feature extractor in sniffer | **P1** | None |
| SYN-3 | Write synthetic flow generator (Python/Scapy) | P1 | SYN-1, SYN-2 |
| SYN-4 | Validate generated CSV against §9 criteria | P1 | SYN-3 |
| SYN-5 | Retrain Random Forest with synthetic + CTU-13 data | P1 | SYN-4 |
| SYN-6 | Validate retrained model on held-out CTU-13 Neris | P1 | SYN-5 |
| SYN-7 | Update F1 log (`docs/experiments/f1_replay_log.csv`) | P1 | SYN-6 |
| SYN-8 | Implement `dst_port_445_ratio` extractor | P2 | None |
| SYN-8b | Implement `flow_duration_min` extractor (aporte DeepSeek DAY 91) | P2 | None |
| SYN-9 | Implement `port_diversity_ratio` extractor | P2 | None |
| SYN-10 | Implement FEAT-WINDOW-2 (60s secondary window) | P2 | SYN-1, SYN-2 |
| SYN-11 | NotPetya-specific validation with 60s window | P2 | SYN-10 |
| SYN-12 | GAN-based augmentation (optional) | P3 | SYN-5 |

**Critical path:** SYN-1 → SYN-2 → SYN-3 → SYN-4 → SYN-5 → SYN-6 → SYN-7

The first milestone is **rst_ratio + syn_ack_ratio implementation** in the sniffer (DAY 91–92, next VM session).

---

## References

- CTU-13 Dataset: Garcia et al., "An empirical comparison of botnet detection methods" (2014)
- WannaCry technical analysis: NHS Digital Incident Report (2017); Check Point Research (2017)
- NotPetya technical analysis: ESET "Industroyer" report; Talos Intelligence (2017)
- EternalBlue (MS17-010): Microsoft Security Bulletin MS17-010
- Consejo de Sabios — Consulta #1 decisiones finales: `docs/consejo/consejo_consulta_1_decisiones_finales.md`
- ADR-007 (AND-consensus scoring): `docs/adr/ADR-007-consensus-scoring-firewall.md`
- ADR-008 (flow graphs and forensic retraining): `docs/adr/ADR-008-flow-graphs-reentrenamiento-forense.md`

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus EDR)*
*DAY 91 — 19 marzo 2026*