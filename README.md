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

**After the paper**, the work continues in the same spirit: the detection heads are being rebuilt **one at a time**, each with a measured contract, lab-generated training data and a written prediction before every measurement. Only a head that passes that bar is allowed to make decisions. Today that is **one head: DDoS** (see *Current state*). In parallel, the pipeline's own control plane — how components authenticate, where keys live, who may decide what is never blocked — is being hardened under the same rule: measured, written down, and certified from scratch.

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

Releases since the paper, each one a branch closed by a from-scratch quality gate and tagged on its merge commit:

| Tag | What changed |
|---|---|
| `pre-release-ddos-mitigation-0.0.4` | DDoS head v2 can detect, classify and block a DDoS in the lab (mitigation off by default) |
| `pre-release-rag-retired-0.0.5` | RAG subsystem retired (rag-security, rag-ingester, llama.cpp, FAISS): a 4-component pipeline |
| `pre-release-heads-switch-0.0.6` | head switch; the sniffer only collects features and runs the fast-path, inference lives only in the ML detector |
| `pre-release-ddos-v1-retired-0.0.7` | DDoS v1 retired: `ddos_v2` is the only DDoS head |
| `pre-release-flow-expiry-0.0.8` | the sniffer expires flows, with fixed-size per-flow state |
| `pre-release-rag-logger-retire-0.0.9` | RAG Logger and CsvEventWriter out; the bronze HMAC key comes from the etcd-server |
| `pre-release-etcd-mtls-vault-0.0.10` | control plane over mTLS, keys in Vault, signed manifest of protected ranges, host surveillance (below) |

### Control plane — mTLS, keys in Vault, a signed manifest of protected ranges (DAY312–323)

The pipeline's control plane (registration, heartbeats, configuration and keys) used to be plain HTTP on the same host as the sensor, with the HMAC key of the bronze travelling in clear. It now lives on its own machine and every call is authenticated. Design and decisions: [ADR-060](docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md) and [`docs/ml-heads/day312_diseno.md`](docs/ml-heads/day312_diseno.md) (both in Spanish).

- **Its own VM.** The etcd-server runs on the `etcd` VM (`192.168.100.20`) as a systemd service, next to a real etcd (3.6, gRPC + TLS, RBAC) and a Vault server. Nothing listens on 2379 on the defender any more. The service comes back by itself after a reboot, and Vault starts and unseals without Vagrant (with its own unseal identity).
- **HTTPS + mutual TLS everywhere.** Sniffer, ML detector and firewall talk to the etcd-server over mTLS with a client certificate each, through one shared client library with a list of 1–7 endpoints (no answer or 5xx → next endpoint; 4xx → final answer). Authorization is per (OU, CN), from a table in the server's JSON. Without a certificate, or with one from another CA, there is no HTTP answer at all.
- **HMAC keys in Vault**, never in clear: kv v2 with `cas_required=true`, an immutable key per fingerprint and a two-key window updated with compare-and-set. A component can only fetch its own key (`/secrets/<CN>`). With Vault down the server keeps serving the last window with both its keys; without it, 503 — never a key that was not stored first. The firewall checks its key periodically with the same cases as the ML detector (no key, extended mode, confirmed, changed, recovered).
- **Components do not depend on the control plane to protect.** They start without the etcd-server, register (or resume their heartbeat) when it comes back, and upload their start-up JSON. Measured: restarting the etcd-server with the pipeline live and benign traffic keeps the same bronze key fingerprint, creates no new registration, heartbeats stay 200, and every bronze segment of the interval verifies with the key from before and from after.
- **A signed manifest of protected ranges, one per hospital** (ADR-060). The lists of sources that aRGus must never block used to live in each firewall's JSON — N copies of the truth, any of which grants full immunity. They now come from a single manifest per hospital, with four categories (`infraestructura` — aRGus' own control plane and sensors —, `intranet`, `dmz`, `externos_criticos`), narrow entries (`cidr`, mandatory interface, optional MAC, reason) and per-category prefix limits (`/32`/`/128` for infrastructure). It is signed with **Ed25519 in Vault transit** (non-exportable key per hospital); the public key is **compiled into the firewall** (two slots, to rotate without leaving firewalls unable to verify) and into the etcd-server, which also verifies before storing. Versions only grow (anti-rollback, also across restarts); undoing means re-signing old content as a new version. The firewall verifies the signature, the hospital, its own floor and the limits, applies atomically (`ipset swap`), logs `[INFRA-CAMBIO]` with signer and diff, keeps a signed cache on disk to start without etcd, and keeps the last verified set if a new one fails. **Real mitigation only takes effect with a verified manifest**: without it the firewall stays in shadow and says so periodically.
- **`argus-infra`**, the admin tool (a single Python file, standard library only): `init`, `list`, `add`, `del`, `diff`, `verificar`, `deshacer N`. It signs with the admin's own Vault identity, from an authorized CIDR, recorded by Vault's audit device. It is a separate role from day-to-day administration (`admin`, which rotates HMAC keys and cannot sign): measured, `argus-infra` gets 403 reading, rotating or exporting HMAC keys, and the etcd-server gets 403 signing. In the lab it lives on the `etcd` VM and the bootstrap provisions the manifest with it.
- **Watched "like hawks".** The firewall compares the kernel's protected set with the manifest every N seconds (any divergence is an alarm and is reconciled); drops spoofed sources in `raw PREROUTING`, one rule per entry generated from the manifest (a protected source arriving on the wrong interface or with the wrong MAC), with counters and sample packets; reports the applied manifest version in its heartbeat and in `pipeline-status`. **Falco** (on the defender and the `etcd` VM) and **Wazuh** agents (file integrity of configuration, PKI and binaries on both machines; Vault errors, including audit-device failures; disk usage of the audit partition; the firewall's log) report to the Wazuh manager. All third-party software (Wazuh, Falco, Jenkins) is installed from its maintainer's signed apt repository, with a pinned version and the key checked by fingerprint.
- **`pipeline-status` shows real state** for the control plane: etcd-server (systemd and `/health`), each etcd member (healthy, leader, term, lag) and each Vault node. Components on the defender are still checked as processes only.

