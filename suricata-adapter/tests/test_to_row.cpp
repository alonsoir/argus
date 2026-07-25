// suricata-adapter/tests/test_to_row.cpp
// aRGus NDR — test de la capa PURA del adapter de suricata.
//
// Sin framework: main() con asserts, ejecutado por ctest. to_row es pura, así que
// el test le da una línea literal y comprueba el Row campo a campo. Sin VM, sin
// fichero, sin reloj.
//
// VECTOR REAL: primera alerta de logs/day225-suricata-neris/eve.json, copiada
// literalmente (DAY 226). Es un "SURICATA TCPv4 invalid checksum", o sea un
// artefacto de la captura (68/1000 checksums invalidos, medido DAY 225), no un
// ataque. Da igual para el test: trae community_id y flow.start, que es lo que
// se comprueba. Pero no sirve de escaparate en el paper.
//
// Reproducir:  grep -m1 '"event_type":"alert"' logs/day225-suricata-neris/eve.json

#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>

#include "suricata_adapter/to_row.hpp"

namespace {

const char* kAlertLine = R"({"timestamp":"2011-08-10T09:06:36.150781+0000","flow_id":1180526643469803,"pcap_cnt":126,"event_type":"alert","src_ip":"94.63.149.152","src_port":80,"dest_ip":"147.32.84.165","dest_port":1040,"proto":"TCP","pkt_src":"wire/pcap","community_id":"1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=","alert":{"action":"allowed","gid":1,"signature_id":2200074,"rev":2,"signature":"SURICATA TCPv4 invalid checksum","category":"Generic Protocol Command Decode","severity":3},"app_proto":"http","direction":"to_client","flow":{"pkts_toserver":6,"pkts_toclient":3,"bytes_toserver":532,"bytes_toclient":4556,"start":"2011-08-10T09:06:36.078254+0000","src_ip":"147.32.84.165","dest_ip":"94.63.149.152","src_port":1040,"dest_port":80}})";

int failures = 0;

void check(bool cond, const char* what) {
    if (!cond) {
        std::cerr << "FALLO: " << what << "\n";
        ++failures;
    }
}

void test_parse_iso8601() {
    int64_t secs = 0;
    int32_t nanos = 0;
    check(suricata_adapter::parse_iso8601("2011-08-10T09:06:36.078254+0000", secs, nanos),
          "parse_iso8601 acepta el formato medido");
    check(secs == 1312967196, "epoch de 2011-08-10T09:06:36Z");
    check(nanos == 78254000, "micros x 1000 -> nanos (078254 -> 78254000)");

    // El offset es DEL EVENTO: la misma hora de pared con +0200 son 2 h menos de epoch.
    int64_t secs_cest = 0;
    int32_t nanos_cest = 0;
    check(suricata_adapter::parse_iso8601("2011-08-10T09:06:36.078254+0200", secs_cest, nanos_cest),
          "parse_iso8601 acepta offset no nulo");
    check(secs_cest == secs - 7200, "el offset del evento se resta");
}

void test_alerta_produce_fila() {
    auto r = suricata_adapter::to_row(kAlertLine, "cpp_sniffer_v33_day12");
    check(r.status == suricata_adapter::ToRowResult::Status::Ok, "una alerta con community_id da Ok");
    if (r.status != suricata_adapter::ToRowResult::Status::Ok) return;

    check(r.row.schema_version == "1",                          "col 0 schema_version");
    check(r.row.source_sensor == "suricata",                  "col 1 source_sensor");
    check(r.row.event_id.rfind("suricata:", 0) == 0,          "col 2 event_id prefijado (D3)");
    check(r.row.node_id == "cpp_sniffer_v33_day12",             "col 3 node_id de la config");
    check(r.row.community_id == "1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=", "col 4 community_id");
    check(r.row.flow_start_sec == 1312967196,                   "col 5 de flow.start (09:06:36), NO del timestamp del evento (09:06:36.150781)");
    check(r.row.flow_start_nano == 78254000,                    "col 6 de flow.start");

    // Cols 7-10 del OBJETO flow (originador), no del nivel superior (paquete).
    // En este vector estan invertidos entre si, como en el 99,4% de las alertas
    // del Neris: si el adapter copiara el nivel superior, aqui saldria
    // 94.63.149.152:80 -> 147.32.84.165:1040. Este test es el que lo impide.
    check(r.row.src_ip == "147.32.84.165",                      "col 7 <- flow.src_ip, no el de nivel superior");
    check(r.row.dst_ip == "94.63.149.152",                      "col 8 <- flow.dest_ip");
    check(r.row.src_port == 1040,                               "col 9 <- flow.src_port");
    check(r.row.dst_port == 80,                                 "col 10 <- flow.dest_port");
    check(r.row.protocol == "TCP",                              "col 11 proto -> protocol");
    check(r.row.final_classification == "SURICATA TCPv4 invalid checksum",
          "col 12 <- alert.signature (D6)");
    check(r.row.threat_category == "Generic Protocol Command Decode",
          "col 13 <- alert.category (D6)");
    check(r.row.fast_detector_score == 0.0,                     "col 14 = 0.0 ausencia (D6)");
    check(r.row.ml_detector_score == 0.0,                       "col 15 = 0.0 ausencia (D6)");
    check(r.row.overall_threat_score == 0.0,                    "col 16 = 0.0 ausencia (D6)");
    check(r.row.authoritative_source == "suricata",           "col 17 authoritative_source");
}

void test_event_id_determinista() {
    auto a = suricata_adapter::to_row(kAlertLine, "n1");
    auto b = suricata_adapter::to_row(kAlertLine, "n1");
    check(a.status == suricata_adapter::ToRowResult::Status::Ok &&
          a.row.event_id == b.row.event_id,
          "D3: la misma linea da el mismo event_id (reprocesar no duplica nodos)");
}

void test_descartes() {
    auto stats = suricata_adapter::to_row(R"({"event_type":"stats"})", "n1");
    check(stats.status == suricata_adapter::ToRowResult::Status::Skip, "stats se descarta (D5)");

    auto dns = suricata_adapter::to_row(R"({"event_type":"dns","community_id":"1:abc="})", "n1");
    check(dns.status == suricata_adapter::ToRowResult::Status::Skip, "la telemetria se descarta hoy (D4)");

    auto decoder = suricata_adapter::to_row(
        R"({"event_type":"alert","alert":{"signature_id":2200076}})", "n1");
    check(decoder.status == suricata_adapter::ToRowResult::Status::Skip,
          "alerta de decoder sin community_id se descarta (D5), no es Error");

    auto basura = suricata_adapter::to_row("{esto no es json", "n1");
    check(basura.status == suricata_adapter::ToRowResult::Status::Error,
          "json ilegible es Error, no Skip: un Skip lo haria invisible");
}

}  // namespace

int main() {
    test_parse_iso8601();
    test_alerta_produce_fila();
    test_event_id_determinista();
    test_descartes();

    if (failures != 0) {
        std::cerr << failures << " comprobacion(es) fallidas\n";
        return 1;
    }
    std::cout << "OK — capa pura del adapter de suricata\n";
    return 0;
}
