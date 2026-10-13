# Datasets borrados del disco — DAY296 (2026-10-13)

Criterio (Alonso): se conserva solo lo que usa el pipeline en su estado actual o lo necesario para regenerar lo que
tenemos. Lo demás se borra y se vuelve a descargar cuando una cabeza tenga estrategia escrita que lo justifique.
Origen de descarga: ver ml-training/datasets/README.md (se conserva).

| Dataset | Ruta | Tamaño | Citado en código | Motivo |
|---|---|---|---|---|
| RanSMAP | ml-training/datasets/RanSMAP | 160 GB | solo metadatos de modelos ransomware NO de confianza (ml-training/outputs/...) y site/ | sin uso en el pipeline actual |
| UNSW-NB15 | ml-training/datasets/UNSW-NB15 (+ .tar.gz) | 751 MB | solo metadatos/informes en ml-training/outputs y site/ | sin uso en el pipeline actual |
| TON_IoT | ml-training/datasets/ton-iot.tar.gz | 954 MB | solo metadatos/informes en ml-training/outputs | sin uso en el pipeline actual |

Se conservan: CICDDoS2019 (datasets/cicddos2019 PCAP y ml-training/datasets/CICDDoS2019 CSV: grieta B y batería del
lab), CIC-IDS-2017 (metadatos del level1 en ml-detector/models/production), ctu13 (Makefile, experimentos,
paper-artifacts), internal-normal, ugransome y los pequeños sin referencias.

Además (datos del lab, fuera de git): 32 días de logs/ml-detector/events/*.csv y sus Parquet con timestamp_utc_ns
monotónico (691461 de 774069 filas), más la cuarentena DAY294 (2026-10-01): 66 ficheros, 862 MB.
