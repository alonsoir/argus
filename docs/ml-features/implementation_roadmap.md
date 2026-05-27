# docs/ml-features/implementation_roadmap.md

# Ransomware Detection - Implementation Roadmap
## From Feature Design to Operational Model

**Status:** Design Complete ✅ | Implementation Pending ⏳  
**Target:** Operational Level 3 ransomware detector in 2-3 weeks  
**Hardware:** Raspberry Pi 4 (1-4GB RAM)  

---

## 📋 What We Just Designed

### ✅ Features Defined
- **20 critical features** optimized for RPi
- **4 categories:** C&C, Lateral Movement, Exfiltration, Behavioral
- **Performance budget:** <500 µs inference, <50 MB memory

### ✅ Files Created
1. `ransomware_20_features_design.md` - Full design document
2. `ransomware_20_features.json` - JSON schema for sniffer

---

## 🔧 Configuration Changes Needed

### 1. Update sniffer.json

**File:** `sniffer/config/sniffer.json`

**Changes:**
```json
"ransomware_feature_group": {
  "count": 20,  // ← Change from 83 to 20
  "reference": "config/features/ransomware_20_features.json",  // ← Update path
  "description": "Ransomware detection features (20 critical features for RPi)"
}
```

**Location to place JSON file:**
```bash
mkdir -p sniffer/config/features/
cp ransomware_20_features.json sniffer/config/features/
```

### 2. Update ml_detector_config.json

**File:** `ml-detector/config/ml_detector_config.json`

**Changes:**
```json
"level2": {
  "ransomware": {
    "enabled": false,  // ← Keep false until model is trained
    "name": "ransomware_detector",
    "model_file": "level2/ransomware_rf_20.onnx",  // ← New filename
    "features_count": 20,  // ← Change from 82 to 20
    "model_type": "RandomForest",
    "description": "Ransomware detection - RandomForest (20 features, RPi optimized)",
    "requires_scaling": false,
    "timeout_ms": 10
  }
}
```

---

## 🏗️ Implementation Phases

### Phase 1: Feature Extraction Infrastructure (Week 1)
**Goal:** Sniffer can extract all 20 features

#### 1.1 Add Data Structures to Sniffer

**New classes needed:**

```cpp
// sniffer/src/flow_tracker.hpp
class FlowTracker {
    struct FlowKey {
        uint32_t src_ip, dst_ip;
        uint16_t src_port, dst_port;
        uint8_t protocol;
    };
    
    struct FlowStats {
        uint64_t bytes_sent, bytes_received;
        uint32_t packets_sent, packets_received;
        uint64_t start_time_ns, last_seen_ns;
        uint16_t tcp_flags;  // Bitmask of all flags seen
    };
    
    std::unordered_map<FlowKey, FlowStats> flows_;
    
public:
    void update_flow(const Packet& pkt);
    FlowStats* get_flow(const FlowKey& key);
    void cleanup_expired_flows(uint64_t timeout_ns);
    size_t get_flow_count() const;
};
```

```cpp
// sniffer/src/ip_whitelist.hpp
class IPWhitelist {
    struct IPEntry {
        uint32_t ip;
        uint64_t last_seen_timestamp;
    };
    
    // LRU cache of 10K IPs
    std::unordered_map<uint32_t, uint64_t> seen_ips_;
    
public:
    bool is_known_ip(uint32_t ip);
    void add_ip(uint32_t ip, uint64_t timestamp);
    size_t count_new_ips_in_window(uint64_t window_start);
    void evict_old_entries(uint64_t cutoff_timestamp);
};
```

```cpp
// sniffer/src/dns_analyzer.hpp
class DNSAnalyzer {
    struct DNSQuery {
        std::string query_name;
        uint64_t timestamp;
        bool success;  // true = got response, false = NXDOMAIN
    };
    
    std::deque<DNSQuery> recent_queries_;  // Ring buffer, 1K entries
    
public:
    void add_query(const std::string& name, uint64_t timestamp, bool success);
    float calculate_entropy();  // Shannon entropy of query names
    float get_query_rate_per_minute();
    float get_failure_ratio();
};
```

```cpp
// sniffer/src/time_window_aggregator.hpp
class TimeWindowAggregator {
    struct WindowFeatures {
        // All 20 features aggregated over window
        float dns_query_entropy;
        int new_external_ips_30s;
        float dns_query_rate_per_min;
        // ... etc for all 20 features
    };
    
    WindowFeatures aggregate_features(uint64_t window_start, uint64_t window_end);
    
private:
    FlowTracker& flow_tracker_;
    IPWhitelist& ip_whitelist_;
    DNSAnalyzer& dns_analyzer_;
    // ... etc
};
```

#### 1.2 Implement Feature Extraction Functions

**Priority order:**
1. **Phase 1A (Critical):** Features 1, 2, 7
   - `dns_query_entropy` - Requires DNS parsing
   - `new_external_ips_30s` - Requires IP whitelist
   - `smb_connection_diversity` - Requires port detection

