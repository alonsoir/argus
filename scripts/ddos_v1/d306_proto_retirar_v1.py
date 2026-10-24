#!/usr/bin/env python3
# DAY306 — DEBT-DDOS-V1-RETIRE-001, commit 2: los siete campos de la v1 pasan a 'reserved' en el proto y salen del
# sniffer, del CSV del ml-detector, de los tests y de las herramientas sinteticas. [DDOS-V1-RETIRE-D306]
#
# Uso (Mac, raiz del repo, DESPUES del commit 1):
#   python3 scripts/ddos_v1/d306_proto_retirar_v1.py --check    # valida TODO, no escribe nada
#   python3 scripts/ddos_v1/d306_proto_retirar_v1.py --apply    # valida TODO y, solo si todo casa, escribe
#
# Mismas reglas que el commit 1: sha256 PRE/POST por fichero, anclas unicas, bloques borrados por sha256, nada se
# escribe si algo no casa. Los .pb.cc/.pb.h/_pb2.py se regeneran despues con 'make proto' (no los toca este script).
# El residuo sniffer/src/userspace/ml_defender_features.cpp.bak.day79 (copia con la v1) se retira con 'git rm'.
import hashlib
import os
import sys

MARK = "[DDOS-V1-RETIRE-D306]"


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def dl(*lines):
    """Borra lineas completas; cada una debe casar exactamente una vez."""
    return [("rep", ln, "") for ln in lines]


E = {}

E["protobuf/network_security.proto"] = [
    ("rep",
     "// 🛡️ LEVEL 2 - DDoS Detection Features (10 features)\n"
     "message DDoSFeatures {\n"
     "    float syn_ack_ratio = 1;\n"
     "    float packet_symmetry = 2;  // FUERA DEL VECTOR DAY286: la captura no ve el trafico de vuelta\n"
     "    float source_ip_dispersion = 3;  // FUERA DEL VECTOR DAY286: hasta pcap multi-origen (H1)\n"
     "    float protocol_anomaly_score = 4;  // FUERA DEL VECTOR DAY286: ver 12\n"
     "    float packet_size_entropy = 5;\n"
     "    float traffic_amplification_factor = 6;  // FUERA DEL VECTOR DAY286: la captura no ve el trafico de vuelta\n"
     "    float flow_completion_rate = 7;\n"
     "    float geographical_concentration = 8;\n"
     "    float traffic_escalation_rate = 9;  // FUERA DEL VECTOR DAY286: ver 14\n"
     "    float resource_saturation_score = 10;  // FUERA DEL VECTOR DAY286: ver 15\n",
     "// 🛡️ Rasgos DDoS del contrato v2 (cabeza ddos_v2; calculados una vez en el sniffer)\n"
     "message DDoSFeatures {\n"
     "    // " + MARK + " campos de la cabeza DDoS v1, retirada: numeros y nombres reservados, NUNCA reutilizarlos.\n"
     "    // Los mensajes antiguos que los traigan se siguen leyendo (llegan como campos desconocidos).\n"
     "    reserved 2, 3, 4, 6, 8, 9, 10;\n"
     "    reserved \"packet_symmetry\", \"source_ip_dispersion\", \"protocol_anomaly_score\",\n"
     "             \"traffic_amplification_factor\", \"geographical_concentration\",\n"
     "             \"traffic_escalation_rate\", \"resource_saturation_score\";\n"
     "    float syn_ack_ratio = 1;\n"
     "    float packet_size_entropy = 5;\n"
     "    float flow_completion_rate = 7;\n"),
    ("rep", "        RANDOM_FOREST_DDOS = 6;            // RF Binary DDoS detector (8 features, 98.61% acc)\n",
     "        RANDOM_FOREST_DDOS = 6;            // cabeza ddos_v2 (bosque de la etapa 2) " + MARK + "\n"),
]

