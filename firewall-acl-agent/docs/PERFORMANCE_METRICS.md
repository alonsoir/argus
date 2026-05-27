# Firewall ACL Agent - Performance Metrics & Observability

## Purpose
Define what to measure during distributed stress tests to make data-driven optimization decisions.

**Status:** Pre-Stress Test  
**Review After:** Distributed stress test completion

---

## Critical Success Metrics

### 1. End-to-End Latency

**Metric:** `detection_to_block_latency_ms`

**Definition:** Time from ML detector outputting a detection until the IP is blocked in kernel ipset.

**Measurement:**
```cpp
// Pseudo-code
auto t0 = detection.timestamp;  // From ML detector
ipset_wrapper.add_batch(ips);
auto t1 = now();
metric = (t1 - t0).milliseconds();
```

**Targets:**
- P50: < 50ms
- P95: < 150ms
- P99: < 200ms
- P99.9: < 500ms

**Decision Points:**
```
IF P99 > 500ms:
  ACTION: Reduce BATCH_TIME_THRESHOLD
  
IF P99 > 200ms AND batch_size_avg < 100:
  ACTION: Batches too small, increase threshold
  
IF P99 > 200ms AND batch_size_avg > 500:
  ACTION: Investigate ipset restore performance
```

---

### 2. Throughput

**Metric:** `ips_blocked_per_second`

**Definition:** Rate of unique IPs successfully added to ipset.

**Measurement:**
```cpp
// Rolling window
uint64_t ips_added_last_second = 0;
std::chrono::seconds window = 1s;

// Update every second
metric = ips_added_last_second;
```

**Targets:**
- Sustained: > 10K IPs/sec (for 1M pkt/sec @ 1% attack rate)
- Burst: > 50K IPs/sec
- Peak: > 100K IPs/sec

**Decision Points:**
```
IF sustained < 10K IPs/sec:
  ACTION: CRITICAL - Optimization required
  → Check CPU usage
  → Check batch_add_latency
  → Consider parallel processing

IF burst < 50K IPs/sec:
  ACTION: May struggle with DDoS spikes
  → Consider larger batches
  → Check system load
```

---

### 3. Queue Depth

**Metric:** `pending_ips_queue_size`

**Definition:** Number of IPs waiting to be added to ipset.

**Measurement:**
```cpp
// Current size of accumulator
size_t current = pending_ips_.size();
size_t max = pending_ips_max_size_;  // Historical max

metrics.set("pending_ips_current", current);
metrics.set("pending_ips_max", max);
```

**Targets:**
- Average: < 500 IPs
- P95: < 2000 IPs
- P99: < 5000 IPs
- Max: < 10000 IPs

**Decision Points:**
```
IF max > 10K:
  ACTION: Queue backing up, system can't keep up
  → Check ipset_batch_add_latency
  → Consider parallel processors
  → Reduce BATCH_SIZE_THRESHOLD

IF average > 2K AND latency OK:
  ACTION: Batches too small
  → Increase BATCH_SIZE_THRESHOLD
```

---

### 4. Batch Performance

**Metric:** `batch_add_latency_ms`

**Definition:** Time to execute `ipset restore < batch_file`.

**Measurement:**
```cpp
auto t0 = now();
auto result = execute_command("ipset restore < " + tmpfile);
auto t1 = now();
metric = (t1 - t0).milliseconds();
```

**Targets:**
- P50: < 5ms (for ~500 IPs)
- P95: < 15ms
- P99: < 25ms
- P99.9: < 50ms

**Scaling:**
```
Expected latency by batch size:
  100 IPs:   ~2ms
  500 IPs:   ~5ms
  1000 IPs:  ~10ms
  5000 IPs:  ~40ms
  10K IPs:   ~80ms
```

**Decision Points:**
```
IF P99 > 50ms:
  ACTION: ipset restore is slow
  → Check system load
  → Check ipset hashsize/maxelem config
  → Consider smaller batches
  → LAST RESORT: libipset C API

IF latency scales linearly with size:
  STATUS: ✅ Normal behavior
  
IF latency scales super-linearly:
  ACTION: Hash collisions or memory pressure
  → Tune ipset hashsize
```

---

### 5. Batch Characteristics

**Metrics:**
- `batch_size_histogram`: Distribution of batch sizes
- `batch_flush_reason`: time vs size triggered
- `batch_dedup_ratio`: duplicates removed / total IPs

**Measurement:**
```cpp
// Histogram buckets
buckets = [0-100, 100-500, 500-1000, 1000-5000, 5000+]

// Flush reason
enum FlushReason { TIME_THRESHOLD, SIZE_THRESHOLD };

// Dedup ratio
ratio = duplicates_removed / total_ips_in_batch;
```

**Decision Points:**
```
IF most batches < 100 IPs:
  ACTION: Batches too small
  → Increase BATCH_SIZE_THRESHOLD
  → Consider longer BATCH_TIME_THRESHOLD

IF most batches = max size:
  ACTION: Size limit hit frequently
  → May need larger batches
  → Or faster flush rate

IF dedup_ratio > 0.9:
  ACTION: Excellent in-memory deduplication
  STATUS: ✅ Working as designed

IF dedup_ratio < 0.3:
  ACTION: Few duplicates within batches
  → May indicate distributed attack
  → Normal for diverse botnet
```

