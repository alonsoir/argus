# Hot-Reload ML Models - Design Document

> **Arquitectura completa para carga dinámica de modelos ML en runtime sin downtime**

---

## 🎯 Executive Summary

### Problema a Resolver

Actualmente, añadir o actualizar un modelo ML en el detector requiere:
1. ❌ Detener el proceso ml-detector
2. ❌ Recompilar o al menos reiniciar
3. ❌ Perder eventos durante el downtime
4. ❌ No poder hacer A/B testing en producción

### Solución Propuesta

Sistema de **Hot-Reload** que permite:
- ✅ Cargar nuevos modelos en runtime (zero downtime)
- ✅ Validación automática de compatibilidad de features
- ✅ Ensemble learning con múltiples modelos simultáneos
- ✅ A/B testing y gradual rollout
- ✅ Rollback instantáneo si un modelo falla
- ✅ Monitoreo de performance por modelo

### Valor del Sistema

```
Business Value:
- Continuous improvement sin interrupciones
- Experimentación rápida (A/B testing)
- Reducción de MTTR (Mean Time To Recovery)

Technical Value:
- Zero downtime deployments
- Concurrent model inference
- Graceful degradation
- Real-time performance metrics
```

---

## 🏗️ Arquitectura del Sistema

### Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST (macOS)                                 │
│                                                                       │
│  ml-training/                                                        │
│    ├─> scripts/train_level1_v2.py                                   │
│    ├─> scripts/convert_to_onnx.py                                   │
│    └─> outputs/onnx/                                                 │
│        ├─> level1_rf_v1.onnx  (baseline)                            │
│        ├─> level1_rf_v2.onnx  (NEW - better accuracy)               │
│        ├─> level1_rf_v3.onnx  (NEW - experimental)                  │
│        └─> metadata.json       (model info + features)              │
│                                                                       │
│  etcd (opcional):                                                    │
│    └─> PUT /models/level1/v2 {path, features, metrics}             │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
                    (shared folder /vagrant)
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         VAGRANT VM                                   │
│                                                                       │
│  ModelWatcher (inotify thread)                                       │
│    ├─> Watches: /vagrant/ml-training/outputs/onnx/                  │
│    ├─> Detects: IN_CLOSE_WRITE on *.onnx files                      │
│    ├─> Reads: metadata.json (validation)                            │
│    └─> Triggers: ModelRegistry.hot_load()                           │
│                                                                       │
│  ModelRegistry (thread-safe registry)                                │
│    ├─> models_ = {                                                   │
│    │     "level1_v1": {session, metrics, features: 23},             │
│    │     "level1_v2": {session, metrics, features: 23},  ← HOT      │
│    │   }                                                             │
│    ├─> active_models_ = ["level1_v1", "level1_v2"]                 │
│    ├─> shared_mutex for concurrent reads                            │
│    └─> Validation: feature dimensions, ONNX format                  │
│                                                                       │
│  InferenceEngine (ensemble predictor)                                │
│    ├─> Strategy: voting | weighted | stacking | all                 │
│    ├─> Per-event:                                                    │
│    │     for model in active_models:                                │
│    │       predictions[model] = model.infer(features)               │
│    └─> final = ensemble(predictions)                                │
│                                                                       │
│  MetricsCollector (monitoring)                                       │
│    └─> Per model: inferences, latency, accuracy, errors             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Componentes Principales

### 1. ModelWatcher - File System Observer

**Responsabilidad:** Detectar nuevos modelos y triggear hot-reload.

**Tecnología:** `inotify` (Linux kernel subsystem)

**Header (`include/model_watcher.hpp`):**

