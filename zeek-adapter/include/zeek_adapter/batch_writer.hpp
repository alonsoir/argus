// zeek-adapter/include/zeek_adapter/batch_writer.hpp
// aRGus NDR — capa [bytes -> disco] del adapter.
//
// POR QUÉ NO SE REUTILIZA CorrelationWriter: vive en ml-detector y arrastra protobuf
// (correlation_v1.hpp, corte en tres capas). Y su complejidad —rotación por tiempo
// absoluto, mutex, reloj— existe para un productor CONTINUO. Este adapter es de LOTE:
// un fichero por ejecución. Copiar aquella máquina sería complejidad sin demanda.
//
// Lo que SÍ se copia es lo que importa: escritura atómica .tmp -> rename, para que
// ningún consumidor vea jamás un fichero a medio escribir.
#pragma once

#include <cstdint>
#include <fstream>
#include <string>

namespace zeek_adapter {

class BatchWriter {
public:
    BatchWriter(std::string base_dir, std::string source_sensor);
    ~BatchWriter();

    BatchWriter(const BatchWriter&) = delete;
    BatchWriter& operator=(const BatchWriter&) = delete;

    // Abre <base_dir>/<source_sensor>-%Y-%m-%d-%H%M%S.csv.tmp
    [[nodiscard]] bool open();

    // Escribe una línea ya serializada por libs/correlation-v1 (cols 0-18).
    [[nodiscard]] bool write_line(const std::string& line);

    // Cierra y RENOMBRA .tmp -> definitivo. Hasta aquí el fichero no existe
    // para nadie. Si no se llama, el .tmp se queda: fallo visible, no silencioso.
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

}  // namespace zeek_adapter
