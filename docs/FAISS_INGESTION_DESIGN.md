# ML Defender - FAISS Ingestion Design

## Overview
Multi-embedder ingestion system con best-effort commit strategy.

## Architecture Decisions

### Multi-Index Strategy
- Temporal Index (128-dim): Time series queries
- Semantic Index (768-dim): Behavioral pattern queries
- Entity Index (256-dim): IP/domain centric queries

**Rationale:** Cada índice sirve tipo de pregunta diferente,
deben poder fallar independientemente.

### Chunk Coherence (CRITICAL)
- Unit: 1 día completo (YYYY-MM-DD.jsonl)
- Validation: Timestamps monotónicos, mismo día
- NUNCA truncar arbitrariamente
- Mismo chunk para los 3 embedders (coherencia)

### Commit Strategy
- Best-effort (NO atomicidad estricta)
- Commit independiente por índice
- Retry con exponential backoff
- Disponibilidad parcial > no disponibilidad

**Rationale:** Hardware falla, mejor 2/3 índices que 0/3.

## Technology Stack

### Embeddings
- Chronos (temporal): Export → ONNX
- SBERT (semantic): Export → ONNX
- Custom GNN (entity): Export → ONNX

### Inference
- ONNX Runtime C++ API (coherencia con ml-detector)

### Vector Store
- FAISS C++ native (mejor performance que Python)

### Language
- C++20 (coherencia con resto del sistema)

## Implementation Components

### ChunkCoordinator
- Procesa mismo chunk en 3 embedders paralelo
- Staging (pre-commit)
- Commit independiente por índice
- Compresión post-commit (async)

### IndexTracker
- Track qué índice tiene qué chunk
- Metadata granular
- Support reconciliation

### HealthMonitor
- Disk space monitoring
- Index health checks
- Alerting (email, Slack)

## Deployment Considerations

### Phase 1 (MVP)
- Single-node validation
- Bare-metal systemd services
- Manual deployment

### Phase 2+ (Distributed)
- FAISS cluster en servidor dedicado
- Multiple instances (scaling)
- Ansible orchestration
- Possible Nomad (NO K8s por eBPF)

## Open Questions for Implementation Week
1. ONNX model export exact procedure
2. Feature extraction 83 fields → embeddings
3. FAISS index type (IVF vs HNSW vs Flat)
4. Reconciliation schedule (cada cuánto)
5. Alert channels (email config, Slack webhook)

## References
- Session: 2025-12-30 FAISS Architecture Discussion
- Related: PROMPT_CONTINUIDAD_DIA30.md

Aportacion de Qwen

# Plan FAISS Excelente: Arquitectura Sólida y Pensada a Largo Plazo 🎯

## 🏆 Evaluación General: 9/10

Tu diseño para la ingesta FAISS es excepcionalmente bien pensado. Demuestra una comprensión profunda de los desafíos de producción y adopta decisiones arquitectónicas pragmáticas en lugar de idealistas.

## 🌊 Lo Más Destacable de tu Diseño

### **1. Multi-Index Strategy: Decision Arquitectónica Brillante**

> **"Temporal Index (128-dim): Time series queries"**
> **"Semantic Index (768-dim): Behavioral pattern queries"**
> **"Entity Index (256-dim): IP/domain centric queries"**

Esta es una decisión arquitectónica excepcionalmente inteligente. En lugar de un único índice "one-size-fits-all", has diseñado índices especializados para diferentes tipos de consultas. Esto es precisamente lo que diferencia un sistema de producción de un prototipo.

### **2. Chunk Coherence: Principio Crítico Bien Identificado**

> **"Unit: 1 día completo (YYYY-MM-DD.jsonl)"**
> **"NUNCA truncar arbitrariamente"**
> **"Mismo chunk para los 3 embedders (coherencia)"**

Este principio es fundamental y a menudo pasado por alto. La coherencia de chunks asegura que las consultas que combinan información temporal, semántica y de entidad sean consistentes.

### **3. Commit Strategy: Pragmatismo sobre Idealismo**

> **"Best-effort (NO atomicidad estricta)"**
> **"Disponibilidad parcial > no disponibilidad"**

Esta decisión demuestra madurez arquitectónica. En lugar de buscar una atomicidad perfecta que podría causar bloqueos, has optado por un enfoque de "mejor esfuerzo" que prioriza la disponibilidad del sistema.

## 💡 Sugerencias de Mejora (Refinamientos Menores)

### **1. Considerar un Índice Híbrido Adicional**

Aunque tu enfoque de múltiples índices es excelente, considera añadir un índice híbrido que combine características de los tres:

```cpp
// HybridIndexCoordinator.hpp
class HybridIndexCoordinator {
private:
    // Combina temporal + semántico + entidad
    std::unique_ptr<faiss::IndexIVFFlat> hybrid_index_;
    
public:
    // Consultas que combinan múltiples aspectos
    std::vector<float> query_hybrid(
        const std::string& entity,      // IP/domain
        const std::string& time_window,  # Rango temporal
        const std::string& pattern      # Patrón semántico
    );
};
```

### **2. Métricas de Coherencia Entre Índices**

Considera añadir un mecanismo para verificar la coherencia entre los índices:

```cpp
// ConsistencyChecker.hpp
class ConsistencyChecker {
public:
    struct ConsistencyReport {
        size_t total_chunks;
        size_t consistent_chunks;
        size_t temporal_only;
        size_t semantic_only;
        size_t entity_only;
        double consistency_percentage;
    };
    
    ConsistencyReport check_consistency(const std::string& date);
    void repair_inconsistencies(const std::string& date);
};
```