---

### 6. System Resources

**Metrics:**
- `cpu_usage_percent`: Agent process CPU
- `memory_usage_mb`: Agent RSS
- `ipset_kernel_memory_mb`: Kernel ipset memory
- `ipset_entry_count`: Total IPs in ipset

**Targets:**
```
CPU Usage:
  Average: < 50%
  P99: < 80%
  If > 90%: Agent is bottleneck

Memory (Agent):
  RSS: < 100MB
  If > 200MB: Memory leak suspected

Memory (ipset):
  < 500MB for 1M IPs
  Linear scaling expected

Entry Count:
  Monitor growth rate
  Implement expiration if needed
```

**Decision Points:**
```
IF cpu_usage > 90% sustained:
  ACTION: Agent is bottleneck
  → Profile with perf
  → Optimize hot path
  → Consider parallel processing

IF memory_agent > 200MB:
  ACTION: Investigate memory leak
  → Check pending_ips_ growth
  → Check std::string allocations

IF ipset_memory > 1GB:
  ACTION: Too many IPs blocked
  → Implement IP expiration (timeout)
  → Consider separate sets for temp/perm blocks
```

---

## Stress Test Scenarios

### Scenario 1: Sustained Load
**Description:** Constant attack rate over extended period

**Parameters:**
- Duration: 10 minutes
- Attack rate: 10K IPs/sec
- Pattern: Distributed botnet (varied IPs)

**Expected Results:**
- Throughput: 10K IPs/sec sustained ✅
- Latency P99: < 200ms ✅
- Queue depth: Stable < 1K IPs ✅
- CPU: < 50% average ✅

**Success Criteria:** All targets met

---

### Scenario 2: Burst Attack
**Description:** Sudden spike in attack rate

**Parameters:**
- Baseline: 1K IPs/sec
- Spike: 100K IPs/sec for 10 seconds
- Return: 1K IPs/sec

**Expected Results:**
- Queue spike: May reach 5K IPs (acceptable)
- Latency spike: P99 may hit 500ms during burst
- Recovery: < 5 seconds to baseline

**Success Criteria:**
- No queue overflow
- No dropped detections
- Clean recovery

---

### Scenario 3: Duplicate Heavy
**Description:** Repetitive attack from same IPs

**Parameters:**
- Attack rate: 50K detections/sec
- Unique IPs: 1K (98% duplicates)
- Duration: 5 minutes

**Expected Results:**
- In-memory dedup: 50K → 1K IPs
- Throughput to kernel: ~1K IPs/sec
- CPU: Low (most work is hash lookup)
- Latency: Low (small batches)

**Success Criteria:**
- Efficient deduplication (>95%)
- Low resource usage

---

### Scenario 4: Distributed DDoS
**Description:** Massive diverse botnet

**Parameters:**
- Attack rate: 1M packets/sec
- Unique IPs: 100K IPs/sec (10% attack rate)
- Duration: 2 minutes

**Expected Results:**
- ⚠️ This is the STRESS TEST
- Throughput: Must sustain 100K IPs/sec
- Queue: May spike to 10K IPs
- Latency: P99 < 500ms

**Success Criteria:**
- System doesn't crash
- No queue overflow
- Metrics stabilize

**If fails:**
- CRITICAL: Optimization required
- Start optimization decision tree

---

### Scenario 5: Memory Pressure
**Description:** Long-running with no IP expiration

**Parameters:**
- Duration: 1 hour
- Attack rate: 5K new IPs/sec
- Total IPs: ~18M IPs
- Expected memory: ~5GB

**Expected Results:**
- Linear memory growth
- No performance degradation
- System remains stable

**Success Criteria:**
- ipset handles large sets
- No memory leaks
- Performance remains constant

**If fails:**
- Implement IP expiration (timeout)
- Consider set rotation strategy

---

## Instrumentation Code

