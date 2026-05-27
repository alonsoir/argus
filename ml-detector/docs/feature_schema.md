# FEATURE_SCHEMA.md
# ML Defender — CSV Feature Schema (Day 64)
# Authors: Alonso Isidoro Roman + Claude (Anthropic)
#
# CONTRACT between ml-detector (producer) and rag-ingester (consumer).
# Any change to column order, count, or type is a BREAKING CHANGE and
# requires bumping CSV_SCHEMA_VERSION and updating CsvEventLoader.
#
# CSV_SCHEMA_VERSION: 1.0
# CSV_TOTAL_COLS:     127
# CSV_HAS_HEADER:     false  (no header row written)
# CSV_DELIMITER:      comma
# CSV_FLOAT_PRECISION: 6 decimal places (%.6f)
# CSV_STRING_ENCODING: UTF-8, strings quoted only if they contain comma or newline
#
# WHO FILLS WHAT
# ──────────────
# sniffer-eBPF   → populates NetworkFeatures scalar fields (Section 2)
# ml-detector    → populates embedded detector sub-messages (Section 3)
#                  and TricapaMLAnalysis predictions (Section 4)
# etcd-server    → provides HMAC key used in Section 5
#
# ZERO VALUES
# ───────────
# If a field was not populated by its producer, it appears as 0 (numeric)
# or empty string (text). CsvEventLoader must tolerate zeros gracefully.
# A future FEATURE_SCHEMA v1.1 may add a bitmask column flagging which
# sections were actually populated.

---

## Section 1 — Event Metadata (cols 0–13, 14 total)

| Col | Name              | Type   | Source        | Proto field / notes                          |
|-----|-------------------|--------|---------------|----------------------------------------------|
| 0   | timestamp_ns      | uint64 | ml-detector   | event_timestamp.seconds * 1e9                |
| 1   | event_id          | string | ml-detector   | NetworkSecurityEvent.event_id                |
| 2   | src_ip            | string | sniffer       | network_features.source_ip                   |
| 3   | dst_ip            | string | sniffer       | network_features.destination_ip              |
| 4   | src_port          | uint32 | sniffer       | network_features.source_port                 |
| 5   | dst_port          | uint32 | sniffer       | network_features.destination_port            |
| 6   | protocol          | string | sniffer       | network_features.protocol_name               |
| 7   | final_class       | string | ml-detector   | NetworkSecurityEvent.final_classification    |
| 8   | confidence        | float  | ml-detector   | TricapaMLAnalysis.ensemble_confidence        |
| 9   | threat_category   | string | ml-detector   | NetworkSecurityEvent.threat_category         |
| 10  | fast_score        | float  | ml-detector   | NetworkSecurityEvent.fast_detector_score     |
| 11  | ml_score          | float  | ml-detector   | NetworkSecurityEvent.ml_detector_score       |
| 12  | divergence        | float  | ml-detector   | DecisionMetadata.score_divergence            |
| 13  | final_decision    | string | ml-detector   | DetectionProvenance.final_decision           |

---

## Section 2 — Raw NetworkFeatures from sniffer (cols 14–75, 62 total)

All values read directly from NetworkSecurityEvent.network_features.
Sniffer populates these; ml-detector passes them through unchanged.

### 2.1 — Packet counts (cols 14–17)

| Col | Name                    | Type   | Proto field                       |
|-----|-------------------------|--------|-----------------------------------|
| 14  | total_fwd_packets       | uint64 | total_forward_packets             |
| 15  | total_bwd_packets       | uint64 | total_backward_packets            |
| 16  | total_fwd_bytes         | uint64 | total_forward_bytes               |
| 17  | total_bwd_bytes         | uint64 | total_backward_bytes              |

### 2.2 — Forward packet length stats (cols 18–21)

| Col | Name                    | Type   | Proto field                       |
|-----|-------------------------|--------|-----------------------------------|
| 18  | fwd_pkt_len_max         | uint64 | forward_packet_length_max         |
| 19  | fwd_pkt_len_min         | uint64 | forward_packet_length_min         |
| 20  | fwd_pkt_len_mean        | double | forward_packet_length_mean        |
| 21  | fwd_pkt_len_std         | double | forward_packet_length_std         |

### 2.3 — Backward packet length stats (cols 22–25)

