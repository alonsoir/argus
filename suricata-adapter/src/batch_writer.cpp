// suricata-adapter/src/batch_writer.cpp

#include "suricata_adapter/batch_writer.hpp"

#include <cstdio>
#include <ctime>
#include <utility>

namespace suricata_adapter {

BatchWriter::BatchWriter(std::string base_dir, std::string source_sensor)
    : base_dir_(std::move(base_dir)), source_sensor_(std::move(source_sensor)) {}

BatchWriter::~BatchWriter() {
    if (out_.is_open()) out_.close();   // .tmp sin renombrar = fallo visible
}

bool BatchWriter::open() {
    if (out_.is_open()) return false;

    // Basename idéntico en forma al del oráculo: <sensor>-%Y-%m-%d-%H%M%S.csv
    // Este es el ÚNICO uso del reloj en todo el componente; to_row es puro.
    const std::time_t now = std::time(nullptr);
    std::tm tm{};
    localtime_r(&now, &tm);
    char stamp[32];
    std::strftime(stamp, sizeof(stamp), "%Y-%m-%d-%H%M%S", &tm);

    final_path_ = base_dir_ + "/" + source_sensor_ + "-" + stamp + ".csv";
    tmp_path_   = final_path_ + ".tmp";

    out_.open(tmp_path_, std::ios::out | std::ios::trunc);
    return out_.is_open();
}

bool BatchWriter::write_line(const std::string& line) {
    if (!out_.is_open()) return false;
    out_ << line << "\n";               // sin cabecera: el bronce no la tiene
    if (!out_) return false;
    ++lines_written_;
    return true;
}

bool BatchWriter::close() {
    if (!out_.is_open()) return false;
    out_.flush();
    const bool stream_ok = static_cast<bool>(out_);
    out_.close();
    if (!stream_ok) return false;
    return std::rename(tmp_path_.c_str(), final_path_.c_str()) == 0;
}

}  // namespace suricata_adapter
