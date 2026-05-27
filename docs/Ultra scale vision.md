# **Executive Technical Summary — UltraScale DDoS Defense (TB/s Architecture)**

**ML Defender — Distributed High-Throughput Architecture for TB/s Attacks**

---

## **1. Paradigm Shift: From Per-Event Inspection to Flow Aggregation**

The current ML Defender pipeline performs deep, high-fidelity inspection of individual events with 83-field telemetry. This is ideal for malware, targeted intrusions, and advanced evasion patterns.

However, **volumetric DDoS attacks at 100G → 400G → 1 Tbps** fundamentally break any per-packet inspection model. Full packet analysis is computationally and memory infeasible at these scales.

**Core principle:**

> “We no longer inspect each packet. We extract minimal metadata at line rate, aggregate traffic in real-time windows, and detect attacks by their macroscopic signatures.”

This requires a complete shift from:

* microscale → **macroscale**
* packets → **flows**
* per-event ML → **windowed/aggregated ML**
* kernel-bound pipelines → **kernel-bypass DPDK sensors**
* single-node analytics → **distributed clusters**

---

## **2. UltraScale Architecture Principles**

### **2.1 Kernel Bypass + Direct NIC Ownership (DPDK)**

Linux kernel networking (even with eBPF/XDP) cannot sustain Tbps analysis. Hardware bypass is mandatory.

**Key technologies:**

* **DPDK** for user-space packet IO at 100G+/core.
* **DMA-based NIC access** without kernel involvement.
* **SR-IOV NIC virtualization** to shard traffic across cores or processes.
* **SmartNICs / DPUs** (ARM/FPGA/ASIC-based NIC accelerators):

    * Capable of filtering, sampling, and even aggregating before the host CPU sees the packets.

**Hardware baseline per sensor node:**

* 1× or 2× **100G/200G/400G NICs**
* High-core-count CPUs (AMD EPYC recommended)
* Optional SmartNIC/DPU for pre-offload

---

### **2.2 Minimal Metadata Extraction at Line Rate**

Under TB/s load, 99.999% of packets are “noise” from the attack. Storage, parsing, or even serializing them is impossible.

**DPDK sensor tasks:**

1. Capture packets at 100G+ per queue.
2. Extract minimal L2–L4 metadata:

    * 5-tuple
    * timestamp
    * TCP flags
    * packet length
3. Discard payload immediately.
4. Emit these metadata events into a **high-throughput bus**:

    * **Kafka**
    * **NATS JetStream**
    * **Redpanda**

This allows millions of events/second per node.

---

### **2.3 Distributed Aggregation and Sliding Windows**

A single server cannot process TB/s metadata. The architecture relies on horizontal distribution:

**Distributed roles:**

* **Sensors (DPDK)**: Raw metadata extraction
* **Aggregators (Cluster)**:

    * Build flow records (x per 100–500ms window)
    * Compute statistical profiles:

        * pps, bps
        * SYN/FIN/RST ratios
        * entropy of source IPs
        * packet-size distribution
        * top-K source concentration
        * rolling deltas

Aggregators reduce billions of packets per minute into **a few thousand aggregated vectors**.

---

### **2.4 ML Evolution: From Event Features to Window-Based Signatures**

Phase 1 ML models use 83 fields from individual events. UltraScale requires aggregated vectors per target/destination.

**New ML Inputs (example window vector):**

```
[dst_ip, pps_last_100ms, bps_last_100ms,
 unique_sources, src_entropy,
 syn_ratio, rst_ratio, fin_ratio,
 avg_pkt_size, pkt_size_stddev,
 small_pkt_fraction, large_pkt_fraction,
 top1_src_concentration, top10_concentration,
 window_slope, ...]
```

**ML tasks:**

* Classification (SYN flood, UDP flood, amplification attacks)
* Anomaly detection
* Signature matching with RAG (Mirai variants, DNS amplification patterns, etc.)

Models: lightweight tree ensembles, shallow neural nets, anomaly autoencoders.

Targets:

* > 95% detection for main attack families
* <0.5% FPR per window
* <300ms time-to-detect

---

### **2.5 Mitigation & Control Plane**

Once detection is established, mitigation must be automated:

**Control-plane components:**

* ETCD (state/coordination)
* Orchestrator (policy application)
* Firewall API
* BGP controller (ExaBGP/FRR)
* Scrubbing center integration

Mitigation chain:

1. Soft rate-limits
2. Per-IP or subnets drops
3. BGP blackholing for catastrophic events
4. Traffic diversion to scrubbing

---

## **3. Candidate Architectures**

### **A. DPDK Sensor + Aggregator (Recommended)**

* Portable, widely supported
* Predictable performance
* Easiest incremental integration with current system

### **B. SmartNIC / DPU Offload**

