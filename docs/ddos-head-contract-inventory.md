# Inventario del contrato de la cabeza DDoS — DAY282

Rama `feat/ddos-head-contract`. Todo lo que sigue esta MEDIDO (fichero:linea) salvo lo marcado como hipotesis.
Objetivo: una sola definicion de rasgos compartida train/serve (orden acordado DAY281, paso 2).

## 1. Donde vive cada pieza

- **Modelo unico**: `ml-detector/include/ml_defender/ddos_trees_inline.hpp`. El sniffer lo enlaza compilando
  `../ml-detector/src/{ddos,ransomware,traffic,internal}_detector.cpp` (`sniffer/CMakeLists.txt:260-263`).
- **Dos inferencias vivas sobre ese mismo modelo, con entradas distintas**:
  - **sniffer** — `ring_consumer.cpp::run_ml_detection` (~L1566): ejecuta las 4 cabezas en cada evento con
    entrada `ddos_embedded` (`ml_defender_features.cpp:23`) y umbrales `config_.ml_defender`. Escribe en el proto
    `final_classification`, `threat_category`, `overall_threat_score`. NO escribe veredicto en la provenance.
  - **ml-detector** — `zmq_handler.cpp`: entrada `extract_level2_ddos_features(nf)` (`feature_extractor.cpp:224`).
    Sobrescribe los tres campos anteriores.
  - Hipotesis sin medir: el CSV del ml-detector se escribe ANTES de su `set_threat_category` ⇒ la col 9
    (`threat_category`) contiene la categoria del SNIFFER.

## 2. Tres definiciones por rasgo

| Rasgo | Train (sintetico) | ml-detector (lo que come el bosque desplegado) | sniffer (`ddos_embedded`) |
|---|---|---|---|
| syn_ack_ratio | generador | no leido (0,000 observado DAY272) | `syn/(ack+1)`, tope 10 |
| packet_symmetry | generador | `fwd/(fwd+bwd)` (simetrico = 0,5) | `\|fwd−bwd\|/total` (simetrico = 0) |
| source_ip_dispersion | generador | `normalize(1,0,10)` = 0,1 constante | aggregator GLOBAL 30 s (no por victima) |
| protocol_anomaly | generador | 0 constante | heuristica de flags (SYN sin ACK, RST, FIN, URG) |
| packet_size_entropy | generador | `packet_length_std/1500` | entropia real de `all_lengths` |
| traffic_amplification | generador | no leido | `dbytes/sbytes`, tope 100 |
| flow_completion_rate | generador | no leido | {0; 0,5; 1} por flags |
| traffic_escalation | "tasa de crecimiento" lognormal | MB/s del flujo | pps/1000, tope 1 |
| resource_saturation | generador | `pkts/max(dur,1)/1000` | {0; 0,5; 1}: <100 B + >500 pps |

Ademas: los umbrales del .hpp estan en espacio MinMax de train; ambos lados de serve pasan valores crudos.
Ninguna de las dos escalation de serve es una "escalada": ambas son caudal instantaneo del flujo.

## 3. Que tiene disponible el sniffer

- **Por flujo** (`FlowStatistics`, `flow_manager.hpp:17`): spkts/dpkts, sbytes/dbytes, vectores completos de
  longitudes (fwd/bwd/all) y timestamps (fwd/bwd/all ⇒ IAT), flags TCP totales y direccionales, longitudes de
  cabecera, `TimeWindowManager` por flujo. Direccion = coincidencia con `FlowKey`.
- **Por victima** (`stamp_victim_window`, `ring_consumer.cpp:1223`, sellado en cada evento y en fast-alerts):
  `d_pkts`, `d_bytes`, `window_ms`, `seq`, `age_ms`. Kernel `ddos_victims` = `{pkts, bytes}` por `(dst_ip, proto)`,
  LRU 65536. SIN recuento de origenes, SIN historia de ventanas.

## 4. Huecos de diseno (no faltan datos: falta decidir)

- **H1** Dispersion de origenes POR VICTIMA: ni el kernel ni el aggregator actual la dan.
- **H2** Linea base por victima para una escalation real: la ventana es un delta sin historia; habria que
  guardarla en userspace (tablero).
- **H3** protocol_anomaly: decidir que significa antes de preguntar si es factible.

## 5. Decisiones abiertas (Alonso)

- **D1** Definicion unica por rasgo. Candidata base: la del sniffer (entropia real, heuristica de flags), revisando
  rasgo a rasgo; symmetry y escalation hay que redefinirlas con intencion.
- **D2** ¿El sniffer infiere o solo calcula? Hoy ejecuta 4 bosques por evento y el ml-detector pisa el resultado.
  Medible con `stats_.ml_detection_time_us` antes de decidir.
- **D3** Sin MinMaxScaler: bosque invariante a escala, umbrales en crudo.
- Dataset de train generado por EL MISMO codigo de serve (replay de pcaps por el sniffer, metodo DAY270).
