#pragma once
#include <vector>
#include <string>

namespace Rag {

    class CommandManager {
    public:
        virtual ~CommandManager() = default;

        // Método para procesar comandos específicos del componente
        virtual void processCommand(const std::vector<std::string>& args) = 0;

        // Métodos de comandos específicos que pueden ser implementados
        virtual void showConfig(const std::vector<std::string>& /*args*/) {}
        virtual void updateSetting(const std::vector<std::string>& /*args*/) {}
        virtual void showCapabilities(const std::vector<std::string>& /*args*/) {}
    };

} // namespace Rag