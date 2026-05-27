# rag - Product Backlog

## 🎯 Component Mission
Intelligent vector database and query engine that provides natural language access to complete ML Defender system history, enabling forensic analysis, ML retraining, and operational intelligence.

**Current Status**: Basic RAG with ml-detector data. Needs enhancement for firewall data and advanced querying.

---

## 🔥 Priority 1: Enhanced Query Capabilities

### P1.1: Cross-Component Query Support
**Epic**: Query across ml-detector + firewall data with relationship awareness

**Problem**: Current RAG treats all documents independently
```
Query: "Show IPs detected but NOT blocked"
Current: Can't answer (no relationship linking)
Needed: Cross-reference detection vs block events
```

**Solution**: Relationship-aware embeddings and query expansion

**Technical Design**:

```python
# rag/query_engine.py

class RelationshipAwareQueryEngine:
    """Enhanced query engine with cross-component understanding"""
    
    def __init__(self, vectorstore, llm):
        self.vectorstore = vectorstore
        self.llm = llm
        self.relationship_graph = RelationshipGraph()
    
    def query(self, query_text: str) -> str:
        """
        Process query with relationship awareness:
        1. Expand query to include related concepts
        2. Retrieve from vector store
        3. Apply relationship filters
        4. Synthesize answer
        """
        
        # Detect query intent
        intent = self._classify_intent(query_text)
        
        if intent == "cross_component":
            return self._cross_component_query(query_text)
        elif intent == "forensic":
            return self._forensic_query(query_text)
        elif intent == "temporal":
            return self._temporal_query(query_text)
        else:
            return self._standard_query(query_text)
    
    def _cross_component_query(self, query: str) -> str:
        """Handle queries spanning multiple components"""
        
        # Example: "IPs detected but not blocked"
        
        # 1. Get all detections
        detections = self.vectorstore.similarity_search(
            "ml-detector detected IP",
            filter={"source": "ml-detector"}
        )
        
        # 2. Get all blocks
        blocks = self.vectorstore.similarity_search(
            "firewall blocked IP",
            filter={"source": "firewall-acl-agent"}
        )
        
        # 3. Find detections WITHOUT corresponding blocks
        detected_ips = {d.metadata['ip'] for d in detections}
        blocked_ips = {b.metadata['ip'] for b in blocks}
        unblocked = detected_ips - blocked_ips
        
        # 4. Synthesize answer
        return f"""
        Found {len(unblocked)} IPs that were detected but NOT blocked:
        {list(unblocked)[:10]}
        
        Possible reasons:
        - IPSet was full (capacity limit)
        - Low confidence score (below threshold)
        - Whitelist match
        - System error during blocking
        
        Recommended action: Investigate why these were not blocked.
        """

class RelationshipGraph:
    """Graph structure linking related events"""
    
    def __init__(self):
        self.edges = defaultdict(list)  # ip -> [events]
    
    def add_detection(self, ip: str, event: Dict):
        """Link detection event to IP"""
        self.edges[ip].append({
            'type': 'detection',
            'timestamp': event['timestamp'],
            'confidence': event['confidence'],
            'attack_type': event['attack_type']
        })
    
    def add_block(self, ip: str, event: Dict):
        """Link block event to IP"""
        self.edges[ip].append({
            'type': 'block',
            'timestamp': event['timestamp'],
            'duration': event['duration'],
            'packets_dropped': event.get('packets_dropped', 0)
        })
    
    def get_timeline(self, ip: str) -> List[Dict]:
        """Get chronological timeline for an IP"""
        events = self.edges.get(ip, [])
        return sorted(events, key=lambda e: e['timestamp'])
    
    def find_unlinked_detections(self) -> List[str]:
        """Find IPs with detection but no block"""
        unlinked = []
        for ip, events in self.edges.items():
            has_detection = any(e['type'] == 'detection' for e in events)
            has_block = any(e['type'] == 'block' for e in events)
            if has_detection and not has_block:
                unlinked.append(ip)
        return unlinked
```

**Query Examples**:

