// test_config_loader_traversal.cpp
//
// ACCEPTANCE TEST — DEBT-PRODUCTION-TESTS-REMAINING-001 (firewall-acl-agent)
// RED->GREEN: path traversal rejection en ConfigLoader.
// Consejo 8/8 DAY 125: el prefix nunca se deriva del input.

#include <gtest/gtest.h>
#include "firewall/config_loader.hpp"
#include <filesystem>
#include <fstream>
#include <sys/stat.h>

namespace fs = std::filesystem;

// RED: path con ../ debe lanzar SECURITY VIOLATION con prefix fijo
TEST(ConfigLoaderTraversal, RejectDotDotWithFixedPrefix) {
    EXPECT_THROW(
        mldefender::firewall::ConfigLoader::load_from_file("../etc/passwd", "/etc/ml-defender/"),
        std::runtime_error
    ) << "Fixed prefix MUST reject ../ traversal";
}

// RED: path absoluto fuera del prefix debe ser rechazado
TEST(ConfigLoaderTraversal, RejectAbsolutePathOutsidePrefix) {
    EXPECT_THROW(
        mldefender::firewall::ConfigLoader::load_from_file("/tmp/evil.json", "/etc/ml-defender/"),
        std::runtime_error
    ) << "Fixed prefix MUST reject absolute paths outside prefix";
}

// GREEN: path dentro de un prefix controlado — safe_path lo acepta
// (puede fallar por JSON invalido, pero NO por SECURITY VIOLATION)
TEST(ConfigLoaderTraversal, AcceptPathInsidePrefix) {
    char tmpdir[] = "/tmp/fw_traversal_XXXXXX";
    ASSERT_NE(mkdtemp(tmpdir), nullptr);
    const std::string prefix = std::string(tmpdir) + "/";
    const std::string config_path = prefix + "firewall.json";

    {
        std::ofstream f(config_path);
        f << R"({"network":{"zmq_bind_address":"tcp://*:5560","zmq_connect_address":"tcp://localhost:5560"},"firewall":{"default_policy":"DROP","ipset_name":"ml_defender_blocklist","max_rules":10000,"rule_timeout_seconds":3600},"logging":{"level":"info","file":"/tmp/fw_test.log","max_size_mb":10,"max_files":3},"performance":{"batch_size":100,"flush_interval_ms":1000}})";
    }

    try {
        mldefender::firewall::ConfigLoader::load_from_file(config_path, prefix);
        SUCCEED();
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        // Acepta cualquier error EXCEPTO SECURITY VIOLATION
        EXPECT_EQ(msg.find("SECURITY VIOLATION"), std::string::npos)
            << "Path inside prefix MUST NOT trigger SECURITY VIOLATION: " << msg;
    }
    fs::remove_all(tmpdir);
}
// Sin main() — GTest::gtest_main lo provee