```cpp
#pragma once
#include <string>
#include <thread>
#include <functional>
#include <atomic>
#include <sys/inotify.h>

namespace mldetector {

class ModelWatcher {
public:
    using ModelCallback = std::function<void(const std::string& /* path */)>;
    
    ModelWatcher(const std::string& watch_dir, ModelCallback on_new_model);
    ~ModelWatcher();
    
    // Lifecycle
    void start();
    void stop();
    bool is_running() const { return running_.load(); }
    
    // Config
    void set_file_pattern(const std::string& pattern) { file_pattern_ = pattern; }
    void set_cooldown_ms(uint32_t ms) { cooldown_ms_ = ms; }
    
private:
    void watch_loop();
    bool matches_pattern(const std::string& filename) const;
    
    std::string watch_dir_;
    std::string file_pattern_ = "*.onnx";
    ModelCallback on_new_model_;
    
    int inotify_fd_;
    int watch_descriptor_;
    std::thread watcher_thread_;
    std::atomic<bool> running_{false};
    
    uint32_t cooldown_ms_ = 1000;  // Evitar múltiples triggers
    std::chrono::steady_clock::time_point last_trigger_;
};

} // namespace mldetector
```

**Implementation (`src/core/model_watcher.cpp`):**

```cpp
#include "model_watcher.hpp"
#include <sys/inotify.h>
#include <unistd.h>
#include <iostream>
#include <cstring>

namespace mldetector {

ModelWatcher::ModelWatcher(const std::string& watch_dir, ModelCallback callback)
    : watch_dir_(watch_dir)
    , on_new_model_(callback)
    , inotify_fd_(-1)
    , watch_descriptor_(-1) {
}

ModelWatcher::~ModelWatcher() {
    stop();
}

void ModelWatcher::start() {
    if (running_.load()) {
        std::cerr << "[ModelWatcher] Already running" << std::endl;
        return;
    }
    
    // Initialize inotify
    inotify_fd_ = inotify_init1(IN_NONBLOCK);
    if (inotify_fd_ < 0) {
        throw std::runtime_error("Failed to initialize inotify");
    }
    
    // Watch directory for file writes
    watch_descriptor_ = inotify_add_watch(
        inotify_fd_,
        watch_dir_.c_str(),
        IN_CLOSE_WRITE | IN_MOVED_TO  // File completely written
    );
    
    if (watch_descriptor_ < 0) {
        close(inotify_fd_);
        throw std::runtime_error("Failed to watch directory: " + watch_dir_);
    }
    
    running_.store(true);
    watcher_thread_ = std::thread(&ModelWatcher::watch_loop, this);
    
    std::cout << "[ModelWatcher] ✅ Started watching: " << watch_dir_ << std::endl;
}

void ModelWatcher::stop() {
    if (!running_.load()) return;
    
    running_.store(false);
    
    if (watcher_thread_.joinable()) {
        watcher_thread_.join();
    }
    
    if (watch_descriptor_ >= 0) {
        inotify_rm_watch(inotify_fd_, watch_descriptor_);
    }
    
    if (inotify_fd_ >= 0) {
        close(inotify_fd_);
    }
    
    std::cout << "[ModelWatcher] ✅ Stopped" << std::endl;
}

void ModelWatcher::watch_loop() {
    constexpr size_t EVENT_SIZE = sizeof(struct inotify_event);
    constexpr size_t BUF_LEN = 1024 * (EVENT_SIZE + 16);
    char buffer[BUF_LEN];
    
    while (running_.load()) {
        int length = read(inotify_fd_, buffer, BUF_LEN);
        
        if (length < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }
            std::cerr << "[ModelWatcher] Read error: " << strerror(errno) << std::endl;
            break;
        }
        
        int i = 0;
        while (i < length) {
            struct inotify_event* event = (struct inotify_event*)&buffer[i];
            
            if (event->len > 0) {
                std::string filename = event->name;
                
                // Check if matches pattern
                if (matches_pattern(filename)) {
                    // Apply cooldown to avoid duplicate triggers
                    auto now = std::chrono::steady_clock::now();
                    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                        now - last_trigger_
                    ).count();
                    
                    if (elapsed > cooldown_ms_) {
                        std::string full_path = watch_dir_ + "/" + filename;
                        std::cout << "[ModelWatcher] 🔔 New model detected: " 
                                  << filename << std::endl;
                        
                        on_new_model_(full_path);
                        last_trigger_ = now;
                    }
                }
            }
            
            i += EVENT_SIZE + event->len;
        }
    }
}

bool ModelWatcher::matches_pattern(const std::string& filename) const {
    // Simple pattern matching (can be enhanced with regex)
    if (file_pattern_ == "*.onnx") {
        return filename.size() > 5 && 
               filename.substr(filename.size() - 5) == ".onnx";
    }
    return true;
}

} // namespace mldetector
```

