#include <gtest/gtest.h>
#include <safe_path/safe_path.hpp>
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

class SafePathTest : public ::testing::Test {
protected:
    std::string tmp_dir;
    std::string allowed_dir;
    std::string forbidden_dir;

    void SetUp() override {
        tmp_dir       = (fs::temp_directory_path() / "argus_test_safe_path").string();
        allowed_dir   = tmp_dir + "/allowed/";
        forbidden_dir = tmp_dir + "/forbidden/";
        fs::create_directories(allowed_dir);
        fs::create_directories(forbidden_dir);
        std::ofstream(allowed_dir + "legit.json") << "{\"ok\":true}";
        std::ofstream(forbidden_dir + "secret.bin") << "FORBIDDEN_CONTENT";
    }

    void TearDown() override {
        fs::remove_all(tmp_dir);
    }
};

TEST_F(SafePathTest, LegitimatePathResolvesCorrectly) {
    EXPECT_NO_THROW({
        auto r = argus::safe_path::resolve(allowed_dir + "legit.json", allowed_dir);
        EXPECT_FALSE(r.empty());
    });
}

TEST_F(SafePathTest, RejectDotDotTraversal) {
    const std::string attack = allowed_dir + "../forbidden/secret.bin";
    {
        std::ifstream f(attack);
        EXPECT_TRUE(f.good()) << "Prerequisite: without safe_path, file is accessible";
    }
    EXPECT_THROW(
        argus::safe_path::resolve(attack, allowed_dir),
        std::runtime_error
    ) << "safe_path MUST reject ../ traversal";
}

TEST_F(SafePathTest, RejectAbsolutePathOutsidePrefix) {
    EXPECT_THROW(
        argus::safe_path::resolve("/etc/passwd", allowed_dir),
        std::runtime_error
    );
}

TEST_F(SafePathTest, RejectPrefixBypassWithoutTrailingSlash) {
    const std::string evil_dir = tmp_dir + "/allowed_evil/";
    fs::create_directories(evil_dir);
    std::ofstream(evil_dir + "secret.bin") << "EVIL";
    const std::string prefix_without_slash = tmp_dir + "/allowed";
    EXPECT_THROW(
        argus::safe_path::resolve(evil_dir + "secret.bin", prefix_without_slash),
        std::runtime_error
    ) << "Trailing slash normalisation MUST prevent prefix bypass";
}

TEST_F(SafePathTest, RejectSymlinkPointingOutsidePrefix) {
    const std::string symlink_path = allowed_dir + "evil_link";
    fs::create_symlink(forbidden_dir + "secret.bin", symlink_path);
    EXPECT_THROW(
        argus::safe_path::resolve(symlink_path, allowed_dir),
        std::runtime_error
    ) << "Symlink pointing outside prefix MUST be rejected";
}

TEST_F(SafePathTest, RejectEmptyPath) {
    EXPECT_THROW(
        argus::safe_path::resolve("", allowed_dir),
        std::runtime_error
    );
}

TEST_F(SafePathTest, RejectWritableWithNonExistentParent) {
    const std::string ghost = allowed_dir + "nonexistent/output.bin";
    EXPECT_THROW(
        argus::safe_path::resolve_writable(ghost, allowed_dir),
        std::runtime_error
    );
}

TEST_F(SafePathTest, ErrorMessageContainsSecurityAlert) {
    const std::string attack = allowed_dir + "../forbidden/secret.bin";
    try {
        argus::safe_path::resolve(attack, allowed_dir);
        FAIL() << "Expected runtime_error";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        EXPECT_NE(msg.find("SECURITY VIOLATION"), std::string::npos);
        EXPECT_NE(msg.find("Pipeline halt"), std::string::npos);
        EXPECT_NE(msg.find("Administrator notified"), std::string::npos);
    }
}

TEST_F(SafePathTest, SeedRejectSymlink) {
    const std::string real_seed = allowed_dir + "seed.bin";
    std::ofstream(real_seed) << "FAKESEED";
    chmod(real_seed.c_str(), 0400);
    const std::string sym = allowed_dir + "seed_link.bin";
    fs::create_symlink(real_seed, sym);
    EXPECT_THROW(
        argus::safe_path::resolve_seed(sym, allowed_dir),
        std::runtime_error
    ) << "resolve_seed MUST reject symlinks even within the prefix";
}

TEST_F(SafePathTest, SeedRejectWrongPermissions) {
    const std::string seed = allowed_dir + "seed.bin";
    std::ofstream(seed) << "FAKESEED";
    chmod(seed.c_str(), 0644);
    EXPECT_THROW(
        argus::safe_path::resolve_seed(seed, allowed_dir),
        std::runtime_error
    ) << "resolve_seed MUST reject seed files with permissions != 0400";
}

// ─── ACCEPTANCE TEST 10: path relativo ──────────────────────────────────────
// ATAQUE: componente recibe config_path = "config/foo.json" (relativo al CWD)
// SIN FIX: weakly_canonical no canonicalizaba el prefix antes de la comparacion
//          → prefix era "config/" → no matching con path absoluto resuelto
//          → SECURITY VIOLATION falso positivo → rag-ingester STOPPED (DAY 124)
// CON FIX: prefix canonicalizado con weakly_canonical antes de la comparacion.
TEST_F(SafePathTest, RelativePathResolvesBeforePrefixCheck) {
    // Crear un config legitimo dentro del allowed_dir
    std::ofstream(allowed_dir + "config.json") << "{\"ok\":true}";

    // Construir path relativo desde CWD al fichero dentro de allowed_dir
    const fs::path abs_path = fs::path(allowed_dir + "config.json");
    const fs::path cwd = fs::current_path();
    std::string rel_path;
    try {
        rel_path = fs::relative(abs_path, cwd).string();
    } catch (...) {
        // Si no es posible construir un path relativo (e.g. distinto volumen),
        // usamos el path absoluto directamente — el test sigue siendo valido.
        rel_path = abs_path.string();
    }

    // El path relativo debe resolverse correctamente — no SECURITY VIOLATION
    EXPECT_NO_THROW({
        auto r = argus::safe_path::resolve(rel_path, allowed_dir);
        EXPECT_FALSE(r.empty());
    }) << "Fichero legitimo en allowed_dir no debe ser rechazado por path relativo";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    std::cout << "\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  ADR-037 ACCEPTANCE TESTS — safe_path security gate  \n";
    std::cout << "  RED→GREEN: cada test documenta un ataque real        \n";
    std::cout << "═══════════════════════════════════════════════════════\n\n";
    return RUN_ALL_TESTS();
}