```python
# Efficacy Analysis
query("What percentage of detections resulted in blocks?")
→ "98.5% success rate: 1,234 detections, 1,216 blocks, 18 failures"

# Gap Analysis  
query("Show me IPs that were detected but not blocked")
→ "47 IPs detected but not blocked. Reasons: 23 low-confidence, 18 ipset-full, 6 whitelisted"

# Timeline Investigation
query("Complete timeline for IP 192.168.1.100")
→ """
  07:35:10 - Detected (confidence 0.95, DDoS)
  07:35:11 - Blocked (1 sec latency)
  07:35:11 - 07:40:11 - Active block (5 min)
  07:40:11 - Timeout expired, unblocked
  """

# Recidivism
query("IPs that returned after being unblocked")
→ "127 recidivist IPs: [list with return times]"
```

**Acceptance Criteria**:
- [ ] Relationship graph linking detection ↔ block events
- [ ] Cross-component queries (detection vs block)
- [ ] Timeline reconstruction for any IP
- [ ] Gap analysis (detected but not blocked)
- [ ] Recidivism detection (returned after timeout)

**Estimated Effort**: 5 days
**Depends On**: rag-ingester P1.1 (firewall logs ingested)
**Blocks**: Advanced forensic analysis

---

### P1.2: Temporal Query Engine
**Epic**: Natural language time-based queries

**Examples**:
```
"What happened yesterday?"
"Show me blocks from last week"
"IPs blocked in the last hour"
"Trend over the past 30 days"
```

**Technical Design**:

```python
import parsedatetime

class TemporalQueryEngine:
    """Parse and execute time-based queries"""
    
    def __init__(self):
        self.calendar = parsedatetime.Calendar()
    
    def parse_temporal_query(self, query: str) -> Dict:
        """Extract time range from natural language"""
        
        # Parse relative times
        time_struct, parse_status = self.calendar.parse(query)
        
        if parse_status:
            timestamp = datetime(*time_struct[:6])
            return {
                'start': timestamp,
                'end': datetime.now(),
                'timeframe': self._extract_timeframe(query)
            }
        
        return None
    
    def _extract_timeframe(self, query: str) -> str:
        """Detect timeframe: hour, day, week, month"""
        if 'hour' in query:
            return 'hour'
        elif 'day' in query or 'yesterday' in query:
            return 'day'
        elif 'week' in query:
            return 'week'
        elif 'month' in query:
            return 'month'
        return 'all'
    
    def temporal_filter(self, documents: List[Dict], 
                       start: datetime, 
                       end: datetime) -> List[Dict]:
        """Filter documents by time range"""
        filtered = []
        for doc in documents:
            doc_time = datetime.fromisoformat(doc.metadata['timestamp'])
            if start <= doc_time <= end:
                filtered.append(doc)
        return filtered

# Usage
engine = TemporalQueryEngine()

query = "Show me all blocks from yesterday"
time_range = engine.parse_temporal_query(query)
# → {start: 2026-02-07 00:00, end: 2026-02-07 23:59, timeframe: 'day'}

documents = vectorstore.similarity_search("blocked")
filtered = engine.temporal_filter(documents, time_range['start'], time_range['end'])
```

**Supported Time Expressions**:
- **Relative**: "yesterday", "last week", "past 30 days"
- **Specific**: "February 8, 2026", "2026-02-08"
- **Ranges**: "between Feb 1 and Feb 15"
- **Durations**: "last 24 hours", "past 7 days"

**Acceptance Criteria**:
- [ ] Parse natural language time expressions
- [ ] Support relative times (yesterday, last week)
- [ ] Support specific dates (2026-02-08)
- [ ] Time range filtering on queries
- [ ] Aggregate by hour/day/week/month

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: Time-based analytics

---

### P1.3: Aggregation & Statistics
**Epic**: Compute statistics over large result sets

**Problem**: Current RAG returns individual documents, no aggregation

**Solution**: Post-retrieval aggregation engine

**Technical Design**:

```python
class AggregationEngine:
    """Compute statistics over query results"""
    
    def aggregate(self, documents: List[Dict], agg_type: str) -> Dict:
        """
        Aggregation types:
        - count: Count of documents
        - group_by: Group and count by field
        - time_series: Bucket by time intervals
        - percentiles: Distribution analysis
        - top_n: Top N by field value
        """
        
        if agg_type == "count":
            return {"total": len(documents)}
        
        elif agg_type == "group_by":
            return self._group_by(documents)
        
        elif agg_type == "time_series":
            return self._time_series(documents)
        
        elif agg_type == "percentiles":
            return self._percentiles(documents)
        
        elif agg_type == "top_n":
            return self._top_n(documents)
    
    def _group_by(self, documents: List[Dict], field: str = "ip") -> Dict:
        """Group by field and count"""
        groups = defaultdict(int)
        for doc in documents:
            value = doc.metadata.get(field)
            if value:
                groups[value] += 1
        
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))
    
    def _time_series(self, documents: List[Dict], 
                     interval: str = "hour") -> Dict:
        """Bucket documents by time interval"""
        
        buckets = defaultdict(int)
        for doc in documents:
            timestamp = datetime.fromisoformat(doc.metadata['timestamp'])
            
            if interval == "hour":
                bucket = timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "day":
                bucket = timestamp.strftime("%Y-%m-%d")
            elif interval == "week":
                bucket = timestamp.strftime("%Y-W%W")
            
            buckets[bucket] += 1
        
        return dict(sorted(buckets.items()))
    
    def _top_n(self, documents: List[Dict], 
               field: str = "ip", n: int = 10) -> List[Dict]:
        """Get top N by occurrence count"""
        counts = self._group_by(documents, field)
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{"value": k, "count": v} for k, v in top]

# Usage Examples

# Count total blocks
agg = AggregationEngine()
blocks = rag.query("firewall blocks")
total = agg.aggregate(blocks, "count")
# → {"total": 1234}

# Top 10 blocked IPs
top_ips = agg.aggregate(blocks, "top_n")
# → [{"value": "1.2.3.4", "count": 47}, ...]

# Hourly time series
hourly = agg._time_series(blocks, interval="hour")
# → {"2026-02-08 07:00": 23, "2026-02-08 08:00": 45, ...}
```

**Query Examples**:
```
"How many IPs were blocked today?" 
→ Use count aggregation

"What are the top 10 most blocked IPs?"
→ Use top_n aggregation

"Show blocking rate per hour over the last day"
→ Use time_series aggregation
```

**Acceptance Criteria**:
- [ ] Count aggregation
- [ ] Group-by with counting
- [ ] Time series bucketing (hour/day/week)
- [ ] Top-N ranking
- [ ] Percentile calculation for numeric fields

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: Statistical analysis

---

## 🔧 Priority 2: Performance & Scale

### P2.1: Embedding Cache
**Epic**: Cache embeddings to avoid recomputation

**Problem**: Re-embedding same queries wastes compute

**Solution**: Redis cache for embeddings

**Technical Design**:

```python
import redis
import hashlib

class EmbeddingCache:
    """Cache embeddings in Redis"""
    
    def __init__(self, redis_url: str = "localhost:6379"):
        self.redis = redis.Redis.from_url(redis_url)
        self.ttl = 3600  # 1 hour
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding or None"""
        key = self._hash(text)
        cached = self.redis.get(key)
        
        if cached:
            return np.frombuffer(cached, dtype=np.float32)
        return None
    
    def set_embedding(self, text: str, embedding: np.ndarray):
        """Cache embedding"""
        key = self._hash(text)
        self.redis.setex(
            key,
            self.ttl,
            embedding.astype(np.float32).tobytes()
        )
    
    def _hash(self, text: str) -> str:
        """Hash text to cache key"""
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()}"

# Integration
class CachedEmbedder:
    def __init__(self, embedding_model, cache):
        self.model = embedding_model
        self.cache = cache
    
    def embed(self, text: str) -> np.ndarray:
        # Try cache first
        cached = self.cache.get_embedding(text)
        if cached is not None:
            return cached
        
        # Compute and cache
        embedding = self.model.embed(text)
        self.cache.set_embedding(text, embedding)
        return embedding
```

**Acceptance Criteria**:
- [ ] Redis integration
- [ ] Cache hit/miss metrics
- [ ] TTL configurable
- [ ] Cache invalidation strategy
- [ ] Performance: 10x faster for cached queries

**Estimated Effort**: 2 days
**Depends On**: None
**Blocks**: High-throughput querying

---

### P2.2: Index Optimization (FAISS)
**Epic**: Faster similarity search with FAISS

