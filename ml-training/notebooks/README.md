ml-training/
├── notebooks/
│   ├── 01_data_download.ipynb          # Descargar datasets
│   ├── 02_data_exploration.ipynb       # EDA
│   ├── 03_feature_engineering.ipynb    # Mapear a features sniffer
│   ├── 04_model_level1_training.ipynb  # Train Level 1 (23 features)
│   ├── 05_model_level2_ddos.ipynb      # Train Level 2 DDOS (82)
│   ├── 06_model_level3_retrain.ipynb   # Re-train tráfico interno/web
│   ├── 07_onnx_conversion.ipynb        # Convertir todos a ONNX
│   └── 08_validation.ipynb             # Validar ONNX vs sklearn
├── datasets/
│   ├── CIC-IDS-2017/
│   └── CIC-DDoS-2019/
└── outputs/
├── models/                          # .joblib
├── onnx/                            # .onnx
└── metadata/                        # .json