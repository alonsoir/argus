// zeek-adapter/tests/test_to_row.cpp
// aRGus NDR — test de la capa PURA del adapter de zeek.
//
// Sin framework: main() con asserts, ejecutado por ctest. to_row es pura: se le
// pasa el indice del `#fields` y una fila literal, y se comprueba el Row campo a
// campo. Sin VM, sin fichero, sin reloj.
//
// VECTOR REAL: la fila diana de logs/day235-zeek-neris/conn.log (MEDIDO DAY 235),
// flujo 147.32.84.165:1027 -> 74.125.232.195:80, community_id validado seed 0
// contra Suricata y aRGus. Zeek es TELEMETRIA: cols de veredicto vacias.
//
// Reproducir:  grep -m1 '1:IN7uqVpMWxpmuhQTowSQB2XEe0E=' logs/day235-zeek-neris/conn.log

#include <cstdint>
#include <iostream>
#include <string>

#include "zeek_adapter/to_row.hpp"

namespace {

// `#fields` real de conn.log (24 tokens: el literal `#fields` + 23 campos).
const char* kFieldsLine =
    "#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice"
    "\tduration\torig_bytes\tresp_bytes\tconn_state\tlocal_orig\tlocal_resp"
    "\tmissed_bytes\thistory\torig_pkts\torig_ip_bytes\tresp_pkts\tresp_ip_bytes"
    "\ttunnel_parents\tip_proto\tcommunity_id";

// Fila diana (23 valores).
const char* kConnLine =
    "1312967066.683089\tCLZYnU2cVwWj3YmTXf\t147.32.84.165\t1027\t74.125.232.195\t80"
    "\ttcp\thttp\t0.045136\t393\t77\tRSTO\tF\tF\t0\tShADTadR\t8\t1122\t3\t205\t-\t6"
    "\t1:IN7uqVpMWxpmuhQTowSQB2XEe0E=";

int failures = 0;

void check(bool cond, const char* what) {
    if (!cond) { std::cerr << "FALLO: " << what << "\n"; ++failures; }
}

void test_parse_zeek_ts() {
    int64_t secs = 0; int32_t nanos = 0;
    check(zeek_adapter::parse_zeek_ts("1312967066.683089", secs, nanos), "parse_zeek_ts acepta epoch double");
    check(secs == 1312967066, "parte entera = epoch de la conexion");
    check(nanos == 683089000, "micros (683089) -> nanos x1000");

    int64_t s2 = 0; int32_t n2 = 0;
    check(zeek_adapter::parse_zeek_ts("1312967066", s2, n2), "acepta epoch sin fraccion");
    check(s2 == 1312967066 && n2 == 0, "sin fraccion -> nanos 0");

    int64_t s3 = 0; int32_t n3 = 0;
    check(!zeek_adapter::parse_zeek_ts("no-es-ts", s3, n3), "rechaza no numerico");
}

void test_conn_produce_fila() {
    const auto idx = zeek_adapter::parse_conn_fields(kFieldsLine);
    check(!idx.empty(), "parse_conn_fields construye el indice del #fields");

    auto r = zeek_adapter::to_row(kConnLine, idx, "zeek_test_node");
    check(r.status == zeek_adapter::ToRowResult::Status::Ok, "una conexion con community_id da Ok");
    if (r.status != zeek_adapter::ToRowResult::Status::Ok) return;

    check(r.row.schema_version == "1",                           "col 0 schema_version");
    check(r.row.source_sensor == "zeek",                         "col 1 source_sensor");
    check(r.row.event_id.rfind("zeek:", 0) == 0,                 "col 2 event_id prefijado (D3)");
    check(r.row.node_id == "zeek_test_node",                     "col 3 node_id de la config");
    check(r.row.community_id == "1:IN7uqVpMWxpmuhQTowSQB2XEe0E=","col 4 community_id");
    check(r.row.flow_start_sec == 1312967066,                    "col 5 flow_start <- ts (inicio de conexion, D4)");
    check(r.row.flow_start_nano == 683089000,                    "col 6 flow_start nanos");
    check(r.row.src_ip == "147.32.84.165",                       "col 7 <- id.orig_h");
    check(r.row.dst_ip == "74.125.232.195",                      "col 8 <- id.resp_h");
    check(r.row.src_port == 1027,                                "col 9 <- id.orig_p");
    check(r.row.dst_port == 80,                                  "col 10 <- id.resp_p");
    check(r.row.protocol == "tcp",                               "col 11 proto minusculas (D-proto-case)");

    // D6 — Zeek es telemetria: veredicto vacio.
    check(r.row.final_classification.empty(),                    "col 12 vacia (sin veredicto)");
    check(r.row.threat_category.empty(),                         "col 13 vacia (sin veredicto)");
    check(r.row.fast_detector_score == 0.0,                      "col 14 = 0.0 ausencia (D6)");
    check(r.row.ml_detector_score == 0.0,                        "col 15 = 0.0 ausencia (D6)");
    check(r.row.overall_threat_score == 0.0,                     "col 16 = 0.0 ausencia (D6)");
    check(r.row.authoritative_source == "zeek",                  "col 17 authoritative_source");
}

void test_event_id_determinista() {
    const auto idx = zeek_adapter::parse_conn_fields(kFieldsLine);
    auto a = zeek_adapter::to_row(kConnLine, idx, "n1");
    auto b = zeek_adapter::to_row(kConnLine, idx, "n1");
    check(a.status == zeek_adapter::ToRowResult::Status::Ok &&
          a.row.event_id == b.row.event_id,
          "D3: la misma fila da el mismo event_id (reprocesar no duplica nodos)");
    check(zeek_adapter::make_event_id("1:abc=", "1312967066.683089") ==
          zeek_adapter::make_event_id("1:abc=", "1312967066.683089"),
          "make_event_id determinista");
    check(zeek_adapter::make_event_id("1:abc=", "1").rfind("zeek:", 0) == 0,
          "make_event_id prefijado zeek:");
}

void test_descartes() {
    const auto idx = zeek_adapter::parse_conn_fields(kFieldsLine);

    // community_id unset ('-') -> Skip (D5), no Error.
    std::string sin_cid =
        "1312967066.683089\tu\t147.32.84.165\t1027\t74.125.232.195\t80\ttcp\thttp\t0\t0\t0"
        "\tRSTO\tF\tF\t0\t-\t0\t0\t0\t0\t-\t6\t-";
    check(zeek_adapter::to_row(sin_cid, idx, "n1").status == zeek_adapter::ToRowResult::Status::Skip,
          "sin community_id se descarta (D5)");

    // Linea vacia y linea de preambulo -> Skip.
    check(zeek_adapter::to_row("", idx, "n1").status == zeek_adapter::ToRowResult::Status::Skip,
          "linea vacia se descarta");
    check(zeek_adapter::to_row("#close\t2026-07-28", idx, "n1").status == zeek_adapter::ToRowResult::Status::Skip,
          "linea de preambulo se descarta");

    // ts no parseable -> Error (un Skip lo haria invisible).
    std::string ts_malo =
        "no-es-ts\tu\t147.32.84.165\t1027\t74.125.232.195\t80\ttcp\thttp\t0\t0\t0\tRSTO"
        "\tF\tF\t0\t-\t0\t0\t0\t0\t-\t6\t1:IN7uqVpMWxpmuhQTowSQB2XEe0E=";
    check(zeek_adapter::to_row(ts_malo, idx, "n1").status == zeek_adapter::ToRowResult::Status::Error,
          "ts no parseable es Error, no Skip");
}

}  // namespace

int main() {
    test_parse_zeek_ts();
    test_conn_produce_fila();
    test_event_id_determinista();
    test_descartes();

    if (failures != 0) { std::cerr << failures << " comprobacion(es) fallidas\n"; return 1; }
    std::cout << "OK — capa pura del adapter de zeek\n";
    return 0;
}