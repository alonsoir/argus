#pragma once
#include <atomic>
// ============================================================================
// plugin_loader.hpp — ML Defender Plugin Loader Interface
// ============================================================================
// Gestiona el ciclo de vida de plugins cargados vía dlopen/dlsym (lazy).
// Un componente host instancia esta clase, llama a load_plugins() en init,
// invoke_all() en cada paquete, y shutdown() al cerrar.
//
// Sin crypto. Sin seed-client. PHASE 1 — solo carga + resolución de símbolos.
// Autenticación de plugins: PHASE 2 (ADR-013, seed-client DAY 95-96).
// ============================================================================

#include <string>
#include <vector>
#include <memory>
#include <cstdint>
#include "plugin_api.h"

namespace ml_defender {

// ----------------------------------------------------------------------------
// PluginStats — estadísticas por plugin, accesibles al host
// ----------------------------------------------------------------------------
struct PluginStats {
    std::string name;
    uint64_t    invocations      = 0;
    uint64_t    budget_overruns  = 0;
    uint64_t    errors           = 0;
};

// ----------------------------------------------------------------------------
// PluginLoader — gestor de plugins dlopen-based
// ----------------------------------------------------------------------------
static constexpr size_t MAX_PLUGIN_PAYLOAD_SIZE = 65536; // 64KB — D8 extendido (FIX-D, Consejo DAY 110)

class PluginLoader {
public:
    // config_json_path: ruta al JSON del componente host (ej: "config/sniffer.json")
    // El loader lee la sección "plugins" de ese JSON.
    explicit PluginLoader(const std::string& config_json_path);
    ~PluginLoader();

    // Carga todos los plugins habilitados en plugins.enabled[].
    // - Si un .so no existe: warning + continue (NUNCA abort del componente host)
    // - Si plugin_api_version() != PLUGIN_API_VERSION: warning + skip
    // - Llama a plugin_init() en cada plugin cargado correctamente
    void load_plugins();

    // Invoca plugin_process_packet() en todos los plugins cargados.
    // Mide latencia. Si elapsed_us > budget_us_, incrementa budget_overruns.
    void invoke_all(PacketContext& ctx);

    // Invoca plugin_process_message() en todos los plugins que lo exporten.
    // ADR-023 PHASE 2a — Graceful Degradation D1: plugins sin este símbolo
    // son silenciosamente omitidos (no son descartados del loader).
    // Post-invocation: valida invariantes read-only (D8).
    void invoke_all(MessageContext& ctx);

    // Llama a plugin_shutdown() en todos los plugins y hace dlclose.
    void shutdown();

    // Estadísticas por plugin (para health endpoint o logging periódico)
    const std::vector<PluginStats>& stats() const;

    // Número de plugins cargados correctamente
    size_t loaded_count() const;

private:
    struct LoadedPlugin;
    std::vector<std::shared_ptr<LoadedPlugin>> plugins_;
    std::vector<PluginStats>                   stats_;
    std::string                                config_path_;
    uint32_t                                   budget_us_ = 100; // default: 100µs
    std::atomic<bool>                          shutdown_called_{false};
};

}  // namespace ml_defender
