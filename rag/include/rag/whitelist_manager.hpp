#pragma once
#include "rag/command_manager.hpp"
#include "rag/etcd_client.hpp"
#include "rag/config_manager.hpp"
#include <memory>
#include <unordered_map>
#include <vector>
#include <string>

namespace Rag {

    class WhiteListManager {
    public:
        WhiteListManager();
        ~WhiteListManager();

        bool initialize();
        void processCommand(const std::string& input);
        void registerCommandManager(const std::string& component_name,
                                   std::shared_ptr<CommandManager> manager);
        void showHelp() const;

        // Métodos para gestión de etcd
        bool registerComponentInEtcd(const std::string& component_name, const nlohmann::json& config);
        bool unregisterComponentFromEtcd(const std::string& component_name);
        bool updateComponentConfigInEtcd(const std::string& component_name, const std::string& config);

    private:
        std::unordered_map<std::string, std::shared_ptr<CommandManager>> command_managers_;
        std::unique_ptr<EtcdClient> etcd_client_;
        // Cambiar a referencia en lugar de shared_ptr
        ConfigManager& config_manager_;
        void registerSystemWithEtcd();
        void unregisterSystemFromEtcd();
        std::vector<std::string> tokenizeCommand(const std::string& input);

        void handleQuerySimilar(const std::vector<std::string>& tokens);
    };

} // namespace Rag