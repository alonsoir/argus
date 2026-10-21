// ddos_protegidos.hpp
// [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001: rangos protegidos de la cabeza DDoS.
// Un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango protegido (dmz, intranet, externos_criticos) se
// registra como ALERTA_PROTEGIDO y nunca se convierte en bloqueo automatico.
// Si no queda ningun rango valido (bloque ausente, listas vacias o todas las entradas invalidas) se
// protegen por defecto los rangos privados RFC 1918 y fc00::/7 como intranet (decision de Alonso DAY300:
// un descuido de configuracion no puede acabar bloqueando la intranet o la DMZ).
// Funciones puras, sin JSON ni red: config_loader extrae las listas y las pasa aqui.
#pragma once
#include "firewall/ip_cidr_validator.hpp"
#include <arpa/inet.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <ostream>
#include <sstream>  // [PROTEGIDOS-D300]
#include <string>
#include <vector>

namespace mldefender::firewall {

enum class CategoriaProtegida : uint8_t { NINGUNA = 0, DMZ = 1, INTRANET = 2, EXTERNOS_CRITICOS = 3 };

inline const char* nombre_categoria(CategoriaProtegida c) {
    switch (c) {
        case CategoriaProtegida::DMZ: return "dmz";
        case CategoriaProtegida::INTRANET: return "intranet";
        case CategoriaProtegida::EXTERNOS_CRITICOS: return "externos_criticos";
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
    if (!is_valid_ip_cidr(cidr)) return false;
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
    bool por_defecto = false;

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

inline const std::vector<std::string>& rangos_protegidos_por_defecto() {
    static const std::vector<std::string> v{"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"};
    return v;
}

// Construye los rangos desde las tres listas del JSON. Cada entrada valida se registra con [CONFIG];
// cada invalida se descarta con [CONFIG-DEFAULT] (el resto sigue protegiendo). Sin ningun rango valido:
// defecto RFC 1918 + fc00::/7 como intranet, con [CONFIG-DEFAULT].
inline RangosProtegidos construir_rangos_protegidos(const std::vector<std::string>& dmz,
                                                    const std::vector<std::string>& intranet,
                                                    const std::vector<std::string>& externos_criticos,
                                                    std::ostream& log) {
    RangosProtegidos out;
    struct Lista {
        const std::vector<std::string>* entradas;
        CategoriaProtegida cat;
    };
    const Lista listas[] = {{&dmz, CategoriaProtegida::DMZ},
                            {&intranet, CategoriaProtegida::INTRANET},
                            {&externos_criticos, CategoriaProtegida::EXTERNOS_CRITICOS}};
    for (const auto& l : listas) {
        for (const auto& e : *l.entradas) {
            RangoProtegido r;
            if (parsear_rango(e, l.cat, r)) {
                log << "[CONFIG] ddos_protegidos." << nombre_categoria(l.cat) << " += " << e << " (JSON)\n";
                out.rangos.push_back(r);
            } else {
                log << "[CONFIG-DEFAULT] ddos_protegidos." << nombre_categoria(l.cat) << ": entrada '"
                    << detalle_protegidos::saneado(e)
                    << "' descartada (formato: IPv4 o IPv6 con prefijo opcional /0-32 o /0-128, p. ej. "
                       "10.20.0.0/16 o fd00::/8)\n";
            }
        }
    }
    if (out.rangos.empty()) {
        out.por_defecto = true;
        log << "[CONFIG-DEFAULT] ddos_protegidos: ningun rango valido en el JSON (bloque ausente, listas vacias o "
               "entradas invalidas). Se protegen como intranet los rangos privados:";
        for (const auto& e : rangos_protegidos_por_defecto()) {
            RangoProtegido r;
            if (parsear_rango(e, CategoriaProtegida::INTRANET, r)) {
                out.rangos.push_back(r);
                log << " " << e;
            }
        }
        log << ". Configure dmz, intranet y externos_criticos de ESTE despliegue "
               "(docs/operaciones/GUIA_OPERACIONES.md, seccion DDOS-PROTEGIDOS)\n";
    }
    return out;
}

}  // namespace mldefender::firewall
