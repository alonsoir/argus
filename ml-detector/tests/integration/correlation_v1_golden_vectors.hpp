// correlation_v1_golden_vectors.hpp — aRGus NDR — DAY 185 (B2/B3)
// FUENTE ÚNICA de los eventos del golden. La incluyen capture_golden.cpp (B2,
// captura) y test_correlation_v1_oracle.cpp (B3, comparación). Si vivieran en dos
// sitios, derivarían y el golden mentiría. Authors: Alonso Isidoro Roman + Claude.
//
// DETERMINISTA: cero RNG, todos los campos literales. El injector NO sirve aquí
// (random_device -> no reproducible, y no estresa comas/comillas/NaN).
//
// DOS BLOQUES:
//   realista — heredados del patrón de test_correlation_roundtrip (eventos que el
//              pipeline sí produce).
//   rincon   — los rincones del serializador: comas, comillas, \n, \r, \t, NaN, Inf,
//              negativos, alta precisión, UTF-8, vacíos, puertos/ts extremos, los 7
//              enums de DetectorSource, enum desconocido (drift), y community_id vacío
//              (SKIP, D-F). "Ponernos en lo peor": no sabemos qué traerán Suricata/
//              Zeek/Wazuh/Andrés.
#pragma once

#include <cmath>
#include <limits>
#include <string>
#include <vector>

#include <network_security.pb.h>