---

### 2. ModelRegistry - Thread-Safe Model Manager

**Responsabilidad:** Gestión centralizada de modelos con acceso concurrente.

**Header (`include/model_registry.hpp`):**

```cpp
#pragma once
#include <map>
#include <vector>
#include <string>
#include <memory>
#include <shared_mutex>
#include <onnxruntime_cxx_api.h>

namespace mldetector {

struct ModelInfo {
    std::string name;
    std::string path;
    size_t expected_features;
    bool enabled;
    
    // Metrics
    uint64_t total_inferences = 0;
    double avg_latency_us = 0.0;
    uint64_t errors = 0;
    std::chrono::system_clock::time_point loaded_at;
};

struct Prediction {
    int label;           // 0 = BENIGN, 1 = ATTACK
    float confidence;    // [0.0, 1.0]
    std::string model_name;
    double latency_us;
};

class ModelRegistry {
public:
    ModelRegistry(size_t expected_features);
    ~ModelRegistry();
    
    // Model Management (write operations)
    bool load_model(const std::string& name, const std::string& path);
    bool unload_model(const std::string& name);
    bool enable_model(const std::string& name);
    bool disable_model(const std::string& name);
    
    // Inference (read operations - concurrent)
    std::vector<Prediction> infer_all(const std::vector<float>& features);
    Prediction infer_single(const std::string& name, const std::vector<float>& features);
    
    // Query
    std::vector<std::string> get_active_models() const;
    ModelInfo get_model_info(const std::string& name) const;
    std::vector<ModelInfo> get_all_models_info() const;
    size_t count_active() const;
    
private:
    struct ModelEntry {
        std::unique_ptr<Ort::Session> session;
        ModelInfo info;
    };
    
    bool validate_model(const std::string& path);
    void update_metrics(const std::string& name, double latency_us, bool error);
    
    size_t expected_features_;
    std::map<std::string, ModelEntry> models_;
    std::vector<std::string> active_models_;
    
    mutable std::shared_mutex mutex_;  // Read-write lock
    Ort::Env env_{ORT_LOGGING_LEVEL_WARNING, "MLDetector"};
};

} // namespace mldetector
```

**Implementation (`src/inference/model_registry.cpp`):**

