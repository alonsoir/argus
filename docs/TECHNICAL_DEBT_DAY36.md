# TECHNICAL DEBT - Day 36 Discovery
**Date:** 09-Enero-2026  
**Discovered During:** Day 36 PCA Training Pipeline Planning  
**Severity:** 🟡 MEDIUM - System functional but RAG/FAISS pipeline incomplete  
**Impact:** FAISS ingestion pipeline blocked until resolved

---

## Executive Summary

Durante la planificación de Day 36 (training pipeline PCA), descubrimos una **desconexión arquitectural** entre los sistemas de extracción de features y los embedders ONNX creados para FAISS. El sistema de detección en tiempo real funciona correctamente (20+ horas estables), pero los eventos guardados para RAG/FAISS no contienen las features necesarias para los embedders.

**Estado Actual:**
- ✅ Sistema de detección: FUNCIONAL
- ❌ Pipeline RAG/FAISS: INCOMPLETO
- 🔄 Solución: Plan A→B→A' (3-4 días)

---

## The Gap - Sistemas Desconectados

### Sistema 1: Feature Extraction Legacy (83 features) - NUNCA USADO

```
Componente: FeatureExtractor (sniffer/src/userspace/feature_extractor.cpp)
Propósito:  Extracción completa de 83 features para datasets CTU-13
Estado:     ✅ CÓDIGO EXISTE - ❌ NUNCA SE USA EN PRODUCCIÓN

Features extraídas (83):
├─ Original 23: duration, spkts, dpkts, sbytes, dbytes, sload, smean, dmean, 
│               flow_iat_mean, flow_iat_std, fwd_psh_flags, bwd_psh_flags, 
│               fwd_urg_flags, bwd_urg_flags, packet_len_mean, packet_len_std,
│               packet_len_var, fin/syn/rst/psh/ack/urg_flag_count
├─ Phase 1 (20): dload, rate, srate, drate, ratios, IAT max/min, 
│                 packet lengths, headers, ECE/CWR flags
├─ Phase 2 (15): forward/backward IAT stats, active/idle times, fwd_len_std
├─ Phase 3 (20): subflow stats, bulk transfer, window sizes, headers
└─ Phase 4 (5):  avg packet/segment sizes, bulk packets

Entrada:  FlowStatistics (con vectores completos de timestamps, lengths, etc.)
Salida:   std::array<double, 83>

Uso real: ❌ NUNCA llamado desde ring_consumer.cpp
```

**Razón de NO uso:** Diseñado para datasets offline. El pipeline en tiempo real usa otro sistema.

---

### Sistema 2: ML Defender Extractor (40 features) - EN USO PERO INCOMPLETO

```
Componente: MLDefenderExtractor (sniffer/src/userspace/ml_defender_features.cpp)
Propósito:  Features para 4 detectores C++20 embebidos (tiempo real)
Estado:     ✅ CÓDIGO EXISTE - ⚠️ NO SE GUARDA EN .pb

Features extraídas (40):
├─ DDoS (10):        syn_ack_ratio, packet_symmetry, source_ip_dispersion, etc.
├─ Ransomware (10):  io_intensity, entropy, resource_usage, network_activity, etc.
├─ Traffic (10):     packet_rate, connection_rate, tcp_udp_ratio, avg_packet_size, etc.
└─ Internal (10):    connection_rate, service_port_consistency, lateral_movement, etc.

Entrada:  FlowStatistics (mismo que FeatureExtractor)
Salida:   4 submensajes protobuf (DDoSFeatures, RansomwareEmbeddedFeatures, etc.)

Código en ring_consumer.cpp línea 693:
    ml_extractor_.populate_ml_defender_features(*flow_stats, proto_event);

Estado en .pb guardados:
    ❌ Submensajes VACÍOS (ddos_embedded, ransomware_embedded, etc.)
    ❌ Solo 11 campos básicos guardados
    ✅ Tag "requires_processing" presente (sabíamos que faltaba algo)
```

---

### Sistema 3: Embedders ONNX (83 features) - PLACEHOLDER

```
Componente: chronos_embedder.onnx, sbert_embedder.onnx, attack_embedder.onnx
Propósito:  Generar embeddings para FAISS vector search
Estado:     ✅ MODELOS EXISTEN - ❌ NUNCA RECIBEN DATOS REALES

Arquitectura:
├─ chronos_embedder.onnx:  83 features → 512-d embedding
├─ sbert_embedder.onnx:    83 features → 384-d embedding
└─ attack_embedder.onnx:   83 features → 256-d embedding

Creación: PyTorch MLP sintéticos (create_*_embedder.py)
Training: Datos sintéticos (torch.randn(1, 83))
Validación: Test C++ PASSED (Day 34)

Estado actual:
    ✅ ONNX models operacionales
    ✅ C++ inference funciona
    ❌ Esperan 83 features que NO existen en .pb guardados
    ❌ Gap: .pb tiene 11 campos, embedders esperan 83
```

