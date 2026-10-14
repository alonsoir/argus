# aRGus NDR (ML Defender)

**Open-source, C++20 multi-sensor network + host detection pipeline for critical infrastructure. Research artifact — not a production system.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2604.04952_cs.CR-red)](https://arxiv.org/abs/2604.04952)
[![C++20](https://img.shields.io/badge/C%2B%2B-20-blue)]()
[![Status](https://img.shields.io/badge/Status-Research_artifact_(not_production)-orange)]()

> *Via Appia Quality — systems built like Roman roads, designed to endure.*

---

## What this is

aRGus NDR is a reproducible pipeline that drives network traffic through **four heterogeneous sensors** and correlates what they see into a queryable graph:

- **aRGus** — an embedded ML classifier with an eBPF/XDP sensor (the lens the project controls end to end)
- **Suricata** — signature / rule-based detection
- **Zeek** — protocol telemetry (observation, not verdict)
- **Wazuh** — host-based (HIDS) telemetry

The three network sensors emit a `correlation_v1` contract → medallion **gold** (Parquet) → a **Kuzu** graph, correlated across sensors by `community_id` (edge `CORRELATES_FLOW`). Wazuh emits a separate `host_domain_v1` contract into its **own** Kuzu graph.

The sensors are heterogeneous **by design** and complementary, not competitors: one classifies, one detects, one describes, one watches the host. The value of the instrument is characterizing that heterogeneity — the bias of each lens against ground truth — not normalizing it away.

## Defensive by design

aRGus exists to protect hospitals and civilian critical infrastructure. It is **defensive by design**: it observes, classifies and (in the future) blocks traffic on the perimeter it watches. It has no offensive capabilities — no counter-attack, no active scanning of third parties, no "hack-back" — and it never will. This is a statement of the project's purpose, not a restriction added to the license.

## The honest thesis

This project began as an attempt to build an ML system that classifies network telemetry and acts on it autonomously. The paper ends as something more useful and less triumphant: **a complete, reproducible forensic record of how a system reporting F1 = 0.9985 on a curated subset was, operationally, carried by a heuristic fast-path with its ML head effectively blind on cross-distribution botnet traffic.**

That is an empirical confirmation, with traces, of what Sommer & Paxson argued in 2010 and Arp et al. in 2022. The failure here was **not** "ML for intrusion detection is impossible" — there is modest real signal (in-sample AUC ≈ 0.746) — it was **distribution transfer** (a model trained on CIC-IDS-2017 collapses to ≈ 0.0001 on CTU-13 Neris). Negative results in security ML are systematically under-published; this repository is the audit almost nobody runs, because there is no incentive to run it.

For critical-infrastructure operators, a blind NDR that gives false confidence is worse than none. Saying so with data is the contribution.

**After the paper**, the work continues in the same spirit: the detection heads are being rebuilt **one at a time**, each with a measured contract, lab-generated training data and a written prediction before every measurement. Only a head that passes that bar is allowed to make decisions. Today that is **one head: DDoS** (see *Current state*).

## Results of the paper, anchored

Every number below is behind a `make` target (see *Reproduce the paper*); the exact outputs for the anchored run `20260804-080140` are committed under [`paper-artifacts/`](paper-artifacts/), readable without running anything. The [paper](https://arxiv.org/abs/2604.04952) carries the full treatment; this is the door.

**Classifier, on the curated behavioral subset (646 malicious flows of CTU-13 Neris):** F1 = 0.9985, Precision = 0.9969, Recall = 1.0000, false-positive rate 0.017% (2 FP in 12,077 benign, both host-only adapter artifacts). This is a **curated subset** — it is not the operational picture, and it is stated as such.

**Operational per-lens bias, over the full replayed capture** (run `20260804-080140`, denominator = 14,188 lens-observable botnet flows):

| Lens | What it is | Botnet coverage | Verdict |
|---|---|---|---|
| **Zeek** | protocol telemetry | 99.9% (14,178 / 14,188) | observer, ~1:1 per connection, no verdict |
| **Suricata** | signatures (ET Open) | 1.5% (206 / 14,188) | only protocol-anomaly hits, **no botnet signature** — the ET Open "F1 = 0 on 2011 Neris" made precise |
| **aRGus** | embedded ML | coarse: 48 distinct flows, ~28.5 events each | captures the persistent C&C; ML head blind (≈ 0.07), heuristic fast-path (0.75) carries **every** MALICIOUS verdict |

> aRGus and Zeek quantize the *same* traffic at different granularities — Zeek 1:1 into ~14k micro-flows, aRGus into coarse persistent flows (×28.5 events) — so a raw "visibility %" is not comparable across those two lenses. The bias is granularity, not blindness; see the paper.

- **True denominator** (tshark over the pcap): 14,255 botnet flows. **Lens-observable:** 14,188. The 0.47% gap (67 flows) never reached the replayed wire — verified across both capture stacks and Zeek's raw `conn.log` — a **replay-fidelity limit**, not a detection or pipeline gap.
- **Provenance limit:** the CTU-13 Neris pcap is from 2011, third-party, captured under unknown conditions. We declare this and do not interpret beyond what tshark and the pipeline measure.

These are the paper's results and they describe the pipeline **as it was in that run**. The sections below describe what has changed since.

## Current state (after the paper)

### DDoS head v2 — in shadow mode (tag `pre-release-ddos-only-0.0.3`)

The DDoS head was rebuilt from scratch and is the **only head trusted to decide** (`final_decision`). The other models are still loaded but do not decide.

- **Two stages.** Stage 1: per-victim rate ratio against its own baseline (`victim_rate_ratio ≥ 3`). Stage 2: a 100-tree Random Forest over 6 flow features, trained only on rows under pressure, exported to C++ with raw thresholds. Python/C++ parity: 127,930 / 127,930.
- **Trained on lab-generated traffic** (a controlled battery of reflection/flood families at several rates), not on a public dataset.
- **The firewall runs it in SHADOW mode** (`dry_run`): a per-victim policy (m = 5 DROP per 1 s window, k/n = 3/5 windows to start, 30 windows of hold to end) **records** START/END but **does not block**.

Measured live in the lab (NTP reflection at 60 pps against a host, with an innocent concurrent sender at 10 pps):

| Measure | Value |
|---|---|
| First DROP decision after the attack starts | 0.8–1.8 s |
| Shadow START after the first DROP | 2 windows (k = 3) |
| Shadow END after the last DROP | exactly 30 windows (also under ±5 s wall-clock jumps) |
| DROP events | all from the attacker; 0 from the innocent sender (different traffic type: see the twin test below) |
| Benign run pressing stage 1 (real `dnsperf` at 30/100 q/s + legitimate 50 KB/s TCP upload) | 0 START; 2 isolated positives in ~18,000 rows, absorbed by k = 3/5 |

Known limits of this head (measured, not hidden):

- **Stage 2 learns the signatures of our traffic generators** (packet size, reflection pattern), not behaviour. With a family left out of training, detection of that family drops to ~0%.
- **The head discriminates the type of traffic, not the sender (measured, DAY297).** A "twin" sending the attacker's exact packets from another address is dropped like the attacker: 99.56% of its packets with the twin at 10 pps and 99.17% at 60 pps (attacker: 99.65% / 99.19%). In the same runs, 446 legitimate NTP packets to the same victim from the benign sender got 0 DROP. Per-source features are future work; until then, no per-source blocking.
- **Cold start (measured, to be fixed):** the 30-window warm-up only gates the sniffer's hysteresis state; stage 1 compares the raw rate ratio, so a cold victim can be decided on. In one run, 32 DROP decisions hit legitimate traffic (a Wazuh agent talking to its manager) in the first second after the pipeline started; the shadow did not open an episode.
- **Long attacks are absorbed (measured offline against the production function):** the per-victim baseline keeps learning during the attack, so stage 1 stops passing a sustained attack after 15–25 minutes (sooner for weaker attacks) and the shadow would close the episode mid-attack. Real DDoS attacks can last days; the next branch makes stage 1 consume the hysteresis state and freezes the baseline during an episode.
- **The firewall does not block yet.** Real mitigation is a separate piece of work.
- **Lab only:** VirtualBox VMs on a laptop, rates up to ~110 pps without ring losses; end-to-end accounting at up to 130 pps toward the victim found 0 events lost or duplicated between sniffer and firewall. None of this is real hardware: see [docs/carta_reyes_magos_caceres.md](docs/carta_reyes_magos_caceres.md) for what cannot be measured here.

### Time contract v1 — one time base for the whole pipeline (accepted, DAY297)

A single field used to mix two clock bases (kernel monotonic and wall-clock epoch) depending on the event type. That froze the shadow's clock, corrupted Parquet data and made latencies unmeasurable. The time contract v1 fixes it:

- **One internal base: `CLOCK_MONOTONIC`** for windows, hold and latencies. Wall-clock epoch is derived only at the edges (bronze, logs) through a **per-node anchor** (REALTIME − MONOTONIC).
- **Clock events are detected and logged:** `[CLOCK-STEP]` (wall-clock jump, re-anchoring) and `[CLOCK-SLEW]` (gradual correction, MONOTONIC vs MONOTONIC_RAW).
- Every event carries a `time_context` (`boot_id`, producer sequence, anchor, clock state, contract version). Events with anomalous time are **kept out of the decision windows** and logged for study, never punished on the packet's source IP.
- **Latency is measured per hop** (sniffer → ML detector → firewall) and the parts add up exactly.

Measured in the lab (production build, single node):

| Measure | Value |
|---|---|
| Sniffer → firewall latency, at rest | mean 3.3–5.9 ms, max ≤ 11 ms |
| Same, under a 60 pps attack | mean 2.2–7.6 ms, max ≤ 18.5 ms |
| ±5 s wall-clock jumps mid-attack | detected (+4.9986 s / −5.0001 s); shadow END unaffected; 0 time anomalies |
| Controlled clock slew (+5.3%) | detected at 52,994 ppm (expected 53,000); no false step |
| Producer sequence, sniffer → firewall (3 runs, up to 130 pps) | 0 lost, 0 duplicated in 15,262 / 17,129 / 26,110 events |
| Delivery order | not guaranteed: up to 12 flow events per run overtaken by the next fast-alert (decision logic unaffected; under study) |

The contract is **single-node** (sensor, detector and firewall on the same host). A distributed deployment needs synchronized wall clocks (PTP) and a different design; that is future work.

### Data quality

- The Parquet validator now checks **every row**, not just the first one. Doing so revealed that 89% of the rows of the historical ML-detector Parquet (from 2026-03-08) carried timestamps in the wrong clock base; that data was discarded.
- **Fast-alerts are excluded from the `correlation_v1` bronze** (`correlation_writer.include_fast_alerts = false`) until they are reliable: they carry no flow start time and fire roughly once per DNS packet.

## Reproduce the paper

The reproducibility baseline is **from scratch** — a clean VM (`vagrant destroy -f && vagrant up`, or just `make up` on a fresh clone), keys regenerated, every binary built from zero — so the claim is "reproducible", not "reproducible on my machine". Every figure in the paper is regenerable by a command, and the exact figures of the anchored run sit in [`paper-artifacts/`](paper-artifacts/) for reviewers who would rather read than run.

**One command, from a clean checkout:**

```bash
make up && make bootstrap     # 5 VMs + full pipeline, built and started (first run ~20–30 min)
make reproduce-paper          # builds the sensor binaries it needs, fetches CTU-13 Neris,
                              # drives the replay through the 3 lenses, regenerates every number
```

`make reproduce-paper` composes the seven steps below in order and assumes the pipeline is up (`make bootstrap` leaves it running; on a machine that already has the VMs, prepend `vagrant destroy -f` for a truly clean baseline). The regenerated numbers fall **within replay variance**: the 2011 pcap is replayed at `--mbps=10`, which rewrites inter-arrivals, and tcpreplay deterministically drops 2,630 GSO/TSO super-frames (0.81%) that do not fit standard Ethernet. The figures in `paper-artifacts/` are the exact ones the paper cites.

<details>
<summary>The same, step by step</summary>

```bash
make fetch-neris            # CTU-13 Neris pcap (~56 MB)
make fetch-neris-labels     # per-flow labels (.binetflow, ~386 MB)
make ctu-start              # replay the labelled capture through aRGus + Suricata + Zeek → Kuzu
make dataset-export         # project the graph's gold to a mode-A dataset CSV
make bias-report            # per-lens TP/FP/FN against the CTU labels
make bias-denominator-true  # true denominator (tshark) + the 0.47% blind-spot analysis
make autopsy-67             # where the 67 blind-spot flows die (answer: capture/wire, not pipeline)
```
</details>

The dataset a run produces is a **function of the traffic driver**: a simple driver → a simple dataset, a richer one → a richer dataset. `ctu-start` (replay of the labelled Neris capture) and `mitre-start` (live adversarial nmap, an independent second driver) are two worked drivers over the same invariant downstream. To write your own attack driver — you fill **one line**, the harness does the rest — see [`docs/WRITING-A-DRIVER.md`](docs/WRITING-A-DRIVER.md).

## Install

**macOS**
```bash
brew install --cask virtualbox vagrant
xcode-select --install
```

**Linux (Debian/Ubuntu)** — VirtualBox from Oracle's repo (distro package is often stale), then Vagrant from HashiCorp's repo; `sudo apt-get install -y make`. See the [VirtualBox](https://www.virtualbox.org/wiki/Linux_Downloads) and [Vagrant](https://developer.hashicorp.com/vagrant/install) install docs for the current repo lines.

**Windows 11** — best-effort, **not** officially supported. aRGus produces only Linux binaries (x86-64 / ARM64); Windows is the host, the pipeline runs inside the Linux VM. Run everything from Git Bash. Note the Hyper-V / VirtualBox conflict with WSL2.

> **Clone with submodules** — `git clone --recurse-submodules https://github.com/alonsoir/argus.git`. `third_party/llama.cpp` is a submodule; without the flag it is empty and `rag-security` builds without LLM support (`make submodule-init` fixes an existing clone).
>
> **TinyLlama** (`tinyllama-1.1b-chat-v1.0.Q4_0.gguf`, ~700 MB) is downloaded automatically during `vagrant up`; it is gitignored, never committed.

```bash
make up && make bootstrap    # first run ~20–30 min: builds llama.cpp, installs FAISS/ONNX/XGBoost/libsodium
```

### Running the live lab

The Makefile defaults to a **debug** build (`PROFILE ?= debug`), and `pipeline-start` launches the build of the profile it is given — not the last one compiled. To measure what would be deployed, build, test **and start** with the same profile:

```bash
make pipeline-build  PROFILE=production
make test-components PROFILE=production
make pipeline-stop
make pipeline-start  PROFILE=production
```

If the host sleeps (e.g. the laptop is suspended), the VMs freeze and their wall clocks fall behind; chrony may take a couple of minutes to notice. Realign the lab clocks as soon as the host wakes up, before measuring:

```bash
make lab-clock-step     # chrony makestep on defender, then client; fails if the offset stays ≥ 1 ms
```

Component configuration lives in each component's JSON (`*/config/*.json`): every field documents its format and limits, and a missing or invalid field falls back to a validated default with a `[CONFIG-DEFAULT]` warning while the component keeps running.

## Architecture & review

- **Generated documentation** (browsable): https://alonsoir.github.io/argus/
- **Architecture decisions:** `docs/adr/`
- **Living contracts** (Protobuf / JSON / RAG): `docs/contracts/`
- **Time contract v1:** [`docs/timebase/contrato_temporal_day295.md`](docs/timebase/contrato_temporal_day295.md) (Spanish; §8 holds the measurements)
- **Writing an attack driver:** [`docs/WRITING-A-DRIVER.md`](docs/WRITING-A-DRIVER.md)
- **Code graph** (Graphify — on-device, Apache-2.0): a graph of the *source code*, distinct from the telemetry graph above. Kept by the author as a maintenance aid; **requires login**: https://app.graphify.com/aironman-labs/
- The design was reviewed across eight independent models — the *Consejo de Sabios* (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) — as structured disagreement. The methodology is documented in §6 of the paper.

## Limitations — known and declared

Honesty as an engineering property, not an afterthought:

- **Research artifact, not production.** Only the DDoS head is trusted to decide, and it runs in shadow mode: nothing is blocked yet. The other heads (ransomware, internal traffic, the original level-1 classifier) are not trusted and do not decide.
- **Lab, not hardware.** Every live measurement comes from VirtualBox VMs on a laptop. Latencies, clock behaviour and the thresholds in the JSON files are lab-calibrated and must be measured again on real hardware. What cannot be measured without hardware (native XDP drop rate, ring saturation, ransomware detection under a real DDoS, upstream defence of the bandwidth) and the equipment that would unlock it are written down in [docs/carta_reyes_magos_caceres.md](docs/carta_reyes_magos_caceres.md) (in Spanish).
- **DDoS head, measured limits:** it discriminates traffic type, not sender; it absorbs sustained attacks after 15–25 minutes; it can decide on a cold victim. See "Current state" above.
- **Single node.** The time contract assumes sensor, detector and firewall on one host. Distributed deployment (PTP-synchronized clocks) is future work.
- **Fast-alerts are not reliable** and are excluded from the bronze contract until they are.
- **Deferred hardening**, carried as known-and-deferred (not hidden): productive Vault, key rotation, real fault-injection, secure HMAC transport (HTTPS/Vault), and a reverse-engineering audit of the shipped binaries.
- **Replay fidelity:** 0.47% of the offline-true botnet flows do not reach the replayed wire.
- **Provenance:** the 2011 Neris pcap is third-party, captured under unknown conditions.

## History

The day-by-day engineering log lives in [`docs/HITOS.md`](docs/HITOS.md) (DAY 111–252) and, for later days, in [`docs/BACKLOG.md`](docs/BACKLOG.md) and the design documents under `docs/`. They record what was understood on each day; many figures there were later refined or corrected (e.g. F1 = 0.9985 was anchored to the 646-flow behavioral subset). They are **not** a description of the current state of the pipeline — this README is.

[`docs/continuity/PROMPT_CONTINUE_CLAUDE.md`](docs/continuity/PROMPT_CONTINUE_CLAUDE.md) holds the latest working state and plan, written to resume development with Claude. If someday you find something new correlated with Sommer and Paxson, give it to Claude and continue.

## License

MIT — see [LICENSE](LICENSE).

**Via Appia Quality** 🏛️ — built to last decades.
