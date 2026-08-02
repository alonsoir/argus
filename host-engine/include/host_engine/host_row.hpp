#pragma once
#include <string>
#include <vector>
#include <cstdint>

namespace host_engine {

// Una fila del oro host_domain_v1 (34 cols; solo los campos que el grafo usa).
struct HostRow {
    std::string event_id;
    std::string host_id;
    std::string agent_name;
    std::string agent_ip;
    std::string os_hostname;
    std::string timestamp;
    std::string rule_id;
    std::int32_t level = 0;
    std::string rule_description;
    std::string decoder;
    std::string location;
    std::string full_log;
    std::string srcuser, dstuser, srcip, srcport, uid, command;
    std::string data_json;
    std::string wazuh_alert_id;
    std::string groups_json;    // JSON crudo, prop de Rule
    std::string tactics_json;   // JSON crudo, prop de Rule
    std::string mitre_ids_json;
    std::string mitre_techniques_json;
};

// Par (id, name) resultado de zipear mitre_ids ↔ mitre_techniques.
struct Technique {
    std::string id;
    std::string name;
};

// Parsea una lista JSON de strings simple: ["a","b"] -> {"a","b"}.
// Suficiente para el encode_string_list del converter (JSON compacto, sin anidar).
std::vector<std::string> parse_json_string_list(const std::string& json);

// Zip alineado de mitre_ids ↔ mitre_techniques. Si las longitudes difieren,
// devuelve vacío y deja la discrepancia en `mismatch` (fail-loud, no inventa).
std::vector<Technique> zip_techniques(const std::string& ids_json,
                                      const std::string& techniques_json,
                                      bool& mismatch);

}  // namespace host_engine