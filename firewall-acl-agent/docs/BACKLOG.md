# firewall-acl-agent - Product Backlog

## 🎯 Component Mission
High-performance endpoint for the ML Defender pipeline that receives encrypted threat detections and autonomously blocks malicious IPs using kernel-level IPSet/IPTables integration.

**Current Status**: Production-ready for crypto pipeline. Needs capacity optimization for sustained high throughput.

---

## 🔥 Priority 1: Critical for Production Scale

### P1.1: Multi-Tier Storage System
**Epic**: Unlimited capacity blocking with forensic persistence

**Problem**:
- IPSet has fixed capacity (100K max realistic)
- Evicted IPs are lost (no forensics)
- No ML retraining data
- Analysts can't investigate historical blocks

**Solution**: 3-tier architecture
```
Tier 1: IPSet (kernel, fast, limited)
  ↓ eviction
Tier 2: SQLite (disk, unlimited, queryable)
  ↓ aggregation
Tier 3: Parquet (archive, compressed, ML training)
```

**Technical Design**:
```cpp
// New component: BlockHistoryDB
class BlockHistoryDB {
    void store_block(const BlockEvent& event);
    void store_eviction(const std::string& ip, const EvictionReason& reason);
    std::vector<BlockEvent> query_ip(const std::string& ip);
    std::vector<BlockEvent> query_timerange(time_t start, time_t end);
    void export_to_parquet(const std::string& path, time_t cutoff);
};

// Schema
CREATE TABLE blocked_ips (
    ip TEXT PRIMARY KEY,
    first_seen INTEGER,
    last_seen INTEGER,
    block_count INTEGER,
    total_packets INTEGER,
    total_bytes INTEGER,
    max_confidence REAL,
    attack_types TEXT,  -- JSON array
    evicted INTEGER DEFAULT 0,
    eviction_reason TEXT
);

CREATE INDEX idx_last_seen ON blocked_ips(last_seen);
CREATE INDEX idx_block_count ON blocked_ips(block_count);
```

**Acceptance Criteria**:
- [ ] SQLite database created on startup
- [ ] Every IP added to ipset also logged to SQLite
- [ ] Evicted IPs marked with eviction_reason
- [ ] Query API: "has_been_blocked(ip)" returns history
- [ ] Daily export to Parquet with compression
- [ ] Retention policy: 30 days in SQLite, forever in Parquet

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: RAG integration (need persistent data)

---

### P1.2: Async Queue + Worker Pool for IPSet Operations
**Epic**: Sustained high throughput (1K+ IPs/sec)

**Problem**:
- Current: Synchronous `ipset restore --exist` in batch processor
- At 364 IPs/sec, queue backed up to 16,690 entries
- Blocking operations cause backpressure
- Single-threaded bottleneck

**Solution**: Producer-consumer pattern with worker pool

**Technical Design**:
```cpp
class AsyncBatchProcessor {
private:
    // Lock-free queue
    boost::lockfree::queue<BlockEvent> event_queue_;
    
    // Worker pool
    std::vector<std::thread> workers_;
    std::atomic<bool> running_{true};
    
    // Batch accumulator per worker
    struct WorkerState {
        std::vector<std::string> batch;
        std::chrono::steady_clock::time_point last_flush;
    };
    
    void worker_loop(int worker_id) {
        WorkerState state;
        while (running_) {
            BlockEvent event;
            if (event_queue_.pop(event)) {
                state.batch.push_back(event.ip);
                
                // Flush conditions
                if (state.batch.size() >= batch_size_ ||
                    time_since(state.last_flush) > flush_interval_) {
                    flush_batch(state.batch);
                    state.batch.clear();
                    state.last_flush = now();
                }
            }
        }
    }
    
    void flush_batch(const std::vector<std::string>& ips) {
        // Non-blocking: ipset restore --exist
        ipset_wrapper_.add_batch_async(ips);
    }
};
```

**Configuration**:
```json
{
  "async_processor": {
    "worker_threads": 4,
    "queue_size": 100000,
    "batch_size_per_worker": 100,
    "flush_interval_ms": 500,
    "backpressure_threshold": 80000
  }
}
```

**Acceptance Criteria**:
- [ ] Lock-free queue (boost::lockfree or folly)
- [ ] Configurable worker pool (2-8 threads)
- [ ] Each worker maintains own batch
- [ ] Parallel `ipset restore` calls
- [ ] Backpressure metric: queue depth %
- [ ] Graceful shutdown: flush all pending batches
- [ ] Benchmark: 1K+ IPs/sec sustained

**Estimated Effort**: 5 days
**Depends On**: None
**Blocks**: High-throughput production deployment

---

### P1.3: Capacity Monitoring & Auto-Eviction
**Epic**: Prevent ipset overflow with intelligent eviction