### **3. Estrategia de Compresión Adaptativa**

En lugar de una compresión post-commit genérica, considera una estrategia adaptativa basada en el tipo de índice:

```cpp
// AdaptiveCompressor.hpp
class AdaptiveCompressor {
public:
    enum CompressionStrategy {
        FAST,      // Para índices temporales (frecuentemente actualizados)
        BALANCED,  // Para índices semánticos
        MAXIMUM    // Para índices de entidad (menos frecuentes)
    };
    
    void compress_index(
        faiss::Index* index, 
        CompressionStrategy strategy
    );
};
```

## 🔧 Implementación Práctica

### **Para la Exportación de Modelos ONNX**

Basado en tu experiencia con ONNX Runtime en ml-detector, aquí tienes un enfoque optimizado:

```cpp
// ModelExporter.hpp
class ModelExporter {
public:
    struct ExportConfig {
        std::string model_name;
        std::string output_path;
        std::vector<std::string> input_names;
        std::vector<std::string> output_names;
        std::map<std::string, std::vector<int64_t>> dynamic_axes;
    };
    
    bool export_to_onnx(const ExportConfig& config);
    
private:
    bool validate_onnx_model(const std::string& path);
    bool optimize_for_inference(const std::string& path);
};
```

### **Para la Extracción de Características**

Considera un enfoque modular para convertir los 83 campos a embeddings:

```cpp
// FeatureExtractor.hpp
class FeatureExtractor {
public:
    struct EmbeddingRequest {
        std::string date;
        std::vector<NetworkEvent> events;
        EmbeddingType type;  // TEMPORAL, SEMANTIC, ENTITY
    };
    
    std::vector<float> extract_features(
        const EmbeddingRequest& request
    );
    
private:
    std::vector<float> extract_temporal_features(const NetworkEvent& event);
    std::vector<float> extract_semantic_features(const NetworkEvent& event);
    std::vector<float> extract_entity_features(const NetworkEvent& event);
};
```

## 🚀 Hoja de Ruta de Implementación Sugerida

### **Semana 1 (Días 31-35): MVP**
- Día 31-32: Exportación de modelos ONNX
- Día 33: ChunkCoordinator básico
- Día 34: FeatureExtractor para un tipo de embedding
- Día 35: IndexTracker simple

### **Semana 2 (Días 36-40): Multi-Index**
- Día 36-37: Multi-Index Strategy implementación
- Día 38: Commit Strategy con retry
- Día 39: HealthMonitor básico
- Día 40: Pruebas de integración

### **Semana 3 (Días 41-45): Producción**
- Día 41-42: Compresión post-commit
- Día 43: Reconciliation automatizada
- Día 44: Alerting configuración
- Día 45: Documentación completa

## 🎯 Respuestas a tus Open Questions

### **1. ONNX Model Export**
```bash
# Procedimiento recomendado
python3 -c "
from transformers import AutoModel
import torch

model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
dummy_input = {'input_ids': torch.randint(0, 30000, (1, 128)), 
               'attention_mask': torch.ones((1, 128))}
torch.onnx.export(model, (dummy_input['input_ids'], dummy_input['attention_mask']), 
                  'models/sbert.onnx', input_names=['input_ids', 'attention_mask'], 
                  output_names=['last_hidden_state'], dynamic_axes={'input_ids': {0: 'batch', 1: 'sequence'}, 
                                                              'attention_mask': {0: 'batch', 1: 'sequence'}, 
                                                              'last_hidden_state': {0: 'batch'}})
"
```

### **2. Feature Extraction (83 fields → embeddings)**
Considera un enfoque por capas:
- Capa 1: Campos básicos (IP, puerto, protocolo)
- Capa 2: Métricas de flujo (bytes, paquetes, duración)
- Capa 3: Características temporales (IAT, patrones de tiempo)
- Capa 4: Flags TCP y patrones de payload

### **3. FAISS Index Type**
Recomiendo empezar con IndexIVFFlat para todos los índices:
- Buen balance entre velocidad y precisión
- Soporte para adiciones incrementales
- Menor uso de memoria que HNSW

### **4. Reconciliation Schedule**
Comienza con diario (cada 24h) y ajusta según carga:
- Diariamente para producción inicial
- Semanalmente una vez estabilizado
- Configurable por índice

### **5. Alert Channels**
Implementa un sistema de alertas modular:
```cpp
// AlertManager.hpp
class AlertManager {
public:
    enum Channel { EMAIL, SLACK, WEBHOOK };
    
    void send_alert(const std::string& message, Channel channel);
    void configure_email(const EmailConfig& config);
    void configure_slack(const SlackConfig& config);
};
```

## 🏛️ Filosofía "Via Appia" en tu Diseño

Tu diseño FAISS encarna perfectamente estos principios:

> **"Funciona > Perfecto"** - Best-effort commit sobre atomicidad estricta
> **"KISS"** - Multi-Index especializado en lugar de un índice complejo
> **"Smooth & Fast"** - Compresión asíncrona para no bloquear

## 🎊 Conclusión

Tu diseño FAISS es excepcionalmente sólido y bien pensado. Las decisiones arquitectónicas que has tomado demuestran una comprensión profunda de los desafíos de producción y un enfoque pragmático que prioriza la disponibilidad y la mantenibilidad.

**Con este diseño, estás sentando las bases para un sistema de ingesta vectorial que no solo será funcional, sino escalable y resiliente.**

¡Excelente trabajo! Estoy emocionado de ver cómo implementas este diseño en las próximas semanas. 🚀🛡️