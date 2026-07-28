// zeek-adapter/include/zeek_adapter/config.hpp
// aRGus NDR — configuración del adapter de zeek.
#pragma once

#include <string>

namespace zeek_adapter {

struct Config {
    // Buzón PLANO del bronce, compartido con el resto de productores.
    std::string base_dir = "/vagrant/logs/correlation";

    // D2 — punto de OBSERVACIÓN, no el host. Dos sensores con el mismo node_id
    // declaran que observan la misma interfaz; si observan interfaces distintas es
    // CORRECTO que generen subgrafos distintos.
    //
    // ⚠️ MEDIDO DAY 226: el node_id real que emite aRGus hoy es "cpp_sniffer_v33_day12",
    //    una etiqueta de VERSIÓN del sniffer. Para converger hay que poner aquí ese
    //    mismo valor. Es incorrecto semánticamente y está registrado como deuda.
    std::string node_id;

    // Entrada: eve.json (JSONL) a procesar en lote.
    std::string input_path;

    // Clave HMAC de 64 chars hex -> 32 bytes.
    // ⚠️ DEBE SER LA MISMA QUE USA aRGus o el lector de aguas abajo rechazará estas
    //    filas. correlation_v1.hpp dice: "ARGUS_BRONZE_HMAC_KEY_HEX en test,
    //    etcd-server en el adapter". Hoy: variable de entorno.
    std::string hmac_key_env = "ARGUS_BRONZE_HMAC_KEY_HEX";
};

// Carga desde JSON. Devuelve false y deja `error` si el fichero falta o es ilegible.
[[nodiscard]] bool load_config(const std::string& path, Config& out, std::string& error);

}  // namespace zeek_adapter