| Col | Name                    | Type   | Proto field                       |
|-----|-------------------------|--------|-----------------------------------|
| 22  | bwd_pkt_len_max         | uint64 | backward_packet_length_max        |
| 23  | bwd_pkt_len_min         | uint64 | backward_packet_length_min        |
| 24  | bwd_pkt_len_mean        | double | backward_packet_length_mean       |
| 25  | bwd_pkt_len_std         | double | backward_packet_length_std        |

### 2.4 — Flow speeds and ratios (cols 26–33)

| Col | Name                      | Type   | Proto field                     |
|-----|---------------------------|--------|---------------------------------|
| 26  | flow_bytes_per_sec        | double | flow_bytes_per_second           |
| 27  | flow_packets_per_sec      | double | flow_packets_per_second         |
| 28  | fwd_packets_per_sec       | double | forward_packets_per_second      |
| 29  | bwd_packets_per_sec       | double | backward_packets_per_second     |
| 30  | dl_ul_ratio               | double | download_upload_ratio           |
| 31  | avg_packet_size           | double | average_packet_size             |
| 32  | avg_fwd_segment_size      | double | average_forward_segment_size    |
| 33  | avg_bwd_segment_size      | double | average_backward_segment_size   |

### 2.5 — Flow inter-arrival times (cols 34–37)

| Col | Name                      | Type   | Proto field                         |
|-----|---------------------------|--------|-------------------------------------|
| 34  | flow_iat_mean             | double | flow_inter_arrival_time_mean        |
| 35  | flow_iat_std              | double | flow_inter_arrival_time_std         |
| 36  | flow_iat_max              | uint64 | flow_inter_arrival_time_max         |
| 37  | flow_iat_min              | uint64 | flow_inter_arrival_time_min         |

### 2.6 — Forward inter-arrival times (cols 38–42)

| Col | Name                      | Type   | Proto field                             |
|-----|---------------------------|--------|-----------------------------------------|
| 38  | fwd_iat_total             | double | forward_inter_arrival_time_total        |
| 39  | fwd_iat_mean              | double | forward_inter_arrival_time_mean         |
| 40  | fwd_iat_std               | double | forward_inter_arrival_time_std          |
| 41  | fwd_iat_max               | uint64 | forward_inter_arrival_time_max          |
| 42  | fwd_iat_min               | uint64 | forward_inter_arrival_time_min          |

### 2.7 — Backward inter-arrival times (cols 43–47)

| Col | Name                      | Type   | Proto field                              |
|-----|---------------------------|--------|------------------------------------------|
| 43  | bwd_iat_total             | double | backward_inter_arrival_time_total        |
| 44  | bwd_iat_mean              | double | backward_inter_arrival_time_mean         |
| 45  | bwd_iat_std               | double | backward_inter_arrival_time_std          |
| 46  | bwd_iat_max               | uint64 | backward_inter_arrival_time_max          |
| 47  | bwd_iat_min               | uint64 | backward_inter_arrival_time_min          |

### 2.8 — TCP flag counts (cols 48–55)

| Col | Name                      | Type   | Proto field          |
|-----|---------------------------|--------|----------------------|
| 48  | fin_flag_count            | uint32 | fin_flag_count       |
| 49  | syn_flag_count            | uint32 | syn_flag_count       |
| 50  | rst_flag_count            | uint32 | rst_flag_count       |
| 51  | psh_flag_count            | uint32 | psh_flag_count       |
| 52  | ack_flag_count            | uint32 | ack_flag_count       |
| 53  | urg_flag_count            | uint32 | urg_flag_count       |
| 54  | cwe_flag_count            | uint32 | cwe_flag_count       |
| 55  | ece_flag_count            | uint32 | ece_flag_count       |

### 2.9 — Directional TCP flags (cols 56–59)

| Col | Name                      | Type   | Proto field          |
|-----|---------------------------|--------|----------------------|
| 56  | fwd_psh_flags             | uint32 | forward_psh_flags    |
| 57  | bwd_psh_flags             | uint32 | backward_psh_flags   |
| 58  | fwd_urg_flags             | uint32 | forward_urg_flags    |
| 59  | bwd_urg_flags             | uint32 | backward_urg_flags   |

### 2.10 — Headers and bulk transfer (cols 60–67)

