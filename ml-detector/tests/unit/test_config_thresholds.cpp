// test_config_thresholds.cpp
// aRGus NDR — DEBT-CONFIG-L3-THRESHOLDS-UNPARSED-001 (P0).
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// EL BUG QUE ESTE TEST HABRÍA CAZADO (DAY 215):
//   level3_web y level3_internal estaban en el struct (config_loader.hpp:144-145)
//   y en el JSON (0.6 / 0.65), pero NO en el parseo (config_loader.cpp:229-232).
//   Con `DetectorConfig config;` (default-init), quedaban INDETERMINADOS.
//   Medido en producción: level3_web=0, level3_internal=1.09486e+27.
//   Consecuencia: is_internal(0) → SIEMPRE true (guard abierto);
//                 is_suspicious(1.09e27) → SIEMPRE false (nunca sella).
//   Sobrevivió a 13 tests unitarios y a EMECAS+++ durante ~200 días.
//
// POR QUÉ ESTE TEST Y NO OTRO:
//   Un test que comprobara `level3_web == 0.6f` sería un ESPEJO del JSON: se
//   rompe al cambiar el valor y no caza la clase de bug. Este test comprueba una
//   PROPIEDAD: toda clave presente en ml.thresholds DEBE tener destino en el
//   struct Y el valor parseado DEBE coincidir con el del fichero.
//   ⟹ Añadir una clave al JSON y olvidar el get_required = ROJO, automáticamente.
//
// Estilo: main() + CHECK, sin GTest (igual que test_verdict_decision_logic).

#include "config_loader.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <functional>
#include <string>
#include <utility>
#include <vector>

static int g_failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { \
        std::printf("  ❌ FAIL L%d: %s\n", __LINE__, #cond); \
        ++g_failures; \
    } \
} while (0)

using ml_detector::ConfigLoader;
using ml_detector::DetectorConfig;

// Getters explícitos: `thresholds` es un struct ANÓNIMO anidado, así que no hay
// puntero-a-miembro cómodo. La tabla es el CONTRATO: clave JSON → campo del struct.
// Si el JSON gana una clave que no está aquí, el test la detecta como HUÉRFANA.
using Getter = std::function<float(const DetectorConfig&)>;
static const std::vector<std::pair<std::string, Getter>> kThresholdMap = {
    {"level1_attack",     [](const DetectorConfig& c) { return c.ml.thresholds.level1_attack; }},
    {"level2_ddos",       [](const DetectorConfig& c) { return c.ml.thresholds.level2_ddos; }},
    {"level2_ransomware", [](const DetectorConfig& c) { return c.ml.thresholds.level2_ransomware; }},
    {"level3_anomaly",    [](const DetectorConfig& c) { return c.ml.thresholds.level3_anomaly; }},
    {"level3_web",        [](const DetectorConfig& c) { return c.ml.thresholds.level3_web; }},
    {"level3_internal",   [](const DetectorConfig& c) { return c.ml.thresholds.level3_internal; }},
};

int main(int argc, char** argv) {
    std::printf("== test_config_thresholds (DEBT-CONFIG-L3-THRESHOLDS-UNPARSED-001) ==\n");

    const std::string cfg_path = (argc > 1)
        ? argv[1]
        : "../config/ml_detector_config.json";

    // El JSON se lee DOS VECES: una por el ConfigLoader (camino de producción) y
    // otra crudo aquí. Comparar ambas es lo que detecta el campo no parseado.
    std::ifstream f(cfg_path);
    if (!f.is_open()) {
        std::printf("  ❌ FATAL: no se pudo abrir %s\n", cfg_path.c_str());
        return 1;
    }
    nlohmann::json raw;
    f >> raw;

    ConfigLoader loader(cfg_path);
    const DetectorConfig config = loader.load();

    const auto& jt = raw["ml"]["thresholds"];

    // ---- PROPIEDAD 1: toda clave del JSON tiene destino conocido en el struct.
    // Caza "el admin añadió un umbral al JSON y nadie tocó el parseo".
    for (const auto& item : jt.items()) {
        const std::string& key = item.key();
        bool mapped = false;
        for (const auto& [k, _] : kThresholdMap) {
            if (k == key) { mapped = true; break; }
        }
        if (!mapped) {
            std::printf("  ❌ FAIL: clave HUÉRFANA en JSON sin destino en el struct: '%s'\n",
                        key.c_str());
            ++g_failures;
        }
    }

    // ---- PROPIEDAD 2 (EL CRÍTICO): el valor parseado == el valor del fichero.
    // Esto es lo que estaba roto. Un campo declarado pero no parseado quedaba
    // indeterminado (o 0.0f con value-init) y NUNCA igualaba al del JSON.
    for (const auto& [key, get] : kThresholdMap) {
        if (!jt.contains(key)) {
            std::printf("  ❌ FAIL: '%s' esperado en el JSON y NO está\n", key.c_str());
            ++g_failures;
            continue;
        }
        const float expected = jt.at(key).get<float>();
        const float actual   = get(config);
        if (std::fabs(expected - actual) > 1e-6f) {
            std::printf("  ❌ FAIL: '%s' JSON=%.6f  parseado=%.6g  ← NO SE LEE DEL FICHERO\n",
                        key.c_str(), static_cast<double>(expected), static_cast<double>(actual));
            ++g_failures;
        }
    }

    // ---- PROPIEDAD 3: un umbral de probabilidad vive en [0,1].
    // 1.09486e+27 (el valor real medido) habría reventado aquí de forma obvia.
    for (const auto& [key, get] : kThresholdMap) {
        const float v = get(config);
        if (!(v >= 0.0f && v <= 1.0f) || std::isnan(v)) {
            std::printf("  ❌ FAIL: '%s' = %.6g  fuera de [0,1] — no es una probabilidad\n",
                        key.c_str(), static_cast<double>(v));
            ++g_failures;
        }
    }

    if (g_failures == 0) {
        std::printf("  ✅ ALL CHECKS PASSED (%zu umbrales verificados contra el JSON)\n",
                    kThresholdMap.size());
        return 0;
    }
    std::printf("  💥 %d CHECK(s) FAILED\n", g_failures);
    return 1;
}