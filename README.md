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

aRGus exists to protect hospitals and civilian critical infrastructure. It is **defensive by design**: it observes, classifies and can block traffic on the perimeter it watches. It has no offensive capabilities — no counter-attack, no active scanning of third parties, no "hack-back" — and it never will. This is a statement of the project's purpose, not a restriction added to the license.

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

### DDoS head v2 — detects, classifies and can stop a DDoS (lab-verified; mitigation off by default)

The DDoS head was rebuilt from scratch and is the **only head trusted to decide** (`final_decision`). The other models are still loaded but do not decide. Since DAY303 the pipeline can, in the lab, **detect a DDoS, classify it and block it at the firewall**, and every one of those steps is checked end to end by the quality gate (see *Quality gate*).

- **Two stages.** Stage 1: per-victim state with hysteresis, computed in the sniffer (cold / normal / under pressure) against the victim's own baseline (`victim_rate_ratio ≥ 3` to enter). Stage 2: a 100-tree Random Forest over 6 flow features, trained only on rows under pressure, exported to C++ with raw thresholds. Python/C++ parity: 127,930 / 127,930.
- **Trained on lab-generated traffic** (a controlled battery of reflection/flood families at several rates), not on a public dataset.
- **Per-victim episodes** (m = 5 DROP per 1 s window, k/n = 3/5 windows to start, 30 windows of hold to end), recorded as START/END.
- **Real mitigation, behind two keys.** With `operation.dry_run = false` **and** `ddos_mitigacion.habilitada = true` in the firewall JSON, the source of an episode is put in an `ipset` with a timeout; each repeated offence raises the penalty (escalation ladder, `recidivism.strike_durations_sec`), and every packet still seen renews the penalty without adding a strike. **Both keys ship off**: out of the box the firewall only records what it would block (`[DDOS-MITIGACION] modo: DESHABILITADA`).
- **Protected ranges.** Sources in the protected ranges of the JSON (DMZ, intranet, critical externals; RFC 1918 + `fc00::/7` by default) are **never blocked**: they raise `ALERTA_PROTEGIDO` instead.

Fixed in the branch merged on DAY303 (measured before and after, see `docs/ml-heads/`):

| Problem (measured before) | After |
|---|---|
| A sustained attack was absorbed into the baseline: marking stopped after ~889 s | the baseline freezes while the victim is under pressure: **99.97%** of a sustained attack marked (was 84.3%), no cut-off |
| Cold start: an empty baseline decided on legitimate traffic, and an attack in progress was learned as normal | victims with no history enter via an absolute threshold (`abs_pps`, 200 by default, calibrated per installation): **0** false passes on 50 pps benign traffic (was 200); a 300 pps attack at startup marked 13,373 / 13,373 |
| A sniffer restart lost the per-victim state | state is persisted (periodic and on stop) and restored: after a clean stop **or a `kill -9`** mid-attack the victim is restored under pressure and marking continues |

Measured end to end in the lab, inside the from-scratch quality gate of DAY303 (production build):

| Measure | Value |
|---|---|
| Restart mid-attack, CSV deleted (control) | restored cold; 0 events marked after the restart, as designed (70 pps < `abs_pps`) |
| Restart mid-attack, clean stop / `kill -9` | restored with 1 victim under pressure; marking continues (after/before ratio 1.397 / 1.378) |
| Detector → firewall accounting | **exact**: marked events = firewall DROP decisions, difference 0 (8,260 / 20,290 / 20,272 in the three restart runs) |
| Protected source (`.61`, intranet) attacking at 30 pps together with the attacker | never blocked; 5,393 `ALERTA_PROTEGIDO`; identity DROP = episode + alerts holds with difference 0 (16,180 = 10,787 + 5,393) |
| Real mitigation (DAY302, two NTP attacks at 60 pps) | the attacker enters the block set **4.5–4.9 s** after the attack starts; the DROP rule drops **92%** of the attack packets (3,312 / 3,348 of 3,600); the second attack escalates the timeout from 60 s to 120 s; the innocent and the protected sources never enter |