E["sniffer/src/userspace/ml_defender_features.cpp"] = [
    ("rep", "// DDOS FEATURES (10 features)\n", "// DDOS FEATURES — contrato v2 (cabeza ddos_v2) " + MARK + "\n"),
] + dl(
    "    ddos->set_packet_symmetry(extract_ddos_packet_symmetry(flow));\n",
    "    ddos->set_source_ip_dispersion(extract_ddos_source_ip_dispersion(flow));\n",
    "    ddos->set_protocol_anomaly_score(extract_ddos_protocol_anomaly_score(flow));\n",
    "    ddos->set_traffic_amplification_factor(extract_ddos_traffic_amplification_factor(flow));\n",
    "    ddos->set_geographical_concentration(extract_ddos_geographical_concentration(flow));\n",
    "    ddos->set_traffic_escalation_rate(extract_ddos_traffic_escalation_rate(flow));\n",
    "    ddos->set_resource_saturation_score(extract_ddos_resource_saturation_score(flow));\n",
) + [
    ("cut", "float MLDefenderExtractor::extract_ddos_packet_symmetry(",
     "float MLDefenderExtractor::extract_ddos_packet_size_entropy(", "", None),
    ("cut", "float MLDefenderExtractor::extract_ddos_traffic_amplification_factor(",
     "float MLDefenderExtractor::extract_ddos_flow_completion_rate(", "", None),
    ("cut", "float MLDefenderExtractor::extract_ddos_geographical_concentration(",
     "// ============================================================================\n// RANSOMWARE FEATURES (10 features)\n",
     "", None),
]

E["sniffer/include/ml_defender_features.hpp"] = [
    ("rep", "    // DDOS FEATURE EXTRACTORS (10 features)\n",
     "    // DDOS FEATURE EXTRACTORS — contrato v2 " + MARK + "\n"),
] + dl(
    "    float extract_ddos_packet_symmetry(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_source_ip_dispersion(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_protocol_anomaly_score(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_traffic_amplification_factor(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_geographical_concentration(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_traffic_escalation_rate(const FlowStatistics& flow) const;\n",
    "    float extract_ddos_resource_saturation_score(const FlowStatistics& flow) const;\n",
)

E["sniffer/src/userspace/ring_consumer.cpp"] = dl(
    "    ddos->set_packet_symmetry(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_source_ip_dispersion(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_protocol_anomaly_score(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_traffic_amplification_factor(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_geographical_concentration(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_traffic_escalation_rate(MISSING_FEATURE_SENTINEL);\n",
    "    ddos->set_resource_saturation_score(MISSING_FEATURE_SENTINEL);\n",
)

E["sniffer/tests/test_ring_consumer_protobuf.cpp"] = [
    ("rep",
     "    EXPECT_GE(ddos.syn_ack_ratio(), 0.0f) << \"SYN/ACK ratio populated\";\n"
     "    EXPECT_GE(ddos.packet_symmetry(), 0.0f) << \"Packet symmetry populated\";\n"
     "    EXPECT_GE(ddos.packet_size_entropy(), 0.0f) << \"Packet size entropy populated\";\n"
     "    EXPECT_GE(ddos.traffic_amplification_factor(), 0.0f) << \"Amplification factor populated\";\n",
     "    // " + MARK + " rasgos de flujo del contrato v2 que rellena el extractor\n"
     "    EXPECT_GE(ddos.syn_ack_ratio(), 0.0f) << \"SYN/ACK ratio populated\";\n"
     "    EXPECT_GE(ddos.packet_size_entropy(), 0.0f) << \"Packet size entropy populated\";\n"
     "    EXPECT_GT(ddos.flow_packet_count(), 0.0f) << \"Flow packet count populated\";\n"
     "    EXPECT_GT(ddos.mean_packet_size(), 0.0f) << \"Mean packet size populated\";\n"),
    ("rep", "              << \"symmetry=\" << ddos.packet_symmetry() << \" \"\n",
     "              << \"pkts=\" << ddos.flow_packet_count() << \" \"\n"),
    ("rep",
     "    // Packet symmetry should reflect 10:5 ratio\n"
     "    EXPECT_GT(ddos.packet_symmetry(), 0.0f) << \"Asymmetry detected\";\n"
     "    EXPECT_LT(ddos.packet_symmetry(), 1.0f) << \"Not completely one-directional\";\n"
     "\n"
     "    // Amplification factor (backward/forward bytes)\n"
     "    EXPECT_GT(ddos.traffic_amplification_factor(), 0.0f) << \"Amplification calculated\";\n"
     "\n"
     "    std::cout << \"✅ Bidirectional: symmetry=\" << ddos.packet_symmetry()\n"
     "              << \" amplification=\" << ddos.traffic_amplification_factor() << \"\\n\";\n",
     "    // " + MARK + " symmetry y amplification (v1) retirados: el 10:5 se comprueba en los campos de flujo\n"
     "    const auto& nfb = proto_event.network_features();\n"
     "    EXPECT_EQ(nfb.total_forward_packets(), 10u) << \"Forward packets in the event\";\n"
     "    EXPECT_EQ(nfb.total_backward_packets(), 5u) << \"Backward packets in the event\";\n"
     "    EXPECT_FLOAT_EQ(ddos.flow_packet_count(), 15.0f) << \"v2 flow_packet_count = fwd + bwd\";\n"
     "\n"
     "    std::cout << \"✅ Bidirectional: fwd=\" << nfb.total_forward_packets()\n"
     "              << \" bwd=\" << nfb.total_backward_packets()\n"
     "              << \" flow_packet_count=\" << ddos.flow_packet_count() << \"\\n\";\n"),
]