**Problem**:
- No monitoring of ipset capacity usage
- When full, blocking stops (security hole)
- No alerts to operators
- No automatic remediation

**Solution**: Thresholds + eviction strategies

**Technical Design**:
```cpp
class CapacityMonitor {
private:
    struct Thresholds {
        float warning = 0.70;    // 70% full
        float critical = 0.85;   // 85% full  
        float emergency = 0.95;  // 95% full
    };
    
    void check_capacity() {
        int current = ipset_.get_entry_count();
        int max = config_.max_elements;
        float usage = float(current) / max;
        
        if (usage >= thresholds_.emergency) {
            evict_aggressive(max * 0.20);  // Free 20%
            alert("EMERGENCY: IPSet at 95%, evicted 20%");
        } else if (usage >= thresholds_.critical) {
            evict_lru(max * 0.15);  // Free 15%
            alert("CRITICAL: IPSet at 85%, evicted 15%");
        } else if (usage >= thresholds_.warning) {
            log_warning("IPSet at 70% capacity");
        }
    }
    
    void evict_lru(int count) {
        // Get oldest IPs by timeout
        auto entries = ipset_.list_with_timeouts();
        std::sort(entries.begin(), entries.end(), 
                  [](auto& a, auto& b) { return a.timeout < b.timeout; });
        
        for (int i = 0; i < count && i < entries.size(); ++i) {
            block_history_db_.store_eviction(entries[i].ip, "LRU");
            ipset_.remove(entries[i].ip);
        }
    }
};
```

**Eviction Strategies**:
1. **LRU** (Least Recently Used): Evict oldest by timeout
2. **LFU** (Least Frequently Used): Evict by packet count
3. **Score-based**: `score = confidence × recency × packet_count`

**Acceptance Criteria**:
- [ ] Monitor capacity every 10 seconds
- [ ] WARNING at 70%: log only
- [ ] CRITICAL at 85%: evict 15% via LRU
- [ ] EMERGENCY at 95%: evict 20% aggressively
- [ ] All evictions logged to BlockHistoryDB
- [ ] Metrics exported to Prometheus
- [ ] Alerts sent to Slack/email

**Estimated Effort**: 2 days
**Depends On**: P1.1 (BlockHistoryDB for eviction logging)
**Blocks**: Production deployment without supervision

---

## 🔧 Priority 2: Operational Excellence

### P2.1: Runtime Configuration via etcd
**Epic**: Adjust capacity and timeouts without restart

**Current**: All config requires restart
```json
{
  "ipsets": {
    "blacklist": {
      "max_elements": 100000,  // Fixed at startup
      "timeout": 300            // Fixed at startup
    }
  }
}
```

**Target**: Hot-reload from etcd
```
/config/firewall/ipset_capacity → 500000  (change without restart)
/config/firewall/timeout → 600            (change without restart)
```

**Technical Design**:
```cpp
class EtcdConfigWatcher {
    void watch_config_changes() {
        etcd_client_.watch("/config/firewall/", [this](auto& response) {
            for (auto& event : response.events) {
                if (event.key == "/config/firewall/ipset_capacity") {
                    int new_capacity = std::stoi(event.value);
                    adjust_ipset_capacity(new_capacity);
                    FIREWALL_LOG_INFO("Capacity adjusted via etcd", 
                                      "new_capacity", new_capacity);
                }
                // Similar for timeout, eviction_threshold, etc.
            }
        });
    }
    
    void adjust_ipset_capacity(int new_capacity) {
        // Note: ipset can't resize live, need recreation
        // Strategy: create new set, migrate entries, swap
        ipset_.create_temp_set(new_capacity);
        ipset_.copy_entries_to_temp();
        ipset_.swap_active_set();
    }
};
```

**Acceptance Criteria**:
- [ ] Watch etcd keys: capacity, timeout, eviction_threshold
- [ ] Apply changes without restart
- [ ] Log all config changes
- [ ] Validate new values before applying
- [ ] Rollback on validation failure

**Estimated Effort**: 3 days
**Depends On**: etcd-client integration (already done)
**Blocks**: Dynamic capacity management

---

### P2.2: Prometheus Metrics Exporter
**Epic**: Production-grade observability

**Current**: Logs only
```
FIREWALL_LOG_INFO("Periodic metrics", "ips_blocked", 197);
```

**Target**: Prometheus endpoint
```
# HELP firewall_ips_blocked_total Total IPs blocked
# TYPE firewall_ips_blocked_total counter
firewall_ips_blocked_total 197

# HELP firewall_ipset_capacity_usage IPSet capacity usage ratio
# TYPE firewall_ipset_capacity_usage gauge
firewall_ipset_capacity_usage{set="blacklist"} 0.82
```

