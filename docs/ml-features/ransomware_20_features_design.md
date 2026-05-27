# Ransomware Detection Features - v1.0 (RPi Version)
## 20 Critical Features for Real-Time Detection

**Target Hardware:** Raspberry Pi 4 (1GB-4GB RAM)  
**Detection Goal:** Catch ransomware BEFORE encryption starts  
**Inference Budget:** <500 µs  
**False Positive Rate:** <1%  

---

## Feature Categories

### 🔴 CATEGORY 1: C&C Communication (6 features)
**Rationale:** Ransomware MUST communicate with C&C before encryption

| # | Feature Name | Type | Calculation | Why It Matters | Evasion Difficulty |
|---|-------------|------|-------------|----------------|-------------------|
| 1 | `dns_query_entropy` | float | Shannon entropy of DNS queries in 30s window | DGA domains have high entropy (random chars) | HARD - legitimate domains have low entropy |
| 2 | `new_external_ips_30s` | int | Count of never-seen-before external IPs in 30s | Ransomware contacts new C&C servers | MEDIUM - normal browsing also contacts new IPs |
| 3 | `dns_query_rate_per_min` | float | DNS queries/minute | Beaconing behavior (periodic check-ins) | MEDIUM - can slow down beaconing |
| 4 | `failed_dns_queries_ratio` | float | Failed DNS / Total DNS | DGA generates many failed queries | HARD - legitimate apps rarely fail DNS |
| 5 | `tls_self_signed_cert_count` | int | Self-signed TLS certs in 30s window | C&C often uses self-signed certs | MEDIUM - some apps use self-signed |
| 6 | `non_standard_port_http_count` | int | HTTP traffic on non-80/443 ports | C&C often on odd ports (8443, 9443) | EASY - can use standard ports |

**Total C&C features: 6**

---

### 🟠 CATEGORY 2: Lateral Movement (4 features)
**Rationale:** Ransomware spreads to other devices before encrypting

| # | Feature Name | Type | Calculation | Why It Matters | Evasion Difficulty |
|---|-------------|------|-------------|----------------|-------------------|
| 7 | `smb_connection_diversity` | int | Unique internal IPs contacted via SMB | Worm-like spreading via file shares | HARD - legitimate SMB is usually to 1-2 servers |
| 8 | `rdp_failed_auth_count` | int | Failed RDP authentication attempts | Brute force / credential stuffing | MEDIUM - can slow down attempts |
| 9 | `new_internal_connections_30s` | int | New internal IPs contacted in 30s | Devices that never talked now talking | MEDIUM - depends on network topology |
| 10 | `port_scan_pattern_score` | float | Sequential port attempts / total connections | Port scanning to find vulnerable services | HARD - random scanning is less effective |

**Total Lateral Movement features: 4**

---

### 🟡 CATEGORY 3: Data Exfiltration Prep (4 features)
**Rationale:** Some ransomware exfiltrates data before encryption (double extortion)

| # | Feature Name | Type | Calculation | Why It Matters | Evasion Difficulty |
|---|-------------|------|-------------|----------------|-------------------|
| 11 | `upload_download_ratio_30s` | float | Upload bytes / Download bytes in 30s | Massive uploads indicate exfiltration | MEDIUM - can slow down exfil |
| 12 | `burst_connections_count` | int | Connections started in <5s window | Sudden activity spike | MEDIUM - can spread over time |
| 13 | `unique_destinations_30s` | int | Unique external IPs contacted in 30s | Trying multiple exfil channels | HARD - normal traffic goes to few destinations |
| 14 | `large_upload_sessions_count` | int | Uploads >10MB in single session | Stealing large files | EASY - can split into small uploads |

**Total Exfiltration features: 4**

---

### 🟢 CATEGORY 4: Behavioral Anomalies (6 features)
**Rationale:** Ransomware behaves differently than normal applications

| # | Feature Name | Type | Calculation | Why It Matters | Evasion Difficulty |
|---|-------------|------|-------------|----------------|-------------------|
| 15 | `nocturnal_activity_flag` | bool | Activity between 00:00-05:00 local time | Ransomware often waits for off-hours | EASY - can adjust timing |
| 16 | `connection_rate_stddev` | float | Std deviation of connections/min over 5min | Normal traffic is steady, ransomware bursts | MEDIUM - can emulate steady rate |
| 17 | `protocol_diversity_score` | float | Unique protocols used / time window | Ransomware uses many protocols (SMB+HTTP+DNS+TLS) | HARD - legitimate apps stick to 1-2 protocols |
| 18 | `avg_flow_duration_seconds` | float | Average connection duration | Ransomware has short, bursty connections | MEDIUM - can keep connections alive longer |
| 19 | `tcp_rst_ratio` | float | RST packets / Total TCP packets | Scanning/probing causes many RSTs | MEDIUM - can handle RSTs gracefully |
| 20 | `syn_without_ack_ratio` | float | SYN without corresponding ACK | Failed connection attempts (scanning) | MEDIUM - can complete handshakes |

