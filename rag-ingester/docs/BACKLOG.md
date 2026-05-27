# rag-ingester - Product Backlog

## 🎯 Component Mission
Continuously monitor ML Defender component logs, parse structured events, and ingest them into the RAG vector database for intelligent querying and system analysis.

**Current Status**: Ingesting ml-detector logs. Needs firewall-acl-agent integration for complete picture.

---

## 🔥 Priority 1: Complete System Coverage

### P1.1: Firewall Log Parser & Ingestion
**Epic**: Ingest firewall-acl-agent logs for ground truth blocking data

**Problem**: RAG only has ml-detector predictions, missing actual blocking outcomes
```
Current RAG knowledge:
  ✅ What ml-detector predicted (detection)
  ❌ What firewall actually blocked (action)
  ❌ How long IPs were blocked (duration)
  ❌ Packets/bytes dropped (impact)
  ❌ Eviction events (capacity)
```

**Solution**: Parse firewall-agent.log and cross-reference with detections

**Technical Design**:

```python
# rag-ingester/parsers/firewall_parser.py

import re
from datetime import datetime
from typing import Dict, List, Optional

class FirewallLogParser:
    """Parse firewall-acl-agent logs for RAG ingestion"""
    
    PATTERNS = {
        # IP blocking events
        'ip_blocked': re.compile(
            r'Added IP directly to batch.*'
            r'ip=(?P<ip>\d+\.\d+\.\d+\.\d+).*'
            r'confidence=(?P<confidence>\d+\.\d+)'
        ),
        
        # Batch operations
        'batch_flush': re.compile(
            r'Batch flush successful.*'
            r'batch_size=(?P<batch_size>\d+).*'
            r'ips_blocked=(?P<ips_blocked>\d+)'
        ),
        
        # Capacity issues
        'ipset_full': re.compile(
            r'Batch flush failed.*'
            r'error=(?P<error>.*)'
        ),
        
        # Eviction events
        'eviction': re.compile(
            r'IPSet eviction.*'
            r'evicted_count=(?P<count>\d+).*'
            r'strategy=(?P<strategy>\w+)'
        ),
        
        # System state dumps
        'state_dump': re.compile(
            r'System State Dump.*'
            r'events_processed=(?P<events>\d+).*'
            r'ipset_failures=(?P<failures>\d+).*'
            r'crypto_errors=(?P<crypto_errors>\d+)'
        ),
        
        # Timestamp extraction
        'timestamp': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)'
        )
    }
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single log line"""
        
        # Extract timestamp
        ts_match = self.PATTERNS['timestamp'].match(line)
        if not ts_match:
            return None
        
        timestamp = datetime.fromisoformat(ts_match.group('timestamp'))
        
        # Try each pattern
        for event_type, pattern in self.PATTERNS.items():
            if event_type == 'timestamp':
                continue
                
            match = pattern.search(line)
            if match:
                return {
                    'type': f'firewall_{event_type}',
                    'timestamp': timestamp,
                    'data': match.groupdict(),
                    'raw_line': line
                }
        
        return None
    
    def parse_to_documents(self, log_file: str) -> List[Dict]:
        """Convert log file to RAG-ingestible documents"""
        documents = []
        
        with open(log_file) as f:
            for line in f:
                event = self.parse_line(line)
                if not event:
                    continue
                
                # Create natural language summary
                doc_text = self._event_to_natural_language(event)
                
                documents.append({
                    'text': doc_text,
                    'metadata': {
                        'source': 'firewall-acl-agent',
                        'event_type': event['type'],
                        'timestamp': event['timestamp'].isoformat(),
                        **event['data']
                    }
                })
        
        return documents
    
    def _event_to_natural_language(self, event: Dict) -> str:
        """Convert structured event to natural language for RAG"""
        
        if event['type'] == 'firewall_ip_blocked':
            return f"""
            IP {event['data']['ip']} was blocked by the firewall on 
            {event['timestamp']} with confidence score {event['data']['confidence']}.
            This blocking action was taken autonomously by the firewall-acl-agent
            component after receiving a threat detection from ml-detector.
            """
        
        elif event['type'] == 'firewall_batch_flush':
            return f"""
            Firewall batch operation completed on {event['timestamp']}.
            Batch size: {event['data']['batch_size']} IPs.
            Successfully blocked: {event['data']['ips_blocked']} IPs.
            This batch operation added multiple IPs to the kernel IPSet in a single
            atomic operation for efficiency.
            """
        
        elif event['type'] == 'firewall_ipset_full':
            return f"""
            CRITICAL: IPSet capacity limit reached on {event['timestamp']}.
            Error: {event['data']['error']}.
            The firewall's blocking capacity is exhausted. New threats cannot be
            blocked until older entries expire or are evicted. This represents a
            potential security gap.
            """
        
        elif event['type'] == 'firewall_eviction':
            return f"""
            IPSet eviction occurred on {event['timestamp']}.
            Evicted count: {event['data']['count']} IPs.
            Strategy: {event['data']['strategy']}.
            To free up capacity, the firewall removed older blocked IPs using the
            {event['data']['strategy']} eviction strategy. Evicted IPs are logged
            to the database for forensic analysis.
            """
        
        elif event['type'] == 'firewall_state_dump':
            return f"""
            Firewall system state snapshot on {event['timestamp']}.
            Total events processed: {event['data']['events']}.
            IPSet operation failures: {event['data']['failures']}.
            Crypto/decryption errors: {event['data']['crypto_errors']}.
            This periodic snapshot provides insight into the firewall's operational
            health and performance metrics.
            """
        
        return f"Firewall event of type {event['type']} at {event['timestamp']}"
```

