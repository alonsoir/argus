#include "host_engine/host_row.hpp"

namespace host_engine {

// Parser mínimo para ["a","b","c"] con posibles comillas escapadas \".
// No es un parser JSON general: asume el formato que emite encode_string_list.
std::vector<std::string> parse_json_string_list(const std::string& json) {
    std::vector<std::string> out;
    std::size_t i = 0, n = json.size();
    auto skip_ws = [&] { while (i < n && (json[i]==' '||json[i]=='\t'||json[i]=='\n'||json[i]=='\r')) ++i; };
    skip_ws();
    if (i >= n || json[i] != '[') return out;   // vacío o "[]" o basura -> lista vacía
    ++i;
    skip_ws();
    if (i < n && json[i] == ']') return out;     // "[]"
    while (i < n) {
        skip_ws();
        if (i >= n || json[i] != '"') break;     // esperábamos apertura de string
        ++i;
        std::string s;
        while (i < n && json[i] != '"') {
            if (json[i] == '\\' && i + 1 < n) {   // \" \\ etc: copia el siguiente literal
                s.push_back(json[i+1]);
                i += 2;
            } else {
                s.push_back(json[i]);
                ++i;
            }
        }
        if (i < n) ++i;                           // consume la comilla de cierre
        out.push_back(s);
        skip_ws();
        if (i < n && json[i] == ',') { ++i; continue; }
        if (i < n && json[i] == ']') break;
        break;
    }
    return out;
}

std::vector<Technique> zip_techniques(const std::string& ids_json,
                                      const std::string& techniques_json,
                                      bool& mismatch) {
    auto ids = parse_json_string_list(ids_json);
    auto names = parse_json_string_list(techniques_json);
    mismatch = (ids.size() != names.size());
    std::vector<Technique> out;
    if (mismatch) return out;                     // fail-loud: no inventa alineación
    out.reserve(ids.size());
    for (std::size_t k = 0; k < ids.size(); ++k)
        out.push_back({ids[k], names[k]});
    return out;
}

}  // namespace host_engine