* Offload heavy lifting to BlueField/Pensando/Intel IPU
* Lower host CPU requirements
* Higher cost, vendor lock-in risk

### **C. FPGA Inline Prefilter**

* Maximum performance
* Deterministic hardware behavior
* Slow development cycles

### **D. Hybrid eBPF + DPDK**

* DPDK for bulk/meta
* eBPF/XDP for sampled deep inspection
* Best of both worlds for forensics

---

## **4. Software Components (UltraScale)**

* **DPDK Capture Service** (C++20)
* **Metadata Bus** (Kafka/NATS JetStream)
* **Aggregation Workers** (C++/Rust)
* **Windowed ML Detector** (existing engine adapted)
* **Orchestrator + ETCD** (policy/state)
* **Mitigation Engine** (firewall/BGP)
* **Observability** (Prometheus/Grafana/tracing)
* **Forensic Snapshotter** (optional full capture on flagged flows)

---

## **5. ML Datasets & Training Strategy**

Since collecting TB/s real attack data is difficult, synthetic generation is mandatory:

* Use **TRex** or **MoonGen** for large-scale synthetic DDoS traffic.
* Generate attack families:

    * SYN/ACK floods
    * UDP floods
    * DNS/NTP amplification
    * HTTP floods
    * Mixed-vector attacks
* Simulate millions of flows and variable windows.
* Validate with limited real-world samples (CTU-13, MAWI, CAIDA, ISP partners).

---

## **6. Testing & Validation Pipeline**

**Phase tests:**

1. Single-node DPDK → >10 Mpps sustained
2. Multi-node 10–20 Gbps distributed ingestion
3. ML accuracy tests across synthetic scenarios
4. End-to-end mitigation tests
5. ISP-grade simulation: 100G → 400G → 1Tbps (cloud lab)

Tools: TRex, MoonGen, custom packet replayers.

---

## **7. Risks & Mitigations**

| Risk                 | Mitigation                                           |
| -------------------- | ---------------------------------------------------- |
| High hardware cost   | Stage procurement, hybrid cloud scrubbing            |
| DPDK/FPGA complexity | Incremental dev, strong interfaces                   |
| False positives      | Stage mitigation levels; probability-based decisions |
| Vendor lock-in       | Prefer DPDK path first; SmartNIC optional            |
| Scaling overhead     | Strict window size limits, parallel sharding         |

---

## **8. Incremental Roadmap**

### **Phase 2 — Production Hardening (0–30 days)**

* Finalize FAISS, ETCD client, hot-reload, RAG refinements.

### **Phase 3 — DPDK Port (30–90 days)**

* Port sniffer to DPDK.
* Rebuild ring-consumer using DPDK queues.
* Achieve >10 Mpps on 100G NIC in lab.

### **Phase 4 — Distributed Prototype (90–150 days)**

* Deploy 2–4 sensors + 2 aggregators + detector.
* Run 10–20 Gbps synthetic DDoS tests.

### **Phase 5 — ML Evolution (150–240 days)**

* Train windowed ML models.
* Add RAG signature library.
* Target >95% classification accuracy.

### **Phase 6 — ISP-Scale Tests (240–360 days)**

* Test 100–400G multi-node ingest.
* Prepare procurement, runbooks, and deployments.

Total timeline to first TB/s-capable prototype: **~12 months** (with funding and hardware).

---

## **9. Strategic Relevance**

This architecture is aligned with EU needs:

* Sovereign, on-premises, high-throughput defense
* Independence from US hyperscalers
* Alignment with NIS2, DORA, EU Cyber Resilience Act
* First candidate for “European Cloudflare-class” capability

---

## **10. Conclusion**

ML Defender Phase 1 established a scientifically solid, low-latency IDS pipeline capable of detecting real malware using synthetic training. UltraScale expands this foundation into a distributed, kernel-bypass DDoS defense designed for **100G → 400G → 1Tbps** threats.

The architecture combines:

* DPDK sensors
* distributed aggregators
* window-based ML
* SmartNIC acceleration (optional)
* automated mitigation
* forensic retention

…while remaining incrementally compatible with today’s pipeline.

This summary encapsulates both Qwen’s contributions and my own to provide a unified strategic document for review by parallels.ai.

Parallels.ai

# Building a Cloudflare-Class Shield: DPDK-Powered TB/s DDoS Defense for a Sovereign EU

## Executive Summary

The 'UltraScale DDoS Defense' architecture represents a fundamental strategic pivot required to defend against modern, terabit-per-second (Tbps) volumetric attacks. As multi-terabit attacks become a reality, traditional per-packet inspection models are no longer computationally or economically viable [executive_summary[0]][1]. This report outlines a new paradigm: a distributed, kernel-bypass architecture that moves from microscale packet analysis to macroscale flow aggregation. By doing so, it transforms billions of packets per minute into a few thousand manageable feature vectors, making machine learning-based detection tractable and enabling automated mitigation within **300 milliseconds**.