Why the manifest exists, measured (DAY317): with all VMs up for the first time, the DDoS head put the `etcd` VM's NTP client queries into an NTP-reflection episode against the defender. In shadow mode nothing happened; with real mitigation, the first NTP DDoS would have blocked the whole control plane for an hour — a self-inflicted DoS. The quality gate caught it, and its verdict was made stricter, not looser.

### DDoS head v2 — detects, classifies and can stop a DDoS (lab-verified; mitigation off by default)

The DDoS head was rebuilt from scratch and is the **only head trusted to decide** (`final_decision`). Since DAY303 the pipeline can, in the lab, **detect a DDoS, classify it and block it at the firewall**, and every one of those steps is checked end to end by the quality gate (see *Quality gate*).

- **Two stages.** Stage 1: per-victim state with hysteresis, computed in the sniffer (cold / normal / under pressure) against the victim's own baseline (`victim_rate_ratio ≥ 3` to enter). Stage 2: a 100-tree Random Forest over 6 flow features, trained only on rows under pressure, exported to C++ with raw thresholds. Python/C++ parity: 127,930 / 127,930.
- **Trained on lab-generated traffic** (a controlled battery of reflection/flood families at several rates), not on a public dataset.
- **Per-victim episodes** (m = 5 DROP per 1 s window, k/n = 3/5 windows to start, 30 windows of hold to end), recorded as START/END.
- **Real mitigation, behind two keys and a signature.** With `operation.dry_run = false` **and** `ddos_mitigacion.habilitada = true` in the firewall JSON, **and a verified protected-ranges manifest**, the source of an episode is put in an `ipset` with a timeout; each repeated offence raises the penalty (escalation ladder, `recidivism.strike_durations_sec`), and every packet still seen renews the penalty without adding a strike. **Both keys ship off**: out of the box the firewall only records what it would block (`[DDOS-MITIGACION] modo: DESHABILITADA`).
- **Protected ranges** come from the signed manifest (see *Control plane*): sources in it are **never blocked** and raise `ALERTA_PROTEGIDO`, counted per category. The old lists in the firewall JSON and the RFC 1918 + `fc00::/7` default are gone.

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

Since DAY323 the protected-ranges verdict is stricter and derived from the manifest the firewall actually applies: the episode's sources must be the attacker only, every entry of the deployment template must be present, and alerts are accounted per category.

Known limits of this head (measured, not hidden):

