# Network-Only NIDS: Behavioral Features That Survive Encryption

## Executive Summary

Research across prioritized academic venues indicates that inferring fine-grained host resource usage—such as absolute CPU utilization, disk I/O, or per-process activity—from network-only telemetry is largely unsolved and impractical for general-purpose production environments [executive_summary[0]][1] [key_conclusions_by_research_area[0]][2]. Precise resource attribution requires host-side sensors [key_conclusions_by_research_area[1]][3]. Therefore, network-only streaming ML pipelines must deprioritize fine-grained resource estimation and instead invest in behavioral, windowed, and graph features that scale and survive encryption.

Conversely, network-based host profiling and behavioral fingerprinting are mature and highly effective [executive_summary[0]][1]. Techniques such as device clock skew analysis, passive OS fingerprinting via TCP/IP headers, and TLS client fingerprinting (JA3/JA3S) provide robust methods for identifying device types and software stacks without payload access [executive_summary[0]][1] [executive_summary[1]][4].

Modern NIDS datasets, including CIC-IDS2017, UNSW-NB15, CTU-13, and UGR'16, align perfectly with a streaming, network-only design [executive_summary[2]][5]. They rely heavily on flow-based features like durations, byte/packet counts, rates, and inter-arrival time (IAT) statistics [executive_summary[2]][5]. Time-window aggregation is a cornerstone of modern NIDS, utilizing statistical features like normalized entropy, distinct counts (fan-in/out), burstiness metrics, and spectral analysis to detect anomalies [executive_summary[4]][6] [executive_summary[7]][7]. As encryption protocols like TLS 1.3 and QUIC obscure payload and handshake metadata, shifting detection weight to these encryption-resilient, shape-based features is critical for future-proofing your pipeline.

## What You Can and Cannot Infer from Network Alone

Disentangling achievable network-only signals from impractical goals is essential for focusing engineering efforts on viable features.

### Why precise CPU/disk/process inference is not viable in production

Reliably estimating fine-grained, absolute host resource metrics from network-only telemetry is an unsolved problem [key_conclusions_by_research_area[0]][2]. While academic studies demonstrate inference capabilities, they rely on fragile side-channels in highly controlled environments [host_resource_inference_analysis[0]][2]. For example, cache-contention timing requires co-resident cloud VMs, and disk I/O timing channels exploit microsecond-level latency variations that do not survive real-world network jitter [host_resource_inference_analysis[1]][8] [host_resource_inference_analysis[2]][9].

Research exploring "delay signatures" induced by internal CPU and memory contention shows that excessive context switching can add delay to packet execution [unsolved_and_impractical_features.feature_name[0]][2]. However, the relationship between external network traffic patterns and internal host resource usage is indirect, non-unique, and noisy [unsolved_and_impractical_features.reason_for_impracticality[0]][2]. Factors like NIC offloading, kernel-level batching, process multiplexing, virtualization, and middleboxes obscure any potential correlation [unsolved_and_impractical_features.reason_for_impracticality[0]][2].

### Coarse proxies that correlate with host load without agents

While precise measurement is impossible, network traffic can reveal coarse-grained activity, such as whether a host is busy or idle [host_resource_inference_analysis[0]][2]. Coarse proxies for resource usage include packet rates, request/response sizes, and flow counts [feature_taxonomy_by_data_source.feature_examples[0]][2]. More advanced features include fine-grained packet inter-arrival timing, retransmission patterns, bandwidth utilization traces, and TCP window size fluctuations [feature_taxonomy_by_data_source.feature_examples[0]][2]. These should be used as indirect indicators of behavioral change rather than absolute resource meters.

### Host-Internal Goals vs Feasibility vs Required Data