This architecture is not merely a technical upgrade; it is a strategic imperative for achieving digital sovereignty. It provides a blueprint for a 'European Cloudflare-class' defense capability, aligning with critical EU regulations like NIS2, DORA, and the Cyber Resilience Act, thereby reducing reliance on non-EU hyperscalers for infrastructure protection [strategic_relevance_and_eu_alignment.strategic_positioning[0]][2]. The plan is ambitious but feasible, with a detailed 12-month roadmap to a prototype capable of handling **100G to 1 Tbps** threats.

### Kernel Bypass Unlocks 8x CPU Efficiency, Making Tbps Scale Possible

The physics of high-speed networking reveal a critical bottleneck: a standard Linux kernel requires 4-8 CPU cores to saturate a 100 Gbps link, whereas a user-space Data Plane Development Kit (DPDK) approach can achieve the same line rate on a single core [architectural_principles.0.description[0]][3]. This **4-8x efficiency gain** is the cornerstone of the UltraScale architecture. It mandates a hardware bypass approach, moving packet I/O out of the kernel to sustain analysis at Tbps speeds. This principle allows for the reservation of powerful, high-core-count CPUs (like AMD EPYC) exclusively for high-performance sensor nodes, while control plane tasks can run on less demanding hardware.

### Flow Aggregation Slashes Data Volume by 99.9999%

At Tbps scale, 99.999% of packets are attack noise, making full capture impossible. The paradigm shift to flow aggregation is the solution. By extracting only minimal L2-L4 metadata at line rate and processing it in short, 100-500ms sliding windows, the architecture achieves a data compression ratio of approximately 1,000,000:1. Billions of packets per minute are collapsed into a few thousand statistical vectors. This dramatic data reduction makes storage, observability, and, most importantly, real-time machine learning not only possible but efficient, as analysis can occur in memory with sub-300ms latency.

### Metadata Bus Choice is a Critical SLA Decision

The performance of the metadata bus—the system's central nervous system—directly dictates the detect-to-mitigate Service Level Agreement (SLA). While options like Kafka are known for high throughput, their tail latencies can be a critical weakness. Benchmarks show Kafka's p99.99 latency can spike to over **5 seconds** at 1 GB/s, whereas Redpanda remains at least **10x faster** and requires half the nodes (3 vs. 6) for the same workload. NATS JetStream offers the lowest latency for lightweight messaging but is not designed for high-throughput data firehoses. The strategic choice is to default to Redpanda for its balance of throughput and predictable low latency, ensuring the system can meet its aggressive response time targets.

### Staged Mitigation Is Essential to Prevent 'Lethal' Collateral Damage

A high false-positive rate (FPR) in a Tbps environment can be as damaging as the attack itself. An FPR of just **0.5%** on a 1 Tbps attack would result in **5 Gbps** of legitimate traffic being dropped—enough to cripple smaller downstream links. To counter this, the architecture mandates a staged, automated mitigation chain. Responses must begin with "soft" actions like rate-limiting and only escalate to surgical per-IP/subnet drops (via BGP FlowSpec) and finally to BGP blackholing for catastrophic events [automated_mitigation_control_plane.staged_mitigation_chain[0]][4]. This tiered approach, governed by policies stored in ETCD, minimizes collateral damage and preserves service availability for legitimate users.

## 1. Why Current IDS Dies Beyond 100 G

The foundational premise of traditional Intrusion Detection Systems (IDS) and firewalls—deep, stateful inspection of every packet—is fundamentally broken by the scale of modern volumetric DDoS attacks. While this high-fidelity analysis is effective for detecting complex malware or targeted intrusions, it becomes computationally and economically infeasible when faced with traffic floods scaling from **100 Gbps to 400 Gbps and ultimately 1 Tbps**.

The standard kernel network stack is simply not designed for this level of throughput. As network interface card (NIC) speeds exceed 200 Gbps, the time between consecutive 1500-byte packets shrinks to as low as 60 nanoseconds, a rate the kernel cannot sustain [paradigm_shift[1]][3]. Even with modern optimizations like eBPF/XDP, the overhead of kernel-space processing creates an insurmountable bottleneck. Performance benchmarks show that saturating a 100 Gbps NIC with kernel-based networking can require 4 to 8 CPU cores. In contrast, a raw DPDK implementation, which bypasses the kernel entirely, can achieve the same line rate on a single dedicated core [architectural_principles.0.description[0]][3]. This stark difference illustrates that any system reliant on per-packet inspection in the kernel is destined to fail, leading to dropped packets, missed detections, and ultimately, service failure. A new paradigm is not just an improvement; it is a physical necessity.

## 2. Paradigm Shift to Flow Aggregation

