#pragma once
// etcd-server/include/etcd_server/etcd_server_config.hpp — [ETCD-CONFIG-D312]
// Configuración del etcd-server: bloques "server", "secrets" y "heartbeat" de etcd-server.json
// (DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001). Política de Alonso (DAY291/DAY300/DAY308/DAY312): el JSON es la ley y se
// lee SIEMPRE; si un campo falta, tiene otro tipo o está fuera de rango, se usa el DEFECTO validado (los mismos
// valores que trae etcd-server.json), se avisa con [CONFIG-DEFAULT] (campo, formato y límites) y el proceso arranca
// igual. La línea [ETCD-CONFIG] del arranque dice el valor de cada campo y de dónde sale (JSON o DEFECTO, y por qué).
// Los bloques "identity" (SeedClient) y "alerting" (AlertClient) tienen su propio lector y no se tocan aquí.
// Sin estado y sin dependencias del resto del etcd-server, para probarlo suelto (tests/test_etcd_server_config.cpp),
// como flow_table_config.hpp del sniffer (DAY308).
#include <nlohmann/json.hpp>
#include <arpa/inet.h>
#include <cstdint>
#include <iostream>
#include <string>

namespace argus::etcdcfg {

// Defectos validados: iguales a etcd-server.json. Límites: los del _doc de cada bloque del JSON.
struct EtcdServerConfig {
    std::string host = "0.0.0.0";           // server.host: IPv4 en notación decimal con puntos
    int port = 2379;                         // server.port: [1024, 65535]
    int grace_period_seconds = 300;          // secrets.grace_period_seconds: [1, 86400]
    int default_key_length_bytes = 32;       // secrets.default_key_length_bytes: [32, 64]
    int min_rotation_interval_seconds = 300; // secrets.min_rotation_interval_seconds: [1, 86400], >= grace_period
    int heartbeat_interval_seconds = 30;     // heartbeat.interval_seconds: [1, 3600]
    int heartbeat_timeout_multiplier = 3;    // heartbeat.timeout_multiplier: [2, 10]
    int heartbeat_check_interval_seconds = 10; // heartbeat.check_interval_seconds: [1, 3600], <= interval * multiplier
};

struct Resultado {
    EtcdServerConfig cfg;
    int defectos = 0;   // campos con valor por defecto (ausente, tipo, rango o regla)
    int obsoletos = 0;  // campos que ya no se usan y siguen en el JSON
};

namespace detalle {
inline const nlohmann::json& bloque(const nlohmann::json& root, const char* nombre, std::ostream& aviso) {
    static const nlohmann::json kVacio = nlohmann::json::object();
    if (!root.is_object() || !root.contains(nombre)) return kVacio;
    if (!root[nombre].is_object()) {
        aviso << "[CONFIG-DEFAULT] " << nombre << " no es un objeto: se usan los defectos de todos sus campos"
              << std::endl;
        return kVacio;
    }
    return root[nombre];
}

// Entero en [mn, mx]: solo enteros JSON (un 300.0, un "300" o un true no valen). Devuelve el origen del valor.
inline std::string entero(const nlohmann::json& blk, const char* bloque_nom, const char* clave, int def, int mn,
                          int mx, int& out, int& n, std::ostream& aviso) {
    const std::string campo = std::string(bloque_nom) + "." + clave;
    const std::string formato = "entero en [" + std::to_string(mn) + ", " + std::to_string(mx) + "]";
    out = def;
    if (!blk.contains(clave)) {
        aviso << "[CONFIG-DEFAULT] " << campo << " ausente (" << formato << "): se usa " << def << std::endl;
        ++n;
        return "DEFECTO: ausente";
    }
    const nlohmann::json& v = blk[clave];
    if (!v.is_number_integer()) {
        aviso << "[CONFIG-DEFAULT] " << campo << "=" << v.dump() << " no es entero (" << formato << "): se usa "
              << def << std::endl;
        ++n;
        return "DEFECTO: no entero";
    }
    const long long x = v.get<long long>();
    if (x < mn || x > mx) {
        aviso << "[CONFIG-DEFAULT] " << campo << "=" << x << " fuera de rango (" << formato << "): se usa " << def
              << std::endl;
        ++n;
        return "DEFECTO: fuera de rango";
    }
    out = static_cast<int>(x);
    return "JSON";
}

inline std::string ipv4(const nlohmann::json& blk, const char* bloque_nom, const char* clave, const std::string& def,
                        std::string& out, int& n, std::ostream& aviso) {
    const std::string campo = std::string(bloque_nom) + "." + clave;
    const char* formato = "IPv4 en notación decimal con puntos, p. ej. 0.0.0.0 o 192.168.100.20";
    out = def;
    if (!blk.contains(clave)) {
        aviso << "[CONFIG-DEFAULT] " << campo << " ausente (" << formato << "): se usa " << def << std::endl;
        ++n;
        return "DEFECTO: ausente";
    }
    const nlohmann::json& v = blk[clave];
    in_addr a{};
    if (!v.is_string() || inet_pton(AF_INET, v.get<std::string>().c_str(), &a) != 1) {
        aviso << "[CONFIG-DEFAULT] " << campo << "=" << v.dump() << " no es una IPv4 válida (" << formato
              << "): se usa " << def << std::endl;
        ++n;
        return "DEFECTO: mal formado";
    }
    out = v.get<std::string>();
    return "JSON";
}

inline void obsoleto(const nlohmann::json& blk, const char* bloque_nom, const char* clave, const char* motivo,
                     int& n, std::ostream& aviso) {
    if (blk.is_object() && blk.contains(clave)) {
        aviso << "[CONFIG-OBSOLETO] " << bloque_nom << (bloque_nom[0] ? "." : "") << clave << " ya no se usa desde DAY312 ("
              << motivo << "). Se ignora: quitarlo de etcd-server.json" << std::endl;
        ++n;
    }
}
}  // namespace detalle

inline Resultado parse_etcd_server_config(const nlohmann::json& root, std::ostream& aviso = std::cerr,
                                          std::ostream& info = std::cout) {
    Resultado r;
    EtcdServerConfig& c = r.cfg;
    const EtcdServerConfig d{};
    int& n = r.defectos;
    if (!root.is_object()) {
        aviso << "[CONFIG-DEFAULT] la raíz de etcd-server.json no es un objeto: se usan los defectos de todo"
              << std::endl;
    }
    const auto& srv = detalle::bloque(root, "server", aviso);
    const auto& sec = detalle::bloque(root, "secrets", aviso);
    const auto& hb = detalle::bloque(root, "heartbeat", aviso);

    std::string o_host = detalle::ipv4(srv, "server", "host", d.host, c.host, n, aviso);
    std::string o_port = detalle::entero(srv, "server", "port", d.port, 1024, 65535, c.port, n, aviso);
    std::string o_grace = detalle::entero(sec, "secrets", "grace_period_seconds", d.grace_period_seconds, 1, 86400,
                                          c.grace_period_seconds, n, aviso);
    std::string o_klen = detalle::entero(sec, "secrets", "default_key_length_bytes", d.default_key_length_bytes, 32, 64,
                                         c.default_key_length_bytes, n, aviso);
    std::string o_minrot = detalle::entero(sec, "secrets", "min_rotation_interval_seconds",
                                           d.min_rotation_interval_seconds, 1, 86400,
                                           c.min_rotation_interval_seconds, n, aviso);
    std::string o_hbi = detalle::entero(hb, "heartbeat", "interval_seconds", d.heartbeat_interval_seconds, 1, 3600,
                                        c.heartbeat_interval_seconds, n, aviso);
    std::string o_hbm = detalle::entero(hb, "heartbeat", "timeout_multiplier", d.heartbeat_timeout_multiplier, 2, 10,
                                        c.heartbeat_timeout_multiplier, n, aviso);
    std::string o_hbc = detalle::entero(hb, "heartbeat", "check_interval_seconds", d.heartbeat_check_interval_seconds,
                                        1, 3600, c.heartbeat_check_interval_seconds, n, aviso);

    // Regla ADR-004: una clave antigua no puede acumularse; la rotación mínima no baja de la gracia.
    if (c.min_rotation_interval_seconds < c.grace_period_seconds) {
        aviso << "[CONFIG-DEFAULT] regla secrets.min_rotation_interval_seconds >= secrets.grace_period_seconds rota ("
              << c.min_rotation_interval_seconds << " < " << c.grace_period_seconds << "): se usan "
              << d.min_rotation_interval_seconds << " y " << d.grace_period_seconds << std::endl;
        c.min_rotation_interval_seconds = d.min_rotation_interval_seconds;
        c.grace_period_seconds = d.grace_period_seconds;
        o_minrot = o_grace = "DEFECTO: regla min_rotation >= grace";
        ++n;
    }
    // Regla: el monitor mira al menos una vez dentro del plazo de muerte de un componente.
    if (c.heartbeat_check_interval_seconds > c.heartbeat_interval_seconds * c.heartbeat_timeout_multiplier) {
        aviso << "[CONFIG-DEFAULT] regla heartbeat.check_interval_seconds <= interval_seconds * timeout_multiplier rota ("
              << c.heartbeat_check_interval_seconds << " > " << c.heartbeat_interval_seconds << " * "
              << c.heartbeat_timeout_multiplier << "): se usan " << d.heartbeat_interval_seconds << ", "
              << d.heartbeat_timeout_multiplier << " y " << d.heartbeat_check_interval_seconds << std::endl;
        c.heartbeat_interval_seconds = d.heartbeat_interval_seconds;
        c.heartbeat_timeout_multiplier = d.heartbeat_timeout_multiplier;
        c.heartbeat_check_interval_seconds = d.heartbeat_check_interval_seconds;
        o_hbi = o_hbm = o_hbc = "DEFECTO: regla check <= interval * multiplier";
        ++n;
    }

    // Campos que nunca hicieron nada (leídos en el código o no): si siguen, el admin cree configurado algo que no lo está.
    int& ob = r.obsoletos;
    static const nlohmann::json kVacio = nlohmann::json::object();
    detalle::obsoleto(srv, "server", "worker_threads", "httplib usa su propio pool; nunca se leyó", ob, aviso);
    detalle::obsoleto(sec, "secrets", "enabled", "el SecretsManager siempre está activo; nunca se leyó", ob, aviso);
    detalle::obsoleto(sec, "secrets", "rotation_interval_hours", "no hay rotación automática; solo se escribía en el log",
                      ob, aviso);
    detalle::obsoleto(sec, "secrets", "auto_generate_on_startup", "la clave se crea en la primera petición; nunca se leyó",
                      ob, aviso);
    detalle::obsoleto(sec, "secrets", "storage", "las claves pasan a Vault (paso 4b.5); nunca se leyó", ob, aviso);
    detalle::obsoleto(sec, "secrets", "keys", "rutas de ejemplo que nadie leía", ob, aviso);
    detalle::obsoleto(hb, "heartbeat", "enabled", "el monitor de latidos siempre está activo; nunca se leyó", ob, aviso);
    detalle::obsoleto(root.is_object() ? root : kVacio, "", "auto_restart",
                      "nunca se leyó; el reinicio por system() que lo usaría se borra en 4b.6 por inseguro", ob, aviso);
    detalle::obsoleto(root.is_object() ? root : kVacio, "", "security",
                      "cifrado y compresión los decide la petición; nunca se leyó", ob, aviso);

    if (n > 0) {
        aviso << "[CONFIG-DEFAULT] " << n << " ajustes con valor por defecto en etcd-server.json: revisarlo" << std::endl;
    }
    info << "[ETCD-CONFIG] server.host=" << c.host << " (" << o_host << ") server.port=" << c.port << " (" << o_port
         << ") secrets.grace_period_seconds=" << c.grace_period_seconds << " (" << o_grace
         << ") secrets.default_key_length_bytes=" << c.default_key_length_bytes << " (" << o_klen
         << ") secrets.min_rotation_interval_seconds=" << c.min_rotation_interval_seconds << " (" << o_minrot
         << ") heartbeat.interval_seconds=" << c.heartbeat_interval_seconds << " (" << o_hbi
         << ") heartbeat.timeout_multiplier=" << c.heartbeat_timeout_multiplier << " (" << o_hbm
         << ") heartbeat.check_interval_seconds=" << c.heartbeat_check_interval_seconds << " (" << o_hbc << ")"
         << std::endl;
    return r;
}

}  // namespace argus::etcdcfg