| Objective | Network-Only Feasibility | Minimum Data Requirement | Feature Examples |
| :--- | :--- | :--- | :--- |
| **Host Resource Usage Inference (CPU, Disk, Memory)** | Low / Impractical. Signals are noisy and easily disrupted by environmental factors [feature_taxonomy_by_data_source.network_only_feasibility[0]][2]. | Host Sensors (OS performance counters, EDR agents) [feature_taxonomy_by_data_source.minimum_data_requirement[0]][2]. | Coarse proxies: packet rates, flow counts. Brittle proxies: delay signatures, IAT timing [feature_taxonomy_by_data_source.feature_examples[0]][2]. |
| **Process-Level Attribution** | Unsolved. Modern protocols break the one-flow-per-process assumption [unsolved_and_impractical_features.reason_for_impracticality[0]][2]. | Host Sensors (/proc metrics, perf) [unsolved_and_impractical_features.required_data_source_for_feasibility[0]][2]. | N/A |
| **Behavioral Profiling & Fingerprinting** | High. Mature field with practical techniques [key_conclusions_by_research_area[0]][2]. | Packet Headers, Flow Metadata, TLS Handshake [network_based_host_profiling_techniques.data_requirements[0]][10]. | Clock skew, passive OS fingerprinting, JA3/JA3S [key_conclusions_by_research_area[0]][2]. |

*Takeaway: Accurate resource and process attribution strictly requires host sensors. Network-only pipelines must rely on coarse behavioral proxies.*

## Proven Network-Only Profiling to Implement Now

Behavioral fingerprinting is a well-established research area offering practical, network-only techniques to profile hosts and identify software stacks [key_conclusions_by_research_area[0]][2].

### Device/OS fingerprints from headers

Passive OS fingerprinting identifies operating systems by analyzing patterns in initial connection packets (SYN/SYN-ACK) [key_conclusions_by_research_area[3]][11]. Features include initial TTL, TCP window size, and TCP options ordering [key_conclusions_by_research_area[3]][11]. Additionally, physical devices can be fingerprinted by measuring the skew of their hardware clocks via TCP timestamps [executive_summary[1]][4]. While effective, these methods can be impacted by NAT and middleboxes, requiring per-segment confidence scoring.

### TLS/QUIC client fingerprinting and near-term viability

TLS fingerprinting (JA3/JA3S) is highly effective for identifying specific client applications and malware C2 channels [network_based_host_profiling_techniques.effectiveness_and_limitations[0]][10]. JA3 concatenates values from the unencrypted TLS ClientHello message (Version, Accepted Ciphers, Extensions, Elliptic Curves, Formats) and hashes them [network_based_host_profiling_techniques.description[0]][1]. JA3S does the same for the ServerHello [network_based_host_profiling_techniques.description[0]][1]. This technique is network-only and does not require decrypting the payload [network_based_host_profiling_techniques.data_requirements[0]][10]. However, its reliability is degrading due to adversarial randomization, TLS 1.3 GREASE extensions, and the upcoming Encrypted ClientHello (ECH) [network_based_host_profiling_techniques.effectiveness_and_limitations[0]][10]. Implement JA3/JA3S now, but plan to pivot toward timing and graph features as ECH adoption grows.

## Dataset-Informed Feature Design

Modern NIDS datasets are predominantly composed of features extracted from flow metadata, making them ideal for developing network-only streaming pipelines [key_conclusions_by_research_area[0]][2].

### Dataset comparison: features, scope, and visibility

| Dataset | Year | Span/Scale | Feature Count | Data Type | Notable Strengths | Caveats |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CIC-IDS2017** | 2017 | Multi-day lab capture | ~80-84 | PCAP + Flow CSV | Rich per-flow timing/flags [cic_ids2017_feature_analysis.dataset_overview[0]][5]. | Flow termination/labeling bugs [cic_ids2017_feature_analysis.known_issues_and_caveats[0]][12]. |
| **UNSW-NB15** | 2015 | 100 GB PCAP | 49 | PCAP-derived | Mix of flow/time/app features [unsw_nb15_feature_analysis.dataset_overview[0]][13]. | `ct_*` features hard to stream exactly [unsw_nb15_feature_analysis.streaming_feasibility_analysis[0]][14]. |
| **CTU-13** | 2011 | 13 scenarios | Argus fields | PCAP + Argus flows | Botnet scenarios, bidirectional stats [ctu13_and_ugr16_feature_analysis[0]][15]. | Scenario-specific bias. |
| **UGR'16** | 2016 | 100-day calibration | NetFlow fields | NetFlow v9 | Cyclostationarity evaluation [ctu13_and_ugr16_feature_analysis[1]][16]. | No payload/app fields. |

*Takeaway: All four datasets support network-only feature extraction, prioritizing flow statistics, timing, and windowed aggregates over payload inspection.*

### CIC-IDS2017: 80+ flow features; fix termination/labels

