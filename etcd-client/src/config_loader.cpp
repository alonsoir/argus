// etcd-client/src/config_loader.cpp — [ETCD-CLIENTE-D316] lector único del bloque "etcd" (DEBT-ETCD-HA-TLS-RAFT-001
// paso 5, decisión F1 de Alonso, DAY316). Sustituye a Config::from_json/from_json_file (sin usuarios, F2).
// El JSON es la ley: cada campo se registra con su valor y su origen. endpoints, ca_file, cert_file y key_file los
// rellena el aprovisionamiento (D1): sin defecto, fatales para etcd ([ETCD-CLIENTE-FATAL]). El resto: defecto + aviso.
#include "etcd_client/etcd_client.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <regex>
#include <set>
#include <sstream>

namespace etcd_client {

namespace {

constexpr int kMaxEndpoints = 7;

void fatal(LecturaBloque& r, std::ostream& log, const std::string& campo, const std::string& motivo,
           const std::string& formato) {
    std::string linea = "[ETCD-CLIENTE-FATAL] etcd." + campo + ": " + motivo + " (formato: " + formato +
                        "). Sin este campo el componente no puede hablar con el etcd-server; lo rellena el "
                        "aprovisionamiento (inventario/Jenkins)";
    log << linea << std::endl;
    r.fatales.push_back(linea);
}

// Entero en [mn, mx] con defecto (solo enteros JSON: un 300.0, un "300" o un true no valen)
int entero(const nlohmann::json& b, const char* clave, int def, int mn, int mx, LecturaBloque& r, std::ostream& log) {
    const std::string campo = std::string("etcd.") + clave;
    const std::string formato = "entero en [" + std::to_string(mn) + ", " + std::to_string(mx) + "]";
    if (!b.contains(clave)) {
        log << "[CONFIG-DEFAULT] " << campo << " ausente (" << formato << "): se usa " << def << std::endl;
        ++r.defectos;
        return def;
    }
    const nlohmann::json& v = b[clave];
    if (!v.is_number_integer()) {
        log << "[CONFIG-DEFAULT] " << campo << "=" << v.dump() << " no es entero (" << formato << "): se usa " << def
            << std::endl;
        ++r.defectos;
        return def;
    }
    const long long x = v.get<long long>();
    if (x < mn || x > mx) {
        log << "[CONFIG-DEFAULT] " << campo << "=" << x << " fuera de rango (" << formato << "): se usa " << def
            << std::endl;
        ++r.defectos;
        return def;
    }
    log << "[CONFIG] " << campo << "=" << x << " (JSON)" << std::endl;
    return static_cast<int>(x);
}

// Ruta absoluta de un fichero que se puede leer; sin defecto
void ruta(const nlohmann::json& b, const char* clave, std::string& out, LecturaBloque& r, std::ostream& log) {
    const char* formato = "ruta absoluta de un fichero PEM legible";
    if (!b.contains(clave)) return fatal(r, log, clave, "ausente", formato);
    const nlohmann::json& v = b[clave];
    if (!v.is_string() || v.get<std::string>().empty() || v.get<std::string>()[0] != '/')
        return fatal(r, log, clave, "valor " + v.dump() + " mal formado", formato);
    const std::string p = v.get<std::string>();
    std::ifstream f(p);
    if (!f.is_open()) return fatal(r, log, clave, "no se puede leer " + p, formato);
    out = p;
    log << "[CONFIG] etcd." << clave << "=" << p << " (JSON)" << std::endl;
}

// https://<host>:<puerto>; host = IPv4 o nombre DNS; puerto 1-65535
bool url_valida(const std::string& u) {
    static const std::regex re(R"(^https://([A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?):([0-9]{1,5})$)");
    std::smatch m;
    if (!std::regex_match(u, m, re)) return false;
    const long p = std::stol(m[3].str());
    return p >= 1 && p <= 65535;
}

void endpoints(const nlohmann::json& b, std::vector<std::string>& out, LecturaBloque& r, std::ostream& log) {
    const std::string formato = "lista de 1 a " + std::to_string(kMaxEndpoints) +
                                " URL https://<host>:<puerto> sin repetir, puerto en [1, 65535]";
    if (!b.contains("endpoints")) return fatal(r, log, "endpoints", "ausente", formato);
    const nlohmann::json& v = b["endpoints"];
    if (!v.is_array() || v.empty() || v.size() > static_cast<size_t>(kMaxEndpoints))
        return fatal(r, log, "endpoints", "valor " + v.dump() + " mal formado", formato);
    std::set<std::string> vistos;
    std::vector<std::string> l;
    for (const auto& e : v) {
        if (!e.is_string() || !url_valida(e.get<std::string>()))
            return fatal(r, log, "endpoints", "elemento " + e.dump() + " mal formado (http:// no vale: solo TLS)",
                         formato);
        if (!vistos.insert(e.get<std::string>()).second)
            return fatal(r, log, "endpoints", "elemento " + e.dump() + " repetido", formato);
        l.push_back(e.get<std::string>());
    }
    out = l;
    log << "[CONFIG] etcd.endpoints=" << v.dump() << " (JSON)" << std::endl;
}

}  // namespace

LecturaBloque leer_bloque_etcd(const nlohmann::json& b, std::ostream& log) {
    LecturaBloque r;
    Config& c = r.config;
    const Config d{};
    if (!b.is_object()) {
        fatal(r, log, "(bloque)", "falta el bloque \"etcd\" o no es un objeto", "objeto JSON");
        return r;
    }
    endpoints(b, c.endpoints, r, log);
    ruta(b, "ca_file", c.ca_file, r, log);
    ruta(b, "cert_file", c.cert_file, r, log);
    ruta(b, "key_file", c.key_file, r, log);
    c.connection_timeout_ms = entero(b, "connection_timeout_ms", d.connection_timeout_ms, 100, 60000, r, log);
    c.retry_attempts = entero(b, "retry_attempts", d.retry_attempts, 1, 10, r, log);
    c.retry_interval_ms = entero(b, "retry_interval_ms", d.retry_interval_ms, 100, 60000, r, log);
    c.heartbeat_interval_seconds = entero(b, "heartbeat_interval_seconds", d.heartbeat_interval_seconds, 5, 300, r, log);
    // C3, D2, E3 (DAY316): campos que ya no hacen nada
    for (const char* k : {"enabled", "crypto_token_path", "config_sync_path", "required_for_encryption",
                          "service_registration_path", "fallback_mode", "lease_ttl_seconds"}) {
        if (b.contains(k)) {
            log << "[CONFIG-OBSOLETO] etcd." << k << " ya no se usa desde DAY316 (DEBT-ETCD-HA-TLS-RAFT-001 paso 5). "
                << "Se ignora: quitarlo del JSON" << std::endl;
            ++r.obsoletos;
        }
    }
    log << "[ETCD-CLIENTE-CONFIG] bloque etcd leído: " << c.endpoints.size() << " direcciones, " << r.defectos
        << " campos con defecto, " << r.obsoletos << " obsoletos, " << r.fatales.size() << " fatales" << std::endl;
    return r;
}

LecturaBloque leer_bloque_etcd(const std::string& bloque_json, std::ostream& log) {
    if (bloque_json.empty()) return leer_bloque_etcd(nlohmann::json(), log);
    try {
        return leer_bloque_etcd(nlohmann::json::parse(bloque_json), log);
    } catch (const nlohmann::json::exception& e) {
        LecturaBloque r;
        fatal(r, log, "(bloque)", std::string("JSON ilegible: ") + e.what(), "objeto JSON");
        return r;
    }
}

}  // namespace etcd_client