**Current**: Chroma with basic indexing
**Target**: FAISS with IVF + PQ for 100K+ documents

**Technical Design**:

```python
import faiss

class FAISSVectorStore:
    """High-performance vector store using FAISS"""
    
    def __init__(self, dimension: int = 768):
        # IVF (Inverted File) with PQ (Product Quantization)
        self.dimension = dimension
        self.index = faiss.IndexIVFPQ(
            faiss.IndexFlatL2(dimension),  # Quantizer
            dimension,                      # Vector dimension
            100,                            # Number of clusters (nlist)
            8,                              # Number of sub-quantizers (M)
            8                               # Bits per sub-quantizer
        )
        self.metadata = []
    
    def add(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Add embeddings to index"""
        if not self.index.is_trained:
            self.index.train(embeddings)
        
        self.index.add(embeddings)
        self.metadata.extend(metadata)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict]:
        """Search for k nearest neighbors"""
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1), 
            k
        )
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            results.append({
                'metadata': self.metadata[idx],
                'distance': float(dist)
            })
        
        return results
```

**Performance Targets**:
- 100K documents: <10ms query time
- 1M documents: <50ms query time
- 10M documents: <200ms query time

**Acceptance Criteria**:
- [ ] FAISS integration
- [ ] IVF+PQ indexing
- [ ] Benchmark: 10x faster than Chroma for 100K+ docs
- [ ] Persistence (save/load index)

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: Large-scale deployment

---

### P2.3: Metadata Filtering
**Epic**: Pre-filter by metadata before similarity search

**Problem**: Searching 1M docs when only need last hour

**Solution**: Two-phase filter → search

**Technical Design**:

```python
class MetadataFilter:
    """Filter documents by metadata before vector search"""
    
    def __init__(self, vectorstore):
        self.vectorstore = vectorstore
        self.metadata_index = defaultdict(set)  # field_value -> doc_ids
    
    def build_index(self, documents: List[Dict]):
        """Build inverted index on metadata fields"""
        for idx, doc in enumerate(documents):
            for field, value in doc.metadata.items():
                self.metadata_index[f"{field}:{value}"].add(idx)
    
    def filter_search(self, 
                     query_embedding: np.ndarray,
                     filters: Dict,
                     k: int = 5) -> List[Dict]:
        """
        Filter by metadata, then search within filtered subset.
        
        Example:
        filters = {
            "source": "firewall-acl-agent",
            "timestamp_after": "2026-02-08"
        }
        """
        
        # Get candidate doc IDs
        candidate_ids = None
        for field, value in filters.items():
            key = f"{field}:{value}"
            ids = self.metadata_index.get(key, set())
            
            if candidate_ids is None:
                candidate_ids = ids
            else:
                candidate_ids &= ids  # Intersection
        
        if not candidate_ids:
            return []
        
        # Search only within candidates
        filtered_docs = [self.vectorstore.documents[i] 
                        for i in candidate_ids]
        
        return self._search_subset(query_embedding, filtered_docs, k)
```

**Acceptance Criteria**:
- [ ] Pre-filtering by source, timestamp, IP, etc.
- [ ] Combine multiple filters (AND logic)
- [ ] 10x speedup for filtered searches
- [ ] Inverted index for fast lookups

**Estimated Effort**: 2 days
**Depends On**: None
**Blocks**: Efficient filtered queries

---

## 📊 Priority 3: Query Intelligence

### P3.1: Query Intent Classification
**Epic**: Automatically detect query type and route to best handler

**Query Types**:
```
1. Forensic: "What happened to IP X?"
2. Statistical: "How many blocks today?"
3. Trend: "Is blocking rate increasing?"
4. Comparison: "Detections vs blocks"
5. Search: "Find similar events"
```

**Technical Design**:

```python
from transformers import pipeline

class IntentClassifier:
    """Classify query intent to route to best handler"""
    
    def __init__(self):
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        self.intents = [
            "forensic_investigation",
            "statistical_analysis", 
            "trend_detection",
            "comparison_analysis",
            "general_search"
        ]
    
    def classify(self, query: str) -> str:
        """Classify query intent"""
        result = self.classifier(query, self.intents)
        return result['labels'][0]
    
    def route(self, query: str) -> Any:
        """Route to appropriate handler"""
        intent = self.classify(query)
        
        if intent == "forensic_investigation":
            return ForensicQueryHandler().handle(query)
        elif intent == "statistical_analysis":
            return StatisticalQueryHandler().handle(query)
        elif intent == "trend_detection":
            return TrendQueryHandler().handle(query)
        elif intent == "comparison_analysis":
            return ComparisonQueryHandler().handle(query)
        else:
            return GeneralSearchHandler().handle(query)
```

**Acceptance Criteria**:
- [ ] Intent classification for 5+ query types
- [ ] Routing to specialized handlers
- [ ] >90% classification accuracy
- [ ] Fallback to general search if uncertain

**Estimated Effort**: 3 days
**Depends On**: None
**Blocks**: Intelligent query routing

---

### P3.2: Query Suggestions
**Epic**: Suggest follow-up questions

**Example**:
```
User: "How many IPs blocked today?"
RAG: "1,234 IPs blocked today"

Suggestions:
- "What are the top 10 most blocked IPs?"
- "Show me blocks from this hour"
- "Were any detections not blocked?"
```

**Technical Design**:

```python
class QuerySuggester:
    """Generate contextual follow-up questions"""
    
    def suggest(self, original_query: str, 
                result: str) -> List[str]:
        """Generate 3-5 relevant follow-up questions"""
        
        # Extract entities from query
        entities = self._extract_entities(original_query)
        
        # Generate templates based on query type
        if "count" in original_query.lower():
            return [
                f"What are the top 10 {entities['subject']}?",
                f"Show trend over time",
                f"Compare to yesterday"
            ]
        
        elif "ip" in original_query.lower():
            ip = entities.get('ip')
            return [
                f"When was {ip} first blocked?",
                f"How many times has {ip} been blocked?",
                f"What attack type was {ip} detected as?"
            ]
```

**Acceptance Criteria**:
- [ ] Generate 3-5 relevant suggestions per query
- [ ] Context-aware (based on query type)
- [ ] Clickable in UI
- [ ] Learn from user selections (reinforcement)

**Estimated Effort**: 2 days
**Depends On**: P3.1 (intent classification)
**Blocks**: Improved user experience

---

## 🎨 Priority 4: Advanced Features

### P4.1: Multi-Modal RAG
**Epic**: Include packet captures, charts, graphs

**Beyond Text**:
- PCAP files (packet captures)
- Charts (matplotlib/plotly)
- Network topology diagrams

**Estimated Effort**: 5 days

---

### P4.2: Federated Search
**Epic**: Query across multiple RAG instances

**Use Case**: Multi-datacenter deployment

**Estimated Effort**: 4 days

---

### P4.3: Continuous Learning
**Epic**: RAG learns from user feedback

**Mechanism**: Users upvote/downvote answers, rerank accordingly

**Estimated Effort**: 3 days

---

## 📈 Performance Targets

### Current
- Query latency: ~500ms
- Document count: ~10K
- Embedding model: sentence-transformers

### Target
- 🎯 Query latency: <100ms (p95)
- 🎯 Document count: 1M+
- 🎯 Concurrent queries: 100/sec
- 🎯 Recall@10: >95%

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] Relationship graph building
- [ ] Temporal parsing
- [ ] Aggregation functions
- [ ] Intent classification

### Integration Tests
- [ ] End-to-end query pipeline
- [ ] Cross-component queries
- [ ] Metadata filtering

### Performance Tests
- [ ] Query latency under load
- [ ] Scale to 1M documents
- [ ] Concurrent query handling

---

## 🚀 Release Roadmap

### v1.1 (1 week) - Cross-Component Queries
- P1.1: Relationship-aware queries
- P1.2: Temporal queries
- P1.3: Aggregation

**Goal**: Advanced forensic analysis

### v1.2 (1 week) - Performance
- P2.1: Embedding cache
- P2.2: FAISS indexing
- P2.3: Metadata filtering

**Goal**: Scale to 1M+ documents

### v1.3 (1 week) - Intelligence
- P3.1: Intent classification
- P3.2: Query suggestions

**Goal**: Smarter, more helpful responses

---

**Via Appia Quality**: The RAG knows the complete truth 🏛️