// ============================================================================
// hello_plugin.cpp — ML Defender Hello World Plugin
// ============================================================================
// Plugin de validación: no tiene lógica de seguridad.
// Propósito único: validar el contrato plugin_api.h end-to-end.
//
// Criterios de éxito (ADR-012):
//   [x] dlopen/dlsym funcionan correctamente
//   [x] plugin_init() recibe la config JSON parseada
//   [x] plugin_process_packet() se invoca en cada paquete
//   [x] plugin_shutdown() se llama limpiamente al cerrar el host
//   [ ] Si se elimina el .so, el host arranca sin errores (validar manualmente)
//   [ ] Si budget_us se excede, aparece warning en el log (validar manualmente)
// ============================================================================

#include "plugin_loader/plugin_api.h"
#include <cstdio>

extern "C" {

const char* plugin_name()        { return "hello"; }
const char* plugin_version()     { return "0.1.0"; }
int         plugin_api_version() { return PLUGIN_API_VERSION; }

PluginResult plugin_init(const PluginConfig* config) {
    fprintf(stderr, "[plugin:hello] init OK — name=%s config=%s\n",
            config->name, config->config_json);
    return PLUGIN_OK;
}

PluginResult plugin_process_packet(PacketContext* ctx) {
    fprintf(stderr, "[plugin:hello] packet src=%u:%u dst=%u:%u proto=%u len=%zu\n",
            ctx->src_ip, ctx->src_port,
            ctx->dst_ip, ctx->dst_port,
            ctx->protocol, ctx->length);
    // No modifica ctx->threat_hint — solo observa
    return PLUGIN_OK;
}

void plugin_shutdown() {
    fprintf(stderr, "[plugin:hello] shutdown OK\n");
}

} // extern "C"