E["sniffer/tests/test_proto3_embedded_serialization.cpp"] = [
    ("rep",
     "    ddos_emb->set_source_ip_dispersion(0.5f);\n"
     "    ddos_emb->set_geographical_concentration(0.5f);\n"
     "    ddos_emb->set_flow_completion_rate(0.5f);\n",
     "    ddos_emb->set_mean_packet_size(0.5f);  // " + MARK + " campos v2 (los de la v1 estan reservados)\n"
     "    ddos_emb->set_victim_rate_ratio(0.5f);\n"
     "    ddos_emb->set_flow_completion_rate(0.5f);\n"),
    ("rep",
     "    EXPECT_FLOAT_EQ(nf.ddos_embedded().source_ip_dispersion(), 0.5f);\n"
     "    EXPECT_FLOAT_EQ(nf.ddos_embedded().geographical_concentration(), 0.5f);\n",
     "    EXPECT_FLOAT_EQ(nf.ddos_embedded().mean_packet_size(), 0.5f);\n"
     "    EXPECT_FLOAT_EQ(nf.ddos_embedded().victim_rate_ratio(), 0.5f);\n"),
    ("rep",
     "    EXPECT_GE(nf.ddos_embedded().source_ip_dispersion(), 0.0f);\n"
     "    EXPECT_LE(nf.ddos_embedded().source_ip_dispersion(), 1.0f);\n",
     "    EXPECT_GE(nf.ddos_embedded().victim_rate_ratio(), 0.0f);\n"
     "    EXPECT_LE(nf.ddos_embedded().victim_rate_ratio(), 1.0f);\n"),
    ("rep",
     "    ddos->set_packet_symmetry(0.33f);\n"
     "    ddos->set_source_ip_dispersion(0.5f);\n"
     "    ddos->set_flow_completion_rate(1.0f);\n",
     "    ddos->set_mean_packet_size(512.0f);  // " + MARK + "\n"
     "    ddos->set_flow_completion_rate(1.0f);\n"),
]

E["ml-detector/src/csv_event_writer.cpp"] = [
    ("rep",
     "        sep() << fmt_float(d.packet_symmetry());            // 77\n"
     "        sep() << fmt_float(d.source_ip_dispersion());       // 78\n"
     "        sep() << fmt_float(d.protocol_anomaly_score());     // 79\n",
     "        // " + MARK + " 77, 78, 79, 81, 83, 84 y 85 eran rasgos de la v1 (reservados en el proto): se quedan\n"
     "        // vacios para no mover el resto de columnas hasta la rama del RAG Logger.\n"
     "        sep();                                              // 77 (v1 retirada)\n"
     "        sep();                                              // 78 (v1 retirada)\n"
     "        sep();                                              // 79 (v1 retirada)\n"),
    ("rep", "        sep() << fmt_float(d.traffic_amplification_factor()); // 81\n",
     "        sep();                                              // 81 (v1 retirada)\n"),
    ("rep",
     "        sep() << fmt_float(d.geographical_concentration()); // 83\n"
     "        sep() << fmt_float(d.traffic_escalation_rate());    // 84\n"
     "        sep() << fmt_float(d.resource_saturation_score());  // 85\n",
     "        sep();                                              // 83 (v1 retirada)\n"
     "        sep();                                              // 84 (v1 retirada)\n"
     "        sep();                                              // 85 (v1 retirada)\n"),
]

