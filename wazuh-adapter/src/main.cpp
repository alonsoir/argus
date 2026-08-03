// wazuh-adapter/src/main.cpp
// aRGus NDR — adapter de wazuh (host-domain), modo LOTE.
//
// Pipeline: linea alerts.json -> to_row() -> serialize() -> BatchWriter
//                                            ^^^^^^^^^^^
//                          libs/host-domain-v1, notario único (P3).
//                          Lo que validate() rechaza (host_id vacío, \n embebido),
//                          serialize() NO lo emite -> cuenta como err_serialize.
//
// Contadores RUIDOSOS al final (D5): un descarte silencioso es indistinguible de un bug.
// A diferencia de suricata/zeek NO llama a sodium_init(): mint_event_id vive en la lib y lo
// hace por su cuenta (idempotente); este binario no toca libsodium directamente.

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <host_domain_v1/host_domain_v1.hpp>

#include "wazuh_adapter/batch_writer.hpp"
#include "wazuh_adapter/config.hpp"
#include "wazuh_adapter/to_row.hpp"

namespace {

// 64 chars hex -> 32 bytes. La lib recibe la clave YA decodificada (input puro).
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
    if (argc < 2) {
        std::cerr << "uso: wazuh_adapter <config.json> [entrada.json]\n";
        return 2;
    }

    wazuh_adapter::Config cfg;
    std::string error;
    if (!wazuh_adapter::load_config(argv[1], cfg, error)) {
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

    wazuh_adapter::BatchWriter writer(cfg.base_dir, wazuh_adapter::SOURCE_SENSOR);
    if (!writer.open()) {
        std::cerr << "[FATAL] no se puede abrir el fichero de salida en " << cfg.base_dir << "\n";
        return 2;
    }

    uint64_t total = 0, written = 0, skipped = 0, to_row_err = 0, serialize_err = 0;
    std::string line;
    while (std::getline(in, line)) {
        ++total;
        auto tr = wazuh_adapter::to_row(line);

        if (tr.status == wazuh_adapter::ToRowResult::Status::Skip) {
            ++skipped;
            continue;
        }
        if (tr.status == wazuh_adapter::ToRowResult::Status::Error) {
            ++to_row_err;
            std::cerr << "[WARN] to_row linea " << total << ": " << tr.reason << "\n";
            continue;
        }

        auto sr = host_domain_v1::serialize(tr.row, hmac_key);
        if (!sr) {
            ++serialize_err;
            std::cerr << "[WARN] serialize rechazo linea " << total << ": " << sr.error << "\n";
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

    // D5 — contadores ruidosos.
    std::cout << "[" << wazuh_adapter::SOURCE_SENSOR << "-adapter]"
              << " leidas="        << total
              << " escritas="      << written
              << " descartadas="   << skipped
              << " err_to_row="    << to_row_err
              << " err_serialize=" << serialize_err
              << "\n salida: "     << writer.final_path() << "\n";

    return (written > 0) ? 0 : 1;   // 0 filas es fallo, no exito silencioso
}