# Documentation Package - Firewall ACL Agent

## Summary
Comprehensive documentation of design decisions, performance metrics, and optimization paths for the Firewall ACL Agent. This enables data-driven iteration per "Via Appia Quality" philosophy.

---

## Documents Created

### 1. DESIGN_DECISIONS.md
**Purpose:** Record WHY we made each design choice, trade-offs, and when to revisit.

**Key decisions documented:**
- System commands vs libipset C API → Commands chosen
- No deduplication lookups → Math proves it's 200x faster to skip
- Test performance "failures" → Acceptable because not used in production
- Batch flush strategy → Time + size based batching
- Thread-local architecture → Zero mutex contention (Phase 0 proven)

**Value:**
- Prevents bike-shedding in code reviews
- Clear optimization paths IF stress tests show need
- Documents what we DON'T know yet (requires measurement)

---

### 2. PERFORMANCE_METRICS.md
**Purpose:** Define WHAT to measure during stress tests to make data-driven decisions.

**Metrics defined:**
- `detection_to_block_latency_ms` → P99 < 200ms target
- `ips_blocked_per_second` → 10K/sec sustained target
- `pending_ips_queue_size` → Monitor for backups
- `batch_add_latency_ms` → ipset restore performance
- System resources → CPU, memory tracking

**Stress test scenarios:**
1. Sustained load (10K IPs/sec for 10 min)
2. Burst attack (100K IPs/sec spike)
3. Duplicate heavy (98% duplicates)
4. Distributed DDoS (100K unique IPs/sec) ← THE CONTRACT TEST
5. Memory pressure (1 hour, no expiration)

**Value:**
- Clear success/failure criteria
- Optimization decision tree based on results
- No guessing what "good enough" means

---

### 3. ipset_wrapper.hpp (Updated)
**Purpose:** Document performance characteristics inline in code.

**Key additions:**
- ⚠️  Warning on `test()` method that it's 3ms slow
- Explains WHY it's slow (shell process overhead)
- Explains WHY it's ACCEPTABLE (not used in production)
- Mathematical proof that skipping lookups is 300x faster
- References to DESIGN_DECISIONS.md

**Value:**
- Future developers understand trade-offs immediately
- No confusion about "why is test() so slow?"
- Links to deeper documentation for context

---

## Decision Philosophy

### Current Status: Phase 1 Implementation
```
┌─────────────────────────────────────────┐
│ We are HERE:                            │
│                                         │
│ [Implementation] → [Stress Test] → [?] │
│       ✅              Next       TBD    │
└─────────────────────────────────────────┘
```

### Our Approach
1. ✅ **Build what's adequate NOW** (simple, maintainable)
2. 🔄 **Measure in realistic conditions** (distributed stress tests)
3. ⏳ **Iterate based on DATA** (not speculation)

### NOT Premature Optimization
We explicitly chose:
- ❌ NOT to use libipset C API (complex, hard to maintain)
- ❌ NOT to implement lookup caching (unnecessary until proven)
- ❌ NOT to parallelize (single thread may be sufficient)

**UNTIL** stress tests prove we need these optimizations.

---

## What Happens Next

### Step 1: Complete Implementation
- ✅ ipset_wrapper (done)
- ⏳ iptables_wrapper (next)
- ⏳ ZMQ subscriber
- ⏳ Batch processor
- ⏳ Main agent loop

### Step 2: Distributed Stress Tests
Run all 5 scenarios from PERFORMANCE_METRICS.md:
```
Scenario 1: Sustained Load      → MUST PASS
Scenario 2: Burst Attack        → MUST PASS  
Scenario 3: Duplicate Heavy     → MUST PASS
Scenario 4: Distributed DDoS    → CONTRACT TEST (critical)
Scenario 5: Memory Pressure     → MUST PASS
```

### Step 3: Data-Driven Decision
```
IF all scenarios pass:
  ✅ DONE - Ship to production with monitoring
  Document actual performance characteristics
  
ELSE IF Scenario 4 (DDoS) fails:
  → Follow optimization decision tree
  → Level 1: Parameter tuning (1 hour)
  → Level 2: Parallel processing (1 day)
  → Level 3: libipset C API (2 days)
  
ELSE IF other scenarios fail:
  → Specific action plan in PERFORMANCE_METRICS.md
```

---

## Optimization Decision Tree

Documented in detail in PERFORMANCE_METRICS.md, summary:

```
START: Run stress tests

├─ All pass? 
│  └─ ✅ DONE - Current implementation adequate
│
├─ Throughput < 10K IPs/sec?
│  └─ Check CPU usage
│     ├─ High CPU? Optimize code
│     └─ Low CPU? I/O bound → Consider libipset
│
├─ Queue backing up?
│  └─ Tune batch parameters
│     OR parallel processing
│
└─ Memory issues?
   └─ Implement IP expiration
```

---

## Key Metrics to Watch

### During Stress Tests
```
CRITICAL:
  detection_to_block_latency_ms (P99)
  ips_blocked_per_second (sustained)
  pending_ips_queue_size (max)

IMPORTANT:
  batch_add_latency_ms (P99)
  cpu_usage_percent (average)
  memory_usage_mb

INFORMATIONAL:
  batch_size_histogram
  batch_dedup_ratio
```

### Decision Points
```
P99 latency > 500ms          → CRITICAL
Throughput < 10K IPs/sec     → CRITICAL
Queue depth > 10K IPs        → CRITICAL
CPU usage > 90%              → Optimization needed
Memory > 500MB for 1M IPs    → Tuning needed
```

---

## Why This Documentation Matters

### For Current Development
- Prevents premature optimization
- Focuses effort on implementation
- Clear path forward

### For Stress Testing
- Know exactly what to measure
- Know exactly what "success" means
- Clear decision points

### For Future Iteration
- Documented trade-offs prevent re-litigating decisions
- Clear optimization paths if needed
- Evidence-based prioritization

### For Team Communication
- Stakeholders understand why we built it this way
- Code reviewers have context
- Future maintainers understand intent

---

## Quotes from Design Documents

> "This is Via Appia Quality: Build what's needed now, measure obsessively,
> iterate methodically."

> "The lookup only would be useful if:
>  - Cost lookup < Cost add duplicado × Tasa duplicados
>  - 3000μs < 10μs × 0.90
>  - 3000μs < 9μs
>  - ❌ FALSO"

> "We will follow this implementation, adequate for this moment, and if we
> detect after stress tests that we don't meet requirements, we'll revisit,
> but then KNOWING that we have data supporting the hypothesis to rewrite
> the algorithm."

---

## Files to Review

1. **DESIGN_DECISIONS.md** (10 min read)
    - Start here for full context
    - Understand all 5 major decisions
    - See optimization paths

2. **PERFORMANCE_METRICS.md** (15 min read)
    - See what we'll measure
    - Understand stress test scenarios
    - Review decision tree

3. **ipset_wrapper.hpp** (code review)
    - See inline documentation
    - Understand performance characteristics
    - Links to other docs

---

## Next Immediate Action

**Continue with iptables_wrapper.cpp**

The documentation is complete. We have:
- ✅ Clear design rationale
- ✅ Measurable success criteria
- ✅ Optimization decision tree
- ✅ Inline code documentation

Now we build the rest of the system and let the stress tests tell us if we need to optimize.

**This is engineering, not speculation.** 🎯