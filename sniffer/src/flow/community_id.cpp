#include "flow/community_id.hpp"

#include <arpa/inet.h>   // inet_pton, htons
#include <openssl/evp.h> // EVP_Digest, EVP_sha1, EVP_EncodeBlock

#include <array>
#include <cstring>
#include <vector>

namespace sniffer::flow {

namespace {

constexpr uint8_t kProtoTCP = 6;
constexpr uint8_t kProtoUDP = 17;

// Parsea IP a su forma binaria en orden de red (4 bytes v4 / 16 bytes v6).
std::optional<std::vector<uint8_t>> ip_to_bytes(const std::string& ip) {
    std::array<uint8_t, 16> buf{};
    if (inet_pton(AF_INET, ip.c_str(), buf.data()) == 1)
        return std::vector<uint8_t>(buf.begin(), buf.begin() + 4);
    if (inet_pton(AF_INET6, ip.c_str(), buf.data()) == 1)
        return std::vector<uint8_t>(buf.begin(), buf.begin() + 16);
    return std::nullopt;
}

void push_u16_be(std::vector<uint8_t>& b, uint16_t v) {
    b.push_back(static_cast<uint8_t>(v >> 8));
    b.push_back(static_cast<uint8_t>(v & 0xFF));
}

}  // namespace

std::optional<std::string> compute_community_id(
    const std::string& saddr,
    const std::string& daddr,
    uint16_t sport,
    uint16_t dport,
    uint8_t  proto,
    uint16_t seed) {

    // Primer corte: solo protocolos con puertos. ICMP/otros -> diferido.
    if (proto != kProtoTCP && proto != kProtoUDP)
        return std::nullopt;

    auto sb = ip_to_bytes(saddr);
    auto db = ip_to_bytes(daddr);
    if (!sb || !db || sb->size() != db->size())
        return std::nullopt;

    // Orden canónico: (ip,puerto) menor primero. Comparar IP como bytes; si
    // empata, por puerto. El puerto VIAJA con su IP en el swap (catch de Kimi).
    const std::vector<uint8_t>* lo_ip = &*sb;
    const std::vector<uint8_t>* hi_ip = &*db;
    uint16_t lo_port = sport, hi_port = dport;
    int cmp = std::memcmp(sb->data(), db->data(), sb->size());
    if (cmp > 0 || (cmp == 0 && sport > dport)) {
        std::swap(lo_ip, hi_ip);
        std::swap(lo_port, hi_port);
    }

    // Buffer: seed(2 BE) ‖ ip_lo ‖ ip_hi ‖ proto(1) ‖ pad(1=0x00) ‖ port_lo(2 BE) ‖ port_hi(2 BE)
    std::vector<uint8_t> buf;
    buf.reserve(2 + lo_ip->size() + hi_ip->size() + 2 + 4);
    push_u16_be(buf, seed);
    buf.insert(buf.end(), lo_ip->begin(), lo_ip->end());
    buf.insert(buf.end(), hi_ip->begin(), hi_ip->end());
    buf.push_back(proto);
    buf.push_back(0x00);
    push_u16_be(buf, lo_port);
    push_u16_be(buf, hi_port);

    // SHA1 vía EVP (SHA1() está deprecated en OpenSSL 3 -> -Werror lo rechaza).
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int md_len = 0;
    if (EVP_Digest(buf.data(), buf.size(), md, &md_len, EVP_sha1(), nullptr) != 1)
        return std::nullopt;

    // base64 estándar con padding (EVP_EncodeBlock, single-shot, sin saltos de línea).
    std::array<char, 64> b64{};
    int n = EVP_EncodeBlock(reinterpret_cast<unsigned char*>(b64.data()), md, static_cast<int>(md_len));
    if (n <= 0)
        return std::nullopt;

    return std::string("1:") + std::string(b64.data(), static_cast<size_t>(n));
}

}  // namespace sniffer::flow