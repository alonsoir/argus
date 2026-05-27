// ============================================================================
// test_autonomy_state_writer.cpp — DEBT-AUTONOMY-STATE-PERSISTENCE-001 (DAY 157)
// ============================================================================
// RED→GREEN tests para AutonomyStateWriter.
//
// Casos cubiertos:
//   T1: write NORMAL  → read_and_verify → modo correcto
//   T2: write AUTONOMOUS → read_and_verify → modo correcto
//   T3: firma inválida (pk equivocada) → nullopt
//   T4: fichero ausente → nullopt
//   T5: JSON corrupto → nullopt
//   T6: campo faltante → nullopt
//   T7: AUTONOMOUS con timestamp > 24h → nullopt
//   T8: secuencia se preserva
//   T9: escritura atómica — fichero .tmp no queda tras write exitoso
// ============================================================================

#include "autonomy_state_writer.h"
#include <sodium.h>
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace fs = std::filesystem;
using namespace ml_defender;

// ── Helpers ───────────────────────────────────────────────────────────────────

static std::string tmp_path() {
    return "/tmp/argus-test-state-" +
           std::to_string(static_cast<uint64_t>(
               std::chrono::system_clock::now().time_since_epoch().count())) +
           ".json";
}

struct TestKeys {
    Ed25519PublicKey  pk{};
    Ed25519SecretKey  sk{};

    TestKeys() {
        std::array<uint8_t, 32> seed{};
        randombytes_buf(seed.data(), seed.size());
        crypto_sign_seed_keypair(pk.data(), sk.data(), seed.data());
    }
};

static int passed = 0;
static int failed = 0;

#define ASSERT_TRUE(expr)                                                    \
    do {                                                                      \
        if (!(expr)) {                                                        \
            std::cerr << "  FAIL [" << __LINE__ << "]: " #expr "\n";        \
            ++failed; return;                                                 \
        }                                                                     \
    } while (0)

#define ASSERT_FALSE(expr) ASSERT_TRUE(!(expr))

// ── Tests ─────────────────────────────────────────────────────────────────────

static void t1_write_normal_read_ok() {
    const std::string path = tmp_path();
    TestKeys keys;
    AutonomyStateWriter writer(path);

    writer.write(OperationalMode::NORMAL, keys.sk, "etcd-server", "boot", 1);
    auto rec = writer.read_and_verify(keys.pk);

    ASSERT_TRUE(rec.has_value());
    ASSERT_TRUE(rec->mode == OperationalMode::NORMAL);
    ASSERT_TRUE(rec->node_id == "etcd-server");
    ASSERT_TRUE(rec->reason == "boot");
    ASSERT_TRUE(rec->sequence == 1);

    fs::remove(path);
    std::cout << "  PASS T1: write NORMAL → read_and_verify OK\n";
    ++passed;
}

static void t2_write_autonomous_read_ok() {
    const std::string path = tmp_path();
    TestKeys keys;
    AutonomyStateWriter writer(path);

    writer.write(OperationalMode::AUTONOMOUS, keys.sk,
                 "etcd-server", "vault_unreachable", 7);
    auto rec = writer.read_and_verify(keys.pk);

    ASSERT_TRUE(rec.has_value());
    ASSERT_TRUE(rec->mode == OperationalMode::AUTONOMOUS);
    ASSERT_TRUE(rec->sequence == 7);

    fs::remove(path);
    std::cout << "  PASS T2: write AUTONOMOUS → read_and_verify OK\n";
    ++passed;
}

static void t3_wrong_pk_returns_nullopt() {
    const std::string path = tmp_path();
    TestKeys keys;
    TestKeys other_keys;  // keypair diferente
    AutonomyStateWriter writer(path);

    writer.write(OperationalMode::AUTONOMOUS, keys.sk,
                 "etcd-server", "vault_unreachable", 1);
    auto rec = writer.read_and_verify(other_keys.pk);  // pk equivocada

    ASSERT_FALSE(rec.has_value());

    fs::remove(path);
    std::cout << "  PASS T3: firma inválida (pk equivocada) → nullopt\n";
    ++passed;
}

static void t4_missing_file_returns_nullopt() {
    AutonomyStateWriter writer("/tmp/argus-nonexistent-state-xyz.json");
    TestKeys keys;
    auto rec = writer.read_and_verify(keys.pk);
    ASSERT_FALSE(rec.has_value());
    std::cout << "  PASS T4: fichero ausente → nullopt\n";
    ++passed;
}