---

## Root Cause Analysis

### ¿Por qué pasó esto?

**1. Evolución del proyecto en fases:**
```
Fase 1 (CTU-13):    FeatureExtractor (83) diseñado para datasets offline
Fase 2 (Tiempo Real): MLDefenderExtractor (40) para detección instantánea
Fase 3 (FAISS/RAG):   Embedders ONNX (83) como placeholders para validar pipeline
```

**2. Sistemas paralelos nunca se conectaron:**
- FeatureExtractor (83) ← legacy, nunca integrado
- MLDefenderExtractor (40) ← funciona en tiempo real, no se guarda
- Embedders ONNX (83) ← creados para futuro, esperan features inexistentes

**3. Tag "requires_processing" dejado como recordatorio:**
```cpp
// ring_consumer.cpp línea 678
proto_event.add_event_tags("requires_processing");
```
**Sabíamos** que faltaba procesamiento adicional, pero nunca se implementó.

---

## Current State - What Works vs What Doesn't

### ✅ Sistema de Detección (FUNCIONA PERFECTAMENTE)

```
Pipeline en tiempo real:
    eBPF Sniffer → 11 campos básicos → ZeroMQ → ml-detector
                                                    ↓
                                        FeatureExtractor (ml-detector)
                                                    ↓
                                        Extrae features de 11 campos:
                                        ├─ Level 1: 23 features → ONNX
                                        ├─ Level 2: 10 features → DDoS C++20
                                        ├─ Level 2: 10 features → Ransomware C++20
                                        ├─ Level 3: 10 features → Traffic C++20
                                        └─ Level 3: 10 features → Internal C++20
                                                    ↓
                                        Dual-Score Decision System
                                                    ↓
                                        Detection Output ✅

Estado: 20+ horas de operación continua sin fallos
Performance: Detectando ataques correctamente
Problema: NINGUNO - Este sistema está completo
```

---

### ❌ Pipeline RAG/FAISS (INCOMPLETO)

```
Pipeline FAISS (planeado):
    Eventos históricos → .pb guardados (11 campos) ❌
                              ↓
                      "requires_processing" tag
                              ↓
                      ??? PROCESADOR FALTANTE ???
                              ↓
                      83 features completas ❌
                              ↓
                      ONNX Embedders (512/384/256-d) ❌
                              ↓
                      PCA Reduction (128-d) ❌
                              ↓
                      FAISS Index ❌

Estado actual:
    .pb files: Solo 11 campos básicos de NetworkFeatures
    Esperado: 83 features o 40 features completas
    Gap: 72-79 features faltantes
    Bloqueado: Cannot train PCA without proper features
```

---

## Impact Assessment

### Sistema de Detección
**Impact:** ✅ NONE - System functional
- Detectores funcionan correctamente
- Performance dentro de expectativas
- Sin cambios necesarios

### Sistema RAG/FAISS
**Impact:** 🔴 BLOCKING - Pipeline incomplete
- Cannot train PCA reducers with real data
- Cannot populate FAISS indices
- Cannot perform semantic search on historical events
- Day 36-40 blocked until resolved

### Timeline Impact
```
Original Plan:
    Day 36: Train PCA with real data (4-6h) ❌ BLOCKED
    Day 37-38: Integration testing
    Day 39-40: FAISS ingester implementation

With workaround (Plan A→B→A'):
    Day 36: Train PCA with synthetic data (4-6h) ✅ UNBLOCKED
    Day 37-38: Implement feature processing (2-3 days)
    Day 36 BIS: Re-train PCA with real data (2h)
    Day 39-40: Continue as planned
```

**Net delay:** 1-2 days (if Plan B takes 2 days instead of 3)

---

## Solution Strategy - Plan A→B→A'

### Plan A: Synthetic Data Workaround (Day 36 - 4-6h)

**Objective:** Validate pipeline end-to-end with synthetic data

```python
# Generate synthetic 83-feature events
synthetic_features = np.random.randn(20000, 83).astype(np.float32)

# Pass through ONNX embedders
chronos_emb = chronos_model(synthetic_features)  # 20K × 512
sbert_emb = sbert_model(synthetic_features)      # 20K × 384
attack_emb = attack_model(synthetic_features)    # 20K × 256

# Train PCA reducers
pca_chronos.fit(chronos_emb)  # 512 → 128, target ≥96% variance
pca_sbert.fit(sbert_emb)      # 384 → 128, target ≥96% variance
pca_attack.fit(attack_emb)    # 256 → 128, target ≥96% variance

# Save models
save_models("/shared/models/pca/")
```

