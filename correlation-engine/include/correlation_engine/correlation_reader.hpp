// correlation_reader.hpp — lector resiliente de bronce (contrato correlation_v1).
// Responsabilidad: validar HMAC por fila y parsear. Descarta (no lanza) filas
// corruptas, truncadas (append no-atómico del writer) o con HMAC inválido (tampering).
#pragma once
#include "correlation_engine/correlation_record.hpp"
#include <optional>
#include <string>
#include <vector>
#include <cstdint>

namespace argus::correlation {

    // Valida HMAC-SHA256(key, body) contra la última columna y parsea las 19 columnas.
    // Devuelve nullopt si: nº de columnas != 19, HMAC inválido, o campo numérico ilegible.
    // 'hmac_key' = 32 bytes crudos (los mismos que el writer decodifica de su hex de 64).
    std::optional<CorrelationRecord> parse_and_verify(const std::string& line,
                                                      const std::vector<uint8_t>& hmac_key);

}  // namespace argus::correlation