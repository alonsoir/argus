// correlation-engine/src/config_loader.cpp
// DAY 202 — DEBT-CONFIG-BRONZE-HARDCODE-001 (mitad reader).
#include "correlation_engine/config_loader.hpp"

#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>

namespace argus::correlation {

CorrelationEngineConfig load_correlation_engine_config(const std::string& config_path) {
    std::ifstream file(config_path);
    if (!file.is_open()) {
        throw std::runtime_error("no se puede abrir config: " + config_path);
    }

    nlohmann::json j;
    try {
        file >> j;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("JSON invalido en " + config_path + ": " + e.what());
    }

    CorrelationEngineConfig cfg;

    // Informativo hoy — ninguna logica depende de ellos todavia.
    if (j.contains("component") && j["component"].contains("name")) {
        cfg.component_name = j["component"]["name"].get<std::string>();
    }
    if (j.contains("component") && j["component"].contains("version")) {
        cfg.component_version = j["component"]["version"].get<std::string>();
    }
    if (j.contains("node_id")) {
        cfg.node_id = j["node_id"].get<std::string>();
    }
    if (j.contains("cluster_name")) {
        cfg.cluster_name = j["cluster_name"].get<std::string>();
    }

    // bronze: unico bloque REQUERIDO — razon de ser de este loader.
    if (!j.contains("bronze") || !j["bronze"].contains("root_dir")) {
        throw std::runtime_error("config invalida: falta bronze.root_dir en " + config_path);
    }
    cfg.bronze.root_dir = j["bronze"]["root_dir"].get<std::string>();
    cfg.bronze.file_pattern = j["bronze"].value("file_pattern", std::string("%Y-%m-%d.csv"));

    // profiles / etcd: NO parseados todavia — ver _refactor_notes en el JSON.

    return cfg;
}

} // namespace argus::correlation
