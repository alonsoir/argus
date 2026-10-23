#pragma once
// sniffer/include/heads_config.hpp — [HEADS-TESTS-D305]
// Lectores de configuracion del fast-path y de los intervalos del sniffer (reglas de Alonso, DAY305). Sin estado,
// para poder probarlos sueltos (tests/test_heads_config.cpp). Los avisos van a 'aviso' (std::cerr por defecto).
#include <json/json.h>
#include <cctype>
#include <iostream>
#include <string>

namespace sniffer::heads {

// 'enabled': booleano o texto "true"/"false" sin distinguir mayusculas; ausente o invalido -> false + aviso.
inline bool leer_enabled(const Json::Value& blk, const std::string& ctx, std::ostream& aviso = std::cerr) {
    if (blk.isObject() && blk.isMember("enabled")) {
        const Json::Value& v = blk["enabled"];
        if (v.isBool()) {
            return v.asBool();
        }
        if (v.isString()) {
            std::string s = v.asString();
            for (auto& c : s) {
                c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            }
            if (s == "true") {
                return true;
            }
            if (s == "false") {
                return false;
            }
        }
        aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (formato true|false, tambien como texto sin "
                 "distinguir mayusculas): se usa false (APAGADO)" << std::endl;
        return false;
    }
    aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (APAGADO)"
          << std::endl;
    return false;
}

// Entero en [mn, mx]: solo tipos enteros de JSON (un 30.0 o un "30" no valen); ausente, no entero o fuera de
// rango -> defecto + aviso con campo, formato y limites.
inline int leer_entero(const Json::Value& blk, const char* clave, const std::string& ctx, int def, int mn, int mx,
                       std::ostream& aviso = std::cerr) {
    if (!blk.isObject() || !blk.isMember(clave)) {
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << clave << " ausente (entero en [" << mn << ", " << mx
              << "]): se usa " << def << std::endl;
        return def;
    }
    const Json::Value& v = blk[clave];
    const bool entero = v.type() == Json::intValue || v.type() == Json::uintValue;
    if (!entero || (v.type() == Json::uintValue && v.asLargestUInt() > static_cast<Json::LargestUInt>(mx)) ||
        v.asLargestInt() < mn || v.asLargestInt() > mx) {
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << clave << " invalido (entero en [" << mn << ", " << mx
              << "]): se usa " << def << std::endl;
        return def;
    }
    return static_cast<int>(v.asLargestInt());
}

}  // namespace sniffer::heads
