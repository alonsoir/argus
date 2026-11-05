// libs/protegidos/include/protegidos/rangos.hpp (antes firewall-acl-agent/include/firewall/ddos_protegidos.hpp; libs/protegidos, ADR-060 F-B)
// [PROTEGIDOS-D300] rangos protegidos: un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango protegido se registra
// como ALERTA_PROTEGIDO y nunca se convierte en bloqueo automatico; ningun camino lo mete en el blacklist.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen SOLO del manifiesto firmado verificado
// (protegidos/manifiesto.hpp). Fuera ddos_protegidos de firewall.json y el defecto RFC 1918 de DAY300: con el
// candado (D6), sin manifiesto verificado no hay bloqueo real del que proteger. La barrera protege por IP siempre
// (D-G). Funciones puras, sin JSON ni red.
#pragma once
#include "argus/ip_cidr_validator.hpp"
#include <arpa/inet.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <ostream>
#include <sstream>  // [PROTEGIDOS-D300]
#include <string>
#include <vector>

namespace argus::protegidos {

// [PROTEGIDOS-MANIFIESTO-D318] INFRAESTRUCTURA (ADR-060 D1): el plano de control de aRGus (etcd, etcd-server, Vault).
enum class CategoriaProtegida : uint8_t { NINGUNA = 0, DMZ = 1, INTRANET = 2, EXTERNOS_CRITICOS = 3, INFRAESTRUCTURA = 4 };

inline const char* nombre_categoria(CategoriaProtegida c) {
    switch (c) {
        case CategoriaProtegida::DMZ: return "dmz";
        case CategoriaProtegida::INTRANET: return "intranet";
        case CategoriaProtegida::EXTERNOS_CRITICOS: return "externos_criticos";
        case CategoriaProtegida::INFRAESTRUCTURA: return "infraestructura";
        default: return "ninguna";
    }
}

struct RangoProtegido {
    bool v6 = false;
    std::array<uint8_t, 16> red{};
    int prefijo = 0;
    CategoriaProtegida cat = CategoriaProtegida::NINGUNA;
    std::string texto;
};

namespace detalle_protegidos {

inline bool a_bytes(const std::string& ip, bool& v6, std::array<uint8_t, 16>& b) {
    b.fill(0);
    in_addr a4{};
    in6_addr a6{};
    if (inet_pton(AF_INET, ip.c_str(), &a4) == 1) {
        v6 = false;
        std::memcpy(b.data(), &a4, 4);
        return true;
    }
    if (inet_pton(AF_INET6, ip.c_str(), &a6) == 1) {
        v6 = true;
        std::memcpy(b.data(), &a6, 16);
        return true;
    }
    return false;
}

inline bool coincide(const std::array<uint8_t, 16>& ip, const std::array<uint8_t, 16>& red, int prefijo) {
    const std::size_t completos = static_cast<std::size_t>(prefijo / 8);
    for (std::size_t i = 0; i < completos; ++i) {
        if (ip[i] != red[i]) return false;
    }
    const int resto = prefijo % 8;
    if (resto == 0) return true;
    const uint8_t mascara = static_cast<uint8_t>(0xFFu << (8 - resto));
    return (ip[completos] & mascara) == (red[completos] & mascara);
}

// Para el log: sin caracteres de control (una entrada invalida del JSON no puede inyectar lineas).
inline std::string saneado(const std::string& s) {
    std::string o;
    for (unsigned char c : s) {
        if (o.size() >= 64) {
            o += "...";
            break;
        }
        o += (c >= 0x20 && c < 0x7f) ? static_cast<char>(c) : '?';
    }
    return o;
}

}  // namespace detalle_protegidos

inline bool parsear_rango(const std::string& cidr, CategoriaProtegida cat, RangoProtegido& out) {
    if (!::argus::is_valid_ip_cidr(cidr)) return false;
    const auto barra = cidr.find('/');
    const std::string ip = (barra == std::string::npos) ? cidr : cidr.substr(0, barra);
    RangoProtegido r;
    if (!detalle_protegidos::a_bytes(ip, r.v6, r.red)) return false;
    r.prefijo = r.v6 ? 128 : 32;
    if (barra != std::string::npos) r.prefijo = std::stoi(cidr.substr(barra + 1));
    // Normaliza la red: bits de host a cero (192.168.100.77/24 -> 192.168.100.0/24).
    for (std::size_t i = 0; i < r.red.size(); ++i) {
        const int bit_ini = static_cast<int>(i) * 8;
        if (bit_ini >= r.prefijo) {
            r.red[i] = 0;
        } else if (bit_ini + 8 > r.prefijo) {
            r.red[i] &= static_cast<uint8_t>(0xFFu << (8 - (r.prefijo - bit_ini)));
        }
    }
    r.cat = cat;
    r.texto = cidr;
    out = r;
    return true;
}

struct RangosProtegidos {
    std::vector<RangoProtegido> rangos;

    // Categoria del primer rango que contiene la IP; NINGUNA si ninguno o si la IP no es valida.
    CategoriaProtegida categoria_de(const std::string& ip) const {
        bool v6 = false;
        std::array<uint8_t, 16> b{};
        if (!detalle_protegidos::a_bytes(ip, v6, b)) return CategoriaProtegida::NINGUNA;
        for (const auto& r : rangos) {
            if (r.v6 == v6 && detalle_protegidos::coincide(b, r.red, r.prefijo)) return r.cat;
        }
        return CategoriaProtegida::NINGUNA;
    }
};

}  // namespace argus::protegidos
