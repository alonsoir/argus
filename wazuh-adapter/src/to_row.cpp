// wazuh-adapter/src/to_row.cpp
// aRGus NDR — alerts.json (Wazuh) -> HostDomainV1Row.
//
// ⚠️ ÚNICO FICHERO DEL COMPONENTE QUE TOCA JSON. Deliberado: cambiar de parser (rapidjson
//    /simdjson) es reescribir este fichero y nada más.
//
// Decisiones aplicadas (docs/design/host-domain-contract/host_domain_v1-contract.md):
//   D-HOST-1  event_id acuñado por la lib sobre la línea CRUDA (mint_event_id).
//   D-HOST-2  las 10 listas -> encode_string_list de la lib. data_json = volcado compacto
//             del bag `data` con ORDEN DE CLAVES PRESERVADO (ordered_json), "{}" si no hay.
//   D-HOST-3  newline-guard: full_log/rule_description/command salen de logs y pueden traer
//             \n/\r reales (medido: rule.id 533 netstat es multilínea). Se SANEAN a escape
//             literal (\n/\r de dos chars) para que 1 fila lógica = 1 línea física, en vez
//             de que validate() las rechace y se pierda el evento. Ratificado DAY 242.
//   D-HOST-4  rule_level int (default 0 si ausente; guard de rango DIFERIDO). Comunes de
//             `data` string, "" = ausente. host_id vacío NO se filtra aquí (lo hace validate).

#include "wazuh_adapter/to_row.hpp"

#include <string>

#include <nlohmann/json.hpp>

namespace wazuh_adapter {

namespace {

// ORDERED: preserva el orden de claves que emitió Wazuh en el volcado de data_json
// (fidelidad + determinismo del bronce). El json por defecto de nlohmann ordena alfabético.
using json = nlohmann::ordered_json;

// Saneador de saltos de línea embebidos (D-HOST-3): \r/\n reales -> escape literal de dos
// chars, para no romper el reader getline aguas abajo. \t NO se toca (no rompe getline).
std::string nl(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c == '\r')      out += "\\r";
        else if (c == '\n') out += "\\n";
        else                out += c;
    }
    return out;
}

// Extrae una clave escalar como string. Ausente/null -> ""; string -> tal cual; número u
// otro -> su representación JSON (str() de Python en la referencia). "" = ausente (D-HOST-4).
std::string gs(const json& obj, const char* key) {
    auto it = obj.find(key);
    if (it == obj.end() || it->is_null()) return {};
    if (it->is_string()) return it->get<std::string>();
    return it->dump();
}

// Extrae un array de strings -> JSON-celda canónica vía la lib (D-HOST-2). Ausente -> "[]".
std::string enc(const json& obj, const char* key) {
    std::vector<std::string> items;
    auto it = obj.find(key);
    if (it != obj.end() && it->is_array()) {
        for (const auto& e : *it) {
            items.push_back(e.is_string() ? e.get<std::string>() : e.dump());
        }
    }
    return host_domain_v1::encode_string_list(items);
}

}  // namespace