2. **Phase 1B (High):** Features 3, 4, 9, 11, 13, 17
   - DNS rates, failed queries
   - New internal connections
   - Upload/download ratios
   - Protocol diversity

3. **Phase 1C (Medium):** Remaining features

#### 1.3 Add Protobuf Fields (if needed)

**Check:** Does `NetworkFeatures` in protobuf have fields for all 20 features?

If not, add to `protobuf/network_event.proto`:
```protobuf
message RansomwareFeatures {
  // C&C Communication
  float dns_query_entropy = 1;
  int32 new_external_ips_30s = 2;
  float dns_query_rate_per_min = 3;
  float failed_dns_queries_ratio = 4;
  int32 tls_self_signed_cert_count = 5;
  int32 non_standard_port_http_count = 6;
  
  // Lateral Movement
  int32 smb_connection_diversity = 7;
  int32 rdp_failed_auth_count = 8;
  int32 new_internal_connections_30s = 9;
  float port_scan_pattern_score = 10;
  
  // Exfiltration
  float upload_download_ratio_30s = 11;
  int32 burst_connections_count = 12;
  int32 unique_destinations_30s = 13;
  int32 large_upload_sessions_count = 14;
  
  // Behavioral
  bool nocturnal_activity_flag = 15;
  float connection_rate_stddev = 16;
  float protocol_diversity_score = 17;
  float avg_flow_duration_seconds = 18;
  float tcp_rst_ratio = 19;
  float syn_without_ack_ratio = 20;
}

// Add to NetworkFeatures message:
message NetworkFeatures {
  // ... existing fields ...
  RansomwareFeatures ransomware = 100;  // New field
}
```

#### 1.4 Testing Strategy

**Unit tests for each component:**
```bash
# Test flow tracker
./tests/test_flow_tracker
# Expected: Can track 100K flows, cleanup works, no memory leaks

# Test IP whitelist
./tests/test_ip_whitelist
# Expected: LRU eviction works, can handle 10K IPs

# Test DNS analyzer
./tests/test_dns_analyzer
# Expected: Entropy calculation correct, query rate accurate

# Test time window aggregator
./tests/test_time_window_aggregator
# Expected: All 20 features extracted correctly from sample PCAP
```

**Integration test:**
```bash
# Run sniffer with test PCAP
./build/sniffer --config config/sniffer.json --input-pcap tests/data/ransomware_sample.pcap

# Expected output:
# - All 20 features populated
# - No segfaults
# - Memory usage <10 MB
# - Processing time <1ms per packet
```

---

### Phase 2: Dataset Preparation & Training (Week 2)

#### 2.1 Download Datasets

**Ransomware samples:**
```bash
cd ml-training/datasets

# CTU-13 Botnet Dataset
wget https://www.stratosphereips.org/datasets-ctu13
# Contains: Neris, Rbot, Virut, Menti, Sogou, Murlo, etc.

# CIC-IDS2017 Dataset
wget https://www.unb.ca/cic/datasets/ids-2017.html
# Contains: DoS, DDoS, Brute Force, Web Attack, Infiltration, Botnet

# Stratosphere IPS
wget https://www.stratosphereips.org/datasets-malware
# Contains: Recent malware captures including ransomware
```

**Benign samples:**
```bash
# Capture your own network (7 days minimum)
sudo tcpdump -i eth0 -w benign_traffic.pcap -G 3600 -W 168

# Or use public datasets:
wget https://cloudstor.aarnet.edu.au/plus/s/2DhnLGDdEECo4ys  # UNSW-NB15
```

#### 2.2 Feature Extraction from PCAPs

**Create Python script:** `ml-training/extract_features.py`

```python
import pyshark
import pandas as pd
from pathlib import Path

def extract_features_from_pcap(pcap_path):
    """
    Extract all 20 ransomware features from PCAP file.
    
    Returns: pandas DataFrame with columns:
    - dns_query_entropy
    - new_external_ips_30s
    - ... (all 20 features)
    - label (0=benign, 1=ransomware)
    """
    # Use tshark to parse PCAP
    cap = pyshark.FileCapture(pcap_path, display_filter='ip')
    
    # Aggregate over 30-second windows
    features = []
    
    for window_start in range(0, total_duration, 30):
        window_features = compute_features_for_window(
            cap, window_start, window_start + 30
        )
        features.append(window_features)
    
    return pd.DataFrame(features)

# Process all PCAPs
benign_df = extract_features_from_pcap('benign_traffic.pcap')
benign_df['label'] = 0

ransomware_df = extract_features_from_pcap('ransomware_traffic.pcap')
ransomware_df['label'] = 1

# Combine and save
df = pd.concat([benign_df, ransomware_df])
df.to_csv('ransomware_training_data.csv', index=False)
```

**Run feature extraction:**
```bash
cd ml-training
python extract_features.py --input datasets/ctu13/ --output data/ctu13_features.csv
python extract_features.py --input datasets/cicids/ --output data/cicids_features.csv
python extract_features.py --input datasets/benign/ --output data/benign_features.csv

# Combine all features
python combine_datasets.py --output data/final_training_data.csv
```