```cpp
#include "model_registry.hpp"
#include <iostream>
#include <algorithm>
#include <chrono>

namespace mldetector {

ModelRegistry::ModelRegistry(size_t expected_features)
    : expected_features_(expected_features) {
    std::cout << "[ModelRegistry] Initialized (expecting " 
              << expected_features << " features)" << std::endl;
}

ModelRegistry::~ModelRegistry() {
    std::unique_lock lock(mutex_);
    models_.clear();
    active_models_.clear();
}

bool ModelRegistry::validate_model(const std::string& path) {
    try {
        Ort::SessionOptions options;
        Ort::Session session(env_, path.c_str(), options);
        
        // Get input shape
        auto input_info = session.GetInputTypeInfo(0);
        auto tensor_info = input_info.GetTensorTypeAndShapeInfo();
        auto shape = tensor_info.GetShape();
        
        if (shape.size() < 2) {
            std::cerr << "[ModelRegistry] ❌ Invalid input shape" << std::endl;
            return false;
        }
        
        size_t feature_count = shape[1];  // [batch_size, features]
        
        if (feature_count != expected_features_) {
            std::cerr << "[ModelRegistry] ❌ Feature mismatch: "
                      << "expected " << expected_features_ 
                      << ", got " << feature_count << std::endl;
            return false;
        }
        
        std::cout << "[ModelRegistry] ✅ Model validation passed" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "[ModelRegistry] ❌ Validation error: " << e.what() << std::endl;
        return false;
    }
}

bool ModelRegistry::load_model(const std::string& name, const std::string& path) {
    // First validate without holding the lock
    if (!validate_model(path)) {
        return false;
    }
    
    std::unique_lock lock(mutex_);
    
    // Check if already exists
    if (models_.find(name) != models_.end()) {
        std::cerr << "[ModelRegistry] ⚠️  Model already exists: " << name << std::endl;
        return false;
    }
    
    try {
        ModelEntry entry;
        
        // Load ONNX session
        Ort::SessionOptions options;
        options.SetIntraOpNumThreads(1);
        options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        
        entry.session = std::make_unique<Ort::Session>(env_, path.c_str(), options);
        
        // Set info
        entry.info.name = name;
        entry.info.path = path;
        entry.info.expected_features = expected_features_;
        entry.info.enabled = true;
        entry.info.loaded_at = std::chrono::system_clock::now();
        
        // Add to registry
        models_[name] = std::move(entry);
        active_models_.push_back(name);
        
        std::cout << "[ModelRegistry] ✅ Hot-loaded model: " << name 
                  << " (total active: " << active_models_.size() << ")" << std::endl;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "[ModelRegistry] ❌ Failed to load model: " << e.what() << std::endl;
        return false;
    }
}

bool ModelRegistry::unload_model(const std::string& name) {
    std::unique_lock lock(mutex_);
    
    auto it = models_.find(name);
    if (it == models_.end()) {
        return false;
    }
    
    // Remove from active list
    active_models_.erase(
        std::remove(active_models_.begin(), active_models_.end(), name),
        active_models_.end()
    );
    
    // Remove from registry
    models_.erase(it);
    
    std::cout << "[ModelRegistry] ✅ Unloaded model: " << name << std::endl;
    return true;
}

std::vector<Prediction> ModelRegistry::infer_all(const std::vector<float>& features) {
    std::shared_lock lock(mutex_);  // Multiple readers allowed
    
    std::vector<Prediction> predictions;
    predictions.reserve(active_models_.size());
    
    for (const auto& name : active_models_) {
        auto it = models_.find(name);
        if (it == models_.end() || !it->second.info.enabled) {
            continue;
        }
        
        try {
            auto start = std::chrono::high_resolution_clock::now();
            
            // Prepare input tensor
            Ort::MemoryInfo memory_info = Ort::MemoryInfo::CreateCpu(
                OrtDeviceAllocator, OrtMemTypeCPU
            );
            
            std::vector<int64_t> input_shape = {1, static_cast<int64_t>(features.size())};
            Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
                memory_info,
                const_cast<float*>(features.data()),
                features.size(),
                input_shape.data(),
                input_shape.size()
            );
            
            // Run inference
            const char* input_names[] = {"float_input"};
            const char* output_names[] = {"label", "probabilities"};
            
            auto output_tensors = it->second.session->Run(
                Ort::RunOptions{nullptr},
                input_names, &input_tensor, 1,
                output_names, 2
            );
            
            // Extract prediction
            int64_t* label_data = output_tensors[0].GetTensorMutableData<int64_t>();
            float* probs_data = output_tensors[1].GetTensorMutableData<float>();
            
            auto end = std::chrono::high_resolution_clock::now();
            double latency_us = std::chrono::duration<double, std::micro>(end - start).count();
            
            Prediction pred;
            pred.label = static_cast<int>(label_data[0]);
            pred.confidence = probs_data[pred.label];
            pred.model_name = name;
            pred.latency_us = latency_us;
            
            predictions.push_back(pred);
            
            // Update metrics (need to acquire write lock briefly)
            lock.unlock();
            update_metrics(name, latency_us, false);
            lock.lock();
            
        } catch (const std::exception& e) {
            std::cerr << "[ModelRegistry] ❌ Inference error in " << name 
                      << ": " << e.what() << std::endl;
            
            lock.unlock();
            update_metrics(name, 0, true);
            lock.lock();
        }
    }
    
    return predictions;
}

void ModelRegistry::update_metrics(const std::string& name, double latency_us, bool error) {
    std::unique_lock lock(mutex_);
    
    auto it = models_.find(name);
    if (it == models_.end()) return;
    
    if (error) {
        it->second.info.errors++;
    } else {
        it->second.info.total_inferences++;
        
        // Running average of latency
        double alpha = 0.1;  // Exponential moving average factor
        it->second.info.avg_latency_us = 
            alpha * latency_us + (1.0 - alpha) * it->second.info.avg_latency_us;
    }
}

std::vector<std::string> ModelRegistry::get_active_models() const {
    std::shared_lock lock(mutex_);
    return active_models_;
}

std::vector<ModelInfo> ModelRegistry::get_all_models_info() const {
    std::shared_lock lock(mutex_);
    
    std::vector<ModelInfo> infos;
    infos.reserve(models_.size());
    
    for (const auto& [name, entry] : models_) {
        infos.push_back(entry.info);
    }
    
    return infos;
}

} // namespace mldetector
```