- **Stage 2 learns the signatures of our traffic generators** (packet size, reflection pattern), not behaviour. With a family left out of training, detection of that family drops to ~0%.
- **The head discriminates the type of traffic, not the sender (measured, DAY297).** A "twin" sending the attacker's exact packets from another address is dropped like the attacker (99.56% / 99.17% of its packets). With mitigation on, that twin would be blocked too. Per-source features are future work — one reason mitigation ships off.
- **Legitimate traffic to the victim joins the episode (measured, DAY323).** During a UDP attack on the defender, the sensors' NTP queries to the same host entered the episode, one event per sensor. Outside shadow mode, a client that only asked for the time or a name could be blocked. In the lab the sensors are now protected infrastructure; the model defect itself is open (DEBT-DDOS-COLATERAL-LEGITIMO-001: first measure what the model sees; benign service traffic in training and a per-source evidence threshold are the expected fixes).
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

**One clock for the lab (DAY323).** Each sensor VM used to take its time from a different Internet NTP server, and the VMs drift 2,000–4,600 ppm (3–7 minutes a day) without NTP. Now every VM takes its time from the defender, the provisioning fails if a VM's source is not the defender, and `mitre-check` realigns and checks the clocks of the VMs in its run before it starts.

### Data quality

- The Parquet validator now checks **every row**, not just the first one. Doing so revealed that 89% of the rows of the historical ML-detector Parquet (from 2026-03-08) carried timestamps in the wrong clock base; that data was discarded.
- **Fast-alerts are excluded from the `correlation_v1` bronze** (`correlation_writer.include_fast_alerts = false`) until they are reliable: they carry no flow start time and fire roughly once per DNS packet.
- **The bronze HMAC key** is fetched over mTLS from the etcd-server, which keeps it in Vault; the drivers (`mitre-start`, `ctu-start`, custom drivers) fetch it with the converter's own certificate.
- **A session's graph holds only that session's data (DAY323).** `mitre-start` used to copy Suricata's whole `eve.json` (a run passed with the previous day's alerts) and lost Zeek's sweep when the hourly rotation fell mid-run. It now cuts every sensor's bronze to one window [T0, T1] of the defender's clock, row by row (the per-row HMAC still verifies), harvests Zeek after its archiving finishes, and every step checks its result: a FATAL can no longer end in `rc=0`. `ctu-start` still has the old pattern (DEBT-CTU-START-VENTANA-001).

### Quality gate — EMECAS+++, from scratch for real

A merge to `main` is certified by `make emecas+++` with the default production build. On DAY303 it was made to be **from scratch in fact, not only in name**: the repository folder is shared with the VMs and survives `vagrant destroy`, and with it every build directory. Measured that day: the synthetic E2E injectors had not been rebuilt since June, one component was starting a debug binary from April, and the active-profile links pointed to debug builds. No test failed — everything "worked". The gate now:

1. destroys the VMs and **deletes every build directory on the host** before `vagrant up` (`clean-host-builds`), then brings up **the production topology, all six VMs** (defender, client, suricata, zeek, wazuh, etcd): a subset hides faults that only the topology shows (the DAY317 self-inflicted DoS did not exist with two VMs);
2. builds everything from zero and **checks freshness**: every pipeline binary must be newer than a stamp written after the VMs are created, and must be the one the active profile points to (validated negatively first: with a later stamp, 8/8 binaries fail);
3. deploys the etcd-server to its VM, bootstraps the signed manifest with `argus-infra`, and runs all unit and component tests, the firewall's root-only tests (fails on any skipped test) and its performance measurements, the `argus-infra` tests and the Wazuh rule tests;
4. runs the **lab E2E tests with strict PASS/FAIL verdicts** derived from the design, not from timing: sniffer restart mid-attack (cold, clean stop, `kill -9`), protected ranges (P1–P6), real mitigation, the kernel ↔ manifest watcher, anti-spoofing, the manifest version in the heartbeat, host surveillance (Falco and Wazuh alerts arriving at the manager) and an etcd-server restart with the pipeline live;
5. runs the Vault acts (nominal start, rotation through the synthetic pipeline, token revocation);
6. drives the live MITRE attack through aRGus, Suricata and Zeek to the graph, and **requires attack rows from every sensor inside the session window**, invariant 0 and corroborated flows > 0.