The CIC-IDS2017 dataset provides approximately 80-84 features per flow, generated by the CICFlowMeter tool [cic_ids2017_feature_analysis.feature_summary[0]][17]. These include basic identifiers, temporal features (duration, IAT stats), volumetric features, rate features, and TCP flag counts [cic_ids2017_feature_analysis.feature_summary[0]][17]. However, the original generation process had significant flaws: the tool incorrectly terminated TCP flows upon observing the first FIN flag, creating spurious "TCP appendices," and ignored RST packets [cic_ids2017_feature_analysis.known_issues_and_caveats[0]][12]. When replicating these features, implement correct TCP teardown logic (waiting for both FINs or RST) to avoid tainting your models.

### UNSW-NB15: 49 features; connection-based ct_* need streaming approximations

UNSW-NB15 defines 49 features categorized into basic, flow, content, time-based, and connection-based metrics [unsw_nb15_feature_analysis.feature_summary[0]][18]. While basic and time-based features are highly feasible for streaming, the 13 connection-based (`ct_*`) features are challenging [unsw_nb15_feature_analysis.streaming_feasibility_analysis[0]][14]. These features rely on looking back at the "last 100 connections" with specific properties [unsw_nb15_feature_analysis.feature_summary[0]][18]. In a high-throughput streaming environment, this requires approximation using probabilistic data structures like Count-Min Sketch or fixed-size sliding windows [unsw_nb15_feature_analysis.streaming_feasibility_analysis[0]][14].

### CTU-13 and UGR'16: Long-span NetFlow for cyclostationarity

CTU-13 provides bidirectional flow records generated by Argus, offering crucial per-direction byte and packet counts ideal for analyzing traffic asymmetry [ctu13_and_ugr16_feature_analysis[0]][15]. UGR'16 provides NetFlow v9 data captured over an extended period, explicitly designed for evaluating IDSs that leverage long-term traffic patterns and periodicity (cyclostationarity) [ctu13_and_ugr16_feature_analysis[1]][16]. This supports building time-varying baselines to detect anomalies as deviations from periodic norms [ctu13_and_ugr16_feature_analysis[1]][16].

## Time-Window Features That Scale

Time-window aggregation is a fundamental technique for detecting anomalies from network-only data [key_conclusions_by_research_area[0]][2]. Multi-scale windows combined with sketches deliver high signal with bounded compute.

### Distributional shifts via normalized entropy

Shannon entropy of source/destination IPs and ports is highly effective for detecting distributional changes caused by scans, worms, and DDoS attacks [key_conclusions_by_research_area[0]][2]. To decouple the feature from traffic volume, compute normalized entropy by dividing the Shannon entropy value by the logarithm of the number of distinct elements in the window [high_value_additions_for_pipeline[7]][6]. This provides a stable indicator of distributional shifts regardless of overall throughput.

### Distinct counts and heavy hitters with HLL/CMS

Features like `fan-out` and `fan-in` are critical for detecting scanning and spreading behavior [time_window_aggregation_feature_analysis[0]][19]. In a streaming context, these are efficiently approximated using the HyperLogLog (HLL) algorithm, which provides high-accuracy distinct counts with a small, fixed memory footprint [time_window_aggregation_feature_analysis[0]][19]. For frequency counts and identifying heavy hitters, use the Count-Min Sketch (CMS) [streaming_pipeline_recommendations[2]][20].

### Timing dynamics: IAT statistics and burstiness

Temporal features capture the timing dynamics of traffic. Compute the mean, standard deviation, and key percentiles (e.g., p90, p99) of packet Inter-Arrival Times (IATs) within a window [time_window_aggregation_feature_analysis[0]][19]. Additionally, calculate the Coefficient of Variation (CV = std/mean) of IATs as a measure of burstiness [high_value_additions_for_pipeline[0]][10]. These features expose stealthy scanning, periodic C2 beaconing, and traffic shaping [time_window_aggregation_feature_analysis[0]][19].

### Periodicity and spectral analysis

For detecting long-term patterns, spectral analysis using the Fast Fourier Transform (FFT) on a time series of packet/byte counts can reveal dominant frequencies [time_window_aggregation_feature_analysis[0]][19]. Foundational work shows network traffic is statistically self-similar across time scales. Building cyclostationary baselines for expected traffic patterns at different times of day allows for the detection of anomalies that break established rhythms [time_window_aggregation_feature_analysis[0]][19].

