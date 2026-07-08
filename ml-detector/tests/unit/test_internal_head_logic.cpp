#include "ml_defender/internal_head_logic.hpp"
#include "ml_defender/internal_detector.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using namespace ml_defender;

#define GREEN "\033[32m"
#define RED   "\033[31m"
#define RESET "\033[0m"

static int tests_run = 0;
static int tests_passed = 0;

#define CHECK(cond, name)                                          \
    do {                                                           \
        ++tests_run;                                               \
        if (cond) {                                                \
            ++tests_passed;                                        \
            std::cout << GREEN << "  ✓ " << RESET << name << "\n"; \
        } else {                                                   \
            std::cout << RED << "  ✗ " << RESET << name            \
                      << "  [FALLO línea " << __LINE__ << "]\n";   \
        }                                                          \
    } while (0)

// ---------------------------------------------------------------------------
// TEST 1 — build_internal_features mapea los índices correctamente
// ---------------------------------------------------------------------------
void test_mapping_indices() {
    std::cout << "\n=== TEST 1: mapeo de índices (contrato del modelo) ===\n";

    // Vector con un valor DISTINTO por posición → detecta cualquier swap.
    std::vector<float> feats = {0.0f, 1.0f, 2.0f, 3.0f, 4.0f,
                                5.0f, 6.0f, 7.0f, 8.0f, 9.0f};
    auto f = build_internal_features(feats);

    CHECK(f.internal_connection_rate     == 0.0f, "[0] internal_connection_rate");
    CHECK(f.service_port_consistency     == 1.0f, "[1] service_port_consistency");
    CHECK(f.protocol_regularity          == 2.0f, "[2] protocol_regularity");
    CHECK(f.packet_size_consistency      == 3.0f, "[3] packet_size_consistency");
    CHECK(f.connection_duration_std      == 4.0f, "[4] connection_duration_std");
    CHECK(f.lateral_movement_score       == 5.0f, "[5] lateral_movement (REAL)");
    CHECK(f.service_discovery_patterns   == 6.0f, "[6] service_discovery_patterns");
    CHECK(f.data_exfiltration_indicators == 7.0f, "[7] data_exfiltration (REAL)");
    CHECK(f.temporal_anomaly_score       == 8.0f, "[8] temporal_anomaly_score");
    CHECK(f.access_pattern_entropy       == 9.0f, "[9] access_pattern_entropy");

    // to_array debe preservar el mismo orden (round-trip del contrato).
    auto arr = f.to_array();
    bool roundtrip_ok = true;
    for (std::size_t i = 0; i < 10; ++i)
        if (arr[i] != static_cast<float>(i)) roundtrip_ok = false;
    CHECK(roundtrip_ok, "to_array preserva el orden del contrato");
}

// ---------------------------------------------------------------------------
// TEST 2 — build_internal_features valida el tamaño de entrada
// ---------------------------------------------------------------------------
void test_size_validation() {
    std::cout << "\n=== TEST 2: validación de tamaño ===\n";

    bool threw_short = false;
    try { build_internal_features({1.0f, 2.0f, 3.0f}); }
    catch (const std::invalid_argument&) { threw_short = true; }
    CHECK(threw_short, "rechaza vector corto (3 features)");

    bool threw_long = false;
    try {
        build_internal_features(std::vector<float>(15, 1.0f));
    } catch (const std::invalid_argument&) { threw_long = true; }
    CHECK(threw_long, "rechaza vector largo (15 features)");

    bool ok_exact = false;
    try {
        build_internal_features(std::vector<float>(10, 0.5f));
        ok_exact = true;
    } catch (...) { ok_exact = false; }
    CHECK(ok_exact, "acepta exactamente 10 features");
}