// ---------------------------------------------------------------------------
ToRowResult ToRowResult::ok(host_domain_v1::HostDomainV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

// ---------------------------------------------------------------------------
// to_row
// ---------------------------------------------------------------------------
ToRowResult to_row(const std::string& raw_line) {
    if (raw_line.empty()) return ToRowResult::skip("linea vacia");

    json e;
    try {
        e = json::parse(raw_line);
    } catch (const json::parse_error& ex) {
        return ToRowResult::error(std::string("json ilegible: ") + ex.what());
    }

    // Sub-objetos (ausentes -> objeto vacío, para que gs/enc devuelvan "" / "[]").
    const json empty_obj = json::object();
    const json empty_arr = json::array();
    const json& rule  = (e.contains("rule")       && e["rule"].is_object())       ? e["rule"]       : empty_obj;
    const json& agent = (e.contains("agent")      && e["agent"].is_object())      ? e["agent"]      : empty_obj;
    const json& data  = (e.contains("data")       && e["data"].is_object())       ? e["data"]       : empty_obj;
    const json& pre   = (e.contains("predecoder") && e["predecoder"].is_object()) ? e["predecoder"] : empty_obj;
    const json& dec   = (e.contains("decoder")    && e["decoder"].is_object())    ? e["decoder"]    : empty_obj;
    const json& mitre = (rule.contains("mitre")   && rule["mitre"].is_object())   ? rule["mitre"]   : empty_obj;

    host_domain_v1::HostDomainV1Row r;

    // -- producidos por nosotros --
    r.schema_version = SCHEMA_VERSION;              // 0  (D-C)
    r.source_sensor  = SOURCE_SENSOR;               // 1  (D-C)
    r.event_id       = host_domain_v1::mint_event_id(raw_line);  // 2  (D-HOST-1, línea cruda)
    r.host_id        = gs(agent, "id");             // 3  (= agent.id, PK; validate rechaza si "")

    // -- copiados de Wazuh --
    r.wazuh_alert_id = gs(e, "id");                 // 4  epoch.offset (procedencia, no PK)
    r.timestamp      = gs(e, "timestamp");          // 5  ISO8601 top-level
    r.agent_id       = gs(agent, "id");             // 6
    r.agent_name     = gs(agent, "name");           // 7
    r.agent_ip       = gs(agent, "ip");             // 8  "" en agente 000
    r.os_hostname    = gs(pre, "hostname");         // 9  "" si no hay predecoder (533/503)
    r.rule_id        = gs(rule, "id");              // 10

    // 11 rule_level: int32, siempre presente en una alerta real; default 0 si faltara
    // (guard de rango DIFERIDO, D-HOST-4).
    r.rule_level = (rule.contains("level") && rule["level"].is_number_integer())
                       ? rule["level"].get<int32_t>()
                       : 0;

    r.rule_description = nl(gs(rule, "description"));  // 12  (saneado)
    r.rule_groups      = enc(rule, "groups");         // 13  [json]
    r.decoder_name     = gs(dec, "name");             // 14
    r.location         = gs(e, "location");           // 15
    r.full_log         = nl(gs(e, "full_log"));       // 16  (saneado; 533 es multilínea)

    // 17 data_json: bag `data` completo, compacto, orden preservado. "{}" si no hay data.
    r.data_json = (!data.empty()) ? data.dump() : "{}";

    // -- comunes extraídas del bag data ("" = ausente, D-HOST-4) --
    r.srcuser = gs(data, "srcuser");                  // 18
    r.dstuser = gs(data, "dstuser");                  // 19
    r.srcip   = gs(data, "srcip");                    // 20  breadcrumb de mov. lateral
    r.srcport = gs(data, "srcport");                  // 21
    r.uid     = gs(data, "uid");                      // 22
    r.command = nl(gs(data, "command"));              // 23  (saneado)

    // -- MITRE ATT&CK (normalizado por regla aguas abajo, D-HOST-2) --
    r.mitre_ids        = enc(mitre, "id");            // 24  [json]
    r.mitre_tactics    = enc(mitre, "tactic");        // 25  [json]
    r.mitre_techniques = enc(mitre, "technique");     // 26  [json]

    // -- cumplimiento (capturado aunque los nodos Control sean P4 diferido) --
    r.pci_dss     = enc(rule, "pci_dss");             // 27  [json]
    r.gdpr        = enc(rule, "gdpr");                // 28  [json]
    r.hipaa       = enc(rule, "hipaa");              // 29  [json]
    r.nist_800_53 = enc(rule, "nist_800_53");        // 30  [json]
    r.tsc         = enc(rule, "tsc");                // 31  [json]
    r.gpg13       = enc(rule, "gpg13");              // 32  [json]
    // col 33 (HMAC) la calcula serialize(); no vive en el Row.

    return ToRowResult::ok(std::move(r));
}

}  // namespace wazuh_adapter