Result for `pre-release-etcd-mtls-vault-0.0.10` (DAY323, merge of PR #153): **PASS, rc = 0, 4 h 02 min** on a 2019 laptop. `mitre-check`: aRGus 1,777 events in the graph (1,253 from the attack, in the window), Suricata 31 (31), Zeek 1,114 (1,068), invariant 0, 1,080 corroborated flows. It took four from-scratch runs that day; each stop had its cause measured, its fix tested on its own and its commit (Suricata running with its factory configuration, blind: wrong interface and 0 signatures; one clock per sensor; a MITRE window that mixed days; Jenkins' apt key; the sensors' NTP inside the DDoS episode). None was visible without a from-scratch run.

```bash
nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &
bash scripts/emecas/emecas_watch.sh 60    # progress, VM CPU, stopped/zombie processes, first make error
make emecas-progreso                      # per-step progress and % (from the stored step times)
```

Each run keeps a `resumen.md` and one log per step under `logs/lab/emecas/`. Sanitizer runs (ASan/TSan) are deliberately left for real pre-production hardware.

## Reproduce the paper

The reproducibility baseline is **from scratch** — a clean VM (`vagrant destroy -f && vagrant up`, or just `make up` on a fresh clone), keys regenerated, every binary built from zero — so the claim is "reproducible", not "reproducible on my machine". Every figure in the paper is regenerable by a command, and the exact figures of the anchored run sit in [`paper-artifacts/`](paper-artifacts/) for reviewers who would rather read than run.

**One command, from a clean checkout:**

```bash
make up && make bootstrap     # 6 VMs + full pipeline, built and started (measured from scratch: ~55 min + ~38 min)
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
make up && make bootstrap    # first run ~1.5 h from scratch: six VMs, ONNX/XGBoost/libsodium, Vault, etcd, Wazuh, Falco
```

**Memory:** the six VMs use about 19 GB of RSS; 32 GB on the host is the measured working size.

### Running the live lab

The Makefile builds the **production** profile by default (`PROFILE ?= production`: `-O3`, LTO, `-march=native`, warnings as errors), so what you test is what would be deployed. `make pipeline-build` builds the whole pipeline and finishes by pointing every `build-active` link at the profile just built; debug, TSan and ASan builds stay available with an explicit `PROFILE=…`.

```bash
make pipeline-build
make test-components
make pipeline-stop
make pipeline-start
make pipeline-status    # components, and the real state of etcd-server, etcd members and Vault
make lab-e2e            # every lab E2E test with its PASS/FAIL verdict (restarts, protected ranges,
                        # mitigation, watcher, anti-spoofing, heartbeat, surveillance, etcd-server restart)
```

If the host sleeps (e.g. the laptop is suspended), the VMs freeze and their wall clocks fall behind; chrony may take a couple of minutes to notice. Realign the lab clocks as soon as the host wakes up, before measuring:

```bash
make lab-clock-step                                  # defender, then client
make lab-clock-step LAB_CLOCK_VMS="client suricata zeek"
# fails if a VM's source is not the defender (192.168.100.1) or its offset stays ≥ 1 ms
```

Component configuration lives in each component's JSON (`*/config/*.json`): every field documents its format and limits, and a missing or invalid field falls back to a validated default with a `[CONFIG-DEFAULT]` warning while the component keeps running. The exception is what has no safe default: the etcd-server's store endpoints in etcd mode, and `argus-infra`'s Vault, etcd-server and TLS settings, refuse to start without them.

## Architecture & review

- **Generated documentation** (browsable): https://alonsoir.github.io/argus/
- **Architecture decisions:** `docs/adr/` — the latest, [ADR-060](docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md), the signed manifest of protected ranges (Spanish)
- **Control plane (mTLS, Vault, etcd), day by day:** [`docs/ml-heads/day312_diseno.md`](docs/ml-heads/day312_diseno.md) (Spanish)
- **Living contracts** (Protobuf / JSON / RAG): `docs/contracts/`
- **Time contract v1:** [`docs/timebase/contrato_temporal_day295.md`](docs/timebase/contrato_temporal_day295.md) (Spanish; §8 holds the measurements)
- **DDoS head, day by day** (Spanish): `docs/ml-heads/` — `day298_etapa1_resultados.md`, `day299_estado_arranque_persistencia.md`, `day300_reinicio_e2e.md`, `day300_parada_y_protegidos.md`, `day303_emecas_desde_cero.md`
- **Writing an attack driver:** [`docs/WRITING-A-DRIVER.md`](docs/WRITING-A-DRIVER.md)
- **Code graph** (Graphify — on-device, Apache-2.0): a graph of the *source code*, distinct from the telemetry graph above. Kept by the author as a maintenance aid; **requires login**: https://app.graphify.com/aironman-labs/
- The design was reviewed across eight independent models — the *Consejo de Sabios* (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) — as structured disagreement. The methodology is documented in §6 of the paper.

## Limitations — known and declared

Honesty as an engineering property, not an afterthought:

- **Research artifact, not production.** Only the DDoS head is trusted to decide. Its real mitigation works in the lab but **ships switched off**; turning it on is an operator's decision, two keys in the JSON plus a verified manifest. The other heads (ransomware, internal traffic, the original level-1 classifier) are not trusted and do not decide.
- **Lab, not hardware.** Every live measurement comes from VirtualBox VMs on a laptop. Latencies, clock behaviour and the thresholds in the JSON files are lab-calibrated and must be measured again on real hardware. What cannot be measured without hardware (native XDP drop rate, ring saturation, ransomware detection under a real DDoS, upstream defence of the bandwidth) and the equipment that would unlock it are written down in [docs/carta_reyes_magos_caceres.md](docs/carta_reyes_magos_caceres.md) (in Spanish).
- **DDoS head, measured limits:** it discriminates traffic type, not sender (a twin of the attacker would be blocked too); legitimate traffic to the victim can join the episode; ~5 s reaction window; an attack below `abs_pps` at cold start is learned as baseline. See "Current state" above.
- **Control plane on a single node.** One etcd member, one Vault server, one etcd-server, all on the `etcd` VM. High availability (≥ 3 etcd nodes, Vault HA, their Ansible) is the next branch. In the lab, Vault is unsealed automatically and `argus-infra` runs on the `etcd` VM, which plays the admin machine (no RAM for one more VM): development simplifications, written down.
- **What the manifest does not solve.** Root on the defender through a kernel vulnerability defeats everything (it can replace the binary); the goal is that it cannot do so silently. A protected address is never blocked by aRGus, even when spoofed: off-interface spoofing is dropped, same-segment spoofing is only stopped by the MAC when the entry carries one; spoofing third parties' addresses cannot be solved at the hospital's edge. No two-person rule for signing yet.
- **Status checks.** `pipeline-status` reports the real state of the control plane, but the components on the defender are still liveness only (RUNNING when the process exists, not when it is healthy).
- **Single-node time contract.** The time contract assumes sensor, detector and firewall on one host. Distributed deployment (PTP-synchronized clocks) is future work.
- **Fast-alerts are not reliable** and are excluded from the bronze contract until they are.
- **Deferred hardening**, carried as known-and-deferred (not hidden): HA of the control plane, sanitizer runs on real hardware, a reverse-engineering audit of the shipped binaries, and the remaining supply-chain origins (Jenkins' JDK via SDKMAN, libsodium, the provenance of etcd's checksum). The Vault acts of the quality gate still run a dev Vault on the defender (DEBT-VAULT-ENTERPRISE-SMOKE-VM-001).
- **Replay fidelity:** 0.47% of the offline-true botnet flows do not reach the replayed wire.
- **Provenance:** the 2011 Neris pcap is third-party, captured under unknown conditions.

## What comes next

In order, one branch each, each closed by a from-scratch EMECAS+++:

1. **High availability of the control plane** (PR2, in small PRs): ≥ 3 etcd nodes (one node down, re-election, time to resynchronize; all down and back one by one), Vault in HA, the number of nodes in the inventory and `etcd.conf.yml` generated from it.
2. **A slimming diet:** deprecated code out, and a vulnerability scan of the dependencies (Trivy).
3. **The remaining supply-chain origins** (touches Jenkins and needs its own gate).
4. **Fast path in XDP:** drop clear attacks before classification, to close the ~5 s reaction window.
5. **Hardening audit of the shipped binaries** (what an attacker gets from a sensor's binary), then as an asynchronous CI stage.
6. The remaining heads (ransomware, lateral movement, generic attacks), **one at a time**, under the same bar as DDoS — and, for DDoS, per-source features and legitimate service traffic in training.

## History

The day-by-day engineering log lives in [`docs/HITOS.md`](docs/HITOS.md) (DAY 111–252) and, for later days, in [`docs/BACKLOG.md`](docs/BACKLOG.md) and the design documents under `docs/`. They record what was understood on each day; many figures there were later refined or corrected (e.g. F1 = 0.9985 was anchored to the 646-flow behavioral subset). They are **not** a description of the current state of the pipeline — this README is.

[`docs/continuity/PROMPT_CONTINUE_CLAUDE.md`](docs/continuity/PROMPT_CONTINUE_CLAUDE.md) holds the latest working state and plan, written to resume development with Claude. If someday you find something new correlated with Sommer and Paxson, give it to Claude and continue.

## License

MIT — see [LICENSE](LICENSE).

**Via Appia Quality** 🏛️ — built to last decades.