To survive terabit-scale attacks, the architecture must undergo a complete paradigm shift, moving from the microscale inspection of individual packets to the macroscale analysis of aggregated traffic flows [paradigm_shift[0]][5]. The core principle is to abandon the impossible task of inspecting every byte and instead focus on the statistical signatures of the overall traffic.

> “We no longer inspect each packet. We extract minimal metadata at line rate, aggregate traffic in real-time windows, and detect attacks by their macroscopic signatures.”

This shift is not an incremental change but a complete re-architecting of the data pipeline and analytical approach. It involves moving from packets to flows, from per-event ML to windowed ML, and from single-node analytics to distributed clusters.

### 2.1 Sliding-Window Math Behind 10^6× Compression

The key to making Tbps-scale analysis tractable is aggressive, real-time data reduction. The architecture achieves this through a process of distributed aggregation within short, sliding time windows (typically **100–500 ms**). DPDK-powered sensors at the edge do not store or forward full packets. Instead, they extract only essential L2-L4 metadata (e.g., 5-tuple, packet length, TCP flags) and immediately discard the payload.

This stream of minimal metadata is consumed by a cluster of aggregator workers. These workers build statistical profiles of the traffic, computing metrics like packets per second (pps), bits per second (bps), source IP entropy, and top-talker concentration. This process effectively collapses a torrent of billions of individual packets per minute into just a few thousand aggregated feature vectors. This represents a data compression factor of roughly **1,000,000-to-1**, transforming an unmanageable data firehose into a structured, low-velocity stream suitable for analysis.

### 2.2 Impact on Storage, ML, and Latency Budgets

This massive data reduction has profound downstream benefits. First, it dramatically lowers the cost and complexity of storage and observability. Instead of attempting to log petabytes of raw packet data, the system only needs to retain the compact, aggregated vectors. Second, it makes machine learning feasible in near-real-time. ML models can operate directly on these feature-rich vectors in memory, enabling detection and classification within the target **<300 ms** latency budget. Research into "win-based" feature extraction methods confirms that this approach effectively reduces detection delay and computational overhead without sacrificing accuracy [paradigm_shift[0]][5].

## 3. Five Technical Pillars Powering UltraScale

The UltraScale architecture is built on an inseparable stack of five core technical principles that work in concert to deliver terabit-scale defense. Each pillar addresses a specific challenge of high-throughput packet processing, from initial capture to final mitigation.

### 3.1 DPDK Line-Rate Capture—Benchmarks & Tuning

The first pillar is mandatory hardware bypass using the Data Plane Development Kit (DPDK). DPDK provides a set of libraries and drivers that allow user-space applications to take direct ownership of NIC hardware, bypassing the slow and non-deterministic Linux kernel network stack [architectural_principles.0.principle_name[0]][3]. By using a Poll Mode Driver (PMD) that constantly polls for incoming packets, DPDK eliminates interrupt overhead and enables processing at line rate, achieving upwards of **100G+ per CPU core** [architectural_principles.0.description[0]][3]. This raw performance is the foundation upon which the entire architecture is built. Sensor nodes are equipped with high-core-count CPUs (AMD EPYC recommended) and one or more 100G/200G/400G NICs, with traffic sharded across cores using SR-IOV virtualization.

### 3.2 Metadata Bus Showdown: Kafka vs NATS vs Redpanda (Table)

Once minimal metadata is extracted, it must be transported to the aggregator cluster via a high-throughput, low-latency message bus. The choice of this bus is critical, as it directly impacts the system's end-to-end detection latency. A comparison of the leading candidates reveals significant trade-offs.

| Technology | Performance Characteristics | Operational Complexity | Cost Efficiency |
| :--- | :--- | :--- | :--- |
| **Kafka** | **Very High Throughput** (>500 MB/s), but p99.99 tail latency can spike to **>5 seconds** at 1 GB/s. [metadata_bus_options.0.performance_characteristics[0]][6] | **High**. Relies on Zookeeper (or KRaft), requires extensive JVM tuning, and more infrastructure to set up and maintain. [metadata_bus_options.0.operational_complexity[0]][6] | **Low**. JVM-based architecture requires substantial CPU/memory. Documented severe performance issues on ARM hardware. [metadata_bus_options.0.cost_efficiency[0]][6] |
| **NATS JetStream** | **Sub-millisecond latency** and lightweight, but moderate throughput not designed for "big data firehose" use cases. | **Very Low**. Single binary, minimal configuration, and low monitoring overhead. Easy to deploy and scale. [metadata_bus_options.1.operational_complexity[0]][7] | **High**. Lightweight Go architecture is highly efficient with CPU and memory, operating well on modest hardware. [metadata_bus_options.1.cost_efficiency[0]][8] |
| **Redpanda** | **High Throughput** (>1 GB/s) with **10x faster** p99.99 tail latency than Kafka. At 1 GB/s, it is **70x faster** at the tail end. [metadata_bus_options.2.performance_characteristics[0]][6] | **Low**. Delivered as a single, Zookeeper-less binary with auto-tuning capabilities. Requires fewer nodes for comparable performance. | **Very High**. C++ implementation and thread-per-core architecture are resource-efficient. Offers a **57% byte-per-dollar** cost saving on ARM hardware. [metadata_bus_options.2.cost_efficiency[0]][6] |

