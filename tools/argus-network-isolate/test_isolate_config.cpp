// test_isolate_config.cpp — ADR-042 IRP config parser unit test
// DAY 143 — cobertura de campos auto_isolate, threat_score_threshold,
//            auto_isolate_event_types
#include <cassert>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include "isolate.hpp"

static void write_json(const std::string& path, const std::string& content) {
    std::ofstream f(path);
    f << content;
}

int main() {
    int failures = 0;

    // ── TEST 1: campos nuevos presentes ──────────────────────────────────
    {
        const std::string p = "/tmp/test_isolate_full.json";
        write_json(p, R"({
            "auto_isolate": true,
            "threat_score_threshold": 0.95,
            "isolate_interface": "eth2",
            "auto_isolate_event_types": ["ransomware","lateral_movement","c2_beacon"]
        })");
        auto cfg = argus::irp::IsolateConfig::from_file(p);
        if (!cfg.auto_isolate) {
            std::cerr << "FAIL TEST-1a: auto_isolate debe ser true\n"; ++failures;
        } else std::cout << "PASS TEST-1a: auto_isolate=true\n";

        if (cfg.threat_score_threshold != 0.95) {
            std::cerr << "FAIL TEST-1b: threat_score_threshold debe ser 0.95\n"; ++failures;
        } else std::cout << "PASS TEST-1b: threat_score_threshold=0.95\n";

        if (cfg.isolate_interface != "eth2") {
            std::cerr << "FAIL TEST-1d: isolate_interface debe ser eth2\n"; ++failures;
        } else std::cout << "PASS TEST-1d: isolate_interface=eth2\n";

        if (cfg.auto_isolate_event_types.size() != 3 ||
            cfg.auto_isolate_event_types[0] != "ransomware" ||
            cfg.auto_isolate_event_types[1] != "lateral_movement" ||
            cfg.auto_isolate_event_types[2] != "c2_beacon") {
            std::cerr << "FAIL TEST-1c: auto_isolate_event_types incorrecto\n"; ++failures;
        } else std::cout << "PASS TEST-1c: auto_isolate_event_types=[ransomware,lateral_movement,c2_beacon]\n";
    }

    // ── TEST 2: defaults cuando los campos están ausentes ────────────────
    {
        const std::string p = "/tmp/test_isolate_defaults.json";
        write_json(p, R"({})");
        auto cfg = argus::irp::IsolateConfig::from_file(p);
        if (!cfg.auto_isolate) {
            std::cerr << "FAIL TEST-2a: default auto_isolate debe ser true\n"; ++failures;
        } else std::cout << "PASS TEST-2a: default auto_isolate=true\n";

        if (cfg.threat_score_threshold != 0.95) {
            std::cerr << "FAIL TEST-2b: default threat_score_threshold debe ser 0.95\n"; ++failures;
        } else std::cout << "PASS TEST-2b: default threat_score_threshold=0.95\n";

        if (cfg.isolate_interface != "eth0") {
            std::cerr << "FAIL TEST-2d: default isolate_interface debe ser eth0\n"; ++failures;
        } else std::cout << "PASS TEST-2d: default isolate_interface=eth0\n";

        if (!cfg.auto_isolate_event_types.empty()) {
            std::cerr << "FAIL TEST-2c: default auto_isolate_event_types debe ser vacío\n"; ++failures;
        } else std::cout << "PASS TEST-2c: default auto_isolate_event_types=[]\n";
    }

    // ── TEST 3: auto_isolate=false ────────────────────────────────────────
    {
        const std::string p = "/tmp/test_isolate_disabled.json";
        write_json(p, R"({"auto_isolate": false, "threat_score_threshold": 0.99})");
        auto cfg = argus::irp::IsolateConfig::from_file(p);
        if (cfg.auto_isolate) {
            std::cerr << "FAIL TEST-3a: auto_isolate debe ser false\n"; ++failures;
        } else std::cout << "PASS TEST-3a: auto_isolate=false\n";

        if (cfg.threat_score_threshold != 0.99) {
            std::cerr << "FAIL TEST-3b: threat_score_threshold debe ser 0.99\n"; ++failures;
        } else std::cout << "PASS TEST-3b: threat_score_threshold=0.99\n";
    }

    std::cout << "\n";
    if (failures == 0)
        std::cout << "✅ test_isolate_config: ALL PASSED (9/9)\n";
    else
        std::cout << "❌ test_isolate_config: " << failures << " FAILED\n";

    return failures == 0 ? 0 : 1;
}
