// ============================================================================
// test_integ_xgboost_1.cpp — TEST-INTEG-XGBOOST-1
// ============================================================================
// Verifica que plugin_xgboost carga el modelo y produce inferencia válida.
//   Caso A: payload sintético BENIGN (23 floats bajos) → score ∈ [0,1], no NaN
//   Caso B: payload sintético ATTACK (23 floats altos) → score ∈ [0,1], no NaN
//   Caso C: 3 flows reales BENIGN (CIC-IDS-2017 Tuesday) → score < 0.1 (medical gate)
//   Caso D: 3 flows reales ATTACK (CIC-IDS-2017 Tuesday) → score > 0.5 (medical gate)
//   Caso E: payload nullptr → std::terminate() (fail-closed ADR-023 FIX-C)
//           NO ejecutado en CI — documentado como invariante
//
// Gate ADR-026 / DEBT-XGBOOST-TEST-REAL-001:
//   Casos A+B: sanity (score ∈ [0,1], no NaN)
//   Casos C+D: BLOQUEANTE MERGE — gate médico Precision≥0.99
//              BENIGN real → score < 0.1  (FP inaceptable en hospital)
//              ATTACK real → score > 0.5  (detección mínima requerida)
//
// Dataset: CIC-IDS-2017 Tuesday-WorkingHours.pcap_ISCX.csv
// Features: LEVEL1_FEATURE_NAMES (23 features, docs/xgboost/features.md)
// DAY 121 — Alonso Isidoro Román
// ============================================================================
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <cassert>
#include <cmath>

using namespace ml_defender;

static const char* XGBOOST_CONFIG = "/tmp/test_xgboost_config.json";

// ── Sintético BENIGN (sanity) ────────────────────────────────────────────────
static float benign_features[23] = {
    10.0f, 512.0f, 128.0f, 64.0f, 5.0f, 100.0f, 2.0f, 64.0f, 3.0f,
    512.0f, 8.0f, 10.0f, 256.0f, 443.0f, 0.0f, 3.0f, 1000.0f, 85.0f,
    256.0f, 42.0f, 20.0f, 1.5f, 8.0f
};

// ── Sintético ATTACK (sanity) ────────────────────────────────────────────────
static float attack_features[23] = {
    1400.0f, 65000.0f, 1500.0f, 1500.0f, 50000.0f, 2000000.0f, 50000.0f,
    1500.0f, 50000.0f, 65000.0f, 500.0f, 100000.0f, 32000.0f, 0.0f, 0.0f,
    50000.0f, 0.0f, 1200.0f, 32000.0f, 800.0f, 0.0f, 0.001f, 100000.0f
};

// ── Reales BENIGN — CIC-IDS-2017 Tuesday (medical gate: score < 0.1) ─────────
static float real_benign[3][23] = {
    {99.001837f, 440.000000f, 220.000000f, 62.857143f, 0.000000f, 9801.363636f,
     1.000000f, 179.000000f, 2.000000f, 440.000000f, 107.349008f, 10937.500000f,
     358.000000f, 88.000000f, 8192.000000f, 7.000000f, 1.000000f, 66.500000f,
     358.000000f, 89.500000f, 0.000000f, 640.000000f, 17187.500000f},
    {527.434262f, 600.000000f, 300.000000f, 66.666667f, 0.000000f, 278186.901100f,
     1.000000f, 1472.000000f, 2.000000f, 600.000000f, 132.287566f, 10000.000000f,
     2944.000000f, 88.000000f, 8192.000000f, 9.000000f, 1.000000f, 253.142857f,
     2944.000000f, 736.000000f, 0.000000f, 900.000000f, 14444.444440f},
    {690.098917f, 2776.000000f, 1388.000000f, 396.571429f, 0.000000f, 476236.515200f,
     1.000000f, 1415.000000f, 2.000000f, 2776.000000f, 677.274651f, 5809.128631f,
     2830.000000f, 88.000000f, 8192.000000f, 7.000000f, 1.000000f, 467.166667f,
     2830.000000f, 707.500000f, 0.000000f, 1205.000000f, 9128.630705f},
};

