// community_id_log.hpp — telemetría de paridad cross-sensor (DAY 171, test #1)
// Gateado por env var ARGUS_CID_CROSSCHECK: OFF en hot path (RSS #5), ON para el crosscheck.
// NO recalcula: recibe el cid ya sellado en el .pb + la 5-tupla que lo originó.
// Escribe TSV a fichero dedicado (ARGUS_CID_CROSSCHECK_PATH), una línea por flujo.
#pragma once
#include <cstdint>
#include <string>
namespace sniffer::flow {
    // Lee ARGUS_CID_CROSSCHECK una vez (thread-safe). true si == "1".
    bool cid_crosscheck_enabled();
    // Emite: cid \t saddr \t daddr \t sport \t dport \t proto \t ts_emision_ns
    // Llamar SOLO tras un set_community_id() con valor (no en el "" diferido).
    void log_community_id_emission(
        const std::string& cid,
        const std::string& saddr,
        const std::string& daddr,
        uint16_t sport,
        uint16_t dport,
        uint8_t  proto);
}  // namespace sniffer::flow