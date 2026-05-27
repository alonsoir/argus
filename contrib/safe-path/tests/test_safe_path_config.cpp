// test_safe_path_config.cpp
//
// ACCEPTANCE TEST — DEBT-DEV-PROD-SYMLINK-001
// RED->GREEN: resolve_config() permite symlinks en prefix confiable,
// rechaza traversal lexical, y sigue el symlink para abrir el fichero real.
// (Consejo 8/8 DAY 125)

#include <gtest/gtest.h>
#include <safe_path/safe_path.hpp>
#include <filesystem>
#include <fstream>
#include <sys/stat.h>

namespace fs = std::filesystem;

class SafePathConfigTest : public ::testing::Test {
protected:
    std::string tmp_dir;
    std::string allowed_dir;

    void SetUp() override {
        char buf[] = "/tmp/safe_path_config_XXXXXX";
        tmp_dir = std::string(mkdtemp(buf));
        allowed_dir = tmp_dir + "/etc/ml-defender/";
        fs::create_directories(allowed_dir);
    }

    void TearDown() override {
        fs::remove_all(tmp_dir);
    }
};

// RED: path con ../ debe ser rechazado lexicalmente (sin seguir symlinks)
TEST_F(SafePathConfigTest, RejectDotDotTraversalLexical) {
    EXPECT_THROW(
        argus::safe_path::resolve_config("../etc/passwd", allowed_dir),
        std::runtime_error
    ) << "resolve_config MUST reject ../ traversal lexically";
}

// RED: path absoluto fuera del prefix rechazado
TEST_F(SafePathConfigTest, RejectAbsolutePathOutsidePrefix) {
    EXPECT_THROW(
        argus::safe_path::resolve_config("/tmp/evil.json", allowed_dir),
        std::runtime_error
    ) << "resolve_config MUST reject paths outside allowed prefix";
}

// GREEN: symlink dentro del prefix es aceptado y resuelto correctamente
TEST_F(SafePathConfigTest, AcceptSymlinkInsidePrefix) {
    // Fichero real en /tmp/
    const std::string real_file = tmp_dir + "/firewall.json";
    std::ofstream(real_file) << R"({"test": true})";

    // Symlink dentro del prefix (simula /etc/ml-defender/ → /vagrant/)
    const std::string symlink_path = allowed_dir + "firewall.json";
    fs::create_symlink(real_file, symlink_path);

    std::string resolved;
    EXPECT_NO_THROW(
        resolved = argus::safe_path::resolve_config(symlink_path, allowed_dir)
    ) << "resolve_config MUST accept symlinks inside the prefix";

    // El resultado debe ser el path real (symlink resuelto)
    EXPECT_EQ(resolved, fs::weakly_canonical(real_file).string())
        << "resolve_config MUST return the resolved real path";
}

// GREEN: fichero real dentro del prefix (sin symlink) también funciona
TEST_F(SafePathConfigTest, AcceptRealFileInsidePrefix) {
    const std::string config_path = allowed_dir + "config.json";
    std::ofstream(config_path) << R"({"test": true})";

    EXPECT_NO_THROW(
        argus::safe_path::resolve_config(config_path, allowed_dir)
    ) << "resolve_config MUST accept real files inside the prefix";
}

// GREEN: path vacío rechazado
TEST_F(SafePathConfigTest, RejectEmptyPath) {
    EXPECT_THROW(
        argus::safe_path::resolve_config("", allowed_dir),
        std::runtime_error
    ) << "resolve_config MUST reject empty path";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    std::cout << "\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  DEBT-DEV-PROD-SYMLINK-001 — resolve_config()        \n";
    std::cout << "  RED->GREEN: symlinks permitidos en prefix confiable  \n";
    std::cout << "═══════════════════════════════════════════════════════\n\n";
    return RUN_ALL_TESTS();
}
