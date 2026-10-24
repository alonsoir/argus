#!/usr/bin/env python3
# DAY306 — DEBT-DDOS-V1-RETIRE-001, commit 1: retirar la cabeza DDoS v1 del ml-detector. [DDOS-V1-RETIRE-D306]
#
# Uso (Mac, raiz del repo):
#   python3 scripts/ddos_v1/d306_ml_retirar_v1.py --check    # valida TODO, no escribe nada
#   python3 scripts/ddos_v1/d306_ml_retirar_v1.py --apply    # valida TODO y, solo si todo casa, escribe
#
# Reglas: valida antes de escribir nada. Cada fichero debe tener EXACTAMENTE el sha256 medido en HEAD 9dcf014e
# (estado PRE) o el del resultado (estado POST, ya aplicado). Cada ancla casa una sola vez. Cada bloque que se
# borra entero se comprueba por sha256. Si un solo fichero esta en un estado distinto, no se escribe ninguno.
# Este parcheador NO borra ficheros: los tres ficheros de la v1 se retiran despues con 'git rm'.
# NO toca el proto ni el sniffer (commit 2).
import hashlib
import os
import sys

MARK = "[DDOS-V1-RETIRE-D306]"


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# Ediciones. ("rep", viejo, nuevo): viejo casa 1 vez. ("cut", ancla_ini, ancla_fin, nuevo, sha_bloque): se borra
# desde ancla_ini (incluida) hasta ancla_fin (excluida) y se pone 'nuevo'; el bloque borrado debe tener sha_bloque.
# ---------------------------------------------------------------------------------------------------------------
SEP = "        // " + "\u2501" * 67 + "\n"

E = {}

E["ml-detector/include/zmq_handler.hpp"] = [
    ("rep", '#include "ml_defender/ddos_detector.hpp"\n', ""),
    ("rep", "        uint64_t detections_ddos = 0;        // [SUMMARY-D285]\n", ""),
    ("rep", "        std::shared_ptr<ml_defender::DDoSDetector> ddos_detector,\n", ""),
    ("rep", "    std::shared_ptr<ml_defender::DDoSDetector> ddos_detector_;\n", ""),
]

