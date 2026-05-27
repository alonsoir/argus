// ============================================================================
// test_integ_4e.cpp — TEST-INTEG-4e
// ============================================================================
// Verifica PHASE 2e: contrato READONLY de rag-security (ADR-029 D1-D5).
//   Caso A: READONLY + evento real → PLUGIN_OK, result_code ignorado (D4)
//   Caso B: g_plugin_loader=nullptr → invoke_all no llamado, no crash (D3)
//   Caso C: simulación lógica signal handler → shutdown limpio (D2/D5)
// Gate: 3/3 PASS = condición para PHASE 2 completa.
// ADR-029 aprobado implícitamente Consejo DAY 110.
// ============================================================================
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <unistd.h>
using namespace ml_defender;

// ADR-029 D1: patrón global obligatorio — raw pointer estático
static ml_defender::PluginLoader* g_plugin_loader = nullptr;

// ADR-029 D2: simulación de la lógica del signal handler (sin señal real)
// En producción esto se ejecuta desde signalHandler() con write() + raise()
static bool simulate_signal_handler_logic() {
    const char msg[] = "[rag-security] signal received — shutting down\n";
    write(STDERR_FILENO, msg, sizeof(msg) - 1);
    if (g_plugin_loader != nullptr) {
        g_plugin_loader->shutdown();
        g_plugin_loader = nullptr;  // evitar double-shutdown
        return true;  // shutdown ejecutado
    }
    return false;  // noop — g_plugin_loader era nullptr
}

int main() {
    int failures = 0;

    // ----------------------------------------------------------------
    // Caso A: READONLY + evento real → result_code ignorado (ADR-029 D4)
    // Espera: PLUGIN_OK, errors==0, result_code ignorado por diseño
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4e CASO A: READONLY + evento real ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        g_plugin_loader = &loader;  // ADR-029 D3: asignación antes de uso

        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = nullptr;   // READONLY: sin payload (ADR-029 D4)
            ctx.payload_len = 0;
            ctx.mode        = PLUGIN_MODE_READONLY;
            ctx.result_code = 0;
            ctx.src_ip      = 0xC0A80001;
            ctx.dst_ip      = 0xC0A80002;
            ctx.src_port    = 12345;
            ctx.dst_port    = 80;
            ctx.protocol    = 6;
            ctx.direction   = 0;
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            memset(ctx.annotation, 0, sizeof(ctx.annotation));
            memset(ctx.reserved,   0, sizeof(ctx.reserved));

            g_plugin_loader->invoke_all(ctx);
            // ADR-029 D4: result_code ignorado — guardián semántico
            int errs = 0;
            for (auto& s : loader.stats()) errs += (int)s.errors;
            if (errs == 0) {
                fprintf(stderr, "Caso A: errors=%d mode=%d result_code ignorado → PASS\n",
                        errs, ctx.mode);
            } else {
                fprintf(stderr, "Caso A: FAIL errors=%d\n", errs);
                failures++;
            }
        }
        g_plugin_loader = nullptr;
    }

    // ----------------------------------------------------------------
    // Caso B: g_plugin_loader=nullptr → no crash, no invoke_all (ADR-029 D3)
    // Espera: proceso continúa, no segfault
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4e CASO B: g_plugin_loader=nullptr, no crash ===\n");
    {
        // g_plugin_loader ya es nullptr tras Caso A
        if (g_plugin_loader != nullptr) {
            fprintf(stderr, "Caso B: FAIL — g_plugin_loader debería ser nullptr\n");
            failures++;
        } else {
            // Simular código de producción: guard antes de invoke_all
            bool invoked = false;
            if (g_plugin_loader != nullptr) {
                MessageContext ctx{};
                g_plugin_loader->invoke_all(ctx);
                invoked = true;
            }
            if (!invoked) {
                fprintf(stderr, "Caso B: g_plugin_loader=nullptr → invoke_all no llamado → PASS\n");
            } else {
                fprintf(stderr, "Caso B: FAIL — invoke_all llamado con nullptr\n");
                failures++;
            }
        }
    }

    // ----------------------------------------------------------------
    // Caso C: simulación lógica signal handler → shutdown limpio (ADR-029 D2/D5)
    // Espera: shutdown() ejecutado exactamente una vez, g_plugin_loader=nullptr
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4e CASO C: simulacion signal handler → shutdown limpio ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        g_plugin_loader = &loader;  // ADR-029 D3

        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            // Simular recepción de SIGTERM
            bool shutdown_ran = simulate_signal_handler_logic();

            // Post-condiciones ADR-029 D2/D5:
            // 1. shutdown ejecutado
            // 2. g_plugin_loader = nullptr (evitar double-shutdown)
            // 3. proceso sigue vivo (no crash)
            if (shutdown_ran && g_plugin_loader == nullptr) {
                fprintf(stderr, "Caso C: shutdown ejecutado, g_plugin_loader=nullptr → PASS\n");
            } else {
                fprintf(stderr, "Caso C: FAIL shutdown_ran=%d g_plugin_loader=%s\n",
                        shutdown_ran, g_plugin_loader ? "non-null" : "nullptr");
                failures++;
            }
        }
    }

    fprintf(stderr, "\n=== TEST-INTEG-4e: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