**Configuration**:
```json
{
  "watchers": [
    {
      "name": "ml-detector",
      "path": "/vagrant/logs/lab/ml-detector*.log",
      "parser": "MLDetectorParser",
      "enabled": true
    },
    {
      "name": "firewall-acl-agent",
      "path": "/vagrant/logs/lab/firewall-agent.log",
      "parser": "FirewallLogParser",
      "enabled": true
    }
  ],
  "cross_reference": {
    "enabled": true,
    "detection_to_block": {
      "match_fields": ["ip"],
      "time_window_seconds": 60,
      "link_type": "detection_resulted_in_block"
    }
  }
}
```

**Cross-Reference Logic**:
```python
class CrossReferencer:
    """Link related events across different components"""
    
    def link_detection_to_block(self, 
                                detection_event: Dict, 
                                block_events: List[Dict]) -> Optional[str]:
        """
        Find if a detection led to a block.
        
        Returns enriched text explaining the relationship.
        """
        detection_ip = detection_event['metadata']['ip']
        detection_time = datetime.fromisoformat(detection_event['metadata']['timestamp'])
        
        for block in block_events:
            if block['metadata'].get('ip') != detection_ip:
                continue
            
            block_time = datetime.fromisoformat(block['metadata']['timestamp'])
            time_diff = abs((block_time - detection_time).total_seconds())
            
            if time_diff <= 60:  # Within 1 minute
                return f"""
                LINKED EVENT: The ml-detector detection of IP {detection_ip} 
                (confidence {detection_event['metadata']['confidence']}) 
                resulted in a firewall block {time_diff:.1f} seconds later.
                This demonstrates the end-to-end pipeline: detection → encryption →
                transmission → decryption → autonomous blocking.
                """
        
        return None
```

**Acceptance Criteria**:
- [ ] FirewallLogParser parses all event types from firewall-agent.log
- [ ] Natural language summaries generated for RAG
- [ ] Cross-reference detection → block events within 1 min window
- [ ] File watcher monitors firewall-agent.log for new entries
- [ ] Incremental ingestion (only new lines since last run)
- [ ] Error handling for malformed log lines
- [ ] Metrics: events parsed, documents ingested, cross-references found

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: P1.2 (forensic queries), P1.3 (ML retraining data)

---

### P1.2: Forensic Query Examples
**Epic**: Pre-built queries for common investigations

**Problem**: Analysts don't know what questions to ask the RAG

**Solution**: Query library with examples

**Forensic Queries**:

```python
FORENSIC_QUERIES = {
    "ip_investigation": {
        "template": "What happened to IP {ip} on {date}?",
        "example": "What happened to IP 192.168.1.100 on 2026-02-08?",
        "expected": """
        - Detected by ml-detector at 07:35:10 (confidence 0.95, DDoS attack)
        - Blocked by firewall at 07:35:11 (1 second latency)
        - Remained blocked for 5 minutes (timeout)
        - Dropped 1,523 packets, 156KB data
        - Not evicted (capacity available)
        """
    },
    
    "detection_efficacy": {
        "template": "What percentage of detections resulted in successful blocks?",
        "expected": "98.5% of detections resulted in confirmed blocks"
    },
    
    "false_positives": {
        "template": "Were any internal IPs blocked by mistake?",
        "expected": "3 internal IPs (10.0.0.15, 10.0.0.22, 10.0.0.31) blocked with low confidence (<0.7)"
    },
    
    "capacity_incidents": {
        "template": "Show all times the IPSet was full",
        "expected": "IPSet reached capacity 2 times: Feb 8 07:40, Feb 8 08:15"
    },
    
    "recidivism": {
        "template": "Which IPs were unblocked but returned within 24 hours?",
        "expected": "47 IPs returned after timeout: [list]"
    },
    
    "crypto_health": {
        "template": "Were there any encryption/decryption failures?",
        "expected": "0 crypto errors across 36,000 events (100% success rate)"
    },
    
    "top_attackers": {
        "template": "What are the top 10 most frequently blocked IPs?",
        "expected": "[Ranked list with block counts]"
    }
}
```

**Implementation**:
```python
# rag-ingester/query_library.py

class QueryLibrary:
    """Pre-built queries for common use cases"""
    
    def run_forensic_query(self, query_name: str, **params) -> str:
        """Execute a pre-built query with parameters"""
        template = FORENSIC_QUERIES[query_name]
        query_text = template['template'].format(**params)
        
        # Query the RAG
        result = rag_client.query(query_text)
        return result
    
    def list_available_queries(self) -> List[Dict]:
        """Show all available pre-built queries"""
        return [
            {
                'name': name,
                'description': query['template'],
                'example': query.get('example', '')
            }
            for name, query in FORENSIC_QUERIES.items()
        ]
```

**Acceptance Criteria**:
- [ ] Library of 10+ forensic queries
- [ ] CLI tool: `rag-query forensic ip_investigation --ip 1.2.3.4`
- [ ] Documentation with examples
- [ ] Test suite validating expected results

**Estimated Effort**: 2 days
**Depends On**: P1.1 (firewall logs ingested)
**Blocks**: Analyst adoption

---

### P1.3: ML Retraining Data Export
**Epic**: Export ground truth data for model retraining

**Problem**: ML models need feedback loop
```
ml-detector predicts → firewall blocks → need to know accuracy
```

**Solution**: Export (prediction, actual_block, outcome) tuples

**Technical Design**:
```python
class MLTrainingExporter:
    """Export RAG data for ML retraining"""
    
    def export_training_data(self, 
                            start_date: datetime,
                            end_date: datetime,
                            output_file: str):
        """
        Export dataset:
        - Features from ml-detector
        - Confidence scores
        - Actual blocking outcome (ground truth)
        - Packets dropped (impact measurement)
        """
        
        # Query RAG for linked events
        query = f"""
        Find all ml-detector detections between {start_date} and {end_date}
        that were linked to firewall blocking events.
        """
        
        events = rag_client.query_structured(query)
        
        # Build training dataset
        dataset = []
        for event in events:
            dataset.append({
                'ip': event['ip'],
                'timestamp': event['detection_timestamp'],
                'features': event['ml_features'],  # 83 features
                'predicted_confidence': event['ml_confidence'],
                'predicted_attack_type': event['ml_attack_type'],
                'actually_blocked': event['block_confirmed'],
                'block_duration_sec': event['block_duration'],
                'packets_dropped': event.get('packets_dropped', 0),
                'false_positive': event.get('whitelisted_later', False)
            })
        
        # Export to Parquet
        import pyarrow.parquet as pq
        table = pa.Table.from_pylist(dataset)
        pq.write_table(table, output_file)
```

**Use Cases**:
1. **Model validation**: Compare predictions vs actual blocks
2. **Threshold tuning**: Find optimal confidence cutoff
3. **Feature importance**: Which features correlate with real threats?
4. **False positive reduction**: Identify patterns in mistakes

