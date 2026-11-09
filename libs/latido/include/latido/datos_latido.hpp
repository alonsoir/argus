#pragma once
// libs/latido/include/latido/datos_latido.hpp — [LATIDO-DATOS-D321] ADR-060 8e.4c (H-H): datos genéricos del latido.
// Una sola regla para los dos lados: el etcd-client la aplica antes de enviar y el etcd-server otra vez al recibir.
// Contrato del protocolo (no es configuración: no va en ningún JSON de componente, como el tamaño máximo de la carga del
// manifiesto): "datos" es un objeto de 0 a kMaxDatos claves ^[a-z][a-z0-9_]{0,31}$ con valores enteros en
// [0, kMaxValor] (2^53 - 1: el mayor entero que cualquier lector JSON representa sin perder precisión). Solo enteros
// (decisión de Alonso, DAY321). Coste O(datos), con datos <= 8.
// Solo cabecera; depende de nlohmann/json.
#include <nlohmann/json.hpp>

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace argus::latido {

inline constexpr std::size_t kMaxDatos = 8;
inline constexpr std::size_t kMaxClave = 32;
inline constexpr std::int64_t kMaxValor = (static_cast<std::int64_t>(1) << 53) - 1;

inline const char* formato() {
    return "objeto de 0 a 8 claves ^[a-z][a-z0-9_]{0,31}$ con valores enteros en [0, 9007199254740991]";
}

inline bool clave_valida(std::string_view c) {
    if (c.empty() || c.size() > kMaxClave) return false;
    if (c[0] < 'a' || c[0] > 'z') return false;
    for (const char ch : c) {
        const bool ok = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_';
        if (!ok) return false;
    }
    return true;
}

inline bool valor_valido(std::int64_t v) { return v >= 0 && v <= kMaxValor; }

// Clave recortada y sin caracteres de control, para el log (una clave rechazada puede traer cualquier cosa)
inline std::string para_log(std::string_view s) {
    std::string o;
    for (std::size_t i = 0; i < s.size() && i < 40; ++i) {
        const unsigned char ch = static_cast<unsigned char>(s[i]);
        o += (ch >= 0x20 && ch < 0x7f) ? static_cast<char>(ch) : '?';
    }
    if (s.size() > 40) o += "...";
    return o;
}

// "" si d vale; si no, el motivo (con la clave y el formato). O(datos).
inline std::string validar_datos(const nlohmann::json& d) {
    if (!d.is_object()) return std::string("no es un objeto (") + d.type_name() + "); formato: " + formato();
    if (d.size() > kMaxDatos)
        return std::to_string(d.size()) + " claves, máximo " + std::to_string(kMaxDatos) + "; formato: " + formato();
    for (auto it = d.begin(); it != d.end(); ++it) {
        if (!clave_valida(it.key())) return "clave '" + para_log(it.key()) + "' mal formada; formato: " + formato();
        const auto& v = it.value();
        bool ok = false;
        if (v.is_number_unsigned()) {
            ok = v.get<std::uint64_t>() <= static_cast<std::uint64_t>(kMaxValor);
        } else if (v.is_number_integer()) {
            ok = valor_valido(v.get<std::int64_t>());
        }
        if (!ok) return "valor de '" + it.key() + "' (" + para_log(v.dump()) + ") no es un entero en [0, " +
                        std::to_string(kMaxValor) + "]; formato: " + formato();
    }
    return "";
}

}  // namespace argus::latido
