# ml-training-scripts/ddos_detection/DDOSFeatures.py
DDOS_FEATURES = [
    # KERNEL SPACE (captura directa)
    "syn_ack_ratio",                 # Ratio SYN vs ACK packets
    "packet_symmetry",               # Inbound vs outbound ratio
    "source_ip_dispersion",          # Unique source IPs per second
    "protocol_anomaly_score",        # Unusual protocol mix
    "packet_size_entropy",           # Entropy of packet sizes

    # USER SPACE (análisis complejo)
    "traffic_amplification_factor",  # Request/response size ratio
    "flow_completion_rate",          # Percentage of completed flows
    "geographical_concentration",    # Geo-IP concentration
    "traffic_escalation_rate",       # Traffic increase over time
    "resource_saturation_score"      # System load correlation
]