---

### 3. EnsemblePredictor - Multi-Model Inference

**Header (`include/ensemble_predictor.hpp`):**

```cpp
#pragma once
#include "model_registry.hpp"
#include <string>
#include <map>

namespace mldetector {

enum class EnsembleMode {
    SINGLE,       // Use only best model
    VOTING,       // Majority vote
    WEIGHTED,     // Weighted average
    ALL           // Return all predictions
};

struct EnsembleResult {
    int final_label;
    float confidence;
    std::vector<Prediction> individual_predictions;
    
    // Metadata
    size_t models_used;
    double total_latency_us;
    bool unanimous;  // All models agree
};

class EnsemblePredictor {
public:
    EnsemblePredictor(ModelRegistry& registry);
    
    void set_mode(EnsembleMode mode) { mode_ = mode; }
    void set_weights(const std::map<std::string, float>& weights) { weights_ = weights; }
    
    EnsembleResult predict(const std::vector<float>& features);
    
private:
    EnsembleResult voting(const std::vector<Prediction>& predictions);
    EnsembleResult weighted(const std::vector<Prediction>& predictions);
    EnsembleResult single_best(const std::vector<Prediction>& predictions);
    
    ModelRegistry& registry_;
    EnsembleMode mode_ = EnsembleMode::VOTING;
    std::map<std::string, float> weights_;
};

} // namespace mldetector
```

**Implementation:**

