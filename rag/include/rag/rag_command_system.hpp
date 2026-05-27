#pragma once
#include <string>
#include <unordered_set>
#include <regex>
#include <vector>

class RAGCommandSystem {
private:
    // Acciones permitidas explícitamente
    const std::unordered_set<std::string> allowed_actions_{
        "search", "query", "find", "list", "config",
        "stats", "health", "version", "metrics", "status", "help"
    };

    // Patrones permitidos para parámetros
    const std::vector<std::regex> allowed_patterns_{
        std::regex{R"(error\s+.+)"},                    // error 404, error timeout
        std::regex{R"(logs?\s+.+)"},                    // logs, log analysis
        std::regex{R"(troubleshoot\s+.+)"},             // troubleshoot memory
        std::regex{R"(documentation)"},                 // documentation
        std::regex{R"(guide|tutorial|examples)"},       // guide, tutorial
        std::regex{R"(how\s+to\s+.+)"},                 // how to configure
        std::regex{R"(best\s+practices)"},              // best practices
        std::regex{R"(configuration\s+.+)"},            // configuration settings
        std::regex{R"(performance\s+.+)"},              // performance issues
        std::regex{R"(\w+\s+documentation)"},           // API documentation
        std::regex{R"(collections)"},                   // collections (para list)
        std::regex{R"(get\s+\w+)"}                      // get timeout, get cache_size
    };

public:
    struct CommandResult {
        bool is_valid{false};
        std::string action;
        std::string parameters;
        std::string error_message;
        std::string normalized_command;
    };

    CommandResult parse_and_validate(const std::string& user_input) {
        CommandResult result;

        // Convertir a lowercase para comparación case-insensitive
        std::string input = to_lower(user_input);

        // Extraer comando básico: rag <acción> '<parámetros>'
        auto parsed = extract_command(input);
        if (!parsed.has_value()) {
            result.error_message = "Formato de comando inválido. Use: rag <acción> '<parámetros>'";
            return result;
        }

        auto [action, parameters] = parsed.value();
        result.action = action;
        result.parameters = parameters;

        // Validar acción
        if (!is_action_allowed(action)) {
            result.error_message = "Acción '" + action + "' no permitida. Use 'rag help' para ver acciones disponibles.";
            return result;
        }

        // Validar parámetros según la acción
        if (!validate_parameters(action, parameters)) {
            result.error_message = "Parámetros no permitidos para la acción '" + action + "'";
            return result;
        }

        result.is_valid = true;
        result.normalized_command = "rag " + action + " '" + parameters + "'";
        return result;
    }

    std::string generate_help() {
        return R"(
🛡️ RAG Command System - Comandos Permitidos

📊 COMANDOS DEL SISTEMA:
  rag stats           - Estado del sistema
  rag health          - Salud del servicio
  rag version         - Versión del software
  rag metrics         - Métricas de rendimiento
  rag status          - Estado general
  rag help            - Esta ayuda

🗄️  OPERACIONES DE DATOS:
  rag list collections     - Listar colecciones disponibles
  rag config get <clave>   - Consultar configuración (timeout, cache_size, etc.)

🔧 DIAGNÓSTICO Y TROUBLESHOOTING:
  rag search 'error <tipo>'       - Buscar errores específicos
  rag query 'troubleshoot <problema>' - Diagnosticar problemas
  rag find 'logs <filtro>'        - Buscar en logs del sistema

📚 CONSULTAS DE DOCUMENTACIÓN:
  rag search '<tema> documentation' - Buscar documentación
  rag find '<tema> guide'     - Buscar guías y tutoriales
  rag query 'how to <acción>' - Consultas de aprendizaje

💡 EJEMPLOS PERMITIDOS:
  rag search 'error 404 documentation'
  rag query 'how to configure cache'
  rag find 'performance troubleshooting guide'
  rag config get timeout
  rag list collections

🔒 SEGURIDAD: Solo los comandos listados están permitidos.
)";
    }

private:
    std::string to_lower(const std::string& str) {
        std::string lower = str;
        std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
        return lower;
    }

    std::optional<std::pair<std::string, std::string>> extract_command(const std::string& input) {
        // Patrón: rag <acción> '<parámetros>'
        std::regex pattern{R"(rag\s+(\w+)\s+'([^']*)')"};
        std::smatch matches;

        if (std::regex_search(input, matches, pattern) && matches.size() == 3) {
            return std::make_pair(matches[1].str(), matches[2].str());
        }

        return std::nullopt;
    }

    bool is_action_allowed(const std::string& action) {
        return allowed_actions_.find(action) != allowed_actions_.end();
    }

    bool validate_parameters(const std::string& action, const std::string& parameters) {
        if (action == "list") {
            return parameters == "collections";
        }
        else if (action == "config") {
            return std::regex_match(parameters, std::regex{R"(get\s+\w+)"});
        }
        else if (action == "stats" || action == "health" ||
                 action == "version" || action == "metrics" ||
                 action == "status" || action == "help") {
            return parameters.empty();
        }
        else if (action == "search" || action == "query" || action == "find") {
            return validate_search_parameters(parameters);
        }

        return false;
    }

    bool validate_search_parameters(const std::string& parameters) {
        // Verificar contra patrones permitidos
        for (const auto& pattern : allowed_patterns_) {
            if (std::regex_match(parameters, pattern)) {
                return true;
            }
        }
        return false;
    }
};