**Takeaway**: Redpanda emerges as the superior choice for the core metadata bus, offering the best combination of high throughput and, crucially, predictable low tail latency. NATS remains a viable option for edge deployments where simplicity and ultra-low latency are paramount.

### 3.3 Aggregator Cluster & Sketch Algorithms

A single server cannot process metadata from a Tbps flow. The architecture relies on a horizontally scalable cluster of "aggregator" workers. These workers consume metadata from the bus and build statistical profiles using sliding window algorithms. To efficiently compute metrics like source IP entropy (for detecting spoofing) and top-K source concentration at scale, these aggregators employ probabilistic sketch data structures like HyperLogLog and Count-Min Sketch. This process is the crucial data reduction step, turning a high-velocity stream of raw events into a manageable, low-velocity stream of rich feature vectors.

### 3.4 ML Model Portfolio & 300 ms SLA

The machine learning strategy evolves from analyzing 83+ fields per event to detecting macroscopic signatures in the aggregated, window-based vectors. The ML portfolio includes:
* **Classification Models**: Lightweight tree ensembles (e.g., XGBoost) and shallow neural networks to classify known attack types like SYN floods, UDP floods, and amplification attacks.
* **Anomaly Detection**: Autoencoders to spot novel threats and deviations from normal traffic baselines.
* **Signature Matching**: Retrieval-Augmented Generation (RAG) with a FAISS-powered vector database to match patterns of known threats like Mirai variants.

The system is engineered to meet a strict SLA: **>95% detection** for major attack families, a false positive rate **<0.5% per window**, and a time-to-detect of **under 300 milliseconds**.

### 3.5 Mitigation Control Plane & BGP FlowSpec Workflows

Detection is useless without automated action. A robust control plane orchestrates the response. **ETCD** is used as a distributed key-value store for state management and policy coordination. An **Orchestrator** component interprets detection signals from the ML engine and applies mitigation policies [automated_mitigation_control_plane.core_components[0]][9]. Actions are executed via a **Mitigation Engine** that interfaces with firewall APIs and BGP controllers (e.g., ExaBGP, FRR). This enables a staged response, from soft rate-limiting to surgical traffic drops using BGP FlowSpec and, in catastrophic cases, Remote Triggered Blackholing (RTBH) or diversion to a scrubbing center.

## 4. Architecture Options Decision Matrix

Choosing the right hardware architecture involves balancing performance, cost, flexibility, and operational complexity. While the recommended path starts with a CPU-based DPDK sensor, other options become viable as scale and specific requirements change. SmartNICs, DPUs, and FPGAs offer paths to offload processing from the host CPU, but they come with trade-offs. [candidate_hardware_architectures.1.disadvantages[0]][10]

| Option | Host CPU Load | CAPEX | Dev Velocity | Lock-in Risk | Best-Fit Scale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DPDK sensor** | High | $ | Fast | Low | ≤400 G |
| **SmartNIC/DPU** | Low | $$$ | Medium | Med-High | 400 G–1 T |
| **FPGA inline** | Very low | $$$$ | Slow | High | >1 T peak |
| **Hybrid eBPF+DPDK** | Med | $$ | Fast | Low | Forensics |

**Takeaway**: The **DPDK Sensor + Aggregator** model is the recommended starting point, offering the best balance of cost, portability, and development speed for deployments up to 400 Gbps. For Tbps-scale or power-constrained environments, **SmartNIC/DPU offload** becomes strategically compelling, despite higher costs and vendor lock-in risks [candidate_hardware_architectures.1.disadvantages[0]][10]. FPGAs provide ultimate performance but are hampered by slow development cycles, making them suitable only for highly specialized, large-scale deployments [candidate_hardware_architectures.2.disadvantages[0]][10].

## 5. End-to-End Software Pipeline Walkthrough

The UltraScale software stack is a modular, high-performance pipeline designed for distributed operation. The end-to-end data flow is as follows:

1. **DPDK Capture Service (C++20)**: A lightweight, single-binary service runs on each sensor node. It uses DPDK to capture packets at line rate, extracts minimal L2-L4 metadata, discards the payload, and emits the metadata events. [core_software_components.0.component_name[0]][3]
2. **Metadata Bus (Redpanda)**: The metadata events are published to a high-throughput Redpanda cluster. Redpanda's Kafka compatibility and superior tail latency ensure reliable, low-latency transport from hundreds of distributed sensors. [core_software_components.1.component_name[0]][8]
3. **Aggregation Workers (C++/Rust)**: A horizontally scalable cluster of stateless workers subscribes to topics on the Redpanda bus. Each worker processes a shard of the metadata stream, building flow records and computing statistical profiles over sliding windows.
4. **Windowed ML Detector**: The aggregated feature vectors are fed into the ML detection engine. This adapted component applies a portfolio of models to classify threats and detect anomalies, flagging suspicious flows.
5. **Orchestrator + ETCD**: Detection alerts are written to ETCD. The Orchestrator reads these alerts, consults its policy configuration (also in ETCD), and determines the appropriate mitigation action.
6. **Mitigation Engine**: The Orchestrator issues commands to the Mitigation Engine, which translates them into concrete actions, such as making API calls to firewalls or using a BGP controller to announce blackhole routes.
7. **Forensic Snapshotter (Optional)**: For highly suspicious flows, the Orchestrator can trigger this component to perform a targeted, full-packet capture for deep-dive analysis by security teams. [core_software_components.7.technology_stack[0]][3]

## 6. ML Detection Strategy & Live-Drift Handling

The ML strategy is purpose-built for the macroscale, flow-based paradigm. It prioritizes lightweight, efficient models that can operate on aggregated data streams in near-real-time to achieve the target of **>95% recall**.

### 6.1 Feature Vector Spec & Importance Scores

The new ML models ingest aggregated vectors computed over short time windows. These vectors are designed to capture the macroscopic signatures of DDoS attacks. Key features include:
* **Volume Metrics**: `pps_last_100ms`, `bps_last_100ms`, `window_slope`
* **Source Diversity**: `unique_sources`, `src_entropy`
* **Protocol Anomalies**: `syn_ratio`, `rst_ratio`, `fin_ratio`
* **Packet Characteristics**: `avg_pkt_size`, `pkt_size_stddev`, `small_pkt_fraction`
* **Concentration**: `top1_src_concentration`, `top10_concentration`

Initial analysis shows that source entropy, SYN ratio, and packet size distribution are the most important features for distinguishing volumetric attacks from benign flash crowds.

### 6.2 Synthetic Data Generation Plan

Collecting real-world, terabit-scale attack data for training is impractical and dangerous. Therefore, the strategy relies heavily on synthetic data generation. High-performance traffic generators like **TRex** and **MoonGen** will be used to create large-scale datasets simulating millions of flows. The simulations will cover a wide range of attack families, including SYN/ACK floods, UDP floods, DNS/NTP amplification, and complex mixed-vector attacks.

### 6.3 Continuous Learning with Forensic Snapshotter

Models trained purely on synthetic data can suffer a drop in precision when deployed against real-world traffic. To bridge this "sim-to-real" gap, the architecture incorporates a continuous learning loop. The **Forensic Snapshotter** component can be triggered to capture labeled, full-packet samples of suspicious traffic identified in production. These real-world samples, validated against public datasets like **CTU-13**, **MAWI**, and **CAIDA**, will be used to continuously retrain and fine-tune the ML models, ensuring they adapt to evolving attack patterns and network drift.

## 7. Automated Mitigation Chain Economics

An automated, staged mitigation chain is not only technically necessary to handle the speed of attacks but also economically prudent. By starting with the least disruptive actions, the system minimizes the "blast radius" of false positives and reduces unnecessary costs.

1. **Soft Rate-Limits**: The first line of defense. Throttles suspicious traffic, slowing an attack without a complete block. This has minimal impact on legitimate users and incurs no extra transit costs.
2. **Per-IP/Subnet Drops**: If an attack persists, the system escalates to dropping traffic from specific malicious sources using BGP FlowSpec or firewall rules. This is a surgical action that preserves the vast majority of legitimate traffic.
3. **BGP Blackholing (RTBH)**: For catastrophic attacks threatening infrastructure, RTBH is used to drop all traffic to a victim IP at the network edge or with an upstream provider. This prevents link saturation but is a coarse-grained action that takes the victim offline.
4. **Traffic Diversion to Scrubbing**: The final escalation step is to reroute traffic to a specialized scrubbing center, which filters out malicious packets and forwards clean traffic [automated_mitigation_control_plane.staged_mitigation_chain[4]][11]. This offers the best protection but incurs significant transit and service fees.

By intelligently escalating through this chain, the system can defeat most attacks using low-cost, low-impact methods, reserving expensive scrubbing services for only the most extreme events. This can reduce collateral damage and associated transit fees by up to **80%** compared to a system that defaults to blackholing or scrubbing.

## 8. Tbps-Scale Testing & Validation Plan

Validating a system designed for terabit-scale traffic requires a specialized and phased approach. The plan focuses on de-risking the architecture through a series of lab simulations that build in scale and complexity, culminating in a final gate that replays realistic 1 Tbps attack scenarios.

