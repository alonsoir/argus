## 🔍 ADR-002: Multi-Engine Provenance & Situational Intelligence

**Date:** 12 Enero 2026  
**Status:** APPROVED  
**Decision:** Extend protobuf contract to capture multiple engine verdicts  
**Proposer:** Gemini (peer reviewer)  
**Implementation:** Day 37 (before ONNX embedders)

---

### Context

Currently, the protobuf contract only stores the **final classification** result. This discards valuable information:

- **Sniffer verdict:** Fast-path decision (eBPF/XDP)
- **RandomForest verdict:** ML primary classification
- **CNN verdict:** ML secondary classification (if enabled)

**The discrepancy between engines IS the signal** for detecting:
- APTs (Advanced Persistent Threats) camouflaged as benign traffic
- 0-days (unknown attacks)
- False positives (industrial equipment with unusual patterns)

### Decision

Add `DetectionProvenance` message to protobuf contract with:
1. **Array of verdicts** - All engine opinions
2. **Reason codes** - WHY each engine decided
3. **Discrepancy score** - Measure of disagreement
4. **Final decision** - What action was taken

### Protobuf Extension

```protobuf
// network_security.proto

message EngineVerdict {
  string engine_name = 1;      // "fast-path-sniffer", "random-forest", "cnn-secondary"
  string classification = 2;   // "Benign", "DDoS", "Ransomware", etc.
  float confidence = 3;        // 0.0 - 1.0
  string reason_code = 4;      // WHY (see table below)
  uint64 timestamp_ns = 5;     // When this engine decided
}

message DetectionProvenance {
  repeated EngineVerdict verdicts = 1;  // ALL opinions
  uint64 global_timestamp_ns = 2;       // When event was logged
  string final_decision = 3;            // "ALLOW", "DROP", "ALERT"
  float discrepancy_score = 4;          // 0.0 (agree) - 1.0 (disagree)
  string logic_override = 5;            // If human/RAG forced decision
}

// Add to NetworkSecurityEvent:
message NetworkSecurityEvent {
  // ... existing fields (101 features) ...
  
  DetectionProvenance provenance = 20;  // NEW
}
```

### Reason Codes (Gemini's Table)

| Code | Meaning | Value for RAG/LLM |
|------|---------|-------------------|
| `SIG_MATCH` | Exact signature match (blacklist) | **Immediate block priority** |
| `STAT_ANOMALY` | Statistical deviation (Z-score high) | Unusual behavior, not necessarily malicious |
| `PCA_OUTLIER` | Vector outside normal cloud (latent space) | **Critical for 0-day detection** 🎯 |
| `PROT_VIOLATION` | Protocol malformation (impossible TCP flags) | Low-level technical attack |
| `ENGINE_CONFLICT` | Sniffer vs ML disagree significantly | **High-priority alert for LLM analysis** 🚨 |

**Implementation:**
```cpp
// reason_codes.hpp
namespace ml_defender {

enum class ReasonCode {
    SIG_MATCH,         // Signature match
    STAT_ANOMALY,      // Statistical anomaly
    PCA_OUTLIER,       // Outside normal latent space
    PROT_VIOLATION,    // Protocol violation
    ENGINE_CONFLICT,   // Engines disagree
    UNKNOWN
};

const char* to_string(ReasonCode code) {
    switch(code) {
        case ReasonCode::SIG_MATCH:       return "SIG_MATCH";
        case ReasonCode::STAT_ANOMALY:    return "STAT_ANOMALY";
        case ReasonCode::PCA_OUTLIER:     return "PCA_OUTLIER";
        case ReasonCode::PROT_VIOLATION:  return "PROT_VIOLATION";
        case ReasonCode::ENGINE_CONFLICT: return "ENGINE_CONFLICT";
        default:                          return "UNKNOWN";
    }
}

} // namespace ml_defender
```

### Implementation Strategy

**Phase 1: ml-detector (writes provenance)**
```cpp
void RAGLogger::log_event(
    const PacketAnalysis& sniffer_verdict,
    const RandomForestResult& rf_result,
    const CNNResult& cnn_result
) {
    NetworkSecurityEvent event;
    
    // ... existing feature extraction ...
    
    // NEW: Fill provenance
    auto* prov = event.mutable_provenance();
    
    // 1. Sniffer verdict
    auto* v1 = prov->add_verdicts();
    v1->set_engine_name("fast-path-sniffer");
    v1->set_classification(sniffer_verdict.classification);
    v1->set_confidence(sniffer_verdict.confidence);
    v1->set_reason_code(to_string(sniffer_verdict.reason));
    v1->set_timestamp_ns(sniffer_verdict.timestamp_ns);
    
    // 2. RandomForest verdict
    auto* v2 = prov->add_verdicts();
    v2->set_engine_name("random-forest-primary");
    v2->set_classification(rf_result.classification);
    v2->set_confidence(rf_result.confidence);
    v2->set_reason_code(to_string(rf_result.reason));
    v2->set_timestamp_ns(now_ns());
    
    // 3. CNN verdict (if enabled)
    if (cnn_enabled_) {
        auto* v3 = prov->add_verdicts();
        v3->set_engine_name("cnn-secondary");
        v3->set_classification(cnn_result.classification);
        v3->set_confidence(cnn_result.confidence);
        v3->set_reason_code(to_string(cnn_result.reason));
        v3->set_timestamp_ns(now_ns());
    }
    
    // 4. Calculate discrepancy
    prov->set_discrepancy_score(
        calculate_discrepancy(sniffer_verdict, rf_result, cnn_result)
    );
    
    // 5. Final decision
    prov->set_final_decision(firewall_action);  // "ALLOW", "DROP", "ALERT"
    prov->set_global_timestamp_ns(now_ns());
    
    // Encrypt, compress, write...
}

float calculate_discrepancy(/* verdicts */) {
    // Simple: max confidence delta
    // Example: Sniffer 95% Benign, ML 60% Malicious → 0.85 discrepancy
    float max_delta = 0.0f;
    for (auto& v1 : verdicts) {
        for (auto& v2 : verdicts) {
            if (v1.classification != v2.classification) {
                float delta = std::abs(v1.confidence - v2.confidence);
                max_delta = std::max(max_delta, delta);
            }
        }
    }
    return max_delta;
}
```

