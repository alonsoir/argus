# ML Training Pipeline

Entrenamiento de modelos Random Forest para detección de ataques de red usando datasets CIC-IDS-2017 y CIC-DDoS-2019.

## 🎯 Objetivo

Entrenar modelos ML optimizados para el **ml-detector C++** del proyecto upgraded-happiness, con arquitectura tricapa:

- **Level 1**: Detector general de ataques (23 features)
- **Level 2**: Detectores especializados DDoS/Ransomware (82 features)
- **Level 3**: Detección de anomalías en tráfico interno/web (4 features)

## 📦 Instalación
```bash
    # Crear entorno virtual
    python3 -m venv venv
    source venv/bin/activate  # En Linux/Mac
    # venv\Scripts\activate   # En Windows
    
    # Instalar dependencias
    pip install -r requirements.txt
    
    # Instalar en modo desarrollo (opcional)
    pip install -e .
```

📊 Datasets
CIC-IDS-2017

Descripción: Dataset de detección de intrusiones con tráfico benigno y 7 tipos de ataques
Tamaño: ~1.1 GB (CSV)
Flows: ~2.8 millones
Clases: BENIGN, DoS, DDoS, PortScan, Infiltration, Web Attack, Botnet

CIC-DDoS-2019

Descripción: Dataset especializado en ataques DDoS
Tamaño: ~33 GB (CSV)
Flows: ~50 millones
Clases: 12 tipos de ataques DDoS + BENIGN

Descarga

# Los datasets se descargan manualmente desde:
# CIC-IDS-2017: http://cicresearch.ca/CICDataset/CIC-IDS-2017/
# CIC-DDoS-2019: http://cicresearch.ca/CICDataset/CICDDoS2019/

# Estructura esperada:
datasets/
├── CIC-IDS-2017/MachineLearningCVE/
└── CIC-DDoS-2019/{01-12,03-11}/

🚀 Uso
1. Exploración de Datos
```bash
    # Ejecutar script de exploración
    python scripts/explore.py
    
    # O usar notebook interactivo
    jupyter notebook notebooks/01_data_exploration.ipynb
```

2. Entrenamiento de Modelos
```bash
    # Level 1: Detector general
    python scripts/train_level1.py
    
    # Level 2: Detector DDoS especializado
    python scripts/train_level2_ddos.py
```
3. Conversión a ONNX
```bash
    # Convertir todos los modelos a ONNX
    python scripts/convert_to_onnx.py
    
    # Validar modelos ONNX
    python scripts/validate_models.py
```
4. Notebooks Jupyter
```bash
    jupyter notebook
    # Navegar a notebooks/ y ejecutar en orden:
    # 01 → 02 → 03 → 04 → 05
```
📁 Estructura del Proyecto
ml-training/
├── requirements.txt      # Dependencias Python
├── README.md            # Esta documentación
├── notebooks/           # Jupyter notebooks
├── scripts/             # Scripts ejecutables
├── src/ml_training/     # Código fuente reutilizable
├── datasets/            # Datasets (no versionados)
├── outputs/             # Modelos y metadata (no versionados)
└── tests/               # Tests unitarios

📊 Outputs Generados
outputs/
├── models/              # Modelos .joblib (sklearn)
│   ├── level1_attack_detector.joblib
│   ├── level2_ddos_detector.joblib
│   └── level3_*.joblib
├── onnx/                # Modelos .onnx (para C++)
│   ├── level1_attack_detector.onnx
│   ├── level2_ddos_detector.onnx
│   └── level3_*.onnx
├── metadata/            # Metadatos JSON
│   ├── level1_metadata.json
│   └── feature_mapping.json
└── plots/               # Visualizaciones
├── confusion_matrix_*.png
└── feature_importance_*.png

🔗 Integración con ml-detector C++
Los modelos ONNX generados se copian a:
```bash
    # Desde ml-training/
  cp outputs/onnx/*.onnx ../ml-detector/models/production/
```

📈 Métricas Esperadas
Level 1 (General Attack Detector)

Accuracy: >95%
Precision: >93%
Recall: >92%
F1-Score: >92%
False Positive Rate: <5%

Level 2 (DDoS Specialist)

Accuracy: >97%
Precision: >95% (por clase)
Recall: >94% (por clase)

🛠️ Desarrollo
```bash
    # Formatear código
    black scripts/ src/
    
    # Linting
    flake8 scripts/ src/
    
    # Type checking
    mypy scripts/ src/
    
    # Tests
    pytest tests/
```

📚 Referencias

CIC-IDS-2017 Paper
CIC-DDoS-2019 Paper
ONNX Documentation
scikit-learn
http://cicresearch.ca/CICDataset/CICDDoS2019/Dataset/CSVs/
http://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/CIC-IDS-2017/
https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/
https://www.unb.ca/cic/datasets/ids-2017.html
https://www.unb.ca/cic/datasets/ddos-2019.html
https://github.com/showlab/Paper2Video

📝 Licencia
MIT License - Ver LICENSE en el directorio raíz del proyecto.
✉️ Contacto
Proyecto: upgraded-happiness
ML Detector C++20 + eBPF Sniffer
