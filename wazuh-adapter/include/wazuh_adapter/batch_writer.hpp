// wazuh-adapter/include/wazuh_adapter/batch_writer.hpp
// aRGus NDR — capa [bytes -> disco] del adapter de wazuh.
//
// Calcado del batch_writer de suricata/zeek: escritura atómica .tmp -> rename (ningún
// consumidor ve un fichero a medio escribir), un fichero por ejecución (modo LOTE). El
// único uso del reloj de todo el componente vive aquí; to_row es puro.
#pragma once

#include <cstdint>
#include <fstream>
#include <string>

namespace wazuh_adapter {

    class BatchWriter {
    public:
        BatchWriter(std::string base_dir, std::string source_sensor);
        ~BatchWriter();

        BatchWriter(const BatchWriter&) = delete;
        BatchWriter& operator=(const BatchWriter&) = delete;

        // Abre <base_dir>/<source_sensor>-%Y-%m-%d-%H%M%S.csv.tmp
        [[nodiscard]] bool open();

        // Escribe una línea ya serializada por libs/host-domain-v1 (cols 0-33).
        [[nodiscard]] bool write_line(const std::string& line);

        // Cierra y RENOMBRA .tmp -> definitivo. Si no se llama, el .tmp se queda: fallo visible.
        [[nodiscard]] bool close();

        uint64_t lines_written() const noexcept { return lines_written_; }
        const std::string& tmp_path()   const noexcept { return tmp_path_; }
        const std::string& final_path() const noexcept { return final_path_; }

    private:
        std::string base_dir_;
        std::string source_sensor_;
        std::string tmp_path_;
        std::string final_path_;
        std::ofstream out_;
        uint64_t lines_written_ = 0;
    };

}  // namespace wazuh_adapter