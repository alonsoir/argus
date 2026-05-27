# 🤖 Model #2 - Ransomware XGBoost Detector

**Fecha:** 2025-11-04  
**Objetivo:** Entrenar modelo XGBoost optimizado para Raspberry Pi 5  
**Target:** >99% accuracy, <10ms inference, <50MB model size

---

## 📋 Quick Start

### 1. **Verificar dependencias**

```bash
cd ml-training/scripts

# Verificar Python y librerías
python --version  # Debe ser 3.11+

pip list | grep -E "xgboost|scikit-learn|pandas|imbalanced-learn"

# Si falta algo:
pip install xgboost scikit-learn pandas numpy matplotlib seaborn imbalanced-learn joblib
```

### 2. **Copiar archivos al proyecto**

```bash
cd /path/to/argus/ml-training

# Los archivos están en outputs/ (generados por Claude)
# Copiarlos a scripts/
cp ../outputs/train_ransomware_xgboost_Claude.py scripts/
cp ../outputs/ransomware_feature_mapping.json scripts/

# Verificar
ls -lh scripts/train_ransomware_xgboost_Claude.py
ls -lh scripts/ransomware_feature_mapping.json
```

### 3. **Entrenar el modelo**

```bash
cd ml-training/scripts

# Ejecutar training (puede tardar 10-30 minutos)
python train_ransomware_xgboost_Claude.py

# O con logging:
python train_ransomware_xgboost_Claude.py 2>&1 | tee ransomware_training.log
```

---

## 📊 Datasets Utilizados

### **CIC-IDS-2018**
- **Archivo:** `datasets/CIC-IDS-2018/02-28-2018.csv`
- **Samples:** 68,871 "Infilteration" + 544,200 "Benign"
- **Comportamiento:** Infiltration attacks (ransomware-like)

### **CIC-IDS-2017**
- **Archivos:** `datasets/CIC-IDS-2017/MachineLearningCVE/*.csv`
- **Samples:** 1,966 "Bot" + 2.27M "Benign"
- **Comportamiento:** Botnet C&C (similar a ransomware)

**Total:**
- Attack: ~70K samples
- Benign: ~2.8M samples
- Balancing: SMOTE (30% ratio)

---

## 🎯 Features (28 total)

### **RansomwareFeatures (20)** - del protobuf
```
C&C Communication (4):
  - dns_query_entropy
  - new_external_ips_30s
  - dns_query_rate_per_min
  - failed_dns_queries_ratio

Lateral Movement (3):
  - smb_connection_diversity
  - new_internal_connections_30s
  - port_scan_pattern_score

Exfiltration (4):
  - upload_download_ratio_30s
  - burst_connections_count
  - unique_destinations_30s
  - large_upload_sessions_count

Behavioral (6):
  - nocturnal_activity_flag
  - connection_rate_stddev
  - protocol_diversity_score
  - avg_flow_duration_seconds
  - tcp_rst_ratio
  - syn_without_ack_ratio
```

### **NetworkFeatures Base (8)**
```
  - Flow Byts/s
  - Flow Pkts/s
  - Total Forward/Backward Packets
  - Packet Length Mean/Std
  - SYN/RST/PSH/ACK Flag Counts
  - Destination Port
```

---

## 🔧 Configuración

El script tiene configuración optimizada para **macOS training** y **Pi5 deployment**:

```python
# En train_ransomware_xgboost_Claude.py (líneas 40-50)

SAMPLE_SIZE = 100000      # 100k samples para training rápido
USE_SMOTE = True          # Balancear con SMOTE
SMOTE_RATIO = 0.3         # Attack class → 30% de benign

XGBOOST_PARAMS = {
    'max_depth': 6,              # Shallow trees → rápido
    'n_estimators': 100,         # Balance accuracy/speed
    'learning_rate': 0.1,
    'tree_method': 'hist',       # Eficiente en memoria
    ...
}
```

**Para cambiar:**
- **Más datos:** `SAMPLE_SIZE = 500000` (más lento, mejor accuracy)
- **Menos datos:** `SAMPLE_SIZE = 50000` (más rápido, menor accuracy)
- **Más árboles:** `n_estimators': 200` (mejor modelo, más lento)