**Phase 2: rag-ingester (reads provenance)**
```cpp
// event_loader.cpp
Event EventLoader::load(const std::string& filepath) {
    // Decrypt, decompress, parse protobuf...
    
    Event event;
    event.id = proto_event.event_id();
    event.features = extract_101_features(proto_event);
    
    // NEW: Parse provenance
    if (proto_event.has_provenance()) {
        const auto& prov = proto_event.provenance();
        
        for (const auto& verdict : prov.verdicts()) {
            EngineVerdict v;
            v.engine_name = verdict.engine_name();
            v.classification = verdict.classification();
            v.confidence = verdict.confidence();
            v.reason_code = verdict.reason_code();
            v.timestamp_ns = verdict.timestamp_ns();
            
            event.verdicts.push_back(v);
        }
        
        event.discrepancy_score = prov.discrepancy_score();
        event.final_decision = prov.final_decision();
    }
    
    return event;
}
```

**Phase 3: Embedders use discrepancy**
```cpp
// chronos_embedder.cpp
std::vector<float> ChronosEmbedder::embed(const Event& event) {
    std::vector<float> input = event.features;  // 101 features
    
    // NEW: Add meta-features
    input.push_back(event.discrepancy_score);   // Feature 102
    input.push_back(event.verdicts.size());     // Feature 103 (num engines)
    
    // ONNX inference: 103 features → 512-d
    return run_inference(input);
}
```

### Use Cases

**Case 1: APT Camouflaged**
```
Sniffer: "Benign" (95%) - reason: SIG_MATCH (whitelist)
RF:      "Exfiltration" (55%) - reason: STAT_ANOMALY (timing)
CNN:     "Suspicious" (62%) - reason: PCA_OUTLIER (latent)

→ discrepancy_score: 0.85 (HIGH)
→ RAG flags for human review
→ LLM: "Sniffer fooled by TLS, but timing+PCA suspicious"
→ Action: ALERT + monitor
```

**Case 2: Industrial False Positive**
```
Sniffer: "Benign" (99%) - reason: SIG_MATCH (known IoT)
RF:      "Anomaly" (40%) - reason: STAT_ANOMALY (Z-score)
CNN:     "Benign" (90%) - reason: (normal pattern)

→ discrepancy_score: 0.35 (MEDIUM)
→ Campus A: LLM learns "RF always alerts on this equipment"
→ Action: Auto-whitelist campus A, monitor campus B
```

**Case 3: 0-Day Detection**
```
Sniffer: "Benign" (80%) - reason: (no signature)
RF:      "Unknown" (50%) - reason: STAT_ANOMALY
CNN:     "Malicious" (70%) - reason: PCA_OUTLIER (never seen)

→ discrepancy_score: 0.75 (HIGH)
→ reason_code: PCA_OUTLIER (critical!)
→ RAG: "No engine is sure, but CNN detects novelty"
→ Action: Escalate to human (possible 0-day)
→ If confirmed → Global vaccine
```

### Benefits

1. **Situational Intelligence** - Not just "what" but "why" and "how sure"
2. **0-day Detection** - PCA_OUTLIER + ENGINE_CONFLICT = red flag
3. **Adaptive Learning** - LLM learns campus-specific patterns
4. **Reduced False Positives** - Context helps distinguish noise from threats
5. **Forensics** - Complete audit trail of all engine decisions
6. **Vaccine Quality** - Discrepancies help prioritize which events to analyze

### Risks & Mitigations

**Risk 1:** Increased protobuf size
- **Mitigation:** Compression (LZ4) reduces overhead
- **Estimate:** +50 bytes per event → <5% increase after compression

**Risk 2:** Processing overhead
- **Mitigation:** Discrepancy calculation is O(n²) but n≤3 engines
- **Estimate:** <1ms per event

**Risk 3:** Complexity
- **Mitigation:** Backward compatible (optional provenance field)
- **Rollout:** Gradual (ml-detector first, rag-ingester later)

### Success Metrics

- ✅ Reduced false positive rate (target: -20%)
- ✅ 0-day detection improved (measure: time to detection)
- ✅ LLM can explain decisions (qualitative: operator feedback)
- ✅ Vaccine quality improved (measure: global vs local vaccine ratio)

### Implementation Timeline

**Day 37 Morning (2-3 hours):**
- [ ] Update `network_security.proto`
- [ ] Regenerate protobuf (make proto-unified)
- [ ] Update ml-detector (fill provenance)
- [ ] Add encryption to ml-detector (BONUS)
- [ ] Test with synthetic data

**Day 37 Afternoon (3-4 hours):**
- [ ] Update rag-ingester (parse provenance)
- [ ] Update embedders (use discrepancy as feature)
- [ ] Implement ONNX embedders
- [ ] Test end-to-end

---

**Status:** APPROVED - Ready for implementation  
**Next Step:** Update protobuf contract  
**Blocking:** None

🏛️ **Via Appia:** This transforms the system from binary decision to situational intelligence - exactly the kind of architectural decision that builds systems for 2000 years.