E["ml-detector/tests/integration/test_csv_event_writer.cpp"] = dl(
    "        ddos->set_packet_symmetry(0.8f);\n",
    "        ddos->set_source_ip_dispersion(0.9f);\n",
    "        ddos->set_protocol_anomaly_score(0.2f);\n",
    "        ddos->set_traffic_amplification_factor(1.2f);\n",
    "        ddos->set_geographical_concentration(0.3f);\n",
    "        ddos->set_traffic_escalation_rate(0.4f);\n",
    "        ddos->set_resource_saturation_score(0.6f);\n",
)

E["ml-detector/tests/integration/test_csv_feature_extraction.cpp"] = [
    ("rep",
     "    d->set_syn_ack_ratio(0.11f);   d->set_packet_symmetry(0.82f);\n"
     "    d->set_source_ip_dispersion(0.91f); d->set_protocol_anomaly_score(0.22f);\n"
     "    d->set_packet_size_entropy(0.51f);  d->set_traffic_amplification_factor(1.3f);\n"
     "    d->set_flow_completion_rate(0.96f); d->set_geographical_concentration(0.31f);\n"
     "    d->set_traffic_escalation_rate(0.41f); d->set_resource_saturation_score(0.61f);\n",
     "    d->set_syn_ack_ratio(0.11f);  // " + MARK + " solo los rasgos v2 que el CSV aun escribe\n"
     "    d->set_packet_size_entropy(0.51f);\n"
     "    d->set_flow_completion_rate(0.96f);\n"),
    ("rep",
     "        if (cols[c] != \"0\" && !cols[c].empty()) ++populated;\n"
     "    }\n"
     "    EXPECT_EQ(populated, ml_defender::CSV_S3_EMBEDDED_COUNT)\n"
     "        << \"All S3 columns should be non-zero for a full event\";\n",
     "        if (cols[c] != \"0\" && !cols[c].empty()) ++populated;\n"
     "    }\n"
     "    // " + MARK + " las 7 columnas de la v1 (77-79, 81, 83-85) salen vacias\n"
     "    constexpr size_t kColumnasV1Retiradas = 7;\n"
     "    EXPECT_EQ(populated, ml_defender::CSV_S3_EMBEDDED_COUNT - kColumnasV1Retiradas)\n"
     "        << \"All S3 columns except the 7 retired v1 ones should be non-zero for a full event\";\n"),
    ("rep",
     "    (void)d->syn_ack_ratio();           (void)d->packet_symmetry();\n"
     "    (void)d->source_ip_dispersion();    (void)d->protocol_anomaly_score();\n"
     "    (void)d->packet_size_entropy();     (void)d->traffic_amplification_factor();\n"
     "    (void)d->flow_completion_rate();    (void)d->geographical_concentration();\n"
     "    (void)d->traffic_escalation_rate(); (void)d->resource_saturation_score();\n",
     "    (void)d->syn_ack_ratio();           (void)d->packet_size_entropy();  // " + MARK + "\n"
     "    (void)d->flow_completion_rate();    (void)d->mean_packet_size();\n"
     "    (void)d->reflection_signature();    (void)d->flow_packet_count();\n"
     "    (void)d->victim_rate_ratio();       (void)d->victim_pps();\n"),
]