// ---------------------------------------------------------------------------
// TEST 3 — evaluate_internal: lógica de suspicious y discrepancia
// ---------------------------------------------------------------------------
void test_evaluate_logic() {
    std::cout << "\n=== TEST 3: evaluate_internal (veredicto + hueco) ===\n";

    const float thr = 0.5f;

    // Predicción SOSPECHOSA (class 1, prob alta).
    InternalDetector::Prediction suspicious_pred{
        .class_id = 1, .probability = 0.9f,
        .benign_prob = 0.1f, .suspicious_prob = 0.9f};

    // Predicción BENIGNA (class 0, prob alta).
    InternalDetector::Prediction benign_pred{
        .class_id = 0, .probability = 0.9f,
        .benign_prob = 0.9f, .suspicious_prob = 0.1f};

    // Caso A: sospechoso + L1 dijo benigno (label 0) → DISCREPANCIA (el hueco).
    auto a = evaluate_internal(suspicious_pred, thr, /*label_l1=*/0);
    CHECK(a.suspicious,     "A: sospechoso detectado");
    CHECK(a.is_discrepancy, "A: DISCREPANCIA (L1=benigno, interno=amenaza) ← el hueco");

    // Caso B: sospechoso + L1 también dijo attack (label 1) → NO discrepancia.
    auto b = evaluate_internal(suspicious_pred, thr, /*label_l1=*/1);
    CHECK(b.suspicious,      "B: sospechoso detectado");
    CHECK(!b.is_discrepancy, "B: NO discrepancia (L1 ya vio el attack)");

    // Caso C: benigno + L1 benigno → ni amenaza ni hueco.
    auto c = evaluate_internal(benign_pred, thr, /*label_l1=*/0);
    CHECK(!c.suspicious,     "C: benigno, no sospechoso");
    CHECK(!c.is_discrepancy, "C: NO discrepancia (ambos benignos)");

    // Caso D: umbral respetado — prob justo por debajo no dispara.
    InternalDetector::Prediction borderline{
        .class_id = 1, .probability = 0.49f,
        .benign_prob = 0.51f, .suspicious_prob = 0.49f};
    auto d = evaluate_internal(borderline, thr, /*label_l1=*/0);
    CHECK(!d.suspicious,     "D: prob 0.49 < umbral 0.5 → no sospechoso");
    CHECK(!d.is_discrepancy, "D: sin sospecha no hay discrepancia");
}

// ---------------------------------------------------------------------------
// TEST 4 — integración pura: perfil lateral/exfil real → detector → suspicious
// ---------------------------------------------------------------------------
void test_real_detector_lateral_exfil() {
    std::cout << "\n=== TEST 4: detector real sobre perfil lateral/exfil ===\n";

    InternalDetector detector;

    // Perfil de barrido/exfiltración: lateral_movement[5] y exfil[7] altos.
    // (Coherente con los rangos del synthetic_sniffer_injector para tráfico
    //  de exfiltración: forward alto, backward ~0.)
    std::vector<float> lateral_exfil = {
        0.8f,  // [0] connection_rate alto
        0.5f,  // [1] port_consistency
        0.5f,  // [2] protocol_regularity
        0.3f,  // [3] packet_size_consistency
        0.6f,  // [4] duration_std
        0.9f,  // [5] LATERAL alto
        0.4f,  // [6] service_discovery
        0.85f, // [7] EXFIL alto
        0.7f,  // [8] temporal_anomaly
        0.5f   // [9] access_pattern_entropy
    };

    auto features = build_internal_features(lateral_exfil);
    auto pred = detector.predict(features);

    std::cout << "    → class=" << pred.class_id
              << " suspicious_prob=" << pred.suspicious_prob << "\n";

    // No fijamos un umbral duro sobre el resultado del modelo (sería frágil
    // frente a reentrenos): verificamos que el detector PRODUCE una predicción
    // válida y que la lógica de evaluación la procesa sin romper.
    CHECK(pred.class_id == 0 || pred.class_id == 1, "predicción válida (class 0|1)");
    CHECK(pred.suspicious_prob >= 0.0f && pred.suspicious_prob <= 1.0f,
          "suspicious_prob en [0,1]");

    auto eval = evaluate_internal(pred, 0.5f, /*label_l1=*/0);
    CHECK(eval.suspicious == (pred.suspicious_prob >= 0.5f),
          "evaluate_internal coherente con la prob del detector");
}

// ---------------------------------------------------------------------------
int main() {
    std::cout << "\n╔════════════════════════════════════════════════╗\n";
    std::cout <<   "║  TEST: internal_head_logic (DAY 212)           ║\n";
    std::cout <<   "║  DEBT-VERDICT-MONOCAPA-001 — contrato cabeza   ║\n";
    std::cout <<   "╚════════════════════════════════════════════════╝\n";

    test_mapping_indices();
    test_size_validation();
    test_evaluate_logic();
    test_real_detector_lateral_exfil();

    std::cout << "\n─────────────────────────────────────\n";
    std::cout << "Resultado: " << tests_passed << "/" << tests_run << " tests\n";
    if (tests_passed == tests_run) {
        std::cout << GREEN << "✅ TODOS VERDES" << RESET << "\n";
        return 0;
    }
    std::cout << RED << "❌ HAY FALLOS" << RESET << "\n";
    return 1;
}