E["ml-detector/src/zmq_handler.cpp"] = [
    ("rep", "    std::shared_ptr<ml_defender::DDoSDetector> ddos_detector,\n", ""),
    ("rep", "    , ddos_detector_(ddos_detector)\n", ""),
    ("rep",
     "    if (ddos_detector_) {\n"
     "        logger_->info(\"   Level 2: DDoS ({} trees, {} features)\",\n"
     "                     ddos_detector_->num_trees(), ddos_detector_->num_features());\n"
     "    }\n", ""),
    ("rep", "                const uint64_t d_ddos = summary_delta(s.detections_ddos, summary_prev.detections_ddos);\n", ""),
    ("rep",
     "                if (d_ddos + d_rw + d_int > 0) {\n"
     "                    logger_->warn(\"[DETECCIONES] ddos={} ransomware={} internal={} en los últimos {} s\",\n"
     "                                  d_ddos, d_rw, d_int, secs);\n",
     "                if (d_rw + d_int > 0) {  // " + MARK + " sin ddos v1; ddos_v2 tiene su resumen [DDOS-V2]\n"
     "                    logger_->warn(\"[DETECCIONES] ransomware={} internal={} en los últimos {} s\",\n"
     "                                  d_rw, d_int, secs);\n"),
    ("rep",
     "        bool ddos_v2_attack = false;\n",
     "        bool ddos_v2_attack = false;\n"
     "        int hs_v2_c = -1;      // " + MARK + " clase de ddos_v2 para [HEAD-SCORES]; -1 = no evaluada\n"
     "        double hs_v2_p = 0.0;  // " + MARK + " p1 de ddos_v2 para [HEAD-SCORES]\n"),
    ("rep",
     "            ddos_v2_score = r2.stage1 ? r2.p1 : 0.0;  // [DDOS-SHADOW-D293]\n",
     "            ddos_v2_score = r2.stage1 ? r2.p1 : 0.0;  // [DDOS-SHADOW-D293]\n"
     "            hs_v2_c = static_cast<int>(r2.clase);  // " + MARK + "\n"
     "            hs_v2_p = static_cast<double>(r2.p1);\n"),
    ("rep",
     "        int hs_ddos_c = -1, hs_ransom_c = -1, hs_traffic_c = -1, hs_internal_c = -1;\n"
     "        double hs_ddos_p = 0.0, hs_ransom_p = 0.0, hs_traffic_p = 0.0, hs_internal_p = 0.0;\n",
     "        int hs_ransom_c = -1, hs_traffic_c = -1, hs_internal_c = -1;  // " + MARK + " sin ddos v1\n"
     "        double hs_ransom_p = 0.0, hs_traffic_p = 0.0, hs_internal_p = 0.0;\n"),
    ("cut", "            // Level 2: DDoS\n", "            // Level 2: Ransomware\n", "", None),
    ("rep", "fast={:.4f}, ddos={}, ransom={}, traffic={}",
     "fast={:.4f}, ddos_v2={}, ransom={}, traffic={}"),
    ("rep", "                          hs_fmt(hs_ddos_c, hs_ddos_p), hs_fmt(hs_ransom_c, hs_ransom_p),\n",
     "                          hs_fmt(hs_v2_c, hs_v2_p), hs_fmt(hs_ransom_c, hs_ransom_p),\n"),
    ("rep", "            ddos_dataset_writer_->write(event, hs_ddos_c, hs_ddos_p);\n",
     "            ddos_dataset_writer_->write(event);  // " + MARK + " old_ddos_* = -1 (cabeza v1 retirada)\n"),
    ("rep", "    const bool d1 = ddos_detector_ && config_.ml.level2.ddos.enabled;\n", ""),
    ("rep", "    if (!l1 && !v2 && !(force_all_heads_ && (d1 || rw || tr || in))) {\n",
     "    if (!l1 && !v2 && !(force_all_heads_ && (rw || tr || in))) {  // " + MARK + "\n"),
    ("rep", "    } else if (!l1 && !force_all_heads_ && (d1 || rw || tr || in)) {\n",
     "    } else if (!l1 && !force_all_heads_ && (rw || tr || in)) {\n"),
    ("rep", "AVISO: ddos_v1/ransomware/traffic/internal solo corren",
     "AVISO: ransomware/traffic/internal solo corren"),
    ("rep",
     "    logger_->warn(\"[HEADS] ({}) level1={} ddos_v2={} ddos_v1={} ransomware={} traffic={} internal={} force_all_heads={}{}\",\n"
     "                  momento, s(l1), s(v2), s(d1), s(rw), s(tr), s(in), s(force_all_heads_), nota);\n",
     "    logger_->warn(\"[HEADS] ({}) level1={} ddos_v2={} ransomware={} traffic={} internal={} force_all_heads={}{}\",\n"
     "                  momento, s(l1), s(v2), s(rw), s(tr), s(in), s(force_all_heads_), nota);\n"),
]

E["ml-detector/src/main.cpp"] = [
    ("rep", '#include "ml_defender/ddos_detector.hpp"\n', ""),
    ("rep",
     "        std::cout << \"   Level 2 DDoS: \" << (config.ml.level2.ddos.enabled ? \"✅\" : \"❌\")\n"
     "                  << \" \" << config.ml.level2.ddos.name\n"
     "                  << \" (\" << config.ml.level2.ddos.features_count << \" features)\\n\";\n",
     "        std::cout << \"   DDoS v2: \" << (config.ml.ddos_v2.enabled ? \"✅\" : \"❌\")  // " + MARK + "\n"
     "                  << \" (k_ratio=\" << config.ml.ddos_v2.k_ratio << \")\\n\";\n"),
    ("cut", SEP + "        // ✨ LEVEL 2: DDoS Detector (C++20 Embedded)\n",
     SEP + "        // Level 2 Ransomware - Embedded C++20 Detector\n", "", None),
    ("rep",
     "        if (ddos_detector) {\n"
     "            log->info(\"     Level 2: DDoS (C++20 - {} trees)\", ddos_detector->num_trees());\n"
     "        }\n", ""),
    ("rep", "            ddos_detector,\n", ""),
]

E["ml-detector/include/config_loader.hpp"] = [
    ("rep", "            float level2_ddos{};\n", ""),
    ("rep", "            ModelConfig ddos;\n", ""),
]

OBS_THR = (
    "        // " + MARK + " la cabeza DDoS v1 se retiro: si el JSON aun trae su umbral, se avisa y se ignora\n"
    "        if (thresh.contains(\"level2_ddos\")) {\n"
    "            std::cerr << \"[CONFIG-OBSOLETO] ml.thresholds.level2_ddos: la cabeza DDoS v1 se retiro (DAY306); el \"\n"
    "                         \"campo se ignora. Quitelo del JSON. La cabeza DDoS vigente es ml.ddos_v2\\n\";\n"
    "        }\n")