E["ml-detector/tests/unit/test_rag_logger_artifact_save.cpp"] = [
    ("rep",
     "    ddos_emb->set_source_ip_dispersion(0.5f);\n"
     "    ddos_emb->set_geographical_concentration(0.5f);\n",
     "    ddos_emb->set_mean_packet_size(0.5f);  // " + MARK + " campo v2 (los de la v1 estan reservados)\n"),
    ("rep",
     "    ddos->set_packet_symmetry(0.33f);\n"
     "    ddos->set_source_ip_dispersion(0.5f);   // Phase 1 sentinel\n",
     "    ddos->set_mean_packet_size(512.0f);  // " + MARK + "\n"),
]

E["tools/generate_synthetic_events.cpp"] = [
    ("rep", "    ddos->set_packet_symmetry(feat.ddos[1]);\n",
     "    // " + MARK + " feat.ddos[1,2,3,5,7,8,9] eran rasgos de la v1 (reservados en el proto): no se escriben\n"),
] + dl(
    "    ddos->set_source_ip_dispersion(feat.ddos[2]);\n",
    "    ddos->set_protocol_anomaly_score(feat.ddos[3]);\n",
    "    ddos->set_traffic_amplification_factor(feat.ddos[5]);\n",
    "    ddos->set_geographical_concentration(feat.ddos[7]);\n",
    "    ddos->set_traffic_escalation_rate(feat.ddos[8]);\n",
    "    ddos->set_resource_saturation_score(feat.ddos[9]);\n",
)

E["tools/synthetic_sniffer_injector.cpp"] = [
    ("rep", "        // DDoS Embedded Features (10 features)\n",
     "        // DDoS Embedded Features: solo los rasgos del contrato v2; los de la v1 estan reservados " + MARK + "\n"),
] + dl(
    "            ddos->set_packet_symmetry(rand_float(0.0, 0.05));\n",
    "            ddos->set_source_ip_dispersion(rand_float(0.8, 1.0));\n",
    "            ddos->set_protocol_anomaly_score(rand_float(0.7, 1.0));\n",
    "            ddos->set_traffic_amplification_factor(rand_float(50, 100));\n",
    "            ddos->set_geographical_concentration(rand_float(0.7, 1.0));\n",
    "            ddos->set_traffic_escalation_rate(rand_float(7.0, 10.0));\n",
    "            ddos->set_resource_saturation_score(rand_float(0.8, 1.0));\n",
    "            ddos->set_packet_symmetry(rand_float(0.0, 1.0));\n",
    "            ddos->set_source_ip_dispersion(rand_float(0.0, 1.0));\n",
    "            ddos->set_protocol_anomaly_score(rand_float(0.0, 1.0));\n",
    "            ddos->set_traffic_amplification_factor(rand_float(1.0, 100.0));\n",
    "            ddos->set_geographical_concentration(rand_float(0.0, 1.0));\n",
    "            ddos->set_traffic_escalation_rate(rand_float(0.0, 10.0));\n",
    "            ddos->set_resource_saturation_score(rand_float(0.0, 1.0));\n",
)

A_BORRAR = [
    "sniffer/src/userspace/ml_defender_features.cpp.bak.day79",
]


