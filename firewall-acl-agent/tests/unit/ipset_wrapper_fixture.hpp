//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// ipset_wrapper_fixture.hpp - fixture IPSetWrapperTest compartido  [ARGUS-GATE-PERF-D303]
// Movido tal cual desde test_ipset_wrapper.cpp para que lo usen los tests funcionales
// (ipset_wrapper_tests, etiqueta e2e) y los de rendimiento (ipset_wrapper_perf_tests, etiqueta perf);
// ambos necesitan root. [ARGUS-GATE-PERF-D303-B]
// Requiere root: SetUp hace GTEST_SKIP sin root, y la puerta ctest_label_gate.sh FALLA si algo se salta.
//===----------------------------------------------------------------------===//
#pragma once

#include "firewall/ipset_wrapper.hpp"

#include <gtest/gtest.h>
#include <unistd.h>
#include <chrono>
#include <random>
#include <sstream>
#include <memory>
#include <string>
#include <vector>

using namespace mldefender::firewall;
using namespace std::chrono;

//===----------------------------------------------------------------------===//
// Test Fixture
//===----------------------------------------------------------------------===//

class IPSetWrapperTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Verify root privileges
        if (geteuid() != 0) {
            GTEST_SKIP() << "⚠️  Tests require root privileges (sudo)";
        }

        // Clean up any leftover test sets
        cleanup_test_sets();

        wrapper_ = std::make_unique<IPSetWrapper>();
    }

    void TearDown() override {
        // Cleanup test sets
        cleanup_test_sets();
        wrapper_.reset();
    }

    void cleanup_test_sets() {
        IPSetWrapper temp_wrapper;
        auto sets = temp_wrapper.list_sets();

        for (const auto& set : sets) {
            if (set.find("test_") == 0) {
                temp_wrapper.destroy_set(set);
            }
        }
    }

    std::string generate_random_ip() {
        static std::random_device rd;
        static std::mt19937 gen(rd());
        static std::uniform_int_distribution<> dist(1, 254);

        std::ostringstream oss;
        oss << dist(gen) << "." << dist(gen) << "."
            << dist(gen) << "." << dist(gen);
        return oss.str();
    }

    std::vector<IPSetEntry> generate_random_ips(size_t count) {
        std::vector<IPSetEntry> ips;
        ips.reserve(count);

        for (size_t i = 0; i < count; ++i) {
            ips.emplace_back(generate_random_ip());
        }

        return ips;
    }

    std::unique_ptr<IPSetWrapper> wrapper_;

    // Standard test set configurations
    static constexpr const char* TEST_SET_NAME = "test_ipset";
    static constexpr const char* TEST_SET_NAME_2 = "test_ipset_2";
};