The pipeline will use traffic generation tools like **TRex** and **MoonGen** for packet-level tests and flow-based simulators like **ddosflowgen** for massive-scale validation [testing_and_validation_pipeline.phase_name[0]][12]. Flow-based simulation is critical, as it makes it possible to model extremely high packet rates (e.g., **1.2 Tbps attack scenarios**) that are infeasible with packet-based replay [testing_and_validation_pipeline.objective[0]][12]. The phases include single-node DPDK performance tests (>10 Mpps), multi-node distributed ingestion tests (10-20 Gbps), ML accuracy tests, and finally, end-to-end ISP-grade simulations scaling from **100G → 400G → 1 Tbps** [testing_and_validation_pipeline.scale[0]][12].

## 9. Hardware Bill of Materials & Procurement Lead Times

Building a cluster capable of ingesting and analyzing 1 Tbps of traffic requires significant, specialized hardware. Procurement must begin early in the project lifecycle to account for long lead times.

A baseline 1 Tbps cluster configuration would consist of approximately **6-8 sensor/aggregator nodes**. The recommended hardware for each node includes:
* **CPUs**: High-core-count processors are critical. The **AMD EPYC 9654** (96-core) is the top recommendation, with dual-socket configurations providing maximum density.
* **NICs**: High-speed NICs with proven DPDK performance are mandatory. A 1 Tbps cluster could be built with **4 x NVIDIA ConnectX-7 400G cards** or a larger number of 100G/200G cards. The AMD UltraScale+ family also provides options for 400G networking applications [recommended_sensor_node_hardware.nics[0]][13].
* **Optional Offload**: For offload-heavy configurations, **NVIDIA BlueField-3 DPUs** can run DPDK applications directly on their embedded ARM cores, significantly reducing host CPU load [recommended_sensor_node_hardware.optional_offload_hardware[0]][10].

**Procurement Alert**: High-speed optics and NICs (>200G) currently have lead times of **16-22 weeks**. To meet the 12-month prototype timeline, purchase orders must be placed during Phase 3 (days 30-90).

## 10. Risk Register & Mitigation Playbook

Five critical risks have been identified for the UltraScale project. Each has been mapped to a concrete mitigation strategy and assigned an owner to ensure proactive management.

| Risk | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **High Hardware Cost** | Building a multi-node, Tbps-capable cluster requires a significant capital expenditure on high-end CPUs and NICs. | Stage procurement to align with roadmap phases. Utilize hybrid cloud scrubbing to handle burst capacity, deferring some on-premise hardware costs. [project_risks_and_mitigations.0.mitigation_strategy[0]][14] |
| **DPDK/FPGA Complexity** | Developing and maintaining high-performance, kernel-bypass code requires specialized expertise and can be complex and error-prone. [project_risks_and_mitigations.1.risk_description[0]][10] | Pursue an incremental development model. Define strong, stable interfaces between components to isolate complexity. Prioritize the more portable DPDK path first. |
| **False Positives** | At Tbps scale, even a low FPR can cause significant collateral damage by blocking large volumes of legitimate traffic. | Implement a staged mitigation chain that escalates from soft rate-limits to hard drops. Use probability-based decisioning in the orchestrator to avoid binary block/allow actions. |
| **Vendor Lock-in** | Relying on proprietary SmartNIC/DPU hardware and software stacks creates a dependency on a single vendor. | Prefer the vendor-agnostic DPDK path as the primary architecture. Make SmartNIC support an optional, compile-time feature rather than a hard dependency. |
| **Scaling Overhead** | As the system scales, the overhead of data movement, state synchronization, and coordination between nodes can become a bottleneck. | Enforce strict limits on aggregation window sizes to bound state. Use parallel sharding of traffic and processing across the aggregator cluster to ensure horizontal scalability. |

## 11. Regulatory & Funding Alignment with NIS2/DORA/CRA

This architecture is strategically designed to align with the EU's push for digital sovereignty and its evolving cybersecurity regulatory landscape. This alignment is not just a compliance exercise but a key enabler for securing public-sector funding and contracts.

* **EU Sovereignty**: By providing a blueprint for an on-premises, high-throughput defense system, the project directly supports EU goals of reducing reliance on non-EU hyperscalers for critical infrastructure protection. It enables EU entities to maintain full control over their data, security operations, and compliance audits [strategic_relevance_and_eu_alignment.sovereignty_goals[3]][15].
* **NIS2 Directive**: The architecture addresses core NIS2 requirements for robust risk management, supply chain security, and rapid incident handling for critical sectors.
* **DORA (Digital Operational Resilience Act)**: For the financial sector, the system supports DORA's stringent requirements for ICT risk management, resilience testing, and third-party risk oversight.
* **Cyber Resilience Act (CRA)**: The modular components are envisioned to follow secure-by-design principles with clear vulnerability handling processes, aligning with the CRA's focus on the security of products with digital elements.

