#pragma once
#include <string>
#include <vector>
#include <algorithm>
#include <map>
#include <iostream>

namespace Rag {

enum class ValidationType {
    INTEGER,
    FLOAT,
    BOOLEAN,
    STRING,
    PORT,
    THRESHOLD,
    LOG_LEVEL,
    FILE_PATH,
    HOST_NAME,
    IP_ADDRESS
};

struct ValidationRule {
    ValidationType type;
    std::string field_name;
    double min_value = 0.0;
    double max_value = 0.0;
    std::vector<std::string> allowed_values;
    std::string custom_error;
};

class BaseValidator {
public:
    virtual ~BaseValidator() = default;

    // Método principal de validación
    virtual bool validate(const std::string& field_name, const std::string& value) const;

    // Método para que los validadores específicos registren sus reglas
    virtual void registerValidationRules() = 0;

    // Método para agregar reglas personalizadas
    void addRule(const std::string& field_name, ValidationType type,
                 double min_val = 0.0, double max_val = 0.0,
                 const std::vector<std::string>& allowed_values = {},
                 const std::string& custom_error = "");

protected:
    std::map<std::string, ValidationRule> validation_rules_;

    // Métodos de validación básicos (implementados en .cpp)
    bool validateInteger(const std::string& value, double min_val, double max_val, const std::string& field_name = "") const;
    bool validateFloat(const std::string& value, double min_val, double max_val, const std::string& field_name = "") const;
    bool validateBoolean(const std::string& value, const std::string& field_name = "") const;
    bool validateString(const std::string& value, size_t max_length, const std::string& field_name = "") const;
    bool validatePort(const std::string& value, const std::string& field_name = "") const;
    bool validateThreshold(const std::string& value, const std::string& field_name = "") const;
    bool validateLogLevel(const std::string& value, const std::string& field_name = "") const;
    bool validateFilePath(const std::string& value, const std::string& field_name = "") const;
    bool validateHostName(const std::string& value, const std::string& field_name = "") const;
    bool validateIpAddress(const std::string& value, const std::string& field_name = "") const;

    // Método de detección automática para campos no registrados
    bool autoDetectAndValidate(const std::string& field_name, const std::string& value) const;

    // Métodos auxiliares
    static std::string toLower(const std::string& str);
    static std::string toUpper(const std::string& str);
    static bool isInteger(const std::string& value);
    static bool isFloat(const std::string& value);
};

} // namespace Rag