**Acceptance Criteria**:
- [ ] Export Parquet with schema: [features, prediction, outcome]
- [ ] CLI: `rag-export training --start 2026-02-01 --end 2026-02-28`
- [ ] Automatically link detection → block events
- [ ] Include metadata: packets_dropped, block_duration
- [ ] Validation: ensure no data leakage (test/train split)

**Estimated Effort**: 3 days
**Depends On**: P1.1 (firewall logs), P1.2 (cross-referencing)
**Blocks**: ML model improvement

---

## 🔧 Priority 2: Operational Excellence

### P2.1: Incremental Ingestion (Avoid Re-parsing)
**Epic**: Only parse new log entries, not entire files

**Current Problem**: Re-parses entire log file on each run (inefficient)

**Solution**: Track file position and only read new lines

**Technical Design**:
```python
import os

class IncrementalWatcher:
    """Track file position to avoid re-parsing"""
    
    def __init__(self, state_file: str = ".ingester_state.json"):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)
    
    def get_new_lines(self, filepath: str) -> Iterator[str]:
        """Yield only new lines since last read"""
        
        # Get last position
        last_pos = self.state.get(filepath, {}).get('position', 0)
        last_inode = self.state.get(filepath, {}).get('inode', None)
        
        # Check if file was rotated
        current_inode = os.stat(filepath).st_ino
        if last_inode and current_inode != last_inode:
            # File rotated, start from beginning
            last_pos = 0
        
        # Read from last position
        with open(filepath) as f:
            f.seek(last_pos)
            for line in f:
                yield line
            
            # Save new position
            new_pos = f.tell()
            self.state[filepath] = {
                'position': new_pos,
                'inode': current_inode,
                'last_read': datetime.now().isoformat()
            }
        
        self._save_state()
```

**Acceptance Criteria**:
- [ ] State persisted in `.ingester_state.json`
- [ ] Only new lines parsed on each run
- [ ] Handle file rotation (log rotation)
- [ ] Resume from crash (state file intact)
- [ ] Metrics: lines_skipped, lines_parsed

**Estimated Effort**: 1 day
**Depends On**: None
**Blocks**: Efficient continuous ingestion

---

### P2.2: Real-Time Ingestion (inotify/fswatch)
**Epic**: Ingest logs as they're written (near-real-time)

**Current**: Cron job every N minutes
**Target**: Sub-second latency from log write to RAG ingestion

**Technical Design**:
```python
import inotify.adapters

class RealtimeWatcher:
    """Watch log files for changes and ingest immediately"""
    
    def __init__(self, watch_paths: List[str]):
        self.inotify = inotify.adapters.Inotify()
        
        for path in watch_paths:
            self.inotify.add_watch(path)
    
    def watch(self):
        """Block and wait for file changes"""
        for event in self.inotify.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            
            if 'IN_MODIFY' in type_names:
                # File was modified, parse new lines
                self.ingest_new_lines(os.path.join(path, filename))
```