Known limits of this head (measured, not hidden):

- **Stage 2 learns the signatures of our traffic generators** (packet size, reflection pattern), not behaviour. With a family left out of training, detection of that family drops to ~0%.
- **The head discriminates the type of traffic, not the sender (measured, DAY297).** A "twin" sending the attacker's exact packets from another address is dropped like the attacker (99.56% / 99.17% of its packets). With mitigation on, that twin would be blocked too. Per-source features are future work — one reason mitigation ships off.
- **Reaction window of ~5 s.** The ~8% of attack packets that get through are the ones sent while detection, episode start and the firewall flush happen. A fast path in XDP (drop before classification) is planned to close it.
- **Below `abs_pps` at cold start**, an attack is learned as baseline (0% marked): the documented cost of never deciding on a victim with no history.
- **Lab only:** VirtualBox VMs on a laptop, rates up to ~110 pps without ring losses; end-to-end accounting at up to 130 pps toward the victim found 0 events lost or duplicated between sniffer and firewall. A 300 pps attack at startup was marked in full, with delivery reordering growing with rate (5.1% at 300 pps vs 0.03% at 60 pps; decision logic unaffected). None of this is real hardware: see [docs/carta_reyes_magos_caceres.md](docs/carta_reyes_magos_caceres.md) for what cannot be measured here.

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

### Quality gate — EMECAS+++, from scratch for real (DAY303)

A merge to `main` is certified by `make emecas+++` with the default production build. On DAY303 it was made to be **from scratch in fact, not only in name**: the repository folder is shared with the VMs and survives `vagrant destroy`, and with it every build directory. Measured that day: the synthetic E2E injectors had not been rebuilt since June, one component was starting a debug binary from April, and the active-profile links pointed to debug builds. No test failed — everything "worked". The gate now:

1. destroys the VMs and **deletes every build directory on the host** before `vagrant up` (`clean-host-builds`);
2. builds everything from zero and **checks freshness**: every pipeline binary must be newer than a stamp written after the VMs are created, and must be the one the active profile points to (validated negatively first: with a later stamp, 8/8 binaries fail);
3. runs all unit and component tests, the firewall's root-only tests (fails on any skipped test) and its performance measurements;
4. runs the **lab E2E tests with strict PASS/FAIL verdicts** derived from the design, not from timing: sniffer restart mid-attack (cold, clean stop, `kill -9`), protected ranges, and real mitigation. The verdicts were validated against earlier, already-judged runs: they accept the four runs that were accepted and reject the one that was rejected;
5. runs the Vault acts (nominal start, rotation through the synthetic pipeline, token revocation).

DAY303 result: **28/28 milestones, rc = 0, 2 h 33 min** on a 2019 laptop.

```bash
nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &
bash scripts/emecas/emecas_watch.sh 60    # progress, VM CPU, stopped/zombie processes, first make error
```

Sanitizer runs (ASan/TSan) are deliberately left for real pre-production hardware.

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

```bash
make up && make bootstrap    # first run ~20–30 min: installs FAISS/ONNX/XGBoost/libsodium
```

### Running the live lab

The Makefile builds the **production** profile by default (`PROFILE ?= production`: `-O3`, LTO, `-march=native`, warnings as errors), so what you test is what would be deployed. `make pipeline-build` builds the whole pipeline and finishes by pointing every `build-active` link at the profile just built; debug, TSan and ASan builds stay available with an explicit `PROFILE=…`.