```cpp
#include "ensemble_predictor.hpp"
#include <algorithm>
#include <numeric>

namespace mldetector {

EnsemblePredictor::EnsemblePredictor(ModelRegistry& registry)
    : registry_(registry) {
}

EnsembleResult EnsemblePredictor::predict(const std::vector<float>& features) {
    // Get predictions from all active models
    auto predictions = registry_.infer_all(features);
    
    if (predictions.empty()) {
        throw std::runtime_error("No active models available");
    }
    
    switch (mode_) {
        case EnsembleMode::SINGLE:
            return single_best(predictions);
        case EnsembleMode::VOTING:
            return voting(predictions);
        case EnsembleMode::WEIGHTED:
            return weighted(predictions);
        case EnsembleMode::ALL:
            // Return all predictions with no aggregation
            EnsembleResult result;
            result.individual_predictions = predictions;
            result.final_label = predictions[0].label;
            result.confidence = predictions[0].confidence;
            result.models_used = predictions.size();
            return result;
    }
    
    return voting(predictions);  // Default
}

EnsembleResult EnsemblePredictor::voting(const std::vector<Prediction>& predictions) {
    EnsembleResult result;
    result.individual_predictions = predictions;
    result.models_used = predictions.size();
    
    // Count votes
    std::map<int, int> votes;
    std::map<int, std::vector<float>> confidences;
    
    for (const auto& pred : predictions) {
        votes[pred.label]++;
        confidences[pred.label].push_back(pred.confidence);
    }
    
    // Find majority
    auto max_vote = std::max_element(
        votes.begin(), votes.end(),
        [](const auto& a, const auto& b) { return a.second < b.second; }
    );
    
    result.final_label = max_vote->first;
    
    // Average confidence of winning label
    const auto& winning_confidences = confidences[result.final_label];
    result.confidence = std::accumulate(
        winning_confidences.begin(),
        winning_confidences.end(),
        0.0f
    ) / winning_confidences.size();
    
    // Check unanimity
    result.unanimous = (votes.size() == 1);
    
    // Total latency
    result.total_latency_us = std::accumulate(
        predictions.begin(), predictions.end(), 0.0,
        [](double sum, const Prediction& p) { return sum + p.latency_us; }
    );
    
    return result;
}

EnsembleResult EnsemblePredictor::weighted(const std::vector<Prediction>& predictions) {
    EnsembleResult result;
    result.individual_predictions = predictions;
    result.models_used = predictions.size();
    
    // If no weights specified, fall back to equal weights
    if (weights_.empty()) {
        return voting(predictions);
    }
    
    // Weighted scoring
    std::map<int, float> weighted_scores;
    
    for (const auto& pred : predictions) {
        float weight = 1.0f;
        if (weights_.count(pred.model_name)) {
            weight = weights_[pred.model_name];
        }
        
        weighted_scores[pred.label] += pred.confidence * weight;
    }
    
    // Find highest weighted score
    auto max_score = std::max_element(
        weighted_scores.begin(), weighted_scores.end(),
        [](const auto& a, const auto& b) { return a.second < b.second; }
    );
    
    result.final_label = max_score->first;
    result.confidence = max_score->second / predictions.size();  // Normalize
    result.unanimous = false;  // Weighted voting doesn't have unanimity concept
    
    result.total_latency_us = std::accumulate(
        predictions.begin(), predictions.end(), 0.0,
        [](double sum, const Prediction& p) { return sum + p.latency_us; }
    );
    
    return result;
}

EnsembleResult EnsemblePredictor::single_best(const std::vector<Prediction>& predictions) {
    // Use the prediction with highest confidence
    auto best = std::max_element(
        predictions.begin(), predictions.end(),
        [](const Prediction& a, const Prediction& b) {
            return a.confidence < b.confidence;
        }
    );
    
    EnsembleResult result;
    result.final_label = best->label;
    result.confidence = best->confidence;
    result.individual_predictions = predictions;
    result.models_used = 1;
    result.unanimous = false;
    result.total_latency_us = best->latency_us;
    
    return result;
}

} // namespace mldetector
```

---

## 🔧 Integración con ml-detector

### Modificación de `main.cpp`

```cpp
#include "model_watcher.hpp"
#include "model_registry.hpp"
#include "ensemble_predictor.hpp"

int main(int argc, char* argv[]) {
    // ... existing initialization ...
    
    // Create model registry
    constexpr size_t EXPECTED_FEATURES = 23;
    mldetector::ModelRegistry model_registry(EXPECTED_FEATURES);
    
    // Load initial model(s)
    if (!model_registry.load_model("level1_v1", "models/level1_rf_model.onnx")) {
        std::cerr << "Failed to load baseline model" << std::endl;
        return 1;
    }
    
    // Create ensemble predictor
    mldetector::EnsemblePredictor ensemble(model_registry);
    ensemble.set_mode(mldetector::EnsembleMode::VOTING);
    
    // Setup model watcher (hot-reload)
    mldetector::ModelWatcher watcher(
        "/vagrant/ml-training/outputs/onnx",
        [&model_registry](const std::string& path) {
            // Extract model name from path
            std::string name = extract_model_name(path);
            
            std::cout << "[HotReload] 🔥 Attempting to load: " << name << std::endl;
            
            if (model_registry.load_model(name, path)) {
                std::cout << "[HotReload] ✅ Successfully loaded: " << name << std::endl;
            } else {
                std::cout << "[HotReload] ❌ Failed to load: " << name << std::endl;
            }
        }
    );
    
    watcher.start();
    
    // Main inference loop
    while (running) {
        auto event = zmq_receive_event();
        auto features = extract_features(event);
        
        // Ensemble prediction with all active models
        auto result = ensemble.predict(features);
        
        std::cout << "[Inference] Label: " << result.final_label
                  << ", Confidence: " << result.confidence
                  << ", Models used: " << result.models_used
                  << ", Unanimous: " << (result.unanimous ? "YES" : "NO")
                  << std::endl;
        
        // Log individual predictions for debugging
        for (const auto& pred : result.individual_predictions) {
            std::cout << "  - " << pred.model_name 
                      << ": " << pred.label 
                      << " (" << pred.confidence << ")"
                      << " [" << pred.latency_us << " μs]"
                      << std::endl;
        }
    }
    
    watcher.stop();
    return 0;
}
```

