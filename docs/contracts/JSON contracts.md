# JSON Contracts — Configuración de Componentes

> **Principio:** `JSON is the law` — toda configuración operacional vive en JSON, nunca en código hardcodeado.
> **Última revisión:** DAY 92 — 20 marzo 2026

---

## Índice

1. [sniffer.json](#snifferjson)
2. [ml_detector_config.json](#ml_detector_configjson)
3. [firewall.json](#firewalljson)
4. [rag-ingester.json](#rag-ingesterjson)
5. [rag-config.json](#rag-configjson)
6. [Convenciones comunes](#convenciones-comunes)
7. [Flujo de datos entre componentes](#flujo-de-datos-entre-componentes)

---

## sniffer.json

**Path:** `sniffer/config/sniffer.json`
**Versión actual:** `3.3.3`
**Componente:** `cpp_evolutionary_sniffer`

### Deployment — modos de operación

El sniffer soporta 4 modos de despliegue:

| Modo | Descripción |
|---|---|
| `host-only` | NIC única — protege solo el host (defensa bastión) |
| `gateway-only` | NIC única — inspecciona tráfico en tránsito (modo router) |
| `dual` | Dual NIC — protección de host + inspección gateway simultánea |
| `validation` | Testing — soporte de replay libpcap para validación con PCAPs |

**Configuración activa:** `dual`

**Interfaces Vagrant (entorno lab):**

| Interfaz | Rol | IP | Comportamiento |
|---|---|---|---|
| `eth0` | NAT | — | Administración Vagrant |
| `eth1` | WAN / host-based | `192.168.56.20` | Captura ingress only — `interface_mode=1` |
| `eth2` | LAN / gateway | `192.168.100.1` | Captura bidireccional — `interface_mode=2` |

### Profiles

| Profile | Worker threads | Compresión | Uso |
|---|---|---|---|
| `lab` | 2 | nivel 1 | Entorno Vagrant/VirtualBox |
| `cloud` | 8 | nivel 3 | Instancias cloud |
| `bare_metal` | 16 | nivel 1 | Hardware dedicado |
| `dual_nic` | 6 | nivel 1 | Dual-NIC lab (activo) |

**Profile activo:** `dual_nic`

### Captura (sección `capture`)

| Parámetro | Valor | Descripción |
|---|---|---|
| `mode` | `ebpf_skb` | Modo eBPF SKB (compatible VirtualBox) |
| `xdp_mode` | `skb` | XDP genérico |
| `excluded_ports` | `[22]` | SSH excluido siempre |
| `default_action` | `capture` | Capturar todo lo no excluido |
| `included_protocols` | `tcp, udp, icmp` | Protocolos capturados |
| `buffer_size` | 65536 | Tamaño del buffer de captura |

### Kernel space — features extraídas en eBPF

```
source_ip, destination_ip, source_port, destination_port,
protocol_number, total_forward_packets, total_backward_packets,
total_forward_bytes, total_backward_bytes,
fin_flag_count, syn_flag_count, rst_flag_count,
psh_flag_count, ack_flag_count, urg_flag_count
```

### Transporte

| Parámetro | Valor |
|---|---|
| `compression.algorithm` | `lz4` (nivel 1) |
| `encryption.algorithm` | `chacha20-poly1305` |
| `encryption.key_rotation_hours` | 24 |
| `zmq_curve_enabled` | `true` |
| `output_socket` | `127.0.0.1:5571` (PUSH) |

### Fast Detector — thresholds externalizados (DAY 12)

> Principio Via Appia Quality: sin thresholds hardcodeados, el JSON manda.

**Activación (cualquier condición activa el detector):**

| Condición | Umbral |
|---|---|
| `external_ips_30s` | > 15 IPs en 30s |
| `smb_diversity` | > 10 conexiones SMB distintas |
| `dns_entropy` | > 2.5 bits |
| `failed_dns_ratio` | > 0.30 |
| `upload_download_ratio` | > 3.0 |
| `burst_connections` | > 50 conexiones en burst |
| `unique_destinations_30s` | > 30 destinos únicos en 30s |

**Scores:**

| Nivel | Score |
|---|---|
| `high_threat` | 0.95 |
| `suspicious` | 0.70 |
| `alert` | 0.75 |

**Clasificación:**
- `high_threat` si: `external_ips_30s > umbral` OR `smb_diversity > umbral`
- `suspicious` si: `dns_entropy > umbral` OR `burst_connections > umbral`

### ML Defender — thresholds de detección

| Detector | Umbral |
|---|---|
| `ddos` | 0.85 |
| `ransomware` | 0.90 |
| `traffic` | 0.80 |
| `internal` | 0.85 |

Rango válido: `[0.5, 0.99]`. Fallback: `0.75`.

### Buffers y ventanas temporales

| Parámetro | Valor |
|---|---|
| `flow_tracking_window_seconds` | 300 |
| `feature_aggregation_window_seconds` | 30 |
| `max_flows_per_window` | 100.000 |
| `flow_state_buffer_entries` | 500.000 |
| `ring_buffer_entries` | 65.536 |

### Logging

- **Path:** `/vagrant/logs/lab/sniffer.log`
- **Level:** `INFO`
- **Rotación:** 10 ficheros × 200 MB

---

## ml_detector_config.json

**Path:** `ml-detector/config/ml_detector_config.json`
**Versión actual:** `1.0.0`
**Componente:** `cpp_ml_detector_tricapa`

### Arquitectura tricapa

```
Nivel 1 — Detección general
    └── Random Forest, 23 features, ONNX (level1_attack_detector.onnx)
         threshold: 0.65

Nivel 2 — Clasificadores especializados (embebidos C++20)
    ├── DDoS Binary Detector    — 10 features, < 50μs, threshold: 0.70
    └── Ransomware Detector     — 10 features, < 55μs, threshold: 0.75

Nivel 3 — Especialización avanzada (embebidos C++20)
    ├── Traffic Classifier      — 10 features, < 50μs, threshold: 0.60
    └── Internal Anomaly        — 10 features, < 48μs, threshold: 0.65
```

### Sockets ZMQ

| Socket | Endpoint | Tipo | Rol |
|---|---|---|---|
| Input | `tcp://127.0.0.1:5571` | PULL | Recibe de sniffer |
| Output | `tcp://0.0.0.0:5572` | PUB | Publica a firewall y RAG |

### Modelos Nivel 1 (ONNX)

| Parámetro | Valor |
|---|---|
| `model_file` | `models/production/level1/level1_attack_detector.onnx` |
| `scaler_file` | `models/production/level1/scaler.json` |
| `features_count` | 23 |
| `requires_scaling` | `true` |
| `timeout_ms` | 10 |

### Modelos Nivel 2 (C++20 embebidos)

**DDoS Binary Detector:**

Features: `syn_ack_ratio`, `packet_symmetry`, `source_ip_dispersion`, `protocol_anomaly_score`, `packet_size_entropy`, `traffic_amplification_factor`, `flow_completion_rate`, `geographical_concentration`, `traffic_escalation_rate`, `resource_saturation_score`

**Ransomware Detector Embedded:**

Features: `io_intensity`, `entropy`, `resource_usage`, `network_activity`, `file_operations`, `process_anomaly`, `temporal_pattern`, `access_frequency`, `data_volume`, `behavior_consistency`

### Modelos Nivel 3 (C++20 embebidos)

**Traffic Classifier:** `packet_rate`, `connection_rate`, `tcp_udp_ratio`, `avg_packet_size`, `port_entropy`, `flow_duration_std`, `src_ip_entropy`, `dst_ip_concentration`, `protocol_variety`, `temporal_consistency`

**Internal Anomaly Detector:** `internal_connection_rate`, `service_port_consistency`, `protocol_regularity`, `packet_size_consistency`, `connection_duration_std`, `lateral_movement_score`, `service_discovery_patterns`, `data_exfiltration_indicators`, `temporal_anomaly_score`, `access_pattern_entropy`

### Scoring y divergencia

| Parámetro | Valor | Significado |
|---|---|---|
| `divergence_warn_threshold` | 0.30 | Divergencia fast/ML que genera warning |
| `divergence_high_threshold` | 0.40 | Divergencia alta — análisis RAG |
| `malicious_threshold` | 0.70 | Score mínimo para clasificar MALICIOUS |
| `requires_rag_threshold` | 0.85 | Score que dispara análisis RAG |

### CSV writer (eventos para RAG)

| Parámetro | Valor |
|---|---|
| `base_dir` | `/vagrant/logs/ml-detector/events/` |
| `min_score_threshold` | 0.50 |
| `max_events_per_file` | 10.000 |

### Logging

- **Path:** `/vagrant/logs/lab/detector.log`
- **Level:** `INFO`
- **Rotación:** 10 ficheros × 200 MB

---

## firewall.json

**Path:** `firewall-acl-agent/config/firewall.json`
**Versión actual:** `1.2.1`
**Componente:** `firewall-acl-agent`

### Rol en el pipeline

El firewall-acl-agent es el **endpoint final** del pipeline. Solo **descifra** y **descomprime** — no cifra ni comprime salidas (no tiene downstream).

**Flujo de procesamiento:**
```
1. Recibir mensaje ZMQ de ml-detector (cifrado + comprimido)  → puerto 5572
2. Descifrar con ChaCha20-Poly1305 (token desde etcd)
3. Descomprimir con LZ4
4. Parsear Protobuf (Detection/DetectionBatch)
5. Aplicar reglas IPTables / IPSet
```

### Socket ZMQ

| Parámetro | Valor |
|---|---|
| `endpoint` | `tcp://localhost:5572` |
| `socket_type` | SUB |
| `recv_timeout_ms` | 1000 |

### IPSets

| Set | Nombre | Max elementos | Timeout |
|---|---|---|---|
| Blacklist | `ml_defender_blacklist_test` | 1000 | 3600s |
| Whitelist | `ml_defender_whitelist` | 500 | 0 (permanente) |

**IPTables:** cadena `ML_DEFENDER_TEST`, política default `ACCEPT`.

```
iptables -A INPUT -m set --match-set ml_defender_blacklist_test src -j DROP
```

### Validación de IPs

Rangos permitidos para bloqueo:

```
192.168.0.0/16
10.0.0.0/8
172.16.0.0/12
```

`block_localhost: false` — nunca bloquear localhost.

### Procesamiento en batch

| Parámetro | Valor |
|---|---|
| `batch_size_threshold` | 10 |
| `batch_time_threshold_ms` | 1000 |
| `min_confidence` | 0.50 |

### CSV batch logger (para RAG)

- **Output:** `/vagrant/logs/firewall_logs/`
- **Batch size:** 100 eventos
- **Batch timeout:** 5s
- Las CSVs incluyen firma HMAC para detección de manipulación

### Logging

- **Path:** `/vagrant/logs/lab/firewall-agent.log`
- **Level:** `debug`
- **Rotación:** 5 ficheros × 10 MB

---

## rag-ingester.json

**Path:** `rag-ingester/config/rag-ingester.json`
**Versión actual:** `0.1.0`
**Componente:** `rag-ingester`

### Rol en el pipeline

Consume eventos de dos fuentes CSV (ml-detector + firewall), genera embeddings y los indexa en FAISS para consultas del rag-security.

### Fuentes de datos

| Fuente | Path | HMAC |
|---|---|---|
| ML Detector events | `/vagrant/logs/ml-detector/events/` | clave en `csv_ml_detector_hmac_key_hex` |
| Firewall blocks | `/vagrant/logs/firewall_logs/firewall_blocks.csv` | clave en `csv_firewall_hmac_key_hex` |

Parámetro `replay_on_start: true` — re-procesa CSVs existentes al arrancar.

### Embedders (modelos ONNX)

| Embedder | Modelo ONNX | Input dim | Output dim | Uso |
|---|---|---|---|---|
| `chronos` | `chronos.onnx` | 83 | 512 | Patrones temporales |
| `sbert` | `sbert.onnx` | 83 | 384 | Semántica de seguridad |
| `attack` | `attack.onnx` | 83 | 256 | Clasificación de ataques |

`attack` tiene `benign_sample_rate: 0.1` — submuestreo de tráfico benigno.

### PCA — reducción de dimensionalidad (anti-curse)

| Embedder | Modelo PCA | Dim entrada | Dim salida |
|---|---|---|---|
| chronos | `chronos_512_128.faiss` | 512 | 128 |
| sbert | `sbert_384_96.faiss` | 384 | 96 |
| attack | `attack_256_64.faiss` | 256 | 64 |

### FAISS

| Parámetro | Valor |
|---|---|
| `index_type` | `Flat` |
| `metric` | `L2` |
| `persist_path` | `/shared/faiss_indexes` |
| `checkpoint_interval_events` | 1000 |

### Health monitoring

| Threshold | Valor | Acción |
|---|---|---|
| `cv_warning_threshold` | 0.20 | Warning en logs |
| `cv_critical_threshold` | 0.15 | Alerta crítica a etcd |

---

## rag-config.json

**Path:** `rag/config/rag-config.json`
**Componente:** `rag-security`

### Modelo LLM

| Parámetro | Valor |
|---|---|
| `model_name` | `tinyllama-1.1b-chat-v1.0.Q4_0.gguf` |
| `embedding_dimension` | 512 |
| `context_size` | 2048 |
| `gpu_layers` | 0 (CPU only) |

### Dimensiones FAISS (deben coincidir con rag-ingester tras PCA)

| Índice | Dimensión |
|---|---|
| `chronos_dim` | 128 |
| `sbert_dim` | 96 |
| `attack_dim` | 64 |

### Capacidades habilitadas

```
component_management  — gestión del ciclo de vida de componentes
config_validation     — validación de configuración JSON
pipeline_control      — control del pipeline completo
embedder_system       — gestión del sistema de embeddings
faiss_search          — consultas FAISS
```

### Transporte

| Parámetro | Valor |
|---|---|
| `compression` | `lz4` |
| `encryption` | `AES-256-CBC` |
| `requires_encryption` | `true` |
| `security_level` | 3 |

### Logging

- **Path:** `/vagrant/logs/rag.log`
- **Level:** `info`
- **Mode:** append

---

## Convenciones comunes

### Puertos ZMQ del pipeline

```
sniffer  →[5571 PUSH/PULL]→  ml-detector  →[5572 PUB/SUB]→  firewall-acl-agent
                                                          └→  rag-security (subscriber)
```

### Etcd — paths de configuración

| Componente | Config path | Crypto token path |
|---|---|---|
| sniffer | `/config/sniffer` | `/crypto/sniffer/tokens` |
| ml-detector | `/config/ml-detector` | `/crypto/ml-detector/tokens` |
| firewall | `/config/firewall` | `/crypto/firewall/tokens` |

### Sentinel value

`MISSING_FEATURE_SENTINEL = -9999.0f` — valor matemáticamente inalcanzable que indica feature ausente. Nunca usar `0.0f` ni `0.5f` para indicar ausencia.

### Schema version

`schema_version = 31` en protobuf equivale a `v3.1.0` semántico. Todos los componentes deben validar esta versión al procesar eventos.

### Rotación de logs

Todos los componentes siguen el patrón:
- Path: `/vagrant/logs/lab/<componente>.log`
- Tamaño máximo: 200 MB (10 MB en firewall)
- Backup count: 10 (5 en firewall)

---

## Flujo de datos entre componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    ML DEFENDER PIPELINE                      │
│                                                             │
│  ┌──────────┐   proto+lz4     ┌─────────────┐              │
│  │  sniffer  │ ──[5571 PUSH]──▶ ml-detector  │              │
│  │  eth1/2   │  +chacha20     │  3 niveles   │              │
│  └──────────┘                 └──────┬───────┘              │
│                                      │ proto+lz4+chacha20   │
│                                      │ [5572 PUB]           │
│                           ┌──────────┴──────────┐           │
│                           ▼                     ▼           │
│                  ┌──────────────┐      ┌─────────────────┐  │
│                  │  firewall-   │      │  rag-security   │  │
│                  │  acl-agent   │      │  (subscriber)   │  │
│                  │  iptables/   │      │  TinyLlama      │  │
│                  │  ipset       │      └────────┬────────┘  │
│                  └──────────────┘               │           │
│                         │ CSV+HMAC              │ FAISS     │
│                         ▼                       ▼           │
│                  ┌──────────────────────────────────────┐   │
│                  │           rag-ingester               │   │
│                  │  chronos + sbert + attack embedders  │   │
│                  └──────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐                                           │
│  │  etcd-server │ ← coordinación, crypto tokens, heartbeat  │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*DAY 92 — 20 marzo 2026*