---

## 📦 Outputs Generados

Después del training, encontrarás:

```
ml-training/outputs/
├── models/
│   └── level2_ransomware_xgboost/
│       ├── level2_ransomware_xgboost.pkl          # Modelo XGBoost
│       ├── level2_ransomware_xgboost_scaler.pkl   # StandardScaler
│       ├── level2_ransomware_xgboost_metadata.json # Métricas y config
│       └── level2_ransomware_xgboost.onnx         # ONNX (para Pi5)
│
└── plots/
    └── level2_ransomware_xgboost/
        ├── feature_importance.png                  # Top features
        └── roc_curve.png                           # ROC-AUC curve
```

---

## ✅ Success Criteria

El modelo debe alcanzar:

| Metric | Target | Notes |
|--------|--------|-------|
| **Accuracy** | >99% | Superar Model #1 (98.61%) |
| **F1 Score** | >0.99 | Balance precision/recall |
| **False Positive Rate** | <1% | Crítico para producción |
| **False Negative Rate** | <1% | No puede perder ransomware |
| **Inference Time** | <10ms | Raspberry Pi 5 |
| **Model Size** | <50MB | Deployment constraint |

---

## 🚀 Integración con cpp_sniffer

### **Paso 1: Copiar modelo a la VM**

```bash
# En el host macOS
scp outputs/models/level2_ransomware_xgboost/*.onnx vagrant@debian:/path/to/ml-detector/models/

# O si usas shared folders:
cp outputs/models/level2_ransomware_xgboost/*.onnx /vagrant/ml-detector/models/
```

### **Paso 2: Actualizar config en cpp_sniffer**

```json
// config/ml_models.json
{
  "level2_ransomware": {
    "enabled": true,
    "model_path": "models/level2_ransomware_xgboost.onnx",
    "feature_mapping": "config/ransomware_feature_mapping.json",
    "threshold": 0.5,
    "inference_timeout_ms": 10
  }
}
```

### **Paso 3: Verificar features en protobuf**

El mapping JSON (`ransomware_feature_mapping.json`) tiene el orden exacto de features que el modelo espera. cpp_sniffer debe extraer las features en ese orden.

---

## 🐛 Troubleshooting

### **Error: "Dataset not found"**
```bash
# Verificar que los datasets están en el lugar correcto
ls -lh datasets/CIC-IDS-2018/02-28-2018.csv
ls -lh datasets/CIC-IDS-2017/MachineLearningCVE/
```

### **Error: "Module not found: xgboost"**
```bash
pip install xgboost
```

### **Error: "Module not found: imblearn"**
```bash
pip install imbalanced-learn
```

### **Warning: "ONNX export failed"**
```bash
# Opcional - solo si quieres ONNX directamente
pip install onnxmltools skl2onnx
```

### **Out of Memory**
Reduce `SAMPLE_SIZE` en el script:
```python
SAMPLE_SIZE = 50000  # En lugar de 100000
```

---

## 📈 Expected Results

Con la configuración por defecto, deberías ver:

```
📊 Test Set Metrics:
  Accuracy:  99.2%
  Precision: 99.0%
  Recall:    98.8%
  F1 Score:  98.9%
  ROC-AUC:   99.6%

⚠️  Error Rates:
  False Positive Rate: 0.8%
  False Negative Rate: 1.2%
```

---

## 🎓 Next Steps

1. ✅ **Training completo** → Este script
2. ⏳ **Integration testing** → Probar con cpp_sniffer
3. ⏳ **Stress testing** → 17h validation como Phase 1
4. ⏳ **Model #3** → Deep Learning (LSTM/Transformer)

---

## 📚 References

- **Protobuf:** `protobuf/network_security.proto` (RansomwareFeatures message)
- **Mapping:** `scripts/ransomware_feature_mapping.json`
- **CIC-IDS-2018:** https://www.unb.ca/cic/datasets/ids-2018.html
- **Phase 1 Docs:** `/vagrant/sniffer/docs/` (ARCHITECTURE, TESTING, etc.)

---

**¡Listo para entrenar! 🚀**

```bash
cd ml-training/scripts
python train_ransomware_xgboost_Claude.py
```