**Total Behavioral features: 6**

---

## Feature Extraction Requirements

### Data Needed from Sniffer

**Per-Packet Level:**
- TCP flags (SYN, ACK, RST, FIN)
- DNS query names (for entropy calculation)
- TLS certificate info (self-signed detection)
- Protocol type (HTTP, SMB, RDP, DNS)
- Ports (source, destination)

**Flow-Level Aggregation (30s windows):**
- Flow 5-tuple: (src_ip, dst_ip, src_port, dst_port, protocol)
- Bytes sent/received per flow
- Connection duration
- Connection count per IP pair
- Protocol transitions

**Historical State (needed for "new" detection):**
- IP whitelist (seen in last 24h)
- Internal IP topology (who talks to whom normally)
- Baseline connection rates per device

---

## Implementation Strategy

### Phase 1: Immediate (This Week)
Features **1-6** (C&C Detection) - Highest priority, easiest to implement
- These catch ransomware at the EARLIEST stage (initial infection)
- Only need DNS and TLS inspection

### Phase 2: Next Week  
Features **7-10** (Lateral Movement) - Medium priority, requires flow tracking
- Catches ransomware BEFORE it spreads widely
- Needs SMB/RDP protocol detection

### Phase 3: Week 3
Features **11-14** (Exfiltration) - Medium priority, requires byte counting
- Catches double-extortion ransomware
- Needs accurate byte accounting per flow

### Phase 4: Week 4
Features **15-20** (Behavioral) - Nice-to-have, polish layer
- Reduces false positives
- Needs longer time windows (5min)

---

## Dataset Requirements

To train a model with these 20 features, we need:

### ✅ Malicious Samples (Ransomware)
1. **CTU-13 Dataset** - Botnet traffic including ransomware
2. **CIC-IDS2017** - Labeled ransomware captures
3. **Stratosphere IPS** - Real malware PCAPs

### ✅ Benign Samples (Normal Traffic)
1. **Your own network** - 7 days of capture for baseline
2. **UNSW-NB15** - Normal traffic samples
3. **ISCX-VPN** - VPN/encrypted normal traffic

### Training Split
- 70% training
- 15% validation  
- 15% test (MUST include zero-day ransomware not seen in training)

---

## Expected Performance

Based on literature review:

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Accuracy** | >95% | High enough to trust automated blocking |
| **False Positive Rate** | <1% | 1 false alarm per 100 connections is tolerable |
| **False Negative Rate** | <5% | Miss rate - acceptable if we catch 95% of ransomware |
| **Inference Time** | <500 µs | Fits Parallels.ai budget for RPi |
| **Memory Footprint** | <50 MB | For model + feature cache |

---

## Enterprise Version (83 Features) - Future

Add these categories to reach 83 features:

- **Advanced TLS Fingerprinting:** JA3/JA4 hashes (20 features)
- **DNS Tunneling Detection:** Subdomain analysis, query patterns (15 features)
- **Advanced Lateral Movement:** Kerberos analysis, LDAP queries (10 features)
- **File Operation Patterns:** SMB file ops, deletions, renames (12 features)
- **Timing Analysis:** Weekday vs weekend, hourly patterns (8 features)
- **Process Lineage:** Parent-child process relationships (requires endpoint agent) (10 features)
- **Cryptographic Activity:** Entropy of traffic payloads (8 features)

**Total: 20 (base) + 63 (advanced) = 83 features**

---

## Critical Implementation Notes

### ⚠️ State Management
- **IP Whitelist:** LRU cache of 10k IPs, evict after 24h
- **Flow Table:** Hash table of 100k flows, evict after 5min
- **DNS Cache:** Ring buffer of 1k queries, for entropy calc

### ⚠️ Performance Considerations
- Use **SIMD** for entropy calculations (AVX2/NEON)
- Use **lock-free queues** for feature aggregation
- Use **memory pools** for flow objects

### ⚠️ False Positive Mitigation
- **Whitelist:** Known good IPs (Google, Microsoft, CDNs)
- **Time-of-day:** Suppress nocturnal flag during backups
- **Thresholds:** Tune per-network (residential vs office)

---

## Next Steps

1. ✅ Create JSON schema for these 20 features
2. ⏳ Design feature extraction code for sniffer
3. ⏳ Download and prepare training datasets
4. ⏳ Train RandomForest model
5. ⏳ Export to ONNX
6. ⏳ Integrate into ml-detector
7. ⏳ Test with real ransomware samples

**Estimated time to operational model:** 2-3 weeks