---

## 📊 Monitoring & Metrics

### Metrics Endpoint (JSON Output)

```cpp
// include/metrics_reporter.hpp
class MetricsReporter {
public:
    MetricsReporter(ModelRegistry& registry);
    
    std::string get_metrics_json() const;
    void start_http_server(uint16_t port);  // Optional: HTTP endpoint
    
private:
    ModelRegistry& registry_;
};

// Example output:
{
  "timestamp": "2025-10-26T10:30:00Z",
  "models": [
    {
      "name": "level1_v1",
      "enabled": true,
      "total_inferences": 152340,
      "avg_latency_us": 45.3,
      "errors": 0,
      "loaded_at": "2025-10-25T16:23:00Z",
      "uptime_hours": 18.1
    },
    {
      "name": "level1_v2",
      "enabled": true,
      "total_inferences": 8730,
      "avg_latency_us": 42.8,
      "errors": 0,
      "loaded_at": "2025-10-26T10:15:00Z",
      "uptime_hours": 0.25
    }
  ],
  "ensemble": {
    "mode": "voting",
    "total_predictions": 8730,
    "unanimous_percentage": 94.2
  }
}
```

---

## 🧪 Testing Strategy

### Unit Tests

```cpp
// tests/test_model_registry.cpp
TEST(ModelRegistry, LoadValidModel) {
    ModelRegistry registry(23);
    ASSERT_TRUE(registry.load_model("test", "models/test_model.onnx"));
    ASSERT_EQ(registry.count_active(), 1);
}

TEST(ModelRegistry, RejectInvalidFeatures) {
    ModelRegistry registry(23);
    // Model with 50 features
    ASSERT_FALSE(registry.load_model("bad", "models/bad_features.onnx"));
}

TEST(ModelRegistry, ConcurrentInference) {
    ModelRegistry registry(23);
    registry.load_model("m1", "models/m1.onnx");
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 10; ++i) {
        threads.emplace_back([&]() {
            std::vector<float> features(23, 0.5f);
            auto preds = registry.infer_all(features);
            ASSERT_FALSE(preds.empty());
        });
    }
    
    for (auto& t : threads) t.join();
}
```

### Integration Test

```bash
#!/bin/bash
# tests/test_hotreload.sh

echo "=== Hot-Reload Integration Test ==="

# 1. Start ml-detector with baseline model
./build/ml-detector -c config/ml_detector_config.json &
DETECTOR_PID=$!

sleep 2

# 2. Send test event
echo "Sending test event..."
python scripts/send_test_event.py

# 3. Copy new model to watched directory
echo "Deploying new model..."
cp models/level1_rf_v2.onnx /vagrant/ml-training/outputs/onnx/

sleep 2

# 4. Verify new model was loaded
echo "Checking metrics..."
curl http://localhost:9090/metrics | jq '.models'

# 5. Send another test event (should use ensemble now)
python scripts/send_test_event.py

# Cleanup
kill $DETECTOR_PID
```

---

## 🗺️ Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Implement `ModelWatcher` with inotify
- [ ] Basic `ModelRegistry` (load/unload)
- [ ] Unit tests for core components
- [ ] Documentation updates

**Deliverable:** Model can be loaded dynamically

### Phase 2: Concurrency (Week 2)
- [ ] Thread-safe `ModelRegistry` with `shared_mutex`
- [ ] Concurrent inference stress tests
- [ ] Metrics collection per model
- [ ] Integration test suite

**Deliverable:** Multiple models can run concurrently

### Phase 3: Ensemble (Week 3)
- [ ] `EnsemblePredictor` implementation
- [ ] Voting strategy
- [ ] Weighted voting
- [ ] Configuration via JSON

**Deliverable:** Ensemble predictions working

### Phase 4: Production (Week 4)
- [ ] Graceful degradation (fallback to single model)
- [ ] HTTP metrics endpoint
- [ ] Performance benchmarks
- [ ] Documentation complete