## Lateral Movement via Temporal Graphs

Enhance your `lateral_movement_score` by modeling host-to-host communications as a temporal graph [high_value_additions_for_pipeline[9]][21]. Recent research frames lateral movement detection as a temporal link prediction problem. By learning normal communication patterns, the system can flag new, low-probability connections (edges) between internal hosts as anomalous. This structural approach elevates rarity signals and surfaces credential abuse more effectively than simple fan-out counts.

## Implementation Blueprint for Real-Time Streaming

A reliable, scalable, and adversarial-aware streaming pipeline requires specific architectural choices.

### Robust flow management: proper FIN/RST handling and timeouts

Implement a flow timeout policy that correctly handles TCP termination. Terminate flows immediately on RST packets, and wait for FINs from both directions (or a final timeout) instead of just the first FIN [cic_ids2017_feature_analysis.streaming_computation_notes[0]][17]. Use a sensible inactivity timeout to expire stale flows and avoid creating the "TCP appendices" seen in flawed datasets [cic_ids2017_feature_analysis.streaming_computation_notes[0]][17].

### Sketch configuration and maintenance

Parameterize HLL precision and bound per-host memory. To defend against sketch poisoning, use strong, universal hash functions with secret, periodically rotated salts [adversarial_considerations.recommended_mitigations[0]][20]. This prevents attackers from reliably predicting hash collisions to manipulate feature outputs.

### Multi-scale windows and online statistics

Adopt a multi-scale windowing strategy: fast windows (1-10s) for bursts, medium windows (30s-5m) for stable distributional statistics, and slow windows (30m-24h) for cyclostationary baselines [streaming_pipeline_recommendations[0]][19]. Use sliding windows with 25-50% overlap [streaming_pipeline_recommendations[0]][19]. Use online algorithms like Welford's method for calculating statistical moments (mean, variance) in a single pass, and t-digest for streaming quantiles [cic_ids2017_feature_analysis.streaming_computation_notes[0]][17].

## Encryption Trendline and Roadmap

Modern encryption protocols are forcing a strategic shift away from deep packet inspection towards behavioral and statistical analysis [impact_of_encryption_on_features[0]][22].

### Near-term (0-12 months): Maximize remaining handshake metadata

Continue utilizing JA3 and JA3S fingerprinting to identify specific client software and malware families [network_based_host_profiling_techniques.description[0]][1]. Mine server-side TLS fingerprints and maintain these features while they remain viable.

### Mid-term (12-36 months): Pivot to shape-first detection

Protocols like TLS 1.3 and QUIC encrypt significantly more connection metadata, and Encrypted Client Hello (ECH) will obscure the Server Name Indication (SNI) [impact_of_encryption_on_features[0]][22]. This will render JA3 and similar techniques ineffective [network_based_host_profiling_techniques.effectiveness_and_limitations[0]][10]. Shift detection weight to encryption-resilient signals: timing (IAT CV, burstiness), size distributions, normalized entropies, and host-to-host graph anomalies [impact_of_encryption_on_features[0]][22].

## Adversarial Considerations

Expect adversaries to attempt sketch poisoning and behavioral mimicry.

### Attack vectors vs mitigations

| Attack Vector | Description | Recommended Mitigation |
| :--- | :--- | :--- |
| **Sketch Poisoning** | Adversary sends crafted traffic to collide with hash locations, manipulating frequencies or hiding attacks [adversarial_considerations.description[0]][20]. | Use conservative-update CMS; employ strong hash functions with secret, rotated salts [adversarial_considerations.recommended_mitigations[0]][20]. |
| **Behavioral Mimicry** | Adversary shapes traffic to match normal IATs or volume profiles. | Use an ensemble of diverse features (distributional, temporal, graph-based) across multi-scale windows [adversarial_considerations.recommended_mitigations[0]][20]. |

*Takeaway: Robust sketch designs and feature ensembles are mandatory to resist targeted evasion in streaming NIDS.*

## High-Value Additions to Your Feature Set