**Technical Design**:
```cpp
#include <prometheus/counter.h>
#include <prometheus/gauge.h>
#include <prometheus/registry.h>
#include <prometheus/exposer.h>

class MetricsExporter {
private:
    prometheus::Exposer exposer_;
    std::shared_ptr<prometheus::Registry> registry_;
    
    // Counters
    prometheus::Family<prometheus::Counter>& ips_blocked_family_;
    prometheus::Counter& ips_blocked_;
    
    // Gauges
    prometheus::Family<prometheus::Gauge>& capacity_family_;
    prometheus::Gauge& capacity_usage_;
    
public:
    MetricsExporter(int port) : exposer_{"0.0.0.0:" + std::to_string(port)} {
        registry_ = std::make_shared<prometheus::Registry>();
        exposer_.RegisterCollectable(registry_);
        
        ips_blocked_family_ = prometheus::BuildCounter()
            .Name("firewall_ips_blocked_total")
            .Register(*registry_);
        ips_blocked_ = ips_blocked_family_.Add({});
        
        // Similar for other metrics
    }
    
    void increment_ips_blocked(int count) {
        ips_blocked_.Increment(count);
    }
    
    void set_capacity_usage(float usage) {
        capacity_usage_.Set(usage);
    }
};
```

**Metrics to Export**:
```
Counters:
  - firewall_ips_blocked_total
  - firewall_batches_flushed_total
  - firewall_ipset_failures_total
  - firewall_crypto_errors_total
  
Gauges:
  - firewall_ipset_capacity_usage
  - firewall_queue_depth
  - firewall_zmq_messages_per_sec
  
Histograms:
  - firewall_batch_flush_duration_seconds
  - firewall_decryption_duration_seconds
```

**Acceptance Criteria**:
- [ ] Metrics endpoint on port 9090
- [ ] All critical metrics exported
- [ ] Grafana dashboard JSON template
- [ ] Alerting rules for Prometheus

**Estimated Effort**: 2 days
**Depends On**: None
**Blocks**: Production monitoring

---

### P2.3: Health Check Endpoint
**Epic**: Kubernetes readiness/liveness probes

**Current**: Internal health checks only (logs)
```cpp
bool healthy = perform_health_checks(...);  // No external API
```

**Target**: HTTP endpoint for K8s
```
GET /health
→ 200 OK if healthy
→ 503 Service Unavailable if degraded

GET /ready
→ 200 OK if ready to accept traffic
→ 503 if initializing or shutting down
```

**Technical Design**:
```cpp
#include <httplib.h>

class HealthCheckServer {
private:
    httplib::Server server_;
    std::atomic<bool> ready_{false};
    std::atomic<bool> healthy_{true};
    
public:
    void start(int port) {
        server_.Get("/health", [this](auto& req, auto& res) {
            if (healthy_.load()) {
                res.set_content("OK", "text/plain");
                res.status = 200;
            } else {
                res.set_content("DEGRADED", "text/plain");
                res.status = 503;
            }
        });
        
        server_.Get("/ready", [this](auto& req, auto& res) {
            if (ready_.load()) {
                res.set_content("READY", "text/plain");
                res.status = 200;
            } else {
                res.set_content("NOT_READY", "text/plain");
                res.status = 503;
            }
        });
        
        server_.listen("0.0.0.0", port);
    }
    
    void set_ready(bool ready) { ready_.store(ready); }
    void set_healthy(bool healthy) { healthy_.store(healthy); }
};
```

**Acceptance Criteria**:
- [ ] HTTP server on port 8080
- [ ] `/health` endpoint (liveness)
- [ ] `/ready` endpoint (readiness)
- [ ] K8s deployment YAML with probes

**Estimated Effort**: 1 day
**Depends On**: None
**Blocks**: Kubernetes deployment

---

## 📊 Priority 3: Forensics & Intelligence

### P3.1: Block Query API
**Epic**: REST API for IP block history

**Use Case**: Analyst queries "Has 192.168.1.100 been blocked before?"

**Technical Design**:
```cpp
server_.Get("/api/v1/blocks/:ip", [this](auto& req, auto& res) {
    std::string ip = req.path_params.at("ip");
    auto history = block_db_.query_ip(ip);
    
    json response = {
        {"ip", ip},
        {"total_blocks", history.block_count},
        {"first_seen", history.first_seen},
        {"last_seen", history.last_seen},
        {"total_packets", history.total_packets},
        {"currently_blocked", ipset_.contains(ip)},
        {"attack_types", history.attack_types}
    };
    
    res.set_content(response.dump(), "application/json");
});
```

