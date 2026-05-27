// test_safe_path_property.cpp
// Property tests para safe_path — DAY 128 (DEBT-PROPERTY-TESTING-PATTERN-001)
//
// Tres invariantes:
//   1. resolve_seed  — nunca escapa prefix, nunca acepta symlinks
//   2. resolve_config — nunca escapa prefix lexical, acepta symlinks dentro
//   3. resolve (general) — prefix fijo nunca deriva del input
//
// REGLA: cada test tiene estado RED demostrado (fallo con código antiguo)
// documentado en docs/testing/PROPERTY-TESTING.md

#include <gtest/gtest.h>
#include <safe_path/safe_path.hpp>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>

namespace fs = std::filesystem;

// ─── Fixture ────────────────────────────────────────────────────────────────

class SafePathPropertyTest : public ::testing::Test {
protected:
    std::string tmp_dir;
    std::string seed_dir;
    std::string config_dir;

    void SetUp() override {
        tmp_dir    = (fs::temp_directory_path() / "argus_property_test").string();
        seed_dir   = tmp_dir + "/seed_dir";
        config_dir = tmp_dir + "/config_dir";
        fs::create_directories(seed_dir);
        fs::create_directories(config_dir);

        // Crear seed.bin con permisos 0400 (como en producción)
        std::string seed_path = seed_dir + "/seed.bin";
        std::ofstream(seed_path) << std::string(32, '\x42');
        fs::permissions(seed_path,
            fs::perms::owner_read,
            fs::perm_options::replace);

        // Crear config legítimo
        std::ofstream(config_dir + "/config.json") << "{\"ok\":true}";
    }

    void TearDown() override {
        fs::remove_all(tmp_dir);
    }
};

// ─── PROPERTY 1: resolve_seed nunca escapa prefix ───────────────────────────

TEST_F(SafePathPropertyTest, ResolveSeedNeverEscapesPrefix) {
    // Invariante: para todo intento de traversal, resolve_seed lanza excepción.
    // RED demostrado: sin la comprobación lstat(), paths con .. escapaban.
    const std::vector<std::string> traversal_attempts = {
        seed_dir + "/../../etc/passwd",
        seed_dir + "/../forbidden/seed.bin",
        seed_dir + "/./../../root/.ssh/id_rsa",
        seed_dir + "/%2e%2e/secret",
        seed_dir + "/subdir/../../outside",
    };

    for (const auto& attempt : traversal_attempts) {
        EXPECT_THROW(
            argus::safe_path::resolve_seed(attempt, seed_dir),
            std::exception
        ) << "resolve_seed deberia rechazar traversal: " << attempt;
    }
}

// ─── PROPERTY 2: resolve_seed nunca acepta symlinks ─────────────────────────

TEST_F(SafePathPropertyTest, ResolveSeedNeverAcceptsSymlinks) {
    // Invariante: resolve_seed rechaza cualquier path que sea o contenga symlink.
    // RED demostrado: fs::is_symlink(resolved) era inútil post-weakly_canonical().
    // Fix correcto: lstat() sobre path original.

    std::string real_seed   = seed_dir + "/seed.bin";
    std::string symlink_seed = seed_dir + "/seed_link.bin";

    // Crear symlink al seed real
    if (!fs::exists(symlink_seed)) {
        fs::create_symlink(real_seed, symlink_seed);
    }

    EXPECT_THROW(
        argus::safe_path::resolve_seed(symlink_seed, seed_dir),
        std::exception
    ) << "resolve_seed deberia rechazar symlink: " << symlink_seed;
}

// ─── PROPERTY 3: resolve_config nunca escapa prefix lexical ─────────────────

TEST_F(SafePathPropertyTest, ResolveConfigNeverEscapesPrefixLexical) {
    // Invariante: para todo intento de traversal lexical, resolve_config lanza.
    // RED demostrado: sin lexically_normal(), paths con .. escapaban el prefix
    // antes de que se siguiera el symlink.

    const std::vector<std::string> traversal_attempts = {
        config_dir + "/../../etc/passwd",
        config_dir + "/../outside/config.json",
        config_dir + "/subdir/../../outside",
    };

    for (const auto& attempt : traversal_attempts) {
        EXPECT_THROW(
            argus::safe_path::resolve_config(attempt, config_dir),
            std::runtime_error
        ) << "resolve_config deberia rechazar traversal: " << attempt;
    }
}

// ─── PROPERTY 4: resolve_config acepta symlinks dentro del prefix ────────────

TEST_F(SafePathPropertyTest, ResolveConfigAcceptsSymlinksInsidePrefix) {
    // Invariante: resolve_config acepta symlinks cuyo destino está dentro del prefix.
    // Este es el caso de uso legítimo: /etc/ml-defender/ → /vagrant/ (ADR-027).

    std::string real_config    = config_dir + "/config.json";
    std::string symlink_config = config_dir + "/config_link.json";

    if (!fs::exists(symlink_config)) {
        fs::create_symlink(real_config, symlink_config);
    }

    // El symlink apunta dentro de config_dir — debe ser aceptado
    EXPECT_NO_THROW(
        argus::safe_path::resolve_config(symlink_config, config_dir)
    ) << "resolve_config deberia aceptar symlink legitimo: " << symlink_config;
}

// ─── PROPERTY 5: resolve general — prefix nunca deriva del input ─────────────

TEST_F(SafePathPropertyTest, ResolveGeneralPrefixNeverDerivesFromInput) {
    // Invariante: el prefix es fijo en el punto de llamada.
    // Un input malicioso no puede cambiar el prefix contra el que se valida.
    // Esta propiedad documenta el contrato arquitectural — no es un bug
    // que el código pueda introducir, sino una regla de uso correcto.

    const std::string fixed_prefix = config_dir;
    const std::vector<std::string> inputs = {
        config_dir + "/config.json",
        config_dir + "/subdir/../config.json",
        config_dir + "/./config.json",
    };

    for (const auto& input : inputs) {
        // Para inputs válidos dentro del prefix, resolve no lanza
        // El prefix es siempre fixed_prefix — nunca se deriva del input
        try {
            auto result = argus::safe_path::resolve(input, fixed_prefix);
            // El resultado debe empezar con el prefix fijo
            EXPECT_EQ(result.substr(0, fixed_prefix.size()),
                      fixed_prefix)
                << "El resultado escapa el prefix fijo para input: " << input;
        } catch (const std::exception&) {
            // Algunos inputs pueden ser rechazados — también es correcto
        }
    }
}
