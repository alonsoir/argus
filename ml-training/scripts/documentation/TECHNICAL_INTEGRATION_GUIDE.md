# ml-training-scripts/documentation/TECHNICAL_INTEGRATION_GUIDE.md

# Guía de Integración Técnica - ML Detection Pipeline

## 📋 Resumen de Modelos

### 4 Modelos Implementados con Accuracy 1.0000

| Modelo | Muestras | Features | Clases | Complejidad |
|--------|----------|----------|---------|-------------|
| Ransomware | 10,000 | 10 | benign, ransomware | Alta |
| External Traffic | 100,000 | 10 | internet, internal | Media |
| DDoS | 50,000 | 10 | normal, ddos | Baja |
| Internal Traffic | 50,000 | 10 | benign, suspicious | Media-Alta |

## 🏗️ Arquitectura Kernel/User Space

### 🔹 RANSOMWARE DETECTION

**Objetivo**: Detección de comportamiento ransomware en endpoints

**KERNEL SPACE Features** (Captura directa eBPF):
- `io_intensity` - Intensidad de operaciones I/O
- `file_operations` - Operaciones de archivo (crear, eliminar, renombrar)
- `network_activity` - Actividad de red del proceso
- `data_volume` - Volumen de datos leídos/escritos
- `access_frequency` - Frecuencia de acceso a recursos

**USER SPACE Features** (Cálculos complejos):
- `entropy` - Entropía comportamental del proceso
- `behavior_consistency` - Consistencia del comportamiento temporal
- `temporal_pattern` - Patrones temporales de actividad
- `process_anomaly` - Anomalías estadísticas del proceso
- `resource_usage` - Uso agregado de recursos del sistema

**Notas Integración**: Requiere hooks de syscall para file operations y network

### 🔹 EXTERNAL TRAFFIC CLASSIFICATION

**Objetivo**: Clasificación tráfico Internet vs Interno

**KERNEL SPACE Features**:
- `packet_rate` - Tasa de paquetes por segundo
- `connection_rate` - Tasa de nuevas conexiones por segundo
- `tcp_udp_ratio` - Ratio entre tráfico TCP y UDP
- `avg_packet_size` - Tamaño promedio de paquetes
- `port_entropy` - Entropía de distribución de puertos

**USER SPACE Features**:
- `flow_duration_std` - Desviación estándar de duración de flujos
- `src_ip_entropy` - Entropía de direcciones IP origen
- `dst_ip_concentration` - Concentración de IPs destino
- `protocol_variety` - Variedad de protocolos de red
- `temporal_consistency` - Consistencia temporal de patrones

**Notas Integración**: Requiere captura a nivel de socket y análisis de headers IP

### 🔹 DDOS DETECTION

**Objetivo**: Detección ataques DDoS en tiempo real

**KERNEL SPACE Features**:
- `syn_ack_ratio` - Ratio entre paquetes SYN y ACK
- `packet_symmetry` - Simetría entre tráfico entrante/saliente
- `source_ip_dispersion` - Dispersión de IPs origen
- `protocol_anomaly_score` - Puntuación de anomalía de protocolos
- `packet_size_entropy` - Entropía de tamaños de paquete

**USER SPACE Features**:
- `traffic_amplification_factor` - Factor de amplificación de tráfico
- `flow_completion_rate` - Tasa de completitud de flujos
- `geographical_concentration` - Concentración geográfica de tráfico
- `traffic_escalation_rate` - Tasa de escalada de tráfico
- `resource_saturation_score` - Puntuación de saturación de recursos

**Notas Integración**: Crítico para detección temprana, requiere análisis en tiempo real

### 🔹 INTERNAL TRAFFIC DETECTION

**Objetivo**: Detección amenazas internas y movimiento lateral

**KERNEL SPACE Features**:
- `internal_connection_rate` - Tasa de conexiones internas
- `service_port_consistency` - Consistencia de puertos de servicio
- `protocol_regularity` - Regularidad de protocolos internos
- `packet_size_consistency` - Consistencia de tamaños de paquete
- `connection_duration_std` - Desviación de duración de conexiones