Based on the research, prioritize adding these features to your pipeline:
1. **Normalized Entropy**: `H(src_ips) / log2(distinct_src_ip_count)` to decouple from volume [high_value_additions_for_pipeline[7]][6].
2. **HLL-based Fan-in/Fan-out**: Scalable distinct counting for scanning detection [high_value_additions_for_pipeline[8]][20].
3. **IAT Statistics**: Mean, std, CV, p90, and p99 of inter-arrival times to expose beacons and stealth scans [high_value_additions_for_pipeline[0]][10].
4. **Cyclostationary Baselines**: Hour-of-week expected values for rates to reduce false positives [high_value_additions_for_pipeline[10]][16].
5. **Temporal Graph Link Prediction**: Score new internal edges by rarity to surface lateral movement [high_value_additions_for_pipeline[9]][21].

## Paper Catalog with Data Requirements

The following peer-reviewed papers provide the evidence base for these feature strategies.

### Peer-reviewed papers and feature computability

| Title | Authors | Year | Venue | Proposed Features | Network-Only? | Data Needed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Remote physical device fingerprinting | T. Kohno, A. Broido, K. Claffy | 2005 | IEEE S&P | Device clock skew via TCP timestamps [relevant_papers_catalog.0.proposed_features_summary[0]][2]. | Yes [relevant_papers_catalog.0.is_network_only[0]][2]. | Packet headers, timestamps [relevant_papers_catalog.0.required_data_source[0]][2]. |
| Mining Anomalies Using Traffic Feature Distributions | A. Lakhina, M. Crovella, C. Diot | 2005 | SIGCOMM | Shannon entropy of IPs/ports over time windows. | Yes. | Flow metadata. |
| Hey, You, Get Off of My Cloud | T. Ristenpart, E. Tromer, H. Shacham, S. Savage | 2009 | ACM CCS | Cache contention timing (Prime+Probe). | No. | Host Sensors (co-resident VM). |
| Counting Packets Sent Between Arbitrary Internet Hosts | J. Knockel, J. Crandall | 2014 | USENIX FOCI | IPID-based remote packet counters [relevant_papers_catalog.10.proposed_features_summary[0]][2]. | Yes [relevant_papers_catalog.10.is_network_only[0]][2]. | Packet headers (active probes). |
| Using Network Traffic to Infer Hardware State | Lanier Watkins et al. | 2015 | ACM TOEC | Delay signatures and CPU fingerprinting [relevant_papers_catalog.3.proposed_features_summary[0]][2]. | Yes [relevant_papers_catalog.3.is_network_only[0]][2]. | Packet headers (timestamps). |
| UGR'16: A New Dataset for the Evaluation of Cyclostationarity-Based Network IDSs | G. Maciá-Fernández et al. | 2016 | Computers & Security | Cyclostationary analysis, time-window aggregates. | Yes [relevant_papers_catalog.1.is_network_only[0]][2]. | Flow metadata (NetFlow) [relevant_papers_catalog.1.required_data_source[0]][2]. |
| TLS fingerprinting with JA3 and JA3S | Salesforce | 2017 | Industry Blog | JA3/JA3S hashes from TLS Hello messages. | Yes. | Packet payload (unencrypted TLS). |
| Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study | G. Engelen, V. Rimmer, W. Joosen | 2021 | WTMC | Identifies flow termination and labeling bugs. | Yes. | Flow metadata. |
| Passive operating system fingerprinting revisited | Martin Laštovička et al. | 2023 | Computer Networks | OS fingerprinting via SYN/SYN-ACK fields. | Yes [relevant_papers_catalog.5.is_network_only[0]][2]. | Packet headers. |
| Detecting Network Lateral Movement via Scalable Temporal Link Prediction | Euler | 2023 | ACM T-P&S | Temporal link prediction on connection graphs. | Yes. | Flow metadata. |
| Sync+Sync: A Covert Channel Built on fsync with Storage | Q. Jiang et al. | 2024 | USENIX Security | Filesystem sync timing side-channel. | No. | Host Sensors. |
| On the Self-Similar Nature of Ethernet Traffic | W. Leland et al. | 1994 | IEEE/ACM Trans. Networking | Hurst exponent for long-range dependence. | Yes. | Packet headers. |

## Unsolved/Impractical Feature Proposals

Accurate CPU, disk IOPS, and per-process attribution from network traffic alone remains unsolved and impractical for general-purpose NIDS [key_conclusions_by_research_area[0]][2]. While niche remote side-channels exist (e.g., IPID-based counters, CPU delay signatures), they are highly brittle, easily disrupted by NAT or middleboxes, and require specific lab or co-residency conditions [key_conclusions_by_research_area[0]][2]. Treat such inferences as supplementary heuristics only; do not rely on them for core detections. Avoid investing engineering resources into precise host resource estimation without endpoint telemetry.

