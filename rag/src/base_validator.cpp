#include "rag/base_validator.hpp"
#include <stdexcept>
#include <regex>

namespace Rag {

bool BaseValidator::validate(const std::string& field_name, const std::string& value) const {
    if (value.empty()) {
        std::cout << "❌ Error: El valor no puede estar vacío" << std::endl;
        return false;
    }

    // Buscar regla específica para este campo
    auto it = validation_rules_.find(field_name);
    if (it != validation_rules_.end()) {
        const ValidationRule& rule = it->second;

        switch (rule.type) {
            case ValidationType::INTEGER:
                return validateInteger(value, rule.min_value, rule.max_value, field_name);
            case ValidationType::FLOAT:
                return validateFloat(value, rule.min_value, rule.max_value, field_name);
            case ValidationType::BOOLEAN:
                return validateBoolean(value, field_name);
            case ValidationType::STRING:
                return validateString(value, 0, field_name); // 0 = sin límite
            case ValidationType::PORT:
                return validatePort(value, field_name);
            case ValidationType::THRESHOLD:
                return validateThreshold(value, field_name);
            case ValidationType::LOG_LEVEL:
                return validateLogLevel(value, field_name);
            case ValidationType::FILE_PATH:
                return validateFilePath(value, field_name);
            case ValidationType::HOST_NAME:
                return validateHostName(value, field_name);
            case ValidationType::IP_ADDRESS:
                return validateIpAddress(value, field_name);
            default:
                std::cout << "❌ Error: Tipo de validación desconocido para '" << field_name << "'" << std::endl;
                return false;
        }
    }

    // Si no hay regla específica, intentar detección automática
    return autoDetectAndValidate(field_name, value);
}

void BaseValidator::addRule(const std::string& field_name, ValidationType type,
                           double min_val, double max_val,
                           const std::vector<std::string>& allowed_values,
                           const std::string& custom_error) {
    ValidationRule rule;
    rule.type = type;
    rule.field_name = field_name;
    rule.min_value = min_val;
    rule.max_value = max_val;
    rule.allowed_values = allowed_values;
    rule.custom_error = custom_error;

    validation_rules_[field_name] = rule;
}

// Implementaciones de métodos de validación
bool BaseValidator::validateInteger(const std::string& value, double min_val, double max_val, const std::string& field_name) const {
    try {
        int int_value = std::stoi(value);

        if (min_val != 0.0 && int_value < min_val) {
            std::cout << "❌ Error: " << field_name << " debe ser al menos " << static_cast<int>(min_val) << std::endl;
            return false;
        }

        if (max_val != 0.0 && int_value > max_val) {
            std::cout << "❌ Error: " << field_name << " no puede exceder " << static_cast<int>(max_val) << std::endl;
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        std::cout << "❌ Error: " << field_name << " debe ser un número entero válido" << std::endl;
        return false;
    }
}

bool BaseValidator::validateFloat(const std::string& value, double min_val, double max_val, const std::string& field_name) const {
    try {
        double float_value = std::stod(value);

        if (min_val != 0.0 && float_value < min_val) {
            std::cout << "❌ Error: " << field_name << " debe ser al menos " << min_val << std::endl;
            return false;
        }

        if (max_val != 0.0 && float_value > max_val) {
            std::cout << "❌ Error: " << field_name << " no puede exceder " << max_val << std::endl;
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        std::cout << "❌ Error: " << field_name << " debe ser un número válido" << std::endl;
        return false;
    }
}

bool BaseValidator::validateBoolean(const std::string& value, const std::string& field_name) const {
    std::string lower_value = toLower(value);

    static const std::vector<std::string> valid_booleans = {
        "true", "false", "1", "0", "yes", "no", "on", "off", "enabled", "disabled"
    };

    if (std::find(valid_booleans.begin(), valid_booleans.end(), lower_value) != valid_booleans.end()) {
        return true;
    }

    std::cout << "❌ Error: " << field_name << " debe ser un valor booleano (true/false, 1/0, yes/no, on/off)" << std::endl;
    return false;
}

bool BaseValidator::validateString(const std::string& value, size_t max_length, const std::string& field_name) const {
    if (value.empty()) {
        std::cout << "❌ Error: " << field_name << " no puede estar vacío" << std::endl;
        return false;
    }

    if (max_length > 0 && value.length() > max_length) {
        std::cout << "❌ Error: " << field_name << " no puede exceder " << max_length << " caracteres" << std::endl;
        return false;
    }

    return true;
}

bool BaseValidator::validatePort(const std::string& value, const std::string& field_name) const {
    return validateInteger(value, 1, 65535, field_name);
}

bool BaseValidator::validateThreshold(const std::string& value, const std::string& field_name) const {
    return validateFloat(value, 0.0, 1.0, field_name);
}

bool BaseValidator::validateLogLevel(const std::string& value, const std::string& field_name) const {
    std::string upper_value = toUpper(value);

    static const std::vector<std::string> valid_levels = {
        "TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"
    };

    if (std::find(valid_levels.begin(), valid_levels.end(), upper_value) != valid_levels.end()) {
        return true;
    }

    std::cout << "❌ Error: " << field_name << " inválido. Use: TRACE, DEBUG, INFO, WARN, ERROR, FATAL" << std::endl;
    return false;
}

bool BaseValidator::validateFilePath(const std::string& value, const std::string& field_name) const {
    if (!validateString(value, 0, field_name)) {
        return false;
    }

    // Advertencia por seguridad (no bloqueante)
    if (value.find("..") != std::string::npos) {
        std::cout << "⚠️  Advertencia: " << field_name << " contiene '..' que puede ser inseguro" << std::endl;
    }

    return true;
}

bool BaseValidator::validateHostName(const std::string& value, const std::string& field_name) const {
    return validateString(value, 253, field_name);
}

bool BaseValidator::validateIpAddress(const std::string& value, const std::string& field_name) const {
    // Expresión regular simple para validar IP
    std::regex ip_pattern(R"(^(\d{1,3}\.){3}\d{1,3}$)");

    if (!std::regex_match(value, ip_pattern)) {
        std::cout << "❌ Error: " << field_name << " debe ser una dirección IP válida" << std::endl;
        return false;
    }

    return true;
}

bool BaseValidator::autoDetectAndValidate(const std::string& field_name, const std::string& value) const {
    std::string lower_field = toLower(field_name);

    // Detección basada en patrones en el nombre del campo
    if (lower_field.find("port") != std::string::npos) {
        return validatePort(value, field_name);
    }
    else if (lower_field.find("threshold") != std::string::npos ||
             lower_field.find("_thresh") != std::string::npos) {
        return validateThreshold(value, field_name);
    }
    else if (lower_field.find("enabled") != std::string::npos ||
             lower_field.find("active") != std::string::npos ||
             lower_field.find("validate") != std::string::npos ||
             lower_field.find("sanitize") != std::string::npos ||
             lower_field.find("include") != std::string::npos) {
        return validateBoolean(value, field_name);
    }
    else if (lower_field.find("level") != std::string::npos) {
        return validateLogLevel(value, field_name);
    }
    else if (lower_field.find("file") != std::string::npos ||
             lower_field.find("path") != std::string::npos) {
        return validateFilePath(value, field_name);
    }
    else if (lower_field.find("host") != std::string::npos) {
        return validateHostName(value, field_name);
    }
    else if (lower_field.find("ip") != std::string::npos ||
             lower_field.find("address") != std::string::npos) {
        return validateIpAddress(value, field_name);
    }
    else if (lower_field.find("dimension") != std::string::npos ||
             lower_field.find("_size") != std::string::npos ||
             lower_field.find("_bytes") != std::string::npos ||
             lower_field.find("_count") != std::string::npos) {
        return validateInteger(value, 1, 1000000000, field_name);
    }

    // Por defecto, intentar detectar el tipo
    if (isInteger(value)) {
        return validateInteger(value, 0, 0, field_name);
    }
    else if (isFloat(value)) {
        return validateFloat(value, 0, 0, field_name);
    }

    // Por defecto, tratar como string
    return validateString(value, 0, field_name);
}

// Métodos auxiliares
std::string BaseValidator::toLower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

std::string BaseValidator::toUpper(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::toupper);
    return result;
}

bool BaseValidator::isInteger(const std::string& value) {
    try {
        size_t pos;
        std::stoi(value, &pos);
        return pos == value.length();
    } catch (...) {
        return false;
    }
}

bool BaseValidator::isFloat(const std::string& value) {
    try {
        size_t pos;
        std::stod(value, &pos);
        return pos == value.length();
    } catch (...) {
        return false;
    }
}

} // namespace Rag