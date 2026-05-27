# Protobuf Contract — `network_security.proto`

> **Fuente canónica:** `protobuf/network_security.proto`
> **Schema version:** `v3.1.0` (`schema_version = 31`)
> **Última revisión:** DAY 91 — 19 marzo 2026

---

## Índice

1. [Filosofía de diseño](#filosofía-de-diseño)
2. [Arquitectura de mensajes](#arquitectura-de-mensajes)
3. [Mensaje principal: NetworkSecurityEvent](#mensaje-principal-networksecurityevent)
4. [Features de red: NetworkFeatures](#features-de-red-networkfeatures)
5. [Detectores embebidos PHASE 1](#detectores-embebidos-phase-1)
6. [Detección avanzada de ransomware: RansomwareFeatures](#detección-avanzada-de-ransomware-ransomwarefeatures)
7. [Sistema dual-score](#sistema-dual-score)
8. [Provenance multi-engine (ADR-002)](#provenance-multi-engine-adr-002)
9. [Geolocalización](#geolocalización)
10. [Pipeline y nodos distribuidos](#pipeline-y-nodos-distribuidos)
11. [Mensajes de firewall](#mensajes-de-firewall)
12. [Ambigüedades documentadas](#ambigüedades-documentadas)
13. [Campos reservados para features SMB (DAY 92+)](#campos-reservados-para-features-smb-day-92)

---

## Filosofía de diseño

- **Todo o nada** — sin campos legacy confusos, sin compatibilidad hacia atrás deliberada
- **`schema_version = 31`** corresponde a la versión semántica `v3.1.0`
- **PHASE 1** agrupa los 4 detectores embebidos C++20 (DDoS, Ransomware, Traffic, Internal)
- **PHASE 2** (enterprise/roadmap) incluye modelos ONNX externos y `RansomwareFeatures` (20 campos)

---

## Arquitectura de mensajes

```
NetworkSecurityEvent  ← mensaje raíz que viaja por el pipeline
├── NetworkFeatures           (83+ features ML del flujo)
│   ├── DDoSFeatures          (embebido, 10 features, PHASE 1)
│   ├── RansomwareEmbeddedFeatures  (embebido, 10 features, PHASE 1)
│   ├── TrafficFeatures       (embebido, 10 features, PHASE 1)
│   ├── InternalFeatures      (embebido, 10 features, PHASE 1)
│   └── RansomwareFeatures    (20 features, PHASE 2 enterprise — ver §Ambigüedades)
├── GeoEnrichment             (geolocalización 3-punto: sniffer/src/dst)
├── TricapaMLAnalysis         (resultados de los 3 niveles ML)
├── DetectionProvenance       (trazabilidad multi-engine, ADR-002)
├── DecisionMetadata          (divergencia fast vs ML, prioridad RAG)
├── PipelineTracking          (timestamps y métricas por etapa)
├── RAGAnalysis               (análisis contextual TinyLlama)
└── HumanInTheLoopReview      (feedback analista humano)
```

---

## Mensaje principal: NetworkSecurityEvent

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `event_id` | string | 1 | UUID único del evento |
| `event_timestamp` | Timestamp | 2 | Marca temporal del evento |
| `originating_node_id` | string | 3 | ID del nodo que origina el evento |
| `network_features` | NetworkFeatures | 4 | Features ML del flujo de red |
| `geo_enrichment` | GeoEnrichment | 5 | Enriquecimiento geográfico |
| `time_window` | TimeWindow | 6 | Ventana temporal del evento |
| `ml_analysis` | TricapaMLAnalysis | 7 | Análisis tricapa ML |
| `additional_model_predictions` | repeated ModelPrediction | 8 | Predicciones adicionales |
| `capturing_node` | DistributedNode | 9 | Nodo capturador |
| `pipeline_tracking` | PipelineTracking | 10 | Trazabilidad de pipeline |
| `rag_analysis` | RAGAnalysis | 11 | Análisis RAG |
| `human_review` | HumanInTheLoopReview | 12 | Revisión humana |
| `overall_threat_score` | double | 15 | Score global 0.0–1.0 |
| `final_classification` | string | 16 | `BENIGN` / `SUSPICIOUS` / `MALICIOUS` |
| `threat_category` | string | 17 | `DDOS` / `RANSOMWARE` / `NORMAL` / etc. |
| `correlation_id` | string | 20 | ID de correlación entre eventos |
| `related_event_ids` | repeated string | 21 | IDs de eventos relacionados |
| `event_chain_id` | string | 22 | Cadena de ataque |
| `schema_version` | uint32 | 25 | `31` = v3.1.0 |
| `custom_metadata` | map<string,string> | 26 | Metadatos custom |
| `event_tags` | repeated string | 27 | Tags del evento |
| `protobuf_version` | string | 28 | `"3.1.0"` |
| `fast_detector_score` | double | 29 | Score heurístico capa 1 (0.0–1.0) |
| `ml_detector_score` | double | 30 | Score ML capa 3 (0.0–1.0) |
| `authoritative_source` | DetectorSource | 31 | Quién determinó la amenaza final |
| `fast_detector_triggered` | bool | 32 | ¿Se activó el Fast Detector? |
| `fast_detector_reason` | string | 33 | Razón de activación |
| `decision_metadata` | DecisionMetadata | 34 | Metadatos de decisión para RAG |
| `provenance` | DetectionProvenance | 35 | Trazabilidad multi-engine (ADR-002) |

---

## Features de red: NetworkFeatures

### Identificación del flujo (campos 1–10)

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `source_ip` | string | 1 | IP origen |
| `destination_ip` | string | 2 | IP destino |
| `source_port` | uint32 | 3 | Puerto origen |
| `destination_port` | uint32 | 4 | Puerto destino |
| `protocol_number` | uint32 | 5 | Número de protocolo |
| `protocol_name` | string | 6 | Nombre del protocolo |
| `interface_mode` | uint32 | 7 | `0`=disabled, `1`=host-based, `2`=gateway |
| `is_wan_facing` | bool | 8 | `true`=WAN, `false`=LAN |
| `source_ifindex` | uint32 | 9 | Índice de interfaz de red |
| `source_interface` | string | 10 | Nombre de interfaz (`eth0`, `eth1`) |

### Timing (campos 11–13)

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `flow_start_time` | Timestamp | 11 | Inicio del flujo |
| `flow_duration` | Duration | 12 | Duración del flujo |
| `flow_duration_microseconds` | uint64 | 13 | Duración en microsegundos |

### Estadísticas de paquetes (campos 14–17)

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `total_forward_packets` | uint64 | 14 | Paquetes forward |
| `total_backward_packets` | uint64 | 15 | Paquetes backward |
| `total_forward_bytes` | uint64 | 16 | Bytes forward |
| `total_backward_bytes` | uint64 | 17 | Bytes backward |

### Estadísticas de longitud — Forward (campos 20–23) / Backward (30–33)

Incluyen `_max`, `_min`, `_mean`, `_std` para ambas direcciones.

### Velocidades y ratios (campos 40–47)

`flow_bytes_per_second`, `flow_packets_per_second`, `forward/backward_packets_per_second`, `download_upload_ratio`, tamaños medios.

### Inter-arrival times (campos 50–63)

Estadísticas de tiempo entre llegadas para flujo (50–53), forward (54–58), backward (59–63).

### TCP Flags counts (campos 70–81)

`fin`, `syn`, `rst`, `psh`, `ack`, `urg`, `cwe`, `ece` + versiones direccionales forward/backward para `psh` y `urg`.

### Headers y bulk transfer (campos 85–92)

Longitudes de cabecera y estadísticas de transferencia en bulk para ambas direcciones.

### Estadísticas adicionales (campos 95–99, 104–105)

`min/max/mean/std/variance` de longitud de paquetes, `active_mean`, `idle_mean`.

### Features para modelos ML (campos 100–103)

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `ddos_features` | repeated double | 100 | 83 features para DDoS |
| `ransomware_features` | repeated double | 101 | 83 features ransomware enterprise (PHASE 2) |
| `general_attack_features` | repeated double | 102 | 23 features RF general |
| `internal_traffic_features` | repeated double | 103 | 4–5 features tráfico interno |

### Detectores embebidos PHASE 1 (campos 112–115)

| Campo | Tipo | Nº | Descripción |
|---|---|---|---|
| `ddos_embedded` | DDoSFeatures | 112 | 10 features DDoS embebido |
| `ransomware_embedded` | RansomwareEmbeddedFeatures | 113 | 10 features ransomware PHASE 1 |
| `traffic_classification` | TrafficFeatures | 114 | 10 features clasificación tráfico |
| `internal_anomaly` | InternalFeatures | 115 | 10 features anomalía interna |

### Metadatos (campos 110–111)

`custom_features` y `feature_metadata` como mapas clave-valor.

---

## Detectores embebidos PHASE 1

### DDoSFeatures (mensaje embebido en campo 112)

| Campo | Nº | Rango esperado |
|---|---|---|
| `syn_ack_ratio` | 1 | 0.0–1.0 |
| `packet_symmetry` | 2 | 0.0–1.0 |
| `source_ip_dispersion` | 3 | 0.0–1.0 |
| `protocol_anomaly_score` | 4 | 0.0–1.0 |
| `packet_size_entropy` | 5 | 0.0–8.0 (bits) |
| `traffic_amplification_factor` | 6 | ≥ 1.0 |
| `flow_completion_rate` | 7 | 0.0–1.0 |
| `geographical_concentration` | 8 | 0.0–1.0 |
| `traffic_escalation_rate` | 9 | 0.0–1.0 |
| `resource_saturation_score` | 10 | 0.0–1.0 |

### RansomwareEmbeddedFeatures (mensaje embebido en campo 113)

10 features de comportamiento: `io_intensity`, `entropy`, `resource_usage`, `network_activity`, `file_operations`, `process_anomaly`, `temporal_pattern`, `access_frequency`, `data_volume`, `behavior_consistency`.

### TrafficFeatures (campo 114) / InternalFeatures (campo 115)

Ver proto fuente para lista completa. Ambos con 10 features especializadas.

---

## Detección avanzada de ransomware: RansomwareFeatures

> **Nota:** `RansomwareFeatures` es el mensaje de **20 features** para detección avanzada enterprise (**PHASE 2**, caja doméstica). No confundir con `RansomwareEmbeddedFeatures` (10 features, **PHASE 1**, campo 113 de `NetworkFeatures`). Ambos coexisten para migración gradual sin breaking changes. Ver campo `ransomware` (nº 106) en `NetworkFeatures`.

| Categoría | Campos |
|---|---|
| **C&C Communication** | `dns_query_entropy`, `new_external_ips_30s`, `dns_query_rate_per_min`, `failed_dns_queries_ratio`, `tls_self_signed_cert_count`, `non_standard_port_http_count` |
| **Lateral Movement** | `smb_connection_diversity`, `rdp_failed_auth_count`, `new_internal_connections_30s`, `port_scan_pattern_score` |
| **Exfiltration** | `upload_download_ratio_30s`, `burst_connections_count`, `unique_destinations_30s`, `large_upload_sessions_count` |
| **Behavioral** | `nocturnal_activity_flag`, `connection_rate_stddev`, `protocol_diversity_score`, `avg_flow_duration_seconds`, `tcp_rst_ratio`, `syn_without_ack_ratio` |

---

## Sistema dual-score

Introducido en DAY 13 (diciembre 2025). Preserva scores de ambos detectores para validación F1 contra CTU-13.

### DetectorSource (enum)

| Valor | Código | Significado |
|---|---|---|
| `DETECTOR_SOURCE_UNKNOWN` | 0 | Sin información |
| `DETECTOR_SOURCE_FAST_ONLY` | 1 | Solo Fast Detector activado |
| `DETECTOR_SOURCE_ML_ONLY` | 2 | Solo ML Detector activado |
| `DETECTOR_SOURCE_FAST_PRIORITY` | 3 | Ambos activos, Fast score mayor |
| `DETECTOR_SOURCE_ML_PRIORITY` | 4 | Ambos activos, ML score mayor |
| `DETECTOR_SOURCE_CONSENSUS` | 5 | Ambos activos, scores similares |
| `DETECTOR_SOURCE_DIVERGENCE` | 6 | Divergencia significativa (> 0.30) |

### DecisionMetadata

| Campo | Tipo | Descripción |
|---|---|---|
| `score_divergence` | double | `\|fast_score - ml_score\|` |
| `divergence_reason` | string | Explicación de divergencia |
| `requires_rag_analysis` | bool | Enviar a RAG para investigación |
| `investigation_priority` | string | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `anomaly_flags` | repeated string | Flags específicos detectados |
| `confidence_level` | double | Confianza en la decisión (0.0–1.0) |

**Umbrales de scoring (ml_detector_config.json):**

| Parámetro | Valor |
|---|---|
| `divergence_warn_threshold` | 0.30 |
| `divergence_high_threshold` | 0.40 |
| `malicious_threshold` | 0.70 |
| `requires_rag_threshold` | 0.85 |

---

## Provenance multi-engine (ADR-002)

Introducido en DAY 37 (enero 2026). Registra el veredicto de todos los engines de detección.

### EngineVerdict

| Campo | Tipo | Descripción |
|---|---|---|
| `engine_name` | string | `"fast-path-sniffer"`, `"random-forest"`, `"cnn-secondary"` |
| `classification` | string | `"Benign"`, `"DDoS"`, `"Ransomware"`, etc. |
| `confidence` | float | 0.0–1.0 |
| `reason_code` | string | `"SIG_MATCH"`, `"STAT_ANOMALY"`, `"PCA_OUTLIER"` |
| `timestamp_ns` | uint64 | Timestamp en nanosegundos |

### DetectionProvenance

| Campo | Tipo | Descripción |
|---|---|---|
| `verdicts` | repeated EngineVerdict | Todos los veredictos de engines |
| `global_timestamp_ns` | uint64 | Momento de la decisión final |
| `final_decision` | string | `"ALLOW"` / `"DROP"` / `"ALERT"` |
| `discrepancy_score` | float | 0.0 (total acuerdo) – 1.0 (máxima divergencia) |
| `logic_override` | string | Si RAG/humano forzó la decisión |
| `discrepancy_reason` | string | Explicación si los engines divergen |

---

## Geolocalización

### GeoEnrichment

Análisis geográfico en tres puntos: nodo sniffer, IP origen, IP destino.

**Análisis calculados:**

| Campo | Descripción |
|---|---|
| `source_destination_distance_km` | Distancia geográfica src→dst |
| `source_destination_same_country` | ¿Mismo país? |
| `distance_category` | `local` / `regional` / `national` / `international` |
| `geographic_anomaly_score` | 0.0–1.0 |
| `suspicious_geographic_pattern` | Flag booleano |

**Descubrimiento de IP pública** (para IPs privadas via `ip_discovery_service`).

---

## Pipeline y nodos distribuidos

### PipelineTracking — timestamps por etapa

```
packet_captured_at → features_extracted_at → geoip_enriched_at
    → ml_analyzed_at → threat_detected_at → action_taken_at
```

### DistributedNode — roles

| Rol | Componente ML Defender |
|---|---|
| `PACKET_SNIFFER` (0) | sniffer |
| `ML_ANALYZER` (3) | ml-detector |
| `THREAT_DETECTOR` (4) | ml-detector (fast path) |
| `FIREWALL_CONTROLLER` (5) | firewall-acl-agent |
| `DATA_AGGREGATOR` (6) | rag-ingester |
| `CLUSTER_COORDINATOR` (8) | etcd-server |

---

## Mensajes de firewall

### Detection (mensaje simple para firewall-acl-agent)

| Campo | Tipo | Descripción |
|---|---|---|
| `src_ip` | string | IP a bloquear |
| `type` | DetectionType | `DDOS`/`RANSOMWARE`/`SUSPICIOUS_TRAFFIC`/`INTERNAL_THREAT` |
| `confidence` | float | Score de confianza |
| `timestamp` | uint64 | Timestamp del evento |
| `action` | string | `"BLOCK"` / `"ALERT"` / `"LOG"` |
| `duration_seconds` | uint32 | Duración del bloqueo (`0` = permanente) |

`DetectionBatch` agrupa múltiples `Detection` para procesamiento en lote.

---

## Ambigüedades documentadas

### RansomwareFeatures vs RansomwareEmbeddedFeatures

**Esta dualidad es intencional.** Coexisten para migración gradual sin breaking changes:

| Mensaje | Campos | Campo en NetworkFeatures | Fase |
|---|---|---|---|
| `RansomwareEmbeddedFeatures` | 10 | `ransomware_embedded` (nº 113) | **PHASE 1** — activo en producción |
| `RansomwareFeatures` | 20 | `ransomware` (nº 106) | **PHASE 2** — enterprise/roadmap |

---

## Campos reservados para features SMB (DAY 92+)

> **Pendiente de implementación en DAY 92** — rama `feature/smb-detection-features`

Se añadirá el mensaje `SMBScanFeatures` para detección WannaCry/NotPetya:

```protobuf
// SMBScanFeatures — features de escaneo SMB (WannaCry/NotPetya)
// SYN-1, SYN-2: rst_ratio y syn_ack_ratio (P1 — DAY 92)
// SYN-8b: flow_duration_min_ms (P2 — DAY 97+)
message SMBScanFeatures {
    optional float rst_ratio            = 1;  // RST/SYN — WannaCry > 0.70
    optional float syn_ack_ratio        = 2;  // ACK/SYN — WannaCry < 0.10
    optional float flow_duration_min_ms = 3;  // P2 — flujos WannaCry < 50ms
}
```

**Umbrales de referencia WannaCry:**
- `rst_ratio > 0.70` → señal maligna
- `syn_ack_ratio < 0.10` → señal maligna
- `syn_flag_count == 0` → sentinel `MISSING_FEATURE_SENTINEL = -9999.0f`

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*DAY 92 — 20 marzo 2026*