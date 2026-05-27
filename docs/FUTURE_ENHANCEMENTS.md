# Future Enhancements - Post Integration (Days 35+)

## 🎯 TIMING: Después de Crypto Integration Complete

**NO TOCAR AHORA** - En medio de integraciones críticas:
- Día 27: ml-detector + sniffer crypto-transport
- Día 28: Model Authority básico
- Día 29-30: RAG-Master naive

**IMPLEMENTAR DESPUÉS** - Cuando pipeline estable (Día 35+)

---

## 1. Shadow Authority (ChatGPT-5 Enhancement)

### Concepto
```
Authoritative Model → DECIDE (bloquea/permite)
Shadow Models → OBSERVE (logean, no bloquean)
```

### Casos de Uso
- A/B testing natural en producción
- Detectar ataques legacy (técnicas 2020)
- Regression detection antes de deploy
- Mantener modelos antiguos sin riesgo

### Protobuf Changes (Día 35)
```protobuf
message ModelScore {
    string model_name = 1;
    float score = 2;
    bool shadow_mode = 3;  // ← AÑADIR
}

repeated string shadow_models = 91;  // ← AÑADIR
```

### Implementación ml-detector
```cpp
// Config: models con mode="shadow"
if (model.mode == "shadow") {
    detect_and_log(event);  // Solo observa
    return;  // NO envía a firewall
}
```

### Análisis
```python
# Comparar authoritative vs shadow
shadow_unique = df[df['shadow_models'].str.contains('ddos_v1')]
auth_only = df[df['authoritative_model'] == 'ddos_v2']

# ¿Qué detecta v1 que v2 no?
regression_candidates = shadow_unique[~shadow_unique.isin(auth_only)]
```

---

## 2. Decision Outcome (Ground Truth)

### Concepto
```
Campo: decision_outcome
Valores: blocked, allowed, false_positive, false_negative, unknown, shadow
```

### Pipeline
```
T+0:     Detección → "unknown"
T+1ms:   Firewall → "blocked" o "allowed"
T+1day:  Review → "false_positive" o "false_negative"
```

### Protobuf Changes (Día 40)
```protobuf
string decision_outcome = 90;  // ← AÑADIR
// "blocked", "allowed", "false_positive", "false_negative", "unknown", "shadow"
```

### Reentrenamiento
```python
# Ground truth validado
fps = df[df['decision_outcome'] == 'false_positive']  # → benign
fns = df[df['decision_outcome'] == 'false_negative']  # → malicious

# Reentrenar con errores corregidos
retrain_dataset = pd.concat([fps, fns])
```

---

## 3. Model Authority Enhancement (Día 28 - Básico)

### Protobuf Changes (SIN romper)
```protobuf
// Añadir a PacketEvent (campos 84-89)
string authoritative_model = 84;
float confidence = 85;
string decision_reason = 86;
float runner_up_score = 87;
string runner_up_source = 88;
repeated ModelScore model_scores = 89;
```

### Implementación ml-detector
```cpp
// Identificar mejor modelo
event.set_authoritative_model("ddos_v2");
event.set_confidence(0.89);
event.set_decision_reason("ml won: 0.89 > 0.42");

// Individual scores
for (auto& [model, score] : all_scores) {
    auto* ms = event.add_model_scores();
    ms->set_model_name(model);
    ms->set_score(score);
}
```

---

## 🎯 ROADMAP DE IMPLEMENTACIÓN
```
✅ Día 27-28: Crypto Integration (PRIORIDAD)
   - ml-detector crypto-transport
   - sniffer crypto-transport
   - Stress test

✅ Día 28: Model Authority Básico (5 campos, SIN shadow)
   - Protobuf: campos 84-89
   - ml-detector: enrichment
   - Regenerar proto una sola vez
   - Tests validación

⏳ Día 35: Shadow Authority (después de estabilizar)
   - Protobuf: campo 91 + ModelScore.shadow_mode
   - ml-detector: shadow mode execution
   - Config: model modes
   - Análisis comparativo

⏳ Día 40: Decision Outcome (después de Shadow)
   - Protobuf: campo 90
   - Feedback loop firewall → ml-detector
   - Manual review interface
   - Reentrenamiento pipeline
```

---

## 💡 POR QUÉ ESTE ORDEN

**Día 27-28: Crypto (CRÍTICO)**
- Bloquea todo desarrollo si no funciona
- Componentes deben comunicarse cifrados
- Base para producción

**Día 28: Authority Básico (FUNDACIONAL)**
- Habilita análisis científico
- No requiere cambios grandes
- Una regeneración proto controlada

**Día 35: Shadow (EXPERIMENTAL)**
- Requiere pipeline estable
- No crítico para paper
- Mejora incremental

**Día 40: Outcome (CIENCIA)**
- Requiere Shadow funcionando
- Ground truth para reentrenamiento
- Closed-loop learning

---

## 🔐 DISCIPLINA DE CAMBIOS PROTOBUF

**Regla de Oro:**
> "Cambiar protobuf = recompilar TODO. Hacerlo una sola vez por milestone."

**Milestones Protobuf:**
1. ✅ Día 28: Model Authority (campos 84-89) ← UNA REGENERACIÓN
2. ⏳ Día 35: Shadow Authority (campo 91) ← UNA REGENERACIÓN
3. ⏳ Día 40: Decision Outcome (campo 90) ← UNA REGENERACIÓN

**NUNCA:**
- Cambios protobuf mid-integration
- Múltiples regeneraciones en un día
- Sin testing completo después

---

## 📊 VALOR CIENTÍFICO (Papers)

**Paper 1: Dual-Score Architecture**
- Día 28: authoritative_model data ✅
- Día 35: shadow models comparison

**Paper 2: Distributed Observatory**
- Día 29-30: RAG-Master foundation
- Semana 5: Cross-site analysis

**Paper 3: Closed-Loop Learning**
- Día 40: decision_outcome
- Semana 6: Retraining pipeline
- Semana 7: LLM fine-tuning

---

## ✅ CONCLUSIÓN

**ChatGPT-5 tiene razón en CONCEPTO.**
**Alonso tiene razón en TIMING.**

Documentar ahora = value capture sin riesgo
Implementar después = disciplina de ingeniería

Via Appia Quality: Plan → Execute → Validate

No volverse loco. Despacio pero bien. 🏛️