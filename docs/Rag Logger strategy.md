# 📊 RAGLogger - Estrategia de Logging

## 🤔 LA PREGUNTA FUNDAMENTAL

**"¿Guardamos todo o solo lo interesante?"**

Esta decisión afecta:
- 💾 Almacenamiento (GB/día)
- 🔍 Calidad del RAG (ruido vs señal)
- 📈 Capacidad de validación (F1-scores)
- ⚡ Performance del sistema

---

## 📋 ANÁLISIS COMPARATIVO

### Opción A: Solo Eventos Interesantes (ACTUAL ✅)

#### Criterios de Filtrado
```cpp
bool should_log_event() {
    // Se registra si cumple CUALQUIERA:
    return decision_metadata.requires_rag_analysis ||
           overall_threat_score >= 0.70 ||
           score_divergence >= 0.30;
}
```

#### Configuración
```json
{
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "save_protobuf_artifacts": true,
  "save_json_artifacts": true
}
```

#### Datos Reales Estimados

**SmallFlows (1,207 eventos):**
- RAG events: **87** (~7.2%)
- Motivo: Divergencia Fast=0.70 vs ML=0.39
- Logs: **~500 KB**
- Artifacts: **87 .pb + 87 .json** = **~3 MB**

**Neris (492,358 eventos):**
- RAG events: **~15,000** (~3%)
- Botnet IPs: **~800-1,200** eventos
- Logs: **~75 MB**
- Artifacts: **~300 MB**

**Producción (10M eventos/día):**
- RAG events: **~300,000** (~3%)
- Logs: **~1.5 GB/día**
- Artifacts: **~6 GB/día**
- **Total: 7.5 GB/día**
- **Retención 30 días: 225 GB**

#### ✅ Ventajas
1. **Almacenamiento manejable** - Solo 3% del total
2. **Alta calidad RAG** - Foco en eventos críticos
3. **Performance óptimo** - Overhead <2%
4. **Logs navegables** - Fácil de analizar manualmente
5. **Producción-ready** - Escalable a largo plazo

#### ❌ Desventajas
1. **No hay true negatives** - Dificulta F1-score perfecto
2. **Pierde contexto benigno** - No vemos "normalidad"
3. **Sesgo hacia amenazas** - RAG solo aprende de "malo"

#### 💡 Casos de Uso Ideales
- ✅ Investigación de amenazas
- ✅ Análisis de divergencias Fast vs ML
- ✅ Debugging de falsos positivos
- ✅ Entrenamiento de analistas
- ✅ Producción long-term

---

### Opción B: Muestreo Inteligente

#### Criterios de Filtrado
```cpp
bool should_log_event() {
    // 100% eventos interesantes
    if (overall_threat_score >= 0.70 || score_divergence >= 0.30) {
        return true;
    }
    
    // 1% eventos benignos (muestreo)
    if (overall_threat_score < 0.30 && random(0, 100) < 1) {
        return true;
    }
    
    return false;
}
```

#### Configuración
```json
{
  "mode": "production_with_sampling",
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "sample_benign_rate": 0.01,  // 1% benignos
  "sample_medium_rate": 0.10   // 10% medios (0.30-0.70)
}
```

#### Datos Reales Estimados

**Neris (492,358 eventos):**
- Interesantes: **~15,000** (3%)
- Benignos muestreados: **~4,800** (1% de ~480K)
- Medios muestreados: **~50** (casos edge)
- **Total: ~20,000** (~4%)
- Logs: **~100 MB**
- Artifacts: **~400 MB**

**Producción (10M eventos/día):**
- Interesantes: **~300,000**
- Benignos: **~97,000** (1% muestreo)
- **Total: ~400,000** (~4%)
- **Storage: ~10 GB/día**
- **Retención 30 días: 300 GB**

#### ✅ Ventajas
1. **True negatives disponibles** - F1-score completo
2. **Contexto benigno** - RAG aprende "normalidad"
3. **Balance amenaza/normal** - Dataset balanceado
4. **Validación robusta** - Métricas más confiables

#### ❌ Desventajas
1. **Más almacenamiento** - +33% vs Opción A
2. **Más complejo** - Lógica de muestreo añadida
3. **Random noise** - Algunos benignos poco útiles

#### 💡 Casos de Uso Ideales
- ✅ Validación F1-score
- ✅ Reentrenamiento de modelos
- ✅ Análisis de drift
- ✅ Research papers con métricas completas

---

### Opción C: Todo con Flag Testing

#### Criterios de Filtrado
```cpp
bool should_log_event() {
    if (mode == "testing") {
        // Log EVERYTHING
        return true;
    } else {
        // Production mode (Opción A)
        return overall_threat_score >= 0.70 || score_divergence >= 0.30;
    }
}
```

#### Configuración
```json
{
  "mode": "testing",  // "production" o "testing"
  "testing_max_events": 100000,  // Safety limit
  "production": {
    "min_score_to_log": 0.70,
    "min_divergence_to_log": 0.30
  }
}
```

#### Datos Reales Estimados

**Neris en modo TESTING (492,358 eventos):**
- **Total: 492,358** (100%)
- Logs: **~2.5 GB**
- Artifacts: **~10 GB**
- Tiempo adicional: **+10-15 minutos** (I/O disk)

**Producción en modo TESTING:**
- ❌ **NO RECOMENDADO**
- **Storage: ~50 GB/día**
- **Insostenible a largo plazo**

#### ✅ Ventajas
1. **Datos completos** - Nada se pierde
2. **F1-score perfecto** - Todas las métricas disponibles
3. **Flexibilidad** - Switch on/off fácil

#### ❌ Desventajas
1. **Almacenamiento masivo** - 20x más que Opción A
2. **I/O overhead** - +15% latencia
3. **Solo para testing** - No escalable

