#include "rag/config_manager.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#include <stdexcept>
// rag/src/config_manager.cpp

namespace Rag {

ConfigManager::~ConfigManager() = default;

bool ConfigManager::loadFromFile(const std::string& config_path) {
    try {
        std::ifstream file(config_path);
        if (!file.is_open()) {
            std::cerr << "❌ CRITICAL: Cannot open config file: " << config_path << std::endl;
            return false;
        }

        file >> config_;
        current_config_path_ = config_path;

        std::cout << "✅ Loaded RAG config from: " << config_path << std::endl;

        if (!validateConfig()) {
            std::cerr << "❌ CRITICAL: RAG config validation failed" << std::endl;
            return false;
        }

        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ CRITICAL: Error loading RAG config: " << e.what() << std::endl;
        return false;
    }
}

bool ConfigManager::saveToFile(const std::string& config_path) {
    std::string path = config_path.empty() ? current_config_path_ : config_path;
    if (path.empty()) {
        std::cerr << "❌ CRITICAL: No config path specified for save" << std::endl;
        return false;
    }

    try {
        std::ofstream file(path);
        if (!file.is_open()) {
            std::cerr << "❌ CRITICAL: Cannot open config file for writing: " << path << std::endl;
            return false;
        }

        file << config_.dump(4);
        std::cout << "✅ Saved RAG config to: " << path << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ CRITICAL: Error saving RAG config: " << e.what() << std::endl;
        return false;
    }
}

// Métodos de acceso
std::string ConfigManager::getModelPath() const {
    if (!config_.contains("rag") || !config_["rag"].contains("model_name") ||
        !config_["rag"]["model_name"].is_string()) {
        throw std::runtime_error("CRITICAL: rag.model_name not found in config");
    }
    return config_["rag"]["model_name"].get<std::string>();
}

int ConfigManager::getSecurityLevel() const {
    if (!config_.contains("security_level") || !config_["security_level"].is_number()) {
        return 3;
    }
    return config_["security_level"].get<int>();
}

bool ConfigManager::useLLM() const {
    if (!config_.contains("rag") || !config_["rag"].contains("use_llm") ||
        !config_["rag"]["use_llm"].is_boolean()) {
        return true;
    }
    return config_["rag"]["use_llm"].get<bool>();
}

std::string ConfigManager::getEtcdEndpoint() const {
    auto etcd_config = getEtcdConfig();
    return "http://" + etcd_config.host + ":" + std::to_string(etcd_config.port);
}

std::string ConfigManager::getLogLevel() const {
    if (!config_.contains("log_level") || !config_["log_level"].is_string()) {
        return "INFO";
    }
    return config_["log_level"].get<std::string>();
}

// Métodos para nueva estructura JSON
RagConfig ConfigManager::getRagConfig() const {
    RagConfig rag_config;

    if (config_.contains("rag")) {
        auto rag = config_["rag"];
        if (rag.contains("host") && rag["host"].is_string()) {
            rag_config.host = rag["host"].get<std::string>();
        }
        if (rag.contains("port") && rag["port"].is_number()) {
            rag_config.port = rag["port"].get<int>();
        }
        if (rag.contains("model_name") && rag["model_name"].is_string()) {
            rag_config.model_name = rag["model_name"].get<std::string>();
        }
        if (rag.contains("embedding_dimension") && rag["embedding_dimension"].is_number()) {
            rag_config.embedding_dimension = rag["embedding_dimension"].get<int>();
        }
    }

    return rag_config;
}

EtcdConfig ConfigManager::getEtcdConfig() const {
    EtcdConfig etcd_config;

    if (config_.contains("etcd")) {
        auto etcd = config_["etcd"];
        if (etcd.contains("host") && etcd["host"].is_string()) {
            etcd_config.host = etcd["host"].get<std::string>();
        }
        if (etcd.contains("port") && etcd["port"].is_number()) {
            etcd_config.port = etcd["port"].get<int>();
        }
    }

    return etcd_config;
}

// Métodos de modificación - SIN DUPLICADOS
bool ConfigManager::updateSetting(const std::string& path, const std::string& value) {
    try {
        if (config_.empty()) {
            throw std::runtime_error("Config not loaded");
        }

        if (path.find('.') == std::string::npos) {
            if (!config_.contains(path)) {
                throw std::runtime_error("Setting '" + path + "' not found in config");
            }
            config_[path] = value;
        } else {
            std::istringstream iss(path);
            std::string token;
            nlohmann::json* current = &config_;

            while (std::getline(iss, token, '.')) {
                if (current->is_object() && current->contains(token)) {
                    current = &(*current)[token];
                } else {
                    throw std::runtime_error("Config path '" + path + "' not found");
                }
            }
            *current = value;
        }

        std::cout << "✅ Updated config: " << path << " = " << value << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ CRITICAL: Error updating config '" << path << "': " << e.what() << std::endl;
        return false;
    }
}

bool ConfigManager::updateSetting(const std::string& path, int value) {
    return updateSetting(path, std::to_string(value));
}

bool ConfigManager::updateSetting(const std::string& path, bool value) {
    try {
        if (config_.empty()) {
            throw std::runtime_error("Config not loaded");
        }

        if (path.find('.') == std::string::npos) {
            if (!config_.contains(path)) {
                throw std::runtime_error("Setting '" + path + "' not found in config");
            }
            config_[path] = value;
        } else {
            std::istringstream iss(path);
            std::string token;
            nlohmann::json* current = &config_;

            while (std::getline(iss, token, '.')) {
                if (current->is_object() && current->contains(token)) {
                    current = &(*current)[token];
                } else {
                    throw std::runtime_error("Config path '" + path + "' not found");
                }
            }
            *current = value;
        }

        std::cout << "✅ Updated config: " << path << " = " << (value ? "true" : "false") << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ CRITICAL: Error updating config '" << path << "': " << e.what() << std::endl;
        return false;
    }
}

nlohmann::json ConfigManager::getConfigForEtcd() const {
    if (config_.empty()) {
        throw std::runtime_error("CRITICAL: Config not loaded for etcd registration");
    }
    return config_;
}

std::string ConfigManager::getComponentId() const {
    if (!config_.contains("id") || !config_["id"].is_string()) {
        throw std::runtime_error("CRITICAL: 'id' field not found in config");
    }
    return config_["id"].get<std::string>();
}

std::unordered_map<std::string, std::string> ConfigManager::getConfig() const {
    std::unordered_map<std::string, std::string> result;

    // CORREGIR: Iterar correctamente sobre nlohmann::json
    for (auto& [key, value] : config_.items()) {
        if (value.is_string()) {
            result[key] = value.get<std::string>();
        } else {
            result[key] = value.dump(); // Convertir a string
        }
    }
    return result;
}

std::string ConfigManager::getConfigValue(const std::string& key) const {
    // CORREGIR: nlohmann::json se accede diferente a unordered_map
    if (config_.contains(key)) {
        if (config_[key].is_string()) {
            return config_[key].get<std::string>();
        } else {
            return config_[key].dump(); // Convertir a string para otros tipos
        }
    }
    return "";
}

bool ConfigManager::validateConfig() const {
    if (!config_.contains("rag")) {
        std::cerr << "❌ CRITICAL: 'rag' section is required" << std::endl;
        return false;
    }

    auto rag = config_["rag"];
    if (!rag.contains("host") || !rag["host"].is_string()) {
        std::cerr << "❌ CRITICAL: 'rag.host' field is required and must be a string" << std::endl;
        return false;
    }

    if (!rag.contains("port") || !rag["port"].is_number()) {
        std::cerr << "❌ CRITICAL: 'rag.port' field is required and must be a number" << std::endl;
        return false;
    }

    if (!rag.contains("model_name") || !rag["model_name"].is_string()) {
        std::cerr << "❌ CRITICAL: 'rag.model_name' field is required and must be a string" << std::endl;
        return false;
    }

    if (!config_.contains("etcd")) {
        std::cerr << "❌ CRITICAL: 'etcd' section is required" << std::endl;
        return false;
    }

    auto etcd = config_["etcd"];
    if (!etcd.contains("host") || !etcd["host"].is_string()) {
        std::cerr << "❌ CRITICAL: 'etcd.host' field is required and must be a string" << std::endl;
        return false;
    }

    std::cout << "✅ RAG config validation passed - all critical fields present" << std::endl;
    return true;
}

} // namespace Rag