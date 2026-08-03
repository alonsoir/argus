// zeek-adapter/src/main.cpp
// aRGus NDR — adapter de zeek, modo LOTE.
//
// Pipeline: linea JSONL -> to_row() -> serialize() -> BatchWriter
//                                      ^^^^^^^^^^^
//                          libs/correlation-v1, notario único (P3).
//                          Lo que validate() rechaza, serialize() NO lo emite.
//
// Contadores RUIDOSOS al final (D5): un descarte silencioso es indistinguible de
// un bug. Si skipped y written no cuadran con lo medido en el eve.json, se ve aquí.

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <sodium.h>

#include <correlation_v1/correlation_v1.hpp>

#include "zeek_adapter/batch_writer.hpp"
#include "zeek_adapter/config.hpp"
#include "zeek_adapter/to_row.hpp"

namespace {

// 64 chars hex -> 32 bytes. La lib recibe la clave YA decodificada (es INPUT puro).
bool hex_to_key(const std::string& hex, std::vector<uint8_t>& out, std::string& error) {
    if (hex.size() != 64) {
        error = "la clave HMAC debe tener 64 chars hex, tiene " + std::to_string(hex.size());
        return false;
    }
    out.assign(32, 0);
    for (size_t i = 0; i < 32; ++i) {
        auto nibble = [&](char c, int& v) {
            if (c >= '0' && c <= '9') { v = c - '0';        return true; }
            if (c >= 'a' && c <= 'f') { v = c - 'a' + 10;   return true; }
            if (c >= 'A' && c <= 'F') { v = c - 'A' + 10;   return true; }
            return false;
        };
        int hi = 0, lo = 0;
        if (!nibble(hex[i * 2], hi) || !nibble(hex[i * 2 + 1], lo)) {
            error = "caracter no hexadecimal en la clave HMAC";
            return false;
        }
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    if (sodium_init() < 0) {
        std::cerr << "[FATAL] sodium_init fallo\n";
        return 2;
    }

    if (argc < 2) {
        std::cerr << "uso: zeek_adapter <config.json> [entrada.json]\n";
        return 2;
    }

    zeek_adapter::Config cfg;
    std::string error;
    if (!zeek_adapter::load_config(argv[1], cfg, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }
    if (argc >= 3) cfg.input_path = argv[2];

    const char* key_hex = std::getenv(cfg.hmac_key_env.c_str());
    if (key_hex == nullptr) {
        std::cerr << "[FATAL] variable de entorno no definida: " << cfg.hmac_key_env << "\n";
        return 2;
    }
    std::vector<uint8_t> hmac_key;
    if (!hex_to_key(key_hex, hmac_key, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }

    std::ifstream in(cfg.input_path);
    if (!in) {
        std::cerr << "[FATAL] no se puede abrir la entrada: " << cfg.input_path << "\n";
        return 2;
    }

    zeek_adapter::BatchWriter writer(cfg.base_dir, zeek_adapter::CORRELATION_SOURCE_SENSOR);
    if (!writer.open()) {
        std::cerr << "[FATAL] no se puede abrir el fichero de salida en " << cfg.base_dir << "\n";
        return 2;
    }

    // Zeek conn.log: capturar la linea `#fields` -> indice; saltar el resto del
    // preambulo. `#fields` puede reaparecer (logs rotados/concatenados) -> se
    // reconstruye. Fila de datos sin `#fields` previo = fatal (no hay esquema).
    zeek_adapter::ConnFieldIndex fields;
    bool have_fields = false;

    uint64_t lineno = 0, total = 0, written = 0, skipped = 0, to_row_err = 0, serialize_err = 0;
    std::string line;
    while (std::getline(in, line)) {
        ++lineno;

        if (!line.empty() && line[0] == '#') {
            if (line.rfind("#fields", 0) == 0) {
                fields = zeek_adapter::parse_conn_fields(line);
                have_fields = !fields.empty();
            }
            continue;                        // preambulo: no cuenta como fila
        }
        if (line.empty()) continue;

        if (!have_fields) {
            std::cerr << "[FATAL] fila de datos en la linea " << lineno
                      << " sin un `#fields` previo valido\n";
            return 2;
        }

        ++total;
        auto tr = zeek_adapter::to_row(line, fields, cfg.node_id);

        if (tr.status == zeek_adapter::ToRowResult::Status::Skip) {
            ++skipped;
            continue;
        }
        if (tr.status == zeek_adapter::ToRowResult::Status::Error) {
            ++to_row_err;
            std::cerr << "[WARN] to_row linea " << lineno << ": " << tr.reason << "\n";
            continue;
        }

        auto sr = correlation_v1::serialize(tr.row, hmac_key);
        if (!sr) {
            ++serialize_err;
            std::cerr << "[WARN] serialize rechazo linea " << lineno << ": " << sr.error << "\n";
            continue;
        }
        if (!writer.write_line(sr.line)) {
            std::cerr << "[FATAL] fallo de escritura en " << writer.tmp_path() << "\n";
            return 2;
        }
        ++written;
    }

    if (!writer.close()) {
        std::cerr << "[FATAL] fallo al cerrar/renombrar " << writer.tmp_path() << "\n";
        return 2;
    }

    // D5 — contadores ruidosos. Sin esto, un descarte masivo pasaría por exito.
    std::cout << "[" << zeek_adapter::CORRELATION_SOURCE_SENSOR << "-adapter]"
              << " leidas="        << total
              << " escritas="      << written
              << " descartadas="   << skipped
              << " err_to_row="    << to_row_err
              << " err_serialize=" << serialize_err
              << "\n salida: "     << writer.final_path() << "\n";

    return (written > 0) ? 0 : 1;   // 0 filas es fallo, no exito silencioso
}
