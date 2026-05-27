# Session Summary: Ransomware Detection Design Complete
## Date: 2025-10-28 | Status: Design Phase ✅ | Next: Implementation Phase ⏳

---

## 🎯 What We Accomplished Today

### ✅ Designed 20 Critical Ransomware Features
- **Target:** Raspberry Pi 4 (1-4GB RAM)
- **Performance budget:** <500 µs inference, <50 MB memory
- **Detection goal:** Catch ransomware BEFORE encryption starts

**Feature breakdown:**
- 🔴 **6 features:** C&C Communication (DNS entropy, new IPs, beaconing)
- 🟠 **4 features:** Lateral Movement (SMB scanning, RDP brute force)
- 🟡 **4 features:** Data Exfiltration (upload spikes, burst connections)
- 🟢 **6 features:** Behavioral Anomalies (nocturnal activity, protocol diversity)

### ✅ Created 4 Technical Documents

**1. ransomware_20_features_design.md**
- Full research-backed feature design
- Rationale for each feature
- Evasion difficulty analysis
- Implementation priority (4 phases)
- Expected performance metrics

**2. ransomware_20_features.json**
- Machine-readable schema for sniffer
- Complete feature definitions with:
  - Computation formulas
  - Expected value ranges
  - Dependencies
  - Performance budgets
  - Implementation notes

**3. implementation_roadmap.md**
- 3-week phased implementation plan
- Week 1: Feature extraction infrastructure
- Week 2: Dataset preparation & training
- Week 3: Integration & testing
- Success metrics for each phase

**4. config_update_instructions.md**
- Exact sed commands to update configs
- Validation scripts
- Git commit template

---

## 📊 Technical Decisions Made

### ✅ Architecture: Option C (Hybrid)
**Rationale:** Sniffer sends packets with flow_id → ML-Detector aggregates
- **Pro:** Balance between performance and flexibility
- **Pro:** Sniffer stays lightweight (4 MB RAM target)
- **Pro:** ML-Detector can tune windows without recompiling sniffer
- **Con:** Slightly more work in detector (acceptable tradeoff)

### ✅ Feature Count: 20 (not 83)
**Rationale:** Start lean, expand for enterprise
- **RPi version:** 20 features, <50 MB model
- **Enterprise version:** 83 features, <200 MB model (future)
- **Philosophy:** "Via Appia quality" - build incrementally, test thoroughly

### ✅ Detection Strategy: Multi-Layer
**Layer 1 (Critical):** C&C detection (features 1, 2, 7)  
→ Catches ransomware at initial infection (before encryption)

**Layer 2 (High Priority):** Lateral movement + exfiltration  
→ Catches ransomware during spreading phase

**Layer 3 (Polish):** Behavioral anomalies  
→ Reduces false positives

---

## 🚀 Next Steps - Priority Order

### IMMEDIATE (Do Today)

1. **Copy files to project:**
```bash
cd ~/CLionProjects/argus

# Copy feature JSON
cp ransomware_20_features.json sniffer/config/features/

# Copy documentation
cp ransomware_20_features_design.md docs/
cp implementation_roadmap.md docs/
cp config_update_instructions.md docs/
```

2. **Update configs:**
```bash
# Follow instructions in config_update_instructions.md
# Updates sniffer.json: 83 -> 20 features
# Updates ml_detector_config.json: 82 -> 20 features
```

3. **Validate & commit:**
```bash
# Run validation script from config_update_instructions.md
# If all checks pass:
git add -A
git commit -m "feat: add ransomware detection features (20 critical)"
git tag -a v3.3.0-ransomware-features -m "Ransomware detection features v1.0"
```

4. **Verify build still works:**
```bash
make rebuild
make run-detector  # Terminal 1
make run-sniffer   # Terminal 2
# Should build cleanly (ransomware model not active yet)
```

---

### THIS WEEK (Phase 1: Feature Extraction)