# sha256 de cada fichero tras el commit 1 (PRE) y tras aplicar (POST); y de cada bloque borrado con "cut".
PRE = {
    "ml-detector/src/csv_event_writer.cpp": "d721c2bdfe143609ccca33a9a8344ee1ba3d14c2d145d9181c77c6907dd0e8d5",
    "ml-detector/tests/integration/test_csv_event_writer.cpp": "d38bf99e32a818d9509b5b775207f5d15b6f236d1bdefddbd3e49a57577b4a12",
    "ml-detector/tests/integration/test_csv_feature_extraction.cpp": "805699ef8b5df76ebff4eb638ed6f7c707fc83be344cba6d3bac9e33a09a36a6",
    "ml-detector/tests/unit/test_rag_logger_artifact_save.cpp": "d10f7626e24d4cd48e97f06af81ae16f12e74e0a54aecb93dd8f8f2be78939b8",
    "protobuf/network_security.proto": "19d08048f7d4fa2f87c0f581d1ea29a17947f848a00cdab4a58ea01ddb1a58fd",
    "sniffer/include/ml_defender_features.hpp": "01ad53fa2d9fecc5b6c8d61700fa598e42a00b7ec0c2a486118c79b2b83e9124",
    "sniffer/src/userspace/ml_defender_features.cpp": "34ef6504c6c4400ee7fe06831a8ac3b282eb7504702040fbfefd0faf085b5b52",
    "sniffer/src/userspace/ring_consumer.cpp": "c7e544f1a7b1f19377e39c8f8fcccb07b5d8e3b398155683dc4b2ce3c92f9122",
    "sniffer/tests/test_proto3_embedded_serialization.cpp": "4f5468c0e9d1c428adbb35b6229eb377eb115ae17fa061c41ce5324b75fee2f0",
    "sniffer/tests/test_ring_consumer_protobuf.cpp": "631574e579c88f72fc02c098ea30419c95e9e0660a096c90fc9742c4c158d63c",
    "tools/generate_synthetic_events.cpp": "9b30bdb90a90889e99c0a995b5673d4321a40ce4a79d1d3d2d0242d0c08bf1ca",
    "tools/synthetic_sniffer_injector.cpp": "295b388e8e61fe513f7796d7273f4b9ba0797acc106b5ab38558aba26a39a6b2"
}
POST = {
    "ml-detector/src/csv_event_writer.cpp": "398b637af2054666616f474e8f94c2180bf11b86366ad0edd41acb1ca18c9c46",
    "ml-detector/tests/integration/test_csv_event_writer.cpp": "c6907a6e9637b85d15e1baefc26b2823e06be3a6b4b5e0d0dca628e5041ed813",
    "ml-detector/tests/integration/test_csv_feature_extraction.cpp": "0649c28ac5a22ae02e352cf4d9f50756333d8d3a1db2351edfc8e5e8a0e9a329",
    "ml-detector/tests/unit/test_rag_logger_artifact_save.cpp": "f9a4ec037e03ae02a602239b9d008ac3390a635f50d229ca3b8e85aef92b91f6",
    "protobuf/network_security.proto": "3c7986c44d450c1d5d83eda259fc11ceec9261f92d1c363a957e9314f63f3d76",
    "sniffer/include/ml_defender_features.hpp": "4a191ac076c46ba98066f817c625f93f1a15991030583b946acbc51c1eb18ee8",
    "sniffer/src/userspace/ml_defender_features.cpp": "0fcc3c0856ad3773e53d5b566160c6b122005ac321892d4a7ac12544ac447b77",
    "sniffer/src/userspace/ring_consumer.cpp": "a8c2143e2e6749bf69a9aa5ae2cb027c0dabfdf525301c5377a744c77ec7b109",
    "sniffer/tests/test_proto3_embedded_serialization.cpp": "d0d339fb0cf74b5c02e5034fc92f47ff79b90bd8e7595acdec4a657155dda69b",
    "sniffer/tests/test_ring_consumer_protobuf.cpp": "0e8a2ba978e342a80bf32b05f736d14c7ce43d4650e435b1635457ecc9025f80",
    "tools/generate_synthetic_events.cpp": "96244958656cac9eb6a0023b91bad29c337d160655e231e0e98f36aeab54a01f",
    "tools/synthetic_sniffer_injector.cpp": "06090bec4be6ec93d4bcddde1875e615fc9c0dd6b88c411b6747719c959e817e"
}
CUTS = {
    "sniffer/src/userspace/ml_defender_features.cpp#10": "3b03599bd6cef7ba28793ff9876f6acfbfc86c63dc45f4ff7957757cbe0ce6f2",
    "sniffer/src/userspace/ml_defender_features.cpp#8": "650f67bdbfbe58d4ce6671951fc718770c82e64c19eacae9cd5fc01b5f633c75",
    "sniffer/src/userspace/ml_defender_features.cpp#9": "1bfb9cadca74bd1200e41e8d2442074db5a9c8b50d68c5293b49ace15be0a7d6"
}


