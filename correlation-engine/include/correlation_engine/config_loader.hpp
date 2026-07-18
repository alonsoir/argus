#pragma once
// correlation-engine/include/correlation_engine/config_loader.hpp
// DAY 202 — esqueleto incremental (calca ml_detector_config.json/ConfigLoader).
// Solo el bloque "bronze" se consume hoy (DEBT-CONFIG-BRONZE-HARDCODE-001, mitad
// reader). component/node_id/cluster_name se leen para logging informativo.
// profiles/etcd quedan DECLARADOS en el JSON para crecimiento incremental — nada
// del codigo los exige todavia.
#include <string>

namespace argus::correlation {

struct CorrelationEngineConfig {
    std::string component_name;
    std::string component_version;
    std::string node_id;
    std::string cluster_name;

    struct {
        std::string root_dir;      // p.ej. /vagrant/logs/correlation (PLANO, multi-sensor)
        std::string file_pattern;  // strftime, p.ej. "%Y-%m-%d.csv"
    } bronze;
};

// Lee correlation_engine.json. Lanza std::runtime_error si el fichero no existe,
// el JSON es invalido, o falta bronze.root_dir (unico campo requerido hoy).
CorrelationEngineConfig load_correlation_engine_config(const std::string& config_path);

} // namespace argus::correlation
