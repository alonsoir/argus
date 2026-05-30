// community_id.hpp — Community ID Flow Hashing v1 (Corelight spec)
// https://github.com/corelight/community-id-spec
// DAY 170 — clave de join cross-tool (aRGus/Suricata/Zeek/Wazuh).
// Función pura de la 5-tupla. SHA1 vía EVP (no SHA1() deprecated bajo -Werror).
#pragma once
#include <cstdint>
#include <optional>
#include <string>

namespace sniffer::flow {

    // Devuelve "1:" + base64(sha1(seed‖5-tupla-canónica)) idéntico a Suricata/Zeek.
    // saddr/daddr: IP en texto (IPv4 dotted o IPv6). sport/dport: host order.
    // proto: número IANA (TCP=6, UDP=17). seed: uint16, default 0 (las 4 herramientas).
    // nullopt si la IP no parsea o el proto no está soportado (ICMP diferido) -> caller guarda "".
    std::optional<std::string> compute_community_id(
        const std::string& saddr,
        const std::string& daddr,
        uint16_t sport,
        uint16_t dport,
        uint8_t  proto,
        uint16_t seed = 0);

}  // namespace sniffer::flow