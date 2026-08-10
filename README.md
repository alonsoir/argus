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

- **aRGus** — an embedded ML classifier (the lens the project controls end to end)
- **Suricata** — signature / rule-based detection
- **Zeek** — protocol telemetry (observation, not verdict)
- **Wazuh** — host-based (HIDS) telemetry

The three network sensors emit a `correlation_v1` contract → medallion **gold** (Parquet) → a **Kuzu** graph, correlated across sensors by `community_id` (edge `CORRELATES_FLOW`). Wazuh emits a separate `host_domain_v1` contract into its **own** Kuzu graph.

The sensors are heterogeneous **by design** and complementary, not competitors: one classifies, one detects, one describes, one watches the host. The value of the instrument is characterizing that heterogeneity — the bias of each lens against ground truth — not normalizing it away.

## The honest thesis

This project began as an attempt to build an ML system that classifies network telemetry and acts on it autonomously. It ends as something more useful and less triumphant: **a complete, reproducible forensic record of how a system reporting F1 = 0.9985 on a curated subset was, operationally, carried by a heuristic fast-path with its ML head effectively blind on cross-distribution botnet traffic.**

That is an empirical confirmation, with traces, of what Sommer & Paxson argued in 2010 and Arp et al. in 2022. The failure here was **not** "ML for intrusion detection is impossible" — there is modest real signal (in-sample AUC ≈ 0.746) — it was **distribution transfer** (a model trained on CIC-IDS-2017 collapses to ≈ 0.0001 on CTU-13 Neris). Negative results in security ML are systematically under-published; this repository is the audit almost nobody runs, because there is no incentive to run it.

For critical-infrastructure operators, a blind NDR that gives false confidence is worse than none. Saying so with data is the contribution.

## Results, anchored

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

## Architecture & review

- **Generated documentation** (browsable): https://alonsoir.github.io/argus/
- **Architecture decisions:** `docs/adr/`
- **Living contracts** (Protobuf / JSON / RAG): `docs/contracts/`
- **Writing an attack driver:** [`docs/WRITING-A-DRIVER.md`](docs/WRITING-A-DRIVER.md)
- **Code graph** (Graphify — on-device, Apache-2.0): a graph of the *source code*, distinct from the telemetry graph above. Kept by the author as a maintenance aid; **requires login**: https://app.graphify.com/aironman-labs/
- The design was reviewed across eight independent models — the *Consejo de Sabios* (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) — as structured disagreement. The methodology is documented in §6 of the paper.

## Limitations — known and declared

Honesty as an engineering property, not an afterthought:

- **Research artifact, not production.** The classifier alone (≤ 0.75 at best) cannot autonomously detect or stop DDoS or ransomware. The defensible deliverable is the *pipeline* that leans on multiple sensors to reconstruct what happened after an event on the perimeter it watches.
- **Deferred hardening**, carried as known-and-deferred (not hidden): productive Vault, key rotation, real fault-injection, secure HMAC transport (HTTPS/Vault).
- **Replay fidelity:** 0.47% of the offline-true botnet flows do not reach the replayed wire.
- **Provenance:** the 2011 Neris pcap is third-party, captured under unknown conditions.

## History

The full day-by-day engineering log (DAY 111–252) lives in [`docs/HITOS.md`](docs/HITOS.md). 
It records what was understood on each day; many figures there were later refined or corrected (e.g. F1 = 0.9985 was anchored to the 646-flow behavioral subset). 
It is **not** the current state of the pipeline.

There is a docs/continuity/PROMPT_CONTINUE_CLAUDE.md file with the latest update to Claude. Give it to Claude to resume the development, 
if someday you find something new correlated with Sommer and Paxon.

## License

MIT — see [LICENSE](LICENSE).

**Via Appia Quality** 🏛️ — built to last decades.
