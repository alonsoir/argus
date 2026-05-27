#include "seed_client/seed_client.hpp"

#include <cassert>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace fs = std::filesystem;

// ─── Helpers ──────────────────────────────────────────────────────────────────

static std::string create_temp_dir() {
    fs::path tmp = fs::temp_directory_path() / "seed_client_test_XXXXXX";
    std::string tmpl = tmp.string();
    char* result = mkdtemp(tmpl.data());
    if (!result) {
        throw std::runtime_error("No se pudo crear directorio temporal");
    }
    return std::string(result);
}

static void write_json(const std::string& path,
                       const std::string& component_id,
                       const std::string& keys_dir) {
    std::ofstream f(path);
    f << "{\n"
      << "  \"identity\": {\n"
      << "    \"component_id\": \"" << component_id << "\",\n"
      << "    \"keys_dir\": \"" << keys_dir << "\"\n"
      << "  }\n"
      << "}\n";
}

static void write_seed_bin(const std::string& path, size_t num_bytes = 32) {
    std::ofstream f(path, std::ios::binary);
    for (size_t i = 0; i < num_bytes; ++i) {
        uint8_t b = static_cast<uint8_t>(i + 1);  // bytes 0x01..0x20
        f.write(reinterpret_cast<const char*>(&b), 1);
    }
    // Permisos 0600
    chmod(path.c_str(), 0400); // ADR-037: seed must be 0400
}

static void cleanup(const std::string& dir) {
    fs::remove_all(dir);
}

// ─── Tests ────────────────────────────────────────────────────────────────────

/**
 * TEST 1: Carga correcta
 * Verifica que load() funciona con un JSON válido y un seed.bin de 32 bytes.
 * Verifica component_id(), keys_dir(), is_loaded(), y que seed() no es todo ceros.
 */
static bool test_load_ok() {
    std::cout << "[TEST 1] load_ok ... ";

    const std::string tmp_dir  = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";
    const std::string keys_dir  = tmp_dir + "/keys/";
    const std::string seed_path = keys_dir + "seed.bin";

    fs::create_directory(keys_dir);
    write_json(json_path, "sniffer", keys_dir);
    write_seed_bin(seed_path);

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();

        assert(client.is_loaded());
        assert(client.component_id() == "sniffer");
        // keys_dir puede tener '/' añadido al final — comparar normalizado
        assert(client.keys_dir().find(tmp_dir) != std::string::npos);

        const auto& seed = client.seed();
        assert(seed.size() == 32);

        // Los bytes deben ser 0x01..0x20 (no todo ceros)
        bool all_zero = true;
        for (auto b : seed) {
            if (b != 0) { all_zero = false; break; }
        }
        assert(!all_zero);

        // Byte 0 debe ser 0x01
        assert(seed[0] == 0x01);
        assert(seed[31] == 0x20);

        ok = true;
        std::cout << "PASS\n";
    } catch (const std::exception& e) {
        std::cout << "FAIL: " << e.what() << "\n";
    }

    cleanup(tmp_dir);
    return ok;
}

/**
 * TEST 2: Fichero seed.bin no existe
 * Verifica que load() lanza std::runtime_error si seed.bin no existe.
 */
static bool test_file_not_found() {
    std::cout << "[TEST 2] file_not_found ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";
    const std::string keys_dir  = tmp_dir + "/keys/";

    fs::create_directory(keys_dir);
    write_json(json_path, "sniffer", keys_dir);
    // seed.bin NO se crea

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        std::cout << "FAIL: load() debió lanzar excepción\n";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        if (msg.find("seed.bin") != std::string::npos ||
            msg.find("provision") != std::string::npos) {
            ok = true;
            std::cout << "PASS (excepción correcta: " << msg << ")\n";
        } else {
            std::cout << "FAIL: excepción inesperada: " << msg << "\n";
        }
    }

    cleanup(tmp_dir);
    return ok;
}

/**
 * TEST 3: seed.bin con tamaño incorrecto (16 bytes en lugar de 32)
 * Verifica que load() lanza std::runtime_error si el seed no tiene 32 bytes.
 */