static void t5_corrupt_json_returns_nullopt() {
    const std::string path = tmp_path();
    TestKeys keys;

    // Escribir JSON corrupto
    {
        std::ofstream f(path);
        f << "{ this is not json !!!";
    }

    AutonomyStateWriter writer(path);
    auto rec = writer.read_and_verify(keys.pk);
    ASSERT_FALSE(rec.has_value());

    fs::remove(path);
    std::cout << "  PASS T5: JSON corrupto → nullopt\n";
    ++passed;
}

static void t6_missing_field_returns_nullopt() {
    const std::string path = tmp_path();
    TestKeys keys;

    // JSON válido pero sin campo "signature_hex"
    {
        std::ofstream f(path);
        f << R"({"state":"NORMAL","entered_at_utc":"2026-05-19T03:00:00Z",)"
          << R"("sequence":1,"node_id":"etcd-server","reason":"boot"})";
    }

    AutonomyStateWriter writer(path);
    auto rec = writer.read_and_verify(keys.pk);
    ASSERT_FALSE(rec.has_value());

    fs::remove(path);
    std::cout << "  PASS T6: campo faltante → nullopt\n";
    ++passed;
}

static void t7_autonomous_expired_returns_nullopt() {
    const std::string path = tmp_path();
    TestKeys keys;

    // Escribir AUTONOMOUS con timestamp de hace 25 horas
    // Construir JSON manualmente con timestamp antiguo y firma válida
    nlohmann::json canonical;
    canonical["entered_at_utc"] = "2000-01-01T00:00:00Z";  // muy antiguo
    canonical["node_id"]        = "etcd-server";
    canonical["reason"]         = "vault_unreachable";
    canonical["sequence"]       = uint64_t{1};
    canonical["state"]          = "AUTONOMOUS";
    const std::string to_sign = canonical.dump();

    std::array<uint8_t, crypto_sign_BYTES> sig{};
    unsigned long long sig_len = 0;
    crypto_sign_detached(sig.data(), &sig_len,
        reinterpret_cast<const uint8_t*>(to_sign.data()),
        to_sign.size(), keys.sk.data());

    // Convertir sig a hex
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (size_t i = 0; i < sig_len; ++i)
        oss << std::setw(2) << static_cast<unsigned>(sig[i]);
    canonical["signature_hex"] = oss.str();

    {
        std::ofstream f(path);
        f << canonical.dump(2);
    }

    AutonomyStateWriter writer(path);
    auto rec = writer.read_and_verify(keys.pk);
    ASSERT_FALSE(rec.has_value());  // expirado → nullopt

    fs::remove(path);
    std::cout << "  PASS T7: AUTONOMOUS timestamp > 24h → nullopt\n";
    ++passed;
}

static void t8_sequence_preserved() {
    const std::string path = tmp_path();
    TestKeys keys;
    AutonomyStateWriter writer(path);

    writer.write(OperationalMode::RECONCILING, keys.sk,
                 "etcd-server", "vault_restored", 42);
    auto rec = writer.read_and_verify(keys.pk);

    ASSERT_TRUE(rec.has_value());
    ASSERT_TRUE(rec->sequence == 42);
    ASSERT_TRUE(rec->mode == OperationalMode::RECONCILING);

    fs::remove(path);
    std::cout << "  PASS T8: secuencia se preserva\n";
    ++passed;
}

static void t9_no_tmp_file_after_write() {
    const std::string path = tmp_path();
    const std::string tmp  = path + ".tmp";
    TestKeys keys;
    AutonomyStateWriter writer(path);

    writer.write(OperationalMode::NORMAL, keys.sk, "etcd-server", "boot", 1);

    ASSERT_TRUE(fs::exists(path));
    ASSERT_FALSE(fs::exists(tmp));

    fs::remove(path);
    std::cout << "  PASS T9: fichero .tmp no queda tras write exitoso\n";
    ++passed;
}

// ── main ─────────────────────────────────────────────────────────────────────

int main() {
    if (sodium_init() < 0) {
        std::cerr << "FATAL: sodium_init() falló\n";
        return 1;
    }

    std::cout << "=== test_autonomy_state_writer (DAY 157) ===\n";

    t1_write_normal_read_ok();
    t2_write_autonomous_read_ok();
    t3_wrong_pk_returns_nullopt();
    t4_missing_file_returns_nullopt();
    t5_corrupt_json_returns_nullopt();
    t6_missing_field_returns_nullopt();
    t7_autonomous_expired_returns_nullopt();
    t8_sequence_preserved();
    t9_no_tmp_file_after_write();

    std::cout << "\n";
    if (failed == 0) {
        std::cout << "✅ ALL " << passed << "/9 PASSED\n";
        return 0;
    } else {
        std::cout << "❌ " << failed << " FAILED, " << passed << " passed\n";
        return 1;
    }
}