**Goal:** Sniffer can extract all 20 features

**Implementation order:**
1. **Day 1-2:** Implement `FlowTracker` class
   - Track TCP flows by 5-tuple
   - Maintain byte counters, packet counts, timestamps
   - Cleanup expired flows
   - Unit tests

2. **Day 3-4:** Implement `DNSAnalyzer` class
   - Parse DNS packets
   - Calculate Shannon entropy
   - Track query rates
   - Detect NXDOMAIN failures
   - Unit tests

3. **Day 5-6:** Implement `IPWhitelist` class
   - LRU cache for known IPs (10K entries)
   - 24-hour retention
   - Fast lookup (<1 µs)
   - Unit tests

4. **Day 7:** Implement `TimeWindowAggregator`
   - Aggregate features over 30s windows
   - Call feature extractors
   - Populate protobuf
   - Integration test with sample PCAP

**Expected output:**
- ✅ All 20 features extracted from test PCAP
- ✅ Memory usage <10 MB
- ✅ Processing time <1ms per packet

---

### NEXT WEEK (Phase 2: Training)

**Goal:** Trained ONNX model ready for deployment

**Tasks:**
1. Download datasets (CTU-13, CIC-IDS2017, benign traffic)
2. Extract features from PCAPs (Python script)
3. Train RandomForest model
4. Validate: accuracy >95%, FPR <1%
5. Export to ONNX
6. Copy to `ml-detector/models/production/level2/`

**Expected output:**
- ✅ `ransomware_rf_20.onnx` model (<50 MB)
- ✅ Accuracy >95% on test set
- ✅ Inference time <500 µs

---

### WEEK AFTER (Phase 3: Integration)

**Goal:** End-to-end ransomware detection operational

**Tasks:**
1. Enable ransomware model in ml_detector_config.json
2. End-to-end testing with benign traffic (0 false positives)
3. End-to-end testing with ransomware samples (detect in <30s)
4. Performance testing under load
5. Tune thresholds if needed

**Expected output:**
- ✅ Full pipeline: Sniffer → ML-Detector → Ransomware alert
- ✅ Zero false positives on 24h benign traffic
- ✅ Detects WannaCry/Petya/NotPetya within 30 seconds
- ✅ Latency P99 <5ms

---

## 🏛️ Design Philosophy Applied

### "Via Appia Quality" - Built to Last
- ✅ **Single source of truth:** One feature definition in JSON
- ✅ **DRY principle:** No duplicate configs
- ✅ **Incremental:** 20 features now, 83 later
- ✅ **Testable:** Unit tests for each component
- ✅ **Documented:** Clear implementation notes

### "Make it Impossible to Fuck Up"
- ✅ **Validated configs:** JSON schema validation
- ✅ **Clear dependencies:** Each feature lists what it needs
- ✅ **Phase gates:** Can't proceed until previous phase passes tests
- ✅ **Rollback plan:** Can disable ransomware model anytime

### "Protect Real Businesses"
- ✅ **Detect BEFORE encryption:** Focus on C&C phase (features 1-6)
- ✅ **Low false positives:** <1% FPR target
- ✅ **Fast response:** <3ms detection-to-block budget (per Parallels.ai)
- ✅ **Resource constrained:** Works on Raspberry Pi

---

## 📊 Success Criteria

### Phase 1 Success (This Week)
- [ ] FlowTracker: Tracks 100K flows, <10 MB RAM
- [ ] DNSAnalyzer: Calculates entropy correctly
- [ ] IPWhitelist: LRU works, 10K IPs, 24h retention
- [ ] TimeWindowAggregator: All 20 features extracted
- [ ] Integration test passes with sample PCAP

### Phase 2 Success (Next Week)
- [ ] Dataset: >50K ransomware + >50K benign samples
- [ ] Model: Accuracy >95%, FPR <1%, FNR <5%
- [ ] ONNX export: <50 MB, inference <500 µs
- [ ] Validation: Test set includes zero-day samples

