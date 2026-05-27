// test_seed_client_traversal.cpp
//
// ACCEPTANCE TEST — DEBT-PRODUCTION-TESTS-REMAINING-001 (seed-client)
// RED->GREEN: path traversal + symlink rejection en SeedClient.
// Consejo 8/8 DAY 125: material criptografico — sin compromiso de ergonomia.

#include "seed_client/seed_client.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>

namespace fs = std::filesystem;

static std::string create_temp_dir() {
    fs::path tmp = fs::temp_directory_path() / "seed_traversal_XXXXXX";
    std::string tmpl = tmp.string();
    char* result = mkdtemp(tmpl.data());
    if (!result) throw std::runtime_error("No se pudo crear directorio temporal");
    return std::string(result);
}

static void write_json(const std::string& path,
                       const std::string& component_id,
                       const std::string& keys_dir) {
    std::ofstream f(path);
    f << "{\n  \"identity\": {\n"
      << "    \"component_id\": \"" << component_id << "\",\n"
      << "    \"keys_dir\": \"" << keys_dir << "\"\n"
      << "  }\n}\n";
}

static void write_seed_bin(const std::string& path) {
    std::ofstream f(path, std::ios::binary);
    for (int i = 0; i < 32; ++i) {
        uint8_t b = static_cast<uint8_t>(i + 1);
        f.write(reinterpret_cast<const char*>(&b), 1);
    }
    chmod(path.c_str(), 0400);
}

static void cleanup(const std::string& dir) { fs::remove_all(dir); }

// ─── RED: path traversal en keys_dir ──────────────────────────────────────────
// ATAQUE: keys_dir = /tmp/legit/../../etc/ → seed_path sale del prefix
static bool test_reject_traversal_in_keys_dir() {
    std::cout << "[TEST 1] reject_traversal_in_keys_dir ... ";

    const std::string tmp_dir  = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";

    // keys_dir con ../ — intento de escape del prefix
    const std::string keys_dir = tmp_dir + "/../../tmp/";
    write_json(json_path, "sniffer", keys_dir);

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        std::cout << "FAIL: load() debia lanzar SECURITY VIOLATION\n";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        if (msg.find("SECURITY VIOLATION") != std::string::npos ||
            msg.find("traversal") != std::string::npos ||
            msg.find("lstat") != std::string::npos ||
            msg.find("seed.bin") != std::string::npos) {
            ok = true;
            std::cout << "PASS (excepcion correcta)\n";
        } else {
            std::cout << "FAIL: excepcion inesperada: " << msg << "\n";
        }
    }

    cleanup(tmp_dir);
    return ok;
}

// ─── RED: symlink como seed.bin ───────────────────────────────────────────────
// ATAQUE: seed.bin es un symlink → resolve_seed lanza SECURITY VIOLATION
static bool test_reject_symlink_as_seed() {
    std::cout << "[TEST 2] reject_symlink_as_seed ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";
    const std::string keys_dir  = tmp_dir + "/keys/";
    const std::string real_seed = tmp_dir + "/real_seed.bin";
    const std::string sym_seed  = keys_dir + "seed.bin";

    fs::create_directory(keys_dir);
    write_seed_bin(real_seed);
    fs::create_symlink(real_seed, sym_seed);  // seed.bin es symlink
    write_json(json_path, "sniffer", keys_dir);

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        std::cout << "FAIL: load() debia rechazar symlink\n";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        if (msg.find("SECURITY VIOLATION") != std::string::npos ||
            msg.find("symlink") != std::string::npos) {
            ok = true;
            std::cout << "PASS (symlink rechazado: " << msg << ")\n";
        } else {
            std::cout << "FAIL: excepcion inesperada: " << msg << "\n";
        }
    }

    cleanup(tmp_dir);
    return ok;
}

// ─── GREEN: path legitimo dentro de keys_dir ─────────────────────────────────
static bool test_legitimate_path_accepted() {
    std::cout << "[TEST 3] legitimate_path_accepted ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";
    const std::string keys_dir  = tmp_dir + "/keys/";
    const std::string seed_path = keys_dir + "seed.bin";

    fs::create_directory(keys_dir);
    write_seed_bin(seed_path);
    write_json(json_path, "sniffer", keys_dir);

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        assert(client.is_loaded());
        assert(client.component_id() == "sniffer");
        ok = true;
        std::cout << "PASS\n";
    } catch (const std::exception& e) {
        std::cout << "FAIL: " << e.what() << "\n";
    }

    cleanup(tmp_dir);
    return ok;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  DEBT-PRODUCTION-TESTS-REMAINING-001 — seed-client    \n";
    std::cout << "  RED->GREEN: traversal + symlink rejection             \n";
    std::cout << "═══════════════════════════════════════════════════════\n\n";

    int passed = 0, failed = 0;

    auto run = [&](bool (*fn)(), const char* name) {
        if (fn()) { ++passed; }
        else { ++failed; std::cerr << "  FAILED: " << name << "\n"; }
    };

    run(test_reject_traversal_in_keys_dir, "reject_traversal_in_keys_dir");
    run(test_reject_symlink_as_seed,       "reject_symlink_as_seed");
    run(test_legitimate_path_accepted,     "legitimate_path_accepted");

    std::cout << "\n─────────────────────────────\n";
    std::cout << "Resultados: " << passed << "/" << (passed + failed) << " tests pasados\n";

    if (failed == 0) {
        std::cout << "✅ SEED-CLIENT TRAVERSAL TESTS PASSED\n\n";
        return 0;
    } else {
        std::cout << "❌ " << failed << " test(s) fallaron\n\n";
        return 1;
    }
}
