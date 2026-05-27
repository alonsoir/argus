/**
 * xgboost_plugin.cpp — ADR-026 Track 1
 *
 * Plugin de inferencia XGBoost para ml-detector.
 * Carga modelo pre-entrenado en CIC-IDS-2017 (.ubj XGBoost format).
 * Implementa plugin_process_message(MessageContext&) — PLUGIN_MODE_NORMAL.
 *
 * Payload: float32[] contiguo, 23 features LEVEL1 (docs/xgboost/plugin-contract.md)
 * Fail-closed: std::terminate() si modelo no carga o payload inválido.
 *
 * DAY 120 — Alonso Isidoro Román
 */

#include <plugin_loader/plugin_api.h>
#include <xgboost/c_api.h>

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <stdexcept>

// ── Configuración ────────────────────────────────────────────────
#ifndef MLD_XGBOOST_MODEL_PATH
#define MLD_XGBOOST_MODEL_PATH "/etc/ml-defender/models/xgboost_cicids2017.ubj"
#endif

static constexpr int    NUM_FEATURES = 23;
static constexpr size_t PAYLOAD_BYTES = NUM_FEATURES * sizeof(float);

// ── Estado global del plugin ─────────────────────────────────────
static BoosterHandle g_booster = nullptr;
static bool          g_loaded  = false;

// ── plugin_init ──────────────────────────────────────────────────
// @requires: config != nullptr
// @ensures: g_loaded == true || std::terminate()
extern "C" PluginResult plugin_init(const PluginConfig* config) {
    (void)config;

    fprintf(stderr, "[plugin_xgboost] Loading model: %s\n", MLD_XGBOOST_MODEL_PATH);

    int ret = XGBoosterCreate(nullptr, 0, &g_booster);
    if (ret != 0) {
        fprintf(stderr, "[plugin_xgboost] FATAL: XGBoosterCreate failed: %s\n",
                XGBGetLastError());
        std::terminate();
    }

    ret = XGBoosterLoadModel(g_booster, MLD_XGBOOST_MODEL_PATH);
    if (ret != 0) {
        fprintf(stderr, "[plugin_xgboost] FATAL: model not found at %s: %s\n",
                MLD_XGBOOST_MODEL_PATH, XGBGetLastError());
        XGBoosterFree(g_booster);
        g_booster = nullptr;
        std::terminate();
    }

    g_loaded = true;
    fprintf(stderr, "[plugin_xgboost] Model loaded OK — fail-closed active\n");
    return PLUGIN_OK;
}

// ── plugin_process_packet ────────────────────────────────────────
extern "C" PluginResult plugin_process_packet(PacketContext* ctx) {
    (void)ctx;
    return PLUGIN_SKIP;
}

// ── plugin_process_message ───────────────────────────────────────
// @requires: ctx != nullptr
// @requires: ctx->payload != nullptr
// @requires: ctx->payload_size == NUM_FEATURES * sizeof(float)
// @ensures: ctx->result ∈ [0.0, 1.0] || std::terminate()
extern "C" PluginResult plugin_process_message(MessageContext* ctx) {
    if (!g_loaded || g_booster == nullptr) {
        fprintf(stderr, "[plugin_xgboost] FATAL: invoked without loaded model\n");
        std::terminate();
    }

    // Validar ctx
    if (ctx == nullptr) {
        fprintf(stderr, "[plugin_xgboost] FATAL: null MessageContext\n");
        std::terminate();
    }

    // Validar payload — contratos ADR-023 FIX-C
    if (ctx->payload == nullptr) {
        fprintf(stderr, "[plugin_xgboost] FATAL: null payload (PLUGIN_MODE_NORMAL requires float32[])\n");
        std::terminate();
    }

    if (ctx->payload_len != PAYLOAD_BYTES) {
        fprintf(stderr, "[plugin_xgboost] FATAL: payload_len=%zu expected=%zu\n",
                ctx->payload_len, PAYLOAD_BYTES);
        std::terminate();
    }

    // Validar NaN/Inf en features
    const float* features = reinterpret_cast<const float*>(ctx->payload);
    for (int i = 0; i < NUM_FEATURES; ++i) {
        if (std::isnan(features[i]) || std::isinf(features[i])) {
            fprintf(stderr, "[plugin_xgboost] FATAL: feature[%d] is NaN/Inf\n", i);
            std::terminate();
        }
    }

    // Crear DMatrix con 1 fila x 23 columnas
    DMatrixHandle dmat = nullptr;
    int ret = XGDMatrixCreateFromMat(features, 1, NUM_FEATURES,
                                      std::numeric_limits<float>::quiet_NaN(),
                                      &dmat);
    if (ret != 0 || dmat == nullptr) {
        fprintf(stderr, "[plugin_xgboost] FATAL: XGDMatrixCreateFromMat failed: %s\n",
                XGBGetLastError());
        std::terminate();
    }

    // Inferencia
    bst_ulong out_len = 0;
    const float* out_result = nullptr;
    ret = XGBoosterPredict(g_booster, dmat, 0, 0, 0, &out_len, &out_result);
    XGDMatrixFree(dmat);

    if (ret != 0 || out_result == nullptr || out_len == 0) {
        fprintf(stderr, "[plugin_xgboost] FATAL: XGBoosterPredict failed: %s\n",
                XGBGetLastError());
        std::terminate();
    }

    float score = out_result[0];

    // Validar salida
    if (std::isnan(score) || std::isinf(score)) {
        fprintf(stderr, "[plugin_xgboost] FATAL: prediction is NaN/Inf\n");
        std::terminate();
    }

    ctx->result_code = (score >= 0.5f) ? 1 : 0;  // 1=ATTACK, 0=BENIGN
    // Store score in annotation for observability
    snprintf(ctx->annotation, sizeof(ctx->annotation), "xgb_score=%.6f", score);

    fprintf(stderr, "[plugin_xgboost] inference OK — score=%.6f\n", score);
    return PLUGIN_OK;
}

// ── plugin_shutdown ──────────────────────────────────────────────
extern "C" void plugin_shutdown() {
    if (g_booster != nullptr) {
        XGBoosterFree(g_booster);
        g_booster = nullptr;
    }
    g_loaded = false;
    fprintf(stderr, "[plugin_xgboost] shutdown OK\n");
}

extern "C" int plugin_api_version() { return 1; }
extern "C" const char* plugin_name()    { return "plugin_xgboost"; }
extern "C" const char* plugin_version() { return "0.1.1-adr026-track1"; }