**USER SPACE Features**:
- `lateral_movement_score` - Puntuación de movimiento lateral
- `service_discovery_patterns` - Patrones de descubrimiento de servicios
- `data_exfiltration_indicators` - Indicadores de exfiltración de datos
- `temporal_anomaly_score` - Puntuación de anomalía temporal
- `access_pattern_entropy` - Entropía de patrones de acceso

**Notas Integración**: Esencial para seguridad Zero-Trust, detecta amenazas que evadieron el perímetro

¡Perfecto! Veo que tenemos **3 archivos de documentación** que necesitan actualizarse para reflejar las nuevas funciones `predict()`. Aquí están las actualizaciones necesarias:

## 📝 **ACTUALIZACIONES REQUERIDAS:**

### **1. `TECHNICAL_INTEGRATION_GUIDE.md` - AÑADIR SECCIÓN "USO CON FUNCIONES PREDICT"**

```markdown
## 🚀 Uso con Funciones Predict() - NUEVO

### 🔧 INTEGRACIÓN DIRECTA EN C++

Todos los modelos ahora incluyen funciones `predict()` automáticas para inferencia inmediata:

#### DDoS Detection
```cpp
#include "ddos_trees_inline.hpp"

float features[10] = {0.85f, 0.12f, 0.45f, 0.23f, 0.67f, 0.34f, 0.89f, 0.56f, 0.78f, 0.91f};
float ddos_prob = ml_defender::ddos::predict_ddos(features);
if (ddos_prob > 0.7f) {
    // Trigger DDoS mitigation
}
```

#### External Traffic Classification
```cpp
#include "traffic_trees_inline.hpp"

float features[TRAFFIC_NUM_FEATURES] = {...};
float internal_prob = ml_defender::traffic::predict_traffic(features);
if (internal_prob > 0.5f) {
    // Internal traffic detected
}
```

#### Internal Traffic Threat Detection
```cpp
#include "internal_trees_inline.hpp"

float features[INTERNAL_NUM_FEATURES] = {...};
float suspicious_prob = ml_defender::internal::predict_internal(features);
if (suspicious_prob > 0.6f) {
    // Suspicious internal activity detected
}
```

#### Ransomware Detection
```cpp
#include "ransomware_trees_inline.hpp"

float features[RANSOMWARE_NUM_FEATURES] = {...};
float ransomware_prob = ml_defender::ransomware::predict_ransomware(features);
if (ransomware_prob > 0.8f) {
    // Ransomware behavior detected
}
```

### 📊 THRESHOLDS RECOMENDADOS

| Modelo | Función Predict | Threshold | Acción |
|--------|-----------------|-----------|---------|
| DDoS | `predict_ddos()` | > 0.7 | Mitigación inmediata |
| External Traffic | `predict_traffic()` | > 0.5 | Clasificar como interno |
| Internal Traffic | `predict_internal()` | > 0.6 | Investigar amenaza |
| Ransomware | `predict_ransomware()` | > 0.8 | Aislar proceso |
```

### **2. `TechnicalDocumentation.py` - AÑADIR FUNCIONES PREDICT**