OBS_L2 = (
    "        // " + MARK + " la cabeza DDoS v1 se retiro: si el JSON aun trae su bloque, se avisa y se ignora\n"
    "        if (l2.contains(\"ddos\")) {\n"
    "            std::cerr << \"[CONFIG-OBSOLETO] ml.level2.ddos: la cabeza DDoS v1 se retiro (DAY306); el bloque se \"\n"
    "                         \"ignora. Quitelo del JSON. La cabeza DDoS vigente es ml.ddos_v2\\n\";\n"
    "        }\n"
    "        \n")

E["ml-detector/src/config_loader.cpp"] = [
    ("rep",
     "        config.ml.thresholds.level2_ddos = get_required<float>(thresh, \"level2_ddos\", \"ml.thresholds\");\n",
     OBS_THR),
    ("cut", "        auto& l2ddos = l2[\"ddos\"];\n", "        auto& l2ransom = l2[\"ransomware\"];\n", OBS_L2, None),
    ("rep",
     "    std::cout << \"   Level 2 DDoS: \" << (config.ml.level2.ddos.enabled ? \"✅\" : \"❌\")\n"
     "              << \" \" << config.ml.level2.ddos.name << \" (\" << config.ml.level2.ddos.features_count << \" features)\\n\";\n",
     "    std::cout << \"   DDoS v2: \" << (config.ml.ddos_v2.enabled ? \"✅\" : \"❌\")  // " + MARK + "\n"
     "              << \" (k_ratio=\" << config.ml.ddos_v2.k_ratio << \")\\n\";\n"),
    ("rep", "        std::cout << \"  Level 2 DDoS: \" << config.ml.thresholds.level2_ddos << \"\\n\";\n", ""),
]

E["ml-detector/src/etcd_client.cpp"] = [
    ("rep",
     "    bool ddos_enabled = full_config[\"ml\"][\"level2\"][\"ddos\"].value(\"enabled\", false);\n",
     "    // " + MARK + " ml.level2.ddos (v1) se retiro. Sobre un JSON no constante, operator[] con una clave ausente\n"
     "    // crea un null y value() lanzaria: se lee ml.ddos_v2 solo si existe. Es informativo; el estado efectivo\n"
     "    // de cada cabeza lo da la linea [HEADS].\n"
     "    const auto& ml_cfg = full_config[\"ml\"];\n"
     "    const bool ddos_v2_enabled = ml_cfg.contains(\"ddos_v2\") && ml_cfg[\"ddos_v2\"].is_object() &&\n"
     "                                 ml_cfg[\"ddos_v2\"].contains(\"enabled\") &&\n"
     "                                 ml_cfg[\"ddos_v2\"][\"enabled\"].is_boolean() &&\n"
     "                                 ml_cfg[\"ddos_v2\"][\"enabled\"].get<bool>();\n"),
    ("rep",
     "    std::cout << \"   - Level 2 DDoS: \" << (ddos_enabled ? \"✅\" : \"❌\") << std::endl;\n",
     "    std::cout << \"   - DDoS v2: \" << (ddos_v2_enabled ? \"✅\" : \"❌\") << std::endl;\n"),
]

E["ml-detector/src/contract_validator.cpp"] = [
    ("cut", "    // Level 2 DDoS Features (10 fields required)\n", "    // Level 2 Ransomware Features (10 fields required)\n",
     "    // " + MARK + " ddos_embedded lo consume la cabeza ddos_v2 (contrato v2). El recuento de la v1\n"
     "    // (\"10 fields required\") se retiro: en proto3 un rasgo v2 que vale 0 no se lista y no es un fallo.\n"
     "    if (!nf.has_ddos_embedded()) {\n"
     "        logger->warn(\"  Missing: ddos_embedded (CRITICAL - la cabeza ddos_v2 lo necesita)\");\n"
     "    }\n"
     "    \n", None),
]

E["ml-detector/include/feature_extractor.hpp"] = [
    ("rep",
     "    /**\n"
     "     * @brief Extrae las 10 features del Level 2 DDoS Binary\n"
     "     * @param nf NetworkFeatures del evento\n"
     "     * @return vector<float>[10] para predicción DDoS binaria (accuracy 98.61%)\n"
     "     */\n"
     "    std::vector<float> extract_level2_ddos_features(const protobuf::NetworkFeatures& nf);\n", ""),
]

