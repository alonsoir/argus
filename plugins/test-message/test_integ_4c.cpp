// ============================================================================
// test_integ_4c.cpp — TEST-INTEG-4c
// ============================================================================
// Verifica PHASE 2c: contrato NORMAL del sniffer con payload real.
//   Caso A: NORMAL + payload real presente → PLUGIN_OK, errors==0
//   Caso B: NORMAL + plugin intenta modificar campo read-only → D8 VIOLATION
//           (verificamos que snap != post-invocation → errors>0)
//   Caso C: NORMAL + result_code=-1 → error registrado, no crash
// Gate: Caso A + Caso C PASS = condición mínima para merge.
// Consejo DAY 110: Grok propuso estos 3 casos.
// ============================================================================
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <cassert>
using namespace ml_defender;

static uint8_t fake_payload[64] = {
    0x45, 0x00, 0x00, 0x3c, 0x1c, 0x46, 0x40, 0x00,
    0x40, 0x06, 0x00, 0x00, 0xc0, 0xa8, 0x00, 0x01,
    0xc0, 0xa8, 0x00, 0x02, 0x30, 0x39, 0x00, 0x50,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x50, 0x02, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x47, 0x45, 0x54, 0x20, 0x2f, 0x20, 0x48, 0x54,
    0x54, 0x50, 0x2f, 0x31, 0x2e, 0x31, 0x0d, 0x0a,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

int main() {
    int failures = 0;

    // ----------------------------------------------------------------
    // Caso A: NORMAL correcto — payload real presente
    // Espera: PLUGIN_OK, errors==0, result_code==0
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4c CASO A: NORMAL + payload real ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = fake_payload;
            ctx.payload_len = sizeof(fake_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
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
            int errs = 0;
            for (auto& s : loader.stats()) errs += (int)s.errors;
            int rc   = ctx.result_code;
            if (errs == 0 && rc == 0) {
                fprintf(stderr, "Caso A: errors=%d result_code=%d mode=%d → PASS\n",
                        errs, rc, ctx.mode);
            } else {
                fprintf(stderr, "Caso A: FAIL errors=%d result_code=%d\n", errs, rc);
                failures++;
            }
        }
    }

    // ----------------------------------------------------------------
    // Caso B: D8 VIOLATION — plugin modifica src_ip (campo read-only)
    // Espera: errors>0 (D8 post-invocation catch)
    // Variante B del test-message modifica ctx.src_ip
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4c CASO B: D8 VIOLATION campo read-only ===\n");
    setenv("MLD_TEST_VARIANT", "B", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = fake_payload;
            ctx.payload_len = sizeof(fake_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
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
            int errs = 0;
            for (auto& s : loader.stats()) errs += (int)s.errors;
            if (errs > 0) {
                fprintf(stderr, "Caso B: errors=%d → D8 VIOLATION detectada → PASS\n", errs);
            } else {
                fprintf(stderr, "Caso B: FAIL — D8 VIOLATION no detectada errors=%d\n", errs);
                failures++;
            }
        }
    }

    // ----------------------------------------------------------------
    // Caso C: result_code=-1 → error registrado, no crash
    // Espera: errors==1, proceso sigue vivo
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4c CASO C: result_code=-1 no crash ===\n");
    setenv("MLD_TEST_VARIANT", "C", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = fake_payload;
            ctx.payload_len = sizeof(fake_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
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
            int errs = 0;
            for (auto& s : loader.stats()) errs += (int)s.errors;
            if (errs == 1) {
                fprintf(stderr, "Caso C: errors=%d → PASS (no crash = OK)\n", errs);
            } else {
                fprintf(stderr, "Caso C: FAIL errors=%d (esperado 1)\n", errs);
                failures++;
            }
        }
    }

    fprintf(stderr, "\n=== TEST-INTEG-4c: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