## References

1. *TLS Fingerprinting with JA3 and JA3S - Salesforce Engineering Blog*. https://engineering.salesforce.com/tls-fingerprinting-with-ja3-and-ja3s-247362855967/
2. *Using Network Traffic to Infer Hardware State: A Kernel-Level Investigation: ACM Transactions on Embedded Computing Systems: Vol 14, No 3*. https://dl.acm.org/doi/10.1145/2700094
3. *Relationship between TCP network traffic, CPU utilization, and memory... | Download Scientific Diagram*. https://www.researchgate.net/figure/Relationship-between-TCP-network-traffic-CPU-utilization-and-memory-utilization_fig5_220079349
4. *Clock Skew Based Remote Device Fingerprinting Demystified*. https://www.informatik.tu-cottbus.de/~andriy/papers/clock-skew-ntp-ieee-globecom2012.pdf
5. *IDS 2017 | Datasets | Research | Canadian Institute for Cybersecurity | UNB*. https://www.unb.ca/cic/datasets/ids-2017.html
6. *Mining Anomalies Using Traffic Feature Distributions - Events*. http://conferences.sigcomm.org/sigcomm/2005/paper-LakCro.pdf
7. *Entropy-Based Anomaly Detection in a Network | Wireless Personal Communications: An International Journal*. https://dl.acm.org/doi/abs/10.1007/s11277-018-5288-2
8. *Detecting co-residency with active traffic analysis techniques | Proceedings of the 2012 ACM Workshop on Cloud computing security workshop*. https://dl.acm.org/doi/10.1145/2381913.2381915
9. *
"Detection of Co-resident Virtual Machines Using Network Traffic Patter" by James A Savage
*. https://digitalscholarship.tnstate.edu/dissertations/AAI10119068/
10. *The Limits of JA3 Fingerprinting: Why It Fails at Accurate Device Identification*. https://fingerprint.com/blog/limitations-ja3-fingerprinting-accurate-device-identification/
11. *Passive operating system fingerprinting revisited: : Evaluation and current challenges: Computer Networks: The International Journal of Computer and Telecommunications Networking: Vol 229, No C*. https://dl.acm.org/doi/10.1016/j.comnet.2023.109782
12. *(PDF) Troubleshooting an Intrusion Detection Dataset*. https://www.researchgate.net/publication/353107141_Troubleshooting_an_Intrusion_Detection_Dataset_the_CICIDS2017_Case_Study
13. *The UNSW-NB15 dataset*. https://researchdata.edu.au/the-unsw-nb15-dataset/1957529
14. *(PDF) UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)*. https://www.researchgate.net/publication/287330529_UNSW-NB15_a_comprehensive_data_set_for_network_intrusion_detection_systems_UNSW-NB15_network_data_set
15. *The CTU-13 Dataset. A Labeled Dataset with Botnet, Normal and Background traffic. — Stratosphere Laboratory*. https://www.stratosphereips.org/datasets-ctu13
16. *A New Dataset for the Evaluation of Cyclostationarity- ...*. https://nesg.ugr.es/nesg-ugr16/dataset_AuthorVersionFinal.pdf
17. *CIC-IDS2017: Benchmark for Intrusion Detection*. https://www.emergentmind.com/topics/cic-ids2017-dataset
18. *UNSW-NB15*. https://fkie-cad.github.io/COMIDDS/content/datasets/unsw_nb15/
19. *
      TTANAD: Test-Time Augmentation for Network Anomaly Detection - PMC
*. https://pmc.ncbi.nlm.nih.gov/articles/PMC10217189/
20. *Count-Min Sketch*. http://dimacs.rutgers.edu/~graham/pubs/papers/cmencyc.pdf
21. *Euler: Detecting Network Lateral Movement via Scalable Temporal Link Prediction | ACM Transactions on Privacy and Security*. https://dl.acm.org/doi/full/10.1145/3588771
22. *Encrypted Client Hello: Closing the SNI Metadata Gap - Center for Democracy and Technology*. https://cdt.org/insights/encrypted-client-hello-closing-the-sni-metadata-gap/