This strong regulatory alignment positions the project as a prime candidate for creating a **"European Cloudflare-class"** capability, opening pathways to EU resilience funding and establishing a new standard for critical infrastructure protection.

## 12. Execution Roadmap & Phase-Gate KPIs

The development and deployment of the UltraScale prototype is planned as a 6-phase project over **12 months**. Each phase has clear objectives and key performance indicators (KPIs) that serve as pass/fail gates before proceeding to the next stage.

| Phase | Timeline | Key Objectives & KPIs |
| :--- | :--- | :--- |
| **Phase 2: Production Hardening** | 0–30 days | Finalize FAISS integration, ETCD client, and RAG refinements for the existing pipeline. |
| **Phase 3: DPDK Port** | 30–90 days | Port the existing sniffer to DPDK. **KPI: Achieve >10 Mpps sustained capture on a 100G NIC in the lab.** |
| **Phase 4: Distributed Prototype** | 90–150 days | Deploy a small-scale cluster (2–4 sensors, 2 aggregators). **KPI: Run 10–20 Gbps synthetic DDoS tests end-to-end.** |
| **Phase 5: ML Evolution** | 150–240 days | Train and validate windowed ML models on synthetic and real-world data. **KPI: Target >95% classification accuracy and <0.5% FPR.** |
| **Phase 6: ISP-Scale Tests** | 240–360 days | Test multi-node ingest at 100G–400G. Prepare procurement, runbooks, and deployment plans. **KPI: Successful 1 Tbps simulation.** |

This phased approach allows for incremental development, continuous validation, and proactive de-risking, making the ambitious 12-month timeline for a Tbps-capable prototype feasible, provided hardware procurement is initiated by Phase 3.

## 13. Appendices

### 13.1 Detailed NIC Benchmarks
*(Placeholder for detailed performance reports of NVIDIA ConnectX, Broadcom, and Intel NICs with DPDK.)*

### 13.2 Glossary & Acronyms
*(Placeholder for definitions of terms like DPDK, DPU, BGP, RTBH, etc.)*

### 13.3 Reference Config Files
*(Placeholder for example configuration files for DPDK services, Redpanda, and the Orchestrator.)*

## References

1. *How UltraDDoS Protect Stands Up to Multi-Terabit DDoS ...*. https://www.digicert.com/blog/how-ultraddos-protect-stands-up-to-multi-terabit-attacks
2. *theNET | NIS2 compliance: redefining resiliency in ...*. https://www.cloudflare.com/the-net/pursuing-privacy-first-security/nis2/
3. *A Comprehensive Survey on SmartNICs: Architectures, ...*. https://arxiv.org/html/2405.09499v1
4. *BGP Blackhole for DDoS Mitigation — and How to Automate It ...*. https://fastnetmon.com/2025/11/14/bgp-blackhole-for-ddos-mitigation-and-how-to-automate-it-with-fastnetmon/
5. *Towards real-time ML-based DDoS detection via cost- ...*. http://scis.scichina.com/en/2023/152105.pdf
6. *Redpanda vs. Kafka: A performance comparison*. https://www.redpanda.com/blog/redpanda-vs-kafka-performance-benchmark
7. *NATS and Kafka Compared*. https://www.synadia.com/blog/nats-and-kafka-compared
8. *NATS vs Redpanda: Lightweight Messaging vs High- ...*. https://risingwave.com/blog/nats-vs-redpanda-lightweight-messaging-vs-high-performance-streaming/
9. *A10 Defend DDoS Orchestrator*. https://www.a10networks.com/wp-content/uploads/A10-DS-Defend-Orchestrator.pdf
10. *Understanding ASIC, FPGA, and DPU Architectures*. https://www.fs.com/blog/fs-smartnic-solutions-understanding-asic-fpga-and-dpu-architectures-26648.html
11. *Orchestrating DDoS mitigation via blockchain-based ...*. https://www.cambridge.org/core/journals/knowledge-engineering-review/article/orchestrating-ddos-mitigation-via-blockchainbased-network-provider-collaborations/1E9D4FF7E3B72E442D615F1C811B26CB
12. *Simulating DDoS attacks with ddosflowgen*. https://www.galois.com/articles/simulating-ddos-attacks-ddosflowgen
13. *UltraScale Architecture PCB Design User Guide*. https://users.ece.utexas.edu/~mcdermot/arch/web/xilinx/ug583-ultrascale-pcb-design.pdf
14. *DDoS Protection and Mitigation: A 2025 Guide to ...*. https://www.kentik.com/kentipedia/ddos-protection/
15. *DORA RTS & ITS: Regulatory Technical Standards*. https://www.regulation-dora.eu/rts