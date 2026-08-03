// wazuh-adapter/tests/test_to_row.cpp
// aRGus NDR — test de la capa PURA del adapter de wazuh.
//
// Sin framework: main() con asserts, ejecutado por ctest. to_row es pura, así que el test
// le da una línea literal y comprueba el Row campo a campo. Sin VM, sin fichero, sin reloj.
//
// VECTORES REALES: líneas del snapshot day240
//   docs/design/host-domain-contract/evidencia/alerts-day240-snapshot.json
// una por rule.id. Copiadas literalmente (DAY 242). Verificado en contenedor: C++ y la
// referencia Python (host_domain_v1_ref.py) cruzan byte-idéntico sobre estas mismas líneas.
//
// El caso 533 (netstat) trae \n REAL en full_log: prueba que el saneador (D-HOST-3) lo
// convierte en una sola línea física y que serialize() lo ACEPTA (antes lo rechazaba).

#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include <host_domain_v1/host_domain_v1.hpp>

#include "wazuh_adapter/to_row.hpp"

namespace {

// sshd 5715 — auth success, MITRE T1078+T1021 (Lateral Movement), coordenada de red en data
const char* kLine5715 = R"J({"timestamp":"2026-07-31T03:30:59.264+0000","rule":{"level":3,"description":"sshd: authentication success.","id":"5715","mitre":{"id":["T1078","T1021"],"tactic":["Defense Evasion","Persistence","Privilege Escalation","Initial Access","Lateral Movement"],"technique":["Valid Accounts","Remote Services"]},"firedtimes":1,"mail":false,"groups":["syslog","sshd","authentication_success"],"gdpr":["IV_32.2"],"gpg13":["7.1","7.2"],"hipaa":["164.312.b"],"nist_800_53":["AU.14","AC.7"],"pci_dss":["10.2.5"],"tsc":["CC6.8","CC7.2","CC7.3"]},"agent":{"id":"000","name":"argus-wazuh"},"manager":{"name":"argus-wazuh"},"id":"1785468659.10966","full_log":"Jul 31 03:30:58 argus-wazuh sshd[3140]: Accepted publickey for vagrant from 10.0.2.2 port 49581 ssh2: ED25519 SHA256:hkxznnkU/Fdi7JnHBxX4qQQSuQ+TBVthb5i128+jGyA","predecoder":{"program_name":"sshd","timestamp":"Jul 31 03:30:58","hostname":"argus-wazuh"},"decoder":{"parent":"sshd","name":"sshd"},"data":{"srcip":"10.0.2.2","srcport":"49581","dstuser":"vagrant"},"location":"journald"})J";

// sudo->ROOT 5402 — T1548.003, data con command
const char* kLine5402 = R"J({"timestamp":"2026-07-31T03:22:36.816+0000","rule":{"level":3,"description":"Successful sudo to ROOT executed.","id":"5402","mitre":{"id":["T1548.003"],"tactic":["Privilege Escalation","Defense Evasion"],"technique":["Sudo and Sudo Caching"]},"firedtimes":1,"mail":false,"groups":["syslog","sudo"],"pci_dss":["10.2.5","10.2.2"],"gpg13":["7.6","7.8","7.13"],"gdpr":["IV_32.2"],"hipaa":["164.312.b"],"nist_800_53":["AU.14","AC.7","AC.6"],"tsc":["CC6.8","CC7.2","CC7.3"]},"agent":{"id":"002","name":"zeek","ip":"192.168.100.11"},"manager":{"name":"argus-wazuh"},"id":"1785468156.2917","full_log":"Jul 31 03:22:33 argus-zeek sudo[1200]:  vagrant : PWD=/home/vagrant ; USER=root ; COMMAND=/usr/bin/bash -l","predecoder":{"program_name":"sudo","timestamp":"Jul 31 03:22:33","hostname":"argus-zeek"},"decoder":{"parent":"sudo","name":"sudo","ftscomment":"First time user executed the sudo command"},"data":{"srcuser":"vagrant","dstuser":"root","pwd":"/home/vagrant","command":"/usr/bin/bash -l"},"location":"journald"})J";

// PAM 5501 — T1078, data con uid presente
const char* kLine5501 = R"J({"timestamp":"2026-07-31T03:22:36.849+0000","rule":{"level":3,"description":"PAM: Login session opened.","id":"5501","mitre":{"id":["T1078"],"tactic":["Defense Evasion","Persistence","Privilege Escalation","Initial Access"],"technique":["Valid Accounts"]},"firedtimes":1,"mail":false,"groups":["pam","syslog","authentication_success"],"pci_dss":["10.2.5"],"gpg13":["7.8","7.9"],"gdpr":["IV_32.2"],"hipaa":["164.312.b"],"nist_800_53":["AU.14","AC.7"],"tsc":["CC6.8","CC7.2","CC7.3"]},"agent":{"id":"002","name":"zeek","ip":"192.168.100.11"},"manager":{"name":"argus-wazuh"},"id":"1785468156.3764","full_log":"Jul 31 03:22:33 argus-zeek sudo[1200]: pam_unix(sudo:session): session opened for user root(uid=0) by (uid=1000)","predecoder":{"program_name":"sudo","timestamp":"Jul 31 03:22:33","hostname":"argus-zeek"},"decoder":{"parent":"pam","name":"pam"},"data":{"dstuser":"root","uid":"1000"},"location":"journald"})J";

// netstat 533 — SIN mitre, SIN data, full_log MULTILÍNEA (\n real): el caso del saneador
const char* kLine533 = R"J({"timestamp":"2026-07-31T03:22:09.071+0000","rule":{"level":7,"description":"Listened ports status (netstat) changed (new port opened or closed).","id":"533","firedtimes":1,"mail":false,"groups":["ossec"],"pci_dss":["10.2.7","10.6.1"],"gpg13":["10.1"],"gdpr":["IV_35.7.d"],"hipaa":["164.312.b"],"nist_800_53":["AU.14","AU.6"],"tsc":["CC6.8","CC7.2","CC7.3"]},"agent":{"id":"000","name":"argus-wazuh"},"manager":{"name":"argus-wazuh"},"id":"1785468129.0","previous_output":"Previous output:\nossec: output: 'netstat listening ports':\ntcp 0.0.0.0:22 0.0.0.0:* /usr","full_log":"ossec: output: 'netstat listening ports':\ntcp 0.0.0.0:22 0.0.0.0:* /usr\ntcp 0.0.0.0:1514 0.0.0.0:* 1240/wazuh-remoted","decoder":{"name":"ossec"},"location":"netstat listening ports"})J";

int failures = 0;

void check(bool cond, const char* what) {
    if (!cond) { std::cerr << "FALLO: " << what << "\n"; ++failures; }
}

const host_domain_v1::HostDomainV1Row* row_of(const wazuh_adapter::ToRowResult& r) {
    return (r.status == wazuh_adapter::ToRowResult::Status::Ok) ? &r.row : nullptr;
}

void test_5715_mapping() {
    auto r = wazuh_adapter::to_row(kLine5715);
    check(r.status == wazuh_adapter::ToRowResult::Status::Ok, "5715 -> Ok");
    const auto* row = row_of(r);
    if (!row) return;

    check(row->schema_version == "host_domain_v1",     "col 0 schema_version");
    check(row->source_sensor  == "wazuh",              "col 1 source_sensor");
    check(row->event_id.rfind("wz1:", 0) == 0,          "col 2 event_id prefijo wz1: (D-HOST-1)");
    check(row->host_id   == "000",                      "col 3 host_id = agent.id");
    check(row->wazuh_alert_id == "1785468659.10966",    "col 4 wazuh_alert_id = id top-level");
    check(row->timestamp == "2026-07-31T03:30:59.264+0000", "col 5 timestamp top-level");
    check(row->agent_name == "argus-wazuh",             "col 7 agent_name");
    check(row->agent_ip == "",                          "col 8 agent_ip vacio en agente 000");
    check(row->os_hostname == "argus-wazuh",            "col 9 os_hostname = predecoder.hostname");
    check(row->rule_id == "5715",                       "col 10 rule_id");
    check(row->rule_level == 3,                         "col 11 rule_level (int)");
    check(row->decoder_name == "sshd",                  "col 14 decoder.name");
    check(row->location == "journald",                  "col 15 location");
    check(row->data_json == R"J({"srcip":"10.0.2.2","srcport":"49581","dstuser":"vagrant"})J",
          "col 17 data_json compacto, ORDEN PRESERVADO");
    check(row->dstuser == "vagrant",                    "col 19 dstuser <- data");
    check(row->srcip == "10.0.2.2",                     "col 20 srcip <- data (breadcrumb lateral)");
    check(row->srcport == "49581",                      "col 21 srcport <- data");
    check(row->mitre_ids == R"J(["T1078","T1021"])J",   "col 24 mitre_ids (Lateral Movement)");
    check(row->pci_dss == R"J(["10.2.5"])J",            "col 27 pci_dss");
    check(row->nist_800_53 == R"J(["AU.14","AC.7"])J",  "col 30 nist_800_53");

    // extremo a extremo: la fila serializa y da 34 celdas + HMAC de 64 hex
    auto sr = host_domain_v1::serialize(*row, std::vector<uint8_t>(32, 0xAB));
    check(sr.ok, "5715 serialize OK");
    check(sr.line.size() > 64 && sr.line.substr(sr.line.size() - 65, 1) == ",",
          "5715 la ultima celda es el HMAC (precedido por coma)");
}

void test_5402_command() {
    auto r = wazuh_adapter::to_row(kLine5402);
    const auto* row = row_of(r);
    check(row != nullptr, "5402 -> Ok");
    if (!row) return;
    check(row->host_id == "002",                        "5402 host_id = 002");
    check(row->srcuser == "vagrant",                    "5402 srcuser <- data");
    check(row->command == "/usr/bin/bash -l",           "5402 command <- data");
    check(row->mitre_ids == R"J(["T1548.003"])J",       "5402 mitre_ids privesc");
    check(row->os_hostname == "argus-zeek",             "5402 os_hostname = predecoder.hostname");
}

void test_5501_uid() {
    auto r = wazuh_adapter::to_row(kLine5501);
    const auto* row = row_of(r);
    check(row != nullptr, "5501 -> Ok");
    if (!row) return;
    check(row->uid == "1000",                           "5501 uid <- data");
    check(row->mitre_ids == R"J(["T1078"])J",           "5501 mitre_ids T1078");
    check(row->agent_ip == "192.168.100.11",            "5501 agent_ip = 192.168.100.11 (agente 002)");
}

void test_533_newline_saneado() {
    auto r = wazuh_adapter::to_row(kLine533);
    const auto* row = row_of(r);
    check(row != nullptr, "533 -> Ok");
    if (!row) return;

    // El saneador convirtio los \n reales en escape literal: NINGUN salto fisico.
    check(row->full_log.find('\n') == std::string::npos, "533 full_log SIN \\n fisico (saneado)");
    check(row->full_log.find('\r') == std::string::npos, "533 full_log SIN \\r fisico");
    check(row->full_log.find("\\n") != std::string::npos, "533 full_log CON escape literal \\n");
    check(row->mitre_ids == "[]",                        "533 sin mitre -> []");
    check(row->data_json == "{}",                        "533 sin data -> {}");
    check(row->decoder_name == "ossec",                  "533 decoder.name = ossec");

    // Lo que importa: serialize() la ACEPTA (antes del saneado, validate la rechazaba).
    auto sr = host_domain_v1::serialize(*row, std::vector<uint8_t>(32, 0xAB));
    check(sr.ok, "533 serialize OK tras saneado (el netstat sobrevive, no se pierde)");
}

void test_host_id_vacio_lo_rechaza_la_lib() {
    // Alerta sin objeto agent -> host_id "". to_row NO lo filtra (Ok); serialize() SI (P3).
    auto r = wazuh_adapter::to_row(R"J({"rule":{"id":"5501","level":3},"id":"x"})J");
    const auto* row = row_of(r);
    check(row != nullptr, "sin agent -> to_row Ok (no es el adapter quien filtra)");
    if (!row) return;
    check(row->host_id == "",                            "host_id vacio cuando no hay agent.id");
    auto sr = host_domain_v1::serialize(*row, std::vector<uint8_t>(32, 0xAB));
    check(!sr.ok, "host_id vacio -> serialize RECHAZA (notario unico, D-HOST-3)");
    check(sr.error.find("host_id") != std::string::npos, "el diagnostico menciona host_id");
}

void test_descartes() {
    check(wazuh_adapter::to_row("").status == wazuh_adapter::ToRowResult::Status::Skip,
          "linea vacia -> Skip (D5)");
    check(wazuh_adapter::to_row("{esto no es json").status == wazuh_adapter::ToRowResult::Status::Error,
          "json ilegible -> Error, no Skip (un Skip lo haria invisible)");
}

void test_event_id_determinista() {
    auto a = wazuh_adapter::to_row(kLine5715);
    auto b = wazuh_adapter::to_row(kLine5715);
    check(a.status == wazuh_adapter::ToRowResult::Status::Ok &&
          a.row.event_id == b.row.event_id,
          "D-HOST-1: la misma linea cruda da el mismo event_id (idempotencia por fichero)");
}

}  // namespace

int main() {
    test_5715_mapping();
    test_5402_command();
    test_5501_uid();
    test_533_newline_saneado();
    test_host_id_vacio_lo_rechaza_la_lib();
    test_descartes();
    test_event_id_determinista();

    if (failures != 0) {
        std::cerr << failures << " comprobacion(es) fallidas\n";
        return 1;
    }
    std::cout << "OK — capa pura del adapter de wazuh (host-domain)\n";
    return 0;
}