```python
# En la clase TechnicalDocumentation, añadir esta función:

def generate_predict_functions_documentation(self):
    """Genera documentación de las funciones predict() disponibles"""
    
    predict_functions = {
        'ransomware': {
            'function': 'predict_ransomware',
            'namespace': 'ml_defender::ransomware',
            'parameters': 'const float features[RANSOMWARE_NUM_FEATURES]',
            'return': 'float - Probability of ransomware behavior (0.0 to 1.0)',
            'threshold': '> 0.8 for detection'
        },
        'external_traffic': {
            'function': 'predict_traffic', 
            'namespace': 'ml_defender::traffic',
            'parameters': 'const float features[TRAFFIC_NUM_FEATURES]',
            'return': 'float - Probability of INTERNAL traffic (0.0 to 1.0)',
            'threshold': '> 0.5 for classification'
        },
        'ddos': {
            'function': 'predict_ddos',
            'namespace': 'ml_defender::ddos', 
            'parameters': 'const float features[DDOS_NUM_FEATURES]',
            'return': 'float - Probability of DDoS attack (0.0 to 1.0)',
            'threshold': '> 0.7 for mitigation'
        },
        'internal_traffic': {
            'function': 'predict_internal',
            'namespace': 'ml_defender::internal',
            'parameters': 'const float features[INTERNAL_NUM_FEATURES]',
            'return': 'float - Probability of SUSPICIOUS traffic (0.0 to 1.0)', 
            'threshold': '> 0.6 for investigation'
        }
    }
    
    print("\n🎯 FUNCIONES PREDICT() DISPONIBLES")
    print("=" * 50)
    
    for model, info in predict_functions.items():
        print(f"\n🔹 {model.upper()}:")
        print(f"   Function: {info['function']}")
        print(f"   Namespace: {info['namespace']}") 
        print(f"   Parameters: {info['parameters']}")
        print(f"   Returns: {info['return']}")
        print(f"   Threshold: {info['threshold']}")

# Y actualizar el main para incluir esta documentación:
if __name__ == "__main__":
    doc_gen = TechnicalDocumentation()
    doc_gen.generate_integration_guide()
    doc_gen.generate_predict_functions_documentation()  # NUEVA LÍNEA
```

### **3. `README.md` - ACTUALIZAR SECCIÓN "HEADERS C++20"**

```markdown
## 🔧 **HEADERS C++20 GENERADOS - CON FUNCIONES PREDICT()**

### 📁 **Archivos para ML-Detector:**
```
src/ml_defender/
├── ransomware_trees_inline.hpp    # 3,764 nodos + predict_ransomware()
├── traffic_trees_inline.hpp       # 1,014 nodos + predict_traffic()  
├── ddos_trees_inline.hpp          # 612 nodos + predict_ddos()
└── internal_trees_inline.hpp      # 940 nodos + predict_internal()
```

### 🚀 **USO INMEDIATO:**
```cpp
// Incluir headers
#include "ddos_trees_inline.hpp"
#include "traffic_trees_inline.hpp" 
#include "internal_trees_inline.hpp"
#include "ransomware_trees_inline.hpp"

// Inferencia directa con funciones predict()
float ddos_risk = ml_defender::ddos::predict_ddos(features);
float traffic_type = ml_defender::traffic::predict_traffic(features); 
float internal_threat = ml_defender::internal::predict_internal(features);
float ransomware_prob = ml_defender::ransomware::predict_ransomware(features);

// Tomar decisiones basadas en thresholds
if (ddos_risk > 0.7f) trigger_mitigation();
if (internal_threat > 0.6f) investigate_incident();
```

### ⚡ **Características Técnicas:**
- **Funciones predict() automáticas**: Inferencia en una línea
- **Inferencia inline**: Sin dependencias externas
- **Constexpr optimization**: Máximo rendimiento en compilación
- **Memory efficient**: Solo estructuras esenciales
- **Thread-safe**: Diseñado para entornos concurrentes
```

## 📊 Performance Models

| Modelo | Nodos Totales | Nodos/Árbol | Archivo C++ |
|--------|---------------|-------------|-------------|
| Ransomware | 3,764 | 37.6 | `ransomware_trees_inline.hpp` |
| External Traffic | 1,014 | 10.1 | `traffic_trees_inline.hpp` |
| DDoS | 612 | 6.1 | `ddos_trees_inline.hpp` |
| Internal Traffic | 940 | 9.4 | `internal_trees_inline.hpp` |

## 🚀 Próximos Pasos Integración

1. **Mover headers C++** a `src/ml_defender/`
2. **Extender sniffer eBPF** para capturar 40 features
3. **Integrar en ML-Detector** los 4 modelos
4. **Conectar con Firewall-ACL-Agent**

## ✅ Estado Actual

- **✅ Modelos entrenados** y validados (accuracy 1.0000)
- **✅ Headers C++20** generados
- **✅ Validación cruzada** completada
- **🔄 Pendiente**: Integración en pipeline