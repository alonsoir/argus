// /vagrant/rag/include/rag/security_context.hpp - VERSIÓN EVOLUCIONADA
#pragma once
#include <string>
#include <vector>
#include <map>
#include <nlohmann/json.hpp>

namespace Rag {

struct SecurityContext {
    // Identificación
    std::string user_id;
    std::string session_id;
    std::string user_role;

    // Entorno
    std::string environment;
    std::string source_ip;
    std::string client_info;

    // Niveles de seguridad
    int privilege_level;
    int clearance_level;
    std::vector<std::string> permissions;

    // Contexto temporal
    std::string timestamp;
    std::string timezone;

    // Metadatos adicionales
    std::map<std::string, std::string> metadata;

    // Constructor por defecto
    SecurityContext() :
        user_id("anonymous"),
        session_id("cli_session"),
        user_role("security_analyst"),
        environment("production"),
        source_ip("127.0.0.1"),
        client_info("rag_cli"),
        privilege_level(3),
        clearance_level(2),
        timestamp(""),
        timezone("UTC")
    {
        permissions = {"read_logs", "validate_commands", "query_security"};
        metadata = {{"version", "1.0"}, {"interface", "cli"}};
    }

    // Constructor específico para diferentes casos de uso
    SecurityContext(const std::string& role, int priv_level, const std::string& env) :
        user_id("cli_user"),
        session_id("session_" + std::to_string(time(nullptr))),
        user_role(role),
        environment(env),
        source_ip("127.0.0.1"),
        client_info("rag_security_cli"),
        privilege_level(priv_level),
        clearance_level(priv_level),
        timestamp(""),
        timezone("UTC")
    {
        if (role == "admin") {
            permissions = {"read_logs", "validate_commands", "manage_whitelist", "system_config"};
        } else if (role == "analyst") {
            permissions = {"read_logs", "validate_commands", "query_security"};
        } else {
            permissions = {"validate_commands"};
        }
    }

    // Método para convertir a string (JSON)
    std::string to_string() const {
        nlohmann::json j;
        j["user_id"] = user_id;
        j["session_id"] = session_id;
        j["user_role"] = user_role;
        j["environment"] = environment;
        j["source_ip"] = source_ip;
        j["client_info"] = client_info;
        j["privilege_level"] = privilege_level;
        j["clearance_level"] = clearance_level;
        j["permissions"] = permissions;
        j["timestamp"] = timestamp;
        j["timezone"] = timezone;
        j["metadata"] = metadata;
        return j.dump();
    }

    // Métodos de utilidad
    bool has_permission(const std::string& permission) const {
        return std::find(permissions.begin(), permissions.end(), permission) != permissions.end();
    }

    bool is_admin() const {
        return user_role == "admin" || privilege_level >= 5;
    }

    void set_timestamp_now() {
        // Implementación simple - en producción usar librería de tiempo
        time_t now = time(nullptr);
        timestamp = std::to_string(now);
    }
};

} // namespace Rag