#### 💡 Casos de Uso Ideales
- ✅ Validation runs (Neris, CTU-13)
- ✅ Paper experiments con F1-scores
- ✅ Debugging exhaustivo
- ❌ **NUNCA en producción**

---

## 🎯 RECOMENDACIÓN FINAL

### Para Day 15 (Testing):

**Usar Opción A + Flag Testing:**

```json
{
  "mode": "testing",
  "testing_max_events": 500000,
  "production": {
    "min_score_to_log": 0.70,
    "min_divergence_to_log": 0.30,
    "save_protobuf_artifacts": false,
    "save_json_artifacts": false
  }
}
```

**Justificación:**
- Necesitamos **F1-scores reales** para el paper
- Neris tiene **ground truth** (IPs conocidas)
- Es un **test único**, no producción
- Podemos permitirnos **2.5 GB** por una vez

### Para Producción (Post-Day 16):

**Usar Opción A (Solo Interesantes):**

```json
{
  "mode": "production",
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "save_protobuf_artifacts": true,
  "save_json_artifacts": false
}
```

**Justificación:**
- **Escalable** - 7.5 GB/día sostenible
- **Alta calidad** - RAG se enfoca en amenazas
- **Performance** - <2% overhead
- **Sufficient** - Suficiente para investigación

---

## 🔧 IMPLEMENTACIÓN PRÁCTICA

### Day 15 Morning - SmallFlows (Quick Test)

**Config para SmallFlows:**
```json
{
  "mode": "production",
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "save_protobuf_artifacts": true,
  "save_json_artifacts": true
}
```

**Resultado esperado:** ~87 eventos, ~3 MB

### Day 15 Afternoon - Neris (F1-Score Validation)

**Config para Neris:**
```json
{
  "mode": "testing",
  "testing_max_events": 500000,
  "save_protobuf_artifacts": true,
  "save_json_artifacts": false
}
```

**Resultado esperado:** ~492K eventos, ~2.5 GB

**Post-procesamiento:**
```bash
# Después del test, filtrar solo interesantes para RAG
cat /vagrant/logs/rag/events/*.jsonl | \
  jq 'select(.detection.scores.final_score >= 0.70 or 
             .detection.scores.divergence >= 0.30)' \
  > /vagrant/logs/rag/events/neris_filtered.jsonl

# Resultado: ~15K eventos, ~75 MB
```

### Day 16+ - Producción

**Config para Producción:**
```json
{
  "mode": "production",
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "save_protobuf_artifacts": true,
  "save_json_artifacts": false,
  "max_events_per_file": 10000,
  "max_file_size_mb": 100
}
```

---

## 📊 COMPARATIVA VISUAL

```
Dataset: Neris (492K eventos)

┌─────────────────────────────────────────────────────────────┐
│ Opción A: Solo Interesantes                                 │
├─────────────────────────────────────────────────────────────┤
│ RAG Events:    ████ 15K (3%)                                │
│ Storage:       ██ 375 MB (logs + artifacts)                 │
│ F1-Score:      ⚠️  Parcial (solo positivos)                  │
│ Production:    ✅ Ready                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Opción B: Muestreo Inteligente                              │
├─────────────────────────────────────────────────────────────┤
│ RAG Events:    █████ 20K (4%)                               │
│ Storage:       ███ 500 MB (logs + artifacts)                │
│ F1-Score:      ✅ Completo (positivos + negativos)          │
│ Production:    ⚠️  Viable con trade-offs                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Opción C: Todo (Testing Mode)                               │
├─────────────────────────────────────────────────────────────┤
│ RAG Events:    ████████████████████ 492K (100%)             │
│ Storage:       ████████████ 12.5 GB (logs + artifacts)      │
│ F1-Score:      ✅ Completo                                   │
│ Production:    ❌ NO viable                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 DECISIÓN ESTRATÉGICA

### Mi Recomendación:

1. **Day 15 SmallFlows:** Opción A (baseline test)
2. **Day 15 Neris:** Opción C/Testing (F1-score completo)
3. **Day 16+:** Opción A (producción sostenible)

### Razones:

1. **Neris es único** - Solo lo hacemos una vez para el paper
2. **F1-scores necesarios** - Para validación científica
3. **Producción diferente** - No necesitamos 100% en real-time
4. **Storage temporal OK** - 2.5 GB por una vez es aceptable

### Roadmap:

```
Day 15:
  Morning:  SmallFlows (Opción A) → Validar sistema
  Afternoon: Neris (Opción C) → F1-scores completos
  
Day 16:
  Filtrar Neris → Solo interesantes para RAG ingestion
  Cambiar a Opción A para producción
  
Day 17+:
  Opción A permanente
  Re-evaluar thresholds basados en métricas reales
```

---

## 🎯 CONCLUSIÓN

**¿Qué guardamos en producción?**
**Respuesta: Solo lo interesante (Opción A)**

**¿Por qué?**
- ✅ Sostenible (7.5 GB/día vs 50 GB/día)
- ✅ Alta calidad RAG (foco en amenazas)
- ✅ Performance óptimo (<2% overhead)
- ✅ Suficiente para investigación

**¿Y los F1-scores?**
- Usamos modo "testing" solo para validation runs
- Guardamos datos completos una vez
- Documentamos métricas en paper
- Producción no necesita 100% de eventos

**Storage final recomendado:**
```
Production (30 días retención):
  - Logs RAG: 45 GB
  - Artifacts: 180 GB
  - Total: 225 GB
  
Backup validation runs:
  - Neris completo: 12.5 GB (keepforever)
  - CTU-13 otros: ~50 GB (opcional)
```

**💪 LISTO PARA IMPLEMENTAR** 🚀