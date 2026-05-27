# Baseline Configuration - Functional First

**Created:** 25 Enero 2026  
**Goal:** Establish minimal working configuration  
**Philosophy:** "60 km/h on country road" - stable, not fast

---

## 🎯 Design Principles

1. **Conservatism over Performance**
    - Values chosen for stability, not speed
    - Headroom for unexpected load spikes
    - Easy to understand and debug

2. **No Magic Numbers**
    - Every value has documented rationale
    - Rationale based on component behavior
    - Not based on benchmarks (yet)

3. **Scientific Method (Future)**
    - Baseline establishes measurement reference
    - Phase 2 will optimize empirically
    - Phase 3 will automate tuning

---

## 📊 Component Configurations

### **Sniffer (fast-path-sniffer)**
```json
{
  "flow_manager": {
    "type": "simple",
    "max_flows": 10000,
    "cleanup_interval_seconds": 30,
    "flow_ttl_seconds": 300
  },
  
  "zeromq": {
    "publisher": {
      "endpoint": "tcp://*:5571",
      "hwm": 10000,
      "linger_ms": 1000
    }
  },
  
  "threads": {
    "packet_processors": 2,
    "feature_extractors": 2
  }
}
```

**Rationale:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `max_flows` | 10K | Typical small network has <1K active flows |
| `hwm` | 10K | 10 seconds buffer at 1K events/sec |
| `packet_processors` | 2 | One per NIC (dual-NIC setup) |
| `feature_extractors` | 2 | Match packet processors (1:1 ratio) |

---

### **ML-Detector**
```json
{
  "zeromq": {
    "subscriber": {
      "endpoint": "tcp://localhost:5571",
      "hwm": 10000,
      "conflate": false
    }
  },
  
  "processing": {
    "threads": 2,
    "batch_size": 50,
    "timeout_ms": 1000
  },
  
  "models": {
    "ddos": { "threads": 1 },
    "ransomware": { "threads": 1 },
    "traffic": { "threads": 1 },
    "internal": { "threads": 1 }
  }
}
```

**Rationale:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `hwm` | 10K | Match sniffer (symmetry) |
| `threads` | 2 | Conservative (4-core laptop) |
| `batch_size` | 50 | Small batches = low latency |
| `model threads` | 1 | Sequential classification (simple) |

---

### **Firewall**
```json
{
  "zeromq": {
    "subscriber": {
      "endpoint": "tcp://localhost:5572",
      "hwm": 5000
    }
  },
  
  "processing": {
    "threads": 1,
    "queue_depth": 1000
  }
}
```

**Rationale:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `hwm` | 5K | Half of detector (filtered events only) |
| `threads` | 1 | Firewall is I/O bound, not CPU |
| `queue_depth` | 1K | Enough for burst handling |

---

## ✅ Validation Criteria

These are FUNCTIONAL requirements, not performance:
```markdown
Sniffer:
- [ ] Captures packets from both NICs
- [ ] Extracts 105/105 features
- [ ] Sends to ml-detector via ZMQ
- [ ] No crashes for 1 hour

ML-Detector:
- [ ] Receives events from sniffer
- [ ] Deserializes 105/105 features
- [ ] Classifies with 4 models
- [ ] Sends to firewall via ZMQ
- [ ] No crashes for 1 hour

Firewall:
- [ ] Receives classified events
- [ ] Parses decisions
- [ ] Logs actions
- [ ] No crashes for 1 hour

Integration:
- [ ] E2E latency < 100ms (P99)
- [ ] 0 ZMQ drops
- [ ] 0 segfaults
- [ ] Memory RSS stable (<2GB total)
```

---

## 🚫 What This Is NOT

- ❌ NOT optimized for throughput
- ❌ NOT tuned for latency
- ❌ NOT tested under load
- ❌ NOT benchmarked

**This is BASELINE** - the reference point for future optimization.

---

## 📈 Future Work (Phase 2)

Once baseline is stable, we will:

1. **Empirical Tuning Matrix**
    - Vary threads: 2, 4, 8
    - Vary HWM: 10K, 50K, 100K
    - Vary shards: 1, 8, 16
    - Measure: throughput, latency, CPU, memory

2. **Scientific Analysis**
    - Plot performance curves
    - Identify bottlenecks
    - Find optimal configuration

3. **Hardware Profiling**
    - Raspberry Pi profile
    - Laptop profile (current)
    - Server profile (future)

4. **Auto-Tuner (Phase 3)**
    - Detect hardware automatically
    - Generate optimal configs
    - Validate before deployment

---

## 🏛️ Via Appia Quality

> "Primero funciona. Luego rápido. Luego automático."

**Baseline Configuration embodies:**
- ✅ Conservatism (safety first)
- ✅ Clarity (no magic numbers without rationale)
- ✅ Measurability (establishes reference)
- ✅ Evolvability (designed to be tuned later)

---

**End of Baseline Configuration**

**Next:** Implement and validate functional correctness.  
**Then:** Phase 2 empirical tuning.  
**Future:** Phase 3 auto-tuner (nice to have).