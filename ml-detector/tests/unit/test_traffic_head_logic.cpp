// DAY 213 — 1b-extract: red de tests para la lógica pura de la cabeza traffic.
// Espejo de test_internal_head_logic.cpp. Cubre mapeo de los 10 índices,
// validación de tamaño, y is_internal/is_internet sobre perfiles conocidos.
// Compila suelto (sin handler):
//   g++ -std=c++20 ... tests/unit/test_traffic_head_logic.cpp src/traffic_detector.cpp -o /tmp/test_thl

#include "ml_defender/traffic_head_logic.hpp"
#include "ml_defender/traffic_detector.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using ml_defender::build_traffic_features;
using ml_defender::TrafficDetector;

static int checks = 0;
#define CHECK(cond) do { ++checks; if(!(cond)) { \
    std::cerr << "FAIL L" << __LINE__ << ": " #cond "\n"; return 1; } } while(0)

static bool feq(float a, float b) { return std::fabs(a - b) < 1e-6f; }

int main() {
    // ---- 1. Mapeo de los 10 índices: cada slot va a su campo, sin cruces ----
    {
        std::vector<float> v = {0.10f, 0.11f, 0.12f, 0.13f, 0.14f,
                                0.15f, 0.16f, 0.17f, 0.18f, 0.19f};
        auto f = build_traffic_features(v);
        CHECK(feq(f.packet_rate,          0.10f));
        CHECK(feq(f.connection_rate,      0.11f));
        CHECK(feq(f.tcp_udp_ratio,        0.12f));
        CHECK(feq(f.avg_packet_size,      0.13f));
        CHECK(feq(f.port_entropy,         0.14f));
        CHECK(feq(f.flow_duration_std,    0.15f));
        CHECK(feq(f.src_ip_entropy,       0.16f));
        CHECK(feq(f.dst_ip_concentration, 0.17f));
        CHECK(feq(f.protocol_variety,     0.18f));
        CHECK(feq(f.temporal_consistency, 0.19f));
    }

    // ---- 2. to_array preserva el orden (contrato con predict) ----
    {
        std::vector<float> v = {1,2,3,4,5,6,7,8,9,10};
        auto arr = build_traffic_features(v).to_array();
        for (int i = 0; i < 10; ++i) CHECK(feq(arr[i], float(i + 1)));
    }

    // ---- 3. Validación de tamaño: lanza invalid_argument si size != 10 ----
    {
        bool threw = false;
        try { build_traffic_features(std::vector<float>(9, 0.0f)); }
        catch (const std::invalid_argument&) { threw = true; }
        CHECK(threw);

        threw = false;
        try { build_traffic_features(std::vector<float>(11, 0.0f)); }
        catch (const std::invalid_argument&) { threw = true; }
        CHECK(threw);

        threw = false;
        try { build_traffic_features(std::vector<float>{}); }
        catch (const std::invalid_argument&) { threw = true; }
        CHECK(threw);
    }

    // ---- 4. Semántica de Prediction: is_internal / is_internet mutuamente excluyentes ----
    // (contrato que run_traffic_head y el sellado del gate consumen)
    {
        TrafficDetector::Prediction internal_pred{
            .class_id = 1, .probability = 0.92f,
            .internet_prob = 0.08f, .internal_prob = 0.92f };
        CHECK(internal_pred.is_internal(0.5f));
        CHECK(!internal_pred.is_internet(0.5f));

        TrafficDetector::Prediction internet_pred{
            .class_id = 0, .probability = 0.88f,
            .internet_prob = 0.88f, .internal_prob = 0.12f };
        CHECK(internet_pred.is_internet(0.5f));
        CHECK(!internet_pred.is_internal(0.5f));
    }

    // ---- 5. Umbral: internal por debajo del threshold NO cuenta como internal ----
    // (borde exacto de la puerta level3_web que hoy mete al interno)
    {
        TrafficDetector::Prediction weak_internal{
            .class_id = 1, .probability = 0.60f,
            .internet_prob = 0.40f, .internal_prob = 0.60f };
        CHECK(weak_internal.is_internal(0.5f));   // pasa con umbral bajo
        CHECK(!weak_internal.is_internal(0.7f));  // no pasa con umbral alto
    }

    std::cout << "test_traffic_head_logic: " << checks
              << "/" << checks << " OK\n";
    return 0;
}