**Acceptance Criteria**:
- [ ] inotify (Linux) or fswatch (macOS) integration
- [ ] Sub-second latency from log write to RAG
- [ ] Batch writes every 1 second (don't spam RAG)
- [ ] Graceful handling of rapid writes

**Estimated Effort**: 2 days
**Depends On**: P2.1 (incremental ingestion)
**Blocks**: Real-time analytics

---

### P2.3: Error Handling & Retry Logic
**Epic**: Resilient ingestion even when RAG is down

**Problem**: If RAG database is unavailable, ingestion fails

**Solution**: Retry with exponential backoff, dead-letter queue

**Technical Design**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientIngester:
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    def ingest_document(self, doc: Dict):
        """Ingest with automatic retry"""
        try:
            rag_client.add_document(doc)
        except ConnectionError as e:
            logging.error(f"RAG unavailable: {e}, retrying...")
            raise  # Trigger retry
    
    def handle_failed_document(self, doc: Dict):
        """Dead-letter queue for persistent failures"""
        with open("failed_ingestions.jsonl", "a") as f:
            f.write(json.dumps(doc) + "\n")
        
        logging.error(f"Document failed after retries, written to DLQ")
```

**Acceptance Criteria**:
- [ ] Retry up to 5 times with exponential backoff
- [ ] Dead-letter queue for persistent failures
- [ ] Metrics: retry_count, dlq_size
- [ ] Manual replay tool for DLQ

**Estimated Effort**: 1 day
**Depends On**: None
**Blocks**: Production reliability

---

## 📊 Priority 3: Advanced Analytics

### P3.1: Trend Detection
**Epic**: Identify patterns and anomalies

**Examples**:
- "IPSet capacity trending upward (running out of space)"
- "Crypto errors spiked to 5% (usually 0%)"
- "Blocking rate increased 300% in last hour (DDoS?)"

**Technical Design**:
```python
class TrendDetector:
    """Detect anomalies and trends in ingested data"""
    
    def detect_capacity_trend(self, window_hours: int = 24):
        query = f"IPSet capacity usage over last {window_hours} hours"
        timeseries = rag_client.query_timeseries(query)
        
        # Linear regression
        slope = np.polyfit(timeseries.x, timeseries.y, 1)[0]
        
        if slope > 0.05:  # 5% increase per hour
            return Alert(
                severity="WARNING",
                message=f"IPSet capacity growing at {slope*100}%/hour"
            )
    
    def detect_error_spike(self):
        recent_errors = rag_client.query("crypto_errors in last 1 hour")
        baseline_errors = rag_client.query("crypto_errors in last 24 hours")
        
        if recent_errors > baseline_errors * 3:
            return Alert(
                severity="CRITICAL",
                message=f"Crypto errors spiked 300%: investigate immediately"
            )
```

**Acceptance Criteria**:
- [ ] Trend detection for capacity, errors, throughput
- [ ] Anomaly detection using baseline comparison
- [ ] Alert generation for significant trends
- [ ] Integration with Slack/email

**Estimated Effort**: 3 days
**Depends On**: P1.1 (firewall logs with metrics)
**Blocks**: Proactive operations

---

## 🎨 Priority 4: Nice to Have

### P4.1: Web UI for Query Building
**Epic**: Visual query builder for non-technical users

**Features**:
- Drag-and-drop query construction
- Time range picker
- Field filters (IP, attack type, confidence)
- Export to CSV/JSON

**Estimated Effort**: 5 days

---

### P4.2: Scheduled Reports
**Epic**: Automated daily/weekly reports

**Examples**:
- "Daily Threat Summary: 1,234 IPs blocked, 0 capacity issues"
- "Weekly Top Attackers: [list]"

**Estimated Effort**: 2 days

---

### P4.3: JSONL Bug Fix (ml-detector)
**Epic**: Fix ml-detector's malformed JSONL output

**Problem**: ml-detector occasionally writes invalid JSONL
**Solution**: Stricter validation + repair tool

**Estimated Effort**: 1 day

---

## 📈 Performance Targets

### Current
- ✅ Parses ml-detector logs
- ❌ Does NOT parse firewall logs yet

### Target (After P1.1)
- 🎯 Ingest both ml-detector + firewall logs
- 🎯 Cross-reference 95%+ of detection → block events
- 🎯 Real-time ingestion (<1 sec latency)
- 🎯 Handle 10K events/hour sustained

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] FirewallLogParser (all event types)
- [ ] CrossReferencer (detection → block linking)
- [ ] IncrementalWatcher (file position tracking)

### Integration Tests
- [ ] End-to-end: Log write → parse → RAG insert → query
- [ ] Cross-reference accuracy: validate links are correct
- [ ] File rotation handling

---

## 🚀 Release Roadmap

### v1.1 (1 week) - Firewall Integration
- P1.1: Firewall log parser
- P1.2: Forensic queries
- P2.1: Incremental ingestion

**Goal**: Complete system coverage (ml-detector + firewall)

### v1.2 (3 days) - Real-time
- P2.2: inotify/fswatch
- P2.3: Error handling

**Goal**: Production-grade reliability

### v1.3 (1 week) - Analytics
- P1.3: ML retraining export
- P3.1: Trend detection

**Goal**: Close the ML feedback loop

---

**Via Appia Quality**: The RAG is the L1 cache of system truth 🏛️