// wazuh-adapter/include/wazuh_adapter/config.hpp
// aRGus NDR — configuración del adapter de wazuh (host-domain).
#pragma once

#include <string>

namespace wazuh_adapter {

    struct Config {
        // Buzón PROPIO del bronce host, SEPARADO del /vagrant/logs/correlation de red
        // (invariante: Wazuh = host-domain, su ledger/grafo/BD son un par aparte). DAY 242.
        std::string base_dir = "/vagrant/logs/host-domain";

        // Entrada: alerts.json del manager (JSON por línea). El fichero es LIVE y rota
        // (DEBT-HOST-DOMAIN-P2); el watermark por (inode,offset) es pieza posterior. Para el
        // camino reproducible del paper (destroy&up) se lee el fichero fresco entero.
        std::string input_path = "/var/ossec/logs/alerts/alerts.json";

        // Clave HMAC de 64 chars hex -> 32 bytes. COMPARTIDA con la red (decisión por
        // sencillez; el ledger/loader host son par separado y cualquier clave sella igual).
        std::string hmac_key_env = "ARGUS_BRONZE_HMAC_KEY_HEX";
    };

    // A diferencia de suricata/zeek NO hay node_id: la identidad de host viaja DENTRO de la
    // alerta (host_id = agent.id), no es un parámetro de observación de la config.
    //
    // Devuelve false y deja `error` si el fichero falta o es ilegible.
    [[nodiscard]] bool load_config(const std::string& path, Config& out, std::string& error);

}  // namespace wazuh_adapter