### Metrics Collection
```cpp
class MetricsCollector {
public:
    // Latency tracking
    void record_latency(const std::string& operation, 
                       std::chrono::microseconds duration) {
        latencies_[operation].push_back(duration);
        
        // Keep sliding window (last 10K samples)
        if (latencies_[operation].size() > 10000) {
            latencies_[operation].erase(latencies_[operation].begin());
        }
    }
    
    // Throughput tracking
    void record_throughput(const std::string& operation, uint64_t count) {
        auto now = std::chrono::steady_clock::now();
        throughput_[operation][now] = count;
        
        // Clean old entries (>60s)
        auto cutoff = now - std::chrono::seconds(60);
        auto it = throughput_[operation].begin();
        while (it != throughput_[operation].end() && it->first < cutoff) {
            it = throughput_[operation].erase(it);
        }
    }
    
    // Percentile calculation
    std::chrono::microseconds percentile(const std::string& operation, 
                                        double p) {
        auto& samples = latencies_[operation];
        if (samples.empty()) return std::chrono::microseconds(0);
        
        std::vector<std::chrono::microseconds> sorted(samples);
        std::sort(sorted.begin(), sorted.end());
        
        size_t idx = static_cast<size_t>(p * sorted.size());
        return sorted[idx];
    }
    
    // Export for monitoring
    nlohmann::json export_metrics() {
        nlohmann::json j;
        
        for (const auto& [op, samples] : latencies_) {
            j[op]["p50"] = percentile(op, 0.50).count();
            j[op]["p95"] = percentile(op, 0.95).count();
            j[op]["p99"] = percentile(op, 0.99).count();
            j[op]["p999"] = percentile(op, 0.999).count();
            j[op]["count"] = samples.size();
        }
        
        return j;
    }
    
private:
    std::unordered_map<std::string, std::vector<std::chrono::microseconds>> latencies_;
    std::unordered_map<std::string, std::map<std::chrono::steady_clock::time_point, uint64_t>> throughput_;
};
```

### Usage Example
```cpp
class FirewallACLAgent {
private:
    MetricsCollector metrics_;
    
public:
    void process_batch() {
        auto t0 = std::chrono::steady_clock::now();
        
        // Record queue depth
        metrics_.record_gauge("pending_ips_current", pending_ips_.size());
        
        // Execute batch
        auto result = ipset_wrapper_.add_batch(set_name, entries);
        
        auto t1 = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0);
        
        // Record batch latency
        metrics_.record_latency("batch_add", duration);
        
        // Record throughput
        metrics_.record_throughput("ips_blocked", entries.size());
        
        // Log if slow
        if (duration > std::chrono::milliseconds(50)) {
            LOG_WARN("Slow batch add: {}ms for {} IPs", 
                    duration.count() / 1000, entries.size());
        }
    }
};
```

---

## Optimization Decision Tree

Based on stress test results:

```
START: Run all 5 stress test scenarios

├─ IF all scenarios pass:
│  └─ ✅ DONE - Current implementation adequate
│     Document performance characteristics
│     Move to production monitoring
│
├─ IF Scenario 1 (Sustained) fails:
│  └─ ACTION: Throughput insufficient
│     ├─ Check: CPU usage
│     │  ├─ IF > 90%: Optimize hot path
│     │  └─ IF < 50%: I/O bound
│     │     └─ Consider libipset C API
│     └─ Check: Batch latency
│        └─ IF P99 > 50ms: ipset restore is slow
│           └─ Tune ipset or consider API
│
├─ IF Scenario 2 (Burst) fails:
│  └─ ACTION: Can't handle spikes
│     └─ Increase BATCH_SIZE_THRESHOLD
│        AND/OR add queue overflow handling
│
├─ IF Scenario 3 (Duplicates) fails:
│  └─ ACTION: Deduplication inefficient
│     └─ Should not happen (std::unordered_set is efficient)
│        Investigate implementation
│
├─ IF Scenario 4 (Distributed DDoS) fails:
│  └─ ACTION: CRITICAL - Main use case fails
│     ├─ Level 1: Parameter tuning (1 hour)
│     ├─ Level 2: Parallel processing (1 day)
│     └─ Level 3: libipset C API (2 days)
│
└─ IF Scenario 5 (Memory) fails:
   └─ ACTION: Implement IP expiration
      └─ Use ipset timeout feature
         OR set rotation strategy
```

---

## Production Monitoring

Once deployed, continuously monitor:

### Real-Time Dashboard
```
┌─────────────────────────────────────────┐
│ Firewall ACL Agent - Live Metrics      │
├─────────────────────────────────────────┤
│ Throughput:    12.5K IPs/sec           │
│ Latency P99:   85ms                     │
│ Queue Depth:   234 IPs                  │
│ Batch Size:    ~500 IPs (avg)          │
│ CPU Usage:     34%                      │
│ Memory:        45MB                     │
│ Blocked IPs:   2.4M total               │
└─────────────────────────────────────────┘
```

### Alerts
```yaml
alerts:
  - name: high_latency
    condition: p99(detection_to_block_latency_ms) > 500
    severity: warning
    action: "Check system load and batch performance"
    
  - name: queue_backup
    condition: pending_ips_queue_size > 10000
    severity: critical
    action: "Agent can't keep up - investigate immediately"
    
  - name: low_throughput
    condition: ips_blocked_per_second < 1000
    severity: warning
    action: "Attack in progress but blocking slow"
    
  - name: high_cpu
    condition: cpu_usage_percent > 90
    severity: critical
    action: "Agent is bottleneck - optimize or scale"
```

---

## Conclusion

**This document provides:**
1. ✅ Clear metrics to measure
2. ✅ Targets for each metric
3. ✅ Decision points based on data
4. ✅ Stress test scenarios
5. ✅ Optimization decision tree

**After stress testing:**
- Update this document with actual results
- Document which scenarios passed/failed
- Follow decision tree for any failures
- Make optimization decisions **BASED ON DATA**

**This is empirical engineering - not speculation.**