```bash
make pipeline-build
make test-components
make pipeline-stop
make pipeline-start
make lab-e2e            # the five lab E2E tests with their PASS/FAIL verdicts (~65 min)
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
- **DDoS head, day by day** (Spanish): `docs/ml-heads/` — `day298_etapa1_resultados.md`, `day299_estado_arranque_persistencia.md`, `day300_reinicio_e2e.md`, `day300_parada_y_protegidos.md`, `day303_emecas_desde_cero.md`
- **Writing an attack driver:** [`docs/WRITING-A-DRIVER.md`](docs/WRITING-A-DRIVER.md)
- **Code graph** (Graphify — on-device, Apache-2.0): a graph of the *source code*, distinct from the telemetry graph above. Kept by the author as a maintenance aid; **requires login**: https://app.graphify.com/aironman-labs/
- The design was reviewed across eight independent models — the *Consejo de Sabios* (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) — as structured disagreement. The methodology is documented in §6 of the paper.

## Limitations — known and declared

Honesty as an engineering property, not an afterthought:

- **Research artifact, not production.** Only the DDoS head is trusted to decide. Its real mitigation works in the lab but **ships switched off**; turning it on is an operator's decision, two keys in the JSON. The other heads (ransomware, internal traffic, the original level-1 classifier) are not trusted and do not decide.
- **Lab, not hardware.** Every live measurement comes from VirtualBox VMs on a laptop. Latencies, clock behaviour and the thresholds in the JSON files are lab-calibrated and must be measured again on real hardware. What cannot be measured without hardware (native XDP drop rate, ring saturation, ransomware detection under a real DDoS, upstream defence of the bandwidth) and the equipment that would unlock it are written down in [docs/carta_reyes_magos_caceres.md](docs/carta_reyes_magos_caceres.md) (in Spanish).
- **DDoS head, measured limits:** it discriminates traffic type, not sender (a twin of the attacker would be blocked too); ~5 s reaction window; an attack below `abs_pps` at cold start is learned as baseline. See "Current state" above.
- **Status checks are liveness only.** `pipeline-status` reports a process as RUNNING when it exists, not when it is healthy; measured DAY303: a component (retired DAY304) had not registered with etcd for weeks while showing RUNNING.
- **Single node.** The time contract assumes sensor, detector and firewall on one host. Distributed deployment (PTP-synchronized clocks) is future work.
- **Fast-alerts are not reliable** and are excluded from the bronze contract until they are.
- **Deferred hardening**, carried as known-and-deferred (not hidden): productive Vault, key rotation, secure HMAC transport (HTTPS/Vault), sanitizer runs on real hardware, and a reverse-engineering audit of the shipped binaries.
- **Replay fidelity:** 0.47% of the offline-true botnet flows do not reach the replayed wire.
- **Provenance:** the 2011 Neris pcap is third-party, captured under unknown conditions.

## What comes next

In order, one branch each, each closed by a from-scratch EMECAS+++:

1. **Head switch:** turn each detection head on or off from configuration (etcd), at runtime, with the state reported in the log.
2. **Flow expiry in the sniffer:** flows never expire by inactivity today, which distorts the flow features of long-lived legitimate traffic (memory is bounded; the features are not).
3. **Fast path in XDP:** drop clear attacks before classification, to close the ~5 s reaction window.
4. **Hardening audit of the shipped binaries** (what an attacker gets from a sensor's binary), then as an asynchronous CI stage.
5. The remaining heads (ransomware, lateral movement, generic attacks), **one at a time**, under the same bar as DDoS.

## History

The day-by-day engineering log lives in [`docs/HITOS.md`](docs/HITOS.md) (DAY 111–252) and, for later days, in [`docs/BACKLOG.md`](docs/BACKLOG.md) and the design documents under `docs/`. They record what was understood on each day; many figures there were later refined or corrected (e.g. F1 = 0.9985 was anchored to the 646-flow behavioral subset). They are **not** a description of the current state of the pipeline — this README is.

[`docs/continuity/PROMPT_CONTINUE_CLAUDE.md`](docs/continuity/PROMPT_CONTINUE_CLAUDE.md) holds the latest working state and plan, written to resume development with Claude. If someday you find something new correlated with Sommer and Paxson, give it to Claude and continue.

## License

MIT — see [LICENSE](LICENSE).

**Via Appia Quality** 🏛️ — built to last decades.
