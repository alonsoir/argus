#include "rag/llama_integration.hpp"
#include <iostream>
#include <string>

class LlamaIntegration::Impl {
private:
    bool model_loaded = false;

public:
    bool loadModel(const std::string& model_path) {
        std::cout << "🤖 SIMULACIÓN: Cargando modelo " << model_path << std::endl;

        // Simular carga exitosa del modelo
        model_loaded = true;
        std::cout << "✅ Modelo simulado cargado correctamente" << std::endl;
        std::cout << "💡 Nota: Ejecutando en modo simulación. Las respuestas son predefinidas." << std::endl;
        return true;
    }

    std::string generateResponse(const std::string& prompt) {
        if (!model_loaded) {
            return "❌ Error: Modelo no cargado";
        }

        std::cout << "🎯 Procesando consulta: \"" << prompt << "\"" << std::endl;

        // Convertir a minúsculas para comparación más fácil
        std::string lower_prompt = prompt;
        for (char& c : lower_prompt) {
            c = std::tolower(c);
        }

        // Respuestas simuladas contextuales inteligentes
        if (lower_prompt.find("hola") != std::string::npos ||
            lower_prompt.find("buenas") != std::string::npos ||
            lower_prompt.find("hello") != std::string::npos) {
            return "¡Hola! Soy tu asistente de seguridad RAG. Estoy funcionando en modo simulación. ¿En qué puedo ayudarte?";
        }
        else if (lower_prompt.find("como estas") != std::string::npos ||
                 lower_prompt.find("qué tal") != std::string::npos) {
            return "¡Estoy funcionando correctamente en modo simulación! Listo para analizar comandos y consultas de seguridad.";
        }
        else if (lower_prompt.find("rm -rf") != std::string::npos ||
                 lower_prompt.find("format") != std::string::npos ||
                 lower_prompt.find("dd if=/dev/zero") != std::string::npos) {
            return "🔴 **ALTA PELIGROSIDAD**: Este comando puede causar pérdida irreversible de datos.\n"
                   "   - rm -rf /: Elimina recursivamente todo el sistema de archivos\n"
                   "   - ⚠️  NO EJECUTAR sin verificación exhaustiva\n"
                   "   - Recomendación: Usar con rutas específicas y verificar permisos";
        }
        else if (lower_prompt.find("chmod 777") != std::string::npos ||
                 lower_prompt.find("chmod 666") != std::string::npos) {
            return "🟡 **SOSPECHOSO**: Asignación de permisos excesivos\n"
                   "   - chmod 777: Da permisos de lectura, escritura y ejecución a todos\n"
                   "   - Riesgo: Exposición de archivos sensibles\n"
                   "   - Recomendación: Usar permisos más restrictivos (755, 644)";
        }
        else if (lower_prompt.find("curl") != std::string::npos &&
                 lower_prompt.find("| bash") != std::string::npos) {
            return "🟡 **SOSPECHOSO**: Descarga y ejecución remota\n"
                   "   - curl | bash: Ejecuta código remoto sin verificación\n"
                   "   - Riesgo: Ejecución de código malicioso\n"
                   "   - Recomendación: Verificar la fuente antes de ejecutar";
        }
        else if (lower_prompt.find("firewall") != std::string::npos ||
                 lower_prompt.find("iptables") != std::string::npos ||
                 lower_prompt.find("ufw") != std::string::npos) {
            return "🔵 **CONFIGURACIÓN DE FIREWALL**:\n"
                   "   - ufw enable: Activar firewall Uncomplicated Firewall\n"
                   "   - iptables -A INPUT -p tcp --dport 22 -j ACCEPT: Permitir SSH\n"
                   "   - ufw allow 80/tcp: Permitir tráfico HTTP\n"
                   "   - Recomendación: Seguir principio de mínimo privilegio";
        }
        else if (lower_prompt.find("seguridad") != std::string::npos ||
                 lower_prompt.find("security") != std::string::npos) {
            return "🛡️  **ANÁLISIS DE SEGURIDAD**:\n"
                   "   - Puedo analizar comandos potencialmente peligrosos\n"
                   "   - Identificar configuraciones de riesgo\n"
                   "   - Sugerir mejores prácticas de seguridad\n"
                   "   - Proporcionar alternativas más seguras";
        }
        else if (lower_prompt.find("ls") != std::string::npos ||
                 lower_prompt.find("pwd") != std::string::npos ||
                 lower_prompt.find("cd ") != std::string::npos) {
            return "🟢 **SEGURO**: Comandos básicos de navegación\n"
                   "   - ls: Listar directorios\n"
                   "   - pwd: Mostrar directorio actual\n"
                   "   - cd: Cambiar directorio\n"
                   "   - Riesgo: Bajo (solo lectura/información)";
        }
        else if (lower_prompt.find("qué es") != std::string::npos ||
                 lower_prompt.find("que es") != std::string::npos ||
                 lower_prompt.find("explica") != std::string::npos) {
            return "📚 **RESPUESTA INFORMATIVA**:\n"
                   "   - En modo simulación, proporciono respuestas predefinidas\n"
                   "   - Cuando el modelo LLM esté disponible, generaré respuestas más específicas\n"
                   "   - Actualmente analizo: comandos Linux, seguridad, configuraciones";
        }
        else {
            return "🤖 **MODO SIMULACIÓN**: He procesado tu consulta: \"" + prompt + "\"\n"
                   "   - Tipo: Consulta general\n"
                   "   - Estado: Procesada en modo simulación\n"
                   "   - ¿Necesitas un análisis de seguridad específico o información técnica?";
        }
    }

    ~Impl() {
        // Limpieza simulada
        if (model_loaded) {
            std::cout << "🧹 Limpiando recursos de simulación..." << std::endl;
        }
    }
};

// Implementaciones wrapper
LlamaIntegration::LlamaIntegration() : pImpl(std::make_unique<Impl>()) {}
LlamaIntegration::~LlamaIntegration() = default;

bool LlamaIntegration::loadModel(const std::string& model_path) {
    return pImpl->loadModel(model_path);
}

std::string LlamaIntegration::generateResponse(const std::string& prompt) {
    return pImpl->generateResponse(prompt);
}