E["ml-detector/src/feature_extractor.cpp"] = [
    ("cut", "    // ============================================================================\n// LEVEL 2: DDoS Features (10 features)\n",
     "std::vector<float> FeatureExtractor::extract_level2_ransomware_features(\n", "", None),
]

E["ml-detector/src/csv_event_writer.cpp"] = [
    ("cut", "        // Level 2 — specialized predictions (positional: 0=DDoS, 1=Ransomware)\n",
     "        // Level 3 — specialized predictions (positional: 0=Traffic, 1=Internal)\n",
     "        // " + MARK + " Level 2 por tipo de modelo, no por posicion: ddos_v2 ocupa la posicion 0 y la v1 se\n"
     "        // retiro, asi que la posicion ya no dice que cabeza es. RANDOM_FOREST_DDOS = ddos_v2.\n"
     "        for (const auto& pr : ml.level2_specialized_predictions()) {\n"
     "            if (pr.model_type() == protobuf::ModelPrediction::RANDOM_FOREST_DDOS) {\n"
     "                l2d_pred = pr.prediction_class();\n"
     "                l2d_conf = pr.confidence_score();\n"
     "            } else if (pr.model_type() == protobuf::ModelPrediction::RANDOM_FOREST_RANSOMWARE) {\n"
     "                l2r_pred = pr.prediction_class();\n"
     "                l2r_conf = pr.confidence_score();\n"
     "            }\n"
     "        }\n"
     "\n", None),
]

E["ml-detector/include/ddos_dataset_writer.hpp"] = [
    ("rep",
     "    // old_class < 0 => la cabeza vieja no corrio en este evento: prob y clase = -1\n"
     "    void write(const protobuf::NetworkSecurityEvent& ev, int old_class, double old_prob) {\n",
     "    // " + MARK + " old_ddos_prob/old_ddos_class: la cabeza v1 se retiro; las columnas se conservan con -1\n"
     "    // (= no evaluada) para no romper el formato del dataset.\n"
     "    void write(const protobuf::NetworkSecurityEvent& ev) {\n"),
    ("rep", "            old_class < 0 ? -1.0 : old_prob, old_class < 0 ? -1 : old_class);\n",
     "            -1.0, -1);\n"),
]

E["ml-detector/CMakeLists.txt"] = [
    ("rep", "    ${CMAKE_CURRENT_SOURCE_DIR}/src/ddos_detector.cpp\n", ""),
    ("rep", "        src/ddos_detector.cpp\n", ""),
]

E["ml-detector/tests/CMakeLists.txt"] = [
    ("rep", "            ../src/ddos_detector.cpp\n", ""),
    ("rep", "(standalone + ctest, guardián contrato 9-feat)", "(standalone + ctest: traffic e internal)"),
]

E["ml-detector/tests/unit/test_detectors.cpp"] = [
    ("rep",
     "// Compile: g++ -std=c++20 -O3 test_detectors.cpp ddos_detector.cpp traffic_detector.cpp internal_detector.cpp -o test_detectors\n",
     "// Compile: g++ -std=c++20 -O3 test_detectors.cpp traffic_detector.cpp internal_detector.cpp -o test_detectors\n"
     "// " + MARK + " sin la cabeza DDoS v1 (retirada): quedan traffic e internal.\n"),
    ("rep", '#include "ml_defender/ddos_detector.hpp"\n', ""),
    ("cut", "// ============================================================================\n// TEST 1: DDOS DETECTOR\n",
     "// ============================================================================\n// TEST 2: TRAFFIC DETECTOR\n", "", None),
    ("cut", "// ============================================================================\n// TEST 4: BATCH PREDICTION\n",
     "// ============================================================================\n// MAIN\n", "", None),
    ("rep", "        test_ddos_detector();\n", ""),
    ("rep", "        test_batch_prediction();\n", ""),
]

E["ml-detector/config/ml_detector_config.json"] = [
    ("rep", '      "level2_ddos": 0.7,\n', ""),
    ("cut", '      "ddos": {\n        "_doc": "[HEADS-SWITCH-D305] DDoS v1', '      "ransomware": {\n', "", None),
    ("rep", "Ademas ddos_v1/ransomware/traffic/internal dejan", "Ademas ransomware/traffic/internal dejan"),
]

