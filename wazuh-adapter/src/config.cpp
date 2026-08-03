// wazuh-adapter/src/config.cpp

#include "wazuh_adapter/config.hpp"

#include <fstream>

#include <nlohmann/json.hpp>

namespace wazuh_adapter {

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
        out.input_path   = j.value("input_path", out.input_path);
        out.hmac_key_env = j.value("hmac_key_env", out.hmac_key_env);

        if (out.base_dir.empty()) {
            error = "base_dir vacio: sin buzon de salida no hay bronce";
            return false;
        }
        return true;
    }

}  // namespace wazuh_adapter