static bool test_wrong_size() {
    std::cout << "[TEST 3] wrong_size ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/ml-detector.json";
    const std::string keys_dir  = tmp_dir + "/keys/";
    const std::string seed_path = keys_dir + "seed.bin";

    fs::create_directory(keys_dir);
    write_json(json_path, "ml-detector", keys_dir);
    write_seed_bin(seed_path, 16);  // ← solo 16 bytes

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        std::cout << "FAIL: load() debió lanzar excepción\n";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        if (msg.find("32") != std::string::npos ||
            msg.find("bytes") != std::string::npos) {
            ok = true;
            std::cout << "PASS (excepción correcta: " << msg << ")\n";
        } else {
            std::cout << "FAIL: excepción inesperada: " << msg << "\n";
        }
    }

    cleanup(tmp_dir);
    return ok;
}

/**
 * TEST 4: component_id correcto para cada componente
 * Verifica que component_id() devuelve el valor exacto del JSON.
 */
static bool test_component_id() {
    std::cout << "[TEST 4] component_id ... ";

    const std::vector<std::string> components = {
        "etcd-server", "sniffer", "ml-detector",
        "firewall-acl-agent", "rag-ingester", "rag-security"
    };

    bool all_ok = true;

    for (const auto& comp : components) {
        const std::string tmp_dir   = create_temp_dir();
        const std::string json_path = tmp_dir + "/" + comp + ".json";
        const std::string keys_dir  = tmp_dir + "/keys/";
        const std::string seed_path = keys_dir + "seed.bin";

        fs::create_directory(keys_dir);
        write_json(json_path, comp, keys_dir);
        write_seed_bin(seed_path);

        try {
            ml_defender::SeedClient client(json_path);
            client.load();
            assert(client.component_id() == comp);
        } catch (const std::exception& e) {
            std::cout << "FAIL (" << comp << "): " << e.what() << "\n";
            all_ok = false;
        }

        cleanup(tmp_dir);
    }

    if (all_ok) {
        std::cout << "PASS (6 componentes verificados)\n";
    }
    return all_ok;
}

/**
 * TEST 5: Acceso a seed() antes de load() lanza excepción
 * Verifica que el contrato is_loaded() se hace cumplir.
 */
static bool test_not_loaded_guard() {
    std::cout << "[TEST 5] not_loaded_guard ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/sniffer.json";
    write_json(json_path, "sniffer", tmp_dir);

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        // load() NO llamado
        [[maybe_unused]] const auto& s = client.seed();  // debe lanzar
        std::cout << "FAIL: seed() debió lanzar excepción\n";
    } catch (const std::runtime_error& e) {
        ok = true;
        std::cout << "PASS (excepción correcta: " << e.what() << ")\n";
    }

    cleanup(tmp_dir);
    return ok;
}

/**
 * TEST 6: JSON sin bloque identity lanza excepción descriptiva
 */
static bool test_missing_identity_block() {
    std::cout << "[TEST 6] missing_identity_block ... ";

    const std::string tmp_dir   = create_temp_dir();
    const std::string json_path = tmp_dir + "/bad.json";

    {
        std::ofstream f(json_path);
        f << "{ \"network\": { \"port\": 5555 } }\n";  // sin identity
    }

    bool ok = false;
    try {
        ml_defender::SeedClient client(json_path);
        client.load();
        std::cout << "FAIL: load() debió lanzar excepción\n";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        if (msg.find("identity") != std::string::npos) {
            ok = true;
            std::cout << "PASS (excepción correcta: " << msg << ")\n";
        } else {
            std::cout << "FAIL: excepción inesperada: " << msg << "\n";
        }
    }

    cleanup(tmp_dir);
    return ok;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "\n=== SeedClient Test Suite ===\n\n";

    int passed = 0;
    int failed = 0;

    auto run = [&](bool (*test_fn)(), const char* name) {
        if (test_fn()) {
            ++passed;
        } else {
            ++failed;
            std::cerr << "  ↳ FAILED: " << name << "\n";
        }
    };

    run(test_load_ok,               "load_ok");
    run(test_file_not_found,        "file_not_found");
    run(test_wrong_size,            "wrong_size");
    run(test_component_id,          "component_id");
    run(test_not_loaded_guard,      "not_loaded_guard");
    run(test_missing_identity_block, "missing_identity_block");

    std::cout << "\n─────────────────────────────\n";
    std::cout << "Resultados: " << passed << "/" << (passed + failed)
              << " tests pasados\n";

    if (failed == 0) {
        std::cout << "✅ SUITE COMPLETA — SeedClient listo\n\n";
        return 0;
    } else {
        std::cout << "❌ " << failed << " test(s) fallaron\n\n";
        return 1;
    }
}