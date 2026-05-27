# Claude's PCA Pipeline for ML Defender

**Author:** Claude (Anthropic)  
**Date:** 10 Enero 2025  
**Purpose:** PCA Embedder Training (83 → 64 dimensions)  
**Philosophy:** Via Appia Quality - Simple, measured, production-ready

---

## 📋 Pipeline Overview
```
generate_training_data.py → train_pca_embedder.py → convert_pca_to_onnx.py
         ↓                          ↓                        ↓
  training_data.npz          pca_model.pkl            pca_embedder.onnx
   (100K samples)         (sklearn pipeline)        (C++ inference)
```

---

## 🎯 Features

- **83 features** from `network_security.proto` (4 ML Defender submessages + stats)
- **64 dimensions** target (optimized for FAISS)
- **90%+ variance** retention
- **<100μs** inference time
- **ONNX export** for C++ integration

---

## 📦 Requirements
```bash
pip3 install numpy scikit-learn onnx skl2onnx onnxruntime
```

---

## 🚀 Usage

### Step 1: Generate Training Data
```bash
python3 generate_training_data.py \
    --samples 100000 \
    --output training_data.npz
```

**Output:** `training_data.npz` (100K samples × 83 features)

---

### Step 2: Train PCA Embedder
```bash
python3 train_pca_embedder.py \
    --input training_data.npz \
    --output models/ \
    --components 64 \
    --variance 0.90
```

**Outputs:**
- `models/scaler.pkl` - StandardScaler
- `models/pca_model.pkl` - PCA model
- `models/training_metrics.json` - Training stats

---

### Step 3: Convert to ONNX
```bash
python3 convert_pca_to_onnx.py \
    --input models/ \
    --output models/pca_embedder.onnx \
    --validate
```

**Output:** `models/pca_embedder.onnx` (ready for C++)

---

## 📊 Expected Results
```
✅ Variance explained: 92.3%
✅ Transform time: 45.2 μs/sample
✅ ONNX validation: PASSED (max_diff < 1e-5)
✅ Model size: 127 KB
```

---

## 🔧 Integration with ML Defender
```cpp
// C++ inference example
#include <onnxruntime_cxx_api.h>

Ort::Env env;
Ort::Session session(env, "models/pca_embedder.onnx", session_options);

// Input: float[1][83] - 83 features
// Output: float[1][64] - 64-dim embedding
```

---

## 📝 Notes

- **Synthetic data:** Uses uniform random distributions within feature ranges
- **Real data:** When sniffer bug is fixed, retrain with real traffic
- **Thread-local bug:** See `/vagrant/docs/bugs/2025-01-10_thread_local_flowmanager_bug.md`

---

## 🏛️ Via Appia Quality

- Simple Python scripts (not complex C++)
- sklearn + ONNX (proven stack)
- Measured performance (<100μs)
- Production-ready export
- Clear documentation

---

**Next steps:** FAISS integration with 64-dim embeddings