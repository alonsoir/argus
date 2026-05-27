#include "rag/whitelist_manager.hpp"
#include <iostream>
#include <sstream>

namespace Rag {

WhiteListManager::WhiteListManager()
    : config_manager_(ConfigManager::getInstance()) {  // Inicializar referencia
    // WhiteListManager es el único que crea y usa EtcdClient
    etcd_client_ = std::make_unique<EtcdClient>(config_manager_.getEtcdEndpoint(), "security-system");
    std::cout << "🔧 Inicializando WhiteListManager..." << std::endl;
}

WhiteListManager::~WhiteListManager() {
    unregisterSystemFromEtcd();
    std::cout << "🔧 WhiteListManager finalizado" << std::endl;
}

bool WhiteListManager::initialize() {
    if (!etcd_client_->initialize()) {
        std::cerr << "❌ Error inicializando etcd client" << std::endl;
        return false;
    }

    registerSystemWithEtcd();
    return true;
}

void WhiteListManager::registerCommandManager(const std::string& component_name,
                                            std::shared_ptr<CommandManager> manager) {
    command_managers_[component_name] = manager;
    std::cout << "✅ Registrado manager para componente: " << component_name << std::endl;

    // Registrar automáticamente el componente en etcd
    auto config = config_manager_.getConfigForEtcd();
    registerComponentInEtcd(component_name, config);
}

void WhiteListManager::processCommand(const std::string& input) {
    auto tokens = tokenizeCommand(input);
    if (tokens.empty()) return;

    std::string component = tokens[0];

    if (component == "help") {
        showHelp();
        return;
    }

    if (component == "exit") {
        std::cout << "👋 Saliendo del sistema..." << std::endl;
        exit(0);
    }

    auto it = command_managers_.find(component);
    if (it != command_managers_.end()) {
        // Eliminar el componente de los tokens y pasar el resto al manager
        std::vector<std::string> command_args(tokens.begin() + 1, tokens.end());
        it->second->processCommand(command_args);
    } else {
        std::cout << "❌ Componente no reconocido: " << component << std::endl;
        std::cout << "💡 Componentes disponibles: ";
        for (const auto& [name, _] : command_managers_) {
            std::cout << name << " ";
        }
        std::cout << std::endl;
    }
}

void WhiteListManager::showHelp() const {
    std::cout << "\n🎯 SISTEMA DE SEGURIDAD - COMANDOS DISPONIBLES" << std::endl;
    std::cout << "==============================================" << std::endl;

    for (const auto& [component, manager] : command_managers_) {
        std::cout << component << " [comando] - Comandos para " << component << std::endl;
        std::cout << "   show_config          - Mostrar configuración" << std::endl;
        std::cout << "   update_setting <k> <v> - Actualizar setting" << std::endl;
        std::cout << "   show_capabilities    - Mostrar capacidades" << std::endl;
        std::cout << "   ask_llm <pregunta>   - Consultar al LLM (TinyLlama)" << std::endl;
    }

    std::cout << "help                      - Mostrar esta ayuda" << std::endl;
    std::cout << "exit                      - Salir del sistema" << std::endl;
    std::cout << "==============================================" << std::endl;
    std::cout << "Componentes activos: ";
    for (const auto& [name, _] : command_managers_) {
        std::cout << name << " ";
    }
    std::cout << std::endl;
}

bool WhiteListManager::registerComponentInEtcd(const std::string& component_name, const nlohmann::json& config) {
    std::cout << "🌐 Registrando componente '" << component_name << "' en etcd..." << std::endl;
    // Usar etcd_client_ para registrar el componente
    return etcd_client_->update_component_config(component_name, config.dump());
}

bool WhiteListManager::unregisterComponentFromEtcd(const std::string& component_name) {
    std::cout << "🌐 Desregistrando componente '" << component_name << "' de etcd..." << std::endl;
    // Lógica para desregistrar componente específico
    return true; // Implementar según necesidad
}

bool WhiteListManager::updateComponentConfigInEtcd(const std::string& component_name, const std::string& config) {
    // Actualizar configuración del componente en etcd
    return etcd_client_->update_component_config(component_name, config);
}

void WhiteListManager::registerSystemWithEtcd() {
    std::cout << "🌐 Registrando sistema completo en etcd-server..." << std::endl;
    if (etcd_client_->registerService()) {
        std::cout << "✅ Registro en etcd completado" << std::endl;
    } else {
        std::cerr << "❌ Error en registro etcd" << std::endl;
    }
}

void WhiteListManager::unregisterSystemFromEtcd() {
    std::cout << "🌐 Desregistrando sistema de etcd..." << std::endl;
    if (etcd_client_->unregisterService()) {
        std::cout << "✅ Sistema desregistrado correctamente" << std::endl;
    } else {
        std::cerr << "❌ Error al desregistrar sistema" << std::endl;
    }
}

std::vector<std::string> WhiteListManager::tokenizeCommand(const std::string& input) {
    std::vector<std::string> tokens;
    std::istringstream iss(input);
    std::string token;

    while (iss >> token) {
        tokens.push_back(token);
    }

    return tokens;
}

} // namespace Rag