E["ml-detector/tests/integration/test_csv_event_writer.cpp"] = [
    ("rep", '        l2d->set_model_name("RANDOM_FOREST_DDOS");\n',
     '        l2d->set_model_name("RANDOM_FOREST_DDOS");\n'
     "        l2d->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_DDOS);  // " + MARK + " el CSV elige por tipo\n"),
    ("rep", '        l2r->set_model_name("RANDOM_FOREST_RANSOMWARE");\n',
     '        l2r->set_model_name("RANDOM_FOREST_RANSOMWARE");\n'
     "        l2r->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_RANSOMWARE);  // " + MARK + "\n"),
]

E["ml-detector/tests/integration/test_csv_feature_extraction.cpp"] = [
    ("rep", '    p2d->set_prediction_class("DDoS"); p2d->set_confidence_score(0.93);\n',
     '    p2d->set_prediction_class("DDoS"); p2d->set_confidence_score(0.93);\n'
     "    p2d->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_DDOS);  // " + MARK + " el CSV elige por tipo\n"),
    ("rep", '    p2r->set_prediction_class("BENIGN"); p2r->set_confidence_score(0.07);\n',
     '    p2r->set_prediction_class("BENIGN"); p2r->set_confidence_score(0.07);\n'
     "    p2r->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_RANSOMWARE);  // " + MARK + "\n"),
]

# Ficheros que se retiran con 'git rm' tras --apply (este parcheador solo comprueba que existen).
A_BORRAR = [
    "ml-detector/src/ddos_detector.cpp",
    "ml-detector/include/ml_defender/ddos_detector.hpp",
    "ml-detector/include/ml_defender/ddos_trees_inline.hpp",
]