| Col | Name                        | Type   | Proto field                       |
|-----|-----------------------------|--------|-----------------------------------|
| 60  | fwd_header_length           | double | forward_header_length             |
| 61  | bwd_header_length           | double | backward_header_length            |
| 62  | fwd_avg_bytes_bulk          | double | forward_average_bytes_bulk        |
| 63  | fwd_avg_packets_bulk        | double | forward_average_packets_bulk      |
| 64  | fwd_avg_bulk_rate           | double | forward_average_bulk_rate         |
| 65  | bwd_avg_bytes_bulk          | double | backward_average_bytes_bulk       |
| 66  | bwd_avg_packets_bulk        | double | backward_average_packets_bulk     |
| 67  | bwd_avg_bulk_rate           | double | backward_average_bulk_rate        |

### 2.11 — Global packet length stats (cols 68–72)

| Col | Name                      | Type   | Proto field               |
|-----|---------------------------|--------|---------------------------|
| 68  | min_packet_length         | uint64 | minimum_packet_length     |
| 69  | max_packet_length         | uint64 | maximum_packet_length     |
| 70  | packet_length_mean        | double | packet_length_mean        |
| 71  | packet_length_std         | double | packet_length_std         |
| 72  | packet_length_variance    | double | packet_length_variance    |

### 2.12 — Active / idle (cols 73–74)

| Col | Name                      | Type   | Proto field   |
|-----|---------------------------|--------|---------------|
| 73  | active_mean               | double | active_mean   |
| 74  | idle_mean                 | double | idle_mean     |

### 2.13 — Flow duration (col 75)

| Col | Name                      | Type   | Proto field                    |
|-----|---------------------------|--------|--------------------------------|
| 75  | flow_duration_us          | uint64 | flow_duration_microseconds     |

---

## Section 3 — Embedded Detector Features (cols 76–115, 40 total)

Computed by ml-detector's four embedded C++20 detectors.
Each sub-message maps 1:1 to a proto message field in NetworkFeatures.

### 3.1 — DDoS embedded features (cols 76–85)
Proto: network_features.ddos_embedded (DDoSFeatures)

| Col | Name                         | Proto field                      |
|-----|------------------------------|----------------------------------|
| 76  | ddos_syn_ack_ratio           | syn_ack_ratio                    |
| 77  | ddos_packet_symmetry         | packet_symmetry                  |
| 78  | ddos_src_ip_dispersion       | source_ip_dispersion             |
| 79  | ddos_protocol_anomaly_score  | protocol_anomaly_score           |
| 80  | ddos_packet_size_entropy     | packet_size_entropy              |
| 81  | ddos_traffic_amplification   | traffic_amplification_factor     |
| 82  | ddos_flow_completion_rate    | flow_completion_rate             |
| 83  | ddos_geo_concentration       | geographical_concentration       |
| 84  | ddos_traffic_escalation      | traffic_escalation_rate          |
| 85  | ddos_resource_saturation     | resource_saturation_score        |

### 3.2 — Ransomware embedded features (cols 86–95)
Proto: network_features.ransomware_embedded (RansomwareEmbeddedFeatures)

| Col | Name                         | Proto field              |
|-----|------------------------------|--------------------------|
| 86  | rsw_io_intensity             | io_intensity             |
| 87  | rsw_entropy                  | entropy                  |
| 88  | rsw_resource_usage           | resource_usage           |
| 89  | rsw_network_activity         | network_activity         |
| 90  | rsw_file_operations          | file_operations          |
| 91  | rsw_process_anomaly          | process_anomaly          |
| 92  | rsw_temporal_pattern         | temporal_pattern         |
| 93  | rsw_access_frequency         | access_frequency         |
| 94  | rsw_data_volume              | data_volume              |
| 95  | rsw_behavior_consistency     | behavior_consistency     |

### 3.3 — Traffic classification features (cols 96–105)
Proto: network_features.traffic_classification (TrafficFeatures)

| Col | Name                         | Proto field               |
|-----|------------------------------|---------------------------|
| 96  | trf_packet_rate              | packet_rate               |
| 97  | trf_connection_rate          | connection_rate           |
| 98  | trf_tcp_udp_ratio            | tcp_udp_ratio             |
| 99  | trf_avg_packet_size          | avg_packet_size           |
| 100 | trf_port_entropy             | port_entropy              |
| 101 | trf_flow_duration_std        | flow_duration_std         |
| 102 | trf_src_ip_entropy           | src_ip_entropy            |
| 103 | trf_dst_ip_concentration     | dst_ip_concentration      |
| 104 | trf_protocol_variety         | protocol_variety          |
| 105 | trf_temporal_consistency     | temporal_consistency      |

