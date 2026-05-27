// ============================================================================
// test_integ_4d.cpp — TEST-INTEG-4d
// ============================================================================
// Verifica PHASE 2d: contrato NORMAL del ml-detector con evento puntuado.
//   Caso A: NORMAL + annotation con score ML real → PLUGIN_OK, errors==0
//   Caso B: NORMAL + plugin intenta modificar campo read-only → D8 VIOLATION
//           (verificamos que errors>0)
//   Caso C: NORMAL + result_code=-1 → error registrado, no crash
// Gate: Caso A + Caso C PASS = condición mínima para merge.
// Árbitro DAY 114: TEST-INTEG-4d es condición bloqueante del merge ADR-025.
// ============================================================================
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <cassert>
using namespace ml_defender;

// Payload simulando un evento de red procesado por ml-detector
// (cabecera IP/TCP similar a 4c — el ml-detector ya ha calculado el score)
static uint8_t ml_event_payload[64] = {
    0x45, 0x00, 0x00, 0x3c, 0x2b, 0x57, 0x40, 0x00,
    0x40, 0x06, 0x00, 0x00, 0xc0, 0xa8, 0x00, 0x0a,
    0xc0, 0xa8, 0x00, 0x01, 0xc4, 0x1f, 0x1f, 0x90,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x50, 0x02, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x47, 0x45, 0x54, 0x20, 0x2f, 0x61, 0x64, 0x6d,
    0x69, 0x6e, 0x20, 0x48, 0x54, 0x54, 0x50, 0x2f,
    0x31, 0x2e, 0x31, 0x0d, 0x0a, 0x00, 0x00, 0x00
};

int main() {
    int failures = 0;

    // ----------------------------------------------------------------
    // Caso A: NORMAL + annotation con score ML → PLUGIN_OK, errors==0
    // Contexto: ml-detector ha calculado score=0.9876 (alta anomalía)
    // y lo pasa al plugin via annotation para enriquecimiento/logging.
    // Espera: PLUGIN_OK, errors==0, result_code==0
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4d CASO A: NORMAL + score ML en annotation ===\n");
    setenv("MLD_TEST_VARIANT", "A", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = ml_event_payload;
            ctx.payload_len = sizeof(ml_event_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
            ctx.result_code = 0;
            ctx.src_ip      = 0xC0A8000A;  // 192.168.0.10
            ctx.dst_ip      = 0xC0A80001;  // 192.168.0.1
            ctx.src_port    = 50207;
            ctx.dst_port    = 8080;
            ctx.protocol    = 6;           // TCP
            ctx.direction   = 1;           // outbound
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            // annotation: score ML serializado — campo writable por plugin
            snprintf(ctx.annotation, sizeof(ctx.annotation),
                     "ml_score=0.9876,fast_score=0.0000,source=DIVERGENCE");
            memset(ctx.reserved, 0, sizeof(ctx.reserved));

            loader.invoke_all(ctx);
            int errs = 0;
            for (auto& s : loader.stats()) errs += (int)s.errors;
            int rc = ctx.result_code;
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
    // Caso B: D8 VIOLATION — plugin modifica campo read-only (src_ip)
    // Contexto: plugin malicioso intenta alterar la IP fuente del evento.
    // Espera: errors>0 (D8 post-invocation catch)
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4d CASO B: D8 VIOLATION campo read-only ===\n");
    setenv("MLD_TEST_VARIANT", "B", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = ml_event_payload;
            ctx.payload_len = sizeof(ml_event_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
            ctx.result_code = 0;
            ctx.src_ip      = 0xC0A8000A;
            ctx.dst_ip      = 0xC0A80001;
            ctx.src_port    = 50207;
            ctx.dst_port    = 8080;
            ctx.protocol    = 6;
            ctx.direction   = 1;
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            snprintf(ctx.annotation, sizeof(ctx.annotation),
                     "ml_score=0.9876,fast_score=0.0000,source=DIVERGENCE");
            memset(ctx.reserved, 0, sizeof(ctx.reserved));

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
    // Contexto: plugin devuelve anomalía — el ml-detector no debe caer.
    // Espera: errors==1, proceso sigue vivo
    // ----------------------------------------------------------------
    fprintf(stderr, "\n=== TEST-INTEG-4d CASO C: result_code=-1 no crash ===\n");
    setenv("MLD_TEST_VARIANT", "C", 1);
    {
        PluginLoader loader("/vagrant/plugins/test-message/test_config.json");
        loader.load_plugins();
        if (loader.loaded_count() == 0) {
            fprintf(stderr, "SKIP: no plugins loaded\n");
        } else {
            MessageContext ctx{};
            ctx.payload     = ml_event_payload;
            ctx.payload_len = sizeof(ml_event_payload);
            ctx.mode        = PLUGIN_MODE_NORMAL;
            ctx.result_code = 0;
            ctx.src_ip      = 0xC0A8000A;
            ctx.dst_ip      = 0xC0A80001;
            ctx.src_port    = 50207;
            ctx.dst_port    = 8080;
            ctx.protocol    = 6;
            ctx.direction   = 1;
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            snprintf(ctx.annotation, sizeof(ctx.annotation),
                     "ml_score=0.9876,fast_score=0.0000,source=DIVERGENCE");
            memset(ctx.reserved, 0, sizeof(ctx.reserved));

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

    fprintf(stderr, "\n=== TEST-INTEG-4d: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}