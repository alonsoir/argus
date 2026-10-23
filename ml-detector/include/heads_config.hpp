#pragma once
// ml-detector/include/heads_config.hpp — [HEADS-TESTS-D305]
// Lectores de configuracion de las cabezas del ml-detector (reglas de Alonso, DAY305). Sin estado, para poder
// probarlos sueltos (tests/unit/test_heads_config.cpp). Los avisos van a 'aviso' (std::cerr por defecto).
#include <nlohmann/json.hpp>
#include <cctype>
#include <iostream>
#include <string>

namespace ml_detector::heads {

// 'enabled' de una cabeza: booleano JSON o texto "true"/"false" sin distinguir mayusculas. Ausente o cualquier
// otro valor -> false (cabeza APAGADA) con [CONFIG-DEFAULT].
inline bool read_enabled(const nlohmann::json& block, const std::string& ctx, std::ostream& aviso = std::cerr) {
    if (block.is_object() && block.contains("enabled")) {
        const auto& v = block["enabled"];
        if (v.is_boolean()) {
            return v.get<bool>();
        }
        if (v.is_string()) {
            std::string s = v.get<std::string>();
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
        aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (" << v.dump()
              << "; formato true|false, tambien como texto sin distinguir mayusculas): se usa false (cabeza APAGADA)\n";
        return false;
    }
    aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (cabeza APAGADA)\n";
    return false;
}

// Entero en [mn, mx]. Ausente, no entero (un 60.0 tampoco lo es), o fuera de rango -> 'def' con [CONFIG-DEFAULT]
// que nombra campo, formato y limites.
inline int read_int_in_range(const nlohmann::json& block, const char* key, const std::string& ctx, int def,
                             int mn, int mx, std::ostream& aviso = std::cerr) {
    if (!block.is_object() || !block.contains(key)) {
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << key << " ausente (entero en [" << mn << ", " << mx
              << "]): se usa " << def << "\n";
        return def;
    }
    const auto& v = block[key];
    bool ok = false;
    long long x = 0;
    if (v.is_number_unsigned()) {
        const unsigned long long u = v.get<unsigned long long>();
        ok = u <= static_cast<unsigned long long>(mx);
        x = ok ? static_cast<long long>(u) : 0;
    } else if (v.is_number_integer()) {
        x = v.get<long long>();
        ok = true;
    }
    if (!ok || x < mn || x > mx) {
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << key << " invalido (" << v.dump() << "; entero en [" << mn
              << ", " << mx << "]): se usa " << def << "\n";
        return def;
    }
    return static_cast<int>(x);
}

}  // namespace ml_detector::heads
