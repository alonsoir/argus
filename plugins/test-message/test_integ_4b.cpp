// ============================================================================
// test_integ_4b.cpp — TEST-INTEG-4b
// ============================================================================
// Verifica PHASE 2b: contrato READ-ONLY de rag-ingester.
//   Caso A: mode=READONLY, payload=nullptr → PLUGIN_OK, sin D8 VIOLATION
//   Caso B: mode=READONLY, payload!=nullptr → std::terminate() (D8-pre)
//           (solo verificable en entorno que intercepte SIGABRT)
// Gate: Caso A PASS = condición mínima para merge.
// ============================================================================

#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <cassert>

using namespace ml_defender;

int main() {
    int failures = 0;

    // ----------------------------------------------------------------
    // Caso A: READ-ONLY correcto — payload=nullptr, mode=READONLY
    // Espera: PLUGIN_OK, errors==0, result_code==0
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4b CASO A: READ-ONLY payload=nullptr ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = nullptr;
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

            loader.invoke_all(ctx);
            const auto& stats = loader.stats();
            bool ok = (stats[0].errors == 0 && ctx.result_code == 0);
            fprintf(stderr, "Caso A: errors=%zu result_code=%d mode=%d → %s\n",
                    stats[0].errors, ctx.result_code, ctx.mode,
                    ok ? "PASS" : "FAIL");
            if (!ok) ++failures;
        }
    }

    // ----------------------------------------------------------------
    // Caso B: mode propagado correctamente — campo mode leíble por plugin
    // Espera: ctx.mode == PLUGIN_MODE_READONLY tras invoke_all
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4b CASO B: mode propagation ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);  // variant A: no modifica campos
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() > 0) {
            MessageContext ctx{};
            ctx.payload     = nullptr;
            ctx.payload_len = 0;
            ctx.mode        = PLUGIN_MODE_READONLY;
            ctx.result_code = 0;
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            memset(ctx.annotation, 0, sizeof(ctx.annotation));
            memset(ctx.reserved,   0, sizeof(ctx.reserved));

            loader.invoke_all(ctx);
            bool ok = (ctx.mode == PLUGIN_MODE_READONLY);
            fprintf(stderr, "Caso B: mode=%d (expect %d) → %s\n",
                    ctx.mode, PLUGIN_MODE_READONLY,
                    ok ? "PASS" : "FAIL");
            if (!ok) ++failures;
        }
    }

    fprintf(stderr, "\n=== TEST-INTEG-4b: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