### 3.4 — Internal anomaly features (cols 106–115)
Proto: network_features.internal_anomaly (InternalFeatures)

| Col | Name                         | Proto field                      |
|-----|------------------------------|----------------------------------|
| 106 | int_connection_rate          | internal_connection_rate         |
| 107 | int_service_port_consistency | service_port_consistency         |
| 108 | int_protocol_regularity      | protocol_regularity              |
| 109 | int_packet_size_consistency  | packet_size_consistency          |
| 110 | int_connection_duration_std  | connection_duration_std          |
| 111 | int_lateral_movement_score   | lateral_movement_score           |
| 112 | int_service_discovery        | service_discovery_patterns       |
| 113 | int_data_exfiltration        | data_exfiltration_indicators     |
| 114 | int_temporal_anomaly         | temporal_anomaly_score           |
| 115 | int_access_pattern_entropy   | access_pattern_entropy           |

---

## Section 4 — ML Model Decisions (cols 116–125, 10 total)

Which model fired, its prediction label, and its confidence score.
Source: TricapaMLAnalysis sub-messages in NetworkSecurityEvent.ml_analysis.

| Col | Name                          | Type   | Source                                        |
|-----|-------------------------------|--------|-----------------------------------------------|
| 116 | level1_prediction             | string | level1_general_detection.prediction_class     |
| 117 | level1_confidence             | float  | level1_general_detection.confidence_score     |
| 118 | level2_ddos_prediction        | string | level2_specialized_predictions[0].prediction_class  |
| 119 | level2_ddos_confidence        | float  | level2_specialized_predictions[0].confidence_score  |
| 120 | level2_rsw_prediction         | string | level2_specialized_predictions[1].prediction_class  |
| 121 | level2_rsw_confidence         | float  | level2_specialized_predictions[1].confidence_score  |
| 122 | level3_traffic_prediction     | string | level3_specialized_predictions[0].prediction_class  |
| 123 | level3_traffic_confidence     | float  | level3_specialized_predictions[0].confidence_score  |
| 124 | level3_internal_prediction    | string | level3_specialized_predictions[1].prediction_class  |
| 125 | level3_internal_confidence    | float  | level3_specialized_predictions[1].confidence_score  |

NOTE: level2/level3 repeated fields are indexed by position, not by model_name.
If a detector did not fire, its slot contains empty string and 0.0.
CsvEventLoader must NOT assume index 0 = DDoS; it should validate model_name
from the ModelPrediction message. A v1.1 schema may replace positional indexing
with named columns once the detector activation order is stabilised.

---

## Section 5 — HMAC Integrity (col 126, 1 total)

| Col | Name  | Type   | Notes                                               |
|-----|-------|--------|-----------------------------------------------------|
| 126 | hmac  | string | HMAC-SHA256 over cols 0–125 (the complete row string before appending this field). 64-char lowercase hex. Key retrieved from etcd /secrets/ml-detector at startup. |

HMAC computation:
row_content = join(cols[0..125], ",")
hmac        = HMAC-SHA256(key=hmac_key_bytes, data=row_content).hex()

Verification (CsvEventLoader):
Recompute HMAC over cols[0..125], compare with col[126].
Rows with mismatched HMAC must be quarantined, not silently dropped.

---

## Summary

| Section | Cols     | Count | Producer       |
|---------|----------|-------|----------------|
| 1 Metadata             | 0–13    | 14    | ml-detector    |
| 2 Raw NetworkFeatures  | 14–75   | 62    | sniffer        |
| 3 Embedded detectors   | 76–115  | 40    | ml-detector    |
| 4 ML decisions         | 116–125 | 10    | ml-detector    |
| 5 HMAC                 | 126     | 1     | ml-detector    |
| **Total**              |         | **127** |              |

---

## Changelog

| Version | Date       | Author                              | Change                    |
|---------|------------|-------------------------------------|---------------------------|
| 1.0     | 2026-02-21 | Alonso Isidoro Roman + Claude (Anthropic) | Initial schema definition |