namespace argus_golden {

struct GoldenVector {
    std::string id;        // estable; casa B2 (captura) con B3 (comparación)
    std::string category;  // "realista" | "rincon"
    std::string note;      // qué ejercita (solo informativo)
    bool expect_skip;      // true si community_id vacío -> write_record SKIP, sin línea
    protobuf::NetworkSecurityEvent event;
};

// Evento base válido y realista (clon de los valores de test_correlation_roundtrip).
inline protobuf::NetworkSecurityEvent base_event() {
    protobuf::NetworkSecurityEvent e;
    e.set_event_id("evt-rt-001");
    e.set_originating_node_id("node-uuid-roundtrip");
    e.set_final_classification("MALICIOUS");
    e.set_threat_category("DDOS");
    e.set_fast_detector_score(0.910000);
    e.set_ml_detector_score(0.870000);
    e.set_overall_threat_score(0.890000);
    e.set_authoritative_source(::protobuf::DETECTOR_SOURCE_ML_PRIORITY);  // 4
    auto* nf = e.mutable_network_features();
    nf->set_community_id("1:IN7uqVpMWxpmuhQTowSQB2XEe0E=");
    nf->set_source_ip("147.32.84.165");
    nf->set_destination_ip("74.125.232.195");
    nf->set_source_port(1027u);
    nf->set_destination_port(80u);
    nf->set_protocol_name("tcp");
    nf->mutable_flow_start_time()->set_seconds(1717480800);
    nf->mutable_flow_start_time()->set_nanos(123456000);
    return e;
}

inline std::vector<GoldenVector> make_golden_vectors() {
    std::vector<GoldenVector> v;
    auto add = [&](const std::string& id, const std::string& cat,
                   const std::string& note, bool skip,
                   protobuf::NetworkSecurityEvent ev) {
        v.push_back(GoldenVector{id, cat, note, skip, std::move(ev)});
    };

    // ── BLOQUE REALISTA ──────────────────────────────────────────────────────
    add("realista_01_malicioso_tcp", "realista",
        "base: malicioso tcp ML_PRIORITY", false, base_event());

    {
        auto e = base_event();
        e.set_event_id("evt-benign-002");
        e.set_final_classification("BENIGN");
        e.set_threat_category("NORMAL");
        e.set_fast_detector_score(0.100000);
        e.set_ml_detector_score(0.050000);
        e.set_overall_threat_score(0.080000);
        e.set_authoritative_source(::protobuf::DETECTOR_SOURCE_FAST_ONLY);
        auto* nf = e.mutable_network_features();
        nf->set_protocol_name("udp");
        nf->set_source_ip("10.0.0.5");
        nf->set_destination_ip("10.0.0.6");
        nf->set_source_port(5353u);
        nf->set_destination_port(53u);
        add("realista_02_benigno_udp", "realista", "benigno udp FAST_ONLY", false, e);
    }
    {
        auto e = base_event();
        e.set_event_id("evt-susp-003");
        e.set_final_classification("SUSPICIOUS");
        e.set_threat_category("RANSOMWARE");
        e.set_authoritative_source(::protobuf::DETECTOR_SOURCE_CONSENSUS);
        add("realista_03_consensus", "realista", "sospechoso CONSENSUS", false, e);
    }

    // ── BLOQUE RINCÓN ────────────────────────────────────────────────────────
    {   auto e = base_event();
        e.set_final_classification("DDOS,LATERAL_MOVEMENT");  // coma -> csv_string entrecomilla
        add("rincon_01_coma", "rincon", "coma en final_classification", false, e); }

    {   auto e = base_event();
        e.set_originating_node_id("node\"injected\"id");       // comilla -> escape ""
        add("rincon_02_comilla", "rincon", "comilla embebida en node_id", false, e); }

    {   auto e = base_event();
        e.set_threat_category("A,\"B\"");                      // coma + comilla
        add("rincon_03_coma_y_comilla", "rincon", "coma y comilla en threat_category", false, e); }

    {   auto e = base_event();
        e.set_final_classification("LINEA1\nLINEA2");          // \n -> registro multilínea físico
        add("rincon_04_newline", "rincon",
            "newline embebido (DEBT-BRONZE-EMBEDDED-NEWLINE-001: reader getline)", false, e); }

    {   auto e = base_event();
        e.set_event_id("evt\rCR");                             // \r NO entrecomillado (csv_string solo ,"\n)
        add("rincon_05_cr", "rincon", "carriage return crudo en event_id", false, e); }

    {   auto e = base_event();
        e.mutable_network_features()->set_protocol_name("t\tcp");  // tab crudo (no entrecomillado)
        add("rincon_06_tab", "rincon", "tab crudo en protocol (riesgo TSV downstream)", false, e); }

    {   auto e = base_event();
        e.set_fast_detector_score(std::numeric_limits<double>::quiet_NaN());  // -> "0.000000"
        add("rincon_07_nan", "rincon", "NaN en fast_detector_score", false, e); }

    {   auto e = base_event();
        e.set_ml_detector_score(std::numeric_limits<double>::infinity());     // -> "0.000000"
        add("rincon_08_inf", "rincon", "+Inf en ml_detector_score", false, e); }

    {   auto e = base_event();
        e.set_overall_threat_score(-1.0);                     // sentinel "missing" -> "-1.000000"
        add("rincon_09_negativo", "rincon", "score negativo (sentinel)", false, e); }

    {   auto e = base_event();
        e.set_fast_detector_score(0.123456789);              // redondeo a 6 -> "0.123457"
        add("rincon_10_precision", "rincon", "alta precisión -> redondeo 6 dec", false, e); }

    {   auto e = base_event();
        e.set_originating_node_id("nodo-\xC3\xB1-\xC3\xA9-municipio");  // UTF-8 ñ é
        add("rincon_11_utf8", "rincon", "UTF-8 en node_id (municipio ES)", false, e); }

    {   auto e = base_event();
        e.set_event_id("");                                   // vacíos NO-cid: se escriben vacíos
        e.set_threat_category("");
        add("rincon_12_vacios", "rincon", "event_id y threat_category vacíos", false, e); }

    {   auto e = base_event();
        auto* nf = e.mutable_network_features();
        nf->set_source_port(0u);
        nf->set_destination_port(65535u);
        add("rincon_13_puertos_extremos", "rincon", "puertos 0 y 65535", false, e); }

    {   auto e = base_event();
        auto* ts = e.mutable_network_features()->mutable_flow_start_time();
        ts->set_seconds(0);
        ts->set_nanos(0);
        add("rincon_14_ts_cero", "rincon", "flow_start_time = 0/0", false, e); }

    // los 7 símbolos de DetectorSource — sella el mapeo de la col 17
    {
        const ::protobuf::DetectorSource kEnums[] = {
            ::protobuf::DETECTOR_SOURCE_UNKNOWN,
            ::protobuf::DETECTOR_SOURCE_FAST_ONLY,
            ::protobuf::DETECTOR_SOURCE_ML_ONLY,
            ::protobuf::DETECTOR_SOURCE_FAST_PRIORITY,
            ::protobuf::DETECTOR_SOURCE_ML_PRIORITY,
            ::protobuf::DETECTOR_SOURCE_CONSENSUS,
            ::protobuf::DETECTOR_SOURCE_DIVERGENCE,
        };
        int i = 0;
        for (auto src : kEnums) {
            auto e = base_event();
            e.set_authoritative_source(src);
            char id[48];
            std::snprintf(id, sizeof(id), "rincon_15_enum_%d_%s", i,
                          ::protobuf::DetectorSource_Name(src).c_str());
            add(id, "rincon", "col 17 = " + ::protobuf::DetectorSource_Name(src), false, e);
            ++i;
        }
    }

    // enum DESCONOCIDO (drift): DetectorSource_Name(99) -> "" (o lo que sea).
    // to_row Y build_row llaman la MISMA función -> byte-idéntico pase lo que pase.
    // En v1 el guard D-D NO actúa; esta entrada SELLA el comportamiento v1.
    {   auto e = base_event();
        e.set_authoritative_source(static_cast<::protobuf::DetectorSource>(99));
        add("rincon_16_enum_drift", "rincon",
            "col 17 enum desconocido (99) — v1 sin guard D-D", false, e); }

    // el saco entero: coma + comilla + UTF-8 + NaN + puertos extremos
    {   auto e = base_event();
        e.set_final_classification("X,\"Y\"-\xC3\xB1");
        e.set_fast_detector_score(std::numeric_limits<double>::quiet_NaN());
        auto* nf = e.mutable_network_features();
        nf->set_source_port(0u);
        nf->set_destination_port(65535u);
        add("rincon_17_todo_junto", "rincon", "coma+comilla+UTF8+NaN+puertos", false, e); }

    // community_id VACÍO -> write_record SKIP (D-F). Sin línea en el golden.
    {   auto e = base_event();
        e.set_event_id("evt-skip-cid-vacio");
        e.mutable_network_features()->set_community_id("");
        add("rincon_18_cid_vacio_SKIP", "rincon",
            "community_id vacío -> SKIP (D-F), sin bytes", true, e); }

    return v;
}

}  // namespace argus_golden