**Endpoints**:
```
GET  /api/v1/blocks/:ip           - Get IP history
GET  /api/v1/blocks?since=<ts>    - List recent blocks
GET  /api/v1/stats                - Overall statistics
POST /api/v1/whitelist/:ip        - Add to whitelist
```

**Acceptance Criteria**:
- [ ] RESTful API with JSON responses
- [ ] Query by IP, timerange, attack type
- [ ] Pagination for large results
- [ ] Authentication (JWT or API key)

**Estimated Effort**: 3 days
**Depends On**: P1.1 (BlockHistoryDB)
**Blocks**: Analyst tooling

---

### P3.2: Recidivism Detection
**Epic**: Identify repeat offenders for permanent bans

**Problem**: Some IPs return after timeout expires

**Solution**: Track recidivism, auto-promote to permanent block

**Technical Design**:
```cpp
class RecidivismDetector {
    void check_recidivism(const std::string& ip) {
        auto history = db_.query_ip(ip);
        
        if (history.block_count >= config_.recidivism_threshold) {
            // Promote to permanent block
            ipset_.add_permanent(ip);  // timeout=0
            db_.mark_permanent(ip);
            
            FIREWALL_LOG_WARN("IP promoted to permanent block",
                "ip", ip,
                "block_count", history.block_count,
                "reason", "recidivism");
        }
    }
};
```

**Configuration**:
```json
{
  "recidivism": {
    "enabled": true,
    "threshold": 5,           // 5 blocks = permanent
    "time_window_hours": 24   // Within 24h
  }
}
```

**Acceptance Criteria**:
- [ ] Track block count per IP in SQLite
- [ ] Auto-promote to permanent at threshold
- [ ] Log all promotions
- [ ] Manual override API

**Estimated Effort**: 2 days
**Depends On**: P1.1 (BlockHistoryDB)
**Blocks**: Advanced threat management

---

## 🎨 Priority 4: Nice to Have

### P4.1: Web Dashboard
**Epic**: Real-time visualization

**Features**:
- Live ipset usage gauge
- Real-time block rate chart
- Recent blocks table
- Top blocked IPs
- Map visualization (GeoIP)

**Tech Stack**: React + WebSocket + Chart.js

**Estimated Effort**: 5 days

---

### P4.2: GeoIP Integration
**Epic**: Geographic attribution of threats

**Solution**: MaxMind GeoIP2 database
```cpp
auto location = geoip_.lookup(ip);
// → {country: "CN", city: "Beijing", asn: 4134}
```

**Estimated Effort**: 2 days

---

### P4.3: Threat Intelligence Feeds
**Epic**: Integrate external blocklists

**Sources**:
- AlienVault OTX
- AbuseIPDB
- Spamhaus DROP
- Emerging Threats

**Estimated Effort**: 3 days

---

## 📈 Performance Targets

### Current Performance (Day 52)
- ✅ Throughput: 364 events/sec (tested)
- ✅ Crypto: 0 errors at 36K events
- ✅ CPU: 54% max
- ✅ Memory: 127 MB

### Production Targets
- 🎯 Throughput: 1,000 events/sec sustained
- 🎯 Latency: <10ms p99 (detection → block)
- 🎯 Capacity: 500K IPs in ipset
- 🎯 Uptime: 99.9% (8.76h downtime/year)
- 🎯 Data retention: 30 days SQLite, unlimited Parquet

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] BatchProcessor (async queue)
- [ ] BlockHistoryDB (SQLite ops)
- [ ] CapacityMonitor (eviction logic)
- [ ] IPSetWrapper (mock kernel ops)

### Integration Tests
- [ ] End-to-end: ZMQ → decrypt → block → verify
- [ ] Stress: 1K events/sec for 1 hour
- [ ] Chaos: Kill etcd mid-operation
- [ ] Capacity: Fill ipset, verify eviction

### Benchmarks
- [ ] Throughput: events/sec
- [ ] Latency: p50, p95, p99
- [ ] Memory: RSS, VSZ over time
- [ ] CPU: % utilization

---

## 🚀 Release Roadmap

### v1.1 (2 weeks) - Production Scale
- P1.1: Multi-tier storage
- P1.2: Async queue + worker pool
- P1.3: Capacity monitoring

**Goal**: Handle 1K+ events/sec sustained

### v1.2 (1 week) - Observability
- P2.1: Runtime config via etcd
- P2.2: Prometheus metrics
- P2.3: Health check endpoint

**Goal**: Production monitoring ready

### v1.3 (1 week) - Intelligence
- P3.1: Block query API
- P3.2: Recidivism detection

**Goal**: Forensic analysis capability

### v2.0 (Future) - Advanced
- P4.1: Web dashboard
- P4.2: GeoIP
- P4.3: Threat feeds

**Goal**: Enterprise features

---

**Via Appia Quality**: Built to last decades 🏛️