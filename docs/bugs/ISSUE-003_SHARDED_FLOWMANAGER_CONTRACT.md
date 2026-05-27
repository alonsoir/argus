# ISSUE-003: ShardedFlowManager - Design Contract

**Created:** 25 Enero 2026  
**Authors:** Alonso + Claude + ChatGPT + DeepSeek + Qwen  
**Status:** PRE-IMPLEMENTATION CONTRACT

---

## 🎯 Design Invariants (NON-NEGOTIABLE)

These invariants MUST hold. Any solution that violates them is rejected.

### **Invariant 1: No Global Blocking**
```
RULE: Insert operation NEVER blocks globally
COMPLIANCE: At most ONE shard locked per operation
VIOLATION: If insert() acquires more than 1 mutex → REJECTED
```

### **Invariant 2: Read/Write Isolation**
```
RULE: Read in shard A NEVER blocks write in shard B
COMPLIANCE: shared_mutex per shard, independent locking
VIOLATION: If global lock exists → REJECTED
```

### **Invariant 3: Temporal Order is Local**
```
RULE: Timestamp ordering ONLY guaranteed within a shard
COMPLIANCE: Global ordering is reconstructed view, not system property
VIOLATION: If code assumes global order → REJECTED
```

### **Invariant 4: Cleanup Never Blocks Hot Paths**
```
RULE: Cleanup thread NEVER waits on hot shards
COMPLIANCE: try_lock() only, skip if busy
VIOLATION: If cleanup uses lock() (blocking) → REJECTED
```

---

## 🏗️ Architecture Decision

### **Shard Count: Dynamic**
```cpp
// ✅ CORRECT: Derived from hardware
size_t shard_count = std::max(
    4u,  // Minimum for small systems
    std::thread::hardware_concurrency()
);

// ❌ WRONG: Magic constant
static constexpr size_t NUM_SHARDS = 64;
```

**Rationale:** System runs on Raspberry Pi ($35) to enterprise (256 cores).

### **Shard Selection: Hash-Based (NOT Time-Based)**
```cpp
// ✅ CORRECT: Hash never changes
size_t shard_id = std::hash<FlowKey>{}(key) % shard_count;

// ❌ WRONG: Temporal sharding (brittle)
size_t shard_id = (timestamp / 60000) % shard_count;
```

**Rationale:** Flow keys are stable, timestamps drift.

---

## 📊 Per-Shard Structure
```cpp
struct Shard {
    std::shared_mutex mtx;                    // Read-heavy workload
    std::deque<FlowRecord> events;            // O(1) push_back, O(1) pop_front
    std::atomic<uint64_t> last_seen_ns;       // Lock-free read for cleanup
    std::atomic<size_t> size;                 // Lock-free size check
};
```

**Design Choices:**
- `deque` over `unordered_map`: Sequential access for cleanup
- `last_seen_ns`: Allows skipping cold shards WITHOUT lock
- `shared_mutex`: Readers don't block readers

---

## 🧹 Cleanup Strategy (THE CRITICAL PART)

### **Golden Rule:**
```
Cleanup thread NEVER blocks hot shards.
If try_lock() fails → SKIP shard.
```

### **Implementation Pattern:**
```cpp
void cleanup_expired(std::chrono::seconds ttl) {
    auto now = std::chrono::steady_clock::now();
    
    for (size_t i = 0; i < shards_.size(); ++i) {
        auto& shard = shards_[i];
        
        // 1. Lock-free check: is shard cold enough?
        auto last_seen = shard.last_seen_ns.load();
        if (now - last_seen < ttl) {
            continue;  // Skip hot shard
        }
        
        // 2. Non-blocking try_lock
        std::unique_lock lock(shard.mtx, std::try_to_lock);
        if (!lock.owns_lock()) {
            continue;  // Skip busy shard, try next iteration
        }
        
        // 3. Fast partial cleanup (NOT exhaustive)
        size_t removed = 0;
        auto it = shard.events.begin();
        while (it != shard.events.end() && removed < 100) {
            if (now - it->timestamp > ttl) {
                it = shard.events.erase(it);
                removed++;
            } else {
                ++it;
            }
        }
        
        // 4. Release lock immediately
        lock.unlock();
    }
}
```