### Phase 3 Success (Week After)
- [ ] End-to-end: Sniffer → Detector → Alert
- [ ] Zero false positives on 24h benign traffic
- [ ] Detects known ransomware in <30 seconds
- [ ] Performance: P99 latency <5ms, total RAM <200 MB
- [ ] Ready for firewall integration (future)

---

## 🎓 Key Insights from Research

### Why These 20 Features?

**Research-backed choices:**
1. **DNS entropy** - 90%+ accuracy for DGA detection (source: CTU-13 analysis)
2. **New external IPs** - Ransomware MUST contact C&C (unavoidable)
3. **SMB diversity** - WannaCry/Petya lateral movement signature
4. **Upload/download ratio** - Double-extortion ransomware tell
5. **Protocol diversity** - Ransomware uses SMB+HTTP+DNS+TLS simultaneously

**Evasion difficulty analysis:**
- **HARD to evade:** Features 1, 4, 7, 13, 17 (core behaviors)
- **MEDIUM difficulty:** Features 2, 3, 8, 9, 11, 16, 18, 19, 20
- **EASY to evade:** Features 6, 14, 15

**Strategy:** Combine hard-to-evade with medium-difficulty for 95%+ detection

### Parallels.ai Recommendations Applied

**From their report:**
- ✅ **Sub-3ms budget:** Allocated <500 µs for inference
- ✅ **XDP fast path:** Already using eBPF in sniffer
- ✅ **Multi-scale windows:** 30s (short), 300s (medium), 600s (long)
- ✅ **INT8 quantization:** For ONNX model (future optimization)
- ✅ **Fail-closed strategy:** If detector crashes, block all (future)

---

## 🔗 Related Documents

**In this session:**
1. `/home/claude/ransomware_20_features_design.md` - Full design
2. `/home/claude/ransomware_20_features.json` - JSON schema
3. `/home/claude/implementation_roadmap.md` - 3-week plan
4. `/home/claude/config_update_instructions.md` - Config updates

**Previous sessions:**
- `MODEL_TRAINING_ROADMAP.md` - Original roadmap
- `SESSION_SUMMARY.md` - Config refactoring summary
- Parallels.ai analysis document (uploaded today)

---

## 💭 Questions to Consider

Before starting implementation:

1. **Protobuf:** Do we need to add `RansomwareFeatures` message or reuse existing fields?
2. **eBPF limits:** Can we extract DNS payloads in kernel or user-space only?
3. **TLS inspection:** Self-signed cert detection - worth the complexity?
4. **Datasets:** Do you already have CTU-13 downloaded or need to get it?
5. **Testing environment:** Do you have a safe VM to replay ransomware PCAPs?

---

## 🚀 Ready to Start Implementation?

**Immediate action items:**
1. ✅ Copy 4 documents to project directory
2. ⏳ Apply config updates (use instructions file)
3. ⏳ Validate and commit changes
4. ⏳ Start FlowTracker implementation

**Once configs are updated, next session we can:**
- Design FlowTracker class interface
- Implement first 3 critical features (dns_query_entropy, new_external_ips, smb_connection_diversity)
- Create unit tests
- Run integration test with sample PCAP

---

## 📝 Notes for Next Session

**Bring:**
- Current protobuf schema (to verify RansomwareFeatures fields)
- Sniffer code structure (to see where to add FlowTracker)
- Any questions about implementation approach

**We'll focus on:**
- Writing actual C++20 code for feature extraction
- Making it fast (<1ms per packet)
- Making it testable (unit tests for each component)
- Making it correct (matching research papers)

---

**Status:** Design phase complete ✅  
**Next:** Apply config updates, start Phase 1 implementation  
**Timeline:** Operational ransomware detector in 2-3 weeks  
**Philosophy:** Via Appia quality, one feature at a time 🏛️💙

¿Listo para empezar? 🚀
