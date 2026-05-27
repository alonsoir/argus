// test_config_parser_traversal.cpp
//
// ACCEPTANCE TEST — DEBT-SAFE-PATH-TEST-PRODUCTION-001 (rag-ingester)
// RED->GREEN: path validation gate.
// Usa el config real de produccion — el JSON es la ley.

#include <gtest/gtest.h>
#include "common/config_parser.hpp"
#include <filesystem>

namespace fs = std::filesystem;

// Path al config real de produccion (disponible en la VM via /vagrant)
static const std::string REAL_CONFIG = "/vagrant/rag-ingester/config/rag-ingester.json";

// RED: path inexistente debe lanzar excepcion
TEST(ConfigParserTraversal, RejectNonExistentPath) {
    EXPECT_THROW(
        rag_ingester::ConfigParser::load("/nonexistent/path/config.json"),
        std::runtime_error
    ) << "ConfigParser MUST throw for non-existent path";
}

// RED: path vacio debe lanzar excepcion
TEST(ConfigParserTraversal, RejectEmptyPath) {
    EXPECT_THROW(
        rag_ingester::ConfigParser::load(""),
        std::exception
    ) << "ConfigParser MUST throw for empty path";
}

// GREEN: config real de produccion debe cargarse correctamente
// En dev (VM): allowed_prefix = directorio del config en /vagrant/
// En prod:     allowed_prefix = /etc/ml-defender/ (default)
// El prefix es SIEMPRE explicito — nunca derivado del path. (DEBT-CONFIG-PARSER-FIXED-PREFIX-001)
TEST(ConfigParserTraversal, ProductionConfigLoadsCorrectly) {
    if (!fs::exists(REAL_CONFIG)) {
        GTEST_SKIP() << "Production config not available at " << REAL_CONFIG;
    }
    const std::string dev_prefix =
        fs::weakly_canonical(fs::path(REAL_CONFIG).parent_path()).string();
    EXPECT_NO_THROW({
        auto config = rag_ingester::ConfigParser::load(REAL_CONFIG, dev_prefix);
        EXPECT_EQ(config.service.id, "rag-ingester-default");
    }) << "ConfigParser MUST accept production config with explicit prefix";
}


// RED→GREEN: con prefix fijo, ../ debe ser rechazado aunque el parent sea "/"
// DEBT-CONFIG-PARSER-FIXED-PREFIX-001 — el prefix nunca se deriva del input
TEST(ConfigParserTraversal, RejectDotDotWithFixedPrefix) {
    EXPECT_THROW(
        rag_ingester::ConfigParser::load("../etc/passwd", "/etc/ml-defender/"),
        std::runtime_error
    ) << "Fixed prefix MUST reject ../ traversal";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    std::cout << "\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  DEBT-SAFE-PATH-TEST-PRODUCTION-001 — rag-ingester   \n";
    std::cout << "  RED->GREEN: path validation gate                     \n";
    std::cout << "═══════════════════════════════════════════════════════\n\n";
    return RUN_ALL_TESTS();
}
