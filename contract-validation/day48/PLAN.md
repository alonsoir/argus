# Day 48 Phase 1 - Contract Validation Plan

## Objetivo
Validar que 142 features fluyen correctamente: sniffer → ml-detector → rag-ingester

## Metodología

### 1. Input Validation (ml-detector)
- Verificar que ml-detector recibe 142 features
- Logging de campos recibidos
- Detección de campos faltantes/nulos

### 2. Feature Count Tracking
- Instrumentar pipeline con contadores
- Log every 1000 events
- Track: received, processed, forwarded

### 3. End-to-End Test
- Replay CTU-13 dataset
- Monitor feature counts en cada etapa
- Verificar integridad

### 4. Contract Assertions
```cpp
// En ml-detector/src/ml_detector.cpp
void validate_input_contract(const SecurityEvent& event) {
    // Count non-zero features
    int feature_count = count_valid_features(event);
    
    if (feature_count < 142) {
        LOG_ERROR("Contract violation: expected 142 features, got {}", 
                  feature_count);
        log_missing_features(event);
    }
}
```

## Success Criteria
- [ ] ml-detector logs confirman 142 features
- [ ] rag-ingester logs confirman 142 features
- [ ] 0 pérdidas detectadas en replay CTU-13
- [ ] Contract assertions PASS

## Estimated Duration
- Setup: 30 min
- Implementation: 1-2 hours
- Testing: 30 min
- Analysis: 30 min

Total: ~3 horas

## Deliverables
- Instrumented code con logging
- Test results con feature counts
- Contract validation report
- Issue log (si se detectan pérdidas)
  EOD