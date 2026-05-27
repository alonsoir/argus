#pragma once
#include <string>
#include <nlohmann/json.hpp>
#include <unordered_map>

// Estructuras para configuración
struct RagConfig {
    std::string host = "localhost";
    int port = 8080;
    std::string model_name = "unknown";
    int embedding_dimension = 512;
};

struct EtcdConfig {
    std::string host = "localhost";
    int port = 2379;
};

namespace Rag {

class ConfigManager {
public:
    ~ConfigManager();

    // Método Singleton
    static ConfigManager& getInstance() {
        static ConfigManager instance;
        return instance;
    }

    // Eliminar copia y asignación
    ConfigManager(const ConfigManager&) = delete;
    ConfigManager& operator=(const ConfigManager&) = delete;

    bool loadFromFile(const std::string& config_path = "../config/rag-config.json");
    bool saveToFile(const std::string& config_path = "");

    // Acceso a configuraciones
    std::string getModelPath() const;
    int getSecurityLevel() const;
    bool useLLM() const;
    std::string getEtcdEndpoint() const;
    std::string getLogLevel() const;

    // Métodos para estructura actual
    RagConfig getRagConfig() const;
    EtcdConfig getEtcdConfig() const;

    // Modificación de configuraciones
    bool updateSetting(const std::string& path, const std::string& value);
    bool updateSetting(const std::string& path, int value);
    bool updateSetting(const std::string& path, bool value);

    // Para registro en etcd
    nlohmann::json getConfigForEtcd() const;
    // Junto a getConfigForEtcd() en la sección public:
    const nlohmann::json& getRawConfig() const { return config_; }  // inline, header-only
    std::string getComponentId() const;

    /**
     * @brief Obtiene la configuración completa actual
     * @return Configuración actual como unordered_map
     */
    std::unordered_map<std::string, std::string> getConfig() const;

    /**
     * @brief Obtiene un valor específico de configuración
     * @param key Clave de configuración
     * @return Valor de la configuración o string vacío si no existe
     */
    std::string getConfigValue(const std::string& key) const;

private:
    ConfigManager() = default;
    nlohmann::json config_;
    std::string current_config_path_;

    bool validateConfig() const;
};

} // namespace Rag