**Deliverable:** Production-ready system

---

## 🔒 Safety & Reliability

### Error Handling

```cpp
// Graceful degradation
EnsembleResult EnsemblePredictor::predict(const std::vector<float>& features) {
    try {
        auto predictions = registry_.infer_all(features);
        
        if (predictions.empty()) {
            // No models available - critical error
            throw std::runtime_error("No active models");
        }
        
        return voting(predictions);
        
    } catch (const std::exception& e) {
        std::cerr << "[Ensemble] ❌ Prediction error: " << e.what() << std::endl;
        
        // Try to use at least one model
        auto active = registry_.get_active_models();
        if (!active.empty()) {
            return registry_.infer_single(active[0], features);
        }
        
        throw;  // Re-throw if no fallback possible
    }
}
```

### Resource Limits

```cpp
class ModelRegistry {
private:
    static constexpr size_t MAX_MODELS = 10;
    static constexpr size_t MAX_MEMORY_MB = 2048;
    
    bool check_resource_limits() const {
        if (models_.size() >= MAX_MODELS) {
            std::cerr << "Max model limit reached" << std::endl;
            return false;
        }
        
        // Check memory usage
        size_t total_memory = get_total_model_memory();
        if (total_memory > MAX_MEMORY_MB * 1024 * 1024) {
            std::cerr << "Memory limit exceeded" << std::endl;
            return false;
        }
        
        return true;
    }
};
```

---

## 📈 Performance Considerations

### Latency Analysis

```
Single Model:
- Feature extraction: ~10 μs
- ONNX inference: ~50 μs
- Total: ~60 μs per event

Ensemble (3 models, concurrent):
- Feature extraction: ~10 μs
- ONNX inference (parallel): ~50 μs (NOT 3x!)
- Voting: ~1 μs
- Total: ~61 μs per event
```

**Key Insight:** Concurrent inference with `shared_mutex` allows parallel reads, so latency doesn't scale linearly with model count.

### Memory Usage

```
Baseline (1 model):
- Model size: ~2 MB
- Runtime overhead: ~50 MB
- Total: ~52 MB

Hot-Reload (3 models):
- Models: 3 x 2 MB = 6 MB
- Runtime overhead: ~50 MB
- Total: ~56 MB
```

**Conclusion:** Memory cost is minimal.

---

## 🎓 Best Practices

1. **Always validate features** before loading a model
2. **Use semantic versioning** for model names (level1_v2.1.0)
3. **Log all hot-reload events** for audit trail
4. **Monitor individual model performance** to detect degradation
5. **Implement rollback mechanism** (keep previous version)
6. **Test under load** before production deployment
7. **Document feature engineering** to ensure compatibility

---

## 🚀 Future Enhancements

### Advanced Features (Future Versions)

- **A/B Testing Framework**: Gradual rollout (10% → 50% → 100%)
- **Canary Deployments**: Route specific traffic to new model
- **Model Versioning**: Git-style version control for models
- **Distributed Registry**: Share models across multiple ml-detector instances
- **Auto-scaling**: Load/unload models based on traffic
- **Stacking Meta-Learner**: Train a model that combines predictions

---

## 📚 References & Resources

- [inotify man page](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [ONNX Runtime C++ API](https://onnxruntime.ai/docs/api/c/)
- [C++ Concurrency: shared_mutex](https://en.cppreference.com/w/cpp/thread/shared_mutex)
- [Ensemble Learning Techniques](https://scikit-learn.org/stable/modules/ensemble.html)

---

## 🎯 Success Metrics

**How to know it's working:**

✅ New model appears in watched directory  
✅ ModelWatcher triggers within 1 second  
✅ Model loads successfully (validation passes)  
✅ Ensemble predictions use new model  
✅ Zero downtime during hot-reload  
✅ Latency remains stable (<100 μs)  
✅ No memory leaks (valgrind clean)

---

<div align="center">

## 🎉 This is the Future of Your ML Pipeline 🎉

**Zero Downtime • Continuous Improvement • Production Ready**

*Design Document v1.0 - October 25, 2025*

</div>