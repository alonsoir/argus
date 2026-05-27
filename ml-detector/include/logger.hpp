#pragma once

#include <spdlog/spdlog.h>
#include <memory>
#include <string>

namespace ml_detector {

/**
 * @brief Logger wrapper para spdlog
 */
class Logger {
public:
    /**
     * @brief Crear logger con console y file sinks
     * @param name Nombre del logger
     * @param log_file Ruta al archivo de log (vacío = solo console)
     * @param level Nivel de logging
     */
    static std::shared_ptr<spdlog::logger> create(
        const std::string& name,
        const std::string& log_file = "",
        spdlog::level::level_enum level = spdlog::level::info
    );
    
    /**
     * @brief Cambiar nivel global de logging
     */
    static void set_level(spdlog::level::level_enum level);
    
    /**
     * @brief Shutdown de todos los loggers
     */
    static void shutdown();
};

} // namespace ml_detector