**Expected output:**
- CSV file with ~100K rows (samples)
- 20 feature columns + 1 label column
- Balanced classes (50% benign, 50% ransomware)

#### 2.3 Train RandomForest Model

**Create training script:** `ml-training/train_ransomware_rf.py`

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import skl2onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# Load data
df = pd.read_csv('data/final_training_data.csv')

# Split features and labels
X = df.drop('label', axis=1)
y = df['label']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Train model
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=20,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))

# Export to ONNX
initial_type = [('float_input', FloatTensorType([None, 20]))]
onnx_model = convert_sklearn(model, initial_types=initial_type)

with open('ransomware_rf_20.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
```

**Run training:**
```bash
cd ml-training
python train_ransomware_rf.py

# Expected output:
#               precision    recall  f1-score   support
#            0       0.96      0.97      0.97     10000
#            1       0.97      0.96      0.97     10000
#
#     accuracy                           0.97     20000
```

**Copy model to production:**
```bash
cp ransomware_rf_20.onnx ../ml-detector/models/production/level2/
```

---

### Phase 3: Integration & Testing (Week 3)

#### 3.1 Enable Ransomware Model in ml-detector

**Update config:**
```json
"level2": {
  "ransomware": {
    "enabled": true,  // ← Enable it!
    "name": "ransomware_detector",
    "model_file": "level2/ransomware_rf_20.onnx",
    "features_count": 20,
    "model_type": "RandomForest",
    "description": "Ransomware detection - RandomForest (20 features)",
    "requires_scaling": false,
    "timeout_ms": 10
  }
}
```

**Rebuild ml-detector:**
```bash
cd ml-detector
make clean
make rebuild
```

#### 3.2 End-to-End Testing

**Test 1: Benign Traffic**
```bash
# Terminal 1
make run-detector

# Terminal 2
make run-sniffer

# Expected:
# - Level 2 ransomware predictions: all ~0.0 (benign)
# - No false positives
# - Latency <2ms
```

**Test 2: Ransomware Sample**
```bash
# Replay ransomware PCAP through sniffer
tcpreplay -i eth0 tests/data/wannacry_capture.pcap

# Expected:
# - Level 2 ransomware predictions: >0.75 (malicious)
# - Detection within first 30 seconds
# - Immediate alert triggered
```

**Test 3: Performance Under Load**
```bash
# Generate high traffic load
hping3 -c 10000 -d 120 -S -w 64 -p 80 --flood target_ip

# Expected:
# - System remains stable
# - No packet drops
# - Latency <5ms P99
# - Memory usage <200 MB
```

#### 3.3 Tuning

**Adjust thresholds if needed:**
```json
"thresholds": {
  "level2_ransomware": 0.75,  // ← Start here, tune based on FPR
}
```

**Tune based on metrics:**
- **Too many false positives?** Increase threshold to 0.8-0.85
- **Missing attacks?** Decrease threshold to 0.65-0.7
- **Performance issues?** Reduce feature count or increase window size

---

## 🚨 Next Steps for Integration with Firewall

### Phase 4: Firewall ACL Agent (Future)

**When ransomware detected:**
1. ML-detector sends alert to firewall-acl-agent via ZMQ
2. Firewall agent executes:
   ```bash
   # Kill existing connection
   conntrack -D -s <malicious_ip>
   
   # Add to blocklist
   nft add element inet filter blocklist { <malicious_ip> }
   ```
3. Time to block: <50 µs (per Parallels.ai recommendation)

**Architecture:**
```
Sniffer → ML-Detector → [Ransomware Detected!] → Firewall-ACL-Agent
                                ↓
                        ZMQ message:
                        {
                          "threat": "ransomware",
                          "confidence": 0.89,
                          "src_ip": "192.168.1.100",
                          "action": "BLOCK_IMMEDIATELY"
                        }
```

---

## 📊 Success Metrics

### Phase 1 Complete When:
- ✅ All 20 features extracted correctly
- ✅ Unit tests pass
- ✅ Integration test with sample PCAP works
- ✅ Memory usage <10 MB
- ✅ Processing time <1ms per packet

### Phase 2 Complete When:
- ✅ Dataset has >50K ransomware samples
- ✅ Dataset has >50K benign samples
- ✅ Model accuracy >95%
- ✅ False positive rate <1%
- ✅ ONNX model <50 MB

### Phase 3 Complete When:
- ✅ End-to-end pipeline works
- ✅ Detects WannaCry in <30 seconds
- ✅ Zero false positives on 24h benign traffic
- ✅ Latency P99 <5ms
- ✅ Memory total <200 MB (sniffer + detector)

---

## 🎯 Current Status

**Today's output:**
- ✅ 20 features designed and documented
- ✅ JSON schema created
- ✅ Implementation plan defined
- ⏳ Config updates pending
- ⏳ Code implementation pending

**Next session priorities:**
1. Update sniffer.json and ml_detector_config.json
2. Implement FlowTracker class
3. Implement DNSAnalyzer class
4. Start Phase 1A feature extraction

**Ready to start coding?** Let's begin with the FlowTracker implementation! 🏛️
