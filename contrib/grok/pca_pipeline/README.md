# PCA Pipeline Tools - Day 36 (Plan A: Synthetic)

**Creado por:** Grok 4 (xAI)  
**Fecha:** 09-Enero-2026  
**Propósito:** Herramientas para validar el pipeline de entrenamiento PCA con datos sintéticos (Plan A) y posteriormente con datos reales (Plan A').

## Archivos

- `synthetic_data_generator.cpp`  
  Genera 20.000 muestras sintéticas de 83 features con distribuciones realistas basadas en rangos típicos de CTU-13 y tráfico real.

- `train_pca_pipeline.cpp`  
  Pipeline completo:
    - Carga features (sintéticos o desde .pb procesados)
    - Inferencia con los 3 modelos ONNX (chronos, sbert, attack)
    - Entrena 3 PCA reducers (512→128, 384→128, 256→128) con target ≥96% variance
    - Guarda modelos en `/shared/models/pca/`

## Requisitos

- C++20
- ONNX Runtime (>=1.16)
- protobuf
- Eigen3
- spdlog
- DimensionalityReducer library (del proyecto)

## Compilación

```bash
g++ -std=c++20 -O3 -Wall -Wextra -Werror -I/vagrant/include \
    synthetic_data_generator.cpp -o bin/synthetic_generator

g++ -std=c++20 -O3 -Wall -Wextra -Werror -I/vagrant/include \
    train_pca_pipeline.cpp -lonnxruntime -lprotobuf -o bin/train_pca

./bin/synthetic_generator --output /shared/data/synthetic_features.bin --samples 20000

./bin/train_pca --features /shared/data/synthetic_features.bin \
                --output-dir /shared/models/pca/ \
                --suffix _v1_synthetic \
                --target-variance 0.96