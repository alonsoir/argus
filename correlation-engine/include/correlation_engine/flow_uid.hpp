// flow_uid.hpp — identidad/dedup de flujo del correlation-engine (aRGus NDR, C++20).
// DEBT-FLOWUID-CANONICAL-ENCODING-001 + DEBT-NODEID-CRYPTO-IDENTITY-001 (ADR-052).
//
//   flow_uid = base64_std( BLAKE2b-256( ENCODE(node_id, community_id, window, seq) ) )
//
// Se calcula EN EL ENGINE al insertar nodos en Neo4j, leyendo los tres inputs ya
// disponibles en los Parquet de cada componente. NO viaja en protobuf, NO se computa
// en el sniffer. node_id = NetworkSecurityEvent.originating_node_id (string declarado).
// community_id = NetworkFeatures.community_id (campo 18). window = flow_start_time en micros.
//
// Vectores congelados verificados byte-idénticos contra hashlib.blake2b(digest_size=32):
// crypto_generichash(key=NULL) == BLAKE2b-256 sin clave/salt/personal. NO usar otro digest_size.
#pragma once
#include <sodium.h>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace argus::correlation {

inline constexpr std::string_view kEncodingTag = "argus-flowuid-v1";  // 16B, versión del esquema
static_assert(kEncodingTag.size() == 16);
inline constexpr std::size_t kDigestSize = 32;  // libsodium-compatible; jamás el default 64 de otros libs

namespace detail {
inline void put_be16(std::vector<uint8_t>& b, uint16_t v) { b.push_back(v >> 8); b.push_back(v & 0xFF); }
inline void put_be32(std::vector<uint8_t>& b, uint32_t v) { for (int i = 3; i >= 0; --i) b.push_back((v >> (8*i)) & 0xFF); }
inline void put_be64(std::vector<uint8_t>& b, uint64_t v) { for (int i = 7; i >= 0; --i) b.push_back((v >> (8*i)) & 0xFF); }
}  // namespace detail

// Codificación canónica, self-describing e inyectiva. node_id OPACO (sin normalización).
inline std::vector<uint8_t> encode_flow_input(std::string_view node_id,
                                              std::string_view community_id,
                                              uint64_t flow_start_window,
                                              uint32_t seq_in_window = 0) {
    if (node_id.size() > 0xFFFF || community_id.size() > 0xFFFF)
        throw std::invalid_argument("campo excede uint16 length-prefix");
    std::vector<uint8_t> buf;
    buf.reserve(kEncodingTag.size() + 4 + node_id.size() + community_id.size() + 12);
    buf.insert(buf.end(), kEncodingTag.begin(), kEncodingTag.end());
    detail::put_be16(buf, static_cast<uint16_t>(node_id.size()));
    buf.insert(buf.end(), node_id.begin(), node_id.end());
    detail::put_be16(buf, static_cast<uint16_t>(community_id.size()));
    buf.insert(buf.end(), community_id.begin(), community_id.end());
    detail::put_be64(buf, flow_start_window);
    detail::put_be32(buf, seq_in_window);
    return buf;
}

inline std::string compute_flow_uid(std::string_view node_id,
                                    std::string_view community_id,
                                    uint64_t flow_start_window,
                                    uint32_t seq_in_window = 0) {
    const auto buf = encode_flow_input(node_id, community_id, flow_start_window, seq_in_window);
    std::array<unsigned char, kDigestSize> digest{};
    crypto_generichash(digest.data(), digest.size(), buf.data(), buf.size(), nullptr, 0);
    char b64[sodium_base64_ENCODED_LEN(kDigestSize, sodium_base64_VARIANT_ORIGINAL)];
    sodium_bin2base64(b64, sizeof(b64), digest.data(), digest.size(), sodium_base64_VARIANT_ORIGINAL);
    return std::string(b64);
}

// flow_start_time (protobuf Timestamp: seconds + nanos) -> ventana canónica en micros epoch.
inline uint64_t window_micros(int64_t seconds, int32_t nanos = 0) {
    return static_cast<uint64_t>(seconds) * 1'000'000ULL + static_cast<uint64_t>(nanos) / 1'000ULL;
}

}  // namespace argus::correlation