# sha256 de cada fichero en HEAD 9dcf014e (PRE) y tras aplicar (POST); y de cada bloque borrado con "cut".
PRE = {
    "ml-detector/CMakeLists.txt": "efc3a77b542373528f17e140f2720d792626c30056dfe83ea35a8abdb44d595e",
    "ml-detector/config/ml_detector_config.json": "fff198eaa512fc24c6eee55778d893fa7063f0d91fc24a173f35e8bb35c96fa3",
    "ml-detector/include/config_loader.hpp": "08c61b750bcd074359b921b88e000e7c1e69e573ca7d158fd516f09def8ed631",
    "ml-detector/include/ddos_dataset_writer.hpp": "65ea4861f9311fe88fa64df6c185a269bbf96ca03585e661d4ec8d9514212165",
    "ml-detector/include/feature_extractor.hpp": "a7be6feb6c23f135cc9dcb65572cb13073cc3db620258e1d659fd68af123baef",
    "ml-detector/include/zmq_handler.hpp": "113b07892286ae23473fe1218121b7bbf80ed42f873971a5455f72bed0de9d0b",
    "ml-detector/src/config_loader.cpp": "b8139ad983eee6c8016c13c9a18e730d481b951d70174f2090647053812f1c8a",
    "ml-detector/src/contract_validator.cpp": "98050a136f3ad05297c56d91c2366d6588972a27b90c696c8c67fe70444753ad",
    "ml-detector/src/csv_event_writer.cpp": "bbbce95f88415bd43de76ff719e15072fc1afa3886986e86dba62bfc9523e336",
    "ml-detector/src/etcd_client.cpp": "4da65975dd352d9882fde41b79782fce81c6b42ecf0e6db85858709b8cc99694",
    "ml-detector/src/feature_extractor.cpp": "0bbcf037000c60415f948bc0fb76f794e347d43ed68f51675da9af25da9b95d2",
    "ml-detector/src/main.cpp": "70420d7eca571b2597c1e0b8371f935d200822509884280f339cc7cf59c87442",
    "ml-detector/src/zmq_handler.cpp": "4a9c47199daa77a6158f76e0f44eeaaeb9959a8d62b2741d7450a1c7d879a12d",
    "ml-detector/tests/CMakeLists.txt": "9017bcf25f2bb91d469efd9739d4b9bd5aa6539766844e589d3180cbaa18f2b0",
    "ml-detector/tests/integration/test_csv_event_writer.cpp": "914bc65bcbf8b2e7be0a53abe61efacb8696e392615463273155acae472ae66b",
    "ml-detector/tests/integration/test_csv_feature_extraction.cpp": "851c1731b995b83db4a1e9c86336f46206a7d15bfe88db6d5fdcb4dec9e7e2c5",
    "ml-detector/tests/unit/test_detectors.cpp": "ea9fd5fa4655b27993d105527cdb1035487cfb39d0332cb1d30a387179519118"
}
POST = {
    "ml-detector/CMakeLists.txt": "3e3388ae5f5a467d263ac5b00184ae8ff1e2a5503f08b61824a8282ff036a1bf",
    "ml-detector/config/ml_detector_config.json": "8aff3ae425590335fee37bdb86190c48b9b9cca304c9d58329628e94148aacf3",
    "ml-detector/include/config_loader.hpp": "18192a89584a11eb4426851681a1935a059bbef4b1d4ee3e3262cd6cac39f5f8",
    "ml-detector/include/ddos_dataset_writer.hpp": "c288352214dc2cbfbed8da07836d43a7adf0dd6facee4e8e3ff97aec68db1026",
    "ml-detector/include/feature_extractor.hpp": "5fb04fd3d1c62372c042613c07ca12794df62e79d77c65c077921f2fea536eb5",
    "ml-detector/include/zmq_handler.hpp": "a502e6dd1ca754c320d737f80223b69146077121f039a0342418df28eea51f94",
    "ml-detector/src/config_loader.cpp": "1cce716a2bd9ea66488dce37d8c27a6ded60e114eaaa03b9a25f7818cc5b7e31",
    "ml-detector/src/contract_validator.cpp": "a5f7b4aa677005e9f59990b0ba54a76d2c8f3e5f3d90c08465df14e49a83869d",
    "ml-detector/src/csv_event_writer.cpp": "d721c2bdfe143609ccca33a9a8344ee1ba3d14c2d145d9181c77c6907dd0e8d5",
    "ml-detector/src/etcd_client.cpp": "43e35aebd60f5fc62beea4ea40221a4ecb51a472ca62bd7900ca245c9300bdd7",
    "ml-detector/src/feature_extractor.cpp": "c3c41d8410dd98790fbc10e4b12f29bef443ff6d6a70ed82650deb123eaffce6",
    "ml-detector/src/main.cpp": "a431922020e7231ebc674591df16bdcfe93e7bb5f3dde7d13a2e4d8f67af7cda",
    "ml-detector/src/zmq_handler.cpp": "e94b608313d3e9e23de4adbf320a42940885f89b21f0c29abd1952ff205ed9af",
    "ml-detector/tests/CMakeLists.txt": "69bb1eb3e39f1a61e9dc4b9ee3103ceb363bb1177379ba0a580f1a3188f6dbbb",
    "ml-detector/tests/integration/test_csv_event_writer.cpp": "d38bf99e32a818d9509b5b775207f5d15b6f236d1bdefddbd3e49a57577b4a12",
    "ml-detector/tests/integration/test_csv_feature_extraction.cpp": "805699ef8b5df76ebff4eb638ed6f7c707fc83be344cba6d3bac9e33a09a36a6",
    "ml-detector/tests/unit/test_detectors.cpp": "b7b14760d7bc1ce8c3159e9f639ffad00d03a79af5b546d577590a12356b0f7e"
}
CUTS = {
    "ml-detector/config/ml_detector_config.json#1": "24f143393b9540ba1658c5633c122b6995e19196ef951fd699c01fd5fb818a14",
    "ml-detector/src/config_loader.cpp#1": "41d063e4d3c3bdb9d09614b6a4a8ba3dcdc82eb726266fd50358745c3a5268ee",
    "ml-detector/src/contract_validator.cpp#0": "18224ed57bdab5a22981cb08b645f2b719cf680e75b6e3a9187005fd078b1e71",
    "ml-detector/src/csv_event_writer.cpp#0": "d1fd8dd1d7279922a2522c6aaeaf016a61c6aba838097c451551fb76d4e6e258",
    "ml-detector/src/feature_extractor.cpp#0": "8e2043699bcf045a78179a83355ceaf1b67372db6fade6cb7a74b9ba898bc134",
    "ml-detector/src/main.cpp#2": "17b43e5292aec6ecc237fa7af70f850b5ab5b6e809d6fe005a0752758c84bc4e",
    "ml-detector/src/zmq_handler.cpp#8": "75b4730223c061b3845bcf3a7b59e2760df4469dd1c11b1ee3085284c8e94322",
    "ml-detector/tests/unit/test_detectors.cpp#2": "6a428cd0520554527b2e64851458129a340285e74e992572fb018cc6951f7bf3",
    "ml-detector/tests/unit/test_detectors.cpp#3": "9b6e6439f894e78da915ae40a013a34b4eae059454163e20bb04e7de75e8e37c"
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
            errores.append(f"{path}: sha256 {h[:12]} no es el de HEAD 9dcf014e ({PRE.get(path, '?')[:12]}) ni el aplicado")
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