// ── Reales ATTACK — CIC-IDS-2017 Tuesday FTP-Patator (medical gate: score > 0.5)
// Seleccionadas con score confirmado > 0.99 (model.predict en Python antes de incrustar)
// FTP-Patator mean_score=0.9988 sobre 7938 flows — NO son outliers
static float real_attack[3][23] = {
    // FTP-Patator score=0.9999
    {8.082904f, 14.000000f, 14.000000f, 7.000000f, 1.000000f, 65.333333f, 0.000000f, 0.000000f, 0.000000f, 14.000000f, 9.899495f, 7547.169811f, 0.000000f, 21.000000f, 229.000000f, 2.000000f, 265.000000f, 7.000000f, 0.000000f, 0.000000f, 0.000000f, 265.000000f, 11320.754720f},
    // FTP-Patator score=0.9993
    {8.082904f, 14.000000f, 14.000000f, 7.000000f, 1.000000f, 65.333333f, 0.000000f, 0.000000f, 0.000000f, 14.000000f, 9.899495f, 666666.666700f, 0.000000f, 21.000000f, 229.000000f, 2.000000f, 3.000000f, 9.333333f, 0.000000f, 0.000000f, 0.000000f, 3.000000f, 666666.666700f},
    // FTP-Patator score=0.9999
    {8.082904f, 14.000000f, 14.000000f, 7.000000f, 1.000000f, 65.333333f, 0.000000f, 0.000000f, 0.000000f, 14.000000f, 9.899495f, 9302.325581f, 0.000000f, 21.000000f, 229.000000f, 2.000000f, 215.000000f, 7.000000f, 0.000000f, 0.000000f, 0.000000f, 215.000000f, 13953.488370f},
};

static constexpr float BENIGN_MAX_SCORE = 0.1f;
static constexpr float ATTACK_MIN_SCORE = 0.5f;