**Deliverables:**
- ✅ 3 PCA models trained and saved
- ✅ Training pipeline code validated
- ✅ End-to-end architecture proven
- ✅ Documentation and tests written
- ⚠️ Variance may be lower (synthetic data has no semantic structure)

**Advantages:**
- Unblocks Day 36-40 FAISS work
- Validates training code before real data
- Provides baseline for comparison
- Scientifically honest (we document it's synthetic)

**Via Appia Quality:** Foundation first, even if temporary

---

### Plan B: Implement Real Feature Processing (Day 37-38 - 2-3 days)

**Objective:** Get real 83 or 40 features into .pb files

#### Option B1: Activate MLDefenderExtractor (40 features) - RECOMMENDED

```
Status:  Code exists but output not saved to .pb
Effort:  ~1 day
Quality: ⭐⭐⭐⭐⭐ (uses proven extraction code)

Implementation:
1. Verify ml_extractor_.populate_ml_defender_features() is called
2. Debug why submessages are empty in .pb
3. Fix serialization issue
4. Validate .pb contains 4 submessages with 10 features each

Result: .pb files with 40 real features

Challenge: 40 ≠ 83
Solutions:
  a) Retrain embedders for 40 features (3h)
  b) Pad/derive 83 features from 40 (engineering effort)
  c) Use 40 for now, add 83 later (incremental)
```

#### Option B2: Implement Full 83-Feature Processor

```
Status:  FeatureExtractor exists but not connected
Effort:  ~2-3 days
Quality: ⭐⭐⭐⭐ (reuses existing extraction logic)

Implementation:
1. Create processor that reads .pb raw
2. Extract FlowStatistics from events
3. Call FeatureExtractor::extract_features(flow) → 83 features
4. Save to new format or update .pb

Result: .pb files or separate files with 83 features

Challenge: FlowStatistics reconstruction
- .pb raw has 11 basic fields
- FeatureExtractor needs vectors (timestamps, lengths, etc.)
- May need to aggregate multiple packets into flows
```

#### Option B3: Extend Ring Consumer to Save Full Features

```
Status:  Requires changes to production sniffer
Effort:  ~2 days
Quality: ⭐⭐⭐ (cleaner but riskier)
Risk:    May impact production stability

Implementation:
1. Modify ring_consumer.cpp to call FeatureExtractor
2. Populate NetworkFeatures with all 83 fields
3. Ensure serialization works
4. Test thoroughly before deployment

Result: Future .pb files have 83 features

Challenge: Backward compatibility, testing burden
```

**RECOMMENDATION:** Start with Option B1 (40 features) as lowest risk, fastest path.

---

### Plan A': Re-train with Real Data (Day 36 BIS - 2h)

**Objective:** Validate real data pipeline using same training code

```python
# EXACT SAME CODE as Plan A, only data source changes:

# Load real features from processed .pb
real_features = load_from_processed_pb(
    "/vagrant/logs/rag/processed/*.pb",
    num_samples=20000,
    balanced=True
)  # Now shape (20000, 40) or (20000, 83)

# Rest is IDENTICAL to Plan A
chronos_emb = chronos_model(real_features)
pca_chronos.fit(chronos_emb)
# ... etc ...
```

**Deliverables:**
- ✅ 3 PCA models trained with REAL data
- ✅ Variance comparison: synthetic vs real
- ✅ Same code reused (validation of Plan A)
- ✅ Ready for production FAISS ingestion

**Scientific Value:**
- Documents evolution: synthetic → real
- Shows variance improvement with real data
- Validates both pipeline stages independently

---

## Decision Matrix

| Option | Effort | Risk | Quality | Timeline | Recommendation |
|--------|--------|------|---------|----------|----------------|
| **Plan A (Synthetic)** | 4-6h | 🟢 Low | ⭐⭐⭐ | Day 36 | ✅ DO THIS FIRST |
| **Plan B1 (40 feat)** | 1 day | 🟢 Low | ⭐⭐⭐⭐⭐ | Day 37 | ✅ RECOMMENDED |
| **Plan B2 (83 proc)** | 2-3d | 🟡 Medium | ⭐⭐⭐⭐ | Day 37-38 | 🔄 IF B1 INSUFFICIENT |
| **Plan B3 (Sniffer)** | 2d | 🔴 High | ⭐⭐⭐ | Day 37-38 | ❌ AVOID (prod risk) |
| **Plan A' (Real)** | 2h | 🟢 Low | ⭐⭐⭐⭐⭐ | After B | ✅ VALIDATION |

---

## Timeline with Solution

```
┌─────────────────────────────────────────────────────────────┐
│ WEEK 5-6: FAISS INFRASTRUCTURE (Days 31-40)                 │
├─────────────────────────────────────────────────────────────┤
│ Day 31-34: Infrastructure + ONNX validation      ✅ DONE    │
│ Day 35:    DimensionalityReducer library         ✅ DONE    │
│ Day 36:    Plan A - Train PCA (synthetic)        🔥 NEXT    │
│ Day 37:    Plan B1 - Activate 40 features        📅 PLANNED │
│ Day 38:    Plan A' - Re-train PCA (real)         📅 PLANNED │
│ Day 39-40: Buffer / FAISS ingester start         📅 PLANNED │
└─────────────────────────────────────────────────────────────┘

Net Impact: 1 day delay (if B1 takes 1 day instead of planned buffer)
Result: Foundation validated twice (synthetic + real)
Quality: Via Appia - methodical, documented, reproducible
```

---

## Lessons Learned

### What Went Right ✅
1. **Detection system:** Fully functional, no technical debt here
2. **Early discovery:** Found issue during planning, not during execution
3. **Code exists:** Both extractors written, just not connected
4. **Workaround viable:** Synthetic data validates architecture

### What Went Wrong ❌
1. **Parallel development:** Two feature systems never integrated
2. **Incomplete testing:** Embedders validated with synthetic, never checked real data path
3. **Tag ignored:** "requires_processing" left as TODO without follow-up

### How to Prevent 🛡️
1. **End-to-end validation:** Always test full pipeline with real data
2. **TODO tracking:** Every "requires_processing" needs a ticket
3. **Integration tests:** Don't just unit test components in isolation
4. **Documentation:** Architecture diagrams showing data flow

---

## Action Items

### Immediate (Day 36)
- [ ] Execute Plan A (synthetic PCA training)
- [ ] Document training pipeline code
- [ ] Validate architecture end-to-end
- [ ] Create Plan B implementation tickets

### Short-term (Day 37-38)
- [ ] Execute Plan B1 (activate 40 features)
- [ ] Debug why MLDefenderExtractor output not saved
- [ ] Validate .pb files contain submessages
- [ ] Execute Plan A' (re-train with real data)

### Medium-term (Week 6-7)
- [ ] Consider Plan B2 if 40 features insufficient
- [ ] Document feature extraction architecture
- [ ] Create integration tests for feature pipeline
- [ ] Remove "requires_processing" tag once complete

### Long-term (Phase 3+)
- [ ] Unify feature extraction (single source of truth)
- [ ] Evaluate if 83 features needed or 40 sufficient
- [ ] Consider feature engineering for better embeddings
- [ ] Performance optimization of feature extraction

---

## Communication

### Stakeholder Impact
**Alonso (Project Lead):**
- System functional, no production impact
- 1 day timeline slip (acceptable for quality)
- Foundation-first approach validated
- Scientific honesty maintained (document synthetic→real)

**Future Developers:**
- Clear documentation of why two systems exist
- Path forward documented
- Workarounds explained with rationale

---

## References

### Code Locations
```
Feature Extraction Legacy (83):
├─ /vagrant/sniffer/include/feature_extractor.hpp
└─ /vagrant/sniffer/src/userspace/feature_extractor.cpp

ML Defender Extractor (40):
├─ /vagrant/sniffer/include/ml_defender_features.hpp
└─ /vagrant/sniffer/src/userspace/ml_defender_features.cpp

Ring Consumer Integration:
└─ /vagrant/sniffer/src/userspace/ring_consumer.cpp (line 693)

ONNX Embedders:
├─ /vagrant/rag/models/chronos_embedder.onnx
├─ /vagrant/rag/models/sbert_embedder.onnx
└─ /vagrant/rag/models/attack_embedder.onnx

Protobuf Schema:
└─ /vagrant/protobuf/network_security.proto
```

### Related Documents
- `BACKLOG.md` - Updated with Plan A→B→A'
- `PROMPT_CONTINUE_CLAUDE.md` - Day 36 context
- `journal.txt` - Day 36 discovery log

---

## Conclusion

This is **NOT a critical bug** - it's an **incomplete feature** discovered during planning. The detection system works perfectly. The FAISS/RAG pipeline needs connection work.

**Via Appia Philosophy Applied:**
> "Better to build foundation twice (synthetic + real) than to rush and build poorly once."

**Plan A→B→A'** allows us to:
1. Validate architecture NOW (unblock progress)
2. Fix data pipeline PROPERLY (no hacks)
3. Re-validate with real data (scientific rigor)
4. Document journey (transparency)

**Timeline Impact:** Minimal (1 day)  
**Quality Impact:** Positive (double validation)  
**Risk Mitigation:** Excellent (incremental approach)

🏛️ **Via Appia Quality: Foundation First** 🏛️

---

**Document Version:** 1.0  
**Author:** Claude (Anthropic) + Alonso  
**Date:** 09-Enero-2026  
**Status:** 📋 DOCUMENTED - Ready for Day 36 execution  
**Next Review:** After Plan B completion