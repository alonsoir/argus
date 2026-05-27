# aRGus NDR — XGBoost Feature Set (ADR-026)

## Decisión: Opción A — mismo feature set que RF (unanimidad Consejo DAY 119)

El modelo XGBoost usa exactamente las mismas 23 features que el RF baseline
validado en CTU-13 Neris (F1=0.9985, FPR=6.61%). Esto garantiza que el delta
RF vs XGBoost sea una contribución científica limpia y publicable en §4 del paper.

## Feature vector — LEVEL1 (23 features)

Fuente canónica: `ml-detector/src/feature_extractor.cpp` → `LEVEL1_FEATURE_NAMES`
Función de extracción: `FeatureExtractor::extract_level1_features()`

| Index | Nombre                        | Campo protobuf                              | Unidad         |
|-------|-------------------------------|---------------------------------------------|----------------|
| 0     | Packet Length Std             | nf.packet_length_std()                      | bytes          |
| 1     | Subflow Fwd Bytes             | nf.total_forward_bytes()                    | bytes          |
| 2     | Fwd Packet Length Max         | nf.forward_packet_length_max()              | bytes          |
| 3     | Avg Fwd Segment Size          | nf.average_forward_segment_size()           | bytes          |
| 4     | ACK Flag Count                | nf.ack_flag_count()                         | count          |
| 5     | Packet Length Variance        | nf.packet_length_variance()                 | bytes²         |
| 6     | PSH Flag Count                | nf.psh_flag_count()                         | count          |
| 7     | Bwd Packet Length Max         | nf.backward_packet_length_max()             | bytes          |
| 8     | act_data_pkt_fwd              | nf.total_forward_packets()                  | count          |
| 9     | Total Length of Fwd Packets   | nf.total_forward_bytes()                    | bytes          |
| 10    | Fwd Packet Length Std         | nf.forward_packet_length_std()              | bytes          |
| 11    | Fwd Packets/s                 | nf.forward_packets_per_second()             | pkt/s          |
| 12    | Subflow Bwd Bytes             | nf.total_backward_bytes()                   | bytes          |
| 13    | Destination Port              | nf.destination_port()                       | port number    |
| 14    | Init_Win_bytes_forward        | hardcoded 0.0f (TODO: añadir a protobuf)    | bytes          |
| 15    | Subflow Fwd Packets           | nf.total_forward_packets()                  | count          |
| 16    | Fwd IAT Min                   | nf.forward_inter_arrival_time_min()         | microseconds   |
| 17    | Packet Length Mean            | nf.packet_length_mean()                     | bytes          |
| 18    | Total Length of Bwd Packets   | nf.total_backward_bytes()                   | bytes          |
| 19    | Bwd Packet Length Mean        | nf.backward_packet_length_mean()            | bytes          |
| 20    | Bwd Packet Length Min         | nf.backward_packet_length_min()             | bytes          |
| 21    | Flow Duration                 | nf.flow_duration_microseconds() / 1e6       | seconds        |
| 22    | Flow Packets/s                | nf.flow_packets_per_second()                | pkt/s          |

## Contrato del vector

- Tipo: `float32[]` contiguo en memoria, row-major
- Tamaño: exactamente 23 elementos
- Sin NaN ni Inf (validado por `FeatureExtractor::validate_features()`)
- Feature 14 (`Init_Win_bytes_forward`) siempre 0.0f — deuda técnica documentada
- Rango razonable: [-1e9, 1e9] por feature (warning si se supera)

## Dataset de validación

- CTU-13 Scenario 9 (Neris botnet)
- Gate de calidad: F1 ≥ 0.9985 + Precision ≥ 0.99
- RF baseline: F1=0.9985, FPR=6.61%

## Nota para el paper (arXiv:2604.04952 §4)

La tabla comparativa RF vs XGBoost usará este feature set idéntico.
El delta de latencia y métricas es la contribución científica de ADR-026.
