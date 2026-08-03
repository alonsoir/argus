// zeek-adapter/src/config.cpp

#include "zeek_adapter/config.hpp"

#include <fstream>

#include <nlohmann/json.hpp>

namespace zeek_adapter {

bool load_config(const std::string& path, Config& out, std::string& error) {
    std::ifstream in(path);
    if (!in) {
        error = "no se puede abrir la config: " + path;
        return false;
    }

    nlohmann::json j;
    try {
        in >> j;
    } catch (const nlohmann::json::parse_error& e) {
        error = std::string("config ilegible: ") + e.what();
        return false;
    }

    out.base_dir     = j.value("base_dir", out.base_dir);
    out.node_id      = j.value("node_id", out.node_id);
    out.input_path   = j.value("input_path", out.input_path);
    out.hmac_key_env = j.value("hmac_key_env", out.hmac_key_env);

    if (out.node_id.empty()) {
        error = "node_id vacio: sin el, las filas no convergen con las de aRGus (D2)";
        return false;
    }
    return true;
}

}  // namespace zeek_adapter