def aplicar(path, txt):
    """Devuelve el texto nuevo o lanza ValueError con el motivo. No escribe."""
    for i, ed in enumerate(E[path]):
        if ed[0] == "rep":
            _, old, new = ed
            n = txt.count(old)
            if n != 1:
                raise ValueError(f"{path}: edicion {i}: el ancla casa {n} veces (debe ser 1): {old[:70]!r}")
            txt = txt.replace(old, new)
        else:
            _, a, b, new, _ = ed
            na, nb = txt.count(a), txt.count(b)
            if na != 1 or nb != 1:
                raise ValueError(f"{path}: edicion {i}: anclas casan {na}/{nb} veces (deben ser 1/1): {a[:60]!r}")
            ia, ib = txt.index(a), txt.index(b)
            if ib <= ia:
                raise ValueError(f"{path}: edicion {i}: el ancla final va antes que la inicial")
            bloque = txt[ia:ib]
            key = f"{path}#{i}"
            if CUTS and sha(bloque) != CUTS.get(key):
                raise ValueError(f"{path}: edicion {i}: sha256 del bloque a borrar no casa ({sha(bloque)[:12]})")
            if not CUTS:
                CUTS_NUEVOS[key] = sha(bloque)
            txt = txt[:ia] + new + txt[ib:]
    return txt


CUTS_NUEVOS = {}


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo not in ("--check", "--apply", "--build"):
        print(__doc__ or "", "uso: --check | --apply")
        return 2
    raiz = os.getcwd()
    if modo == "--build":
        raiz = sys.argv[2]
    errores, nuevos, ya = [], {}, []
    for path in E:
        full = os.path.join(raiz, path)
        if not os.path.isfile(full):
            errores.append(f"{path}: no existe")
            continue
        txt = open(full, encoding="utf-8").read()
        h = sha(txt)
        if modo != "--build" and h == POST.get(path):
            ya.append(path)
            continue
        if modo != "--build" and h != PRE.get(path):
            errores.append(f"{path}: sha256 {h[:12]} no es el de partida tras el commit 1 ({PRE.get(path, '?')[:12]}) ni el aplicado")
            continue
        try:
            nuevo = aplicar(path, txt)
        except ValueError as e:
            errores.append(str(e))
            continue
        if modo != "--build" and sha(nuevo) != POST[path]:
            errores.append(f"{path}: el resultado no da el sha256 esperado")
            continue
        nuevos[path] = (h, nuevo)
    if modo != "--build":
        for p in A_BORRAR:
            if not os.path.isfile(os.path.join(raiz, p)):
                print(f"[INFO] {p} ya no existe (ya retirado con git rm)")
    if errores:
        print("[PARAR] no se escribe nada:")
        for e in errores:
            print("   -", e)
        return 1
    if ya and not nuevos:
        print(f"[YA-APLICADO] los {len(ya)} ficheros ya estan en el estado POST; nada que hacer")
        return 0
    if ya:
        print(f"[PARAR] estado mixto: {len(ya)} ficheros aplicados y {len(nuevos)} sin aplicar; no se escribe nada")
        return 1
    if modo == "--build":
        for p, (h, n) in nuevos.items():
            PRE_B[p], POST_B[p] = h, sha(n)
            with open(os.path.join(raiz, p), "w", encoding="utf-8") as f:
                f.write(n)
        return 0
    print(f"[OK] {len(nuevos)} ficheros validados (sha256 PRE, anclas unicas, bloques borrados por sha256)")
    if modo == "--check":
        print("[CHECK] no se ha escrito nada. Para aplicar: --apply")
        return 0
    for p, (_, n) in nuevos.items():
        with open(os.path.join(raiz, p), "w", encoding="utf-8") as f:
            f.write(n)
        print(f"   escrito {p}")
    print("[APPLY] hecho. Retira ahora con git rm:", " ".join(A_BORRAR))
    return 0


PRE_B, POST_B = {}, {}

if __name__ == "__main__":
    rc = main()
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        import json
        print(json.dumps({"PRE": PRE_B, "POST": POST_B, "CUTS": CUTS_NUEVOS}))
    sys.exit(rc)