**Key Properties:**
- ✅ Never blocks hot shards (`try_lock`)
- ✅ Partial cleanup (limit 100 per shard)
- ✅ Lock released quickly
- ✅ Skips busy shards gracefully

---

## 📖 Aggregated Queries (Safe Pattern)

### **Anti-Pattern (WRONG):**
```cpp
// ❌ Holds ALL locks while processing
std::vector<FlowRecord> get_all() {
    std::vector<FlowRecord> result;
    for (auto& shard : shards_) {
        std::shared_lock lock(shard.mtx);
        // ... copy data ...
        // Lock held during append!
    }
    return result;
}
```

### **Safe Pattern (CORRECT):**
```cpp
// ✅ Lock → Copy → Unlock → Process
std::vector<FlowRecord> get_all() {
    std::vector<std::vector<FlowRecord>> per_shard;
    per_shard.reserve(shards_.size());
    
    // Phase 1: Quick locks, local copies
    for (auto& shard : shards_) {
        std::shared_lock lock(shard.mtx);
        per_shard.push_back(shard.events);
        // Lock released here!
    }
    
    // Phase 2: Merge WITHOUT locks
    std::vector<FlowRecord> result;
    for (auto& local : per_shard) {
        result.insert(result.end(), local.begin(), local.end());
    }
    
    // Phase 3: Sort/filter WITHOUT locks
    std::sort(result.begin(), result.end());
    return result;
}
```

---

## ✅ Success Criteria

### **Performance Targets:**
```
Metric                  Current    Target     Method
─────────────────────────────────────────────────────
Insert throughput       500K/s     8M/s       Benchmark
Lookup latency P99      100µs      <10µs      Histogram
Memory spikes           2GB→4GB    Stable     Massif
Lock contention         High       Low        perf stat
Cleanup impact P95      N/A        <1ms       Trace
Scalability (cores)     1x         Linear     Benchmark
```

### **Validation Tests:**
```cpp
// Test 1: Scalability
for (size_t shards : {4, 8, 16, 32, 64}) {
    auto throughput = benchmark_insert(shards);
    EXPECT_GT(throughput, baseline * shards * 0.8);  // 80% linear scaling
}

// Test 2: Cleanup doesn't block
{
    auto start_cleanup = std::async(cleanup_expired, 30s);
    auto throughput_during = benchmark_insert(64);
    EXPECT_GT(throughput_during, baseline * 0.95);  // <5% impact
}

// Test 3: Read doesn't block write
{
    auto reader = std::async(get_all);
    auto writer = std::async(insert_batch, 10000);
    // Both complete without deadlock
}
```

---

## 🚫 What NOT to Do (Phase 2A)

**Deferred to future optimization:**
- ❌ Lock-free structures (RCU, hazard pointers)
- ❌ Custom allocators
- ❌ SIMD optimizations
- ❌ Kernel bypass (io_uring)

**Priority order:**
```
1. Correct   ← Phase 2A
2. Stable    ← Phase 2A
3. Measurable← Phase 2A
4. Fast      ← Phase 2B+
```

---

## 🏛️ Via Appia Quality

**Design Philosophy:**
> "Lo simple es bello. Primero correcto, luego rápido."

**This Contract Ensures:**
- ✅ Clear invariants (testable)
- ✅ No magic constants (configurable)
- ✅ Cleanup won't bite us (non-blocking)
- ✅ Queries are safe (lock discipline)

**Before ANY code:**
1. Review this contract
2. Validate each invariant
3. Design tests first
4. Implement incrementally

---

**End of Contract**

**Next Step:** Implement `sharded_flow_manager.hpp` following this contract.  
**Reviewers:** All invariants must be verified before merge.