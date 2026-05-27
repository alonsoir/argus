// ============================================================================
// plugin_test_message.cpp — Test plugin para TEST-INTEG-4a-PLUGIN
// ============================================================================
// Tres variantes seleccionables por MLD_TEST_VARIANT (A, B, C).
//
// Variante A (default): exporta símbolo, result_code=0, no modifica nada
//   → debe pasar sin errores. Gate: smoke test OK.
//
// Variante B: intenta const_cast sobre direction
//   → D8 pointer check detecta violación.
//
// Variante C: devuelve result_code=-1
//   → host registra error en stats, no std::terminate().
// ============================================================================

#include "plugin_loader/plugin_api.h"
#include <cstdlib>   // getenv
#include <cstring>   // strcmp
#include <cstdio>    // fprintf

#ifdef __cplusplus
extern "C" {
#endif

// ----------------------------------------------------------------------------
// Identificación
// ----------------------------------------------------------------------------
const char* plugin_name()        { return "test-message"; }
const char* plugin_version()     { return "0.1.0"; }
int         plugin_api_version() { return PLUGIN_API_VERSION; }

// ----------------------------------------------------------------------------
// Ciclo de vida
// ----------------------------------------------------------------------------
PluginResult plugin_init(const PluginConfig* config) {
    const char* variant = getenv("MLD_TEST_VARIANT");
    if (!variant) variant = "A";
    fprintf(stderr, "[test-message] plugin_init: variant=%s\n", variant);
    (void)config;
    return PLUGIN_OK;
}

PluginResult plugin_process_packet(PacketContext* ctx) {
    (void)ctx;
    return PLUGIN_OK;
}

void plugin_shutdown() {
    fprintf(stderr, "[test-message] plugin_shutdown\n");
}

// ----------------------------------------------------------------------------
// plugin_process_message — variantes A / B / C
// ----------------------------------------------------------------------------
PluginResult plugin_process_message(MessageContext* ctx) {
    const char* variant = getenv("MLD_TEST_VARIANT");
    if (!variant) variant = "A";

    // --- Variante A: comportamiento correcto, no toca nada read-only ---
    if (variant[0] == 'A') {
        ctx->result_code = 0;
        // Anotación informativa (campo write)
        const char* ann = "variant-A-ok";
        for (int i = 0; i < 63 && ann[i]; ++i) ctx->annotation[i] = ann[i];
        ctx->annotation[63] = '\0';
        fprintf(stderr, "[test-message] variant A: OK\n");
        return PLUGIN_OK;
    }

    // --- Variante B: intenta modificar campo read-only (direction) ---
    // D7: plugins son UNTRUSTED. D8 debe detectar esta violación.
    if (variant[0] == 'B') {
        fprintf(stderr, "[test-message] variant B: intentando const_cast sobre direction\n");
        // El puntero ctx.payload apunta a memoria const — no modificamos el contenido
        // del payload (CRC no cambiaría), pero sí modificamos direction via const_cast,
        // lo que D8 pointer/value check debe detectar.
        uint8_t* mutable_direction = const_cast<uint8_t*>(&ctx->direction);
        *mutable_direction = ctx->direction ^ 0x01u;  // flip bit — D8 violation
        ctx->result_code = 0;
        return PLUGIN_OK;
    }

    // --- Variante C: señaliza anomalía via result_code ---
    // El host debe registrar error en stats sin crash ni std::terminate().
    if (variant[0] == 'C') {
        fprintf(stderr, "[test-message] variant C: returning result_code=-1 (anomaly)\n");
        ctx->result_code = -1;
        return PLUGIN_ERROR;
    }

    // Fallback
    ctx->result_code = 0;
    return PLUGIN_OK;
}

#ifdef __cplusplus
}
#endif