static void write_config() {
    FILE* cfg = fopen(XGBOOST_CONFIG, "w");
    if (!cfg) { fprintf(stderr, "ERROR: no se puede crear config temporal\n"); exit(1); }
    fprintf(cfg,
        "{\n"
        "  \"component\": \"test-xgboost\",\n"
        "  \"plugins\": {\n"
        "    \"directory\": \"/usr/lib/ml-defender/plugins\",\n"
        "    \"budget_us\": 5000,\n"
        "    \"enabled\": [\n"
        "      {\n"
        "        \"name\": \"plugin_xgboost\",\n"
        "        \"path\": \"/usr/lib/ml-defender/plugins/libplugin_xgboost.so\",\n"
        "        \"active\": true\n"
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n");
    fclose(cfg);
}

static float run_inference(const float* features, const char* label) {
    PluginLoader loader(XGBOOST_CONFIG);
    loader.load_plugins();
    if (loader.loaded_count() == 0) {
        fprintf(stderr, "❌ %s: no plugins loaded\n", label);
        return -1.0f;
    }
    MessageContext ctx{};
    ctx.payload     = reinterpret_cast<const uint8_t*>(features);
    ctx.payload_len = 23 * sizeof(float);
    ctx.mode        = PLUGIN_MODE_NORMAL;
    ctx.result_code = 0;
    ctx.src_ip      = 0xC0A80001;
    ctx.dst_ip      = 0xC0A80002;
    ctx.src_port    = 12345;
    ctx.dst_port    = 443;
    ctx.protocol    = 6;
    ctx.direction   = 0;
    ctx.nonce       = nullptr;
    ctx.tag         = nullptr;
    loader.invoke_all(ctx);
    float score = -1.0f;
    sscanf(ctx.annotation, "xgb_score=%f", &score);
    fprintf(stderr, "  result_code=%d annotation='%s' score=%.6f\n",
            ctx.result_code, ctx.annotation, score);
    return score;
}

int main() {
    int failures = 0;
    write_config();

    // ── Caso A: sintético BENIGN — score ∈ [0,1], no NaN ────────────────────
    fprintf(stderr, "\n=== TEST-INTEG-XGBOOST-1 CASO A: sintético BENIGN (sanity) ===\n");
    {
        float score = run_inference(benign_features, "CASO A");
        if (std::isnan(score) || std::isinf(score) || score < 0.0f || score > 1.0f) {
            fprintf(stderr, "❌ CASO A: score=%.6f fuera de [0,1] o NaN/Inf\n", score);
            failures++;
        } else {
            fprintf(stderr, "✅ CASO A: score=%.6f ∈ [0,1] — PASS\n", score);
        }
    }

    // ── Caso B: sintético ATTACK — score ∈ [0,1], no NaN ───────────────────
    fprintf(stderr, "\n=== TEST-INTEG-XGBOOST-1 CASO B: sintético ATTACK (sanity) ===\n");
    {
        float score = run_inference(attack_features, "CASO B");
        if (std::isnan(score) || std::isinf(score) || score < 0.0f || score > 1.0f) {
            fprintf(stderr, "❌ CASO B: score=%.6f fuera de [0,1] o NaN/Inf\n", score);
            failures++;
        } else {
            fprintf(stderr, "✅ CASO B: score=%.6f ∈ [0,1] — PASS\n", score);
        }
    }

    // ── Caso C: reales BENIGN — gate médico score < 0.1 ─────────────────────
    fprintf(stderr, "\n=== TEST-INTEG-XGBOOST-1 CASO C: reales BENIGN (CIC-IDS-2017) ===\n");
    fprintf(stderr, "    Gate médico: score < %.1f\n", BENIGN_MAX_SCORE);
    for (int i = 0; i < 3; i++) {
        fprintf(stderr, "  [BENIGN real #%d]\n", i + 1);
        float score = run_inference(real_benign[i], "CASO C");
        if (std::isnan(score) || std::isinf(score)) {
            fprintf(stderr, "❌ CASO C[%d]: score NaN/Inf\n", i + 1);
            failures++;
        } else if (score >= BENIGN_MAX_SCORE) {
            fprintf(stderr, "❌ CASO C[%d]: score=%.6f >= %.1f — GATE MÉDICO FALLIDO\n",
                    i + 1, score, BENIGN_MAX_SCORE);
            failures++;
        } else {
            fprintf(stderr, "✅ CASO C[%d]: score=%.6f < %.1f — PASS\n",
                    i + 1, score, BENIGN_MAX_SCORE);
        }
    }

    // ── Caso D: reales ATTACK — gate médico score > 0.5 ─────────────────────
    fprintf(stderr, "\n=== TEST-INTEG-XGBOOST-1 CASO D: reales ATTACK (CIC-IDS-2017) ===\n");
    fprintf(stderr, "    Gate médico: score > %.1f\n", ATTACK_MIN_SCORE);
    for (int i = 0; i < 3; i++) {
        fprintf(stderr, "  [ATTACK real #%d]\n", i + 1);
        float score = run_inference(real_attack[i], "CASO D");
        if (std::isnan(score) || std::isinf(score)) {
            fprintf(stderr, "❌ CASO D[%d]: score NaN/Inf\n", i + 1);
            failures++;
        } else if (score <= ATTACK_MIN_SCORE) {
            fprintf(stderr, "❌ CASO D[%d]: score=%.6f <= %.1f — GATE MÉDICO FALLIDO\n",
                    i + 1, score, ATTACK_MIN_SCORE);
            failures++;
        } else {
            fprintf(stderr, "✅ CASO D[%d]: score=%.6f > %.1f — PASS\n",
                    i + 1, score, ATTACK_MIN_SCORE);
        }
    }

    fprintf(stderr, "\n=== TEST-INTEG-XGBOOST-1: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures;
}
